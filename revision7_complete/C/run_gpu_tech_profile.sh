#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AP_PYTHON:?Set independent Linux AP Python}"
: "${AP_GPU_SSH_AUTHORIZED:?Author SSH required}"
"$AP_PYTHON" verify_inputs.py
"$AP_PYTHON" -m anchored_planning inspect-assets --task reacher --assets assets.remote.json
"$AP_PYTHON" gpu_run.py -m anchored_planning evaluate --task reacher --assets assets.remote.json --device cuda:0 --root protocol_main128 --study main --limit 3 --output outputs/tech_profile
"$AP_PYTHON" validate_tech_entry.py
"$AP_PYTHON" check_budget.py --profile outputs/tech_profile/outcomes_reacher_shard0of1.jsonl --cache-receipt assets/cache/reacher.json --output THROUGHPUT_GATE.json
