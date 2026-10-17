import unittest

from app import app


class MahiCloudRouteTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_shared_mobile_polish_assets_and_page_metadata(self):
        from html.parser import HTMLParser

        class AssetParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.links = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                for attr in ("href", "src"):
                    value = attrs.get(attr, "")
                    if value:
                        self.links.append(value)

        pages = (
            "/", "/apps/", "/mahiflix/", "/linkora/", "/lumr/",
            "/instagram-cleaner.html", "/browser-helper-guide.html",
            "/unfollowers/", "/privacy", "/terms",
        )
        for path in pages:
            with self.subTest(page=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn("<title>", html)
                self.assertIn('name="description"', html)
                self.assertIn('href="/site-polish.css"', html)
                self.assertIn('src="/site-polish.js"', html)
                parser = AssetParser()
                parser.feed(html)
                for value in parser.links:
                    if not value.startswith("/") or value.startswith("//"):
                        continue
                    from urllib.parse import urlsplit
                    local_path = urlsplit(value).path
                    if not local_path or local_path.startswith("/api/"):
                        continue
                    linked = self.client.get(local_path, follow_redirects=False)
                    self.assertLess(
                        linked.status_code, 400,
                        f"Broken local link/asset {value!r} found on {path}",
                    )

    def test_custom_404_page_is_branded_and_returns_404(self):
        response = self.client.get("/this-page-should-not-exist")
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Page not found", response.data)
        self.assertIn(b"/site-polish.css", response.data)
        self.assertIn(b"Return to MahiCloud", response.data)

    def test_homepage_is_still_served(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"MahiCloud", response.data)

    def test_existing_project_routes(self):
        routes = [
            "/mahiflix/",
            "/linkora/",
            "/apps/",
            "/unfollowers/",
            "/lumr/",
            "/instagram-cleaner.html",
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_public_pages_hide_own_source_signposts(self):
        for path in ("/", "/apps/", "/mahiflix/", "/linkora/", "/instagram-cleaner.html", "/privacy", "/terms"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True).lower()
                self.assertNotIn("github.com/mahimahfud-ui", body)
                self.assertNotIn("source code", body)
                self.assertNotIn("ai-generated", body)
                self.assertNotIn("browser-helper folder", body)

    def test_quick_add_ui_uses_neutral_public_copy(self):
        response = self.client.get("/quick-add.js")
        self.assertEqual(response.status_code, 200)
        script = response.get_data(as_text=True).lower()
        for phrase in ("github", "render", "source code", "repository", "ai-generated", "chatgpt", "claude", "openai"):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, script)

    def test_browser_helper_guide_and_download_are_available_without_external_source_links(self):
        import io
        import zipfile

        guide = self.client.get("/browser-helper-guide.html")
        self.assertEqual(guide.status_code, 200)
        self.assertIn(b"/download/browser-helper.zip", guide.data)
        self.assertNotIn(b"github.com/mahimahfud-ui/mahicloud", guide.data)

        bundle = self.client.get("/download/browser-helper.zip")
        self.assertEqual(bundle.status_code, 200)
        self.assertIn("application/zip", bundle.headers.get("Content-Type", ""))
        with zipfile.ZipFile(io.BytesIO(bundle.data)) as archive:
            names = set(archive.namelist())
            for name in ("manifest.json", "background.js", "content.js", "dashboard-bridge.js", "popup.html", "popup.js"):
                self.assertIn(name, names)
            self.assertNotIn("README.md", names)

    def test_friendly_aliases_redirect_to_canonical_routes(self):
        cases = {
            "/windows-tools": "/linkora/",
            "/windows-tools/": "/linkora/",
            "/gallery": "/lumr/",
            "/gallery/": "/lumr/",
            "/social-tools": "/instagram-cleaner.html",
            "/social-tools/": "/instagram-cleaner.html",
            "/social-tools/instagram-cleaner": "/instagram-cleaner.html",
        }
        for route, destination in cases.items():
            with self.subTest(route=route):
                response = self.client.get(route, follow_redirects=False)
                self.assertIn(response.status_code, (301, 302, 307, 308))
                self.assertEqual(response.headers.get("Location"), destination)

    def test_integrated_assets_are_served(self):
        assets = [
            "/mahiflix/m-logo-v2.svg",
            "/mahiflix/cinema/cinema.css",
            "/mahiflix/cinema/scene.js",
            "/mahiflix/vendor/three.module.min.js",
            "/mahiflix/assets/logos/7reel.svg",
            "/lumr/cinematic.js",
            "/linkora/downloads/private-folder-hotkey.bat",
        ]
        for path in assets:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)

    def test_security_headers_and_api_cache_control(self):
        response = self.client.get("/api/config", headers={"X-Forwarded-Proto": "https"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertEqual(response.headers.get("Permissions-Policy"), "camera=(), microphone=(), geolocation=()")
        self.assertEqual(response.headers.get("Strict-Transport-Security"), "max-age=31536000; includeSubDomains")
        self.assertEqual(response.headers.get("Cache-Control"), "no-store")

    def test_start_endpoint_has_a_rate_limit(self):
        from app import _rate_events, _rate_lock

        key = ("start", self.client.get("/health").request.environ.get("REMOTE_ADDR") or "unknown")
        with _rate_lock:
            _rate_events.pop(key, None)

        for _ in range(5):
            response = self.client.post("/api/start", data={})
            self.assertEqual(response.status_code, 410)
        response = self.client.post("/api/start", data={})
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response.headers)

    def test_lumr_config_api_is_available_at_both_paths(self):
        for path in ("/api/config", "/lumr/api/config"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertIn("supabaseUrl", payload)
                self.assertIn("publishableKey", payload)
                self.assertIn("youtubeUrl", payload)

    def test_all_integrated_pages_have_responsive_device_polish(self):
        pages = [
            "/",
            "/mahiflix/",
            "/lumr/",
            "/linkora/",
            "/apps/",
            "/unfollowers/",
            "/instagram-cleaner.html",
        ]
        for route in pages:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertIn(b'name="viewport"', response.data)
                self.assertIn(b'id="mahi-device-polish"', response.data)
                self.assertIn(b'prefers-reduced-motion:reduce', response.data)
                self.assertIn(b'viewport-fit=cover', response.data)


    def test_railway_deployment_configuration(self):
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        railway = json.loads((root / "railway.json").read_text(encoding="utf-8"))
        self.assertEqual(railway["deploy"]["healthcheckPath"], "/")
        self.assertIn("app:app", railway["deploy"]["startCommand"])
        self.assertTrue((root / "Procfile").is_file())


    def test_old_ai_chat_is_hidden_and_quick_add_is_injected(self):
        response = self.client.get("/mahi-ai/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("Location"), "/")
        for path in ("/", "/mahiflix/", "/apps/", "/linkora/"):
            with self.subTest(path=path):
                page = self.client.get(path)
                self.assertEqual(page.status_code, 200)
                self.assertIn(b"/quick-add.js", page.data)
        launcher = self.client.get("/quick-add.js")
        self.assertEqual(launcher.status_code, 200)
        self.assertIn(b"mahi-catalog-plus", launcher.data)
        self.assertIn(b"/api/catalog-add", launcher.data)
        self.assertNotIn(b"Mahi AI Control", self.client.get("/").data)

    def test_catalog_add_needs_pin_but_not_openai_key(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"MAHI_CATALOG_PASSWORD": "6993", "MAHI_AI_GITHUB_TOKEN": "", "OPENAI_API_KEY": ""}):
            denied = self.client.post("/api/catalog-add", json={"password": "wrong", "input": "https://example.com"})
            self.assertEqual(denied.status_code, 401)
            self.assertIn("Incorrect password", denied.get_json().get("error", ""))
            unconfigured = self.client.post("/api/catalog-add", json={"password": "6993", "input": "https://example.com"})
            self.assertEqual(unconfigured.status_code, 503)
            self.assertIn("MAHI_AI_GITHUB_TOKEN", unconfigured.get_json().get("error", ""))
            self.assertNotIn("OPENAI_API_KEY", unconfigured.get_data(as_text=True))

    def test_catalog_add_rejects_blank_input(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"MAHI_CATALOG_PASSWORD": "6993", "MAHI_AI_GITHUB_TOKEN": "test-github-key"}):
            response = self.client.post("/api/catalog-add", json={"password": "6993", "input": " "})
            self.assertEqual(response.status_code, 400)
            self.assertIn("Paste a link", response.get_json().get("error", ""))



    def test_quick_add_is_category_first_with_distinct_url_and_script_steps(self):
        launcher = self.client.get("/quick-add.js")
        self.assertEqual(launcher.status_code, 200)
        source = launcher.get_data(as_text=True)
        for fragment in (
            "Choose a category",
            "Movie Websites",
            "Movie Apps",
            "Music Apps",
            "Windows Automation (.BAT)",
            "Windows Automation (.PY)",
            "function showUrl()",
            "function showCode()",
            "function showName()",
            "category:selectedCategory",
            "function showPin()",
            "/api/catalog-add/verify",
            "Unlock Quick Add",
            "Apps",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_category_add_rejects_unknown_categories_and_invalid_scripts_before_publish(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"MAHI_CATALOG_PASSWORD": "6993", "MAHI_AI_GITHUB_TOKEN": "", "OPENAI_API_KEY": ""}):
            unknown = self.client.post("/api/catalog-add", json={
                "password": "6993", "category": "unknown_category", "input": "https://example.com", "name": "Test"
            })
            self.assertEqual(unknown.status_code, 400)
            self.assertIn("supported Quick Add categories", unknown.get_json().get("error", ""))

            invalid_python = self.client.post("/api/catalog-add", json={
                "password": "6993", "category": "windows_python", "input": "def broken(:", "name": "Test Script"
            })
            self.assertEqual(invalid_python.status_code, 400)
            self.assertIn("syntax error", invalid_python.get_json().get("error", ""))

            invalid_bat = self.client.post("/api/catalog-add", json={
                "password": "6993", "category": "windows_bat", "input": "print('not a BAT file')", "name": "Test Script"
            })
            self.assertEqual(invalid_bat.status_code, 400)
            self.assertIn("readable Windows BAT", invalid_bat.get_json().get("error", ""))

            valid_python_without_github = self.client.post("/api/catalog-add", json={
                "password": "6993", "category": "windows_python",
                "input": "print('hello from a harmless utility')", "name": "Test Python Utility"
            })
            self.assertEqual(valid_python_without_github.status_code, 503)
            self.assertIn("MAHI_AI_GITHUB_TOKEN", valid_python_without_github.get_json().get("error", ""))



    def test_direct_app_download_uses_publisher_metadata_and_keeps_download_url(self):
        from unittest.mock import patch
        from mahi_ai import MahiAIError
        from mahi_catalog import _add_link, _app_metadata_page_url, _is_direct_app_download_url

        download_url = "https://github.com/FrancescoGrazioso/Meld/releases/download/v0.7.2/Meld-izzy.apk"
        publisher_url = "https://github.com/FrancescoGrazioso/Meld"
        self.assertTrue(_is_direct_app_download_url(download_url))
        self.assertEqual(publisher_url, _app_metadata_page_url(download_url))
        self.assertFalse(_is_direct_app_download_url("https://example.com/api/app"))

        metadata = {
            "url": publisher_url, "domain": "github.com", "title": "Meld",
            "description": "", "content_hint": "Android music player", "logo_sources": [],
        }
        seen_record = {}
        with patch("mahi_catalog._metadata_for_url", return_value=metadata) as scrape, \
             patch("mahi_catalog._download_logo", side_effect=MahiAIError("no usable logo")), \
             patch("mahi_catalog._repo_file", return_value={"content": "const otherApps=[];", "sha": "page-sha"}), \
             patch("mahi_catalog._insert_js_array_item", side_effect=lambda content, array_name, record: seen_record.update(record) or content), \
             patch("mahi_catalog._commit", return_value="https://github.com/mahimahfud-ui/mahicloud/commit/test-sha"):
            result = _add_link(download_url, download_url, "app", "Meld")

        scrape.assert_called_once_with(publisher_url)
        self.assertEqual(download_url, seen_record["url"])
        self.assertEqual("Download app", seen_record["linkLabel"])
        self.assertIn("Direct app download", seen_record["sublabel"])
        self.assertEqual("Apps", result["category_label"])

    def test_apps_category_switch_has_spacing_and_three_states(self):
        response = self.client.get("/apps/")
        self.assertEqual(response.status_code, 200)
        source = response.get_data(as_text=True)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", source)
        self.assertIn('body[data-category="apps"] .switch:before', source)
        self.assertIn("@media(max-width:520px)", source)

    def test_hidden_metadata_helper_detects_page_logo_images(self):
        from mahi_ai import _MetadataParser

        parser = _MetadataParser()
        parser.feed(
            '<html><head><title>Example Music</title>'
            '<link rel="icon" href="/favicon.ico">'
            '<link rel="apple-touch-icon" sizes="180x180" href="/touch-icon.png">'
            '</head><body>'
            '<img class="navbar-brand" alt="Example Music logo" width="180" height="48" src="/assets/example-logo.svg">'
            '<img src="/content/unrelated-photo.jpg" alt="Album cover">'
            '</body></html>'
        )
        self.assertEqual("Example Music", " ".join(parser.title_parts))
        self.assertTrue(parser.icons)
        self.assertIn("/assets/example-logo.svg", parser.logo_images)
        self.assertNotIn("/content/unrelated-photo.jpg", parser.logo_images)
        self.assertEqual("/touch-icon.png", parser.icons[0])


    def test_github_token_errors_distinguish_bad_credentials_permissions_and_rate_limit(self):
        import os
        from unittest.mock import Mock, patch
        from mahi_ai import MahiAIError, _github

        cases = [
            (401, "Bad credentials", "HTTP 401 (Bad credentials)"),
            (403, "Resource not accessible by personal access token", "Contents permission to Read and write"),
            (403, "API rate limit exceeded for 127.0.0.1", "API rate limit was exceeded"),
        ]
        for status_code, github_message, expected_message in cases:
            with self.subTest(status_code=status_code, github_message=github_message):
                response = Mock()
                response.status_code = status_code
                response.content = b'{"message":"test"}'
                response.json.return_value = {"message": github_message}
                with patch.dict(os.environ, {"MAHI_AI_GITHUB_TOKEN": "test-token"}):
                    with patch("mahi_ai.requests.request", return_value=response):
                        with self.assertRaises(MahiAIError) as captured:
                            _github("GET", "/user")
                self.assertIn(expected_message, captured.exception.message)
                self.assertNotIn("test-token", captured.exception.message)

    def test_catalog_add_diagnostic_requires_pin_and_never_returns_token(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"MAHI_CATALOG_PASSWORD": "6993", "MAHI_AI_GITHUB_TOKEN": "secret-not-for-response"}):
            denied = self.client.post("/api/catalog-add/diagnose", json={"password": "wrong"})
            self.assertEqual(denied.status_code, 401)
            self.assertNotIn("secret-not-for-response", denied.get_data(as_text=True))

            with patch("mahi_catalog._github") as github:
                github.side_effect = [
                    {"login": "mahimahfud-ui"},
                    {"full_name": "mahimahfud-ui/mahicloud", "permissions": {"push": True}},
                    {"object": {"sha": "test-main-sha"}},
                    {"sha": "test-blob-sha"},
                ]
                ok = self.client.post("/api/catalog-add/diagnose", json={"password": "6993"})
            payload = ok.get_json()
            self.assertEqual(ok.status_code, 200)
            self.assertTrue(payload["ok"])
            self.assertEqual("passed", payload["checks"]["contents_write_probe"])
            self.assertEqual("mahimahfud-ui", payload["checks"]["authenticated_as"])
            self.assertNotIn("secret-not-for-response", ok.get_data(as_text=True))
            self.assertEqual("POST", github.call_args_list[-1].args[0])
            self.assertEqual("/repos/mahimahfud-ui/mahicloud/git/blobs", github.call_args_list[-1].args[1])

    def test_catalog_add_diagnostic_identifies_contents_write_failure(self):
        import os
        from unittest.mock import patch
        from mahi_ai import MahiAIError
        with patch.dict(os.environ, {"MAHI_CATALOG_PASSWORD": "6993", "MAHI_AI_GITHUB_TOKEN": "secret-not-for-response"}):
            with patch("mahi_catalog._github") as github:
                github.side_effect = [
                    {"login": "mahimahfud-ui"},
                    {"full_name": "mahimahfud-ui/mahicloud", "permissions": {"push": True}},
                    {"object": {"sha": "test-main-sha"}},
                    MahiAIError("GitHub returned HTTP 403: Resource not accessible by personal access token. Failed endpoint: POST /repos/mahimahfud-ui/mahicloud/git/blobs."),
                ]
                response = self.client.post("/api/catalog-add/diagnose", json={"password": "6993"})
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual("contents_write", payload["stage"])
        self.assertEqual("mahimahfud-ui", payload["authenticated_as"])
        self.assertIn("does not prove what this token was granted", payload["message"])
        self.assertIn("repo scope", payload["message"])
        self.assertIn("POST /repos/mahimahfud-ui/mahicloud/git/blobs", payload["message"])
        self.assertNotIn("secret-not-for-response", response.get_data(as_text=True))

    def test_catalog_diagnostic_reports_actual_github_token_identity(self):
        import os
        from unittest.mock import patch
        from mahi_ai import MahiAIError

        with patch.dict(os.environ, {"MAHI_CATALOG_PASSWORD": "6993", "MAHI_AI_GITHUB_TOKEN": "test-token"}):
            with patch("mahi_catalog._github") as github:
                github.side_effect = [
                    {"login": "another-account"},
                    {"full_name": "mahimahfud-ui/mahicloud", "permissions": {"push": False}},
                    {"object": {"sha": "test-main-sha"}},
                    MahiAIError("GitHub returned HTTP 403: Resource not accessible by personal access token."),
                ]
                response = self.client.post("/api/catalog-add/diagnose", json={"password": "6993"})

        payload = response.get_json()
        self.assertEqual("contents_write", payload["stage"])
        self.assertEqual("another-account", payload["authenticated_as"])
        self.assertIn("not the repository owner @mahimahfud-ui", payload["message"])
        self.assertNotIn("test-token", response.get_data(as_text=True))


    def test_publish_403_message_includes_exact_endpoint(self):
        import os
        from unittest.mock import Mock, patch
        from mahi_ai import MahiAIError, _github

        response = Mock()
        response.status_code = 403
        response.content = b'{"message":"Resource not accessible by personal access token"}'
        response.json.return_value = {"message": "Resource not accessible by personal access token"}
        response.headers = {"X-Accepted-GitHub-Permissions": "contents=write"}
        with patch.dict(os.environ, {"MAHI_AI_GITHUB_TOKEN": "secret-not-for-response"}):
            with patch("mahi_ai.requests.request", return_value=response):
                with self.assertRaises(MahiAIError) as captured:
                    _github("POST", "/repos/mahimahfud-ui/mahicloud/git/blobs", payload={"content": "probe"})
        self.assertIn("POST /repos/mahimahfud-ui/mahicloud/git/blobs", captured.exception.message)
        self.assertIn("contents=write", captured.exception.message)
        self.assertNotIn("secret-not-for-response", captured.exception.message)

    def test_catalog_add_pin_can_be_verified_before_selecting_a_category(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"MAHI_CATALOG_PASSWORD": "6993", "MAHI_AI_GITHUB_TOKEN": "", "OPENAI_API_KEY": ""}):
            wrong = self.client.post("/api/catalog-add/verify", json={"password": "wrong"})
            self.assertEqual(wrong.status_code, 401)
            self.assertIn("Incorrect password", wrong.get_json().get("error", ""))

            correct = self.client.post("/api/catalog-add/verify", json={"password": "6993"})
            self.assertEqual(correct.status_code, 200)
            self.assertTrue(correct.get_json().get("ok"))
            self.assertNotIn("OPENAI_API_KEY", correct.get_data(as_text=True))



    def test_homepage_usability_refinements_are_present(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        source = response.get_data(as_text=True)
        self.assertIn('<style id="mc-usability-refinements">', source)
        for fragment in (
            "--mc-type-display",
            "--mc-text-primary",
            "--mc-r-pill",
            "text-transform: none;",
            '#mcMainNav > a[aria-current="page"]',
            "#top .cta > a.pill:focus-visible",
            ".search input:focus-visible",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_homepage_quick_add_and_mahiflix_audit_fixes(self):
        home = self.client.get("/")
        quick_add = self.client.get("/quick-add.js")
        mahiflix = self.client.get("/mahiflix/")

        self.assertEqual(home.status_code, 200)
        self.assertEqual(quick_add.status_code, 200)
        self.assertEqual(mahiflix.status_code, 200)
        home_source = home.get_data(as_text=True)
        quick_source = quick_add.get_data(as_text=True)
        movie_source = mahiflix.get_data(as_text=True)

        for fragment in (
            "height:280vh;min-height:1600px",
            "Apps, films &amp;",
            '#nav ul{display:none!important}',
            'routeGap=activeRoute==="movies"?8:0',
            "#skip {",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, home_source)

        for fragment in (
            'buttonLabel.textContent="Quick add"',
            ".mc-catalog-plus-label{white-space:nowrap}",
            'body:has([data-mc-frame-panel="movies"].is-active) #mahi-catalog-plus',
            "var(--mc-text-primary,#f3efe8)",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, quick_source)

        for fragment in (
            "--mf-text-primary",
            "--mf-text-display",
            "--mf-r-pill",
            "--mf-action-secondary",
            "font-size:var(--mf-text-display)",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, movie_source)

if __name__ == "__main__":
    unittest.main()
