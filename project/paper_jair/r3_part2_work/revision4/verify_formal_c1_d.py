"""Full saved-log audit only: no environment/model imports or execution."""
from pathlib import Path
import json,csv,hashlib,datetime,sys,argparse
import numpy as np
SCRIPT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project-root',type=Path,default=SCRIPT.parents[2])
parser.add_argument('--corrected-experiment',type=Path,default=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/returns/STAGE3_VERIFIED/experiment'))
parser.add_argument('--output-dir',type=Path,default=SCRIPT)
args=parser.parse_args();W=args.output_dir;W.mkdir(parents=True,exist_ok=True);ROOT=args.project_root;S=ROOT/'d1_execution/step4/resume_01';BASE=args.corrected_experiment
NEW=BASE/'formal_verified';OLD=S/'remote_sync/FINAL_RESULTS/formal'
seal=json.loads((ROOT/'paper_jair/r3_part2_work/CORRECTED_RESULTS_SEAL.json').read_text())['files'];oldseal={r['path']:r['sha256'] for r in json.loads((S/'SEAL.json').read_text())['files']}
specs=json.loads((S/'CONDITION_SPECS.json').read_text());cases=json.loads((S/'cases/HELDOUT_CASES_V2.json').read_text())['tasks']['reacher'];streams=['R3_ORIGINAL','R4_ALT_CEM_1','R4_ALT_CEM_2'];inputs={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(p,old=False):
 h=sha(p);want=oldseal[str(p.relative_to(S))] if old else seal[str(p.relative_to(NEW))]
 assert h==want,(p,h,want);inputs[str(p)]=h;return p
def bitwise(a,b):return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()
def state_equal(a,b):return all(np.array_equal(np.asarray(a[k]),np.asarray(b[k])) for k in ['physics.time','qpos','qvel','target_qpos'])
def writecsv(p,rs):
 with p.open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
rows=[];actions_by={};any_by={};end_by={};details=[]
for cid,s in specs.items():
 if s['task']!='reacher':continue
 for c in cases:
  case=c['case_id']
  for stream in streams:
   rel=Path(cid)/case/stream/'result.json' if s['model']=='LeWM' else Path(cid)/stream/(case+'.json')
   n=json.loads(check(NEW/rel).read_text());o=json.loads(check(OLD/rel,True).read_text());r=n['reacher_runtime']
   aa=[];labels=[]
   for base,old in [(NEW,False),(OLD,True)]:
    p=base/rel
    if s['model']=='LeWM':
     with np.load(check(p.with_name('trajectory.npz'),old),allow_pickle=False) as z:
      aa.append(z['raw_actions'].copy());labels.append(z['successes'].astype(bool))
    else:
     aa.append(np.load(check(p.with_name(case+'.actions.npy'),old),allow_pickle=False));labels.append(np.asarray([x['success'] for x in (o if old else n)['steps']],bool))
   a,b=aa;micro=r['micro_steps'];events=np.asarray(r['events'],bool);an=np.asarray(r['step_any_labels'],bool);en=np.asarray(r['step_end_labels'],bool)
   assert len(micro)==100 and a.shape==b.shape==(50,2) and events.shape==(100,) and an.shape==en.shape==(50,)
   states=[r['initial_state']]+[m['after'] for m in micro];times=np.asarray([x['physics.time'] for x in states]);dts=np.diff(times)
   pred=np.asarray([np.all(np.abs(np.asarray(x['state_at_predicate']['qpos'])-np.asarray(x['state_at_predicate']['target_qpos']))<.05) for x in micro])
   oldhits=np.flatnonzero(labels[1]);stop=int(oldhits[0]) if len(oldhits) else 50;inc=stop+1 if stop<50 else 50
   diffs=[i+1 for i in range(inc) if not bitwise(a[i:i+1],b[i:i+1])]
   allstates=states+[m['before'] for m in micro]+[m['state_at_predicate'] for m in micro]+r['physics_steps']
   checks={
    'reset_mismatch':int(not(r['reset_count']==r['reset_calls']==r['dm_reset_calls']==r['initialize_episode_calls']==len(r['reset_events'])==len(r['dm_reset_events'])==len(r['initialize_episode_events'])==1)),
    'internal_reset_events':len(r['internal_reset_events']),
    'pending_resets':sum(m['pending_reset_before'] or m['pending_reset_after'] for m in micro),
    'time_increment_mismatches':int(np.sum((dts<=0)|(np.abs(dts-.02)>1e-12))),
    'target_mismatches':sum(not np.array_equal(x['target_qpos'],states[0]['target_qpos']) for x in allstates),
    'nonfinite_states':sum(not all(np.isfinite(np.asarray(x[k])).all() for k in ['physics.time','qpos','qvel','target_qpos']) for x in allstates),
    'state_chain_mismatches':sum(not state_equal(m['before'],states[i]) for i,m in enumerate(micro)),
    'endpoint_state_mismatches':sum(not state_equal(x,micro[2*i+1]['after']) for i,x in enumerate(r['physics_steps'])),
    'predicate_state_mismatches':sum(not state_equal(x['state_at_predicate'],x['after']) for x in micro),
    'threshold_mismatches':sum(x['state_at_predicate']['qpos_threshold']!=.05 for x in micro),
    'predicate_mismatches':int(np.sum(pred!=events)),
    'or_label_mismatches':int(np.sum(pred.reshape(50,2).any(1)!=an)),
    'end_label_mismatches':int(np.sum(pred.reshape(50,2)[:,1]!=en)),
    'tracker_alias_mismatch':int(r['events']!=r['tracker_events']),
    'action_prefix_mismatch':int(not bitwise(a[:stop],b[:stop])),
    'action_through_hit_mismatch':int(not bitwise(a[:inc],b[:inc])),
    'any_outcome_mismatch':int(bool(an.any())!=bool(labels[1].any())),
   }
   row={'condition':cid,'model':s['model'],'history':s['history'],'cem':s['iterations'],'checkpoint':str(s['train_seed']),'case_id':case,'stream':stream,'prefix_actions':stop,'through_hit_actions':inc,'max_dt_error':float(np.max(abs(dts-.02))),'first_action_difference':diffs[0] if diffs else '',**checks}
   rows.append(row)
   if any(checks.values()):details.append(row)
   if cid in ['D1V2_001','D1V2_002']:
    actions_by[cid,case,stream]=a;any_by[cid,case,stream]=an;end_by[cid,case,stream]=en
 print('audited',cid,len(rows),flush=True)
assert len(rows)==2700
writecsv(W/'C1_RECORD_CHECKS.csv',rows)
summary={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS' if not details else 'FAIL','records':len(rows),'microsteps':len(rows)*100,'environment_steps':len(rows)*50,'records_with_any_failed_check':len(details),'totals':{k:sum(r[k] for r in rows) for k in checks},'actions_before_first_success':sum(r['prefix_actions'] for r in rows),'actions_through_first_success':sum(r['through_hit_actions'] for r in rows),'max_time_increment_error':max(r['max_dt_error'] for r in rows),'physical_replay':False,'time_note':'0.02 s per microstep, 0.04 s per environment step; float tolerance 1e-12','failures':details}
(W/'C1_FULL_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n')
ds=[]
for c in cases:
 case=c['case_id']
 for stream in streams:
  a=actions_by['D1V2_001',case,stream];b=actions_by['D1V2_002',case,stream];diff=[i+1 for i in range(50) if not bitwise(a[i:i+1],b[i:i+1])]
  ds.append({'case_id':case,'stream':stream,'first25_bitwise_identical':bitwise(a[:25],b[:25]),'first_difference_raw_step':diff[0] if diff else '', 'max_abs_first25':float(np.max(abs(a[:25].astype(float)-b[:25].astype(float)))),'first25_OR_identical':np.array_equal(any_by['D1V2_001',case,stream][:25],any_by['D1V2_002',case,stream][:25]),'first25_END_identical':np.array_equal(end_by['D1V2_001',case,stream][:25],end_by['D1V2_002',case,stream][:25]),'h1_step25':bool(end_by['D1V2_001',case,stream][24]),'h3_step25':bool(end_by['D1V2_002',case,stream][24])})
writecsv(W/'D_FIRST25_RECORDS.csv',ds)
d={'utc':summary['utc'],'pairs':len(ds),'first25_action_mismatch_pairs':sum(not r['first25_bitwise_identical'] for r in ds),'first25_OR_mismatch_pairs':sum(not r['first25_OR_identical'] for r in ds),'first25_END_mismatch_pairs':sum(not r['first25_END_identical'] for r in ds),'max_abs_first25':max(r['max_abs_first25'] for r in ds),'first_divergence_steps':sorted(set(r['first_difference_raw_step'] for r in ds if r['first_difference_raw_step']!='')),'h1_step25_pct':100*np.mean([r['h1_step25'] for r in ds]),'h3_step25_pct':100*np.mean([r['h3_step25'] for r in ds]),'scope':'LeWM h1 vs h3 CEM30, all100 cases x3 streams; saved actions only; no new rollout'}
(W/'D_FIRST25_SUMMARY.json').write_text(json.dumps(d,indent=2)+'\n')
(W/'CD_INPUT_SHA256.json').write_text(json.dumps(inputs,indent=2)+'\n')
print(json.dumps({'C1':summary,'D':d},indent=2))
