#!/bin/bash
set -euo pipefail
cd /workspace/ap_revision7
P=/workspace/ap_revision7/venv_ap_linux/bin/python
"$P" - <<'CHECK'
import json
from pathlib import Path
events=[json.loads(l) for l in Path('GPU_BUDGET_LEDGER.jsonl').read_text().splitlines()]
used=sum(e['seconds'] for e in events if e['event']=='end')+sum(json.load(open(f))['gpu_seconds'] for f in Path('run_ops').glob('BATCH_*.json'))
assert used<21000, 'Insufficient headroom for optional reset-image checks'
CHECK
# Count both tiny renderer checks in the cumulative GPU ledger conservatively.
MUJOCO_GL=osmesa PYOPENGL_PLATFORM=osmesa "$P" gpu_run.py run_ops/render_probe.py
MUJOCO_GL=egl PYOPENGL_PLATFORM=egl "$P" gpu_run.py run_ops/render_probe.py
