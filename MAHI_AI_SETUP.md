# MahiCloud Quick Add

The old Mahi AI chat page is hidden. A floating plus button is injected into HTML pages.

1. Click plus.
2. Enter the shared code 6993.
3. Paste an official Movie Website / Movie App / Music App URL, or describe a supported Windows BAT task.
4. The server reads page metadata, chooses a matching supported catalog category, downloads a safe logo into web/assets/submitted-logos, edits the existing catalog list, and commits to main.

This flow does not call OpenAI and does not require OpenAI API billing. Name/category detection uses the page's metadata and keyword rules, not a generative model. Generic services outside the existing Movie Websites, Movie Apps, and Music Apps catalogs are rejected. For BAT requests, it only generates pre-reviewed templates for flushing DNS, listing network information, testing internet connectivity, and creating a battery report. Arbitrary BAT imports are disabled.

## Flask hosting variables

- MAHI_AI_GITHUB_TOKEN: required; use a fine-grained token with Contents read/write permission for mahimahfud-ui/mahicloud. The token stays on the server.
- MAHI_AI_REPOSITORY: optional; defaults to mahimahfud-ui/mahicloud.
- MAHI_CATALOG_PASSWORD: optional; defaults to 6993. If changed, update the browser launcher code at the same time.

OPENAI_API_KEY and MAHI_AI_ACCESS_TOKEN are not used by quick-add.

## Deployment

Every successful item submission makes a commit to main. The production website shows that entry after its hosting service deploys the commit. The live service must point at this repository and main, with automatic deployments enabled.

## Safety

The shared PIN is visible in public JavaScript and is a lightweight shared prompt, not private authentication. This design intentionally permits visitors who know or inspect the code to add catalog entries. Rate limits, strict categories, SSRF checks and image-format checks reduce abuse but do not eliminate it. Logo downloads support common safe image types. Review Windows BAT scripts before running them.
