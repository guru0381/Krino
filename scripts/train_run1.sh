#!/usr/bin/env bash
# Run 1 of Krino-2B: the judge + documents delta on top of the stage-2 incumbent (docs/EVAL.md), two seeds, one H100 each.
# Data: evals/krino-run1/train.jsonl (scripts/build_run1.sh: HelpSteer2 + strands adequacy, ContractNLI/MuSiQue/BoardgameQA,
# strands' generated documents, + 6,000 decision-v7 and 6,000 mix-v1 replay rows) with anchors.json (scripts/run1_reads.sh:
# the frozen Qwen3.5-4B's distributions on the multi-step rows, the incumbent's own on the replay rows; KL weight 1.0).
# The anchor applies to every record that has a target (kev.train's default): the plan names no anchor_sources, because
# Kev validates that key against the *study* suite's trainable sources (decision-v7's), not the data file's.
# Kev's delta recipe otherwise: lr 2e-5, one epoch, batch 2 x accum 4, max_state 7552. ~35k rows: expect 2-4 h and ~$12 per trial.
# Kev's admission bound is timeout-based (trials x ceiling hours x its H100 rate): two 6 h ceilings bound at $68.10, so the
# budget is 70; the spend is what the trials actually run (stage 2's seed 0: 3 h 31 m).
#
#   scripts/train_run1.sh                 # launches the study and returns; it keeps running if you disconnect
#   scripts/train_run1.sh pull            # later: download runs/krino-run1-2b (ranked by decision-v7 dev; we choose on the panel)
set -euo pipefail
export KEV_HF_SECRET="${KEV_HF_SECRET:-huggingface-secret}"   # the Modal secret with HF_TOKEN, so reads and trials are not anonymous
cd "$(dirname "$0")/.."
STUDY="${STUDY:-krino-run1-2b}"
PLAN="${PLAN:-$PWD/experiments/run1-2b.json}"
MIX=third_party/kev/evals/krino-run1

case "${1:-run}" in
  run)
    [ -f "$MIX/train.jsonl" ] || { echo "no data: run scripts/build_run1.sh first" >&2; exit 1; }
    [ -f "$MIX/anchors.json" ] || { echo "no anchors: run scripts/run1_reads.sh first" >&2; exit 1; }
    [ -f "$MIX/overlap.json" ] || { echo "mix not screened against JevBench: run scripts/build_mix.sh (it writes $MIX/overlap.json)" >&2; exit 1; }
    python3 -c "import json,sys; r=json.load(open('$MIX/overlap.json')); sys.exit(1 if r['offending_records'] else 0)" \
      || { echo "the screen found offending records; fix the mix before training" >&2; exit 1; }
    # trials run on the *deployed* app, whose copy of evals/ is captured at deploy time: redeploy so it ships the mix as it is now
    ( cd third_party/kev && uv run --no-sync modal deploy modal_app.py )
    ( cd third_party/kev && uv run --no-sync modal run modal_app.py::study \
        --suite evals/v7/decision-v7 --plan "$PLAN" \
        --name "$STUDY" --transfer evals/v4/transfer-v4 --budget "${BUDGET:-70}" --timeout "${TIMEOUT:-21600}" )
    ;;
  pull)
    ( cd third_party/kev && uv run --no-sync modal run modal_app.py::pull --name "$STUDY" )
    echo "results: third_party/kev/runs/$STUDY — now score both trials on the panel:"
    echo "  scripts/eval_dev.sh /runs/$STUDY/00-trial-0/checkpoint r1-s0"
    echo "  scripts/eval_dev.sh /runs/$STUDY/01-trial-1/checkpoint r1-s1"
    ;;
  *) echo "usage: train_stage2.sh [run|pull]" >&2; exit 1 ;;
esac
