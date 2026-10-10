#!/usr/bin/env python3
"""Run 1 anchors: {"targets": {record_id: {qid: {option_key: p}}}} for kev.train --anchor (KL toward these, per question).

Two teachers, one file:
  multi-step rows (contractnli / musique / boardgame)  the frozen Qwen3.5-4B's distributions — strands' committed
      third_party/strands/data/synthetic/teacher_multistep_v14.jsonl ({"i": row index, "probs": [...]}), used when our
      rebuilt data/run1/raw/multistep_v14.jsonl matches strands' checksum (data/SHA256SUMS), else a Kev anchors file
      (modal_app.py::anchors with Qwen/Qwen3.5-4B-Base on evals/krino-run1-multistep; --teacher-kev <json>)
  replay rows (replay_decision_v7 / replay_mix_v1)     the incumbent's own distributions, read raw (T = 1) by kev.benchmark
      --split train on evals/krino-run1-replay (--parent runs/krino-run1-parent/rows.json)

    python3 tools/rows_to_anchors.py --parent third_party/kev/runs/krino-run1-parent/rows.json \\
        --out third_party/kev/evals/krino-run1/anchors.json
"""
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEV = ROOT / "third_party" / "kev"
STRANDS = ROOT / "third_party" / "strands"
RAW = ROOT / "data" / "run1" / "raw"


def read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def strands_checksum(name):
    for line in (STRANDS / "data/SHA256SUMS").read_text().splitlines():
        h, _, f = line.partition("  ")
        if f.strip() == name: return h
    return None


def teacher_from_strands(targets):
    """strands' committed frozen-4B distributions, aligned to our multistep records by row index (ids task/<i>)."""
    ours = RAW / "multistep_v14.jsonl"
    want = strands_checksum("data/multistep_v14.jsonl")
    got = hashlib.sha256(ours.read_bytes()).hexdigest()
    if got != want:
        raise SystemExit(f"data/run1/raw/multistep_v14.jsonl ({got[:10]}) differs from strands' build ({want[:10]}): the committed "
                         f"teacher file cannot be aligned; run scripts/run1_reads.sh teacher and pass --teacher-kev")
    rows = read(ours); probs = {r["i"]: r["probs"] for r in read(STRANDS / "data/synthetic/teacher_multistep_v14.jsonl")}
    n = 0
    for i, row in enumerate(rows):
        p = probs.get(i)
        if p is None or len(p) != len(row["options"]): continue
        keys = [o[0] for o in row["options"]]
        if len(set(keys)) != len(keys): continue
        targets[f"{row['task']}/{i}"] = {"label": dict(zip(keys, p))}; n += 1
    return n


def teacher_from_kev(path, targets):
    t = json.loads(Path(path).read_text())["targets"]
    targets.update(t); return len(t)


def parent_from_rows(path, targets):
    n = 0
    for r in read(path) if path.endswith(".jsonl") else json.loads(Path(path).read_text()):
        if r.get("variant", "clean") != "clean": continue
        if r.get("inference_temperature") not in (None, 1.0):
            raise SystemExit("parent rows must be raw (T = 1): read the volume checkpoint, not a calibrated local copy")
        targets.setdefault(r["id"], {})[r["question"]] = dict(zip(r["keys"], r["p"])); n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent", required=True, help="kev.benchmark rows.json of the incumbent on evals/krino-run1-replay (train)")
    ap.add_argument("--teacher-kev", default="", help="a kev.anchors json for the multi-step rows (else strands' committed teacher file)")
    ap.add_argument("--out", default=str(KEV / "evals/krino-run1/anchors.json"))
    a = ap.parse_args()
    targets = {}
    nt = teacher_from_kev(a.teacher_kev, targets) if a.teacher_kev else teacher_from_strands(targets)
    np_ = parent_from_rows(a.parent, targets)
    train_ids = {json.loads(l)["_meta"]["id"] for l in open(KEV / "evals/krino-run1/train.jsonl", encoding="utf-8")}
    missing = [i for i in targets if i not in train_ids]
    covered = sum(1 for i in train_ids if i in targets)
    meta = {"teacher_multistep": "strands teacher_multistep_v14 (frozen Qwen3.5-4B)" if not a.teacher_kev else a.teacher_kev,
            "parent_replay": a.parent, "multistep_questions": nt, "replay_questions": np_, "records_anchored": len(targets),
            "train_records_covered": covered, "targets_not_in_train": len(missing)}
    Path(a.out).write_text(json.dumps({"_meta": meta, "targets": targets}))
    print(json.dumps(meta, indent=1)); print(f"wrote {a.out}")
    if missing: print(f"warning: {len(missing)} anchored ids are not in the training file (first: {missing[:3]})")


if __name__ == "__main__":
    main()
