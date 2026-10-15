# Mahi AI — secure setup

Mahi AI is a private, server-side assistant for the MahiCloud repository. OpenAI and GitHub credentials are never embedded in the browser.

## 1. Add server environment variables

Open the environment-variable settings for the same host that runs the Flask app and add:

| Variable | Purpose |
|---|---|
| OPENAI_API_KEY | OpenAI API key used by the chatbot. |
| MAHI_AI_ACCESS_TOKEN | A long private password for the chatbot's access gate. |
| MAHI_AI_GITHUB_TOKEN | Fine-grained GitHub token for mahimahfud-ui/mahicloud. |
| MAHI_AI_REPOSITORY | Optional; defaults to mahimahfud-ui/mahicloud. |
| MAHI_AI_MODEL | Optional; defaults to gpt-5.5. |

Generate a strong access token locally with PowerShell:

    [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))

Do not put the access token, GitHub token, or OpenAI API key into HTML, JavaScript, Git commits, or chat messages.

## 2. GitHub token permissions

Create a fine-grained personal access token for only the mahicloud repository. Grant **Contents: Read and write** and **Pull requests: Read and write**. The chatbot reads repository source, adds catalog entries through Git database writes, and opens pull requests for ordinary code edits.

Use minimum scope and revoke the token immediately if it is exposed.

## 3. Open the assistant

After the Flask app is redeployed with these server-side environment variables, open:

    https://mahicloud.onrender.com/mahi-ai/

The access key is kept in the current browser tab's session storage. The assistant supports English, Bengali script and Banglish/Romanized Bangla.

## 4. Built-in actions

- **Add Website:** reads public page metadata, asks AI to classify the service, collects original icon/logo candidates, and adds supported movie website/app entries to the correct collection.
- **Add App:** routes supported apps to Movie Apps or Music Apps using the official page metadata.
- **Add BAT Tool:** imports a direct public BAT file or generates a Windows script from a description. Several destructive or suspicious command patterns are blocked. Always inspect a BAT file before running it.
- **Change Code / Route:** searches and reads supported repository files, stages exact changes and opens a GitHub pull request. It does not force-push or auto-merge code changes.

Catalogue additions and BAT entries are committed to main after validation. General code edits go to a pull request so you can review the diff and CI results before merging.

## 5. Hosting and cost

This requires a live Flask backend, outbound HTTPS access to OpenAI and GitHub, and the three server variables above. If the public domain only serves static files, the chat API will not work until the Flask backend is deployed on that origin or behind the same origin.

OpenAI API usage is billed separately from ChatGPT. Configure API usage limits in the OpenAI platform.

## 6. Safety limitations

The BAT checker is a conservative pattern check, not a malware scanner or Windows execution test. Never run unfamiliar scripts without reviewing them. BAT files are not executed on the web server. AI code edits are not auto-merged.
