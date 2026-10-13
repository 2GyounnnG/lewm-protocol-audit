#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AP_PYTHON:?Set AP_PYTHON to the independent AP Python executable}"
: "${AP_GPU_SSH_AUTHORIZED:?Run only after author provides SSH}"
"$AP_PYTHON" verify_inputs.py
"$AP_PYTHON" -m anchored_planning evaluate --assets assets.remote.json --task reacher --study main --root protocol_main128 --device cuda:0 --output outputs/main128
