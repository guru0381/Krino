#!/usr/bin/env bash
# Score a checkpoint on the frozen development panel (docs/EVAL.md): one H100 read per suite on Modal, results pulled to
# third_party/kev/runs/krino-<NAME>-<suite>/, then one table.
#
#   scripts/eval_dev.sh /runs/krino-stage1-2b/00-trial-0/checkpoint s1-s0   # a trial on the Modal runs volume
#   scripts/eval_dev.sh Guru0381/krino-2b@stage1-s0 s1-s0                   # or a Hub checkpoint
#   scripts/eval_dev.sh table s1-s0                                          # re-print the table from pulled results
#   SUITES="hard-v1" scripts/eval_dev.sh RUN NAME                            # a subset
set -euo pipefail
export KEV_HF_SECRET="${KEV_HF_SECRET:-huggingface-secret}"   # the Modal secret with HF_TOKEN, so reads are not anonymous
cd "$(dirname "$0")/.."
RUN="${1:?usage: eval_dev.sh RUN NAME | table NAME}"
NAME="${2:?usage: eval_dev.sh RUN NAME}"
BREADTH="krino-breadth/belebele krino-breadth/sib200 krino-breadth/rtp_lx krino-breadth/polyguard krino-breadth/goemotions krino-breadth/ledgar krino-breadth/kold krino-breadth/laya_apps krino-breadth/multi_eurlex"
# added 2026-10-09 (EVAL.md allows adding suites): held-out multi-hop (HotpotQA, never trained) and answer adequacy (HelpSteer2
# validation; strands' generated adequacy eval); multistep = ContractNLI/MuSiQue/BoardgameQA dev, in-distribution from Run 1 on
NEW="krino-multihop/hotpotqa krino-multihop/multistep krino-judge/helpsteer2 krino-judge/adequacy-gen"
for s in $NEW; do [ -d "third_party/kev/evals/$s" ] || NEW=""; done   # only once scripts/build_run1.sh has made them
SUITES="${SUITES:-v7/decision-v7 v4/transfer-v4 hard-v1 documents-v1 devtools-v1 $BREADTH $NEW}"
if [ "$RUN" != "table" ]; then
  [ -d third_party/kev/evals/krino-breadth ] || scripts/import_breadth.sh
  JOBS=""
  for s in $SUITES; do tag=$(basename "$s"); JOBS="${JOBS:+$JOBS,}${RUN}@evals/${s}@krino-${NAME}-${tag}"; done
  ( cd third_party/kev && uv run --no-sync modal run modal_app.py::benchmarks --jobs "$JOBS" )
fi
python3 - "$NAME" "$SUITES" <<'PY'
import json, sys, pathlib
name, suites = sys.argv[1], sys.argv[2].split()
def num(x, w, d=3):
    return f"{x:{w}.{d}f}" if isinstance(x, (int, float)) and x == x else f"{'-':>{w}s}"
print(f"{'suite':16s} {'n':>5s} {'acc':>6s} {'brier':>6s} {'ece':>6s} {'cov@.9':>6s} {'flip%':>6s}  T")
breadth = []
for s in suites:
    tag = pathlib.Path(s).name
    p = pathlib.Path(f"third_party/kev/runs/krino-{name}-{tag}/report.json")
    if not p.exists(): print(f"{tag:16s} (missing)"); continue
    r = json.load(p.open()); c = r["clean"]; perm = r.get("permutation") or {}
    flip = perm.get("flip_rate"); flip = 100 * flip if isinstance(flip, (int, float)) else None
    label = ("breadth/" + tag) if s.startswith("krino-breadth/") else ("multihop/" + tag) if s.startswith("krino-multihop/") else ("judge/" + tag) if s.startswith("krino-judge/") else tag
    if s.startswith("krino-breadth/"): breadth.append(c["acc"])
    print(f"{label:16s} {c['n']:5d} {num(c['acc'],6)} {num(c['brier'],6)} {num(c['ece'],6)} {num(c.get('coverage_at_0_9'),6)} {num(flip,6,1)}  {r.get('temperature')}")
if breadth: print(f"{'breadth mean':16s} {len(breadth):5d} {sum(breadth)/len(breadth):6.3f}   (mean accuracy over the {len(breadth)} held-out suites)")
PY
