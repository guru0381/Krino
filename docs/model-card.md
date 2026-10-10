---
language:
  - en
  - multilingual
license: apache-2.0
library_name: peft
base_model: Qwen/Qwen3.5-2B-Base
base_model_relation: adapter
pipeline_tag: text-classification
tags:
  - decision-model
  - system-one
  - calibration
  - lora
  - multiple-choice
  - typesafe
  - kev
  - qwen3.5
datasets:
  - legacy-datasets/banking77
  - google/boolq
  - fancyzhx/ag_news
  - nyu-mll/multi_nli
  - SetFit/sst5
  - Yelp/yelp_review_full
  - CogComp/trec
  - fancyzhx/dbpedia_14
  - SetFit/amazon_reviews_multi_en
  - stanfordnlp/imdb
  - allenai/ai2_arc
  - bigcode/commitpackft
  - nvidia/Aegis-AI-Content-Safety-Dataset-2.0
  - davidheineman/consumer-finance-complaints-large
  - mteb/amazon_massive_intent
  - mteb/amazon_massive_scenario
  - google-research-datasets/paws-x
  - clinc/clinc_oos
  - klue/klue
  - skt/kobest_v1
  - LocalLLaMA/typed-decisions
  - textdetox/multilingual_toxicity_dataset
  - jackhhao/jailbreak-classification
  - google/civil_comments
  - jason9693/APEACH
  - google/xquad
metrics:
  - accuracy
  - brier_score
  - expected_calibration_error
model-index:
  - name: Krino-2B
    results:
      - task: { type: text-classification, name: typed decisions, out-of-domain (locked test, read once) }
        dataset: { type: mixed, name: "transfer-v4 test: six never-trained public sources and held-out policy structures" }
        metrics:
          - { type: accuracy, value: {{transfer_test_acc}} }
          - { type: brier_score, value: {{transfer_test_brier}} }
          - { type: expected_calibration_error, value: {{transfer_test_ece}} }
      - task: { type: text-classification, name: typed decisions, trained sources (locked test, read once) }
        dataset: { type: mixed, name: "decision-v7 test" }
        metrics:
          - { type: accuracy, value: {{decision_test_acc}} }
          - { type: brier_score, value: {{decision_test_brier}} }
---

# Krino-2B

Krino (Greek κρίνω, *to decide*; the root of *criterion*) is a 2B-parameter **System One decision model**. You give it
a piece of text (the *state*) and one or more typed questions — `noul` (yes/no), `choice` (pick one option),
`score` (an ordered level) — and it returns a probability for every option of every question in **one forward pass**.
It never generates text, so there is nothing to parse and nothing to hallucinate; what you get is a distribution you can
threshold, route on, or log.

Krino is built on [Kev](https://github.com/jaredpalmer/kev) (Apache-2.0): a rank-16 LoRA adapter and a pointer head on a
frozen `Qwen/Qwen3.5-2B-Base`, served with the TypeSafe System One wire format (`POST /v1/systemone`). It is the
2B-parameter member of that family, between Kev-0.8B and Kev-4B, trained on Kev's open data plus a commercially licensed
breadth mix, and served with one temperature per question type.

- **Weights, code and training data: Apache-2.0 or more permissive.** No research-only sources (XNLI, RACE and
  BeaverTails, which make other 2B decision models non-commercial, are deliberately out).
- **Repository:** [github.com/guru0381/Krino](https://github.com/guru0381/Krino) — the recipe, every script, the
  evaluation protocol (`docs/EVAL.md`), every number (`docs/RESULTS.md`) and the decision log (`PLAN.md`).
- **Base:** `Qwen/Qwen3.5-2B-Base` at revision `b1485b2fa6dfa1287294f269f5fb618e03d52d7c` (1.9B parameters, Apache-2.0).

## Serve

```bash
pip install "krino @ git+https://github.com/guru0381/Krino.git@v0.1.0"
krino-serve --run Guru0381/krino-2b@v0.1.0 --host 0.0.0.0 --port 8008
```

`krino-serve` is Kev's server (`kev.serve`: batching, prefix cache, CUDA graphs, bearer auth with `KEV_API_KEY`) with
one addition: the checkpoint is loaded raw and every answer is re-served at its question type's temperature
(`krino.json` in this repo; see *Calibration*). `GET /v1/krino` shows the map in use. It runs on any CUDA GPU with
about 8 GB free in bf16 (an L4 is enough), on Apple Silicon through Kev's MLX backend, and on CPU for testing.
`KEV_TRUNCATE_STATES=1` truncates states over 65,536 tokens instead of refusing them with a 422.

```bash
curl -s http://127.0.0.1:8008/v1/systemone -H 'content-type: application/json' -d '{
  "model": "kev-latest",
  "state": "Shoes arrived two weeks late and in the wrong size. Also I see two charges on my card.",
  "questions": {
    "department": {"type": "choice", "instructions": "Which team should handle this?",
                   "criteria": {"returns": "Exchanges, refunds, wrong or damaged items",
                                "shipping": "Delivery status, delays, lost packages",
                                "billing": "Charges, invoices, payment problems"}},
    "escalate":   {"type": "noul",  "instructions": "Does this need urgent human attention?"},
    "frustration":{"type": "score", "instructions": "How frustrated is the customer?",
                   "criteria": ["Calm", "Frustrated", "Very angry"]}}}'
```

The response carries `probabilities` for every question (`{"returns": 0.71, "shipping": 0.17, "billing": 0.12}`,
`{"false": 0.3, "true": 0.7}`, a probability per level), the argmax answers, and `usage.input_tokens`. The TypeSafe
Python client works unchanged (`TypeSafeClient(base_url="http://127.0.0.1:8008", api_key="local")`).

## Results

Every number below is on a partition that never entered training, read at the raw temperature (T = 1) unless the column
says otherwise. Partitions, the decision rule and the disclosure log are in
[`docs/EVAL.md`](https://github.com/guru0381/Krino/blob/main/docs/EVAL.md); the full tables with seeds and
intervals are in [`docs/RESULTS.md`](https://github.com/guru0381/Krino/blob/main/docs/RESULTS.md).

### Locked test (read once, after the release candidate was chosen on development)

| suite | questions | accuracy | Brier | ECE |
|---|---:|---:|---:|---:|
| transfer-v4 test (six never-trained public sources + held-out policy structures) | {{transfer_test_n}} | **{{transfer_test_acc}}** | {{transfer_test_brier}} | {{transfer_test_ece}} |
| decision-v7 test (Kev's trained sources) | {{decision_test_n}} | {{decision_test_acc}} | {{decision_test_brier}} | {{decision_test_ece}} |
{{breadth_test_rows}}

### Development panel (chose the checkpoint; two seeds, the released seed shown)

| suite | what it measures | questions | accuracy | Brier | ECE |
|---|---|---:|---:|---:|---:|
| hard-v1 | Kev's seven hard families: long policies with exceptions, trade-offs, probability, multi-hop, dates and arithmetic, judging an answer, missing-fact abstention | 1,083 | 0.717 | 0.392 | 0.091 |
| documents-v1 | real US consumer-finance complaints (CFPB), product and issue, states to 7k tokens | 920 | 0.860 | 0.224 | 0.080 |
| devtools-v1 | developer tooling: code review, commit type, flaky tests, content safety, tool routing, prompt injection | 1,074 | 0.682 | 0.450 | 0.108 |
| transfer-v4 dev | never-trained public sources (MMLU, QNLI, PAWS, SciQ, emotion, tweet_offensive) + held-out policy structures | 656 | 0.790 | 0.312 | 0.090 |
| decision-v7 dev (guard) | Kev's trained sources | 1,264 | 0.842 | 0.236 | 0.088 |
| krino-breadth (nine suites) | datasets neither Kev nor the breadth mix trained on: Belebele, SIB-200, RTP-LX, PolyGuard, GoEmotions, LEDGAR, KOLD, Laya apps, MultiEURLEX | 7,657 | 0.655 (mean) | | |

Option-order permutation flip rate on transfer-v4: 2.8 % (13.9 % after stage 1 of the same recipe).

### JevBench public items (report-only)

[JevBench](https://benchmarkheaven.com/jev-models) publishes 231 of its decisions (original 72, easy 48, hard 111)
and keeps 1,200 sealed. Krino never trained on the public items — every training set is screened against them
(`screen_overlap.py`, 0 offending records) — and never used them to choose a checkpoint; they were read twice for this
checkpoint, once at a global temperature and once with the per-type map, both logged in `docs/EVAL.md`.

| tier | correct | accuracy |
|---|---:|---:|
| original | 66 / 72 | 0.917 |
| easy | 48 / 48 | 1.000 |
| hard | 47 / 111 | 0.423 |
| **all public** | **161 / 231** | **0.697** |

For scale on the same harness and items: Malkuth-2B 159/231 (hard 45/111), Kev-0.8B 147/231 (hard 41/111). The sealed
score is the board's to measure; the request for a row is `docs/jevbench-request.md` in the repository.

## Calibration: one temperature per question type

Krino's head is trained at T = 1 and served through a per-type map, `krino.json`:

| type | served T | why |
|---|---:|---|
| choice | 1.95 | minimises top-label ECE on the nine never-trained breadth suites (five-fold, out-of-fold ECE 0.023); hard-v1 dev ECE 0.091 → 0.041 |
| noul | 0.30 | yes/no answers are read as decisions: a probability near 0.5 is an abstention, and a soft temperature puts half of them there. 0.3 keeps 90 % of answers decisive at the argmax accuracy |
| score | 0.50 | ordered levels are read by expected level; a soft distribution drags the expectation to the middle of the scale |

The argmax never changes with the temperature, so accuracy is identical under any map; what changes is how the
distribution should be read. If you want raw probabilities, run with `KRINO_TEMPERATURES="choice=1,noul=1,score=1"`.
If you want a single global temperature as Kev serves, `choice=1.95,noul=1.95,score=1.95`. Hard, out-of-distribution
inputs are over-confident at every setting: on the JevBench hard tier the per-type map gives Brier 0.844 / ECE 0.321
against 0.706 / 0.236 for the global 1.95 — the price of decisive yes/no answers.

## Training

Two stages, both with Kev's trainer (`kev.train`) on one H100 through Kev's Modal runner, LoRA rank 16 (α 32, dropout
0.05, all linear projections), pointer head from scratch, bf16, gradient checkpointing, cross-entropy over each
question's options, option order shuffled, "none of the above" options and distractors inserted at random, a quarter
of choice records paired with their none-of-the-above minimal pair (`p_none_pair 0.25`).

1. **Stage 1 — Kev's base recipe.** Two epochs on `decision-v7` (12,576 records: ten public classification datasets
   with native labels, generated policy minimal pairs, generated rule structures), learning rate 7e-5, batch 4 × 2
   accumulation. Two seeds; the seed with the better transfer-v4 development accuracy was carried forward.
2. **Stage 2 — one combined delta.** One epoch from stage 1 at learning rate 2e-5, batch 2 × 4, states to 7,552 tokens,
   on **mix v1** (79,484 records) plus 6,000 records replayed from `decision-v7`: the breadth half is Malkuth's
   commercially licensed sources — MASSIVE intent and scenario (Apache-2.0), PAWS-X without English (free for any use),
   CLINC150 (CC BY 3.0), KLUE (CC BY-SA 4.0), NSMC (CC0), KoBEST (CC BY-SA 4.0), typed-decisions (Apache-2.0), ARC
   (CC BY-SA 4.0), multilingual toxicity (OpenRAIL++), jailbreak classification (Apache-2.0), Civil Comments (CC0),
   APEACH (CC BY-SA 4.0), XQuAD without English (CC BY-SA 4.0), Aegis 2.0 (CC BY 4.0); the depth half is Kev's own
   training partitions — `hard-v1` (generated, twice), `documents-v1` (CFPB narratives, public domain) and
   `devtools-v1` (permissive per-source licences in its manifest). Two seeds; both passed every clause of the decision
   rule; the released seed was chosen by transfer-v4 development.

Out, by measurement rather than by taste: a KL anchor to the frozen base (null in Kev's and strands-decider's logs), a
second stacked delta of answer-adequacy and multi-step-document rows (`docs/RESULTS.md`, Run 1: +15 to +39 points on
its own held-out formats and nothing on the hard families, so it was not released), and Malkuth's weights as a warm
start (research-only licence). No output of Jev (TypeSafe's hosted model) was used anywhere.

## Limitations

- **A 2B torso has a ceiling on reading.** Dates and arithmetic (hard-v1 temporal_numeric 0.56) and probability (0.60)
  are where it is weakest, then trade-offs (0.69); long policies, multi-hop and judging sit at 0.73–0.80.
- **Over-confident out of distribution.** The temperatures are fitted on development rows; on harder, unfamiliar
  inputs the confidence runs ahead of the accuracy (JevBench hard tier: 42 % accurate at ECE 0.32 with the per-type
  map). Treat the probabilities as rankings there, or re-fit `krino.json` on your own held-out data.
- **Abstention is a label, not a behaviour.** The model picks the best option it is given; it will not refuse. Put an
  explicit "insufficient information" option in `criteria` if that is a valid answer.
- **Context.** States are encoded up to 65,536 tokens; with `KEV_TRUNCATE_STATES=1` longer ones are cut, otherwise refused.
- **English-centred with multilingual breadth.** Korean, the six PAWS-X languages and the XQuAD languages appear in the
  mix; everything else is zero-shot from the base.
- A decision model answers the question it is asked, on the state it is given. It has no access to anything else.

## Reproduce

The repository pins every input: Kev at `fe64b1274ea7f80d4095866df90666abb03e9cf6`, the base revision above, the
suite checksums in `third_party/kev/evals/*/manifest.json`, the mix builder (`tools/build_mix.py`) with its screen, the
study plans (`experiments/stage1-2b.json`, `experiments/stage2-2b-s1.json`) and the serving map (`tools/typed_competence.py
--write`). `provenance.json` and `training_config.json` beside the weights carry the trial's hashes.

## Citation

```
@misc{krino2b,
  title  = {Krino-2B: a 2B System One decision model with per-type serving temperatures},
  author = {Gurunath Reddy},
  year   = {2026},
  url    = {https://huggingface.co/Guru0381/krino-2b}
}
```

Built on Kev by Jared Palmer (Apache-2.0) and on Malkuth's breadth recipe by newfull5 (Apache-2.0 code); evaluated
with JevBench by Benchmark Heaven. Thanks to all three.
