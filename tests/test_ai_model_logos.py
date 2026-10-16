import os
import unittest
from unittest.mock import Mock, patch

import mahi_ai


class MahiAIModelAndLogoTests(unittest.TestCase):
    def test_default_model_is_gpt6_astra_with_high_reasoning(self):
        with patch.dict(os.environ, {
            "MAHI_AI_MODEL": "",
            "OPENAI_MODEL": "",
            "MAHI_AI_REASONING_EFFORT": "high",
        }):
            self.assertEqual(mahi_ai._active_model(), "gpt-6-astra")
            self.assertEqual(mahi_ai._active_reasoning_effort(), "high")

    def test_responses_request_sends_model_and_reasoning(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"id": "response-test", "output": []}
        with patch.dict(os.environ, {
            "MAHI_AI_MODEL": "",
            "OPENAI_MODEL": "",
            "MAHI_AI_REASONING_EFFORT": "high",
        }), patch("mahi_ai._require_ai", return_value="test-key"), patch(
            "mahi_ai.requests.post", return_value=response
        ) as post:
            mahi_ai._openai_request({"input": "test"})
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "gpt-6-astra")
        self.assertEqual(payload["reasoning"], {"effort": "high"})
        self.assertIs(payload["store"], False)

    def test_logo_candidates_prioritize_brand_and_large_icons(self):
        parser = mahi_ai._MetadataParser()
        parser.feed(
            '<link rel="icon" sizes="16x16" href="/favicon.ico">'
            '<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">'
            '<link rel="icon" sizes="any" href="/assets/brand-mark.svg">'
        )
        self.assertEqual(parser.icons[0], "/assets/brand-mark.svg")
        self.assertIn("/apple-touch-icon.png", parser.icons)
        self.assertEqual(parser.icons[-1], "/favicon.ico")


if __name__ == "__main__":
    unittest.main()
