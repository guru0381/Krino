#!/usr/bin/env python3
"""Run 0 of the research plan: what the served temperature costs under JevBench's typed scoring rules, from saved rows.

JevBench v1.5 (the last published method; docs/METHOD-v1.5.md in the harness) scores the three request types differently:
  choice  CC = 100 * (acc - mean 1/K) / (1 - mean 1/K)           argmax, so the temperature cannot change it
  noul    P(yes) <= 0.20 is No, >= 0.80 is Yes, anything between is an ABSTENTION COUNTED WRONG; CC = 100 * (acc - 0.5) / 0.5
  score   the prediction is the EXPECTED LEVEL of the returned distribution; CC = 100 * (1 - mean nMAE / mean nMAE_chance)
A soft global temperature (ours: 1.95, fitted for choice ECE on the breadth pool) pushes noul probabilities into the band and
score expectations toward the middle of the scale, so it can tax two of the three equal-weighted thirds of Intelligence.
This script re-scores a checkpoint's saved rows (kev.benchmark rows.json, raw logits at T = 1) at a grid of temperatures,
per type, and prints typed competence and ECE so the served map can be chosen per type: choice at the ECE-optimal T,
noul and score at the T that maximises their competence on held-out development rows.

    python3 tools/typed_competence.py s2-s1                      # the suites of the panel for candidate s2-s1
    python3 tools/typed_competence.py s2-s1 --suites hard-v1,documents-v1,devtools-v1 --grid 1.0,1.3,1.6,1.95

Reads only our own development rows (never JevBench items). Stdlib only; no torch.
"""
import argparse, json, math, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = ["hard-v1", "documents-v1", "devtools-v1", "transfer-v4", "decision-v7",
         "belebele", "sib200", "rtp_lx", "polyguard", "goemotions", "ledgar", "kold", "laya_apps", "multi_eurlex"]


def softmax(z, T):
    m = max(z); e = [math.exp((v - m) / T) for v in z]; s = sum(e)
    return [v / s for v in e]


def raw_logits(row):
    """T = 1 logits of a saved row: recorded logits * recorded temperature, else log of the raw probabilities."""
    t = row.get("inference_temperature") or 1.0
    if "logits" in row and row["logits"] is not None:
        return [v * t for v in row["logits"]]
    return [math.log(max(p, 1e-12)) * t for p in row["p"]]


def ece(pairs, bins=10):
    """Top-label ECE over (confidence, correct) pairs, 10 equal-width bins (the harness's definition)."""
    if not pairs: return None
    tot = len(pairs); out = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        inb = [(c, ok) for c, ok in pairs if (lo < c <= hi) or (b == 0 and c == 0)]
        if inb: out += len(inb) / tot * abs(sum(ok for _, ok in inb) / len(inb) - sum(c for c, _ in inb) / len(inb))
    return out


def typed(rows, T):
    """v1.5 typed competence and ECE of clean rows served at T, by type."""
    acc = defaultdict(list); chance = defaultdict(list); pairs = defaultdict(list); band = 0; nmae = []; nmae_chance = []
    for r in rows:
        if r.get("variant", "clean") != "clean" or r.get("source") == "unknowable": continue
        p = softmax(raw_logits(r), T); y = int(r["label"]); K = len(p); t = r["type"]
        top = max(range(K), key=p.__getitem__)
        if t == "choice":
            acc[t].append(top == y); chance[t].append(1 / K); pairs[t].append((p[top], top == y))
        elif t == "noul":
            py = p[r["keys"].index("true")]
            pred = 1 if py >= 0.80 else 0 if py <= 0.20 else None
            if pred is None: band += 1
            acc[t].append(pred == y); pairs[t].append((max(py, 1 - py), top == y))
        else:   # score: expected level
            e = sum(i * pi for i, pi in enumerate(p))
            nmae.append(abs(e - y) / max(K - 1, 1)); nmae_chance.append(sum(abs(l - y) for l in range(K)) / K / max(K - 1, 1))
            acc[t].append(top == y); pairs[t].append((p[top], top == y))
    out = {}
    if acc["choice"]:
        a = sum(acc["choice"]) / len(acc["choice"]); c = sum(chance["choice"]) / len(chance["choice"])
        out["choice"] = {"n": len(acc["choice"]), "acc": a, "cc": 100 * (a - c) / (1 - c), "ece": ece(pairs["choice"])}
    if acc["noul"]:
        a = sum(acc["noul"]) / len(acc["noul"])
        out["noul"] = {"n": len(acc["noul"]), "acc": a, "cc": 100 * (a - 0.5) / 0.5, "ece": ece(pairs["noul"]), "in_band": band / len(acc["noul"]),
                       "argmax_acc": sum(ok for _, ok in pairs["noul"]) / len(pairs["noul"])}
    if nmae:
        a = sum(acc["score"]) / len(acc["score"])
        out["score"] = {"n": len(nmae), "acc": a, "cc": 100 * (1 - (sum(nmae) / len(nmae)) / (sum(nmae_chance) / len(nmae_chance))), "ece": ece(pairs["score"]),
                        "nmae": sum(nmae) / len(nmae)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name", help="candidate name used by scripts/eval_dev.sh, e.g. s2-s1 (rows in third_party/kev/runs/krino-<name>-<suite>/rows.json)")
    ap.add_argument("--suites", default=",".join(PANEL))
    ap.add_argument("--grid", default="0.3,0.5,0.7,0.85,1.0,1.2,1.4,1.6,1.95")
    ap.add_argument("--map", default="", help='the served map to record, e.g. "choice=1.95,noul=0.3,score=0.5"')
    ap.add_argument("--write", default="", help="write krino.json (the map plus its development-panel metrics) to this path, e.g. <checkpoint>/krino.json")
    a = ap.parse_args()
    grid = [float(x) for x in a.grid.split(",")]
    pooled = defaultdict(list)
    for s in a.suites.split(","):
        p = ROOT / "third_party/kev/runs" / f"krino-{a.name}-{s}" / "rows.json"
        if not p.exists(): print(f"{s}: no rows at {p}"); continue
        rows = json.load(p.open())
        tag = "DEV-PANEL" if s in ("hard-v1", "documents-v1", "devtools-v1", "transfer-v4") else "guard" if s == "decision-v7" else "breadth"
        for r in rows: pooled[tag].append(r)
        print(f"\n== {s}  ({len(rows)} rows)")
        print(f"{'T':>5s} | {'choice n':>8s} {'cc':>6s} {'ece':>6s} | {'noul n':>6s} {'cc':>6s} {'in-band':>7s} {'argmax':>6s} {'ece':>6s} | {'score n':>7s} {'cc':>6s} {'nmae':>6s} {'ece':>6s}")
        for T in grid:
            m = typed(rows, T); c, n, sc = m.get("choice"), m.get("noul"), m.get("score")
            f = lambda d, k, w=6, dd=3: f"{d[k]:{w}.{dd}f}" if d and d.get(k) is not None else " " * w
            print(f"{T:5.2f} | {c['n'] if c else '':>8} {f(c,'cc',6,1)} {f(c,'ece')} | {n['n'] if n else '':>6} {f(n,'cc',6,1)} {f(n,'in_band',7)} {f(n,'argmax_acc')} {f(n,'ece')} | "
                  f"{sc['n'] if sc else '':>7} {f(sc,'cc',6,1)} {f(sc,'nmae')} {f(sc,'ece')}")
    print("\n== pooled, per temperature (what a served map would do to each third of Intelligence)")
    for tag, rows in pooled.items():
        print(f"-- {tag} ({len(rows)} rows)")
        best = {}
        for T in grid:
            m = typed(rows, T)
            for t, d in m.items():
                key = ("ece" if t == "choice" else "cc")
                val = -d["ece"] if t == "choice" else d["cc"]
                if t not in best or val > best[t][0]: best[t] = (val, T, d)
            line = "  ".join(f"{t}: cc {d['cc']:5.1f} ece {d['ece']:.3f}" + (f" in-band {d['in_band']:.2f} argmax {d['argmax_acc']:.3f}" if t == "noul" else "") for t, d in m.items())
            print(f"  T {T:4.2f}  {line}")
        print("  best per type: " + "; ".join(f"{t} T={T} ({'min ECE' if t == 'choice' else 'max CC'})" for t, (_, T, _) in best.items()))
        if a.map and tag == "DEV-PANEL":
            chosen = {k: float(v) for k, v in (kv.split("=") for kv in a.map.split(","))}
            metrics = {t: typed(rows, T).get(t) for t, T in chosen.items()}
            print("  chosen map on the DEV-PANEL rows: " + "; ".join(f"{t} T={T}: cc {m['cc']:.1f} ece {m['ece']:.3f}" for t, T in chosen.items() if (m := metrics[t])))
            if a.write:
                Path(a.write).write_text(json.dumps({"temperatures": chosen, "candidate": a.name, "fitted_on": "development partitions of " + a.suites,
                    "rule": "choice: min ECE; noul and score: max typed competence under JevBench METHOD-v1.5 (noul abstention band 0.20-0.80; score expected level)",
                    "dev_panel_metrics": {t: {k: v for k, v in m.items()} for t, m in metrics.items() if m}}, indent=2) + "\n")
                print(f"  wrote {a.write}")
        if "noul" in best:
            m1, m2 = typed(rows, 1.95), typed(rows, best["noul"][1])
            print(f"  equal-thirds Intelligence proxy on these rows: served map (choice 1.95 / noul 1.95 / score 1.95) = "
                  f"{(m1['choice']['cc'] + m1['noul']['cc'] + m1.get('score', m1['noul'])['cc']) / 3:5.1f}   "
                  f"per-type map (choice 1.95 / noul {best['noul'][1]} / score {best.get('score', best['noul'])[1]}) = "
                  f"{(m1['choice']['cc'] + m2['noul']['cc'] + typed(rows, best.get('score', best['noul'])[1]).get('score', m2['noul'])['cc']) / 3:5.1f}")


if __name__ == "__main__":
    main()
