#!/usr/bin/env bash
# Run the official JevBench harness (public items: original 72, easy 48, hard 111) against any
# /v1/systemone endpoint and summarize. Output: runs/jevbench/<NAME>/{original,easy,hard}/ + summary JSON.
#
#   scripts/run_jevbench.sh kev08b runs/endpoints/kev08b.env    # a Modal endpoint from serve_modal.sh (URL + bearer key)
#   scripts/run_jevbench.sh krino-r3 http://10.0.0.5:8009       # any URL, no key
#   scripts/run_jevbench.sh kev08b-local                        # defaults to http://127.0.0.1:8009
#
# These are the PUBLIC items: use them to check the pipeline and to report, never to select a checkpoint.
set -euo pipefail
cd "$(dirname "$0")/.."
NAME="${1:?usage: run_jevbench.sh NAME [ENDPOINT_URL | endpoint.env]}"
TARGET="${2:-http://127.0.0.1:8009}"
KEY_ENV=""
if [ -f "$TARGET" ]; then
  # shellcheck disable=SC1090
  . "$TARGET"                         # sets ENDPOINT, KEV_API_KEY, KEV_MODEL
  export KEV_API_KEY; KEY_ENV="KEV_API_KEY"
else
  ENDPOINT="$TARGET"
fi
MODEL="${JEV_MODEL:-kev-latest}"
OUT="$PWD/runs/jevbench/$NAME"
if [ -e "$OUT" ]; then echo "refusing to overwrite $OUT (the harness never reuses a run dir)"; exit 1; fi
mkdir -p "$OUT"
echo "endpoint: $ENDPOINT  (auth: ${KEY_ENV:-none})"

cd third_party/jevbench
for TIER in original easy hard; do
  echo "== $TIER =="
  uv run --no-sync --project ../kev python -m jevbench.cli run \
    --tasks "datasets/public/$TIER.jsonl" \
    --adapter typesafe --endpoint "$ENDPOINT" --key-env "$KEY_ENV" --model "$MODEL" \
    --cost-basis no_billable_account_public_endpoint --reserve-usd 0 --delay-s 0 \
    --results "$OUT/$TIER/results.jsonl" --raw-dir "$OUT/$TIER/raw" \
    --ledger "$OUT/ledger.jsonl" --manifest "$OUT/$TIER/manifest.json" \
    --run-label "$NAME"
  uv run --no-sync --project ../kev python -m jevbench.cli summarize \
    --tasks "datasets/public/$TIER.jsonl" --results "$OUT/$TIER/results.jsonl" \
    --public-export "$OUT/$TIER/summary.json" | tail -n 25
done
echo
echo "done: $OUT"
