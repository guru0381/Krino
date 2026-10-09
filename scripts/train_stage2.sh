#!/usr/bin/env bash
# Stage 2 of Krino-2B: one combined delta on top of the stage-1 incumbent (docs/EVAL.md), two seeds, one H100 each.
# Data: evals/krino-mix-v1/train.jsonl (scripts/build_mix.sh) + 6,000 replay records from decision-v7's training
# partition; Kev's delta recipe (README "fine-tune on your own data"): lr 2e-5, one epoch, batch 2 x accum 4,
# max_state 7552 so hard-v1's policy states and most documents fit. Expect 2-3 h and ~$10 per trial.
#
#   scripts/train_stage2.sh                 # launches the study and returns; it keeps running if you disconnect
#   scripts/train_stage2.sh pull            # later: download runs/krino-stage2-2b (ranked by decision-v7 dev; we choose on the panel)
#   STUDY=krino-stage2-2b-b scripts/train_stage2.sh    # another study name for a re-run or a variant plan (PLAN=...)
set -euo pipefail
export KEV_HF_SECRET="${KEV_HF_SECRET:-huggingface-secret}"   # the Modal secret with HF_TOKEN, so reads and trials are not anonymous
cd "$(dirname "$0")/.."
STUDY="${STUDY:-krino-stage2-2b}"
PLAN="${PLAN:-$PWD/experiments/stage2-2b.json}"
MIX=third_party/kev/evals/krino-mix-v1

case "${1:-run}" in
  run)
    [ -f "$MIX/train.jsonl" ] || { echo "no mix: run scripts/build_mix.sh first" >&2; exit 1; }
    [ -f "$MIX/overlap.json" ] || { echo "mix not screened against JevBench: run scripts/build_mix.sh (it writes $MIX/overlap.json)" >&2; exit 1; }
    python3 -c "import json,sys; r=json.load(open('$MIX/overlap.json')); sys.exit(1 if r['offending_records'] else 0)" \
      || { echo "the screen found offending records; fix the mix before training" >&2; exit 1; }
    ( cd third_party/kev && uv run --no-sync modal run modal_app.py::study \
        --suite evals/v7/decision-v7 --plan "$PLAN" \
        --name "$STUDY" --transfer evals/v4/transfer-v4 --budget "${BUDGET:-50}" --timeout "${TIMEOUT:-14400}" )
    ;;
  pull)
    ( cd third_party/kev && uv run --no-sync modal run modal_app.py::pull --name "$STUDY" )
    echo "results: third_party/kev/runs/$STUDY — now score both trials on the panel:"
    echo "  scripts/eval_dev.sh /runs/$STUDY/00-trial-0/checkpoint s2-s0"
    echo "  scripts/eval_dev.sh /runs/$STUDY/01-trial-1/checkpoint s2-s1"
    ;;
  *) echo "usage: train_stage2.sh [run|pull]" >&2; exit 1 ;;
esac
