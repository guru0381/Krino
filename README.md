# Krino

**Krino-2B** is a 2B-parameter System One decision model: hand it a text and typed questions (`noul` yes/no,
`choice`, `score`), get a calibrated probability for every option in one forward pass, no generation. *Krino*, from
Greek κρίνω — to judge, to decide — the root of *criterion*, which is what the model takes as input.

- Weights: [`Guru0381/krino-2b`](https://huggingface.co/Guru0381/krino-2b) (Apache-2.0; the model card is
  [`docs/model-card.md`](docs/model-card.md)).
- Architecture and trainer: [Kev](https://github.com/jaredpalmer/kev) (rank-16 LoRA + pointer head on a frozen
  `Qwen/Qwen3.5-2B-Base`), pinned at `fe64b1274ea7f80d4095866df90666abb03e9cf6`.
- Wire format: TypeSafe System One (`POST /v1/systemone`), so anything that talks to Jev, Kev or Laya talks to Krino.
- What is new here: the data mix (Malkuth's breadth recipe with commercially licensed sources only, on top of Kev's
  hard-family, real-document and developer-tooling data), a frozen evaluation protocol with a two-seed decision rule,
  and **one serving temperature per question type**, chosen for how each type is actually scored.

## Serve

```bash
pip install "krino @ git+https://github.com/guru0381/Krino.git@v0.1.0"
krino-serve --run Guru0381/krino-2b@v0.1.0 --host 0.0.0.0 --port 8008
```

`krino-serve` is `kev.serve` with the checkpoint loaded raw and each answer re-served at its type's temperature
(`krino.json`; `GET /v1/krino` shows the map; `KRINO_TEMPERATURES="choice=1,noul=1,score=1"` for raw output). A request
and its response are in the model card. On Modal: `scripts/serve_modal.sh Guru0381/krino-2b@v0.1.0 krino`.

## Results (short)

Development panel, raw temperature — hard-v1 0.717, documents-v1 0.860, devtools-v1 0.682, transfer-v4 0.790
(option-order flip rate 2.8 %), nine never-trained breadth suites 0.655 mean. JevBench public items (report-only,
never trained on): 161/231 — original 66/72, easy 48/48, hard 47/111; Malkuth-2B reads 159/231 on the same harness.
The locked test (read once) and the full tables are in [`docs/RESULTS.md`](docs/RESULTS.md); the partitions, the
decision rule and the public-item disclosure log are in [`docs/EVAL.md`](docs/EVAL.md).

## How it was built

1. **Stage 1** — Kev's base recipe on `decision-v7`, two seeds, chosen on transfer-v4 development.
2. **Stage 2** — one combined delta: mix v1 (`tools/build_mix.py`, 79,484 records) + 6,000 replayed records, one epoch,
   two seeds, both passing every clause of the decision rule; the released seed chosen by transfer-v4 development.
3. **Serving** — Run 0 (`tools/typed_competence.py`): under the board's typed rules a soft global temperature puts half
   of the yes/no answers into the abstention band; per-type temperatures fix that at no cost to accuracy.
4. **Run 1** — a second delta of answer-adequacy and multi-step-document rows with parent-distribution replay: +15 to
   +39 points on its own held-out formats, nothing on the hard families, rejected (two seeds; `docs/LESSONS.md`).

`PLAN.md` has the steps, the decision log and the budget; `docs/LESSONS.md` the evidence the plan rests on;
`docs/research/` the research report behind Steps 7–8; `docs/MALKUTH.md` the read on the breadth recipe.

## House rules

- Checkpoints are chosen on development partitions only, two seeds per candidate, one change per run.
- The test partitions are read once per released model, after the candidate is chosen.
- JevBench's public items are report-only: never trained on (every training set is screened), never used to choose,
  every read logged in `docs/EVAL.md`.
- `third_party/` is pinned and never edited; everything of ours is in `scripts/`, `tools/`, `krino/`, `experiments/`.

## Quick reference

```bash
scripts/bootstrap.sh                      # clone kev + jevbench + malkuth + strands at the pinned commits into third_party/
scripts/setup_linux.sh                    # dev box: uv, Python 3.13, Kev, harness, tests
scripts/build_mix.sh                      # mix v1 (+ the overlap screen against the public JevBench items)
scripts/train_stage2.sh | pull            # the stage-2 study on Modal; pull the trials
scripts/eval_dev.sh RUN NAME              # the development panel + guard for a checkpoint (one table)
scripts/calibrate.sh NAME STUDY/TRIAL     # the global temperature fit (choice); tools/typed_competence.py the per-type map
scripts/publish_candidate.sh TRIAL REV    # a candidate to the Hub on its own branch
scripts/serve_modal.sh MODEL NAME         # any Kev-format checkpoint behind an HTTPS endpoint on Modal
scripts/run_jevbench.sh NAME URL          # the official harness against an endpoint (public items: report-only)
scripts/release_test_read.sh              # the locked test, once -> tools/fill_card.py fills the model card
scripts/release.sh publish | public       # the release to the Hub (+ tag); make the repo public
scripts/release_verify.sh                 # anonymous install + serve + a dev read, as an evaluator would
tools/compare_tasks.py A B                # per-family accuracy of two candidates
```

Layout:

```
krino/            the package: krino.serve (kev.serve + per-type temperatures), krino.temperatures
scripts/          every command, reproducible; scripts/*_modal.py are the Modal apps (serving, release verification)
tools/            data builders and analysis (build_mix, import_strands, typed_competence, compare_tasks, fill_card)
experiments/      study plans for Kev's Modal runner
docs/             EVAL.md (protocol), RESULTS.md (numbers), LESSONS.md, model-card.md, research/, jevbench-request.md
data/             manifests and screens of the data we built (the records themselves are regenerated by the builders)
third_party/      kev, jevbench, malkuth, strands-decider at pinned commits (gitignored; scripts/bootstrap.sh)
```
