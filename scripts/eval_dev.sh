#!/usr/bin/env bash
# Score a checkpoint on the frozen development panel (docs/EVAL.md): one H100 read per suite on Modal, results pulled to
# third_party/kev/runs/krino-<NAME>-<suite>/, then one table.
#
#   scripts/eval_dev.sh /runs/krino-stage1-2b/00-trial-0/checkpoint s1-s0   # a trial on the Modal runs volume
#   scripts/eval_dev.sh Guru0381/krino-2b@stage1-s0 s1-s0                   # or a Hub checkpoint
#   scripts/eval_dev.sh table s1-s0                                          # re-print the table from pulled results
set -euo pipefail
cd "$(dirname "$0")/.."
RUN="${1:?usage: eval_dev.sh RUN NAME | table NAME}"
NAME="${2:?usage: eval_dev.sh RUN NAME}"
SUITES="${SUITES:-v7/decision-v7 v4/transfer-v4 hard-v1 documents-v1 devtools-v1 breadth-v1}"
if [ "$RUN" != "table" ]; then
  JOBS=""
  for s in $SUITES; do tag=$(basename "$s"); JOBS="${JOBS:+$JOBS,}${RUN}@evals/${s}@krino-${NAME}-${tag}"; done
  ( cd third_party/kev && uv run --no-sync modal run modal_app.py::benchmarks --jobs "$JOBS" )
fi
python3 - "$NAME" "$SUITES" <<'PY'
import json, sys, pathlib
name, suites = sys.argv[1], sys.argv[2].split()
print(f"{'suite':14s} {'n':>5s} {'acc':>6s} {'brier':>6s} {'ece':>6s} {'cov@.9':>6s} {'flip%':>6s}  T")
for s in suites:
    tag = pathlib.Path(s).name
    p = pathlib.Path(f"third_party/kev/runs/krino-{name}-{tag}/report.json")
    if not p.exists(): print(f"{tag:14s} (missing)"); continue
    r = json.load(p.open()); c = r["clean"]; perm = r.get("permutation") or {}
    flip = 100 * perm["flip_rate"] if "flip_rate" in perm else float("nan")
    print(f"{tag:14s} {c['n']:5d} {c['acc']:6.3f} {c['brier']:6.3f} {c['ece']:6.3f} {c.get('coverage_at_0_9', float('nan')):6.3f} {flip:6.1f}  {r.get('temperature')}")
PY
