# Cloud routine overlay

Read this before `_common.md` when a job runs as a Claude Code cloud routine (`CLAUDE_CODE_REMOTE=true`) instead of
through `run.sh` on a machine that keeps its files. It covers only what differs there; where it contradicts
`_common.md` or the job file, this file wins.

A routine starts on a fresh clone of the fork's default branch, which carries the `openseo-cron` MCP server
(`.mcp.json`) but not this directory. The routine prompt brings this directory in without switching branches, so the
MCP config and skills loaded at start stay on disk:

```
Run the klaussa.com SEO/GEO cron job "<rank-check|seo|geo>" as an unattended cloud routine.
1. git fetch origin feat/seo-geo-cron && git checkout FETCH_HEAD -- seo-geo-cron
2. Read seo-geo-cron/prompts/_cloud.md, then seo-geo-cron/prompts/_common.md, then
   seo-geo-cron/prompts/<job>.md, and carry out the job as they describe.
Do not commit or push anything.
```

`technical-health` does not run as a routine: its fixes are PRs on `klaussaindonesia/klaussa_fe`, and a routine with
this repository alone cannot reach that repository (a routine with two repositories loads no `.mcp.json`).

## Before anything else

1. Restore the state the laptop runner kept on disk:
   `python3 seo-geo-cron/cloud/state.py pull` (`rank-check` reads no local state and skips this).
   If it fails for any reason, stop the run there and make the error the run's final message. Never create
   `actions.sqlite` or `geo-history.sqlite` from scratch in a routine: an empty file empties the exclusion set and the
   GEO due-gate, so the run would re-draft topics already drafted and buy measurements already bought.
2. The variables `run.sh` sourced from `.env.local` (`BACKEND_URL`, `WRITER_EMAIL`, `WRITER_PASSWORD`,
   `BLOG_REVIEW_WORKER_URL`, `BLOG_REVIEW_HMAC_SECRET`, `BLOG_REVIEW_RECIPIENT`) come from the cloud environment.
   Never print them.

## While the job runs

- **Push state after every write.** After each successful write to `seo-geo-cron/data/*.sqlite` — every insert, every
  `drafted` → `proposed` flip, every judgment, every batch of `geo_runs` rows — run
  `python3 seo-geo-cron/cloud/state.py push`. The VM is discarded when the run ends; a row written after the last push
  is lost, and the next run drafts that topic again.
- **A failed push stops new work.** If a push reports that R2 changed since this run pulled it, another run is writing
  the same state: draft nothing more, record every `blog_id` drafted this run in an escalation (below), and end.
- **Escalations.** `gh issue create --repo klaussaindonesia/klaussa_fe` cannot work here: the routine reaches only
  this repository, and the cloud GitHub proxy blocks `gh issue` and `gh pr` outright. Commenting on an existing
  `klaussa_fe` issue, or reading `klaussa_fe`/`klaussa-lab` source, fails for the same reason. Where `_common.md`, the
  job file or the research log says to escalate or to comment on an issue:
  1. append one `appendResearchLog` entry starting `[ESCALATION] <the issue title>` with the facts the issue body
     would have carried (one line, under 1000 characters);
  2. start the run's final message with the same title and facts.

  "Check the issue does not already exist first" becomes: check the research log for an `[ESCALATION]` entry with the
  same title in the last 14 days. Never open an issue on `eryawww/open-seo` instead — it is public.

- **No local logs.** There is no `data/<job>.log`; the routine's run transcript is the log.

## Finishing

Run a last `state.py push` if anything changed since the previous one, then end with a short summary: drafts created
(`blog_id` and title), rows judged and their outcomes, escalations, and paid calls made.
