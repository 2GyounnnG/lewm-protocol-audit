"""Compare untouched original-AP trace JSON against explicit normalized reference JSONL.
Reference schema: record_id, episode, global_start, global_goal, success,
first_hit_step, actions. No identity fallback or silent success-only comparison.
"""
import argparse,json,csv
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--traces',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--first-n',type=int,default=25);a=p.parse_args()
ref={}
for l in a.reference.read_text().splitlines():
 x=json.loads(l);k=tuple(x[n] for n in ['episode','global_start','global_goal']);assert k not in ref;ref[k]=x
out=[]
for f in sorted(a.traces.rglob('*_clean_gaussian_observed.json')):
 x=json.load(open(f));c=x['compact'];i=c['identity'];k=tuple(i[n] for n in ['episode','global_start','global_goal']);r=ref.get(k)
 row={'record_id':i['record_id'],'identity':str(k),'matched':r is not None}
 if r:
  left=np.asarray(x['actions'],float);right=np.asarray(r['actions'],float);n=min(a.first_n,len(left),len(right));d=np.max(np.abs(left[:n]-right[:n]),axis=1) if n else np.array([])
  row.update(success=c['success'],reference_success=r['success'],first_hit_step=c['primitive_steps'] if c['success'] and not c['prelude']['success'] else 0 if c['success'] else None,reference_first_hit_step=r['first_hit_step'],compared_actions=n,max_action_difference=float(d.max()) if n else None,first_action_difference=int(np.flatnonzero(d>0)[0])+1 if np.any(d>0) else None)
 out.append(row)
a.output.write_text(json.dumps(out,indent=2));print('matched',sum(x['matched'] for x in out),'/',len(out))
