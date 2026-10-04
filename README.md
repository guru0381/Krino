# Krino

A 2B-parameter System One decision model, built to be **#1 in the ≤2B class on JevBench**
and the best open Jev-style model under 4B. *Krino*, from Greek κρίνω: to judge, to decide — the root of
*criterion*, which is what the model takes as input.

- Same contract as Jev / Kev / Laya: `POST /v1/systemone` with a `state` and typed
  `noul` / `choice` / `score` questions → calibrated probabilities, one forward pass, no text.
- Torso: `Qwen/Qwen3.5-2B-Base` — the size nobody ships (Kev stops at 0.8B and jumps to 4B).
- Recipe: Kev's pointer head + LoRA, Kev's real-document and hard-family data, a
  frozen-torso KL anchor, one temperature fitted on held-out datasets. Then our own data.
- Hardware: nothing local. A free GitHub Codespace is the dev box; Modal runs every GPU job (serving for
  evaluation, and training through Kev's runner) and bills by the second. Budget: $200–500.

Everything we build sits on two pinned open repos (`scripts/bootstrap.sh` fetches them):

| Repo | Pinned commit | Why |
|---|---|---|
| [jaredpalmer/kev](https://github.com/jaredpalmer/kev) | `fe64b1274ea7f80d4095866df90666abb03e9cf6` (2026-10-03) | training, serving, eval suites, MLX backend, Modal runner |
| [fstandhartinger/jevbench](https://github.com/fstandhartinger/jevbench) | `bb05a335bc809e61b20c0f745d25499a82b326fc` (2026-09-29) | the official harness and the 231 public items |
| [newfull5/malkuth](https://github.com/newfull5/malkuth) | `af2e1c06ded5c448e78394f356319fc2e49f4c94` (2026-09-25) | the ≤2B leader: its data builder, selection set and 29-suite breadth benchmark (`docs/MALKUTH.md`) |

## Targets

| Axis | Laya (421M) | Malkuth-2B (class #1) | Kev-0.8B | **Krino-2B target** |
|---|---|---|---|---|
| Intelligence | 36 | 41 | 31 | **44–48** |
| Calibration | 64 | 54 | 50 | **74+** |
| Speed | 71 | 91 | 77 | **90** |
| Cost | 86 | 62 | 76 | ~61 (priced at the 4B rate) |
| **JevBench score** | 30.3 | 38.9 | 18.9 | **50–58** |

Composite = harmonic mean of the four axes, × (I/50)² when Intelligence < 50.
Beating 38.9 makes it #1 at ≤2B; 50+ is top-12 overall, above every model under 4B.

## The steps

| # | Step | Where | Status |
|---|---|---|---|
| 1 | Codespace + Modal setup, smoke-test the loop with Kev-0.8B on an L4, run the JevBench harness, then the **Malkuth-2B reference row** | dev box + Modal, ~$0.50 | **← you are here** |
| 2 | Hugging Face token, pin the 2B base revision, 2-minute T4 smoke of the trainer | dev box + Modal | |
| 3 | Baseline: Kev's stage-1 recipe on Qwen3.5-2B-Base (`experiments/stage1-2b.json`), 2 seeds | cloud, ~$10 | |
| 4 | Eval protocol: Kev dev suites + JevBench public + our own unseen-family split; **frozen before step 5** | dev box | |
| 5 | Stage 2: one combined delta — Malkuth's commercial breadth sources + Kev's hard-v1/documents/devtools, replay, KL anchor | cloud, ~$25 | |
| 6 | Calibration: one temperature fitted on held-out *datasets*; serving check on an L4/L40S | cloud, ~$5 | |
| 7 | Our data: family-targeted generators for the sealed families where everyone is weak | dev box + LLM API, ~$50 | |
| 8 | Iterate (15–20 runs), choose on dev, read test once | cloud, ~$150 | |
| 9 | Release: weights + data + server on the Hub, model card, JevBench submission | dev box | |

`PLAN.md` has the detail for each step and the decision log. `docs/LESSONS.md` is the
distilled evidence from Brooker, Kev and Laya that the plan is built on — read it before
changing the recipe. `docs/MALKUTH.md` is the read on the model we are displacing.

## Quick reference

```bash
scripts/bootstrap.sh          # clone kev + jevbench + malkuth at the pinned commits into third_party/
scripts/setup_linux.sh        # dev box: uv, Python 3.13, Kev, harness, tests (Codespaces runs it automatically)
scripts/serve_modal.sh MODEL NAME         # put any Kev-format checkpoint behind an HTTPS endpoint on Modal
scripts/smoke_cloud.sh [MODEL NAME]       # serve on Modal + run the JevBench public items from the dev box
scripts/run_jevbench.sh NAME [URL|.env]   # harness against any /v1/systemone endpoint → runs/jevbench/NAME
scripts/setup_mac.sh, smoke_mac.sh        # optional: the same on an Apple Silicon Mac (docs/APPENDIX-mac-setup.md)
scripts/pin_base.py           # print the current Hub revision of the 2B base, to pin in experiments/
scripts/train_stage1.sh       # the stage-1 study on Modal (H100 per trial)
```

Layout:

```
third_party/kev        pinned, untouched (we never edit it; changes go through our scripts and configs)
third_party/jevbench   pinned, untouched
third_party/malkuth    pinned, untouched (its tools/build_train_mix.py is the template for our tools/build_mix.py)
experiments/           study plans (JSON) for Kev's Modal runner
scripts/               thin wrappers so every command is reproducible
data/                  our own generated/curated records (JSONL in Kev's request+label format)
runs/                  local eval outputs (gitignored except summaries)
docs/                  lessons, step guides, the animated roadmap (roadmap.html), model card draft
.devcontainer/         the Codespaces box definition
```
