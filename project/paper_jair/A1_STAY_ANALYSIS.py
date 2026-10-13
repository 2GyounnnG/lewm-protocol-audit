"""Zero-GPU A1: stay/leave analysis from sealed Step4 full-budget trajectories."""
import csv, json, hashlib, datetime, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
W=ROOT/'d1_execution/step4/resume_01/remote_sync/FINAL_RESULTS'
LAUNCH=json.loads((W/'FORMAL_LAUNCH_RECEIPT.json').read_text())
SPECS=LAUNCH['condition_specs']
OUT=Path(__file__).resolve().parent/'a1_results'; OUT.mkdir(exist_ok=True)
TASKS=['reacher','pusht','tworoom','cube']; STREAMS=['R3_ORIGINAL','R4_ALT_CEM_1','R4_ALT_CEM_2']
MODELS=[('LeWM_h1','LeWM',1,30),('LeWM_h3','LeWM',3,30),('M01_h1','M01',1,30),('M03_h1','M03',1,30),('M07_h1','M07',1,30)]

def conds(model,task,h,it):
    return [(cid,s) for cid,s in SPECS.items() if s['model']==model and s['task']==task and int(s['history'])==h and int(s['iterations'])==it and s['status']=='PASS']

def case_ids(task):
    d=json.loads((W/'cases/HELDOUT_CASES_V2.json').read_text())['tasks'][task]
    return [x['case_id'] for x in d]

def load_success(cid,s,case,stream):
    if s['model']=='LeWM':
        p=W/'formal'/cid/case/stream/'trajectory.npz'; z=np.load(p); return z['successes'].astype(float)
    p=W/'formal'/cid/stream/f'{case}.json'; d=json.loads(p.read_text())
    return np.array([x['success'] for x in d['steps']],dtype=float)

def mean_seed_arrays(model,task,h,it):
    cs=conds(model,task,h,it); assert cs, (model,task,h,it)
    out=[]
    for case in case_ids(task):
      for stream in STREAMS:
        arrays=[load_success(cid,s,case,stream) for cid,s in cs]
        out.append((case,stream,np.mean(arrays,axis=0),len(arrays)))
    return out

def rows_for(model_label,model,task,h,it):
    rows=[]
    for case,stream,a,nseed in mean_seed_arrays(model,task,h,it):
        hits=np.flatnonzero(a>0)
        first=int(hits[0]+1) if len(hits) else ''
        post=float(np.mean(a[hits[0]+1:])) if len(hits) and hits[0]+1<len(a) else ('' if not len(hits) else 0.0)
        post_leave=float(1-post) if post!='' else ''
        rows.append(dict(model=model_label,task=task,case_id=case,stream=stream,n_seeds=nseed,first_hit_step=first,post_hit_occupancy=post,post_hit_leave_rate=post_leave,success_any=int(np.any(a>0)),success_block=int(np.any(a[4::5]>0)),success_final=int(a[-1]>0),**{f'step_{i+1}':float(a[i]) for i in range(50)}))
    return rows

allrows=[]; occupancy=[]; group=[]
for label,m,h,it in MODELS:
 for t in TASKS:
  rr=rows_for(label,m,t,h,it); allrows.extend(rr); group.append((label,t,rr))
  mat=np.array([[r[f'step_{i+1}'] for i in range(50)] for r in rr],float)
  for i,v in enumerate(mat.mean(axis=0),1): occupancy.append(dict(model=label,task=t,raw_step=i,occupancy=float(v),n_case_stream=mat.shape[0]))
summary=[]
for label,t,rr in group:
 vals=[float(r['first_hit_step']) for r in rr if r['first_hit_step']!='']
 post=[float(r['post_hit_occupancy']) for r in rr if r['post_hit_occupancy']!='']
 leave=[float(r['post_hit_leave_rate']) for r in rr if r['post_hit_leave_rate']!='']
 any_fail_leave=[r for r in rr if r['success_any']==1 and r['success_final']==0]
 summary.append(dict(model=label,task=t,case_stream_rows=len(rr),any_success_rows=sum(r['success_any'] for r in rr),block_success_rows=sum(r['success_block'] for r in rr),final_success_rows=sum(r['success_final'] for r in rr),first_hit_n=len(vals),first_hit_mean=(float(np.mean(vals)) if vals else ''),first_hit_median=(float(np.median(vals)) if vals else ''),post_hit_n=len(post),post_hit_occupancy_mean=(float(np.mean(post)) if post else ''),post_hit_leave_rate_mean=(float(np.mean(leave)) if leave else ''),hit_but_not_final_rate=(len(any_fail_leave)/sum(r['success_any'] for r in rr) if sum(r['success_any'] for r in rr) else '')))

def write(name,rows):
 fields=[]
 for r in rows:
  for k in r:
   if k not in fields: fields.append(k)
 with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
write('A1_TRAJECTORY_SUMMARY.csv',allrows); write('A1_OCCUPANCY_CURVES.csv',occupancy); write('A1_GROUP_SUMMARY.csv',summary)
manifest={str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.csv')}
meta={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':str(W),'source_launch_sha256':hashlib.sha256((W/'FORMAL_LAUNCH_RECEIPT.json').read_bytes()).hexdigest(),'models':[x[0] for x in MODELS],'tasks':TASKS,'streams':STREAMS,'aggregation':'M07 three training seeds averaged within case and stream; all other models one condition; each full-budget trajectory has 50 raw steps; first hit is first raw step with success>0; post-hit occupancy averages steps after first hit; hit-but-not-final is any-step-success rows with final=0.','files':manifest}
(OUT/'A1_METADATA.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'groups':len(summary),'rows':len(allrows),'occupancy_rows':len(occupancy),'output':str(OUT)},ensure_ascii=False))
