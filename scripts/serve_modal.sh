#!/usr/bin/env bash
# Put a Kev-format checkpoint behind an HTTPS /v1/systemone endpoint on Modal (one L4 / L40S, scales to zero when idle).
#
#   scripts/serve_modal.sh jaredpalmer/kev-0.8b kev08b          # -> runs/endpoints/kev08b.env  (URL + bearer key)
#   scripts/serve_modal.sh dhtocks/malkuth-2b malkuth2b
#   scripts/serve_modal.sh <you>/krino-2b krino-r3 KEV_GPU=L40S
#   scripts/serve_modal.sh stop malkuth2b                        # take it down (it also scales to zero by itself)
#
# Uses Kev's own deploy file (third_party/kev/skills/kev-deploy/scripts/kev_serve.py). The bearer key is generated here and
# saved only in runs/endpoints/<name>.env (gitignored). Long inputs are truncated rather than refused (a 422 scores as wrong).
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${1:?usage: serve_modal.sh MODEL NAME [KEY=VAL...] | stop NAME}"
NAME="${2:?usage: serve_modal.sh MODEL NAME}"
mkdir -p runs/endpoints
ENVF="$PWD/runs/endpoints/$NAME.env"
LOG="$PWD/runs/endpoints/$NAME.deploy.log"

if [ "$MODEL" = "stop" ]; then
  ( cd third_party/kev && uv run --no-sync modal app stop "krino-$NAME" --yes )
  echo "stopped krino-$NAME"; exit 0
fi

shift 2
export KEV_MODEL="$MODEL" KEV_APP_NAME="krino-$NAME" KEV_TRUNCATE_STATES=1
export KEV_GPU="${KEV_GPU:-L4,L40S}"       # right for anything up to ~4B; override with KEV_GPU=H100 for bigger
for kv in "$@"; do export "$kv"; done
if [ -f "$ENVF" ]; then . "$ENVF"; fi      # reuse the key of an earlier deploy of this name
export KEV_API_KEY="${KEV_API_KEY:-$(openssl rand -hex 24)}"
printf 'KEV_API_KEY=%s\nKEV_MODEL=%s\n' "$KEV_API_KEY" "$MODEL" > "$ENVF"   # saved before deploying, so it is never lost

# Krino's server (scripts/krino_serve_modal.py): Kev's stack, the checkpoint loaded raw, per-type temperatures from the
# checkpoint's krino.json (or KRINO_TEMPERATURES=choice=..,noul=..,score=.. passed as a KEY=VAL argument). Deployed from the
# repository root so the local krino package is mounted. KRINO_SERVER=0 deploys Kev's own kev_serve.py instead (one global T).
if [ "${KRINO_SERVER:-1}" = "1" ]; then
  ( uv run --no-sync --project third_party/kev modal deploy scripts/krino_serve_modal.py ) 2>&1 | tee "$LOG"
else
  ( cd third_party/kev/skills/kev-deploy/scripts && uv run --no-sync --project ../../.. modal deploy kev_serve.py ) 2>&1 | tee "$LOG"
fi

# Modal no longer prints the endpoint URL on deploy. It is https://<workspace>--<app>-api.modal.run; the workspace is the
# first path segment of the "View Deployment: https://modal.com/apps/<workspace>/..." line it does print.
WS=$(sed 's/\x1b\[[0-9;]*m//g' "$LOG" | grep -oE 'modal\.com/apps/[^/ ]+' | head -1 | sed 's|modal\.com/apps/||' || true)
URL=$(sed 's/\x1b\[[0-9;]*m//g' "$LOG" | grep -oE 'https://[A-Za-z0-9._-]+--krino-'"$NAME"'-api[A-Za-z0-9._-]*\.modal\.run' | head -1 || true)
[ -z "$URL" ] && [ -n "$WS" ] && URL="https://${WS}--krino-${NAME}-api.modal.run"
[ -z "$URL" ] && { echo "could not work out the endpoint URL; see $LOG. Set ENDPOINT=... in $ENVF by hand (it is on the app's Modal page)."; exit 1; }

printf 'ENDPOINT=%s\n' "$URL" >> "$ENVF"
echo "endpoint: $URL   (settings in $ENVF)"
echo "warming the container (first start downloads the weights; up to a few minutes) ..."
curl -sL --max-time 900 "$URL/v1/models" -H "authorization: Bearer $KEV_API_KEY" | head -c 400; echo
