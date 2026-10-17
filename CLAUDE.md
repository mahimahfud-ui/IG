# CLAUDE.md — MahiCloud project instructions

## Project context
- Repository: `mahimahfud-ui/mahicloud`.
- Default branch: `main`.
- This is an existing, working multi-page website/project collection. Treat the current repository as the source of truth.
- The public site and sub-sites include `web/index.html`, `web/apps/`, `web/mahiflix/`, `web/linkora/`, and other tools/pages under `web/`. The Python application serves routes and APIs; inspect the actual code before assuming how something works.

## When the user provides design briefs and MotionSite AI demos
1. Treat the user's own design prompt as the primary brief. Treat MotionSite AI prompts as visual/motion references, not replacement specifications.
2. Extract relevant layout, typography, transitions, scroll choreography, micro-interactions, hover states, and responsive ideas from each demo. Adapt those ideas to MahiCloud's actual pages and product purpose; do not blindly copy unrelated branding, copy, business content, or whole demo implementations.
3. First audit the relevant routes, existing structure, CSS/JS, assets, and tests. State a concise implementation plan, then implement rather than stopping at advice.
4. Preserve existing MahiCloud identity, working navigation, route destinations, page content/data, iframe/app router, Quick Add flow, privacy/security controls, APIs, and backend contracts unless the user explicitly asks to change a specific part.
5. Reuse the project's existing architecture and assets where reasonable. Do not add a frontend framework, build system, or large animation dependency just for effects without a clear need.

## Animation, UX, and performance
- Motion must track user input directly and feel smooth on wheel, trackpad, keyboard, touch, and anchor navigation. Avoid artificial scroll-follow easing that visibly falls behind the current scroll position.
- Prefer transform and opacity for animation. Avoid per-frame layout reads/writes, forced synchronous layout, continuously running requestAnimationFrame loops when no animation is visible, and expensive blur/blend/filter effects during scrolling.
- Respect `prefers-reduced-motion`; provide a usable reduced-motion experience, not just hidden animation.
- Make layouts responsive and touch-friendly; retain visible keyboard focus, semantic HTML, sufficient contrast, and accessible names.
- Optimize for real devices and slower hardware, not only a desktop preview. Avoid adding excessive parallax, animation stacking, or decorative layers that degrade scrolling.
- Keep the site useful and readable when JavaScript or an external font/image fails.

## Engineering workflow and safety
1. Start by checking `git status`, current branch, recent commits, and repository instructions. Never overwrite or discard pre-existing user changes.
2. Create a new descriptive branch for each redesign/fix. Do not work directly on `main`, force-push, or rewrite history.
3. Make focused changes that fit the relevant brief; do not mass-reformat or rewrite unrelated pages.
4. Run the relevant automated tests and available lint/build checks. Add or update regression tests for changed behavior. If browser testing is available, inspect desktop and mobile layouts and scroll interaction.
5. Review `git diff` for accidental route/data/API changes, broken links, console errors, accessibility regressions, secrets, or generated assets before finishing.
6. Push the branch and open a pull request for review. Do not merge to `main`, deploy, change deployment settings, or modify secrets without the user's explicit instruction.
7. Never claim tests, browser checks, or deployments passed unless they actually ran and succeeded. Summarize changed files, notable behavior changes, test results, and any unverified items.
8. Never expose credentials. Do not add tokens, passwords, API keys, or private configuration to source control.

## Definition of done for a redesign
- The relevant existing pages/routes still load and all important interactions work.
- The user's design brief is followed; MotionSite inspirations are adapted rather than copied wholesale.
- Scrolling and animation remain responsive, with reduced-motion support.
- Responsive layout, keyboard access, links, and existing business logic are checked.
- Relevant tests pass, and a reviewable branch/PR is ready.
