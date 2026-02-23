#!/usr/bin/env bash
set -euo pipefail

IMAGE="${IMAGE:-metroflow:rocm}"

docker run --rm -it \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --ipc=host \
  --shm-size 8G \
  --cap-add=SYS_PTRACE \
  --security-opt seccomp=unconfined \
  -v "$(pwd):/app" -w /app \
  "${IMAGE}" \
  bash -lc "$*"