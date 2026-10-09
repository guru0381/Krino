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
# kev.publish uploads a fixed file list; the per-type temperature map (krino.json, written by tools/typed_competence.py --write)
# rides along separately so krino.serve finds it in the repo
if [ -f "$CK/krino.json" ]; then
  ( cd third_party/kev && uv run --no-sync python - "$PWD/../../$CK/krino.json" "$REPO" "$REV" <<'PY'
import sys
from huggingface_hub import upload_file
path, repo, rev = sys.argv[1:]
upload_file(path_or_fileobj=path, path_in_repo="krino.json", repo_id=repo, revision=rev, commit_message=f"krino.json: per-type serving temperatures ({rev})")
print(f"uploaded krino.json to {repo}@{rev}")
PY
  )
else
  echo "note: no krino.json beside the checkpoint; the endpoint will serve raw (T = 1.0 for every type) unless KRINO_TEMPERATURES is set" >&2
fi
echo "published: $REPO@$REV"
