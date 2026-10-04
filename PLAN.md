# Plan

Goal: the best ≤2B System One model on JevBench (beat Malkuth-2B's 38.9; aim 50–58), published on the
Hub with weights, data, server and a model card. Budget $200–500. No local hardware: a GitHub Codespace is the dev box, Modal runs every GPU job.

Rules we hold ourselves to (borrowed from Kev's standing rules):
1. Every run names its base revision, data hashes and code commit. `scripts/` wrappers exist for this.
2. Checkpoints are chosen on development partitions. Test partitions are read once, at the end.
3. JevBench public items are reported, never used to pick anything. Keep a log of what we looked at.
4. One change per run. Two seeds before believing a difference under 2 pp.
5. Nothing in `third_party/` is edited. Our changes are configs, data and scripts; if Kev needs a patch,
   it goes upstream or into `patches/` with a reason.

## Step 1 — Cloud setup, smoke test, and the Malkuth reference row (dev box + Modal, ~$0.50)

Done when: a Codespace is running with `scripts/setup_linux.sh` complete, Modal is signed in, and
`scripts/smoke_cloud.sh` has produced `runs/jevbench/smoke-kev08b/` and `runs/jevbench/smoke-malkuth2b/`
(three `summary.json` each).

What it proves: the toolchain works with no local hardware (Codespace for code and the harness, Modal for the
GPU), and we have the two reference rows measured on our own pipeline: Kev-0.8B (board 18.9; public 49.4%) as
the sanity floor, Malkuth-2B (board 38.9; public 69.7%) as the bar. `docs/MALKUTH.md` is the read on what we
are up against.

Guide: `docs/STEP-01-cloud-setup.md`. (The Mac path is kept in `docs/APPENDIX-mac-setup.md`.)

## Step 2 — Hugging Face and the pinned base (dev box + Modal, ~$0)

- Hugging Face account + write token (`hf auth login`). Weights, data and the Space live here.
- Modal is already signed in from Step 1; add a card now (H100s in Step 3 need one; the $30/month credit still applies).
- `scripts/pin_base.py` → paste the sha into `experiments/stage1-2b.json`.
- `KEV_GPU=T4 uv run modal run modal_app.py::smoke` inside `third_party/kev` (about 2 min of GPU).
- Record: Qwen3.5-2B-Base parameter count, context length, and whether Kev's `--lora_targets all`
  picks up its DeltaNet layers the way it does for 0.8B/4B.

## Step 3 — Stage-1 baseline on Qwen3.5-2B-Base (cloud, ~$10)

`scripts/train_stage1.sh`: Kev's `decision-v7` recipe, LoRA r16, 2 epochs, lr 7e-5 (between Kev's 1e-4
at 0.8B and 5e-5 at 4B), seeds 0 and 1. Transfer suite `transfer-v4` scored alongside.
Expected: between Kev-0.8B (new sources 0.648) and Kev-4B (0.817) on transfer-v4 development.
Also run `kev.benchmark` on `transfer-v9` and the JevBench public set, both report-only.

## Step 4 — Freeze the evaluation protocol (dev box, $0) — before any stage-2 training

Development panel (used to choose): transfer-v4 dev, hard-v1 dev, documents-v1 dev, devtools-v1 dev,
breadth-v1 dev (14 public datasets Kev never trained on).
Guards: a short-state pooled panel for regressions (Kev lesson 2), order-sensitivity and isolation from
`kev.benchmark`, ECE on hard-v1 dev.
Report-only: JevBench public (all three files), SemIf.
Test (read once per released model): transfer-v4 test, breadth-v1 test.
Write the panel and thresholds into `docs/EVAL.md` and don't move them afterwards.

## Step 5 — Stage 2: one combined delta, breadth + depth (cloud, ~$25)

Data mix v1 (`tools/build_mix.py`, forked from Malkuth's builder):
- **breadth** — Malkuth's commercially-licensed sources only (MASSIVE intent/scenario, PAWS-X, tweet
  sentiment, CLINC150, KLUE, NSMC, KoBEST, typed-decisions with soft targets, ARC, toxicity, MMMLU, civil
  toxicity, APEACH, XQuAD-MC, Aegis; **no** XNLI, RACE, BeaverTails, or the unlicensed spam/tweet sources);
- **depth** — Kev's hard-v1 train, documents-v1 train, devtools-v1 train.
From the best stage-1 seed with `--init_from`, ONE delta (Kev lesson 3: stacking erodes at small sizes),
`--replay 6000` from decision-v7, `--anchor` KL to the frozen base (Brooker's self-distillation; verify at
2B), `--max_state 5120` so long_policy states fit, one epoch, lr 2e-5. Two seeds. Breadth should carry the
easy/standard/judge tiers to Malkuth's level; depth should take the hard tier, the sealed set and the
Calibration axis past it — the union nobody at 2B has shipped.

## Step 6 — Calibration and serving (cloud, ~$5)

`kev/scripts/calibrate_checkpoint.py` with a held-out-datasets pool (breadth-v1 dev + MMLU-Pro slice),
one global T; compare against per-type T on our own dev split and keep whichever has lower out-of-fold
ECE. Serve on an L4 and an L40S, measure p50/p95 with `kev.benchmark --remote`, confirm requests > 16k
tokens are handled (truncate with `KEV_TRUNCATE_STATES=1` rather than 422, since a refusal scores as wrong).

## Step 7 — Our own data (dev box + LLM API, ~$50)

Targets, from the sealed-family numbers where every leader is weak: long policy (Jev 28%), temporal /
numeric (29%), ambiguous / abstain (30%), probability (Imajev 25%), paraphrase.
Method: generator per family, written from the family description, answers computed by code where
possible (numeric, probability), otherwise two blind open-weight labelers must agree; screen with
`screen_overlap.py`; aim for 2–5k kept records per family; soft targets for abstain / judge items.
Also add 10–15 languages (XNLI, MASSIVE) so one checkpoint covers Laya's multilingual story.

## Step 8 — Iterate (cloud, ~$150)

15–20 runs. Order: (a) stage-2 ablations (anchor on/off, replay size), (b) our data families one at a
time, (c) a Qwen3.8-2B-distill torso A/B, (d) full-weight SFT vs LoRA on the final data mix.
Stop when two consecutive changes don't clear the dev guards, or at the budget.

## Step 9 — Release

Hub: `<you>/krino-2b` (adapter + head + temperature + `training_config.json`), `<you>/krino-data`
(every record we generated, with the screen counts), a Space running the server on ZeroGPU.
Model card: recipe, base revision, every dev/test number with intervals, JevBench public with the
disclosure of how we used it, the Laya and Kev-0.8B comparisons, limitations.
Submit to JevBench via the harness repo's issue template with the pinned revision and the serve command.

## Decision log

- 2026-10-04 — Size class: 2B (not 1B, not 4B). Reason: bar is 38.9, reachable 50–58; same cost reference
  as 4B so no cost penalty relative to the leaders; it is Brooker's class.
- 2026-10-04 — Codebase: build on Kev at `fe64b12` rather than from scratch. It already has the pointer
  head, isolation-correct batching for hybrid Qwen3.5 layers, MLX serving for the Mac, the Modal runner,
  frozen suites, hard-v1/documents/devtools data, calibration and overlap-screening scripts. Our work is
  the 2B recipe, the data, and the release.
- 2026-10-04 — Name: **Krino** (Greek κρίνω, "to decide"; root of *criterion*). Free on PyPI and the Hub, absent from
  the JevBench board at the time of choosing. Package `krino`, Hub `<you>/krino-2b`, board row "Krino-2B".
- 2026-10-04 — No laptop. Dev box = GitHub Codespaces (free, persistent, browser VS Code); GPU = Modal for both
  serving and training (Kev's deploy and study tooling is Modal-native; $30/month free; bills by the second).
  Lightning AI Studio is the fallback dev box if Codespaces hours run out.
- 2026-10-04 — Malkuth: reuse its recipe, not its weights. Its data builder, val-only selection and 29-suite
  breadth benchmark come in (pinned at `af2e1c0`); `--init_from dhtocks/malkuth-2b` is out because the weights
  are research-use-only (XNLI, RACE) and the torso is an unauditable third-party distill. Krino ships
  Apache-2.0, on an official Qwen base, which is itself a reason to pick it over Malkuth. See `docs/MALKUTH.md`.

## Budget tracker

| Step | Planned | Spent | Notes |
|---|---|---|---|
| 1–2 | $1 | | Modal credit, inside the free $30 |
| 3 | $10 | | |
| 5–6 | $25 | | |
| 7 | $50 | | |
| 8 | $150 | | |
| 9 | $10 | | Space on ZeroGPU needs HF PRO (~$9/mo) or stays CPU |
| **Total** | **~$245** | | ceiling $500 |
