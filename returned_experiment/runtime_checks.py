from __future__ import annotations
import os, json, glob, hashlib, time, traceback
os.environ['MUJOCO_GL']='egl'; os.environ['CUDA_VISIBLE_DEVICES']=''
import numpy as np
from pathlib import Path
from stable_worldmodel.envs.dmcontrol.reacher import ReacherDMControlWrapper
from stable_worldmodel.envs.pusht.env import PushT
from stable_worldmodel.envs.two_room.env import TwoRoomEnv
from stable_worldmodel.envs.ogbench.cube_env import CubeEnv
from REVISION_3_REACHER_PATCH import install_nonterminating_reacher
ROOT=Path('/workspace/d1'); W=ROOT/'step4/resume_03_reacher'
def arr(x): return np.asarray(x,dtype=np.float64).copy()
def cont_reacher(patched):
    e=ReacherDMControlWrapper(task='qpos_match',seed=0); e.reset(seed=0)
    e.env.task.target_qpos=e.env.physics.data.qpos.copy()
    tracker=None
    if patched: tracker=install_nonterminating_reacher(e)
    reset_count=0; native_reset=e.reset
    def counted(*a,**k):
        nonlocal reset_count
        reset_count+=1; return native_reset(*a,**k)
    e.reset=counted
    ts=[]; qs=[]; terms=[]
    action=np.zeros(e.action_space.shape,np.float32)
    for _ in range(3):
        before=float(e.env.physics.time()); r=e.step(action); after=float(e.env.physics.time())
        ts.append([before,after]); qs.append(e.env.physics.data.qpos.copy().tolist()); terms.append(bool(r[2]))
    return {'patched':patched,'terminated_flags':terms,'times':ts,'qpos':qs,'reset_calls_after_initial':reset_count,'pending_reset':bool(getattr(e.env,'_reset_next_step',False)),'tracker_events':None if tracker is None else len(tracker.events),'internal_reset_events':None if tracker is None else tracker.internal_reset_events,'pass': (not patched and terms[0] and terms[1] is False) or (patched and not any(terms) and reset_count==0 and all(ts[i][1] > ts[i][0] for i in range(3)) and not tracker.internal_reset_events)}
def cont_pusht():
    e=PushT(render_mode='rgb_array'); e.reset(seed=0); s=e._get_obs().copy(); e._set_goal_state(s); e.goal_state=s.copy(); a=np.zeros(2,np.float32); out=[]; states=[]
    for _ in range(3):
        r=e.step(a); out.append(bool(r[2])); states.append(e._get_obs().copy().tolist())
    return {'terminated_flags':out,'state_continuous':all(np.allclose(states[i],states[0]) for i in range(3)),'pass':all(out) and all(np.allclose(states[i],states[0]) for i in range(3))}
def cont_tworoom():
    e=TwoRoomEnv(render_mode='rgb_array'); e.reset(seed=0); e.target_position=e.agent_position.clone(); a=np.zeros(2,np.float32); out=[]; states=[]
    for _ in range(3):
        r=e.step(a); out.append(bool(r[2])); states.append(np.asarray(r[0]).copy())
    return {'terminated_flags':out,'state_continuous':all(np.allclose(states[i],states[0]) for i in range(3)),'pass':all(out) and all(np.allclose(states[i],states[0]) for i in range(3))}
def cont_cube():
    e=CubeEnv(env_type='single',ob_type='states',permute_blocks=True,multiview=False,height=64,width=64); e.reset(seed=0)
    for i in range(e._num_cubes):
        obj=e._data.joint(f'object_joint_{i}').qpos[:3].copy(); e._data.mocap_pos[e._cube_target_mocap_ids[i]]=obj
    a=np.zeros(e.action_space.shape,np.float32); out=[]; times=[]
    for _ in range(3):
        r=e.step(a); out.append(bool(r[2])); times.append(float(np.asarray(r[4]['time']).ravel()[0]))
    return {'terminated_flags':out,'times':times,'state_continuous':all(times[i]>times[i-1] for i in range(1,len(times))),'success_predicate':list(map(bool,e._compute_successes())),'pass':all(out) and all(times[i]>times[i-1] for i in range(1,len(times)))}
def replay():
    cases={x['case_id']:x for x in json.loads((W/'cases/tech_reacher.json').read_text())}
    paths=glob.glob(str(W/'replay_evidence/all/**/trajectory.npz'),recursive=True)
    chosen=None; chosen_first=10**9
    for p in paths:
        if '/R3_ORIGINAL/' not in p: continue
        z=np.load(p,allow_pickle=True); n=len(z['raw_actions']); ss=np.asarray(z['successes']).astype(bool)
        if n>=50 and ss.any():
            cid=next((c for c in cases if c in p),None); first=int(np.flatnonzero(ss)[0]) if ss.any() else 10**9
            if cid and first < chosen_first: chosen=(p,cid,z); chosen_first=first
    if chosen is None: raise RuntimeError('no 50-step recorded trajectory')
    p,cid,z=chosen; c=cases[cid]; actions=np.asarray(z['raw_actions'])[:50].astype(np.float32); recorded=np.asarray(z['successes']).astype(bool)[:50]
    state=np.r_[c['reset_metadata']['start']['qpos'],c['reset_metadata']['start']['qvel']].astype(np.float64); target=np.asarray(c['reset_metadata']['goal']['qpos'],np.float64)
    def run(patched):
        e=ReacherDMControlWrapper(task='qpos_match',seed=int(c.get('reset_seed',0))); e.reset(seed=int(c.get('reset_seed',0)),options={'state':state}); e.env.task.target_qpos=target.copy(); tracker=install_nonterminating_reacher(e) if patched else None
        obs=[]; terms=[]; times=[]
        for a in actions:
            r=e.step(a); terms.append(bool(tracker.consume_step()) if tracker else bool(r[2])); times.append(float(e.env.physics.time()))
        return np.asarray(terms),times,tracker
    orig,ot,_=run(False); pat,pt,tr=run(True); first=int(np.flatnonzero(recorded)[0]) if recorded.any() else None
    pre_end=first if first is not None else 50
    return {'trajectory':p,'case_id':cid,'n_actions':50,'recorded_success_count':int(recorded.sum()),'original_match_rate':float(np.mean(orig==recorded)),'patched_match_rate':float(np.mean(pat==recorded)),'original_pre_success_match_rate':float(np.mean(orig[:pre_end]==recorded[:pre_end])) if pre_end else None,'patched_pre_success_match_rate':float(np.mean(pat[:pre_end]==recorded[:pre_end])) if pre_end else None,'first_recorded_success_index':first,'patched_post_success_disagreement':None if first is None else int(np.sum(pat[first:]!=recorded[first:])),'original_times_monotonic':bool(np.all(np.diff(ot)>0)),'patched_times_monotonic':bool(np.all(np.diff(pt)>0)),'patched_internal_resets':tr.internal_reset_events}
def main():
    out={'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'cpu_only':True,'four_environment_continuation':{},'reacher_replay':None,'errors':[]}
    for name,fn in [('reacher_original',lambda:cont_reacher(False)),('reacher_patched',lambda:cont_reacher(True)),('pusht',cont_pusht),('tworoom',cont_tworoom),('cube',cont_cube)]:
        try: out['four_environment_continuation'][name]=fn()
        except Exception as e: out['four_environment_continuation'][name]={'pass':False,'error':repr(e),'traceback':traceback.format_exc()}; out['errors'].append(name)
    try: out['reacher_replay']=replay()
    except Exception as e: out['errors'].append('replay'); out['reacher_replay']={'pass':False,'error':repr(e),'traceback':traceback.format_exc()}
    out['status']='PASS' if not out['errors'] and out['four_environment_continuation']['reacher_patched']['pass'] and out['reacher_replay'].get('patched_internal_resets')==[] else 'FAIL'
    (W/'runtime_checks.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__': main()
