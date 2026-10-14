"""Saved-record-only threshold/window analysis, no model/environment imports."""
from pathlib import Path
import hashlib,json,csv,importlib.util,datetime
import numpy as np
W=Path(__file__).resolve().parent;ROOT=W.parents[3];S4=ROOT/'d1_execution/step4/resume_01';WORK=W.parents[1]
sealpath=WORK/'CORRECTED_RESULTS_SEAL.json';seal=json.load(open(sealpath));R=Path(seal['root']);oldseal={x['path']:x['sha256'] for x in json.load(open(S4/'SEAL.json'))['files']}
inputs={}
def read(p,corrected=False):
 p=Path(p);b=p.read_bytes();h=hashlib.sha256(b).hexdigest();rel=p.relative_to(R if corrected else S4).as_posix()
 assert h==(seal['files'][rel] if corrected else oldseal[rel]),p
 inputs[str(p)]=h;return json.loads(b) if p.suffix=='.json' else p
cases=read(S4/'cases/HELDOUT_CASES_V2.json')['tasks'];streams=['R3_ORIGINAL','R4_ALT_CEM_1','R4_ALT_CEM_2'];ks=[5,10,15,20];ths=[.03,.05,.08]
statsfile=ROOT/'d1_execution/step1/upload/code/tools/statistics_d1.py';spec=importlib.util.spec_from_file_location('sealed_stats',statsfile);stats=importlib.util.module_from_spec(spec);spec.loader.exec_module(stats)
inputs[str(statsfile)]=hashlib.sha256(statsfile.read_bytes()).hexdigest()
indices=np.random.default_rng(20261011).integers(0,100,(5000,100));rows=[];vectors={};coverage=[];rtdata={}
def add(task,comparison,threshold,metric,k,a,b):
 d=a.mean(axis=1)-b.mean(axis=1);out=stats.paired(a,b,boot=5000,seed=20261011)
 lo,hi=np.quantile(d[indices].mean(1)*100,[.025,.975]);assert np.allclose([lo,hi],[out['ci95_low_pp'],out['ci95_high_pp']],atol=1e-12,rtol=0)
 rows.append(dict(task=task,comparison=comparison,threshold=threshold,window=k,metric=metric,status='COMPUTED',delta_pp=out['delta_pp'],ci95_low_pp=lo,ci95_high_pp=hi,contains_zero=bool(lo<=0<=hi),n_cases=100,streams=3))
 vectors[f'{task}_{comparison}_{threshold}_{metric}_{k}']=d
for model,cid in [('LeWM_h3','D1V2_002'),('AP','D1V2_010')]:
 labels=np.zeros((3,100,3,50),bool);anylabels=np.zeros((3,100,3),bool);savedany=np.zeros((100,3),bool)
 for ci,c in enumerate(cases['reacher']):
  for si,stream in enumerate(streams):
   p=R/cid/c['case_id']/stream/'result.json' if model=='LeWM_h3' else R/cid/stream/(c['case_id']+'.json')
   j=read(p,True);rt=j['reacher_runtime'];assert j['status']=='COMPLETE' and j['executed_raw_steps']==50
   assert rt['reset_count']==1 and not rt['internal_reset_events'] and len(rt['env_steps'])==50 and len(rt['micro_steps'])==100
   end=np.array([np.abs(np.array(e['state']['qpos'])-np.array(e['state']['target_qpos'])) for e in rt['env_steps']])
   micro=np.array([np.abs(np.array(e['state_at_predicate']['qpos'])-np.array(e['state_at_predicate']['target_qpos'])) for e in rt['micro_steps']])
   for ti,t in enumerate(ths):labels[ti,ci,si]=(end<t).all(1);anylabels[ti,ci,si]=(micro<t).all(1).any()
   assert np.array_equal(labels[1,ci,si],rt['step_end_labels'])
   savedany[ci,si]=bool(j['success_any']);assert savedany[ci,si]==anylabels[1,ci,si]
 rtdata[model]=(labels,anylabels,savedany)
 coverage.append(dict(task='reacher',model=model,trajectories=300,steps_with_state=15000,microsteps_with_state=30000))
for ti,t in enumerate(ths):
 a,aa,sa=rtdata['LeWM_h3'];b,ba,sb=rtdata['AP'];comp='LeWM_h3_minus_AP'
 add('reacher',comp,t,'any_original_OR',0,sa,sb);add('reacher',comp,t,'any_rethresholded_OR',0,aa[ti],ba[ti]);add('reacher',comp,t,'final_END',1,a[ti,:,:,-1],b[ti,:,:,-1])
 for k in ks:
  add('reacher',comp,t,'all_window_END',k,a[ti,:,:,-k:].all(2),b[ti,:,:,-k:].all(2))
  add('reacher',comp,t,'mean_window_END',k,a[ti,:,:,-k:].mean(2),b[ti,:,:,-k:].mean(2))
pdata={};state_fields_seen=set()
for model,cid in [('LeWM_h1','D1V2_003'),('AP','D1V2_015'),('Fast_LeWM','D1V2_014')]:
 a=np.zeros((100,3,50),bool)
 for ci,c in enumerate(cases['pusht']):
  for si,stream in enumerate(streams):
   root=S4/'remote_sync/FINAL_RESULTS/formal'/cid
   p=root/c['case_id']/stream/'result.json' if model=='LeWM_h1' else root/stream/(c['case_id']+'.json')
   j=read(p);assert j['status']=='COMPLETE' and j['executed_raw_steps']==50
   if model=='LeWM_h1':
    q=read(p.with_name('trajectory.npz'))
    with np.load(q) as z:
     state_fields_seen.update(z.files);a[ci,si]=z['successes']
   else:
    assert len(j['steps'])==50
    for e in j['steps']:state_fields_seen.update(e.keys())
    a[ci,si]=[e['success'] for e in j['steps']]
   assert a[ci,si].any()==j['success_any'] and a[ci,si,-1]==j['success_final']
 pdata[model]=a;coverage.append(dict(task='pusht',model=model,trajectories=300,steps_with_saved_labels=15000,steps_with_physical_state=0))
for model in ['AP','Fast_LeWM']:
 comp=model+'_minus_LeWM_h1';a=pdata[model];b=pdata['LeWM_h1']
 add('pusht',comp,20,'any_original_OR',0,a.any(2),b.any(2));add('pusht',comp,20,'final_END',1,a[:,:,-1],b[:,:,-1])
 for k in ks:
  add('pusht',comp,20,'all_window_END',k,a[:,:,-k:].all(2),b[:,:,-k:].all(2));add('pusht',comp,20,'mean_window_END',k,a[:,:,-k:].mean(2),b[:,:,-k:].mean(2))
 for t in [15,25]:
  for k in ks:
   for metric in ['all_window_END','mean_window_END']:
    rows.append(dict(task='pusht',comparison=comp,threshold=t,window=k,metric=metric,status='NOT_ESTIMABLE_NO_SAVED_STATE',delta_pp=None,ci95_low_pp=None,ci95_high_pp=None,contains_zero=None,n_cases=100,streams=3))
with (W/'SENSITIVITY_CONTRASTS.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
np.savez_compressed(W/'CASE_DIFFERENCES.npz',**vectors)
receipt=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='COMPLETE_WITH_EXPLICIT_PUSHT_THRESHOLD_UNAVAILABILITY',bootstrap_function=str(statsfile),bootstrap_replicates=5000,seed=20261011,index_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),all_intervals_verified_against_common_index_vector=True,coverage=coverage,pusht_saved_fields=sorted(state_fields_seen),input_files=inputs,corrected_seal_sha256=hashlib.sha256(sealpath.read_bytes()).hexdigest(),existing_values_changed=False,new_experiments=False)
(W/'ANALYSIS_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
for r in rows:
 if r['status']=='COMPUTED' and r['metric'] in ['final_END','all_window_END']:
  print(r['task'],r['comparison'],r['threshold'],r['metric'],r['window'],f"{r['delta_pp']:+.2f} [{r['ci95_low_pp']:+.2f}, {r['ci95_high_pp']:+.2f}]")
