# Step 1 — Mac setup and the first end-to-end run

Time: ~15 minutes of typing, ~30–45 minutes of waiting (downloads, then the harness).
Cost: $0. Needs: an Apple Silicon MacBook Air (any M-series; 8 GB RAM is enough for this step,
16 GB+ is comfortable for the 2B later), ~6 GB free disk, a normal internet connection.

What you will have at the end: the whole toolchain working on your laptop, a Jev-compatible server
answering decisions locally, and an official-harness score for Kev-0.8B that you can compare against the
public board. Nothing is trained yet; this is the pipeline check.

## 1. Command-line tools and the project folder

Open Terminal.

```bash
xcode-select --install        # git + compilers; skip if it says already installed
```

Unzip `krino.zip` wherever you keep code, then:

```bash
cd ~/path/to/krino
chmod +x scripts/*.sh
```

## 2. Setup (one time)

```bash
scripts/setup_mac.sh
```

This installs `uv`, fetches Kev and JevBench at their pinned commits into `third_party/`, creates a
Python 3.13 environment with torch, transformers, peft and MLX, and runs Kev's unit tests and the
harness's tests. Expect 5–10 minutes. The last line should be `ok: Mac setup complete`.

If `uv` was just installed and the shell can't find it, run `source ~/.zshrc` (or open a new tab).

## 3. The smoke test

```bash
scripts/smoke_mac.sh
```

Step by step it will:

1. Start `kev.serve` with `jaredpalmer/kev-0.8b` on port 8009. The first run downloads the Qwen3.5-0.8B
   base and Kev's adapter (~2 GB). The server log is `runs/serve-8009.log`.
2. Print `/v1/models` so you can see which backend loaded. On a Mac it should say MLX, bf16.
3. Send one hand-written ticket with three questions and print the JSON answer. Look at it: a
   `choice` with per-option probabilities, a `noul` probability, a `score` with a legend. This is the
   contract our model will implement.
4. Run the 231 public JevBench items (original 72, easy 48, hard 111) through the official harness
   and print a summary per tier. On an Air this takes 10–30 minutes; the hard tier has 4k-token states.
5. Stop the server.

Results land in `runs/jevbench/smoke-kev-0.8b-mac/`. Each tier has `summary.json` (accuracy, ECE,
latency) and `results.jsonl` (one line per item: predicted, correct, probabilities).

## 4. What "good" looks like

The board lists Kev-0.8B at public accuracy 49.4% with the self-hosted latency adjustment. Your
accuracies should be close to that per tier (easy high, hard well under 50%); your latencies will be
higher because this is a laptop. If accuracy is wildly off (e.g. near chance on easy), something in the
serving path is wrong and we fix it before anything else.

## 4b. The Malkuth row — the bar we are clearing

Same script, different checkpoint. This is the current #1 at ≤2B (`docs/MALKUTH.md`), served by the same
Kev code, so it runs on your Mac too:

```bash
KEV_RUN=dhtocks/malkuth-2b scripts/smoke_mac.sh malkuth-2b-mac
```

Downloads another ~4.5 GB (the Qwen3.8-2B-Distill base + the adapter). Expect public accuracy near 69.7%.
Memory: Kev folds the adapter into the base while loading, which briefly holds two copies, so the 2B peaks
around 8–9 GB. On a 16 GB or 24 GB Air this is fine. On an 8 GB Air it may be killed — if so, skip this row
on the Mac; it becomes the first thing we run on the first cloud box in Step 2. Either way, keep the
`runs/jevbench/malkuth-2b-mac/` directory: every later checkpoint is compared against it.

## 5. Send back

Paste the last ~25 lines the script printed for each tier (or attach the three `summary.json` files)
for both rows (Kev-0.8B and, if it ran, Malkuth-2B), plus the output of:

```bash
sysctl -n machdep.cpu.brand_string; sysctl -n hw.memsize | awk '{print $1/1073741824 " GB"}'
```

so the 2B plan is sized to your machine.

## If something breaks

- **Server died / `runs/serve-8009.log` shows an MLX error**: run
  `cd third_party/kev && uv sync --extra serve` again, then `uv run --extra serve python -c "import mlx_lm; print(mlx_lm.__version__)"`.
- **`uv sync` complains about Python 3.14**: `cd third_party/kev && uv python install 3.13 && uv sync --extra serve --python 3.13`.
- **Download stalls**: Hugging Face anonymous downloads sometimes throttle; `hf auth login` with a free
  account and rerun.
- **Port 8009 busy**: `PORT=8010 scripts/smoke_mac.sh`.
- **You want it faster**: `scripts/run_jevbench.sh` runs one tier at a time if you edit the loop, but the
  full run is the point of this step; let it finish once.

Next: Step 2 (accounts, pin the 2B base, a 2-minute T4 smoke on Modal). Don't start it until the
summaries from this step look right.
