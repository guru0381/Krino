#!/usr/bin/env python3
"""Write the locked-test numbers into docs/model-card.md from the read scripts/release_test_read.sh made.

    python3 tools/fill_card.py krino-v0.1.0        # reads third_party/kev/runs/locked/krino-v0.1.0[-ungated]/summary.json

Replaces the table between <!-- locked-test:start --> and <!-- locked-test:end --> and the metric values of the two
locked-test entries in the card's model-index, so it can be re-run. Writes the table to runs/locked-<name>.md too.
Stdlib only.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "krino-v0.1.0"
    locked = ROOT / "third_party/kev/runs/locked" / name / "summary.json"
    if not locked.exists():
        alt = ROOT / "third_party/kev/runs/locked" / (name + "-ungated") / "summary.json"
        if alt.exists(): locked, name = alt, name + "-ungated"
        else: raise SystemExit(f"no locked read at {locked}: run scripts/release_test_read.sh")
    suites = json.loads(locked.read_text())["suites"]
    t, d = suites["transfer"]["clean"], suites["decision"]["clean"]
    table = ("| suite | questions | accuracy | Brier | ECE |\n|---|---:|---:|---:|---:|\n"
             f"| transfer-v4 test (six never-trained public sources + held-out policy structures) | {t['n']:,} | **{t['acc']:.3f}** | {t['brier']:.3f} | {t['ece']:.3f} |\n"
             f"| decision-v7 test (Kev's trained sources) | {d['n']:,} | {d['acc']:.3f} | {d['brier']:.3f} | {d['ece']:.3f} |\n")
    print(table)
    out = ROOT / "runs" / f"locked-{name}.md"; out.parent.mkdir(exist_ok=True); out.write_text(table)
    card = ROOT / "docs/model-card.md"; s = card.read_text()
    s, n = re.subn(r"(<!-- locked-test:start -->\n).*?(<!-- locked-test:end -->)", lambda m: m.group(1) + table + m.group(2), s, flags=re.S)
    if n != 1: raise SystemExit("the card has no <!-- locked-test:start/end --> markers")
    # model-index: the first metrics block is transfer-v4 test, the second decision-v7 test
    def fill(block, m):
        block = re.sub(r"(type: accuracy, value: )[\d.]+", rf"\g<1>{m['acc']:.3f}", block)
        block = re.sub(r"(type: brier_score, value: )[\d.]+", rf"\g<1>{m['brier']:.3f}", block)
        return re.sub(r"(type: expected_calibration_error, value: )[\d.]+", rf"\g<1>{m['ece']:.3f}", block)
    head, sep, rest = s.partition("## Krino-2B\n")
    parts = head.split("      - task:")
    if len(parts) >= 3:
        parts[1] = fill(parts[1], t); parts[2] = fill(parts[2], d)
        head = "      - task:".join(parts)
    card.write_text(head + sep + rest)
    print(f"model card updated from {locked.relative_to(ROOT)}; table also in {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
