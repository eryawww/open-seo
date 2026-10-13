#!/bin/bash
# Cloud sessions only (Claude Code on the web and routines), run by the SessionStart hook in .claude/settings.json:
# dependencies at the pinned pnpm, a local-only .env.local (AUTH_MODE=local_noauth) and the local D1 database, so the
# dev server (`pnpm dev`, port 3001), the unit tests and the Playwright e2e suites run without any real secret. Opt-in
# real keys are copied into .env.local only when the cloud environment sets them. The e2e browser comes from the
# environment's setup script. Silent on success; one line per problem, logs in /tmp. Always exits 0.
[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0
cd "$CLAUDE_PROJECT_DIR" || exit 0

# Environments that only run the SEO/GEO cron (no app code) skip the install and the local database.
[ "${CLOUD_SESSION_SKIP_SETUP:-}" = "1" ] && exit 0

# 1. Dependencies, at the pnpm version package.json pins: an older global pnpm rejects the lockfile.
want=$(node -p "require('./package.json').packageManager.replace(/^pnpm@/, '')")
if [ "$(pnpm --version 2>/dev/null)" != "$want" ]; then
  npm install -g "pnpm@$want" > /tmp/cloud-session-pnpm.log 2>&1 \
    || echo "cloud-session: could not install pnpm $want, see /tmp/cloud-session-pnpm.log"
fi
pnpm install --frozen-lockfile > /tmp/cloud-session-install.log 2>&1 \
  || echo "cloud-session: pnpm install failed, see /tmp/cloud-session-install.log"

# 2. Local-only .env.local: the trusted local auth mode, as docs/LOCAL_DEVELOPMENT.md sets it up. No real secrets.
if [ ! -f .env.local ]; then
  echo "AUTH_MODE=local_noauth" > .env.local
  chmod 600 .env.local
fi

# 3. Opt-in real keys the cloud environment sets. The Cloudflare Vite runtime reads Worker vars from .env.local, not
#    from the process environment, so copy them in on every start.
for key in DATAFORSEO_API_KEY OPENROUTER_API_KEY; do
  value="${!key:-}"
  [ -n "$value" ] || continue
  sed -i "/^${key}=/d" .env.local
  printf '%s=%s\n' "$key" "$value" >> .env.local
done

# 4. Local D1 database.
CI=1 pnpm run db:migrate:local > /tmp/cloud-session-migrate.log 2>&1 \
  || echo "cloud-session: local migrations failed, see /tmp/cloud-session-migrate.log"

if [ -n "${PLAYWRIGHT_BROWSERS_PATH:-}" ] && ! ls -d "$PLAYWRIGHT_BROWSERS_PATH"/chromium-* > /dev/null 2>&1; then
  echo "cloud-session: no Chromium under \$PLAYWRIGHT_BROWSERS_PATH; the e2e suites need the environment's setup script"
fi
exit 0
