#!/usr/bin/env bash
# Run exp004 end to end as pre-registered in paper/hypothesis_v4r1.md §9,
# and optionally exp003b (paper/hypothesis_v3b.md §6).
#
#   scripts/run_exp004.sh            # gate, calibration, freeze, exp004
#   scripts/run_exp004.sh --exp003b  # also run exp003b afterwards
#
# Needs a local Ollama with qwen2.5-coder:3b pulled. Safe to rerun: each
# main run resumes from its checkpoint, and calibration is skipped if
# results/exp004_calibration.json already exists.
set -euo pipefail
cd "$(dirname "$0")/.."

MODEL=qwen2.5-coder:3b
OLLAMA_URL=${OLLAMA_URL:-http://127.0.0.1:11434}
PY=${PYTHON:-python}

echo "== preflight: Ollama and model"
if ! curl -fsS "$OLLAMA_URL/api/tags" | grep -q "\"$MODEL\""; then
  echo "Ollama at $OLLAMA_URL is not running or $MODEL is not pulled."
  echo "Run: ollama pull $MODEL"
  exit 1
fi

echo "== step 0: harness gate"
$PY -m pytest -q tests/test_experiment_power.py

echo "== step 1: validate candidate pool"
$PY bench/validate_bench.py --strict \
  --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl

if [[ -f results/exp004_calibration.json ]]; then
  echo "== step 2: calibration already done (results/exp004_calibration.json)"
else
  echo "== step 2: calibration (arm N, K=20, seed 20261026)"
  $PY -m forkling experiment run --protocol 2 \
    --bench bench/benchmark_002_proof/FORKLAND-BENCH-002-candidates.jsonl \
    --k 20 --replicates 1 --temperature 0.8 \
    --model "$MODEL" --ollama-url "$OLLAMA_URL" --seed 20261026 --arms N \
    --checkpoint results/exp004_calibration.ckpt.jsonl \
    --resume-from results/exp004_calibration.ckpt.jsonl \
    --out results/exp004_calibration.json
fi

echo "== step 3: freeze FORKLAND-BENCH-002"
if ! $PY scripts/freeze_bench_002.py; then
  echo "Calibration failed the freeze rule: exp004 is deferred (v4r1 §6)."
  echo "Commit results/exp004_calibration.json and report it; do not run the main experiment."
  exit 2
fi
$PY bench/validate_bench.py --strict --bench bench/FORKLAND-BENCH-002.jsonl
echo "Commit results/exp004_calibration.json and bench/FORKLAND-BENCH-002.jsonl now;"
echo "the benchmark is frozen at that commit."

echo "== step 4: exp004 main run"
$PY -m forkling experiment run --protocol 2 \
  --bench bench/FORKLAND-BENCH-002.jsonl \
  --k 10 --replicates 5 --temperature 0.8 \
  --model "$MODEL" --ollama-url "$OLLAMA_URL" --seed 20261025 \
  --arms N,P,I,R \
  --checkpoint results/exp004.ckpt.jsonl \
  --resume-from results/exp004.ckpt.jsonl \
  --out results/exp004.json
$PY scripts/summarize.py results/exp004.json

if [[ "${1:-}" == "--exp003b" ]]; then
  echo "== exp003b"
  $PY bench/validate_bench.py
  $PY -m forkling experiment run --protocol 2 \
    --bench bench/FORKLAND-BENCH-001.jsonl \
    --k 10 --replicates 5 --temperature 0.8 \
    --model "$MODEL" --ollama-url "$OLLAMA_URL" --seed 20261025 \
    --arms N,P,I,R \
    --checkpoint results/exp003b.ckpt.jsonl \
    --resume-from results/exp003b.ckpt.jsonl \
    --out results/exp003b.json
  $PY scripts/summarize.py results/exp003b.json
fi
