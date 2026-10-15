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


    def test_mahi_ai_control_page_and_launcher_are_served(self):
        page = self.client.get("/mahi-ai/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Add Website", page.data)
        self.assertIn(b"Change Code / Route", page.data)
        launcher = self.client.get("/mahi-ai-launcher.js")
        self.assertEqual(launcher.status_code, 200)
        self.assertIn(b"/mahi-ai/", launcher.data)

    def test_mahi_ai_api_requires_access_token(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"MAHI_AI_ACCESS_TOKEN": "test-control-key", "OPENAI_API_KEY": ""}):
            denied = self.client.post("/api/mahi-ai/chat", json={"message": "hello", "action": "chat"})
            self.assertEqual(denied.status_code, 401)
            accepted_but_unconfigured = self.client.post(
                "/api/mahi-ai/chat", json={"message": "hello", "action": "chat", "history": []},
                headers={"Authorization": "Bearer test-control-key"},
            )
            self.assertEqual(accepted_but_unconfigured.status_code, 503)
            self.assertIn("OPENAI_API_KEY", accepted_but_unconfigured.get_json().get("reply", ""))

    def test_mahi_ai_status_never_returns_secret_values(self):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"MAHI_AI_ACCESS_TOKEN": "test-control-key", "OPENAI_API_KEY": "test-openai-key", "MAHI_AI_GITHUB_TOKEN": "test-github-key"}):
            response = self.client.get("/api/mahi-ai/status")
            self.assertEqual(response.status_code, 200)
            payload = response.get_json()
            self.assertTrue(payload["access_configured"])
            self.assertTrue(payload["ai_configured"])
            self.assertTrue(payload["github_configured"])
            self.assertNotIn("test-openai-key", response.get_data(as_text=True))
            self.assertNotIn("test-github-key", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
