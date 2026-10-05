#!/usr/bin/env bash
# Push a trial's checkpoint to the private Hub repo on its own branch, so Modal can serve it for a report-only
# JevBench run (and so the release path is exercised early).
#
#   scripts/publish_candidate.sh third_party/kev/runs/krino-stage1-2b/00-trial-0 stage1-s0
#   -> Guru0381/krino-2b@stage1-s0  (serve it with: scripts/smoke_cloud.sh Guru0381/krino-2b@stage1-s0 stage1-s0)
set -euo pipefail
cd "$(dirname "$0")/.."
TRIAL="${1:?usage: publish_candidate.sh TRIAL_DIR REVISION}"
REV="${2:?usage: publish_candidate.sh TRIAL_DIR REVISION}"
REPO="${HF_REPO:-Guru0381/krino-2b}"
CK="$TRIAL/checkpoint"; [ -f "$CK/head.pt" ] || CK="$TRIAL"
[ -f "$CK/head.pt" ] || { echo "no head.pt under $TRIAL" >&2; exit 1; }
( cd third_party/kev && uv run --no-sync python -m kev.publish --run "$PWD/../../$CK" --repo "$REPO" \
    --card "$PWD/../../docs/model-card.md" --private --revision "$REV" --message "candidate $REV from $TRIAL" )
echo "published: $REPO@$REV"
