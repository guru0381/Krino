# Lessons the plan is built on

Three sources: Marc Brooker's Hobson write-up (2B, home 3090, two weeks), Kev's research log
(`third_party/kev/PLAN.md`, "What we have learned" and "Negative results"), and Laya's model card.
Where they disagree, the note says so. Don't re-run a listed negative result without a new reason.

## Architecture

- **Pointer head over the torso's hidden states, not raw LM logits.** Brooker's single biggest win;
  Kev's design; the board's raw-logit controls score Calibration in the 20s.
- **Options are unbounded** (1–255 in Kev). Laya's fixed head budget is why it collapses on 77-option
  questions (0.425 vs Jev 0.870). Keep this property.
- **Base checkpoint, not instruct.** Brooker: instruct variants were worse. Kev: post-trained 9B as base
  eroded date arithmetic more and was dropped. (Kev-27B is the exception, and they say they can't audit it.)
- **Torso generation beats torso size.** Brooker: Qwen3.5-2B beat Qwen3-4B. Watch for a newer 2B base;
  Malkuth-2B used a third-party Qwen3.8-2B distill.
- **One forward pass per question, state cached.** Kev's server already does this; Speed is engineering.

## Training

- **Cross-entropy on the gold option. Calibration losses don't help:** label smoothing, CE+Brier and focal
  all lost to a matched CE control (Kev round 3). Brooker also used plain CE.
- **Shuffle option order in training.** Brooker did; one 4B on the board drops 72% → 21% on yes/no items
  when the option order flips. Kev measures order sensitivity in `kev.benchmark`.
- **Anchor to the frozen torso (KL) to limit forgetting.** Brooker's self-distillation, Kev's `--anchor`.
  Kev lists "anchoring toward the base's answers" as a negative at 4B from scratch, so measure it on the
  2B rather than assume; the strongest evidence for it is Brooker's regression story.
- **At small sizes, train deltas together, not stacked.** Kev at 0.8B: skills on top of a documents delta
  eroded both; the same data in one delta passed (lesson 3). We are closer to 0.8B than to 4B.
- **Replay from the base suite when adding a delta** (Kev `--replay`), sized by what the eval resolves.
- **Soft targets beat hard labels for ambiguous items** (teacher disagrees with the label at p ≥ 0.6),
  but softened MNLI hurt — only for genuinely ambiguous sources (Kev lesson 10).
- **Full-weight SFT ≈ LoRA on the same data; the broad data carries the gains** (Kev round 19).
  LoRA r16 at 2B is cheaper and fits a 24 GB card; start there.
- **Not worth repeating:** question-side-only LoRA, checkpoint averaging, a reliability head,
  9B→0.8B distillation, WiSE-FT interpolation, special embeddings, head_dim changes, two epochs on a
  delta, more same-generator data on top of a delta (Kev negatives). RL: untried by Kev; Brooker's next
  experiment; REINFORCE against a proper score has the same optimum as log loss.

## Data

- **Real documents and hard-family generators are the largest levers** (Kev: +7 to +30 pp in-distribution,
  +9 pp on JevBench public hard for 4B). Kev's `hard-v1` tracks JevBench's hard families one by one with
  zero shared items; `documents-v1` is real CFPB complaints; `devtools-v1` is tool routing. All three are
  in the pinned repo. Use them first; they cost nothing.
- **Task diversity over row count.** Brooker: more base params, more kinds of problems; more of the same
  data doesn't help. Kev: +26 pp for the first 6k hard-v1 records, +5 for the next 12k.
- **Templated synthesis is a dead end; LLM-generated with a verifier works.** Brooker generated with a 27B
  and validated with a 397B. Kev labels synthetic items only when two blind open-weight labelers agree.
- **Buried synthetic long states are not real documents.** Judge long-context on real documents (CUAD, CFPB).
- **Family-targeted generators are legal and effective.** decider-4b v2 (#3) wrote generators from the
  published sealed-family names and passed the independent audit. Brooker never did this.
- **Screen everything against JevBench public items** (`kev/scripts/screen_overlap.py`), and release the
  training data. The graders run an 8-gram audit on the top five.

## Calibration

- **One temperature, fitted on held-out *datasets*, transfers.** Kev: in-distribution-fitted T served badly
  on hard workloads (ECE 0.137 → 0.067 with a held-out fit). A single global T transferred from decision-v7
  to transfer-v4; **per-(type, K) temperatures and a logistic head made things worse** (night 2, round 4.10).
  Brooker fitted one T per question type and was happy with it; typecastlm uses four. Start with one global
  T on held-out datasets; test per-type on our dev split before believing either.
- **Laya shipped at T=1 (ECE 0.466); a refit gives 0.081.** Malkuth-4B also shipped unfitted. Free points.
- **Hard-data training moves calibration too** (Kev-4B JevBench hard ECE 0.263 → 0.112 after round 10).

## Evaluation

- **Build the unseen-task split before the first run.** Brooker's v2 (bigger torso) read as worse because
  the holdout didn't test it. Kev: on 656 questions the CI is ±1.7 pp; seed noise at 9B is ±1 pp short,
  ±2 pp long. A one-seed, one-point lead is noise.
- **In-task accuracy is easy to move; generalization is the ceiling.** Brooker at 2B: "useful, not great".
  The sealed set is all unseen tasks; leaders sit at ~37%.
- **Choose on development, read test once.** Kev's standing rule; the Modal runner enforces it
  (`locked_test`).
- **Public JevBench items are for reporting, never for selection.** The graders publish each submitter's
  disclosure; a public-to-sealed gap above 25 pp now reduces Intelligence.

## The board's scoring, for intuition

- Composite = 4 / (1/I + 1/C + 1/S + 1/K); × (I/50)² when I < 50; Speed and Cost gated below 50.
- Speed: 100 − 20·log10(p50 / 0.1 s), self-hosted latency ×2 + 0.15 s. Even 0 ms model time scores ~96.
- Cost: 100 − 30·log10($ per 1k decisions / $0.001). A 2B is priced at the 4B hosted rate (~$0.02/1k →
  K ≈ 61); tokens per decision is the only cost lever, so keep the prompt format compact.
- Intelligence is chance-corrected per tier (hard 30%, easy 14%, standard 28%, judge 28%), blended with
  the sealed set. Every point of I below 50 is worth ~1.5 composite points.

## Laya, specifically

- Encoder (ModernBERT-large) with a 512-token budget: ~320 tokens of state. Hard-tier states run to 4k+.
- Near chance zero-shot on its own typed-decisions set (0.362 vs 0.461 majority class).
- `noul` follows its option labels instead of the state; `score` is its weakest primitive.
- Its reach came from packaging: `pip install laya`, a Jev-compatible server, a Kaggle fine-tune notebook,
  LangChain/MCP. We need the same to displace it, not just a higher score.
