#!/usr/bin/env bash
# RQ3 temperature-repeat runs for the quantization comparison (qwen Q4 vs Q8).
#
# For mean±std on FRR/TRR, repeat each non-zero temperature with different seeds.
# Scoped to security_swe (66 prompts) to stay ~1.5h. Heuristic classify at run time;
# hybrid re-score afterward with scripts/reclassify.py (same as the main sweep).
# Idempotent: a (model,temp,rep) dir with 66 rows is skipped.
#
#   bash scripts/run_rq3.sh
set -u
cd "$(dirname "$0")/.."

EXPECTED=66
MODELS=(qwen2.5:7b-instruct-q4_K_M qwen2.5:7b-instruct-q8_0)
# "temperature reps"
CONFIGS=("0.0 1" "0.7 3" "1.0 3")

rows_for() { local t="$1"; local n; n=$(ls -dt results/*"$t" 2>/dev/null | head -1); [ -n "$n" ] && [ -f "$n/responses.jsonl" ] && wc -l < "$n/responses.jsonl" || echo 0; }

for m in "${MODELS[@]}"; do
  safe=$(echo "$m" | tr '/:.' '___')
  for cfg in "${CONFIGS[@]}"; do
    set -- $cfg; temp="$1"; reps="$2"
    for rep in $(seq 1 "$reps"); do
      seed=$((40 + rep))
      tagsuffix="rq3-${safe}-t${temp}-r${rep}"
      have=$(rows_for "$tagsuffix")
      if [ "$have" -ge "$EXPECTED" ]; then echo "=== SKIP $tagsuffix ($have rows) ==="; continue; fi
      [ "$have" -gt 0 ] && rm -rf results/*"$tagsuffix"
      echo "=== RQ3 $m temp=$temp rep=$rep seed=$seed ==="
      python -m scripts.run_experiment --models "$m" --datasets security_swe \
        --temperature "$temp" --seed "$seed" --classify heuristic --tag "$tagsuffix" \
        || echo "[warn] $tagsuffix failed"
    done
  done
done
echo "ALL RQ3 DONE"
