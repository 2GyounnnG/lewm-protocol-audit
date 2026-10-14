#!/bin/bash
set -euo pipefail
cd /workspace/ap_revision7
P=/workspace/ap_revision7/venv_ap_linux/bin/python
workers=$("$P" -c 'import json; r=json.load(open("run_ops/PARALLEL_GATE.json")); assert r["status"]=="PASS"; print(r["workers"])')
case "$1" in
main) root=protocol_main128; output=outputs/main128;;
42|43|44) root="protocol_seed$1"; output="outputs/appendix/seed$1";;
*) exit 2;;
esac
"$P" run_ops/gpu_batch.py --root "$root" --output "$output" --workers "$workers"
