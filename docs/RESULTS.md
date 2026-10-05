# Results log

## Step 1 reference rows (2026-10-04, Modal L4, official harness, public items)

| run | original (72) | easy (48) | hard (111) | all (231) | p50 (hard) |
|---|---|---|---|---|---|
| Kev-0.8B | 58 = 80.6% | 48 = 100% | 41 = 36.9% | 63.6% | 216 ms |
| Malkuth-2B | 66 = 91.7% | 48 = 100% | 45 = 40.5% | 68.8% | 292 ms |

Latency includes the Codespace → Modal round trip. Cost: $0.13 (Kev-0.8B) + ~$0.15 (Malkuth-2B) of Modal credit.

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
