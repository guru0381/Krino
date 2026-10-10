#!/usr/bin/env bash
# The locked test partitions, read ONCE for the release candidate (docs/EVAL.md: the test is read once per released model,
# after the candidate is chosen on development): transfer-v4 test and decision-v7 test through Kev's locked_test, which
# refuses a second read of the same name on the volume. About $1 of H100 time.
# The nine krino-breadth suites have no test partition (Malkuth's suites are development-only: their manifests list
# test.jsonl with 0 records), so the breadth numbers stay development reads.
#
#   scripts/release_test_read.sh                 # candidate krino-stage2-2b-s1/00-trial-0, read name krino-v0.1.0
#   then: python3 tools/fill_card.py krino-v0.1.0    (writes the numbers into docs/model-card.md)
set -euo pipefail
export KEV_HF_SECRET="${KEV_HF_SECRET:-huggingface-secret}"
cd "$(dirname "$0")/.."
TRIAL="${TRIAL:-krino-stage2-2b-s1/00-trial-0}"
NAME="${NAME:-krino-v0.1.0}"

if [ -f "third_party/kev/runs/locked/$NAME/summary.json" ] || [ -f "third_party/kev/runs/locked/$NAME-ungated/summary.json" ]; then
  echo "transfer-v4 / decision-v7 test already read for $NAME (third_party/kev/runs/locked/); not reading again"
else
  # Kev's locked_test insists the trial passed Kev's own in-trial gates (result.json), or that the read is named
  # '<name>-ungated'. Our gate is docs/EVAL.md's rule on the development panel. Try the plain name; fall back.
  if ! ( cd third_party/kev && uv run --no-sync modal run modal_app.py::locked_test --trial "$TRIAL" --name "$NAME" \
           --decision evals/v7/decision-v7 --transfer evals/v4/transfer-v4 ); then
    echo "locked_test refused the plain name (see above); reading as $NAME-ungated"
    NAME="$NAME-ungated"
    ( cd third_party/kev && uv run --no-sync modal run modal_app.py::locked_test --trial "$TRIAL" --name "$NAME" \
        --decision evals/v7/decision-v7 --transfer evals/v4/transfer-v4 )
  fi
fi
python3 tools/fill_card.py "${NAME%-ungated}"
