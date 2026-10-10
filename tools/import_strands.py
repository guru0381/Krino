#!/usr/bin/env python3
"""Run 1 data: the judge + documents rows, in Kev's format, from strands-decider's builders and committed files.

Inputs (scripts/build_run1.sh produces the first two with strands' own builders, pinned in third_party/strands):
  data/run1/raw/multistep_v14.jsonl, multistep_v14_eval.jsonl     ContractNLI + MuSiQue + BoardgameQA (train), + HotpotQA (eval)
  data/run1/raw/adequacy_hs2.jsonl, adequacy_hs2_eval.jsonl       HelpSteer2 answer adequacy, balanced (CC BY 4.0)
  third_party/strands/data/synthetic/generated_v16.jsonl, generated_v18.jsonl, adequacy_gen.jsonl (+ *_eval.jsonl)
                                                                   verifier-filtered LLM-written documents and adequacy items
Outputs:
  third_party/kev/evals/krino-run1-new/train.jsonl                the new training rows (gold labels), one Kev suite dir
  third_party/kev/evals/krino-run1-multistep/train.jsonl          the multi-step rows alone (the frozen-4B teacher reads these: kev.anchors)
  third_party/kev/evals/krino-run1-replay/train.jsonl             6,000 decision-v7 train + 6,000 mix-v1 rows (the parent reads these)
  third_party/kev/evals/krino-judge/{helpsteer2,adequacy-gen}/development.jsonl, krino-multihop/{hotpotqa,multistep}/development.jsonl
                                                                   new development-panel suites (held out of training)
  third_party/kev/evals/krino-run1/train.jsonl                    new + replay rows: what Run 1 trains on (anchors come from scripts/run1_reads.sh)

strands row format: {"kind", "state", "instructions", "options": [[key, description], ...], "label": index, "task", ...}.
Kev record: {"state", "questions": {qid: {"type", "instructions", "criteria", "label", "src"}}, "_meta": {"source", "id", "group_id", "variant"}}
(group_id = id and variant = "clean" for an unperturbed record: kev.benchmark reads both).
"""
import argparse, hashlib, json, random, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEV = ROOT / "third_party" / "kev"
STRANDS = ROOT / "third_party" / "strands"
RAW = ROOT / "data" / "run1" / "raw"
R = random.Random(0)


def convert(row, source, i, qid="label"):
    """One strands Example -> one Kev record. Choice keys are the option keys; noul label a bool; score label the level index."""
    kind, opts = row["kind"], row["options"]
    q = {"type": kind, "instructions": row["instructions"], "src": f"{source}_{kind}"}
    if kind == "choice":
        keys = [o[0] for o in opts]
        if len(set(keys)) != len(keys) or len(keys) < 2: return None
        q["criteria"] = {o[0]: (o[1] or None) for o in opts}; q["label"] = keys[row["label"]]
    elif kind == "noul":
        q["label"] = bool(row["label"] == 1)
        if opts and any(o[1] for o in opts): q["criteria"] = {"false": opts[0][1] or None, "true": opts[1][1] or None}
    else:
        q["criteria"] = [o[1] or o[0] for o in opts]; q["label"] = int(row["label"])
    return {"state": row["state"], "questions": {qid: q}, "_meta": {"source": source, "id": f"{source}/{i}", "task": row.get("task")}}


def read(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records: f.write(json.dumps(r, ensure_ascii=True) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_suite(directory, parts, sources, eval_only, note):
    """A Kev suite directory: the partitions given plus a manifest Kev's loader and benchmark accept (sha256 + counts)."""
    directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for split in ("train", "calibration", "development", "test"):
        p = directory / f"{split}.jsonl"
        recs = parts.get(split, [])
        for r in recs:   # kev.benchmark's rows need the frozen-suite meta: group_id (bootstrap unit) and variant (clean / perturbed)
            r["_meta"].setdefault("group_id", r["_meta"]["id"]); r["_meta"].setdefault("variant", "clean")
        write(p, recs)
        files[p.name] = {"sha256": digest(p), "records": len(recs)}
    manifest = {"version": directory.name + "-v1", "partitions": [s for s, r in parts.items() if r], "files": files,
                "trainable_sources": [] if eval_only else sorted(sources), "eval_only_sources": sorted(sources) if eval_only else [],
                "holdout_sources": [], "eval_only": eval_only, "base_revisions": {}, "dataset_revisions": {},
                "context": {"max_state": 8192, "max_branch": 8192, "max_packed": 16384, "truncate": False},
                "sources": {s: n for s, n in Counter(r["_meta"]["source"] for rs in parts.values() for r in rs).items()},
                "note": note}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay-each", type=int, default=6000, help="decision-v7 train rows and mix-v1 rows replayed (each)")
    a = ap.parse_args()
    sys.path.insert(0, str(KEV))
    from kev.suite import load_split   # fetches/checks decision-v7 train

    # --- new training rows -------------------------------------------------------------------------------------------
    new, counts = [], Counter()
    def add(rows, source):
        n = 0
        for i, row in enumerate(rows):
            rec = convert(row, source, i)
            if rec: new.append(rec); n += 1
        counts[source] = n
    ms = read(RAW / "multistep_v14.jsonl")
    for j, row in enumerate(ms):   # ids carry the file's row index, so strands' committed teacher file (teacher_multistep_v14.jsonl, keyed "i") aligns
        rec = convert(row, row["task"], j)
        if rec: new.append(rec); counts[row["task"]] += 1
    multistep = [r for r in new]   # these get the frozen-4B teacher's distributions as anchors
    add(read(RAW / "adequacy_hs2.jsonl"), "helpsteer2")
    add(read(STRANDS / "data/synthetic/adequacy_gen.jsonl"), "strands_adequacy_gen")
    add(read(STRANDS / "data/synthetic/generated_v16.jsonl"), "strands_gen_v16")
    add(read(STRANDS / "data/synthetic/generated_v18.jsonl"), "strands_gen_v18")
    print("new rows:", dict(counts), "total", len(new))

    # --- replay rows: what the incumbent already knows, with its own distributions attached later (anchors) -----------
    dv7 = load_split(str(KEV / "evals/v7/decision-v7"), "train")
    replay_dv7 = R.sample(dv7, min(a.replay_each, len(dv7)))
    mix = read(KEV / "evals/krino-mix-v1/train.jsonl")
    replay_mix = R.sample(mix, min(a.replay_each, len(mix)))
    replay = []
    # a random sample splits the suites' contrastive pairs, and kev.benchmark's summary refuses an incomplete pair (after it
    # has written rows.json): the replay rows carry no pair bookkeeping, so the parent read completes. Training never reads it.
    PAIRS = ("pair_id", "sibling", "control_id")
    for r in replay_dv7:
        m = {**{k: v for k, v in r["_meta"].items() if k not in PAIRS}, "origin_source": r["_meta"]["source"], "source": "replay_decision_v7"}
        replay.append({"state": r["state"], "questions": r["questions"], "_meta": m})
    for r in replay_mix:
        m = {**{k: v for k, v in r["_meta"].items() if k not in PAIRS}, "origin_source": r["_meta"]["source"], "source": "replay_mix_v1"}
        replay.append({"state": r["state"], "questions": r["questions"], "_meta": m})
    ids = [r["_meta"]["id"] for r in new + replay]
    assert len(ids) == len(set(ids)), "record ids must be unique (anchors are keyed by id)"

    # --- suites ------------------------------------------------------------------------------------------------------
    srcs_new = sorted({r["_meta"]["source"] for r in new})
    make_suite(KEV / "evals/krino-run1-new", {"train": new}, srcs_new, False, "Run 1 new rows (gold labels)")
    make_suite(KEV / "evals/krino-run1-multistep", {"train": multistep}, ["contractnli", "musique", "boardgame"], False,
               "the multi-step rows alone, for the frozen Qwen3.5-4B teacher read (kev.anchors)")
    make_suite(KEV / "evals/krino-run1-replay", {"train": replay}, ["replay_decision_v7", "replay_mix_v1"], False,
               "replay rows for the parent's own distributions (kev.benchmark --split train on the incumbent)")
    ev = read(RAW / "multistep_v14_eval.jsonl")
    hotpot = [c for i, r in enumerate(x for x in ev if x["task"] == "hotpotqa") if (c := convert(r, "hotpotqa", i))]
    msdev = [c for i, r in enumerate(x for x in ev if x["task"] != "hotpotqa") if (c := convert(r, "multistep_" + r["task"], i))]
    hs2 = [c for i, r in enumerate(read(RAW / "adequacy_hs2_eval.jsonl")) if (c := convert(r, "helpsteer2", i))]
    agen = [c for i, r in enumerate(read(STRANDS / "data/synthetic/adequacy_gen_eval.jsonl")) if (c := convert(r, "strands_adequacy_gen", i))]
    make_suite(KEV / "evals/krino-multihop/hotpotqa", {"development": hotpot}, ["hotpotqa"], True, "HotpotQA comparison questions (CC BY-SA 4.0), never trained on: the multi-hop transfer test (strands v14)")
    make_suite(KEV / "evals/krino-multihop/multistep", {"development": msdev}, sorted({r["_meta"]["source"] for r in msdev}), True, "ContractNLI dev / MuSiQue dev / BoardgameQA valid: in-distribution for Run 1 (report, not selection)")
    make_suite(KEV / "evals/krino-judge/helpsteer2", {"development": hs2}, ["helpsteer2"], True, "HelpSteer2 validation, balanced: answer adequacy (strands v19's held-out read)")
    make_suite(KEV / "evals/krino-judge/adequacy-gen", {"development": agen}, ["strands_adequacy_gen"], True, "strands' generated adequacy items, eval split: categories never trained on")
    # what Run 1 trains on: new + replay (anchors.json is added by scripts/run1_reads.sh)
    allrows = new + replay; R.shuffle(allrows)
    m = make_suite(KEV / "evals/krino-run1", {"train": allrows}, sorted({r["_meta"]["source"] for r in allrows}), False,
                   "Run 1: judge + documents delta from the stage-2 incumbent; anchors: frozen Qwen3.5-4B on the multi-step rows, the incumbent on the replay rows")
    m["inputs"] = {"components": ["krino-run1-new-train", "krino-run1-replay-train", "decision-v7-train", "krino-mix-v1-train"]}
    (KEV / "evals/krino-run1/manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    qtypes = Counter(q["type"] for r in allrows for q in r["questions"].values())
    print(f"krino-run1: {len(allrows)} records ({len(new)} new + {len(replay)} replay), questions {dict(qtypes)}")
    print(f"dev suites: hotpotqa {len(hotpot)}, multistep {len(msdev)}, helpsteer2 {len(hs2)}, adequacy-gen {len(agen)}")


if __name__ == "__main__":
    main()
