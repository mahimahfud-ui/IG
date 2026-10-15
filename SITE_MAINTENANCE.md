# MahiCloud background AI maintenance

This repository includes a scheduled maintenance workflow that audits the site in the background and keeps one GitHub issue updated when checks fail.

## What runs automatically

- Runs every two hours and after relevant commits to the main branch.
- Checks Python syntax across the repository.
- Checks inline JavaScript syntax in HTML pages with Node.js.
- Checks local stylesheet, script, image, font, media and JSON references for missing files.
- Runs the existing Python route/unit tests.
- Checks important live routes on the configured production URL.
- Uploads a JSON diagnostics artifact for workflow runs.
- Creates or refreshes one GitHub issue when checks fail, then closes it after a later clean run.
- When the OpenAI API secret is configured, asks the model for a minimal repair only for repository/code-level errors. Proposed changes are validated and opened as a pull request; the system never pushes them directly to the main branch.

Live DNS, hosting, certificate and server outages are reported instead of being “fixed” by blindly changing application code.

## Enable AI repair

1. Open the repository on GitHub and go to **Settings → Secrets and variables → Actions → New repository secret**.
2. Add a secret named **OPENAI_API_KEY** with an API key from your OpenAI API account. API usage/billing is separate from a ChatGPT subscription.
3. Optional repository variables:
   - **SITE_BASE_URL**: canonical production origin, for example https://mahicloud.onrender.com.
   - **OPENAI_MODEL**: API model name. The default is gpt-5.5.
4. Open **Settings → Actions → General → Workflow permissions** and enable **Allow GitHub Actions to create and approve pull requests** so the workflow can open repair PRs using GITHUB_TOKEN.
5. Go to **Actions → MahiCloud AI site maintenance → Run workflow** to run a manual check.

The key stays in GitHub Actions Secrets and is not written to the repository. AI is called only when repairable code errors are present. AI usage may incur API charges.

## Safety boundaries

- No automatic merge or direct push of AI-generated changes to the main branch.
- AI edits are limited to existing web source files and app.py, with a small patch affecting at most three files.
- Workflows, tests, credentials, environment files, package/deployment configuration, authentication, security headers, rate limits, and APK host allow-lists are not AI-editable targets.
- Every proposed repair must pass syntax, local asset and existing unit-test checks before a pull request is opened.
- If only an external/live route problem is found, the system reports it instead of changing code.
- Review the diff and CI status before merging an AI repair pull request.
