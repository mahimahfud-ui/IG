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


if __name__ == "__main__":
    unittest.main()
