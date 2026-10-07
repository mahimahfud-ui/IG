# Mahi Instagram Helper

A browser-side helper for the Mahi Social Cleaner project.

## Live account actions

The helper runs from the Instagram tab where you are already signed in.

### Non-Followers
It reads the signed-in account's Following and Followers lists, compares them locally, and shows accounts you follow that do not follow you back. You can select up to 25 accounts and unfollow them from one action, or open an individual profile first.

### Liked Posts
It reads the liked-feed exposed to the signed-in Instagram web session and shows the returned posts. You can select up to 25 and unlike them from one action, or open a post individually.

### Comments
Instagram's current Comments Activity page is used. The helper can read the comment activity visible on that page and open the related media. Instagram changes this UI frequently, so this part intentionally avoids blind destructive DOM automation.

## Privacy

- No Instagram password field.
- No Instagram cookies or session tokens are sent to the Mahi server.
- Requests are made from the user's existing instagram.com browser session.
- The extension stores no Instagram credentials.

## Install on desktop Chrome / Edge

1. Clone or download this repository.
2. Open the browser extension manager.
3. Enable Developer mode.
4. Choose Load unpacked.
5. Select the `browser-helper` folder.
6. Open Instagram, log in normally, then open Mahi Instagram Helper.

## Android

Google Chrome for Android does not provide the desktop-style "Load unpacked" extension flow. Use an Android Chromium-based browser that supports extensions, or package this same browser helper into a native WebView/browser wrapper.

## Limits

Instagram can change private web endpoints without notice. The helper does not bypass CAPTCHAs, security checks, rate limits, or other account protections. Review selected accounts/posts before taking an action.

## Source basis

The helper uses browser-session techniques compatible with public community tooling such as:
- InstaPy
- InstagramUnfollowers
- instagram-private-api

It does not copy their source code into this directory.