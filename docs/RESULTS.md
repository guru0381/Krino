
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
