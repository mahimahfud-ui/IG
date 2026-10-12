# Personal portfolio — project guide

The public homepage is `web/index.html`. The portfolio is a lightweight, responsive, single-file frontend with CSS animations, a rotating headline, project filters, scroll reveals, a theme switcher, and custom CSS artwork. It does not depend on a frontend framework or third-party font/image CDN.

## Add a new website or tool

Open `web/index.html` and find the `var projects = [` array inside the script near the bottom. Add a new object before the closing `];`:

```js
{
  id: "my-new-site",
  title: "My New Site",
  type: "website", // use "website" or "tool"
  label: "05 / Category",
  status: "Live",
  description: "A short, clear explanation of what the project does.",
  url: "https://example.com",
  repo: "https://github.com/mahimahfud-ui/my-new-site",
  art: "cinema", // use "cinema", "linkora", "social", or "browser"
  tags: ["Website", "Project"]
}
```

Use a unique lowercase `id`, your real project URL and repository URL, and an accurate status. Use `local: true` only for a project served by this same app (like `/instagram-cleaner.html`). Existing artwork styles can be reused, or new CSS art can be added in the stylesheet.

Commit the edit to `main`. The connected Render service is configured for automatic deploys when active; if the service is suspended, a code commit alone will not make the website live.

## Routes

- `/` — personal project portfolio.
- `/instagram-cleaner.html` — preserved original Mahi Social Cleaner dashboard.
- `/privacy` — existing privacy page.
- `/health` — existing Flask health endpoint.

The original Flask API and project files are intentionally left intact.
