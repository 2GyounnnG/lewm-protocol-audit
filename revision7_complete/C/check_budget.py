import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--profile',type=Path,required=True);p.add_argument('--cache-receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
rows=[json.loads(l) for l in a.profile.read_text().splitlines()];assert len(rows)>=3 and all(r['completed'] for r in rows)
per=[r['elapsed_seconds']/r['decisions'] for r in rows if r['decisions']>0];assert per
cache=json.load(open(a.cache_receipt))['elapsed_seconds']
# Conservatively allow 60 decisions for all 278 planned cases, including the short-offset check.
seconds=2*max(per)*60*278+cache
r={'status':'PASS' if seconds<=6*3600 else 'STOP_ASK_AUTHOR','projected_gpu_hours_upper':seconds/3600,'projection':'2x maximum measured wall seconds/decision * 60 * 278 + full encode-cache wall','profile_rows':len(rows),'cache_seconds':cache,'formal_launch_authorized_by_budget':seconds<=6*3600}
a.output.write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if seconds<=6*3600 else 2)
