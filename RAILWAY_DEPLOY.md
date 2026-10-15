# Deploy MahiCloud on Railway

This repository is configured for Railway's Nixpacks builder and the existing Flask application.

## Deploy

1. Sign in to Railway with the GitHub account that can access `mahimahfud-ui/mahicloud`.
2. Create a new project and choose **Deploy from GitHub repo**.
3. Select `mahimahfud-ui/mahicloud` and deploy the `main` branch.
4. Railway reads `railway.json` and `requirements.txt`; the configured web process starts `app:app` with Gunicorn and binds to Railway's `PORT`.
5. In the service's **Settings → Networking**, generate a public domain.
6. Wait for the deployment to finish, then open the generated domain. Railway checks the homepage at `/` for health.

## Optional environment variables

Set these under the service's **Variables** tab if your integrations need them:

- `SUPABASE_URL`
- `SUPABASE_PUBLISHABLE_KEY` (or the legacy `SUPABASE_ANON_KEY`)
- `YOUTUBE_URL`

Only add values that belong to your own project. Never commit API secrets to GitHub or put secret keys in frontend HTML/JavaScript.

## Notes

- The existing Render configuration is not removed or changed by this Railway setup.
- The Flask app currently keeps Instagram-cleaner jobs in process memory. They are not durable across restarts or multiple replicas; the configured single Gunicorn worker preserves the current in-process behavior, but Railway restarts still clear active jobs.
- This repository change prepares the project for Railway. The Railway service and domain must still be created from your Railway account, and a successful live deployment must be verified there.
