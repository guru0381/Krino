# JevBench benchmark request — Krino-2B

Issue text for https://github.com/fstandhartinger/jevbench/issues (CONTRIBUTING.md: "File a GitHub issue naming the
system, its public interface (API, checkpoint or demo) and its license or terms"). Filled from `scripts/release.sh publish` and
`scripts/release_verify.sh` on 2026-10-10. Title: **Benchmark request: Krino-2B (Kev
post-train on Qwen3.5-2B-Base, Apache-2.0)**.

---

**System.** Krino-2B — a 2B System One decision model: Kev's architecture (rank-16 LoRA + pointer head) post-trained on
`Qwen/Qwen3.5-2B-Base` (revision `b1485b2fa6dfa1287294f269f5fb618e03d52d7c`, 1.9B parameters). One forward pass per
request, native probabilities for `noul`, `choice` and `score`, nothing generated. Class: jev-rebuild, same lineage as
kev-0.8B / kev-4B and Malkuth-2B.

**Checkpoint.** https://huggingface.co/Guru0381/krino-2b — tag `v0.1.0`, commit `ff185abf129206174c67ebbe6058cab4cc9ccaed` (adapter,
head, tokenizer files, `krino.json`, `provenance.json`, `training_config.json`, model card). Public, no token needed.

**Serving code.** https://github.com/guru0381/Krino — tag `v0.1.0`. The server is Kev's (`kev.serve`, pinned at Kev
commit `fe64b1274ea7f80d4095866df90666abb03e9cf6`) plus per-question-type temperatures; it speaks the TypeSafe wire
format (`POST /v1/systemone`, `GET /v1/models`), so the `typesafe` adapter applies unchanged.

```bash
pip install "krino @ git+https://github.com/guru0381/Krino.git@v0.1.0"
KEV_TRUNCATE_STATES=1 krino-serve --run Guru0381/krino-2b@v0.1.0 --host 127.0.0.1 --port 8009
```

Runs on any CUDA GPU with ~8 GB free in bf16 (an L4 is enough; CUDA graphs and the fused Qwen3.5 kernels are used when
available), offline once the weights are cached. `usage.input_tokens` is reported on every response; nothing is
generated (Kev's `usage.output_tokens` counts the serialized answer, not generated text). `KEV_TRUNCATE_STATES=1` truncates states over 65,536 tokens instead of answering 422. Verified from a
fresh container with no credentials (install from the tag, weights without a token, Kev's benchmark through the HTTP
endpoint): `docs/release/v0.1.0-verify.json` in the repository — hard-v1 dev accuracy 0.717, warm p50
12.8 ms on an L40S.

**Served probabilities — please note.** The head is trained at T = 1 and served through a per-type temperature map
(`krino.json`: choice 1.95, noul 0.30, score 0.50), fitted on our own development partitions, never on JevBench items.
The argmax is unchanged by the map; the distributions the harness receives are the served ones. `GET /v1/krino`
reports the map in use. If the board prefers a single global temperature or raw outputs for a comparison, the server
takes `KRINO_TEMPERATURES="choice=1.95,noul=1.95,score=1.95"` (Kev's global serving) or `...=1,...=1,...=1` (raw).

**Licence and terms.** Weights and code Apache-2.0. Training data: Kev's open `decision-v7`, `hard-v1`,
`documents-v1` (CFPB narratives, public domain) and `devtools-v1` training partitions, plus a breadth mix of
commercially licensed public sources only (MASSIVE, PAWS-X, CLINC150, KLUE, NSMC, KoBEST, typed-decisions, ARC,
multilingual toxicity, jailbreak-classification, Civil Comments, APEACH, XQuAD, Aegis 2.0 — licences in the model card).
No research-only sources (no XNLI, RACE or BeaverTails), no outputs of Jev or any hosted decision model. No binding
terms beyond Apache-2.0.

**Public items.** Never trained on and never used to select a checkpoint. Every training set was screened against the
231 public decisions (8-gram overlap, 0 offending records). They were read, report-only, twice for this checkpoint
through our own endpoint with the `typesafe` adapter: original 66/72, easy 48/48, hard 47/111 (161/231); the reads are
logged in `docs/EVAL.md`. We expect the sealed set to be lower, as for every system.

**Pricing.** No hosted tariff exists for this model; the decider-2b / Malkuth-2B precedent (the Qwen3.5-4B hosted
reference, input tokens only) is the basis we would expect.

**Contact.** @guru0381 on GitHub; the repository's `docs/RESULTS.md` has every development number with seeds and the
evaluation protocol is `docs/EVAL.md`. Happy to run anything else you need.
