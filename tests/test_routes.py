import unittest

from app import app


class MahiCloudRouteTests(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

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
            "/mahi-ai/",
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
                self.assertIn(b"/mahi-ai-launcher.js", page.data)
        launcher = self.client.get("/mahi-ai-launcher.js")
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


if __name__ == "__main__":
    unittest.main()
