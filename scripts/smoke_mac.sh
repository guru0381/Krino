#!/usr/bin/env bash
# End-to-end smoke test on the Mac, no GPU rental, no cost:
#   1. serve Kev-0.8B (Qwen3.5-0.8B-Base + pointer head) on Apple Silicon through MLX
#   2. send one request by hand so you see the response shape
#   3. run the 231 public JevBench items through the official harness
#   4. tear the server down
# First run downloads ~2 GB (base model + adapter). Expect ~1–3 s per decision on an Air
# (long hard-tier states are slower), so the full set takes roughly 10–20 minutes.
set -euo pipefail
cd "$(dirname "$0")/.."
RUN="${KEV_RUN:-jaredpalmer/kev-0.8b}"
PORT="${PORT:-8009}"
NAME="${1:-smoke-$(basename "$RUN")-mac}"
LOG="runs/serve-$PORT.log"
mkdir -p runs

echo "== starting $RUN on :$PORT (MLX) — log: $LOG"
( cd third_party/kev && uv run --extra serve python -m kev.serve --run "$RUN" --port "$PORT" ) >"$LOG" 2>&1 &
SERVER=$!
trap 'echo "== stopping server"; kill $SERVER 2>/dev/null || true' EXIT

for i in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then break; fi
  if ! kill -0 $SERVER 2>/dev/null; then echo "server died; see $LOG"; exit 1; fi
  sleep 5
done
curl -s "http://127.0.0.1:$PORT/v1/models" | head -c 600; echo

echo "== one request by hand"
curl -s "http://127.0.0.1:$PORT/v1/systemone" -H 'content-type: application/json' -d '{
  "state": "Shoes arrived two weeks late and in the wrong size. Also I see two charges on my card.",
  "model": "kev-latest",
  "questions": {
    "department": {"type": "choice", "instructions": "Which team should handle this?",
                   "criteria": {"returns": "Exchanges, refunds, wrong or damaged items",
                                "shipping": "Delivery status, delays, lost packages",
                                "billing": "Charges, invoices, payment problems"}},
    "escalate":   {"type": "noul", "instructions": "Does this need urgent human attention?"},
    "frustration":{"type": "score", "instructions": "How frustrated is the customer?",
                   "criteria": ["Calm", "Frustrated", "Very angry"]}
  }}'; echo

echo "== JevBench public items through the official harness"
scripts/run_jevbench.sh "$NAME" "http://127.0.0.1:$PORT"
