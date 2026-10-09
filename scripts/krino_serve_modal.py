"""Krino's endpoint on Modal: Kev's serving stack (kev.serve) with Krino's per-type temperatures (krino.serve).
A fork of Kev's skills/kev-deploy/scripts/kev_serve.py (Apache-2.0); deploy from the repository root so the local `krino`
package is mounted into the image:

    KEV_MODEL=Guru0381/krino-2b@stage2-s1 KEV_APP_NAME=krino-stage2-s1 KEV_TRUNCATE_STATES=1 HF_TOKEN=... \
      uv run --no-sync --project third_party/kev modal deploy scripts/krino_serve_modal.py

Settings as in kev_serve.py (KEV_MODEL, KEV_GPU, KEV_API_KEY, HF_TOKEN, KEV_MIN_CONTAINERS, KEV_REGION, KEV_FLASH,
KEV_APP_NAME, KEV_TRUNCATE_STATES) plus KRINO_TEMPERATURES ("choice=1.95,noul=0.3,score=0.5"; default: the checkpoint's
krino.json, else raw). The checkpoint is loaded raw and every answer is re-served at its type's temperature.
"""
import os
import sys
import time
from pathlib import Path

import modal
import modal.experimental

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # the repository root, so add_local_python_source finds `krino`

KEV_REF = "fe64b1274ea7f80d4095866df90666abb03e9cf6"   # github.com/jaredpalmer/kev commit Krino is built on (scripts/bootstrap.sh)
# GPU preference lists (Modal takes the first with capacity), from runs/serve-*/, runs/fused-27b-*/ and runs/serving-*/report.json in the repo.
# An L4 is enough for the 0.8B but runs out of compute on the 4B; the L40S is the cheapest GPU that answers the 4B in tens
# of milliseconds, the H100 the fastest for the 4B and 9B. The A100 is slower than the L40S here and costs more. Kev-27B
# (55 GB of weights, ~66 GB resident with the batching buffers) is compute-bound under load: a B200 serves it fastest, at
# about the same cost per request as an H200 or H100; an RTX PRO 6000 is slower and costs more per request.
GPU_FOR = {"jaredpalmer/kev-0.8b": ["L4", "L40S"], "jaredpalmer/kev-4b": ["L40S", "H100"], "jaredpalmer/kev-9b": ["H100", "H200", "L40S"],
           "jaredpalmer/kev-27b": ["B200", "H200", "H100"]}

# Deploy-time settings travel in the image env, so the container evaluates this file with the same values.
SETTINGS = {"KEV_MODEL": "Guru0381/krino-2b", "KEV_APP_NAME": "krino", "KEV_MIN_CONTAINERS": "0", "KEV_GPU": "L4,L40S", "KEV_REGION": "", "KEV_FLASH": "0",
            "KEV_TRUNCATE_STATES": "1", "KRINO_TEMPERATURES": ""}   # read by kev.serve / krino.temperatures in the container
SETTINGS = {k: os.environ.get(k, v) for k, v in SETTINGS.items()}
MODEL = SETTINGS["KEV_MODEL"]
GPU = SETTINGS["KEV_GPU"].split(",") if SETTINGS["KEV_GPU"] else GPU_FOR.get(MODEL.split("@")[0])
if not GPU:
    raise SystemExit(f"no default GPU for {MODEL}; set KEV_GPU (e.g. KEV_GPU=H100)")
FLASH = SETTINGS["KEV_FLASH"] == "1"   # Modal's experimental direct HTTP server: ~2x the requests per container, half the round trip
if FLASH and not SETTINGS["KEV_REGION"]:
    raise SystemExit("KEV_FLASH=1 serves through a regional proxy: set KEV_REGION (e.g. us-east) too")
# Flash cannot wake a scaled-to-zero app quickly (its proxy answers 503 "no upstreams available" for minutes): keep one up
MIN_CONTAINERS = max(int(SETTINGS["KEV_MIN_CONTAINERS"]), 1 if FLASH else 0)
# Secret values never go into the image: they ride in a Modal secret (present in the container's env, so this stays equal there).
SECRET = {k: os.environ[k] for k in ("KEV_API_KEY", "HF_TOKEN") if os.environ.get(k)}

app = modal.App(SETTINGS["KEV_APP_NAME"])
image = (
    modal.Image.debian_slim(python_version="3.13")
    .apt_install("git")
    .uv_pip_install(f"kev[serve] @ git+https://github.com/jaredpalmer/kev.git@{KEV_REF}")
    .uv_pip_install("flash-linear-attention==0.5.2", "triton>=3.7.1")   # the fused Qwen3.5 kernels are built on this fla (it needs triton >= 3.7.1 on Hopper)
    .env({"HF_HOME": "/hf", "HF_HUB_DISABLE_PROGRESS_BARS": "1", "TOKENIZERS_PARALLELISM": "false", "PYTHONUNBUFFERED": "1",
          "TRITON_CACHE_DIR": "/hf/triton-cache", **SETTINGS})
    .add_local_python_source("krino")   # this repository's package (deploy from the repository root)
)
cache = modal.Volume.from_name("kev-hf-cache", create_if_missing=True)
QUESTIONS = {"department": {"type": "choice", "instructions": "Which team should handle this?",
                            "criteria": {"returns": "Exchanges, refunds", "shipping": "Delivery, delays", "billing": "Charges, payments"}},
             "escalate": {"type": "noul", "instructions": "Does this need urgent human attention?"},
             "frustration": {"type": "score", "instructions": "How frustrated is the customer?", "criteria": ["Calm", "Frustrated", "Very angry"]}}
# Warm-up at start: compile the kernels and capture CUDA graphs for states of a sentence to a few paragraphs (the state-pass
# graphs do not depend on the questions). Other shapes run eagerly once (~50-90 ms), then replay graphs captured when idle.
TICKET = "Shoes arrived two weeks late and in the wrong size. Also I see two charges on my card. "
WARMUP = [{"state": TICKET * n, "model": "kev-latest", "questions": QUESTIONS} for n in (1, 4, 16)]


def with_serving(cls):
    """Concurrency and the HTTP front: requests queue in the container, whose model thread batches them. Web endpoint
    (default): ~40-50 requests/s per container through Modal's input plane, then more containers. Flash: Modal's direct
    HTTP proxy in KEV_REGION to uvicorn in the container, ~100 requests/s per container at 64 concurrent (Kev-4B, H100)."""
    if FLASH:
        return modal.experimental.http_server(port=8000, proxy_regions=[SETTINGS["KEV_REGION"].split(",")[0]], startup_timeout=1200)(modal.concurrent(target_inputs=32)(cls))
    return modal.concurrent(max_inputs=64, target_inputs=32)(cls)


@app.cls(image=image, gpu=GPU, region=SETTINGS["KEV_REGION"].split(",") if SETTINGS["KEV_REGION"] else None, cpu=4, memory=(16384, 131072), volumes={"/hf": cache}, secrets=[modal.Secret.from_dict(SECRET)] if SECRET else [],
         min_containers=MIN_CONTAINERS, scaledown_window=300, timeout=600, startup_timeout=1200)
@with_serving
class Kev:
    @modal.enter()
    def load(self):
        import torch
        from kev.api import SystemOneRequest
        from kev.checkpoint import Checkpoint, LoadOptions
        from kev.serve import app as api
        from krino.serve import build
        started = time.time()
        # loads MODEL raw (temperature 1.0) and re-serves each answer at its type's temperature (krino.json / KRINO_TEMPERATURES)
        server = build(MODEL, "cuda", LoadOptions(dtype=torch.bfloat16, cuda_graphs=True, fused=True))
        for req in WARMUP: server.answer(SystemOneRequest.model_validate(req))
        server.wait_idle()                                                                  # their CUDA graphs captured before any traffic
        cache.commit()
        api.state.server = server
        print(f"krino serving {MODEL} on {torch.cuda.get_device_name(0)} (temperatures {server.temperatures}, {server.model.graphs.stats()['captured']} CUDA graphs, "
              f"auth {'on' if os.environ.get('KEV_API_KEY') else 'off'}, {'flash' if FLASH else 'web endpoint'}), ready in {time.time() - started:.0f}s", flush=True)
        self.api = api
        if FLASH:
            import threading, uvicorn
            threading.Thread(target=uvicorn.run, args=(api,), kwargs={"host": "0.0.0.0", "port": 8000, "log_level": "warning"}, daemon=True).start()

    if not FLASH:
        @modal.asgi_app(label=f"{SETTINGS['KEV_APP_NAME']}-api")
        def web(self):
            return self.api
