#!/usr/bin/env bash
# Release Krino-2B to the Hub and tag the repository.
#
#   scripts/release.sh publish [v0.1.0]   # the release checkpoint -> Guru0381/krino-2b@main (card: docs/model-card.md,
#                                         #   krino.json beside it), the Hub tag v0.1.0 on that commit, the git tag v0.1.0 here
#   scripts/release.sh public             # make the Hub repo public (type the repo id to confirm)
#   scripts/release.sh status             # what the Hub holds (files on main, tags, private or not)
#
# Order: scripts/release_test_read.sh (fills the card) -> publish -> make the GitHub repo public and push the tag ->
# public -> scripts/release_verify.sh (anonymous install + serve + a dev read) -> the JevBench request (docs/jevbench-request.md).
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN="${HF_TOKEN:-$(cat ~/.cache/huggingface/token 2>/dev/null || true)}"
REPO="${HF_REPO:-Guru0381/krino-2b}"
TRIAL="${TRIAL:-third_party/kev/runs/krino-stage2-2b-s1/00-trial-0}"
CK="$TRIAL/checkpoint"
VER="${2:-v0.1.0}"

case "${1:-}" in
  publish)
    [ -f "$CK/head.pt" ] || { echo "no checkpoint at $CK (scripts/train_stage2.sh pull)" >&2; exit 1; }
    [ -f "$CK/krino.json" ] || { echo "no krino.json beside the checkpoint: tools/typed_competence.py s2-s1 --map ... --write $CK/krino.json" >&2; exit 1; }
    if grep -q '{{' docs/model-card.md; then echo "docs/model-card.md still has {{...}} placeholders: scripts/release_test_read.sh, then tools/fill_card.py" >&2; exit 1; fi
    git diff --quiet -- docs/model-card.md || { echo "commit docs/model-card.md first (the card on the Hub should match a commit)" >&2; exit 1; }
    # kev.publish uploads the adapter, head, tokenizer files, the trial's result/provenance/training_config and the card as
    # README.md. --replace: main holds exactly this upload (the earlier candidate card and anything stale is removed).
    ( cd third_party/kev && uv run --no-sync python -m kev.publish --run "$PWD/../../$CK" --repo "$REPO" \
        --card "$PWD/../../docs/model-card.md" --replace \
        --message "Krino-2B $VER: stage-2 seed 1 (krino-stage2-2b-s1/00-trial-0) with per-type serving temperatures" )
    ( cd third_party/kev && uv run --no-sync python - "$PWD/../../$CK/krino.json" "$REPO" "$VER" <<'PY'
import sys
from huggingface_hub import HfApi
path, repo, ver = sys.argv[1:]
api = HfApi()
api.upload_file(path_or_fileobj=path, path_in_repo="krino.json", repo_id=repo, commit_message=f"krino.json: per-type serving temperatures ({ver})")
api.create_tag(repo, tag=ver, repo_type="model", tag_message=f"Krino-2B {ver}", exist_ok=False)
info = api.model_info(repo, revision=ver)
print(f"{repo}@{ver} = {info.sha}; files: {sorted(s.rfilename for s in info.siblings)}")
PY
    )
    git tag -a "$VER" -m "Krino-2B $VER" 2>/dev/null || echo "git tag $VER exists"
    echo "published $REPO@main and tagged $VER on the Hub."
    echo "now: make github.com/guru0381/Krino public (Settings -> General -> Danger Zone), then"
    echo "  git push --no-verify origin main --tags"
    echo "  scripts/release.sh public"
    ;;
  public)
    read -r -p "make $REPO public? type the repo id to confirm: " ANSWER
    [ "$ANSWER" = "$REPO" ] || { echo "not confirmed"; exit 1; }
    ( cd third_party/kev && uv run --no-sync python - "$REPO" <<'PY'
import sys
from huggingface_hub import HfApi
repo = sys.argv[1]; api = HfApi()
api.update_repo_settings(repo_id=repo, private=False)
print(f"{repo}: private = {api.model_info(repo).private}")
PY
    )
    ;;
  status)
    ( cd third_party/kev && uv run --no-sync python - "$REPO" <<'PY'
import sys
from huggingface_hub import HfApi
repo = sys.argv[1]; api = HfApi(); info = api.model_info(repo)
print(f"{repo}: private={info.private} sha={info.sha}")
print("files on main:", sorted(s.rfilename for s in info.siblings))
refs = api.list_repo_refs(repo); print("branches:", [b.name for b in refs.branches]); print("tags:", [t.name for t in refs.tags])
PY
    )
    ;;
  *) echo "usage: release.sh publish [VERSION] | public | status" >&2; exit 1 ;;
esac
