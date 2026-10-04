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

if [ "$MODEL" = "stop" ]; then
  ( cd third_party/kev && uv run --no-sync modal app stop "krino-$NAME" )
  echo "stopped krino-$NAME"; exit 0
fi

shift 2
export KEV_MODEL="$MODEL" KEV_APP_NAME="krino-$NAME" KEV_TRUNCATE_STATES=1
export KEV_GPU="${KEV_GPU:-L4,L40S}"       # right for anything up to ~4B; override with KEV_GPU=H100 for bigger
for kv in "$@"; do export "$kv"; done
if [ -f "$ENVF" ]; then . "$ENVF"; fi
export KEV_API_KEY="${KEV_API_KEY:-$(openssl rand -hex 24)}"

( cd third_party/kev/skills/kev-deploy/scripts && uv run --no-sync --project ../../.. modal deploy kev_serve.py ) | tee "runs/endpoints/$NAME.deploy.log"
# the label is "<app>-api", so the URL is https://<workspace>--krino-<name>-api.modal.run
URL=$(grep -oE 'https://[A-Za-z0-9._-]+--krino-'"$NAME"'-api[A-Za-z0-9._-]*\.modal\.run' "runs/endpoints/$NAME.deploy.log" | head -1 || true)
[ -z "$URL" ] && URL=$(grep -oE 'https://[^ ]+\.modal\.run' "runs/endpoints/$NAME.deploy.log" | head -1 || true)
[ -z "$URL" ] && { echo "could not find the endpoint URL in the deploy output; see runs/endpoints/$NAME.deploy.log"; exit 1; }

printf 'ENDPOINT=%s\nKEV_API_KEY=%s\nKEV_MODEL=%s\n' "$URL" "$KEV_API_KEY" "$MODEL" > "$ENVF"
echo "endpoint: $URL   (settings in $ENVF)"
echo "warming the container (first start downloads the weights; up to a few minutes) ..."
curl -sL --max-time 900 "$URL/v1/models" -H "authorization: Bearer $KEV_API_KEY" | head -c 400; echo
