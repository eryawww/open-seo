# OpenSEO

> Open source alternative to Semrush and Ahrefs

OpenSEO is an SEO tool for _the people_. If tools like Semrush or Ahrefs are too expensive or bloated, OpenSEO is a pay-as-you-go alternative that you actually control.

> All-in-one SEO tool for you and your AI agent.

Connect with any agent like Claude Code, OpenClaw or Hermes. We have pre-built skills, but you can build your own to tailor OpenSEO to your needs.

<img width="1385" height="794" alt="Image" src="https://github.com/user-attachments/assets/fd208249-44ea-4849-bb4b-5fc896aeab73" />

## Hosted Version

Try OpenSEO for free on our website. If you want to support the project, a hosted subscription is $10/month.

[openseo.so](https://openseo.so)

## Why use OpenSEO?

- Best in class MCP and AI Skills.
- Modern, simple UI.
  - Focused workflows instead of a bloated, complex SEO suite.
- No subscriptions.
  - Bring your own DataForSEO API key and pay only for what you use.
- Fork and vibe code your own custom tool.

## Main SEO Workflows

- Keyword research
- Rank tracking
- Competitor Insights
- Backlinks
- Site Audits
- AI Visibility

## OpenSEO MCP & Agent Skills

OpenSEO exposes an MCP server so AI agents like Claude Code, OpenClaw, and Hermes can use your SEO data directly. Agent Skills are reusable workflows that guide your agent through SEO tasks using the MCP.

- [Set up OpenSEO MCP](https://openseo.so/docs/mcp)
- [Set up OpenSEO Agent Skills](https://openseo.so/docs/skills/setup)

## Self-Hosting

OpenSEO supports two self-hosting paths:

- **Simple: Docker (Best for testing it out)** - For personal use on your own machine. See [`docs/SELF_HOSTING_DOCKER.md`](./docs/SELF_HOSTING_DOCKER.md).
  - Unless you already are self-hosting other apps and are confident doing so, we recommend self-hosting with Cloudflare as opposed to Railway, Coolify or Dokploy.
  - We plan to make it simpler to host on those platforms in the next few months.
- **Recommended: Cloudflare** - For internet-facing self-hosting across multiple devices or with your team (works on the free plan). See [`docs/SELF_HOSTING_CLOUDFLARE.md`](./docs/SELF_HOSTING_CLOUDFLARE.md).

Either way, you need a DataForSEO API key to get SEO data. See [`docs/DATAFORSEO_API_KEY.md`](./docs/DATAFORSEO_API_KEY.md).

## Adapting OpenSEO to Another Platform

This is a playbook for pointing a self-hosted OpenSEO instance at a product you
own and running it as a continuous SEO + GEO loop — an agent that acts on a
schedule — rather than a dashboard someone remembers to open. GEO here means
Generative Engine Optimization: being cited by ChatGPT, Claude, Gemini and
Perplexity, which is measured separately from classic search rank.

> **Scope note.** Steps 1, 3, 4 and 5 work on `main` as-is. Steps 2, 6 and 7
> depend on additions that live on this fork's `feat/seo-geo-cron` branch and
> are **not** on `main` — headless Service Token auth, the `explore_prompt`,
> `lookup_brand` and `record_content_action` MCP tools, and the `seo-geo-cron/`
> job runner. Each step below says what it needs.

### The loop you are building

```
  once ──► 1. deploy instance          your own Cloudflare Worker or Docker host
           2. headless credential      agent authenticates without a human
           3. project + context        who you are, who you compete with
           4. connect GSC / GA4        first-party truth, free to query

  daily ─► 5. observe                  rank, audit, citations, console data
           6. decide                   map each signal to one allowed action
           7. act + record             draft, escalate, or fix — then measure
              └──────────────────────► back to 5, with outcomes judged later
```

Steps 1–4 are setup and happen once. Steps 5–7 repeat on a schedule, and the
only thing that makes the loop worth running is that step 7 writes down what it
did so a later run can judge whether it worked.

### 1. Deploy an instance

Follow [`docs/SELF_HOSTING_CLOUDFLARE.md`](./docs/SELF_HOSTING_CLOUDFLARE.md)
for an internet-facing deployment, or
[`docs/SELF_HOSTING_DOCKER.md`](./docs/SELF_HOSTING_DOCKER.md) to try it
locally first. You need a DataForSEO key either way — see
[`docs/DATAFORSEO_API_KEY.md`](./docs/DATAFORSEO_API_KEY.md).

If you put the Cloudflare deployment behind Cloudflare Access, every route is
gated, including `/mcp`. Plan for that before wiring an agent to it.

### 2. Give the agent a headless credential

*Requires the `feat/seo-geo-cron` branch.*

An interactive OAuth login cannot complete from cron. Two options:

- **Hosted / API key.** Create a key in **Settings → API keys** and send
  `Authorization: Bearer oseo_...` or `x-api-key: oseo_...`.
- **Self-hosted behind Cloudflare Access.** Create a Service Token in Zero
  Trust → Access → Service Auth, add it as an **include** on the Access
  application's policy, then send both headers on every request:

  ```
  CF-Access-Client-Id:     <token-id>.access
  CF-Access-Client-Secret: <token-secret>
  ```

  The branch maps a verified Service Token's `common_name` claim to a stable
  app identity, so a headless caller gets a real user record instead of being
  rejected for having no email. Synthesized identities use the RFC 2606
  `.invalid` TLD and can never collide with a real address.

Verify with `whoami` before building anything on top — it returns your mode,
organization and remaining credits in one call.

### 3. Create the project and seed its context

Create the project, then fill its context with `update_project_context`. This
is the single highest-leverage step: every later job reads it instead of
carrying hardcoded assumptions, so correcting your positioning in one place
corrects every job at once.

Fill in, at minimum:

| Field | What it is for |
| --- | --- |
| `business_overview` | What the product is, its surfaces, its audience |
| `current_goal` | What this cycle is trying to move, and what is known broken |
| `positioning` | Competitive stance — a hypothesis, not a fact |
| `writing_preferences` | House style; binding on anything the agent drafts |
| `competitors` | The canonical list, so no job invents its own |
| `keyPages` | Hub / spoke / money pages, with measured performance |
| `researchLog` | What research has already been bought |

`get_project_context` is free. Have every job call it first, and have every job
check `researchLog` before spending credits on a question already answered.

### 4. Connect first-party data

Connect Google Search Console and, if you use it, GA4. These are the only
sources that tell you what your site actually does rather than what a
third-party index estimates, and both are **free to query** — no DataForSEO
credits. Budget your paid calls around them, not instead of them.

### 5. Define the action space before writing any automation

Decide what the agent is allowed to *do*, and keep the list short. A workable
split is three buckets plus an implicit fourth:

- **Auto-fix and open a PR** — broken links, missing meta, alt text, templated
  schema gaps. Mechanical, reviewable, low blast radius.
- **Write a content brief** — a keyword you should rank for and don't; a
  competitor cited where you are not.
- **Surface to a human** — Core Web Vitals regressions, novel schema gaps,
  wrong or outdated facts about you in an AI answer. Never auto-fix these.
- **Do nothing** — the correct and most common outcome. Say so explicitly, or
  the agent will invent work.

Write this mapping down before the first job runs. Without it, each run
re-derives its own policy and the system drifts.

### 6. Schedule the jobs

*Requires the `feat/seo-geo-cron` branch.*

`seo-geo-cron/` holds a worked example: one prompt per job, a shared preamble
concatenated into each, and a runner invoked by cron.

```
seo-geo-cron/
  run.sh                 prompt + job -> agent, unattended
  pilot-run.sh           same, but pauses for approval on every real action
  prompts/_common.md     rules identical across jobs, so they cannot drift
  prompts/<job>.md       one file per job
  data/                  budget, keyword plans, outcome database
```

Split by cadence and cost, not by topic — a daily cheap job and a weekly
expensive one, each with its own prompt:

| Job | Cadence | Costs credits? |
| --- | --- | --- |
| Technical health (site audit) | daily | crawl free; Lighthouse paid |
| Rank check | daily | yes — live SERP |
| SEO content | daily | mostly free (GSC-driven) |
| GEO citations | weekly | yes — one call per prompt per model |

Run everything through `pilot-run.sh` first. It withholds
`--dangerously-skip-permissions`, so every push, PR and issue stops for
approval and you can watch the agent's judgment before trusting it unattended.

Two rules worth copying: keep a **budget ceiling** the jobs read at runtime and
degrade against rather than overspend, and cap escalations at **one issue per
run per job** so a bad day cannot open twenty tickets.

### 7. Close the loop: act, record, judge

An agent that only reports is a worse dashboard. The value comes from acting
and then grading the action.

**Act through an account that cannot approve itself.** Publish via your
platform's own API using a writer-role service account that is structurally
incapable of approving or publishing, then route drafts to a human. A bot that
can publish its own work will eventually publish something wrong at 3am.

**Record every action locally, at the moment you take it** — topic, keywords,
the page you measured, baseline metrics, status. A small SQLite file next to
the jobs is enough, and it is the source of truth for every later decision.
`record_content_action` mirrors these rows into the SEO Pipeline dashboard
(free, and on the `feat/seo-geo-cron` branch); treat that mirror as best-effort
and never let a failed mirror block or roll back the local write.

**Judge later, as the first step of a future run.** Before looking for new
work, re-read your own rows that are old enough to have moved, pull fresh
Search Console data for the page the action actually produced, and mark the
outcome improved / flat / worse / rejected. Two details cause most of the
silent wrong answers here:

- Store the **canonical** URL form. If your site 301s the bare domain to
  `www.`, Search Console reports every row under `www.` and a bare-domain URL
  matches nothing — a page that is genuinely ranking gets judged on empty data.
- Keep the page that *inspired* an action separate from the page the action
  *created*. Conflating them makes a long-indexed parent page make a brand-new
  child look successful.

**Expect indexing to stay manual.** There is no API that makes Google index a
page faster — sitemap ping is deprecated, the Indexing API only covers
JobPosting and BroadcastEvent, and IndexNow does not reach Google. What you can
automate is *checking* status via `inspect_urls` and surfacing the
`inspectionResultLink` it returns, which is a one-click path to Search
Console's own Request Indexing button.

### Reference implementation

The `feat/seo-geo-cron` branch of this fork carries a complete working example
of steps 2, 6 and 7, along with design specs and implementation plans under
`docs/superpowers/`. Read it as a worked example to adapt, not as a drop-in —
its prompts, budget and keyword plans are specific to one site.

## Costs

OpenSEO needs a [DataForSEO](https://dataforseo.com/?aff=255379) API key so that you can get SEO data. You pay them directly when self hosting.

See [openseo.so/pricing](https://openseo.so/pricing)

When you self host, your costs will be slightly lower than the estimates on our website. The way the hosted service makes money is by charging 28% extra for every request we make to DataForSEO.

## Local Development

See [`docs/LOCAL_DEVELOPMENT.md`](./docs/LOCAL_DEVELOPMENT.md).

## Contributing

Creating clear issues is the best way to contribute.

Read more here: [`docs/CONTRIBUTING.md`](./docs/CONTRIBUTING.md)

We have this skill: `/simple-issue-description` which helps.

```sh
npx skills add every-app/open-seo --skill simple-issue-description
```

## Community

Join Discord to chat: [Discord](https://discord.gg/c9uGs3cFXr)

Follow along for updates:

- Follow on X: https://x.com/bensenescu
- Sign up for the mailing list on our website: [openseo.so](https://openseo.so)
