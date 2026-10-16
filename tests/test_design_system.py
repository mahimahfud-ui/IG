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

    def test_homepage_canvas_animation_is_event_driven(self):
        html = self.get_text("/")
        self.assertIn("function scheduleFrame()", html)
        self.assertIn("if(frameId || document.hidden) return", html)
        self.assertIn('document.addEventListener("visibilitychange"', html)
        self.assertNotIn("/* never cancelled */", html)
        self.assertIn("@media(prefers-reduced-motion:reduce){.stage::before,.grad,.grid.in .card{animation:none!important}}", html)

    def test_hidden_project_iframes_pause_expensive_animation_loops(self):
        home = self.get_text("/")
        for needle in (
            "function setFrameVisibility(route,visible)",
            '"mahicloud:visibility"',
            "setFrameVisibility(previousRoute,false)",
            "setFrameVisibility(route,true)",
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, home)

        lumr = self.get_text("/lumr/cinematic.js")
        self.assertIn('document.addEventListener("mahicloud:visibility"', lumr)
        lumr_page = self.get_text("/lumr/")
        self.assertIn("stopCursor", lumr_page)
        self.assertIn('document.addEventListener(\'mahicloud:visibility\'', lumr_page)

        cinema_main = self.get_text("/mahiflix/cinema/main.js")
        self.assertIn('"mahicloud:visibility"', cinema_main)
        self.assertIn("scene.setVisible(workspaceVisible)", cinema_main)
        cinema_scene = self.get_text("/mahiflix/cinema/scene.js")
        self.assertIn("function setVisible(visible)", cinema_scene)
        self.assertIn("!workspaceVisible", cinema_scene)

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

    def test_quick_add_has_pin_gate_and_category_specific_publish_flow(self):
        js = self.get_text("/mahi-ai-launcher.js")
        self.assertIn("/api/catalog-add", js)
        self.assertIn("/api/catalog-add/verify", js)
        self.assertIn("mahi-catalog-plus", js)
        for step in (
            "Unlock Quick Add",
            "function showPin()",
            "Choose a category",
            "Apps",
            "Movie Websites",
            "Movie Apps",
            "Music Apps",
            "Windows Automation (.BAT)",
            "Windows Automation (.PY)",
            "function showUrl()",
            "function showCode()",
            "function showName()",
            "category:selectedCategory",
        ):
            with self.subTest(step=step):
                self.assertIn(step, js)


if __name__ == "__main__":
    unittest.main()
