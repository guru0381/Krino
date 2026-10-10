#!/usr/bin/env python3
"""Per-task (family) accuracy of two candidates on the same development suites, from kev.benchmark's report.json.

    python3 tools/compare_tasks.py s2-s1 r1-s0                                    # the hard suites + the Run 1 suites
    python3 tools/compare_tasks.py s2-s1 r1-s0 --suites hard-v1,transfer-v4

Reads third_party/kev/runs/krino-<name>-<suite>/report.json (scripts/eval_dev.sh) and prints, per task, n, both accuracies,
the delta in points and the delta over its binomial standard error, so a flat suite total can be read family by family.
Development rows only; stdlib only.
"""
import argparse, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = "hard-v1,documents-v1,devtools-v1,transfer-v4,hotpotqa,multistep,helpsteer2,adequacy-gen"


def report(name, suite):
    p = ROOT / "third_party/kev/runs" / f"krino-{name}-{suite}" / "report.json"
    return json.load(p.open()) if p.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", help="baseline candidate name, e.g. s2-s1")
    ap.add_argument("b", help="candidate name, e.g. r1-s0")
    ap.add_argument("--suites", default=DEFAULT)
    ap.add_argument("--min-n", type=int, default=20)
    args = ap.parse_args()
    for suite in args.suites.split(","):
        ra, rb = report(args.a, suite), report(args.b, suite)
        if not ra or not rb:
            print(f"\n== {suite}: missing report for {'both' if not ra and not rb else args.a if not ra else args.b}"); continue
        ca, cb = ra["clean"], rb["clean"]
        print(f"\n== {suite}  n {ca['n']}  acc {ca['acc']:.3f} -> {cb['acc']:.3f} ({100 * (cb['acc'] - ca['acc']):+.1f} pp)   "
              f"ece {ca['ece']:.3f} -> {cb['ece']:.3f}   brier {ca['brier']:.3f} -> {cb['brier']:.3f}")
        print(f"   {'task':40s} {'n':>5s} {args.a:>8s} {args.b:>8s} {'delta':>7s} {'d/SE':>6s}")
        rows = []
        for task, ma in ra["tasks"].items():
            mb = rb["tasks"].get(task)
            if not mb or ma["n"] < args.min_n: continue
            d = mb["acc"] - ma["acc"]
            se = math.sqrt(max(ma["acc"] * (1 - ma["acc"]), 0.01) / ma["n"] + max(mb["acc"] * (1 - mb["acc"]), 0.01) / mb["n"])
            rows.append((task, ma["n"], ma["acc"], mb["acc"], d, d / se))
        for task, n, a, b, d, z in sorted(rows, key=lambda r: r[4]):
            flag = " <" if z <= -2 else " >" if z >= 2 else ""
            print(f"   {task:40s} {n:5d} {a:8.3f} {b:8.3f} {100 * d:+6.1f}  {z:6.1f}{flag}")


if __name__ == "__main__":
    main()
