#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-metroflow:rocm}"
CACHE_DIR="${METROFLOW_JAX_CACHE_DIR:-/tmp/metroflow-jax-cache}"
CONTAINER_JAX_CACHE_DIR="${CONTAINER_JAX_CACHE_DIR:-/tmp/metroflow_jax_cache}"
XLA_PYTHON_CLIENT_PREALLOCATE="${XLA_PYTHON_CLIENT_PREALLOCATE:-false}"

mkdir -p "${CACHE_DIR}"

ENV_ARGS=(
  -e "XLA_PYTHON_CLIENT_PREALLOCATE=${XLA_PYTHON_CLIENT_PREALLOCATE}"
  -e "JAX_COMPILATION_CACHE_DIR=${CONTAINER_JAX_CACHE_DIR}"
)

for passthrough in JAX_PLATFORMS HIP_VISIBLE_DEVICES ROCR_VISIBLE_DEVICES; do
  if [[ -n "${!passthrough:-}" ]]; then
    ENV_ARGS+=(-e "${passthrough}=${!passthrough}")
  fi
done

docker run --rm -it \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --ipc=host \
  --shm-size 8G \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  "${ENV_ARGS[@]}" \
  -v "$(pwd):/app" -w /app \
  -v "${CACHE_DIR}:${CONTAINER_JAX_CACHE_DIR}" \
  "${IMAGE}" \
  bash -lc "$*"
