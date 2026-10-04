"""Print the current Hub revision of a base model so a study plan can pin it.

    uv run --no-sync --project third_party/kev python scripts/pin_base.py            # Qwen/Qwen3.5-2B-Base
    uv run --no-sync --project third_party/kev python scripts/pin_base.py Qwen/Qwen3.5-0.8B-Base

Every number we publish must name the base commit it came from (Kev does the same), so paste the
printed sha into `base_revision` in experiments/*.json before the first paid run.
"""
import sys

from huggingface_hub import model_info

repo = sys.argv[1] if len(sys.argv) > 1 else "Qwen/Qwen3.5-2B-Base"
info = model_info(repo)
params = getattr(getattr(info, "safetensors", None), "total", None)
print(f"{repo}\n  revision: {info.sha}\n  last modified: {info.last_modified}\n  params: {params}")
cfg = next((s.rfilename for s in info.siblings if s.rfilename == "config.json"), None)
print(f"  config.json: {'present' if cfg else 'missing'}")
