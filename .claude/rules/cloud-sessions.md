# This fork and cloud sessions

This checkout is `eryawww/open-seo`, a public fork of `every-app/open-seo`. `main` mirrors upstream plus the
"Adapting OpenSEO to Another Platform" playbook in `README.md`. The klaussa.com SEO/GEO cron — job prompts, budget,
keyword plans, the SEO Pipeline page, `record_content_action` — lives on `feat/seo-geo-cron` and stays off `main` on
purpose. The self-hosted instance runs on Cloudflare (Alchemy stage `selfhost`).

## Run it

- In a cloud session, `.claude/settings.json` runs `scripts/cloud-session.sh` at start: pnpm at the pinned version,
  `pnpm install`, `.env.local` with `AUTH_MODE=local_noauth`, local D1 migrations. `DATAFORSEO_API_KEY` and
  `OPENROUTER_API_KEY` are copied into `.env.local` only when the cloud environment sets them; without them the paid
  SEO data and SAM features return errors and everything else runs.
- `pnpm dev` serves on port 3001. With `local_noauth`, `http://localhost:3001/mcp` needs no token, and `.mcp.json`'s
  `openseo-cron` server points there unless `OPENSEO_MCP_URL` is set.
- `pnpm test:e2e` runs on fixtures, not DataForSEO. In a cloud session set `PLAYWRIGHT_CHANNEL=chromium`; the browser
  comes from the environment's setup script through `PLAYWRIGHT_BROWSERS_PATH`.

## Checks

- Run the smallest set that covers the change: the focused `pnpm test` files, `pnpm types:check`, `pnpm lint`.
  `pnpm ci:check` before a PR that touches skills or `plugins/`.
- Anything that spends money — DataForSEO through the app or the MCP, OpenRouter, rank checks, GEO prompts — runs only
  when the owner asks.

## Branches, deploys and secrets

- Work on a branch and open a PR. Never push to `main` or `feat/seo-geo-cron` directly.
- The fork is public: no secrets, tokens, customer data or Search Console numbers in commits, PRs or issues. Never
  print `.env.local`, `.env.selfhost` or a cloud environment variable's value.
- Deploys of the self-hosted instance (`pnpm run deploy:selfhost`) run from the owner's machine: they need an Alchemy
  OAuth profile with the `access:write` scope. Cloud sessions don't deploy.
- A cloud routine running the SEO/GEO cron follows `seo-geo-cron/prompts/_cloud.md` on `feat/seo-geo-cron`. It drafts
  blog posts for human approval and never publishes them.
