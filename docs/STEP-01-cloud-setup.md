# Step 1 — Cloud setup and the first end-to-end run (no laptop needed)

Everything from here on runs in a browser. Your computer only needs a browser tab.

Two services, both free to start:

| | What it does for us | Free tier | Paid |
|---|---|---|---|
| **GitHub Codespaces** | the always-on dev box: code, data building, the eval harness, git. A full VS Code in the browser. | 120 core-hours/month (30 h of a 4-core box), 15 GB | $0.36/h for 4 cores if you run out |
| **Modal** | every GPU job: serving checkpoints for evaluation, and training (Kev's trainer is built for it). Scales to zero when idle. | $30 of compute per month | L4 ~$0.80/h, L40S ~$1.95/h, H100 ~$3.95/h |

Why not a GPU dev box (RunPod, Lambda)? You pay while it sits idle, and you lose the environment when you stop it.
Codespaces persists for free; Modal bills by the second and only while something runs. Lightning AI Studio is a fine
alternative to Codespaces if you'd rather have a box you can attach a GPU to directly; `scripts/setup_linux.sh` works
there too.

Time: ~20 minutes of clicking, ~30 minutes of waiting. Cost: ~$0.50 of Modal credit, out of the free $30.

## 1. Put the project on GitHub

1. Sign in to github.com, click **New repository**, name it `krino`, keep it private, don't add a README.
2. On the next page choose **uploading an existing file**, drag in the *contents* of `krino.zip` (the folders and files,
   not the zip itself), commit.
   If you'd rather use git: unzip, `cd krino`, `git init && git add -A && git commit -m init`, then the two `git remote
   add` / `git push` lines GitHub shows you.

## 2. Open a Codespace

Repo page → green **Code** button → **Codespaces** tab → **Create codespace on main**.

It builds from `.devcontainer/devcontainer.json`: a 4-core Python 3.13 box that runs `scripts/setup_linux.sh` on first
start (installs uv, fetches Kev, JevBench and Malkuth at their pins, builds Kev's environment, runs the unit tests).
Expect 5–10 minutes the first time; later starts take seconds. When the terminal shows `ok: Linux setup complete`, the
box is ready. If the terminal is empty, open one with **Terminal → New Terminal** and run `scripts/setup_linux.sh`
yourself.

Codespaces stop after 30 idle minutes and keep everything; they are deleted after 30 days unused unless you pin them, so
commit your work (`git add -A && git commit && git push`) as you go.

## 3. Sign in to Modal

```bash
cd third_party/kev && uv run --no-sync modal setup && cd ../..
```

It prints a link; open it, create the account (GitHub sign-in works), approve, and the terminal says it's authenticated.
Modal's starter plan gives $30 of compute a month with no card; adding a card later raises the limits and is needed for
H100s in Step 3.

## 4. The smoke test: Kev-0.8B, the sanity floor

```bash
scripts/smoke_cloud.sh
```

Step by step it will:

1. Deploy Kev-0.8B behind an HTTPS endpoint on an L4 (`scripts/serve_modal.sh`), with a generated bearer key saved in
   `runs/endpoints/kev08b.env`. The first start downloads the weights (~2 GB) into Modal's cache; later starts reuse it.
2. Send one hand-written ticket with three questions and print the JSON. Look at it: a `choice` with per-option
   probabilities, a `noul` probability, a `score` with a legend. That is the contract our model implements.
3. Run the 231 public JevBench items (original 72, easy 48, hard 111) through the official harness, from the Codespace
   against the endpoint, and print a summary per tier. About 5–10 minutes.
4. Stop the endpoint.

Results: `runs/jevbench/smoke-kev08b/{original,easy,hard}/summary.json` and `results.jsonl`.

## 5. The Malkuth row: the bar we are clearing

```bash
scripts/smoke_cloud.sh dhtocks/malkuth-2b malkuth2b
```

Same flow with the current #1 at ≤2B (`docs/MALKUTH.md`). Expect public accuracy near 69.7% (easy ≈ 100%, hard well
under 50%). Keep `runs/jevbench/smoke-malkuth2b/`: every checkpoint we train is compared against it.

## 6. What "good" looks like

The board lists Kev-0.8B at public accuracy 49.4% and Malkuth-2B at 69.7%. Your per-tier accuracies should be close
(easy high, hard well under 50%). Latencies will be higher than the board's because each request crosses the internet
to Modal; that's fine for now, the board measures speed on its own hardware. If accuracy is far off (near chance on
easy, say), the serving path is wrong and we fix it before anything else.

## 7. Send back

Paste the per-tier summary lines for both rows (or the six `summary.json` files), and the Modal usage shown at
modal.com/settings/usage so we know what the two runs cost.

## If something breaks

- **`modal setup` can't open a browser**: it prints the URL; paste it into any browser, then paste the token back.
- **Deploy fails with "no default GPU"**: `scripts/serve_modal.sh` sets `KEV_GPU=L4,L40S`; for a bigger model pass `KEV_GPU=H100`.
- **The first request hangs**: a cold start can take a few minutes; the script already waits up to 15 minutes on `/v1/models`.
- **401 from the harness**: the key in `runs/endpoints/<name>.env` doesn't match the deployed one; `scripts/serve_modal.sh stop <name>`, delete the .env, deploy again.
- **Codespace out of space**: `du -sh third_party/kev/.venv`; the devcontainer asks for 32 GB, which is plenty.
- **You want to see the endpoint from outside**: `curl -L $ENDPOINT/v1/models -H "authorization: Bearer $KEV_API_KEY"`.

Next: Step 2 (Hugging Face token, pin the 2B base, 2-minute T4 smoke of Kev's trainer on Modal).
