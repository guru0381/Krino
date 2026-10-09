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

Development panel (used to choose): transfer-v4 dev, hard-v1 dev, documents-v1 dev, devtools-v1 dev, and
`krino-breadth` dev (Malkuth's nine held-out suites; Kev's `breadth-v1` is in a private mirror, see the decision log).
Guards: a short-state pooled panel for regressions (Kev lesson 2), order-sensitivity and isolation from
`kev.benchmark`, ECE on hard-v1 dev.
Report-only: JevBench public (all three files), SemIf.
Test (read once per released model): transfer-v4 test, krino-breadth test.
Write the panel and thresholds into `docs/EVAL.md` and don't move them afterwards.

## Step 5 — Stage 2: one combined delta, breadth + depth (cloud, ~$25)

Data mix v1 (`tools/build_mix.py`, forked from Malkuth's builder; `scripts/build_mix.sh` builds and screens it):
- **breadth** — Malkuth's commercially licensed sources only: MASSIVE intent/scenario, PAWS-X (six languages, not
  English), CLINC150, KLUE, NSMC, KoBEST, typed-decisions with soft targets, ARC, textdetox toxicity, civil-comments
  toxicity (score), APEACH, XQuAD-MC (ten languages, not English), Aegis 2.0 train, jailbreak-classification.
  **Out**: XNLI, RACE, BeaverTails (non-commercial), tweet sentiment and sms_spam (no licence), CUAD (hurt ledgar),
  MMMLU and the English PAWS-X / XQuAD slices (they overlap transfer-v4's eval-only mmlu / paws / qnli sources),
  deepset/prompt-injections (devtools-v1's eval-only source). Korean-only sources at half of Malkuth's counts.
- **depth** — Kev's hard-v1 train (×2), documents-v1 train, devtools-v1 train, read through `kev.suite.load_split`
  (checksum-verified; never development or test).
From the stage-1 incumbent with `init_from`, ONE delta (Kev lesson 3: stacking erodes at small sizes), Kev's own
delta recipe (`experiments/stage2-2b.json`): `replay 6000` from decision-v7, `max_state 7552` (hard-v1's context;
`none_pair_max_state 2048` keeps the none-pair siblings on short states), one epoch, lr 2e-5, batch 2 × accum 4,
bf16, two seeds. No `--anchor` in this run: one change per run; the KL anchor is a Step-8 ablation if stage 2
forgets. Breadth should carry the easy/standard/judge tiers to Malkuth's level; depth should take the hard tier, the
sealed set and the Calibration axis past it — the union nobody at 2B has shipped. Launch: `scripts/train_stage2.sh`;
then `scripts/eval_dev.sh` on both trials and the EVAL.md rule.

## Step 6 — Calibration and serving (cloud, ~$5)

`kev/scripts/calibrate_checkpoint.py` with a held-out-datasets pool (breadth-v1 dev + MMLU-Pro slice),
one global T; compare against per-type T on our own dev split and keep whichever has lower out-of-fold
ECE. Serve on an L4 and an L40S, measure p50/p95 with `kev.benchmark --remote`, confirm requests > 16k
tokens are handled (truncate with `KEV_TRUNCATE_STATES=1` rather than 422, since a refusal scores as wrong).

## Step 7 — Research, then the cheapest levers first (dev box, $0–3) — done 2026-10-07

The research report (`docs/research/jevbench-2b-hard-tier-gains.md`) ranked every intervention by measured gain per
dollar from the three public research logs on this architecture (strands-decider/Hobson, Kev, Malkuth), the top ≤4B
board entries and the board's method. Three findings set the plan:

1. The board (v1.6.1) is 300 open + 1,200 sealed decisions in seven subject categories, Intelligence is chance-corrected,
   and the composite is gated by (I/50)²: at our level one Intelligence point ≈ 1.3 composite points, the whole
   Calibration axis ≈ 0.2. Intelligence is the only axis worth a dollar.
2. The last published typed rules make a noul answer with P(yes) in (0.20, 0.80) an abstention counted wrong and score
   a rating by its expected level. Our global T = 1.95 put 52 % of noul answers in the band (noul third below chance).
   **Run 0** (`tools/typed_competence.py`, $0): a per-type served map, choice 1.95 / noul 0.3 / score 0.5, moved the
   equal-thirds proxy on the panel from 37.0 to 59.4. Served by the new `krino` package (`krino.serve`,
   `scripts/krino_serve_modal.py`), map in `krino.json` beside the checkpoint.
3. Only four kinds of data cleared p < 0.01 on held-out sets in any log, and all are cheap: balanced answer-adequacy
   rows, real multi-step documents with a frozen 4B teacher's distributions, verifier-filtered LLM-written documents,
   and replay toward the parent's own distributions.

## Step 8 — The runs the evidence supports (cloud, ≈$70–95 Modal + ≈$50–70 OpenRouter)

- **Run 1 — judge + documents delta** from the incumbent, two seeds (≈$18–22): HelpSteer2 adequacy (CC BY 4.0) +
  strands' committed `adequacy_gen` + ContractNLI/BoardgameQA/MuSiQue multi-step rows with frozen Qwen3.5-4B
  distributions + strands' committed generated documents v16/v18; replay 6,000 toward the parent's own distributions.
  Confirm: EVAL.md gain clause, HelpSteer2 held-out ≥ +0.10, HotpotQA (never trained) ≥ +0.03. Kill: guard below −1.0
  or hard-v1 ≥ 2 pp down (stacking erosion) → Run 3.
- **Run 2 — JevBench-shaped abstention delta**, conditional on Run 1 ($50–70 OpenRouter + ≈$12–16 Modal): ≈2,000
  ambiguous/abstain items written by Qwen3.6-27B and kept on Qwen3.5-397B agreement, look-alike decided cases
  up-weighted, 300 held out as the hard-difficulty temperature pool. The Kev lineage scores 0.11–0.14 on the sealed
  ambiguous family against Plumb-4B's 0.60: the largest per-item headroom on the sealed set.
- **Run 3 — one-delta rebuild** from stage 1 with mix v1 + the new data (≈$40–55), only if Run 1 shows erosion.
- **Not bought** (null or negative in the logs): the KL anchor to the frozen base, more hard-v1, stacking deltas,
  per-(type,K) ECE temperatures, permutation averaging, calibration losses, ensembles, two epochs, full-weight SFT,
  instruct torsos, ShARC/ConditionalQA/RuleTaker/CUAD, temporal/numeric data, a Gemma 4 E2B or MiniCPM5 torso.

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
- 2026-10-05 — Breadth panel: Kev's `breadth-v1` lives in a private mirror we cannot read, so the panel's breadth
  axis is Malkuth's nine held-out suites (`scripts/import_breadth.sh` → `evals/krino-breadth/*`), which also gives a
  like-for-like comparison with Malkuth's and Kev's published numbers. Frozen in `docs/EVAL.md`.
- 2026-10-05 — Stage-1 incumbent: `krino-stage1-2b/00-trial-0` (transfer-v4 0.735; panel in `docs/RESULTS.md`).
- 2026-10-05 — Mix v1 exclusions beyond licensing: MMMLU, PAWS-X-en and XQuAD-en are out because transfer-v4's
  mmlu / paws / qnli slices are built from the same items (MMLU test, PAWS test, SQuAD dev); deepset/prompt-injections
  is out because devtools-v1's eval-only prompt_injection source is built from it. The panel has to stay held-out
  for its numbers to mean anything. hard-v1 enters twice: it is the sealed families, and the hard tier is the gap.
- 2026-10-05 — Stage 2 runs without the KL anchor. Reason: one change per run (the mix is the change); Kev's own
  deltas used replay alone, and the anchor is a Step-8 ablation if the guard (decision-v7, transfer-v4) drops.
- 2026-10-06 — Stage 2 replaces the incumbent (both seeds pass every EVAL.md clause; `docs/RESULTS.md`). Incumbent:
  `krino-stage2-2b-s1/00-trial-0` at T = 1.95, chosen between the seeds on transfer-v4 development. decision-v7 sat
  at −0.75 pp, inside the −1.0 guard but close: the next delta carries the KL-anchor ablation before anything else.
- 2026-10-07 — Serving temperatures are per type (EVAL.md amendment): the board's typed rules make a soft global T an
  abstention tax on noul and a shrink on score. Map choice 1.95 / noul 0.3 / score 0.5, chosen on the development panel.
- 2026-10-07 — The KL-anchor ablation is dropped (null-to-negative in Kev and strands); replay toward the parent's own
  distributions takes its place. Torso stays Qwen3.5-2B-Base (Gemma 4 E2B measured −8.5 hard-tier points same-recipe).
- 2026-10-06 — Trial timeouts are 6 h, not 4: H100 hosts on Modal varied 0.113–0.173 s/record on the same config, and a
  4 h ceiling lost a 75 %-complete seed. The admission bound follows (BUDGET=40 for one trial).

## Budget tracker

| Step | Planned | Spent | Notes |
|---|---|---|---|
| 1–2 | $1 | $0.30 | Modal credit, inside the free $30 |
| 3 | $10 | $6.04 | two H100 trials |
| 5–6 | $25 | ~$70 | stage 2: 3 H100 trials (one timed out on a slow host) ~$62, panel reads and public reads ~$8 |
| 7 | $50 | | |
| 8 | $150 | | |
| 9 | $10 | | Space on ZeroGPU needs HF PRO (~$9/mo) or stays CPU |
| **Total** | **~$245** | ~$77 | ceiling $500. Modal workspace has a $100/month cap (Usage & Billing Settings): raise it before the next training run |
