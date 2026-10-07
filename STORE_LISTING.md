# Chrome Web Store — Mahi Social Cleaner

## Current release

Manifest version: 1.2.0  
Manifest V3

## One-time first publish

Chrome Web Store requires a developer/publisher account with 2-step verification. Before a new item can be published, the Store listing and Privacy tabs must be completed in the Developer Dashboard. See Google's current API/publishing documentation:

https://developer.chrome.com/docs/webstore/using-api

Recommended first-release flow:

1. Open the Chrome Web Store Developer Dashboard.
2. Complete the publisher/developer account setup and 2-step verification.
3. Create/upload the extension package from the browser-helper folder.
4. Use the text in this file for the listing fields.
5. Set the Privacy policy URL to:
   https://mahi-unliker.onrender.com/privacy
6. Submit the first release for review and publish it.
7. Copy the resulting Chrome Web Store extension ID.

## Automatic updates after the first publish

The repository contains .github/workflows/chrome-webstore-publish.yml.

Add these GitHub Actions repository secrets:

- CHROME_WEBSTORE_CLIENT_ID
- CHROME_WEBSTORE_CLIENT_SECRET
- CHROME_WEBSTORE_REFRESH_TOKEN
- CHROME_WEBSTORE_PUBLISHER_ID
- CHROME_WEBSTORE_EXTENSION_ID

The Google OAuth token must use the Chrome Web Store scope:
https://www.googleapis.com/auth/chromewebstore

After these secrets exist, pushes that modify browser-helper/** can be wired to upload and publish new manifest versions through the Chrome Web Store API. Chrome requires the extension manifest version to increase for an update. The workflow in this repository is ready for this API-based update path.

## Store listing

### Product name
Mahi Social Cleaner

### Short description
Privacy-first Instagram utility dashboard for your own account.

### Detailed description
Mahi Social Cleaner is a browser-side utility dashboard for managing your own Instagram account from an organized Chrome extension.

Use it to review accounts you follow that do not follow you back, inspect liked activity exposed to your signed-in Instagram web session, open Instagram's own Comments Activity workflow, and build local InstaPy runner scripts.

### Main features
- Non-Followers: compare Following and Followers, search results, select accounts, open profiles, and confirm an unfollow batch.
- Likes: review liked posts exposed by Instagram's web session, search, select posts, open them, and confirm an unlike batch.
- Comments: open Instagram's own Comments Activity page and scan visible activity.
- Automation: build small original InstaPy runner scripts with configurable actions, target, amount, and delay.

### Privacy
The extension does not ask users to enter their Instagram password. It operates from the Instagram tab where the user is already signed in. Instagram session cookies and tokens are not sent to the Mahi server.

The extension stores only local UI preferences such as compact mode and reduced motion.

### Permissions
- activeTab: interact with the Instagram tab the user has explicitly opened or selected.
- storage: save local UI preferences.
- https://www.instagram.com/* host access: run the helper on Instagram pages and perform requested account actions from the user's existing browser session.

### Limitations
Instagram may change private web endpoints or page behavior at any time. The extension does not bypass CAPTCHAs, security checks, or rate limits. Users must review selections before confirming actions.

Mahi Social Cleaner is an independent project and is not affiliated with, endorsed by, or sponsored by Instagram or Meta.

## Homepage
https://github.com/mahimahfud-ui/IG
