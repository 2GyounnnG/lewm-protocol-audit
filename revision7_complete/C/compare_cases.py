"""Strictly separate AP main reproduction from AP appendix recheck."""
import argparse,json
from pathlib import Path
import numpy as np
W=Path(__file__).resolve().parent
def analyze(traces,group,reference=None,first_n=25):
 seeds=[None] if group=='main' else [42,43,44]
 horizon,budget=(150,300) if group=='main' else (24,50)
 if group=='appendix' and reference is not None:raise ValueError('Appendix cannot use main/paper reference')
 expected={}
 for seed in seeds:
  root='protocol_main128' if seed is None else f'protocol_seed{seed}'
  p=json.load(open(W/root/'protocols/main.json'))
  for r in p['studies']['reacher']['confirm']:
   k=(seed,r['episode'],r['global_start'],r['global_goal']);assert k not in expected;expected[k]=r['record_id']
 refs={}
 if group=='main':
  if reference is None:raise ValueError('Main requires the SHA-verified original128 reference')
  for line in reference.read_text().splitlines():
   r=json.loads(line);k=(None,r['episode'],r['global_start'],r['global_goal']);assert k not in refs;refs[k]=r
  assert set(refs)==set(expected),'Reference cohort mismatch'
 rows={}
 for f in sorted(traces.rglob('*_clean_gaussian_observed.json')):
  x=json.load(open(f));c=x['compact'];i=c['identity'];seed=None if group=='main' else int(i['sample_seed'])
  k=(seed,i['episode'],i['global_start'],i['global_goal'])
  assert k in expected and k not in rows,('Unexpected/duplicate identity',k)
  assert i['record_id']==expected[k]
  assert c['completed'] and c['horizon']==horizon and c['budget']==budget and i['global_goal']-i['global_start']==horizon,'Wrong group protocol'
  actions=np.asarray(x['actions'],float).reshape(-1,2)
  assert np.isfinite(actions).all() and len(actions)==c['primitive_steps']<=budget
  hit=0 if c['success'] and c['prelude']['success'] else c['primitive_steps'] if c['success'] else None
  row=dict(group=group,seed=seed,record_id=i['record_id'],episode=i['episode'],global_start=i['global_start'],global_goal=i['global_goal'],success=c['success'],first_hit_step=hit,first_actions=actions[:first_n].tolist())
  if group=='main':
   r=refs[k];right=np.asarray(r['actions'],float).reshape(-1,2);n=min(first_n,len(actions),len(right));d=np.max(np.abs(actions[:n]-right[:n]),axis=1) if n else np.array([])
   row.update(reference_success=r['success'],reference_first_hit_step=r['first_hit_step'],compared_actions=n,max_action_difference=float(d.max()) if n else None,first_action_difference=int(np.flatnonzero(d>0)[0])+1 if np.any(d>0) else None)
  rows[k]=row
 assert set(rows)==set(expected),f'Incomplete {group}: {len(rows)}/{len(expected)}'
 out={'group':group,'label':'AP 主表协议' if group=='main' else 'AP 附录复核','horizon':horizon,'budget':budget,'paper_comparator_pct':75.8 if group=='main' else None,'cases':list(rows.values())}
 out['per_seed']=[{'seed':seed,'n':sum(k[0]==seed for k in rows),'successes':sum(r['success'] for k,r in rows.items() if k[0]==seed),'success_pct':100*np.mean([r['success'] for k,r in rows.items() if k[0]==seed])} for seed in seeds]
 if group=='main':out['delta_from_paper_reported_pp']=out['per_seed'][0]['success_pct']-75.8
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--group',choices=['main','appendix'],required=True);p.add_argument('--traces',type=Path,required=True);p.add_argument('--reference',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--first-n',type=int,default=25);a=p.parse_args();r=analyze(a.traces,a.group,a.reference,a.first_n);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(r['label'],len(r['cases']),r['per_seed'])
