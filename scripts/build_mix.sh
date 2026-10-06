#!/usr/bin/env bash
# Build the stage-2 training mix and screen it against the public JevBench items before anything trains on it.
#
#   scripts/build_mix.sh            # -> third_party/kev/evals/krino-mix-v1/{train.jsonl,manifest.json,overlap.json}
#   scripts/build_mix.sh --only arc,devtools-v1     # a small dry run of the builder (no screen)
#
# Needs: HF login (~/.cache/huggingface/token) so Kev's hard-v1 and documents-v1 training partitions can be fetched from
# the public kev-suites mirror; ~2 GB of dataset downloads the first time (cached under ~/.cache/huggingface).
# Writing under third_party/kev/evals/ is deliberate: Kev's Modal image ships evals/ (modal_app.py add_local_dir), and a
# trial's `data` must be a .jsonl under evals/. Nothing of Kev's own is edited.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN="${HF_TOKEN:-$(cat ~/.cache/huggingface/token 2>/dev/null || true)}"
MIX=third_party/kev/evals/krino-mix-v1

uv run --no-sync --project third_party/kev python tools/build_mix.py "$@"
[ $# -eq 0 ] || exit 0

echo; echo "== overlap screen against the public JevBench items (counts only; no item text is read or stored)"
( cd third_party/kev && uv run --no-sync python scripts/screen_overlap.py \
    --suite evals/krino-mix-v1 --external ../jevbench/datasets/public --out evals/krino-mix-v1/overlap.json )
echo; echo "== mix"
python3 - <<'PY'
import json, os
m = json.load(open("third_party/kev/evals/krino-mix-v1/manifest.json"))
print(f"{m['records']} records, {m['questions']} questions, {m['question_types']}, {os.path.getsize('third_party/kev/evals/krino-mix-v1/train.jsonl') / 1e6:.0f} MB")
for k, v in m["by_builder"].items(): print(f"  {k:18s} {v:6d}")
PY
echo "ok: mix built and screened. Next: scripts/train_stage2.sh"
