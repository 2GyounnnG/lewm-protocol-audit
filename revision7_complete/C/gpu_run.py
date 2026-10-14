"""Cumulative six-hour command-wall budget for this single-GPU AP experiment."""
import os,sys,json,time,subprocess,uuid
from pathlib import Path
W=Path(__file__).resolve().parent
assert os.environ.get('AP_GPU_SSH_AUTHORIZED'),'Author SSH required'
ledger=W/'GPU_BUDGET_LEDGER.jsonl';events=[json.loads(x) for x in ledger.read_text().splitlines()] if ledger.exists() else []
starts={e['id'] for e in events if e['event']=='start'};ends={e['id'] for e in events if e['event']=='end'}
assert starts==ends,'Unfinished prior command; inspect process and reconcile actual time before resuming'
used=sum(e['seconds'] for e in events if e['event']=='end');remaining=6*3600-used
assert remaining>0,'STOP: six GPU-hour budget exhausted'
ident=str(uuid.uuid4());command=[sys.executable]+sys.argv[1:];begin=time.monotonic()
def log(e):
 with ledger.open('a') as f:f.write(json.dumps(dict(id=ident,**e))+'\n');f.flush()
log({'event':'start','utc_epoch':time.time(),'command':command,'remaining_seconds':remaining})
code=1
try:
 code=subprocess.run(command,cwd=W,timeout=remaining).returncode
except subprocess.TimeoutExpired:code=124
finally:log({'event':'end','seconds':time.monotonic()-begin,'returncode':code})
raise SystemExit(code)
