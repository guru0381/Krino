"""What an evaluator gets from the public release, checked on a fresh GPU container with no credentials:
pip install from the GitHub tag, the weights from the public Hub repo without a token, krino-serve on loopback, one request
by hand, GET /v1/krino, then Kev's benchmark over a development suite through the HTTP endpoint (the same adapter path
JevBench's harness uses). Nothing of ours is mounted except the suite being read.

    KRINO_VERSION=v0.1.0 uv run --no-sync --project third_party/kev modal run scripts/release_verify_modal.py
    KRINO_VERSION=v0.1.0 KRINO_SUITE=evals/hard-v1 KRINO_GPU=L40S ... modal run scripts/release_verify_modal.py
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[1]
VERSION = os.environ.get("KRINO_VERSION", "v0.1.0")
REPO_URL = os.environ.get("KRINO_REPO_URL", "https://github.com/guru0381/Krino.git")
MODEL = os.environ.get("KRINO_MODEL", f"Guru0381/krino-2b@{VERSION}")
SUITE = os.environ.get("KRINO_SUITE", "evals/hard-v1")        # a development suite: the public JevBench items are not read here
GPU = os.environ.get("KRINO_GPU", "L40S")
PORT = 8009

app = modal.App(f"krino-release-verify-{VERSION.replace('.', '-')}")
image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .uv_pip_install(f"krino @ git+{REPO_URL}@{VERSION}")                                  # exactly the card's install line
    .uv_pip_install("flash-linear-attention==0.5.2", "triton>=3.7.1")                       # the fused Qwen3.5 kernels (as the serving image)
    .env({"HF_HOME": "/tmp/hf-anon", "HF_HUB_DISABLE_PROGRESS_BARS": "1", "TOKENIZERS_PARALLELISM": "false", "PYTHONUNBUFFERED": "1",
          "KEV_TRUNCATE_STATES": "1"})
    .add_local_dir(str(ROOT / "third_party/kev" / SUITE), remote_path=f"/root/{SUITE}")
)

SAMPLE = {"model": "kev-latest",
          "state": "Shoes arrived two weeks late and in the wrong size. Also I see two charges on my card.",
          "questions": {"department": {"type": "choice", "instructions": "Which team should handle this?",
                                       "criteria": {"returns": "Exchanges, refunds", "shipping": "Delivery, delays", "billing": "Charges, payments"}},
                        "escalate": {"type": "noul", "instructions": "Does this need urgent human attention?"},
                        "frustration": {"type": "score", "instructions": "How frustrated is the customer?", "criteria": ["Calm", "Frustrated", "Very angry"]}}}


def get(url, data=None, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())


@app.function(image=image, gpu=GPU, cpu=4, memory=(16384, 65536), timeout=5400)
def verify(model: str, suite: str):
    assert not os.environ.get("HF_TOKEN"), "this check must run without a token"
    started = time.time()
    server = subprocess.Popen([sys.executable, "-m", "krino.serve", "--run", model, "--host", "127.0.0.1", "--port", str(PORT)],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    base = f"http://127.0.0.1:{PORT}"
    log = []
    while True:
        if server.poll() is not None:
            print("".join(log)); raise RuntimeError(f"krino-serve exited with {server.returncode}")
        try:
            models = get(f"{base}/v1/models", timeout=5); break
        except Exception:
            time.sleep(5)
            if time.time() - started > 1800: raise RuntimeError("server did not come up in 30 min")
    ready = time.time() - started
    card = get(f"{base}/v1/krino")
    t0 = time.perf_counter(); sample = get(f"{base}/v1/systemone", SAMPLE); first_ms = (time.perf_counter() - t0) * 1000
    lat = []
    for _ in range(20):
        t0 = time.perf_counter(); get(f"{base}/v1/systemone", SAMPLE); lat.append((time.perf_counter() - t0) * 1000)
    lat.sort()
    out = "/tmp/verify"
    bench = subprocess.run([sys.executable, "-m", "kev.benchmark", "--remote", base, "--suite", f"/root/{suite}", "--out", out],
                           capture_output=True, text=True, cwd="/root")
    if bench.returncode != 0:
        print(bench.stdout[-3000:], bench.stderr[-3000:]); raise RuntimeError("kev.benchmark failed against the served endpoint")
    report = json.loads(Path(out, "report.json").read_text())
    server.terminate()
    result = {"model": model, "version": VERSION, "gpu": GPU, "suite": suite, "ready_s": round(ready, 1),
              "served_models": models, "krino": card,
              "sample": {"answers": sample.get("answers"), "usage": sample.get("usage"), "first_request_ms": round(first_ms, 1)},
              "latency_ms_warm": {"p50": round(lat[len(lat) // 2], 1), "p95": round(lat[int(len(lat) * 0.95) - 1], 1)},
              "clean": {k: report["clean"][k] for k in ("n", "acc", "brier", "ece")},
              "benchmark_latency_ms": report.get("latency_ms"), "coverage": report.get("coverage"), "remote": report.get("remote")}
    print(json.dumps(result, indent=1))
    return result


@app.local_entrypoint()
def main():
    result = verify.remote(MODEL, SUITE)
    out = ROOT / "runs" / "release-verify"; out.mkdir(parents=True, exist_ok=True)
    (out / f"{VERSION}.json").write_text(json.dumps(result, indent=1) + "\n")
    c = result["clean"]
    print(f"\n{MODEL} via `pip install krino@{VERSION}` on {GPU}: ready in {result['ready_s']}s, temperatures {result['krino']['temperatures']}, "
          f"warm p50 {result['latency_ms_warm']['p50']} ms, {SUITE} dev acc {c['acc']:.3f} brier {c['brier']:.3f} ece {c['ece']:.3f} "
          f"(n {c['n']}); written to {out / (VERSION + '.json')}")
