#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AP_PYTHON:?Set AP_PYTHON}"
: "${AP_GPU_SSH_AUTHORIZED:?Run only after author provides SSH}"
# Author must resolve whether the LeWM appendix identities retain offset 24 or use AP offset 150.
[[ -f THREE_SEED_PROTOCOL_APPROVED.json ]] || { echo 'BLOCKED: three-seed protocol decision is pending'; exit 2; }
for seed in 42 43 44; do
  "$AP_PYTHON" -m anchored_planning evaluate --assets assets.remote.json --task reacher --study main --root "protocol_seed${seed}" --device cuda:0 --output "outputs/seed${seed}"
done
