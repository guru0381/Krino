#!/usr/bin/env bash
# Step 6: one global temperature fitted on the krino-breadth development rows (held-out datasets, never trained on; docs/EVAL.md),
# written into the candidate's local head.pt. hard-v1 development rows are reported before/after and never fitted.
#   scripts/calibrate.sh s2-s0 krino-stage2-2b/00-trial-0      # after scripts/eval_dev.sh ... s2-s0
set -euo pipefail
cd "$(dirname "$0")/.."
NAME="${1:?usage: calibrate.sh NAME STUDY/TRIAL}"; TRIAL="${2:?usage: calibrate.sh NAME STUDY/TRIAL}"
ROWS=""
for s in belebele sib200 rtp_lx polyguard goemotions ledgar kold laya_apps multi_eurlex; do
  f="runs/krino-$NAME-$s/rows.json"
  [ -f "third_party/kev/$f" ] || { echo "missing third_party/kev/$f: run scripts/eval_dev.sh first" >&2; exit 1; }
  ROWS="$ROWS --rows $f"
done
[ -f "third_party/kev/runs/$TRIAL/checkpoint/head.pt" ] || { echo "no local checkpoint at third_party/kev/runs/$TRIAL/checkpoint (pull the study first)" >&2; exit 1; }
mkdir -p runs
( cd third_party/kev && uv run --no-sync python scripts/calibrate_checkpoint.py --run "runs/$TRIAL/checkpoint" $ROWS \
    --transfer "runs/krino-$NAME-hard-v1/rows.json" "${@:3}" ) 2>&1 | tee "runs/calibration-$NAME.txt"
echo "written into third_party/kev/runs/$TRIAL/checkpoint/head.pt; log: runs/calibration-$NAME.txt"
