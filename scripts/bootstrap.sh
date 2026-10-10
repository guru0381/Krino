#!/usr/bin/env bash
# Fetch the upstream repos at the exact commits this project is built on.
# Safe to re-run: existing clones are reset to the pin, never updated past it.
set -euo pipefail
cd "$(dirname "$0")/.."

KEV_REPO=https://github.com/jaredpalmer/kev.git
KEV_COMMIT=fe64b1274ea7f80d4095866df90666abb03e9cf6
JB_REPO=https://github.com/fstandhartinger/jevbench.git
JB_COMMIT=bb05a335bc809e61b20c0f745d25499a82b326fc
MK_REPO=https://github.com/newfull5/malkuth.git
MK_COMMIT=af2e1c06ded5c448e78394f356319fc2e49f4c94
SD_REPO=https://github.com/strands-labs/strands-decider.git   # AWS Strands Decider (Hobson), Apache-2.0: data builders and committed verified data
SD_COMMIT=3e94e9d84c620ed5a95f1a3310c3decb971e261c

mkdir -p third_party
fetch() {  # name repo commit
  local dir="third_party/$1"
  if [ ! -d "$dir/.git" ]; then
    git clone --filter=blob:none "$2" "$dir"
  fi
  git -C "$dir" fetch -q origin "$3"
  git -C "$dir" checkout -q "$3"
  echo "$1 @ $(git -C "$dir" rev-parse --short HEAD) ($(git -C "$dir" log -1 --format=%cd --date=short))"
}
fetch kev "$KEV_REPO" "$KEV_COMMIT"
fetch jevbench "$JB_REPO" "$JB_COMMIT"
fetch malkuth "$MK_REPO" "$MK_COMMIT"
fetch strands "$SD_REPO" "$SD_COMMIT"
echo "ok: third_party/ is pinned"
