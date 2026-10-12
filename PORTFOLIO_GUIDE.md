# Mahi Personal Website Hub

All public website pages are served from the single Flask app in this repository, from GitHub's `main` branch.

## Public routes

- `/` — animated Mahi portfolio / project directory.
- `/mahiflix/` — the MahiFlix movie and web-series discovery site.
- `/linkora/` — the Linkora / WinForge Windows scripts library.
- `/instagram-cleaner.html` — the preserved original Mahi Social Cleaner dashboard.
- `/privacy` and `/health` — existing routes.

The websites are kept under `web/mahiflix/` and `web/linkora/`. Their assets use path prefixes so they work under the same domain. Linkora's BAT downloads are served from `/linkora/downloads/`.

## Add another site later

1. Add its static website files to `web/<site-slug>/`.
2. Add a Flask route for `/<site-slug>/` in `app.py`, using `send_from_directory(os.path.join(app.root_path, "web", "<site-slug>"), "index.html")`, plus a redirect from `/<site-slug>` to the trailing-slash path.
3. Add a new project object to the `projects` array in `web/index.html`, with its local URL `/<site-slug>/`, description, category, artwork and GitHub source.
4. Commit and push to `main`. The unified Render service is connected to that branch for automatic deployment.

This means new projects can share the same purchased domain and deployment. The existing Instagram automation still needs a persistent Python web service; it should not be converted to a static-only host because its job runner uses background threads.
