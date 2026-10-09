
## Step 3 stage-1 baseline (2026-10-04, study `krino-stage1-2b`, 2 × H100, $6.04)

Kev's `decision-v7` recipe on `Qwen/Qwen3.5-2B-Base@b1485b2f`, LoRA r16 + pointer head, 2 epochs, lr 7e-5.

| trial | seed | objective | decision-v7 dev acc (trained sources) | transfer-v4 dev acc (new sources) |
|---|---|---|---|---|
| 00-trial-0 | 0 | −0.3828 | 0.8513 | **0.7348** |
| 01-trial-1 | 1 | −0.3815 | 0.8584 | 0.7027 |

Reference (Kev's cards, same suites, dev): Kev-0.8B 0.827 / 0.648, Kev-4B 0.873 / 0.817. The 2B lands between
them on both, as expected. Seed spread on new sources is 3.2 pp: generalization is the noisy axis, so every later
comparison needs two seeds. **Carried forward: 00-trial-0** (chosen on transfer-v4 development; the board rewards
new-source accuracy, not trained-source accuracy).

## Stage-1 checkpoint on the public JevBench items (2026-10-05, report-only)

| run | original (72) | easy (48) | hard (111) | all (231) |
|---|---|---|---|---|
| Kev-0.8B | 80.6% | 100% | 36.9% | 63.6% |
| Malkuth-2B | 91.7% | 100% | 40.5% | 68.8% |
| **krino stage1-s0** (T = 1.0) | **93.1%** | 100% | 35.1% | 66.7% |

Kev's base recipe alone already matches Malkuth on the standard tier. The hard tier (35%) is the gap, which is what
stage 2's hard-family data is for; no temperature has been fitted yet, so the Calibration axis is untouched too.

## Incumbent on the frozen development panel (2026-10-05, `scripts/eval_dev.sh`, T = 1.0, Modal H100 reads)

Both stage-1 seeds; `docs/EVAL.md` is the protocol. acc / Brier / ECE are on the clean partition; flip% is the
option-order permutation flip rate (noul/score suites have none; n/r = in `third_party/kev/runs/krino-s1-s1-*/report.json`,
not copied here). No temperature has been fitted yet.

| suite | n | s1-s0 acc | brier | ece | flip% | s1-s1 acc | brier | ece | flip% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| decision-v7 (guard) | 1204 | 0.851 | 0.227 | 0.079 | 1.7 | 0.858 | 0.219 | 0.063 | n/r |
| transfer-v4 | 656 | **0.735** | 0.408 | 0.141 | 13.9 | 0.703 | 0.449 | 0.169 | n/r |
| hard-v1 | 700 | 0.394 | 0.896 | 0.350 | – | 0.391 | 0.913 | 0.348 | – |
| documents-v1 | 568 | 0.768 | 0.340 | 0.075 | – | 0.768 | 0.331 | 0.056 | – |
| devtools-v1 | 900 | 0.520 | 0.788 | 0.362 | – | 0.511 | 0.780 | 0.352 | – |
| breadth/belebele | | 0.677 | | | | 0.675 | | | |
| breadth/sib200 | | 0.798 | | | | 0.820 | | | |
| breadth/rtp_lx | | 0.310 | | | | 0.289 | | | |
| breadth/polyguard | | 0.770 | | | | 0.759 | | | |
| breadth/goemotions | | 0.280 | | | | 0.280 | | | |
| breadth/ledgar | | 0.610 | | | | 0.670 | | | |
| breadth/kold | | 0.680 | | | | 0.620 | | | |
| breadth/laya_apps | | 0.654 | | | | 0.652 | | | |
| breadth/multi_eurlex | | 0.810 | | | | 0.801 | | | |
| **breadth mean (9)** | | **0.621** | | | | 0.618 | | | |

Same nine held-out suites, published full-set results: Kev-0.8B 0.582, Kev-4B 0.669, Malkuth-2B 0.667, Malkuth-4B
0.705, Jev 0.739. Stage 1 (0.62) sits between Kev-0.8B and Malkuth-2B with no breadth data at all, which is what
stage 2's mix is for. What the panel says about where the points are:

- **hard-v1 0.39 at ECE 0.35**: the hard families (long policy, trade-off, probability, multi-hop, temporal/numeric,
  judge, ambiguous) are near chance and confidently wrong. This is the JevBench hard tier and the whole sealed set,
  and the Calibration axis is scored there. Stage 2 trains on hard-v1's training partition, twice.
- **devtools-v1 0.52 at ECE 0.36**: tool routing and code judgements, also untrained; cheap to fix the same way.
- **documents-v1 0.77** with ECE 0.06-0.08: long real documents already work reasonably at T = 1.
- **transfer-v4 flip 13.9%**: option-order sensitivity on new sources is high; a decision rule guard (EVAL.md 4).
- Seeds agree within 1 pp everywhere except transfer-v4 (3.2 pp) and ledgar/kold (6 pp on 100-item suites): those
  are the noisy readouts, and the reason every candidate runs two seeds.

Incumbent: `krino-stage1-2b/00-trial-0` (s1-s0).

## Stage 2, seed 0 on the development panel (2026-10-06, study `krino-stage2-2b`, 1 × H100, 3 h 31 m)

Mix v1 (`data/krino-mix-v1/manifest.json`: 79,484 records; Malkuth's commercially licensed breadth sources + hard-v1
train ×2 + documents-v1 train + devtools-v1 train) plus 6,000 replay records from decision-v7, one epoch at lr 2e-5 from
`krino-stage1-2b/00-trial-0`. Panel at T = 1.0 (what `eval_dev.sh` reads); the served temperature is fitted afterwards.

| suite | n (questions) | stage1-s0 | **stage2-s0** | change |
|---|---:|---:|---:|---:|
| decision-v7 (guard) acc / ECE / flip% | 1264 | 0.851 / 0.079 / 1.7 | 0.845 / 0.087 / 3.3 | −0.6 pp (guard: ≥ −1.0) |
| transfer-v4 acc / ECE / flip% | 656 | 0.735 / 0.141 / 13.9 | **0.755** / 0.125 / **5.6** | +2.0 pp; flips −8.3 pp |
| hard-v1 acc / Brier / ECE | 1083 | 0.394 / 0.896 / 0.350 | **0.729** / 0.377 / **0.066** | +33.5 pp; ECE −0.28 |
| documents-v1 acc / ECE | 920 | 0.768 / 0.075 | **0.866** / 0.071 | +9.8 pp |
| devtools-v1 acc / ECE | 1074 | 0.520 / 0.362 | **0.681** / 0.116 | +16.1 pp |
| breadth/belebele | 1000 | 0.677 | 0.743 | +6.6 |
| breadth/sib200 | 1000 | 0.798 | 0.807 | +0.9 |
| breadth/rtp_lx | 1000 | 0.310 | 0.368 | +5.8 |
| breadth/polyguard | 3000 | 0.770 | 0.811 | +4.1 |
| breadth/goemotions | 100 | 0.280 | 0.310 | +3.0 |
| breadth/ledgar | 100 | 0.610 | 0.610 | 0.0 |
| breadth/kold | 100 | 0.680 | 0.720 | +4.0 |
| breadth/laya_apps | 1000 | 0.654 | 0.706 | +5.2 |
| breadth/multi_eurlex | 357 | 0.810 | 0.796 | −1.4 |
| **breadth mean (9)** | | 0.621 | **0.652** | +3.1 pp |

Against `docs/EVAL.md`: gain on all three gain suites (hard-v1 +33.5, transfer-v4 +2.0, breadth +1.5 needed, +3.1 got);
no forgetting (decision-v7 −0.6, transfer-v4 up); hard-v1 ECE down, not up; transfer-v4 flip rate down, not up. Seed 0
passes alone; seed 1 (`krino-stage2-2b-s1`, rerun after a slow H100 timed out at step 8000/10686 — 0.173 s/record
against seed 0's 0.113) decides the replacement. Breadth 0.652 is just under Malkuth-2B's 0.667 on the same nine suites,
with none of Malkuth's non-commercial sources.

Served temperature (Step 6, `scripts/calibrate.sh s2-s0`): **T = 1.91**, five-fold out-of-fold ECE on the breadth pool
0.120 → 0.017, hard-v1 dev ECE 0.066 → 0.050, accuracy unchanged. Published as `Guru0381/krino-2b@stage2-s0`.

## Stage-2 seed 0 on the public JevBench items (2026-10-06, report-only, T = 1.91)

| run | original (72) | easy (48) | hard (111) | all (231) |
|---|---:|---:|---:|---:|
| Kev-0.8B | 80.6% | 100% | 36.9% | 63.6% |
| Malkuth-2B | 91.7% | 100% | 40.5% | 68.8% |
| krino stage1-s0 (T = 1.0) | 93.1% | 100% | 35.1% | 66.7% |
| **krino stage2-s0 (T = 1.91)** | 87.5% | 100% | **41.4%** | 68.0% |

The hard tier (the sealed families and the Calibration axis) is now past Malkuth-2B; the original tier gave back four of
72 items. Hard-tier calibration, same harness (the board's Calibration axis is scored here):

| run | hard correct (111) | Brier | ECE |
|---|---:|---:|---:|
| Kev-0.8B | 41 | 0.716 | **0.177** |
| Malkuth-2B | 45 | 0.786 | 0.295 |
| krino stage1-s0 (T = 1.0) | 39 | 1.040 | 0.479 |
| **krino stage2-s0 (T = 1.91)** | **46** | **0.713** | 0.246 |

Stage 2 beats Malkuth-2B on all three; Kev-0.8B's ECE is the remaining calibration headroom.

## Stage 2, both seeds: the decision (2026-10-06)

Seed 1 (`krino-stage2-2b-s1/00-trial-0`; the first seed-1 container ran at 0.173 s/record and timed out at step
8000/10686, the rerun on a 6 h ceiling took 5 h 16 m). Panel at T = 1.0:

| suite | stage1-s0 (incumbent) | stage2-s0 | stage2-s1 | stage-2 mean |
|---|---:|---:|---:|---:|
| decision-v7 acc / ECE / flip% | 0.851 / 0.079 / 1.7 | 0.845 / 0.087 / 3.3 | 0.842 / 0.088 / 1.7 | 0.8435 (−0.75 pp) |
| transfer-v4 acc / ECE / flip% | 0.735 / 0.141 / 13.9 | 0.755 / 0.125 / 5.6 | **0.790** / 0.090 / **2.8** | 0.7725 (+3.8 pp) |
| hard-v1 acc / Brier / ECE | 0.394 / 0.896 / 0.350 | **0.729** / 0.377 / 0.066 | 0.717 / 0.392 / 0.091 | 0.723 (+32.9 pp) |
| documents-v1 acc / ECE | 0.768 / 0.075 | **0.866** / 0.071 | 0.860 / 0.080 | 0.863 (+9.5 pp) |
| devtools-v1 acc / ECE | 0.520 / 0.362 | 0.681 / 0.116 | **0.682** / 0.108 | 0.6815 (+16.2 pp) |
| breadth/belebele | 0.677 | 0.743 | 0.744 | |
| breadth/sib200 | 0.798 | 0.807 | 0.824 | |
| breadth/rtp_lx | 0.310 | 0.368 | 0.364 | |
| breadth/polyguard | 0.770 | 0.811 | 0.805 | |
| breadth/goemotions | 0.280 | 0.310 | 0.270 | |
| breadth/ledgar | 0.610 | 0.610 | 0.610 | |
| breadth/kold | 0.680 | 0.720 | 0.740 | |
| breadth/laya_apps | 0.654 | 0.706 | 0.712 | |
| breadth/multi_eurlex | 0.810 | 0.796 | 0.824 | |
| **breadth mean (9)** | 0.621 | 0.652 | **0.655** | 0.6535 (+3.3 pp) |

`docs/EVAL.md` rule, both seeds: gain on all three gain suites with both seeds in the same direction; decision-v7 −0.75 pp
(inside −1.0, the closest clause); transfer-v4 up; hard-v1 ECE at the served temperature 0.050 / 0.041 against 0.350;
transfer-v4 flip rate 5.6 / 2.8 against 13.9. **Stage 2 replaces the incumbent.** Seed chosen by the stage-1 tie-break
(transfer-v4 development): **seed 1**, `krino-stage2-2b-s1/00-trial-0`, served at **T = 1.95** (folds 1.91–2.00;
pool ECE 0.119 → 0.021, out-of-fold 0.023 [0.017, 0.041]; hard-v1 dev 0.091 → 0.041). Published as
`Guru0381/krino-2b@stage2-s1`.

Cost of stage 2: seed 0 3 h 31 m, seed 1 4 h (timed out) + 5 h 16 m, about $62 of H100 time; the plan said $25, the
long states (policy ~3.5k tokens, documents to 7.5k) cost 3× the short-state estimate, and slow hosts cost the rest.

## The incumbent on the public JevBench items (2026-10-06, report-only, T = 1.95)

| run | original (72) | easy (48) | hard (111) | all (231) | hard Brier / ECE |
|---|---:|---:|---:|---:|---|
| Kev-0.8B | 80.6% | 100% | 36.9% | 63.6% | 0.716 / 0.177 |
| Malkuth-2B | 91.7% | 100% | 40.5% | 68.8% | 0.786 / 0.295 |
| krino stage1-s0 (T = 1.0) | 93.1% | 100% | 35.1% | 66.7% | 1.040 / 0.479 |
| krino stage2-s0 (T = 1.91) | 87.5% | 100% | 41.4% | 68.0% | 0.713 / 0.246 |
| **krino stage2-s1 (T = 1.95)** | 91.7% | 100% | **42.3%** | **69.7%** | **0.706 / 0.236** |

Ahead of Malkuth-2B overall (161 vs 159 of 231), on the hard tier (47 vs 45) and on hard-tier Brier and ECE, level on
the original tier, Apache-2.0 on an official Qwen base. Kev-0.8B's hard-tier ECE (0.177) is still the better number.

## Run 0: the served temperature under JevBench's typed rules (2026-10-07, `tools/typed_competence.py`, $0)

Development panel (hard-v1, documents-v1, devtools-v1, transfer-v4 dev: 3,841 questions) of the incumbent, re-scored
under METHOD-v1.5 §3.1 at a grid of temperatures per type. Choice competence is argmax-based and T-invariant (67.9);
noul and score are not.

| served T | noul CC | noul answers in the 0.20–0.80 band | noul ECE | score CC | score ECE | choice ECE |
|---:|---:|---:|---:|---:|---:|---:|
| 0.30 | **46.7** | 10 % | 0.168 | **64.6** | 0.335 | 0.195 |
| 0.50 | 39.0 | 16 % | 0.139 | 63.0 | 0.257 | 0.162 |
| 1.00 | 20.4 | 31 % | 0.078 | 58.9 | 0.216 | 0.095 |
| 1.95 (served until now) | **−10.0** | 52 % | 0.022 | 53.0 | 0.163 | **0.029** |

noul argmax ceiling 0.782 (CC 56.4 if nothing abstained). Equal-thirds Intelligence proxy on these rows: global map
37.0 → per-type map (choice 1.95 / noul 0.3 / score 0.5) **59.4**. On the decision-v7 guard: 70.2 → 78.5. The
Calibration axis moves the other way on noul and score, but under the composite's (I/50)² gate one Intelligence point
is worth ≈1.3 composite points and the whole Calibration axis ≈0.2 (research report, `docs/research/`).

Served map from 2026-10-07: **choice 1.95, noul 0.3, score 0.5** (`krino.json` beside the checkpoint; `krino.serve`).
Public-set accuracy is unchanged by construction (argmax); the public read with the new server is a serving check.
