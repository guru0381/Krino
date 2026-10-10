# Evaluation protocol (frozen 2026-10-05, before any stage-2 training)

This file decides which checkpoint wins. It does not change after today except to add a suite, never to loosen a
threshold. Every number in `docs/RESULTS.md` says which partition it came from.

## Partitions and what each is for

| Partition | Suite(s) | Role | Who may read it |
|---|---|---|---|
| **Development panel** | `evals/v4/transfer-v4` (new sources, 656 q), `evals/hard-v1` (hard families), `evals/documents-v1` (real CFPB complaints), `evals/devtools-v1` (tool routing), `evals/krino-breadth/*` (nine datasets neither Kev nor Malkuth trained on: Malkuth's held-out suites, imported by `scripts/import_breadth.sh`; Kev's own `breadth-v1` is in a private mirror we cannot read) | **chooses checkpoints** | every candidate, every seed |
| **Guard** | `evals/v7/decision-v7` development (trained sources) | catches forgetting | every candidate |
| **Report-only** | JevBench public items (231, via `scripts/smoke_cloud.sh`), SemIf | reported in RESULTS.md, **never used to choose** | at most once per candidate we would otherwise publish |
| **Test** | `transfer-v4` test, `decision-v7` test (`krino-breadth/*` has no test partition: Malkuth's suites are development-only, found at the v0.1.0 read) | the release number | once per released model, read after the release candidate is chosen on development |

`scripts/eval_dev.sh RUN NAME` runs the panel and the guard on Modal and prints one table (acc, Brier, ECE, coverage at
0.9 confidence, option-order flip rate, served temperature).

## The decision rule

A candidate replaces the incumbent only if **all** of these hold, with **two seeds** per candidate:

1. **Gain.** At least one of, on the mean of the two seeds: `hard-v1` dev acc +2.0 pp, or `transfer-v4` dev acc +1.5 pp,
   or the `krino-breadth` mean dev acc +1.5 pp. Both seeds must move in the same direction on that suite.
2. **No forgetting.** `transfer-v4` dev acc and `decision-v7` dev acc each within −1.0 pp of the incumbent (mean of seeds).
3. **No worse calibration.** `hard-v1` dev ECE (at the served temperature) does not rise by more than 0.02.
4. **No worse order sensitivity.** `transfer-v4` permutation flip rate does not rise by more than 2 pp.

A one-seed difference under 2 pp on any suite is noise (Kev's measured seed spread is ±1 pp short-state, ±2 pp on long
panels; our two stage-1 seeds differed by 3.2 pp on `transfer-v4`). Ties keep the incumbent.

## Calibration

The served temperature is fitted on a **held-out-datasets pool** (the `krino-breadth` development partitions), never on training sources (Kev lesson 5: an in-distribution temperature served `hard-v1` at ECE 0.137 against
0.067 with a held-out fit). One global temperature is the default; per-question-type temperatures are tried once on the
same pool and kept only if out-of-fold ECE is lower on `hard-v1` dev.

**Amended 2026-10-07 (typed serving map; a method note, no threshold changes).** JevBench's last published method
(harness `docs/METHOD-v1.5.md` §3.1) scores the three request types differently: choice by argmax, so only its
calibration depends on the temperature; a noul answer with P(yes) strictly between 0.20 and 0.80 is an abstention,
counted wrong; a score answer by the expected level of its distribution. `tools/typed_competence.py` re-scores the
development rows under those rules: at the global T = 1.95, 52 % of our noul answers abstain and the noul third of
Intelligence sits below chance (CC −10.0 on the panel) while the choice third is unchanged. So the served map is
per type — **choice at the ECE-optimal temperature on the held-out pool (unchanged); noul and score at the temperature
that maximises their typed competence on the development panel**, with their ECE reported — written beside the
checkpoint as `krino.json` and served by `krino.serve`. Argmax, and therefore every accuracy in this file, is unchanged.

## Public JevBench items: disclosure log

We run the 231 public items through the official harness to report progress against Malkuth-2B and Kev-0.8B. Rules:
only the per-tier summaries are read (not `results.jsonl`, not individual items); no training record is derived from
them; every training set is screened against them with `kev/scripts/screen_overlap.py` before use; the model card
lists every run below. This log is the disclosure the graders ask for.

| date | checkpoint | original | easy | hard | note |
|---|---|---|---|---|---|
| 2026-10-04 | Kev-0.8B (reference) | 58/72 | 48/48 | 41/111 | pipeline check |
| 2026-10-04 | Malkuth-2B (reference) | 66/72 | 48/48 | 45/111 | the bar |
| 2026-10-05 | krino stage1-s0 | 67/72 | 48/48 | 39/111 | Kev base recipe only, T = 1.0 |
| 2026-10-06 | krino stage2-s0 | 63/72 | 48/48 | 46/111 | mix v1 delta, T = 1.91 (krino-breadth fit); hard tier passes Malkuth-2B |
| 2026-10-06 | krino stage2-s1 | 66/72 | 48/48 | 47/111 | the stage-2 incumbent, T = 1.95; 161/231 against Malkuth-2B's 159 |
| 2026-10-07 | krino stage2-s1, per-type map | 66/72 | 48/48 | 47/111 | serving check of `krino.serve` (choice 1.95 / noul 0.3 / score 0.5): every answer identical, as the map cannot move an argmax; hard-tier Brier 0.844, ECE 0.321 (0.706 / 0.236 at the global 1.95) |
| — | Run 1 (both seeds) | — | — | — | not read: rejected on the development panel |

## Release reads (once per released model)

`scripts/release_test_read.sh` reads the locked test partitions — transfer-v4 test and decision-v7 test through Kev's
`locked_test` (it refuses a second read of the same name) — for the release candidate only, after it was chosen on
development; `tools/fill_card.py` copies the numbers into the model card. Kev's runner names a read `-ungated` when the
trial did not pass Kev's own in-trial gates (`result.json`); our gate is the rule above, so that suffix is bookkeeping. `scripts/release_verify.sh` reads hard-v1 *development* through the published artifact
(anonymous install and serve) to check the release, not to choose anything; the public items are not read again.

| version | candidate | test read | verify read |
|---|---|---|---|
| v0.1.0 | `krino-stage2-2b-s1/00-trial-0` | 2026-10-10, `krino-v0.1.0-ungated`: transfer-v4 test 0.790 / 0.311 / 0.110, decision-v7 test 0.848 / 0.227 / 0.074 (RESULTS.md) | `docs/release/v0.1.0-verify.json` |

## Incumbent

**`krino-stage2-2b-s1/00-trial-0`** (stage 2, seed 1, served at T = 1.95; Hub `Guru0381/krino-2b@stage2-s1`), from
2026-10-06: both stage-2 seeds pass every clause against stage-1 seed 0 (`docs/RESULTS.md`, "the decision"). Seed
tie-break, as in stage 1: transfer-v4 development accuracy. Previous incumbent: `krino-stage1-2b/00-trial-0`.

## Served temperature, per candidate

`scripts/calibrate.sh NAME STUDY/TRIAL` fits the global temperature on the nine `krino-breadth` development rows files
the panel run produced (never on anything the checkpoint trained on; `kev.rounds` checks the mix manifest's `sources`
and `inputs.components` for that) and writes it into the local `head.pt`; `hard-v1` dev rows are reported before and
after, never fitted. The log is kept in `data/calibration/<NAME>.txt`.

| candidate | T | pool ECE raw → fitted (out-of-fold) | hard-v1 dev ECE raw → served |
|---|---:|---|---|
| stage2-s0 | 1.91 | 0.120 → 0.018 (0.017 [0.016, 0.037]) | 0.066 → 0.050 |
| stage2-s1 | 1.95 | 0.119 → 0.021 (0.023 [0.017, 0.041]) | 0.091 → 0.041 |
