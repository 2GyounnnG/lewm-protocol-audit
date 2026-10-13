from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,importlib.util,datetime
W=Path(__file__).resolve().parent;ROOT=W.parents[2];P=ROOT/'paper_jair/revision3_part2';S=ROOT/'d1_execution/step4/resume_01';A=W.parent/'analysis_final';B=W.parent/'paper_assets_final_v2'
stat=ROOT/'d1_execution/step1/upload/code/tools/statistics_d1.py';mod=importlib.util.spec_from_file_location('frozen',stat);stats=importlib.util.module_from_spec(mod);mod.loader.exec_module(stats)
am=json.loads((A/'ANALYSIS_MANIFEST.json').read_text());bm=json.loads((B/'PAPER_ASSETS_MANIFEST.json').read_text())
for base,manifest in [(A,am),(B,bm)]:
 for f,h in manifest['outputs'].items():
  if base == B and not f.startswith('data/'): continue  # presentation assets omitted from public derivative
  p=base/f
  if not p.exists():p=Path(f)
  assert hashlib.sha256(p.read_bytes()).hexdigest()==h,p
cases=json.loads((S/'cases/HELDOUT_CASES_V2.json').read_text())['tasks'];cm=pd.read_csv(A/'CASE_METRICS.csv');nr=pd.read_csv(B/'data/TERMINAL_RAW_NONREACHER.csv');raw=pd.read_csv(A/'TRAJECTORIES.csv')
indices=np.random.default_rng(20261011).integers(0,100,(5000,100))
def vec(task,model,metric):
 ids=[r['case_id'] for r in cases[task]]
 if task=='reacher':
  q=cm[(cm.version=='corrected')&(cm.model==model)&(cm.iterations==30)&(cm.metric==metric)].set_index('case_id')['value'];v=q.reindex(ids).to_numpy()
 else:
  q=nr[(nr.task==task)&(nr.model==model)];assert len(q) in (300,900)
  v=q.groupby('case_id')[metric].mean().reindex(ids).to_numpy()
 assert v.shape==(100,) and np.isfinite(v).all();return v
rows=[]
for task,left,right in [('reacher','M03_h1','LeWM_h3'),('reacher','M03_h1','LeWM_h1'),('pusht','M03_h1','LeWM_h1'),('pusht','M01_h1','LeWM_h1')]:
 for metric in ['last10_occupancy','last10_all']:
  a,b=vec(task,left,metric),vec(task,right,metric);r=stats.paired(a,b,boot=5000,seed=20261011)
  lo,hi=np.quantile((a-b)[indices].mean(1)*100,[.025,.975]);assert abs(lo-r['ci95_low_pp'])<1e-12 and abs(hi-r['ci95_high_pp'])<1e-12
  rows.append(dict(task=task,left=left,right=right,metric=metric,**r))
pd.DataFrame(rows).to_csv(W/'A_WINDOW_PAIRED_INTERVALS.csv',index=False)
# G: the same fixed indices for Cube's AP any/final/difference-in-differences.
a,b=vec('cube','M03_h1','any'),vec('cube','LeWM_h1','any');af,bf=vec('cube','M03_h1','final'),vec('cube','LeWM_h1','final')
g=[]
for label,x,y in [('any',a,b),('final',af,bf),('change',af-bf,a-b)]:g.append(dict(task='cube',metric=label,**stats.paired(x,y,boot=5000,seed=20261011)))
pd.DataFrame(g).to_csv(W/'G_CUBE_PAIRED_INTERVALS.csv',index=False)
# All selected window values and rankings from the same case vectors.
table=[]
for task in ['reacher','pusht']:
 for model in ['LeWM_h1','LeWM_h3','M01_h1','M03_h1','M07_h1']:
  table.append(dict(task=task,model=model,**{m:float(vec(task,model,m).mean()*100) for m in ['any','final','last10_occupancy','last5_all','last10_all']}))
pd.DataFrame(table).to_csv(W/'A_MAIN_WINDOW_TABLE.csv',index=False)
(W/'A_G_ANALYSIS_MANIFEST.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'bootstrap':5000,'seed':20261011,'indices_sha256':hashlib.sha256(indices.tobytes()).hexdigest(),'statistics_sha256':hashlib.sha256(stat.read_bytes()).hexdigest(),'source_analysis_sha256':hashlib.sha256((A/'ANALYSIS_MANIFEST.json').read_bytes()).hexdigest(),'source_assets_sha256':hashlib.sha256((B/'PAPER_ASSETS_MANIFEST.json').read_bytes()).hexdigest(),'status':'COMPLETE','output_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in W.glob('*INTERVALS.csv')}},indent=2)+'\n')
print(pd.DataFrame(rows)[['task','left','right','metric','delta_pp','ci95_low_pp','ci95_high_pp']].to_string(index=False));print('CUBE',g)
