#!/usr/bin/env bash
# Our "unseen datasets" panel. Kev's breadth-v1 lives only in a private mirror (several sources forbid redistribution), so
# we use Malkuth's nine held-out suites instead: datasets neither Kev nor Malkuth trained on, already in Kev's suite
# format (third_party/malkuth/benchmarks/mid). They are copied under Kev's evals/ tree so Modal reads can mount them.
# Evaluation only: each suite keeps its source licence (docs/benchmarks.md in the Malkuth repo).
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=third_party/malkuth/benchmarks/mid
DST=third_party/kev/evals/krino-breadth
for s in belebele sib200 rtp_lx polyguard goemotions ledgar kold laya_apps multi_eurlex; do
  mkdir -p "$DST/$s" && cp "$SRC/$s"/{manifest.json,development.jsonl,test.jsonl} "$DST/$s/"
done
echo "imported $(ls "$DST" | wc -l) suites into $DST:"; ls "$DST"
