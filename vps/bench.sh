#!/usr/bin/env bash
# Benchmark every model in models/ with llama-bench; append JSONL to evals/bench/.
# Modes: "gpu" (all layers offloaded; skipped on hosts without a GPU backend) and
#        "cpu4" (-ngl 0 -t 4: approximates the 4-vCPU VPS).
# Usage: vps/bench.sh [models_dir]   env: MODES="gpu cpu4" PP=512 TG=128 REPS=3
set -euo pipefail
cd "$(dirname "$0")/.."
dir="${1:-models}"; MODES="${MODES:-gpu cpu4}"; PP="${PP:-512}"; TG="${TG:-128}"; REPS="${REPS:-3}"
host="$(hostname -s)"; out="evals/bench/${host}-$(date +%Y%m%d-%H%M).jsonl"
mkdir -p evals/bench

for m in "$dir"/*.gguf; do
  for mode in $MODES; do
    case "$mode" in
      gpu)  args=(-ngl 99) ;;
      cpu4) args=(-ngl 0 -t 4) ;;
      *) echo "unknown mode $mode" >&2; exit 1 ;;
    esac
    echo ">> $(basename "$m") [$mode]" >&2
    llama-bench -m "$m" -p "$PP" -n "$TG" -r "$REPS" "${args[@]}" -o jsonl \
      | python3 -c "import sys,json
for l in sys.stdin:
  d=json.loads(l); d['mode']='$mode'; d['host']='$host'; print(json.dumps(d))" >> "$out"
  done
done
echo "$out"
