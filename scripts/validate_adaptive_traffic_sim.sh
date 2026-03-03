#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

RUNNER="${RUNNER:-bash scripts/in_docker.sh}"
DEMO_SCENARIO="${DEMO_SCENARIO:-synthetic_smoke}"
BENCHMARK_SCENARIO="${BENCHMARK_SCENARIO:-synthetic_100k}"
SEED="${SEED:-42}"
DEMO_TICKS="${DEMO_TICKS:-4}"
BENCHMARK_TICKS="${BENCHMARK_TICKS:-4}"
UI_STREAM_TICKS="${UI_STREAM_TICKS:-4}"

run_step() {
  local label="$1"
  shift
  echo
  echo "[validate] ${label}"
  echo "[validate] command: ${RUNNER} $*"
  ${RUNNER} "$@"
}

echo "[validate] MetroFlow adaptive traffic simulation quickstart smoke"
echo "[validate] root=${ROOT_DIR}"
echo "[validate] runner=${RUNNER}"

run_step \
  "baseline demo smoke" \
  python -m metroflow.demo \
  --scenario "${DEMO_SCENARIO}" \
  --seed "${SEED}" \
  --ticks "${DEMO_TICKS}" \
  --day-type weekday \
  --time-band morning

run_step \
  "unit+integration pytest smoke" \
  python -m pytest -q tests/unit tests/integration

run_step \
  "reproducibility pytest smoke" \
  python -m pytest -q tests/integration/test_us3_reproducibility.py

run_step \
  "benchmark smoke" \
  python -m metroflow.benchmarks.run \
  --scenario "${BENCHMARK_SCENARIO}" \
  --seed "${SEED}" \
  --duration-ticks "${BENCHMARK_TICKS}"

# Quickstart still lists a standalone UI stream server command. The current
# runnable smoke path for packet emission is the demo entrypoint with
# `--ui stream`, which exercises the same stream adapter without a blocking
# server loop.
run_step \
  "ui stream smoke" \
  python -m metroflow.demo \
  --scenario "${DEMO_SCENARIO}" \
  --seed "${SEED}" \
  --ticks "${UI_STREAM_TICKS}" \
  --ui stream \
  --ui-force-snapshot-every 1

echo
echo "[validate] all quickstart smoke commands passed"
