#!/usr/bin/env bash
# Verify the public release the way an evaluator meets it: a fresh Modal container with no credentials installs the package
# from the GitHub tag, fetches the weights from the public Hub repo without a token, serves on loopback, answers one request,
# and runs Kev's benchmark over hard-v1's development partition through the HTTP endpoint. About $0.50 of L40S time.
# The result goes to runs/release-verify/<version>.json; hard-v1 dev accuracy must match the panel read (0.717 for v0.1.0:
# the per-type temperatures never change an argmax).
#
#   scripts/release_verify.sh            # v0.1.0
#   KRINO_VERSION=v0.1.1 scripts/release_verify.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export KRINO_VERSION="${KRINO_VERSION:-v0.1.0}"
unset HF_TOKEN
git ls-remote --tags --exit-code https://github.com/guru0381/Krino.git "refs/tags/$KRINO_VERSION" >/dev/null 2>&1 \
  || { echo "tag $KRINO_VERSION is not on github.com/guru0381/Krino (or the repository is still private): push it first" >&2; exit 1; }
( uv run --no-sync --project third_party/kev modal run scripts/release_verify_modal.py )
