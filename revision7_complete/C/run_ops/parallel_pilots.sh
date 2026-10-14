#!/bin/bash
set -euo pipefail
cd /workspace/ap_revision7
P=/workspace/ap_revision7/venv_ap_linux/bin/python
"$P" -c 'import json; assert json.load(open("TECH_ENTRY_GATE.json"))["status"]=="PASS"; assert json.load(open("THROUGHPUT_GATE.json"))["status"]=="PASS"'
"$P" run_ops/gpu_batch.py --root protocol_main128 --output outputs/parallel2 --workers 2 --limit 4
# Four-way failure is retained; selection may fall back to the successful two-way pilot.
set +e
"$P" run_ops/gpu_batch.py --root protocol_main128 --output outputs/parallel4 --workers 4 --limit 4
four_rc=$?
set -e
printf '%s\n' "$four_rc" > run_ops/PILOT_FOUR_EXIT.txt
"$P" run_ops/select_parallelism.py
