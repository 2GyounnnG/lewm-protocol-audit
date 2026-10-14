#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AP_PYTHON:?Set AP_PYTHON}"
: "${AP_GPU_SSH_AUTHORIZED:?Run only after author provides SSH}"
"$AP_PYTHON" -c 'import json; p=json.load(open("THREE_SEED_PROTOCOL_APPROVED.json")); assert p["offset"]==24 and p["budget"]==50; g=json.load(open("THROUGHPUT_GATE.json")); assert g["status"]=="PASS" and g["projected_gpu_hours_upper"]<=6; assert json.load(open("TECH_ENTRY_GATE.json"))["status"]=="PASS"'
"$AP_PYTHON" verify_inputs.py
for seed in 42 43 44; do
  "$AP_PYTHON" gpu_run.py -m anchored_planning evaluate --assets assets.remote.json --task reacher --study main --root "protocol_seed${seed}" --device cuda:0 --output "outputs/appendix/seed${seed}"
done
