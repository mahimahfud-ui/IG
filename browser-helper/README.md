# Browser Tools

Standalone Instagram browser-session utility for Chrome/Brave. It works from an Instagram tab where you are already signed in and does not ask the extension for your Instagram password.

## Features

- Non-Followers scanner with live scan progress.
- Configurable unfollow limit and min/max pacing delay.
- Liked-post scanner with live scan progress.
- Configurable unlike limit and min/max pacing delay.
- Instagram Comments Activity viewer for currently visible activity.
- Select, review, and delete visible comment activity with configurable limit and min/max pacing delay.
- Per-action progress: processed, success, failed, and remaining.
- Local settings saved with Chrome extension storage.
- Existing Instagram session only; no password or session cookie is sent to the Mahi server.

## Controls

Limits are capped at 50 items per run. Sleep settings are local pacing controls between completed actions and are expressed in seconds in the UI.

The helper does not bypass CAPTCHAs, security checks, rate limits, or other account protections. Instagram can change private web endpoints or its UI without notice.

## Install

1. Extract the ZIP.
2. Open `brave://extensions/` or `chrome://extensions/`.
3. Turn on **Developer mode**.
4. Click **Load unpacked**.
5. Select this `browser-helper` folder (or the extracted folder containing `manifest.json`).
6. Open Instagram and sign in normally.
7. Pin and open **Browser Tools**.

## Updating the helper

After replacing the unpacked helper files with a newer version, open `chrome://extensions/` or `brave://extensions/` and click **Reload** on Browser Tools. A manually loaded extension does not update itself.

## Third-party

See `THIRD_PARTY_LICENSES.md` for existing project attributions.
