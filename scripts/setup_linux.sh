#!/usr/bin/env bash
# One-time setup on a Linux dev box (GitHub Codespaces, Lightning AI Studio, a RunPod pod, any Ubuntu box):
# uv, Python 3.13, Kev (CPU torch is fine here; GPUs live on Modal), the JevBench harness, Malkuth, and the unit tests.
# Also works on a CUDA box: pass --gpu to install the serving extra and flash-linear-attention there.
set -euo pipefail
cd "$(dirname "$0")/.."
GPU=0; [ "${1:-}" = "--gpu" ] && GPU=1

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "uv $(uv --version)"

scripts/bootstrap.sh

( cd third_party/kev && uv python install 3.13 && \
  if [ "$GPU" = 1 ]; then uv sync --extra serve && uv pip install flash-linear-attention; else uv sync --extra serve; fi )

# the harness is stdlib-only and runs inside Kev's venv; its tests want pytest, which Kev's dev group provides
( cd third_party/jevbench && uv run --no-sync --project ../kev python -m pytest tests -q )
( cd third_party/kev && uv run --no-sync python -m pytest tests/test_unit.py tests/test_conventions.py tests/test_generators.py -q )

# Modal CLI comes with Kev's dev group; sign in once (opens a browser link you paste back)
if ! ( cd third_party/kev && uv run --no-sync modal profile current >/dev/null 2>&1 ); then
  echo
  echo "Next: sign in to Modal (free \$30/month of compute):"
  echo "   cd third_party/kev && uv run --no-sync modal setup"
fi
echo
echo "ok: Linux setup complete. Next: scripts/smoke_cloud.sh"
