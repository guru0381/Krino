#!/usr/bin/env bash
# The two teacher reads Run 1 anchors to, on Modal:
#   parent   the incumbent's own distributions on the replay rows (kev.benchmark --split train; ~$1)  -> anchors.json
#   teacher  (only if scripts/build_run1.sh said the rebuilt multistep file differs from strands') the frozen
#            Qwen/Qwen3.5-4B-Base on the multi-step rows (kev.anchors; ~$2)
#
#   scripts/run1_reads.sh            # parent read + anchors.json (teacher from strands' committed file)
#   scripts/run1_reads.sh teacher    # also run the Modal teacher read and use it
set -euo pipefail
export KEV_HF_SECRET="${KEV_HF_SECRET:-huggingface-secret}"
cd "$(dirname "$0")/.."
INCUMBENT="${INCUMBENT:-/runs/krino-stage2-2b-s1/00-trial-0/checkpoint}"
TEACHER=""
if [ "${1:-}" = "teacher" ]; then
  ( cd third_party/kev && uv run --no-sync modal run --detach modal_app.py::anchors --base Qwen/Qwen3.5-4B-Base --suite evals/krino-run1-multistep --name krino-run1-teacher-4b )
  echo "the teacher read runs detached; when /runs/anchors/krino-run1-teacher-4b.json exists on the volume:"
  echo "  cd third_party/kev && uv run --no-sync modal volume get kev-runs anchors/krino-run1-teacher-4b.json runs/anchors/krino-run1-teacher-4b.json; cd ../.."
  echo "then re-run: scripts/run1_reads.sh use-teacher"
  exit 0
fi
[ "${1:-}" = "use-teacher" ] && TEACHER="--teacher-kev third_party/kev/runs/anchors/krino-run1-teacher-4b.json"
PARENT=third_party/kev/runs/krino-run1-parent
if [ ! -f "$PARENT/rows.json" ]; then
  # kev.benchmark writes rows.json before its summary; a read whose summary failed left the rows on the volume: pull, don't re-read
  ( cd third_party/kev && uv run --no-sync modal volume get kev-runs /bench/krino-run1-parent runs/ ) || true   # as Kev's pull_volume does
fi
if [ ! -f "$PARENT/rows.json" ]; then
  # a read that failed part-way leaves its output directory on the volume, and Kev refuses to overwrite one: clear it first
  ( cd third_party/kev && uv run --no-sync modal volume rm kev-runs /bench/krino-run1-parent -r 2>/dev/null || true )
  # 12,000 records, half of them the mix's long policy and document states: give the read 2 h, not the 30 min default
  ( cd third_party/kev && uv run --no-sync modal run modal_app.py::benchmarks --timeout 7200 --jobs "${INCUMBENT}@evals/krino-run1-replay@krino-run1-parent@--split train" )
fi
[ -f "$PARENT/rows.json" ] || { echo "no rows.json for the parent read (see the Modal log above)" >&2; exit 1; }
python3 tools/rows_to_anchors.py --parent third_party/kev/runs/krino-run1-parent/rows.json $TEACHER --out third_party/kev/evals/krino-run1/anchors.json
# the incumbent's baseline on the four new development suites (HotpotQA, multistep, HelpSteer2, adequacy-gen): Run 1's confirm reads compare to these
if [ ! -f third_party/kev/runs/krino-s2-s1-hotpotqa/report.json ]; then
  SUITES="krino-multihop/hotpotqa krino-multihop/multistep krino-judge/helpsteer2 krino-judge/adequacy-gen" scripts/eval_dev.sh "$INCUMBENT" s2-s1
fi
echo "ok: anchors written and the incumbent's baseline read on the new suites. Next: scripts/train_run1.sh"
