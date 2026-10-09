"""Per-question-type serving temperatures.

JevBench's typed scoring (METHOD-v1.5) treats the three request types differently: choice is scored by its argmax, so
only its calibration depends on the temperature; a noul answer with P(yes) strictly between 0.20 and 0.80 is an
abstention, counted wrong; a score answer is the expected level of the returned distribution. One global temperature
fitted for choice calibration (ours was 1.95) therefore pushes half the yes/no answers into the abstention band and the
rating expectations toward the middle of the scale. Krino serves each type at its own temperature, chosen on held-out
development rows with tools/typed_competence.py: choice at the ECE-optimal temperature, noul and score at the
temperature that maximises their typed competence. Argmax never changes.

The map travels with the checkpoint as `krino.json` ({"temperatures": {"choice": T, "noul": T, "score": T}, ...}),
beside head.pt locally or in the Hub repo; KRINO_TEMPERATURES="choice=1.95,noul=0.3,score=0.5" overrides it.
"""
import json
import math
import os
from pathlib import Path

TYPES = ("choice", "noul", "score")
DEFAULT = {"choice": 1.0, "noul": 1.0, "score": 1.0}   # raw, until a map is fitted
FILE = "krino.json"


def parse(spec: str) -> dict:
    out = {}
    for part in filter(None, (p.strip() for p in spec.split(","))):
        k, v = part.split("=")
        if k.strip() not in TYPES: raise ValueError(f"unknown question type {k!r} in KRINO_TEMPERATURES")
        t = float(v)
        if not (math.isfinite(t) and t > 0): raise ValueError("temperatures must be finite and positive")
        out[k.strip()] = t
    return out


def load(run: str, revision: str | None = None) -> dict:
    """The map for a checkpoint: KRINO_TEMPERATURES, else krino.json beside head.pt (local dir) or in the Hub repo, else raw."""
    if os.environ.get("KRINO_TEMPERATURES"):
        return {**DEFAULT, **parse(os.environ["KRINO_TEMPERATURES"])}
    local = Path(run) / FILE
    if local.exists():
        return {**DEFAULT, **json.loads(local.read_text(encoding="utf-8"))["temperatures"]}
    if "/" in run and not Path(run).exists():   # a Hub id, optionally id@revision
        repo, _, rev = run.partition("@")
        try:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(repo, FILE, revision=rev or revision or None)
            return {**DEFAULT, **json.loads(Path(path).read_text(encoding="utf-8"))["temperatures"]}
        except Exception:   # no krino.json in the repo: serve raw and say so
            return dict(DEFAULT)
    return dict(DEFAULT)


def temper(p: list[float], t: float) -> list[float]:
    """The distribution `p` (served at T = 1) re-served at temperature t: softmax(log p / t). Argmax is unchanged."""
    if t == 1.0: return list(p)
    z = [math.log(max(float(v), 1e-12)) / t for v in p]
    m = max(z); e = [math.exp(v - m) for v in z]; s = sum(e)
    return [v / s for v in e]


def apply(ps: list[list[float]], meta: list[dict], temperatures: dict) -> list[list[float]]:
    return [temper(p, temperatures.get(m["type"], 1.0)) for p, m in zip(ps, meta)]
