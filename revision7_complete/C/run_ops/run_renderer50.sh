#!/bin/bash
set -euo pipefail
cd /workspace/ap_revision7
P=/workspace/ap_revision7/venv_ap_linux/bin/python
"$P" - <<'PY'
import json,time
from pathlib import Path
assert json.load(open('run_ops/PARALLEL_GATE.json'))['status']=='PASS'
assert Path('run_ops/acks/compare_complete.json').exists(),'Base groups must be returned before diagnostics'
rows=[]
for p in Path('outputs/main128').glob('outcomes_*.jsonl'):rows += [json.loads(l) for l in p.read_text().splitlines()]
assert len(rows)==128
per=max(r['elapsed_seconds']/r['decisions'] for r in rows if r['decisions'])
events=[json.loads(l) for l in Path('GPU_BUDGET_LEDGER.jsonl').read_text().splitlines()]
used=sum(e['seconds'] for e in events if e['event']=='end')+sum(json.load(open(f))['gpu_seconds'] for f in Path('run_ops').glob('BATCH_*.json'))
upper=used+2*per*60*25*2
r={'status':'PASS' if upper<=21600 else 'STOP_ASK_AUTHOR','prior_gpu_hours':used/3600,'projected_with_renderer50_gpu_hours_upper':upper/3600,'projection':'prior + 2x worst main seconds/decision *60*25 waves*2 GPUs'}
Path('run_ops/RENDERER50_BUDGET_GATE.json').write_text(json.dumps(r,indent=2));print(r);assert r['status']=='PASS'
PY
MUJOCO_GL=egl PYOPENGL_PLATFORM=egl "$P" run_ops/gpu_batch.py --root protocol_main128 --output outputs/diagnostics/egl50 --workers 2 --limit 50
