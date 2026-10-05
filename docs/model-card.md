---
license: apache-2.0
base_model: Qwen/Qwen3.5-2B-Base
base_model_relation: adapter
library_name: peft
pipeline_tag: zero-shot-classification
tags: [decision-model, system-one, calibration, kev, lora, pointer-head]
---

# Krino-2B

Krino (Greek κρίνω, "to decide") is a 2B-parameter System One decision model: give it a text and typed questions
(`noul` yes/no, `choice`, `score`), and it returns calibrated probabilities over the options in one forward pass.
It never generates text.

Architecture and training follow [Kev](https://github.com/jaredpalmer/kev): a rank-16 LoRA adapter and a pointer
head on a frozen `Qwen/Qwen3.5-2B-Base`, served by `kev.serve` with the TypeSafe System One API.

**Status: training candidate, not a release.** Branches other than `main` hold intermediate checkpoints; their
numbers live in the project's `docs/RESULTS.md`. The release model card will replace this file.

## Serve

```bash
git clone https://github.com/jaredpalmer/kev.git && cd kev && uv sync --extra serve
uv run --extra serve python -m kev.serve --run Guru0381/krino-2b --port 8009
```

## License

Apache-2.0 for the weights, the code and every training source used. No research-only data.
