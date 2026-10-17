# Security notes for MahiCloud

## Secrets and environment variables
- Never commit `.env`, production credentials, private keys, database passwords, or Supabase service-role/secret keys.
- Store production secrets in the hosting provider's environment-variable/secret settings.
- `.env.example` must contain names and blank placeholders only; never put default PINs or example credentials in it.
- Supabase publishable/anon keys are intended for client use only when Row Level Security (RLS) and least-privilege policies are correctly configured. Never put a service-role key in browser code or a public API response.
- If a credential was ever committed, rotate/revoke it first. Removing it from the latest commit does not remove it from Git history.

## API and deployment
- Keep debug mode disabled in production and run the app using the production server command in `Procfile`.
- API rate limits in the Flask process are best-effort and per-process. For multiple workers/instances, move limits to a shared store such as Redis.
- Quick Add is a privileged publishing endpoint protected by a shared secret. It now fails closed unless `MAHI_CATALOG_PASSWORD` is explicitly set to a unique value of at least 24 characters. This is not individual user authentication or role-based access control; do not add new admin routes without proper authentication, authorization, CSRF protection where applicable, and audit logging.
- The current social-cleaner job IDs are high-entropy capability tokens. Treat them as secrets and do not share them; they are not a substitute for a full account system.
- The app does not configure permissive CORS middleware; keep API calls same-origin unless a specific trusted origin is deliberately allow-listed.
- No database connection is defined in the Flask backend reviewed here. Review Supabase RLS, storage policies, and database permissions separately if those services are used by frontend subprojects.

## Reporting
If you discover a credential in a commit or deployment log, revoke/rotate it immediately, then investigate access logs and remove it from history where appropriate.
