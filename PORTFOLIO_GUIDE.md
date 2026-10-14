# Mahi Personal Website Hub

All public website pages are served from the single Flask app in this repository, from GitHub's `main` branch.

## Public routes

- `/` — animated, centered Mahi portfolio and project directory.
- `/mahiflix/` — movie and web-series website collection only.
- `/apps/` — separate animated app collection with movie apps and music apps.
- `/linkora/` — Linkora / WinForge Windows scripts library.
- `/lumr/` — LUMR photo and video gallery.
- `/@<username>` — LUMR public creator profiles, matching the source repo's URL pattern.
- `/unfollowers/` — local Instagram export comparison, without requesting account credentials.
- `/instagram-cleaner.html` — preserved original Mahi Social Cleaner dashboard.
- `/privacy` and `/health` — existing routes.

MahiFlix and Linkora live under `web/mahiflix/` and `web/linkora/`; Apps lives under `web/apps/`. Static assets use subpath-safe URLs. Linkora's BAT downloads are served from `/linkora/downloads/`.

## Add another site later

1. Add its static website files to `web/<site-slug>/`.
2. Add a Flask route for `/<site-slug>/` in `app.py`, using `send_from_directory(os.path.join(app.root_path, "web", "<site-slug>"), "index.html")`, plus a redirect from `/<site-slug>` to the trailing-slash path.
3. Add a project object to the `projects` array in `web/index.html`, with local URL `/<site-slug>/`, description, category, artwork and GitHub source.
4. Commit and push to `main`. The unified Render service auto-deploys changes from this branch.

One domain and one service can host every static project under a subpath. Projects requiring server-side code must be integrated into the shared Flask app or a compatible shared route.

## LUMR account and upload setup

The LUMR gallery is integrated under `web/lumr/`. To enable real accounts, public creator profiles and media uploads, run `supabase/schema.sql` in the intended Supabase project's SQL editor, then set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` on the MahiCloud Render service. `YOUTUBE_URL` is optional. `.env.example` contains placeholders only; never commit live keys or a service-role/secret key.
