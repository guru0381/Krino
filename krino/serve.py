"""Krino's server: Kev's TypeSafe-compatible endpoint (POST /v1/systemone, GET /v1/models) with per-type temperatures.

    krino-serve --run Guru0381/krino-2b@stage2-s1 --host 0.0.0.0 --port 8008
    KRINO_TEMPERATURES="choice=1.95,noul=0.3,score=0.5" krino-serve --run <checkpoint dir>

The checkpoint is loaded raw (temperature 1.0) and every answer is re-served at its question type's temperature
(krino.temperatures). Everything else — batching, prefix cache, CUDA graphs, truncation (KEV_TRUNCATE_STATES=1), bearer
auth (KEV_API_KEY) — is Kev's, unchanged.
"""
import argparse
import os
from dataclasses import dataclass, field, replace

from kev.serve import Server, app
from kev.serve import main as _kev_main  # noqa: F401  (kept importable for parity checks)

from . import __version__
from .temperatures import DEFAULT, apply, load


@dataclass
class KrinoServer(Server):
    temperatures: dict = field(default_factory=lambda: dict(DEFAULT))

    def _body(self, req, meta, ps, m):
        return super()._body(req, meta, apply(ps, meta, self.temperatures), m)


@app.get("/v1/krino")
def krino_card():
    s = app.state.server
    return {"version": __version__, "temperatures": getattr(s, "temperatures", DEFAULT), "loaded_temperature": s.model.head.temperature,
            "rule": "choice: ECE-optimal; noul and score: typed competence (METHOD-v1.5) on held-out development rows"}


def build(run: str, device: str, opts, temperatures: dict | None = None) -> KrinoServer:
    """Load `run` raw and wrap it with the per-type map (krino.json beside the checkpoint or in its Hub repo, or the env)."""
    from kev.checkpoint import Checkpoint
    ck = Checkpoint(run)
    tok, model = ck.load(device, replace(opts, temperature=1.0))
    return KrinoServer(ck, tok, model, device, temperatures=temperatures or load(run))


def main():
    import torch
    from kev.checkpoint import LoadOptions
    from kev.checkpoint import fused_available
    from kev.device import default_device
    from kev.model import SERVE_MAX_STATE
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="checkpoint directory or Hub id (optionally @revision)")
    ap.add_argument("--host", default="127.0.0.1"); ap.add_argument("--port", type=int, default=8008)
    a = ap.parse_args()
    dev = default_device()
    opts = LoadOptions.from_env()
    if dev == "mps" and opts.attn is None: opts = replace(opts, attn="sdpa")
    if dev != "cpu" and opts.dtype is None: opts = replace(opts, dtype=torch.bfloat16)
    if dev == "cuda" and opts.cuda_graphs is None: opts = replace(opts, cuda_graphs=True)
    if dev == "cuda" and opts.fused is None: opts = replace(opts, fused=fused_available())
    if opts.backend is None: opts = replace(opts, backend="auto")
    server = build(a.run, dev, opts)
    app.state.server = server
    print(f"krino {__version__}: serving {a.run} on {dev} via {server.model.backend} ({server.model.dtype}) at {a.host}:{a.port}; "
          f"temperatures {server.temperatures}; states over {SERVE_MAX_STATE:,} tokens "
          f"{'truncated' if server.truncate_states else 'refused (422)'}", flush=True)
    import uvicorn
    uvicorn.run(app, host=a.host, port=a.port)


if __name__ == "__main__":
    main()
