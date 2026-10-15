import unittest
from unittest.mock import patch

import mahi_ai


class FakeResponse:
    status_code = 200
    headers = {"Content-Type": "text/html; charset=utf-8"}

    def __init__(self, chunks):
        self.chunks = chunks
        self.closed = False
        self.yielded = 0

    def iter_content(self, chunk_size=8192):
        for chunk in self.chunks:
            self.yielded += 1
            yield chunk

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.trust_env = True
        self.closed = False

    def get(self, *args, **kwargs):
        return self.response

    def close(self):
        self.closed = True


class FetchPublicLimitTests(unittest.TestCase):
    def _run_fetch(self, response, *, max_bytes, allow_truncate=False):
        session = FakeSession(response)
        with patch.object(mahi_ai, "_assert_public_host"), patch.object(
            mahi_ai.requests, "Session", return_value=session
        ):
            result = mahi_ai._fetch_public(
                "https://example.com/", max_bytes=max_bytes, allow_truncate=allow_truncate
            )
        return result, session

    def test_metadata_style_fetch_returns_only_a_bounded_prefix(self):
        response = FakeResponse([b"123456", b"789xyz", b"must-not-be-read"])
        (url, content_type, body), session = self._run_fetch(
            response, max_bytes=7, allow_truncate=True
        )
        self.assertEqual(url, "https://example.com/")
        self.assertEqual(content_type, "text/html")
        self.assertEqual(body, b"1234567")
        self.assertEqual(response.yielded, 2)
        self.assertTrue(response.closed)
        self.assertTrue(session.closed)

    def test_oversized_resources_are_still_rejected_by_default(self):
        response = FakeResponse([b"123456", b"789xyz"])
        session = FakeSession(response)
        with patch.object(mahi_ai, "_assert_public_host"), patch.object(
            mahi_ai.requests, "Session", return_value=session
        ):
            with self.assertRaises(mahi_ai.MahiAIError) as error:
                mahi_ai._fetch_public("https://example.com/", max_bytes=7)
        self.assertEqual(error.exception.status, 413)
        self.assertIn("safety limit", error.exception.message)
        self.assertTrue(response.closed)
        self.assertTrue(session.closed)

    def test_metadata_extractor_opts_in_to_bounded_prefix(self):
        with patch.object(
            mahi_ai,
            "_fetch_public",
            return_value=(
                "https://example.com/",
                "text/html",
                b"<html><head><title>Example Catalog</title></head></html>",
            ),
        ) as fetch:
            metadata = mahi_ai._metadata_for_url("https://example.com/")
        fetch.assert_called_once_with(
            "https://example.com/", max_bytes=2_000_000, allow_truncate=True
        )
        self.assertEqual(metadata["title"], "Example Catalog")
        self.assertEqual(metadata["domain"], "example.com")


    def test_html_is_accepted_when_server_sends_wrong_content_type(self):
        body = b"\xef\xbb\xbf  <!DOCTYPE html><html><head><title>Page</title></head></html>"
        self.assertTrue(mahi_ai._looks_like_html("application/octet-stream", body))
        self.assertTrue(mahi_ai._looks_like_html("text/plain", b"<html><title>Page</title>"))

    def test_binary_download_is_not_mistaken_for_a_website(self):
        self.assertFalse(mahi_ai._looks_like_html("application/zip", b"PK\x03\x04binary data"))
        self.assertFalse(mahi_ai._looks_like_html("application/octet-stream", b"\x00\x01\x02\x03binary"))


    def test_non_html_detail_page_falls_back_to_site_homepage(self):
        with patch.object(
            mahi_ai,
            "_fetch_public",
            side_effect=[
                ("https://example.com/watch/123", "application/json", b'{"id":123}'),
                ("https://example.com/", "text/html", b"<html><head><title>Example Movies</title></head></html>"),
            ],
        ) as fetch:
            metadata = mahi_ai._metadata_for_url("https://example.com/watch/123")
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(metadata["url"], "https://example.com/")
        self.assertEqual(metadata["title"], "Example Movies")

    def test_direct_apk_url_is_rejected_without_homepage_fallback(self):
        with patch.object(
            mahi_ai,
            "_fetch_public",
            return_value=("https://example.com/app.apk", "application/vnd.android.package-archive", b"PK\\x03\\x04"),
        ) as fetch:
            with self.assertRaises(mahi_ai.MahiAIError) as error:
                mahi_ai._metadata_for_url("https://example.com/app.apk")
        self.assertEqual(error.exception.status, 415)
        self.assertIn("official homepage", error.exception.message)
        fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
