#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AP_PYTHON:?Set AP_PYTHON to the independent AP Python executable}"
: "${AP_GPU_SSH_AUTHORIZED:?Run only after author provides SSH}"
"$AP_PYTHON" -c 'import json; g=json.load(open("THROUGHPUT_GATE.json")); assert g["status"]=="PASS" and g["projected_gpu_hours_upper"]<=6'
"$AP_PYTHON" -c 'import json; assert json.load(open("TECH_ENTRY_GATE.json"))["status"]=="PASS"'
"$AP_PYTHON" verify_inputs.py
"$AP_PYTHON" gpu_run.py -m anchored_planning evaluate --assets assets.remote.json --task reacher --study main --root protocol_main128 --device cuda:0 --output outputs/main128
