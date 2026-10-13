from pathlib import Path
import pandas as pd,numpy as np,json,hashlib,importlib.util,datetime
W=Path(__file__).resolve().parent;ROOT=W.parents[2];A=W.parent/'analysis_final';B=W.parent/'paper_assets_final_v2'
s=ROOT/'d1_execution/step1/upload/code/tools/statistics_d1.py';sp=importlib.util.spec_from_file_location('frozen',s);stats=importlib.util.module_from_spec(sp);sp.loader.exec_module(stats)
assert hashlib.sha256(s.read_bytes()).hexdigest()=='58855f7cff9188d6dc0c0f2838f3de6c1a5d6e49793bf0166eabe5a814c6abf3'
for base,name in [(A,'ANALYSIS_MANIFEST.json'),(B,'PAPER_ASSETS_MANIFEST.json')]:
 for f,h in json.loads((base/name).read_text())['outputs'].items():
  if base == B and not f.startswith('data/'): continue  # presentation assets omitted from public derivative
  p=base/f
  if not p.exists():p=Path(f)
  assert hashlib.sha256(p.read_bytes()).hexdigest()==h,p
cases=json.loads((ROOT/'d1_execution/step4/resume_01/cases/HELDOUT_CASES_V2.json').read_text())['tasks']
cm=pd.read_csv(A/'CASE_METRICS.csv');nr=pd.read_csv(B/'data/TERMINAL_RAW_NONREACHER.csv')
ix=np.random.default_rng(20261011).integers(0,100,(5000,100))
def vec(t,m,d):
 ids=[r['case_id'] for r in cases[t]]
 if t=='reacher':q=cm[(cm.version=='corrected')&(cm.model==m)&(cm.iterations==30)&(cm.metric==d)].set_index('case_id')['value']
 else:q=nr[(nr.task==t)&(nr.model==m)].groupby('case_id')[d].mean()
 v=q.reindex(ids).to_numpy();assert v.shape==(100,) and np.isfinite(v).all();return v
def paired(a,b):
 p=stats.paired(a,b,boot=5000,seed=20261011);lo,hi=np.quantile((a-b)[ix].mean(1)*100,[.025,.975]);assert np.allclose([lo,hi],[p['ci95_low_pp'],p['ci95_high_pp']],atol=1e-12,rtol=0);return p
def ci(r):return f"{r['delta_pp']:+.1f} [{r['ci95_low_pp']:+.1f}, {r['ci95_high_pp']:+.1f}]"
rows=[]
for t in ['reacher','pusht']:
 for m in ['LeWM_h3','M01_h1','M03_h1','M07_h1']:
  for d in ['any','final','last10_all']:rows.append(dict(task=t,model=m,metric=d,**paired(vec(t,m,d),vec(t,'LeWM_h1',d))))
pd.DataFrame(rows).to_csv(W/'FIG5_THREE_LABEL_CONTRASTS.csv',index=False)
old=json.loads((W.parent/'revision4/EFFECTIVE_MACROS.json').read_text());table=[];diff=[]
for t,tn in [('reacher','Reacher'),('pusht','PushT'),('tworoom','TwoRoom'),('cube','Cube')]:
 a,b=vec(t,'M03_h1','any'),vec(t,'LeWM_h1','any');af,bf=vec(t,'M03_h1','final'),vec(t,'LeWM_h1','final')
 for d,n,x,y in [('any','Any',a,b),('final','Final',af,bf),('change','Change',af-bf,a-b)]:
  r=dict(task=t,metric=d,macro='APLeWM'+tn+n+'CI',**paired(x,y));table.append(r);before=old[r['macro']];after=ci(r)
  diff.append(dict(task=t,metric=d,old=before,new=after,changed=before!=after))
pd.DataFrame(table).to_csv(W/'TABLE16_UNIFIED_SEED.csv',index=False);(W/'TABLE16_CHANGES.json').write_text(json.dumps(diff,indent=2)+'\n')
r=paired(vec('reacher','LeWM_h3','last10_all'),vec('reacher','M03_h1','last10_all'));(W/'REVERSAL_ALL10.json').write_text(json.dumps(r,indent=2)+'\n')
(W/'ANALYSIS_MANIFEST.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seed':20261011,'bootstrap':5000,'index_sha256':hashlib.sha256(ix.tobytes()).hexdigest(),'statistics_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in W.glob('*.csv')}},indent=2)+'\n')
print(pd.DataFrame(rows).query("metric == 'last10_all'").to_string(index=False));print(json.dumps(diff,indent=2))
