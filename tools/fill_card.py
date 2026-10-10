#!/usr/bin/env python3
"""Fill the locked-test numbers into docs/model-card.md from the reads scripts/release_test_read.sh made.

    python3 tools/fill_card.py krino-v0.1.0            # reads third_party/kev/runs/locked/krino-v0.1.0/summary.json
                                                       #   and third_party/kev/runs/krino-v0.1.0-<breadth suite>/report.json
Prints the table, writes it to runs/locked-<name>.md, and replaces the {{...}} placeholders in the card. Idempotent on
a filled card (nothing left to replace). Stdlib only.
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BREADTH = [("belebele", "Belebele (reading comprehension, 122 languages)"), ("sib200", "SIB-200 (topic, 200 languages)"),
           ("rtp_lx", "RTP-LX (toxicity across languages)"), ("polyguard", "PolyGuard (safety across languages)"),
           ("goemotions", "GoEmotions (28 emotions)"), ("ledgar", "LEDGAR (contract clauses)"), ("kold", "KOLD (Korean offensive language)"),
           ("laya_apps", "Laya apps (typed decisions)"), ("multi_eurlex", "MultiEURLEX (EU law topics)")]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "krino-v0.1.0"
    locked = ROOT / "third_party/kev/runs/locked" / name / "summary.json"
    if not locked.exists():
        alt = ROOT / "third_party/kev/runs/locked" / (name + "-ungated") / "summary.json"
        if alt.exists(): locked, name = alt, name + "-ungated"
        else: raise SystemExit(f"no locked read at {locked}: run scripts/release_test_read.sh")
    summary = json.loads(locked.read_text())
    suites = summary["suites"]
    vals = {}
    for label, key in (("transfer", "transfer"), ("decision", "decision")):
        c = suites[label]["clean"]
        vals[f"{key}_test_n"] = f"{c['n']:,}"
        vals[f"{key}_test_acc"] = f"{c['acc']:.3f}"; vals[f"{key}_test_brier"] = f"{c['brier']:.3f}"; vals[f"{key}_test_ece"] = f"{c['ece']:.3f}"
    rows, accs = [], []
    for suite, desc in BREADTH:
        p = ROOT / "third_party/kev/runs" / f"{name}-{suite}" / "report.json"
        if not p.exists():
            p2 = ROOT / "third_party/kev/runs" / f"{name.removesuffix('-ungated')}-{suite}" / "report.json"
            if p2.exists(): p = p2
            else: print(f"warning: no test read for krino-breadth/{suite}"); continue
        c = json.loads(p.read_text())["clean"]; accs.append(c["acc"])
        rows.append(f"| krino-breadth/{suite} test — {desc} | {c['n']:,} | {c['acc']:.3f} | {c['brier']:.3f} | {c['ece']:.3f} |")
    if accs: rows.append(f"| **krino-breadth test, mean of {len(accs)}** | | **{sum(accs) / len(accs):.3f}** | | |")
    vals["breadth_test_rows"] = "\n".join(rows)
    table = ("| suite | questions | accuracy | Brier | ECE |\n|---|---:|---:|---:|---:|\n"
             f"| transfer-v4 test | {vals['transfer_test_n']} | {vals['transfer_test_acc']} | {vals['transfer_test_brier']} | {vals['transfer_test_ece']} |\n"
             f"| decision-v7 test | {vals['decision_test_n']} | {vals['decision_test_acc']} | {vals['decision_test_brier']} | {vals['decision_test_ece']} |\n"
             + vals["breadth_test_rows"] + "\n")
    print(table)
    out = ROOT / "runs" / f"locked-{name}.md"; out.parent.mkdir(exist_ok=True); out.write_text(table)
    card = ROOT / "docs/model-card.md"; s = card.read_text()
    missing = sorted(set(re.findall(r"\{\{(\w+)\}\}", s)) - set(vals))
    if missing: raise SystemExit(f"card placeholders without a value: {missing}")
    n = 0
    for k, v in vals.items():
        s, c = re.subn(r"\{\{" + k + r"\}\}", v, s); n += c
    card.write_text(s)
    print(f"filled {n} placeholders in {card.relative_to(ROOT)}; table also in {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
