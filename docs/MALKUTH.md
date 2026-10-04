# Malkuth-2B — the model to beat, and what we take from it

Malkuth (Saechan Oh, `newfull5/malkuth`, Hub `dhtocks/malkuth-2b` and `-4b`) is the current #1 at ≤2B on
JevBench. Pinned in `third_party/malkuth` at `af2e1c06ded5c448e78394f356319fc2e49f4c94` (2026-09-25).

## What it is

- **Exactly our architecture**: Kev's rank-16 LoRA + pointer head, trained with `kev.train --data`, served by
  `kev.serve`. 17.9M trainable parameters, 65 MB adapter. So the architecture is not what we beat it with.
- **Torso**: `empero-ai/Qwen3.8-2B-Distill` (a third-party distill of the newer Qwen3.8 generation), revision
  `e37a2dc4…`. The 4B uses `Qwen/Qwen3.5-4B-Base`.
- **Data**: 89,791 labelled requests from 20 public sources, built by `tools/build_train_mix.py`, plus
  `--replay 6000` from Kev's `decision-v7`. It is a *classification* mix: MASSIVE intent and scenario in ~10
  languages, XNLI, PAWS-X, tweet sentiment, CLINC150, KLUE, NSMC, KoBEST, typed-decisions (teacher soft targets),
  RACE, ARC, toxicity, MMMLU, spam, jailbreak; later mixes add civil-comments toxicity, APEACH, XQuAD-as-MC,
  Aegis and BeaverTails. Five sources are Korean-only. The 2B shipped on "mix2"; the 4B on mix4/mix5.
- **Selection and temperature** on a 2,750-question `benchmarks/val/` set only; fitted T = 1.1755 for the 2B.
  (The board notes the evaluated 4B revision shipped with T = 1.0 despite the card saying calibrated.)
- **Licence**: code Apache-2.0; **weights research-use only**, because XNLI (CC-BY-NC-4.0) and RACE
  (non-commercial, no redistribution) are in the mix, and two sources carry no licence at all.

## How it scores

| | Malkuth-2B | Malkuth-4B | Kev-0.8B | Laya |
|---|---|---|---|---|
| JevBench score | **38.9** (#26) | 44.5 (#18) | 18.9 | 30.3 |
| Intelligence | 41.3 | 43.1 | 30.5 | 36.1 |
| Calibration | 53.5 | 61.5 | 49.7 | 63.7 |
| Speed | 91.4 | 88.3 | 77.0 | 71.1 |
| Cost | 61.5 | 61.5 | 76.1 | 86.2 |
| Public accuracy (534) | 69.7% | 74.9% | 49.4% | 58.4% |
| Sealed accuracy (308) | 24.4% | 23.4% | 27.3% | 30.8% |
| p50 (adjusted) | 0.04 s | 0.09 s | 0.43 s | 0.79 s |

On its own 29-suite classification benchmark it beats Kev-9B on held-out datasets (0.703 vs 0.700) and sits 5
points behind Jev (0.754). On the five Korean suites it is far ahead of every Kev.

## Where it is weak, and why

1. **Sealed accuracy is 24.4%, below Laya's 30.8% and Kev-0.8B's 27.3%.** Its public-to-sealed gap is 45 pp.
   The mix has no long-document, multi-hop, policy, numeric, probability or abstention content; the sealed families
   are all of those. Its Intelligence (41) comes from the easy/standard/judge tiers, where classification breadth
   pays, not from the hard tier.
2. **Calibration 53.5.** JevBench's Calibration axis is scored on the hard tier. One temperature fitted on short
   classification items does not transfer to 4k-token policy questions (the same effect Kev measured: in-distribution
   T served hard-v1 at ECE 0.137 vs 0.067 with a held-out fit). Its own reliability table shows over-confidence at
   every bucket (−0.04 to −0.11).
3. **Base is a third-party distill.** Nobody can audit what Qwen3.8-2B-Distill was distilled on; the board's
   notes already flag undisclosed training data as a mark against a row.
4. **Research-use-only weights.** A team that wants Laya's niche (self-hosted, commercial) cannot deploy it.

## What we take

- **The data-builder pattern**, verbatim in spirit: Kev `--data` format, half the records using the eval
  benchmark's wording and half a paraphrase, many-label intents shown as the full label set 70% of the time and a
  random 5–20-option subset otherwise, soft targets for teacher-labelled sources, `--replay` from decision-v7.
  `tools/build_train_mix.py` is Apache-2.0 and most of its sources are commercially licensed; we fork it as
  `tools/build_mix.py` and drop XNLI, RACE, the unlicensed sources and anything else non-commercial.
- **Val-only selection**: a separate ~2–3k-question selection set, never reported.
- **Its 29-suite benchmark** as a second, classification-breadth report alongside JevBench. The lite/mid/val
  suites are checked in; `full/` rebuilds from the sources. It is how we show we didn't trade breadth for depth.
- **The Korean numbers** as a target if we want its multilingual story too.

## What we don't take

- **Its weights as a warm start.** `--init_from dhtocks/malkuth-2b` would inherit the research-only licence and the
  unauditable torso, and Plumb-4B's gain over JevK5 came from *training on top*, not from the start point.
- **Its torso.** We start on `Qwen/Qwen3.5-2B-Base` (Apache-2.0, official) and A/B the Qwen3.8 distill later,
  with the licence question answered first.
- **Its JevBench-blind data mix as the whole mix.** Our mix v1 is its commercially-safe breadth sources **plus**
  Kev's hard-v1, documents-v1 and devtools-v1. Breadth gets the easy/standard/judge tiers; the hard families get
  the hard tier, the sealed set and the Calibration axis. Nobody at 2B has shipped that union.

## Reference row on our pipeline

```bash
KEV_RUN=dhtocks/malkuth-2b scripts/smoke_mac.sh malkuth-2b-mac      # 16 GB+ Mac; see Step 1 for the 8 GB case
```

Expect public accuracy near 69.7% (easy ≈ 100%, hard well under 50%). This row is what every later checkpoint is
compared against; keep its run directory.
