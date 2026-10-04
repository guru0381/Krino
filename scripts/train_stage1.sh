#!/usr/bin/env bash
# Stage 1 of Krino-2B: Kev's released recipe (decision-v7 suite, LoRA r16, pointer head, 2 epochs)
# on Qwen/Qwen3.5-2B-Base, two seeds, one H100 per trial on Modal. About 35–45 min and ~$3 per trial.
#
# Before running:  scripts/pin_base.py  → paste the sha into experiments/stage1-2b.json
#                  cd third_party/kev && uv run modal token new && uv run modal deploy modal_app.py
#
#   scripts/train_stage1.sh                 # launches the study and returns; it keeps running if you disconnect
#   scripts/train_stage1.sh pull            # later: download runs/krino-stage1-2b, ranked by the dev suite
set -euo pipefail
cd "$(dirname "$0")/.."
STUDY="${STUDY:-krino-stage1-2b}"
PLAN="$PWD/experiments/stage1-2b.json"

if grep -q PIN_ME "$PLAN"; then
  echo "pin the base revision first: uv run --no-sync --project third_party/kev python scripts/pin_base.py" >&2; exit 1
fi

cd third_party/kev
case "${1:-run}" in
  run)
    uv run modal run modal_app.py::study \
      --suite evals/v7/decision-v7 --plan "$PLAN" \
      --name "$STUDY" --transfer evals/v4/transfer-v4 --budget 30 --timeout 7200
    ;;
  pull)
    uv run modal run modal_app.py::pull --name "$STUDY"
    echo "results: third_party/kev/runs/$STUDY (choose on development results only)"
    ;;
  *) echo "usage: train_stage1.sh [run|pull]" >&2; exit 1 ;;
esac
