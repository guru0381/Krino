# Evaluation protocol (frozen 2026-10-05, before any stage-2 training)

This file decides which checkpoint wins. It does not change after today except to add a suite, never to loosen a
threshold. Every number in `docs/RESULTS.md` says which partition it came from.

## Partitions and what each is for

| Partition | Suite(s) | Role | Who may read it |
|---|---|---|---|
| **Development panel** | `evals/v4/transfer-v4` (new sources, 656 q), `evals/hard-v1` (hard families), `evals/documents-v1` (real CFPB complaints), `evals/devtools-v1` (tool routing), `evals/krino-breadth/*` (nine datasets neither Kev nor Malkuth trained on: Malkuth's held-out suites, imported by `scripts/import_breadth.sh`; Kev's own `breadth-v1` is in a private mirror we cannot read) | **chooses checkpoints** | every candidate, every seed |
| **Guard** | `evals/v7/decision-v7` development (trained sources) | catches forgetting | every candidate |
| **Report-only** | JevBench public items (231, via `scripts/smoke_cloud.sh`), SemIf | reported in RESULTS.md, **never used to choose** | at most once per candidate we would otherwise publish |
| **Test** | `transfer-v4` test, `krino-breadth/*` test | the release number | once per released model, read after the release candidate is chosen on development |

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

## Incumbent

`krino-stage1-2b/00-trial-0` (stage 1, seed 0). Its development-panel row is the first line of the comparison table in
`docs/RESULTS.md` once `scripts/eval_dev.sh` has run on it.
