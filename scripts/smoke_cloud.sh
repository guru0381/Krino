#!/usr/bin/env bash
# End-to-end smoke test with no local GPU: serve a checkpoint on Modal, send one request by hand, run the 231 public
# JevBench items through the official harness from this box, then stop the endpoint. A few cents of Modal credit each.
#
#   scripts/smoke_cloud.sh                                  # Kev-0.8B, the sanity floor
#   scripts/smoke_cloud.sh dhtocks/malkuth-2b malkuth2b     # the bar we are clearing
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${1:-jaredpalmer/kev-0.8b}"
NAME="${2:-kev08b}"
ENVF="runs/endpoints/$NAME.env"

scripts/serve_modal.sh "$MODEL" "$NAME"
# shellcheck disable=SC1090
. "$ENVF"

echo "== one request by hand"
curl -sL "$ENDPOINT/v1/systemone" -H "authorization: Bearer $KEV_API_KEY" -H 'content-type: application/json' -d '{
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
scripts/run_jevbench.sh "smoke-$NAME" "$ENVF"

scripts/serve_modal.sh stop "$NAME"
echo "results: runs/jevbench/smoke-$NAME/"
