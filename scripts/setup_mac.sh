#!/usr/bin/env bash
# One-time setup on an Apple Silicon Mac: uv, Python 3.13, Kev with the MLX serving extra,
# the JevBench harness, and Kev's unit tests (no weights, no network beyond package installs).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  echo "This script is for Apple Silicon Macs. On Linux/CUDA use the cloud scripts." >&2; exit 1
fi

# 1. uv (Python + venv manager Kev uses). Homebrew is fine too: brew install uv
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "uv $(uv --version)"

# 2. upstream repos at their pins
scripts/bootstrap.sh

# 3. Kev: Python 3.13 venv, torch, transformers, peft, plus MLX for serving on the Mac
( cd third_party/kev && uv python install 3.13 && uv sync --extra serve )

# 4. JevBench harness is stdlib-only; it runs inside Kev's venv (scripts/run_jevbench.sh). Its own tests:
( cd third_party/jevbench && uv run --no-sync --project ../kev python -m pytest tests -q )

# 5. Kev's CI test set: no weights, no server
( cd third_party/kev && uv run --extra serve python -m pytest \
    tests/test_unit.py tests/test_conventions.py tests/test_generators.py -q )

echo
echo "ok: Mac setup complete. Next: scripts/smoke_mac.sh"
