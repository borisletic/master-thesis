#!/usr/bin/env bash
# Resumable cross-model + RQ3 over-refusal sweep.
#
# Runs each model on XSTest + security_swe with heuristic classification, one run
# dir per model (results/*-sweep-<model>). Idempotent: a model whose dir already
# has EXPECTED_ROWS responses is skipped, so re-launching after an interruption
# continues where it left off. Partial dirs are removed and re-run.
#
#   bash scripts/run_sweep.sh
set -u
cd "$(dirname "$0")/.."

EXPECTED_ROWS=516   # 450 xstest + 66 security_swe
MODELS=(
  mistral:latest
  llama3.1:8b-instruct-q4_K_M
  gemma2:9b-instruct-q4_K_M
  phi3.5:3.8b-mini-instruct-q4_0
  qwen2.5:7b-instruct-q4_K_M
  qwen2.5:7b-instruct-q8_0
)

rows_for() {  # newest complete/partial dir row count for a model tag
  local safe="$1" newest
  newest=$(ls -dt results/*sweep-"$safe" 2>/dev/null | head -1)
  [ -n "$newest" ] && [ -f "$newest/responses.jsonl" ] && wc -l < "$newest/responses.jsonl" || echo 0
}

for m in "${MODELS[@]}"; do
  safe=$(echo "$m" | tr '/:.' '___')
  have=$(rows_for "$safe")
  if [ "$have" -ge "$EXPECTED_ROWS" ]; then
    echo "=== SKIP (complete, $have rows): $m ==="
    continue
  fi
  if [ "$have" -gt 0 ]; then
    echo "=== REDO (partial $have rows): $m ==="
    rm -rf results/*sweep-"$safe"
  fi
  echo "=== SWEEP MODEL: $m ==="
  python -m scripts.run_experiment --models "$m" --datasets xstest security_swe \
    --classify heuristic --tag "sweep-$safe" || echo "[warn] $m run failed"
done
echo "ALL SWEEP DONE"
