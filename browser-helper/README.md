# Mahi Instagram Helper v1.1

A clean, mobile-friendly Chrome/Edge extension dashboard for the Mahi Social Cleaner project.

## Included workspaces

**Home** — check the active Instagram session and jump to a tool.

**Non-Followers** — compare your Following and Followers lists, search the result, select accounts, open individual profiles, or confirm an unfollow batch.

**Likes** — read the liked-feed exposed to the current Instagram web session, search, open posts, select items, and confirm an unlike batch.

**Comments** — open Instagram's own Comments Activity page and scan the activity that is currently visible.

**Automation** — build a small original InstaPy runner script, copy it, download it, or open the official InstaPy docs/source.

## Privacy

The extension does not ask for an Instagram password. It runs from the Instagram tab where you are already signed in and does not send Instagram cookies/session tokens to the Mahi server.

## Install on desktop Chrome / Edge

1. Download the repository.
2. Open the browser's extension manager.
3. Turn on Developer mode.
4. Choose **Load unpacked**.
5. Select the **browser-helper** folder.
6. Open Instagram and log in normally.
7. Pin **Mahi Instagram Helper** and open it.

## Android

Standard Google Chrome for Android does not expose the desktop-style Load unpacked flow. Use an Android Chromium-based browser that supports extensions, or package this same browser helper into a native WebView/browser wrapper.

## Important

Instagram can change private web endpoints without notice. The helper does not bypass CAPTCHAs, security checks, rate limits, or other account protections. Review selections before confirming actions. Batch actions are capped at 25 items per click.

## Source / licensing

The helper is original project glue and UI. It uses browser-session techniques compatible with public community tooling and opens the official/source pages for third-party projects where appropriate.

See the repository's `THIRD_PARTY_LICENSES.md` for existing attributions.