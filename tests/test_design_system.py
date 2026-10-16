import unittest

from app import app


class DesignSystemTests(unittest.TestCase):
    """Guards for the shared visual layer: assets are served, pages use them,
    motion stays opt-in/reduced-motion-safe, and Quick Add logic is untouched."""

    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def get_text(self, path):
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, path)
        return response.get_data(as_text=True)

    def test_tokens_stylesheet_is_served_with_core_tokens(self):
        css = self.get_text("/mahicloud-tokens.css")
        for token in ("--mc-bg", "--mc-fg", "--mc-accent", "--mc-font-display", "--mc-ease-out", "--mc-gutter"):
            with self.subTest(token=token):
                self.assertIn(token, css)

    def test_entrance_motion_is_reduced_motion_safe(self):
        css = self.get_text("/mahicloud-tokens.css")
        self.assertIn("prefers-reduced-motion: reduce", css)
        # Animations only run once <html> has .mc-ready, so nothing is hidden by default.
        self.assertIn(".mc-ready .mc-rise", css)
        self.assertNotIn("infinite", css)

    def test_homepage_and_apps_use_shared_tokens(self):
        for path in ("/", "/apps/"):
            with self.subTest(path=path):
                self.assertIn("/mahicloud-tokens.css", self.get_text(path))

    def test_homepage_hero_structure_and_content_preserved(self):
        html = self.get_text("/")
        for needle in ('class="mc-ln"', 'id="heroIndex"', "A world built by", "curiosity.", "Explore the store"):
            with self.subTest(needle=needle):
                self.assertIn(needle, html)
        for url in ("/mahiflix/", "/apps/", "/linkora/", "/instagram-cleaner.html"):
            self.assertIn(url, html)

    def test_hero_has_no_endless_ambient_animation(self):
        html = self.get_text("/")
        self.assertNotIn("animation:drift", html)

    def test_centered_layout_and_calc_compatibility(self):
        home = self.get_text("/")
        apps = self.get_text("/apps/")
        for page, needles in (
            (home, ('id="mc-center-layout-fix"', ".panel{align-items:center;text-align:center}", ".foot-row{flex-direction:column", ".stats{width:auto;justify-content:center;align-items:center;margin-inline:auto;padding:0;border:0;align-self:auto")),
            (apps, ('id="mc-apps-center-layout-fix"', ".hero{display:flex;flex-direction:column;align-items:center;text-align:center", ".apps-grid{display:grid")),
        ):
            for needle in needles:
                with self.subTest(needle=needle):
                    self.assertIn(needle, page)
        for page in (home, apps):
            self.assertNotIn("calc(100% - 2*var(--mc-gutter))", page)

    def test_quick_add_publishing_flow_is_untouched(self):
        js = self.get_text("/mahi-ai-launcher.js")
        self.assertIn("/api/catalog-add", js)
        self.assertIn("mahi-catalog-plus", js)
        self.assertIn("Detect & Add", js)


if __name__ == "__main__":
    unittest.main()
