#!/usr/bin/env bash
# Run 1 data (docs/research: the judge + documents delta), built from licensed sources and strands-decider's committed files:
#   ContractNLI (CC BY 4.0), MuSiQue (CC BY 4.0), BoardgameQA (CC BY 4.0), HelpSteer2 (CC BY 4.0) through strands' own
#   builders (third_party/strands, Apache-2.0), plus strands' verifier-filtered generated documents and adequacy items.
#
#   scripts/build_run1.sh          # -> third_party/kev/evals/krino-run1/{train.jsonl,manifest.json,overlap.json} + the new dev suites
#   then: scripts/run1_reads.sh    # the parent's distributions on the replay rows (Modal, ~$1) -> anchors.json
#   then: scripts/train_run1.sh    # two seeds, ~$20
#
# Needs ~1.5 GB of downloads (data/run1/raw, gitignored) and the HF login for decision-v7's training partition.
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_TOKEN="${HF_TOKEN:-$(cat ~/.cache/huggingface/token 2>/dev/null || true)}"
[ -d third_party/strands/.git ] || scripts/bootstrap.sh
RAW=data/run1/raw; mkdir -p "$RAW/helpsteer2"

echo "== raw sources (strands' recipe.sh fetch; checksums from third_party/strands/data/SHA256SUMS)"
download() { [ -f "$1" ] || { curl -fsSL -o "$1.part" "$2" && mv "$1.part" "$1"; }; }
download "$RAW/contract-nli.zip" https://stanfordnlp.github.io/contract-nli/resources/contract-nli.zip
download "$RAW/musique_data_v1.0.zip" "https://drive.usercontent.google.com/download?id=1tGdADlNjWFaHLeZZGShh2IRcpO6Lv24h&export=download&confirm=t"
for f in train validation; do download "$RAW/helpsteer2/$f.jsonl.gz" "https://huggingface.co/datasets/nvidia/HelpSteer2/resolve/main/$f.jsonl.gz"; done
python3 - "$RAW" <<'PY'
import hashlib, sys, zipfile, pathlib
raw = pathlib.Path(sys.argv[1]); sums = {}
for line in pathlib.Path("third_party/strands/data/SHA256SUMS").read_text().splitlines():
    h, _, f = line.partition("  "); sums[f.strip().replace("data/raw/", "")] = h
for f in ("contract-nli.zip", "musique_data_v1.0.zip", "helpsteer2/train.jsonl.gz", "helpsteer2/validation.jsonl.gz"):
    got = hashlib.sha256((raw / f).read_bytes()).hexdigest()
    if got != sums[f]: raise SystemExit(f"{f}: sha256 {got[:12]} != strands' {sums[f][:12]} (delete data/run1/raw/{f} and re-run)")
    print(f"  {f}: ok")
z = zipfile.ZipFile(raw / "contract-nli.zip"); z.extractall(raw, [m for m in z.namelist() if m.endswith((".json", "LICENSE", "TERMS", "README.md"))])
z = zipfile.ZipFile(raw / "musique_data_v1.0.zip")
for m in ("data/musique_full_v1.0_train.jsonl", "data/musique_full_v1.0_dev.jsonl"): z.extract(m, raw / "musique")
print("  extracted ContractNLI and MuSiQue")
PY

echo "== strands' builders (multi-step documents; HelpSteer2 adequacy), inside Kev's environment"
export PYTHONPATH="$PWD/third_party/strands/src"
[ -f "$RAW/multistep_v14.jsonl" ] || uv run --no-sync --project third_party/kev python -m strands_decider.data.multistep \
    --raw "$RAW" --out "$RAW/multistep_v14.jsonl" --eval-out "$RAW/multistep_v14_eval.jsonl" --tokenizer Qwen/Qwen3.5-2B-Base --max-tokens 3000 --seed 0
[ -f "$RAW/adequacy_hs2.jsonl" ] || uv run --no-sync --project third_party/kev python -m strands_decider.data.adequacy \
    --raw "$RAW/helpsteer2" --out "$RAW/adequacy_hs2.jsonl" --eval-out "$RAW/adequacy_hs2_eval.jsonl" --tokenizer Qwen/Qwen3.5-2B-Base --max-tokens 3000 --seed 0
python3 - "$RAW" <<'PY'
import hashlib, sys, pathlib
raw = pathlib.Path(sys.argv[1]); want = {}
for line in pathlib.Path("third_party/strands/data/SHA256SUMS").read_text().splitlines():
    h, _, f = line.partition("  "); want[f.strip()] = h
for f in ("multistep_v14.jsonl", "multistep_v14_eval.jsonl"):
    got = hashlib.sha256((raw / f).read_bytes()).hexdigest()
    print(f"  {f}: {'matches strands'' build (teacher file aligns)' if got == want.get('data/' + f) else 'DIFFERS from strands'' build: teacher distributions need the Modal read (scripts/run1_reads.sh teacher)'}")
PY
unset PYTHONPATH

echo "== Kev-format rows, suites and the Run 1 training file"
uv run --no-sync --project third_party/kev python tools/import_strands.py

echo "== overlap screen against the public JevBench items"
( cd third_party/kev && uv run --no-sync python scripts/screen_overlap.py --suite evals/krino-run1 --external ../jevbench/datasets/public --out evals/krino-run1/overlap.json )
mkdir -p data/run1 && cp third_party/kev/evals/krino-run1/manifest.json third_party/kev/evals/krino-run1/overlap.json data/run1/
echo "ok: Run 1 data built and screened. Next: scripts/run1_reads.sh"
