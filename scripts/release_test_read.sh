#!/usr/bin/env bash
# The locked test partitions, read ONCE for the release candidate (docs/EVAL.md: the test is read once per released model,
# after the candidate is chosen on development). transfer-v4 + decision-v7 go through Kev's locked_test (it refuses a
# second read of the same name on the volume); the nine krino-breadth tests through kev.benchmark --allow-test (Kev refuses
# to overwrite a read's directory on the volume). About $2 of H100 time.
#
#   scripts/release_test_read.sh                 # candidate krino-stage2-2b-s1/00-trial-0, read name krino-v0.1.0
#   then: python3 tools/fill_card.py krino-v0.1.0    (fills the {{...}} in docs/model-card.md from these reads)
set -euo pipefail
export KEV_HF_SECRET="${KEV_HF_SECRET:-huggingface-secret}"
cd "$(dirname "$0")/.."
TRIAL="${TRIAL:-krino-stage2-2b-s1/00-trial-0}"
NAME="${NAME:-krino-v0.1.0}"
BREADTH="belebele sib200 rtp_lx polyguard goemotions ledgar kold laya_apps multi_eurlex"

if [ -f "third_party/kev/runs/locked/$NAME/summary.json" ]; then
  echo "transfer-v4 / decision-v7 test already read for $NAME (third_party/kev/runs/locked/$NAME); not reading again"
else
  # Kev's locked_test insists the trial passed its in-trial gates, or that the read is named '<name>-ungated' (an
  # exploratory read of a checkpoint without them). Try the plain name; fall back to the explicit one.
  if ! ( cd third_party/kev && uv run --no-sync modal run modal_app.py::locked_test --trial "$TRIAL" --name "$NAME" \
           --decision evals/v7/decision-v7 --transfer evals/v4/transfer-v4 ); then
    echo "locked_test refused the plain name (see above); reading as $NAME-ungated"
    NAME="$NAME-ungated"
    ( cd third_party/kev && uv run --no-sync modal run modal_app.py::locked_test --trial "$TRIAL" --name "$NAME" \
        --decision evals/v7/decision-v7 --transfer evals/v4/transfer-v4 )
  fi
fi

JOBS=""
for s in $BREADTH; do
  if [ ! -f "third_party/kev/evals/krino-breadth/$s/test.jsonl" ]; then echo "krino-breadth/$s: no test partition; skipped"; continue; fi
  if [ -f "third_party/kev/runs/$NAME-$s/report.json" ]; then echo "krino-breadth/$s: already read; skipped"; continue; fi
  JOBS="${JOBS:+$JOBS,}/runs/$TRIAL/checkpoint@evals/krino-breadth/$s@$NAME-$s@--allow-test"
done
if [ -n "$JOBS" ]; then
  ( cd third_party/kev && uv run --no-sync modal run modal_app.py::benchmarks --jobs "$JOBS" )
fi
python3 tools/fill_card.py "$NAME"
