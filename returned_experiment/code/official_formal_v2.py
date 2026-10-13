"""D1 V1.2 native-reset bridge with direct reset-state observation. Native model, solver, history and World evaluation.
Only path/asset/case binding and non-mutating instrumentation are new.
"""
import argparse,ast,datetime,functools,hashlib,json,logging,os,sys,time,traceback
from pathlib import Path
os.environ.setdefault('MUJOCO_GL','egl');os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')
import numpy as np
import torch
from torch import nn
import h5py,hdf5plugin
import stable_worldmodel as swm
from stable_worldmodel.planning import ShootingCostEvaluator,GoalMSE
from stable_worldmodel.planning.solver.cem import CEMSolver
from stable_worldmodel.policy import WorldModelPolicy
from adapters.common import sha,seed,tensor_record,PlanMeter,STREAMS,history_indices
from harness_reference.r3.data import image_transform
ROOT=Path('/workspace/d1');WORK=ROOT/'step4/resume_01';UPLOAD=ROOT/'upload'
ASSETS=json.loads((UPLOAD/'HF_ASSETS_MANIFEST.json').read_text())['assets']
CONTRACT=json.loads((UPLOAD/'code/adapters/task_contracts.json').read_text())
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');tmp.replace(p)
def ar(x):return x.detach().cpu().numpy().copy() if torch.is_tensor(x) else np.asarray(x).copy()
def records(task):return [r for r in ASSETS if r['task']==task]
def build_model(task,device):
 from stable_worldmodel.wm.lewm import LeWM
 from stable_worldmodel.wm.lewm.module import Embedder,MLP,Predictor
 from transformers import ViTConfig,ViTModel
 source=WORK/'evidence/old_spt/utils.py';manifest=json.loads((WORK/'evidence/old_spt/source_manifest.json').read_text())
 assert sha(source)==manifest['files']['stable_pretraining/backbone/utils.py']['sha256']
 node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='vit_hf')
 ns=dict(nn=nn,ViTConfig=ViTConfig,ViTModel=ViTModel,_TRANSFORMERS_AVAILABLE=True,logging=logging)
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),ns)
 cs={'stable_pretraining.backbone.utils.vit_hf':ns['vit_hf'],'stable_worldmodel.wm.lewm.module.Predictor':Predictor,'stable_worldmodel.wm.lewm.module.Embedder':Embedder,'stable_worldmodel.wm.lewm.module.MLP':MLP,'torch.nn.BatchNorm1d':nn.BatchNorm1d}
 rec={r['filename']:r for r in records(task) if r.get('method')=='LeWM_OFFICIAL'}
 for key in ['weights.pt','config.json']:assert sha(ROOT/rec[key]['destination'])==rec[key]['sha256']
 cfg=json.loads((ROOT/rec['config.json']['destination']).read_text());assert cfg['encoder']['pretrained'] is False
 def make(s):
  ctor=cs[s['_target_']];kw={k:make(v) if isinstance(v,dict) and '_target_' in v else v for k,v in s.items() if not k.startswith('_')}
  return functools.partial(ctor,**kw) if s.get('_partial_') else ctor(**kw)
 model=LeWM(**{k:make(cfg[k]) for k in ('encoder','predictor','action_encoder','projector','pred_proj')}).float().eval()
 state=torch.load(ROOT/rec['weights.pt']['destination'],map_location='cpu',weights_only=True)
 result=model.load_state_dict(state,strict=True);assert not result.missing_keys and not result.unexpected_keys
 assert all(not torch.is_floating_point(t) or torch.isfinite(t).all() for t in state.values())
 model.requires_grad_(False);model=model.to(device)
 return model,dict(weights_sha256=rec['weights.pt']['sha256'],config_sha256=rec['config.json']['sha256'],constructor_sha256=sha(source),state_keys=len(state),swm_file=swm.__file__)
def scaler(task):
 from sklearn.preprocessing import StandardScaler
 p=UPLOAD/f'metadata/{task}_normalization.json';d=json.loads(p.read_text())['action'];s=StandardScaler()
 s.mean_=np.asarray(d['mean'],np.float64);s.scale_=np.asarray(d['scale'],np.float64);s.var_=np.asarray(d['variance'],np.float64);s.n_features_in_=len(s.mean_);s.n_samples_seen_=d.get('finite_rows',1)
 return s
class CaseData:
 def __init__(self,hf,case,offset,goal_render=False):
  self.hf=hf;self.case=case;self.offset=offset;task=case['task']
  self.column_names={'reacher':['pixels','qpos','qvel','seed'],'pusht':['pixels','state','seed'],'tworoom':['pixels','proprio','seed'],'cube':['pixels','qpos','qvel','privileged_block_0_pos','privileged_block_0_quat']}[task]
  self.start=None;self.goal=None;self.goal_render=goal_render;self.goal_render_evidence=None
 def load_chunk(self,episodes,starts,ends):
  c=self.case;assert list(episodes)==[c['source_episode_idx']] and list(starts)==[c['start_raw_index']] and list(ends)==[c['start_raw_index']+self.offset+1]
  base=int(self.hf['ep_offset'][episodes[0]]);lo=base+starts[0];hi=base+ends[0];assert ends[0]<=self.hf['ep_len'][episodes[0]]
  row={k:np.asarray(self.hf[k][lo:hi]).copy() for k in self.column_names if k!='seed'}
  if row['pixels'].shape[-1]==3:row['pixels']=row['pixels'].transpose(0,3,1,2)
  self.start={k:v[0].copy() for k,v in row.items()};self.goal={k:v[-1].copy() for k,v in row.items()}
  if self.goal_render:
   from factor_bindings import isolated_goal
   pixels,self.goal_render_evidence=isolated_goal(self.case['task'],self.goal,self.case,CONTRACT)
   row['pixels'][-1]=pixels.transpose(2,0,1);self.goal['pixels']=row['pixels'][-1].copy()
  if 'seed' in self.column_names:row['seed']=np.full(self.offset+1,int(c['reset_seed']),np.int64)
  return [{k:torch.from_numpy(v.copy()) for k,v in row.items()}]

def read_reset_state(env,task,data,case):
 if task=='reacher':
  actual={'qpos':ar(env.env.physics.data.qpos),'qvel':ar(env.env.physics.data.qvel),'target_qpos':ar(env.env.task.target_qpos)}
  expected={'qpos':data.start['qpos'],'qvel':data.start['qvel'],'target_qpos':data.goal['qpos']}
 elif task=='pusht':
  actual={'state':np.asarray(tuple(env.agent.position)+tuple(env.block.position)+(env.block.angle,)+tuple(env.agent.velocity),np.float64),'goal_state':ar(env.goal_state)}
  expected={'state':data.start['state'],'goal_state':data.goal['state']}
 elif task=='tworoom':
  actual={'proprio':ar(env.agent_position),'target':ar(env.target_position)}
  expected={'proprio':data.start['proprio'],'target':data.goal['proprio']}
 else:
  mid=env._cube_target_mocap_ids[0]
  actual={'qpos':ar(env._data.qpos),'qvel':ar(env._data.qvel),'target_pos':ar(env._data.mocap_pos[mid]),'target_quat':ar(env._data.mocap_quat[mid])}
  expected={'qpos':data.start['qpos'],'qvel':data.start['qvel'],'target_pos':data.goal['privileged_block_0_pos'],'target_quat':data.goal['privileged_block_0_quat']}
 comparisons={}
 for name,value in expected.items():
  a=actual[name];e=np.asarray(value)
  comparisons[name]={'actual':a.tolist(),'expected':e.tolist(),'actual_tensor':tensor_record(a),'expected_tensor':tensor_record(e),'exact_values_equal':bool(np.array_equal(a,e)),'max_abs':float(np.max(np.abs(a-e))) if a.shape==e.shape else None}
 source={}
 for name,value in case['reset_metadata'].get('start',{}).items():
  if name in data.start:source[name]=bool(np.array_equal(np.asarray(value),data.start[name]))
 return {'read_before_first_primitive':True,'comparisons':comparisons,'dataset_vs_manifest_start':source,'all_exact':all(v['exact_values_equal'] for v in comparisons.values()) and all(source.values())}

def run_case(model,identity,hf,case,stream,history,replan,success_mode,out,device,variant=None,phase="TECH",condition_id=None,cem_iterations=30,budget=50):
 assert budget==50 or (phase=='TECH' and budget==1)
 out=Path(out);out.mkdir(parents=True,exist_ok=False);dump(out/'STARTED.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),case=case,stream=stream,history=history,replan_raw=replan,success_mode=success_mode,cem_iterations=cem_iterations,model=identity,code_sha256=sha(__file__),phase=phase,condition_id=condition_id))
 actions=[];observed=[];frames=[];plans=[];probes=[];successes=[];snapshot={};task=case['task'];sc=scaler(task);transform=image_transform();current=None
 class Cost(ShootingCostEvaluator):
  def get_cost(self,info,candidates):
   nonlocal current
   if 'model_pixels_shape' not in current:
    t=len(actions);ix=history_indices(t,history);expected=torch.stack([transform(torch.from_numpy(frames[i].transpose(2,0,1).copy())) for i in ix])
    assert torch.equal(expected,info['pixels'][0,0].cpu()),'Real frame mismatch'
    current.update(model_pixels_shape=list(info['pixels'].shape),candidate_shape=list(candidates.shape),history_raw_indices=ix,history_frame_hashes=[tensor_record(frames[i]) for i in ix])
    assert tuple(candidates.shape)==(1,300,5,5*sc.n_features_in_)
    if len(ix)==1:assert 'action_history' not in info
    else:
     past=sc.transform(np.stack(observed[ix[0]+1:t+1])).reshape(len(ix)-1,-1).astype(np.float32)
     actual=ar(info['action_history'])[0,0];assert np.array_equal(past,actual),'Observed action history mismatch'
     assert np.array_equal(np.stack(observed[ix[0]+1:t+1]),np.stack(actions[ix[0]:t]))
     current.update(action_history=tensor_record(actual),real_actions_verified=True)
   costs=super().get_cost(info,candidates);assert torch.isfinite(costs).all();return costs
 cost=Cost(model,GoalMSE());solver=CEMSolver(cost=cost,device=device,seed=seed(task,case['case_id'],0,stream),batch_size=1,num_samples=300,var_scale=1,n_steps=cem_iterations,topk=30)
 if variant=='cem':
  from factor_bindings import SampleStd
  solver.callbacks.append(SampleStd())
 native_solve=solver.solve
 def solve(info,init_action=None):
  nonlocal current
  index=len(probes);sd=seed(task,case['case_id'],index,stream);solver.torch_gen.manual_seed(sd)
  current=dict(replan_index=index,anchor_raw=len(actions),seed_uint64=sd,warm_start_shape=None if init_action is None else list(init_action.shape));probes.append(current)
  output=native_solve(info,init_action=init_action);plan=ar(output['actions'])[0];assert np.isfinite(plan).all();plans.append(plan);current['first_plan' if index==0 else 'plan']=tensor_record(plan);return output
 solver.solve=solve
 policy=WorldModelPolicy(solver=solver,config=swm.PlanConfig(horizon=5,receding_horizon=replan//5,action_block=5,history_len=history),process={'action':sc},transform={'pixels':transform,'goal':transform})
 class Observed:
  def set_env(self,env):policy.set_env(env)
  def get_action(self,info,**kw):
   frames.append(ar(info['pixels'][0,-1]));observed.append(ar(info['action'][0,-1]))
   if 'actual_reset_state' not in snapshot:
    snapshot['actual_reset_state']=read_reset_state(world.envs.envs[0].unwrapped,task,data,case)
    if task=='pusht':
     from native_reset import describe_pusht
     snapshot['native_reset_v12']=describe_pusht(world.envs.envs[0].unwrapped,data.start['state'],data.goal['state'])
    else:assert snapshot['actual_reset_state']['all_exact'],'Unchanged non-PushT reset check'
    snapshot.update(initial_pixels=tensor_record(info['pixels'][0,-1]),goal_pixels=tensor_record(info['goal'][0,-1]),dataset_reset={k:tensor_record(v) for k,v in data.start.items() if k!='pixels'},dataset_goal={k:tensor_record(v) for k,v in data.goal.items() if k!='pixels'})
    assert np.array_equal(info['pixels'][0,-1],data.start['pixels'].transpose(1,2,0))
    assert np.array_equal(info['goal'][0,-1],data.goal['pixels'].transpose(1,2,0))
   allowed={k:ar(v) for k,v in info.items() if k in ('pixels','goal','action','terminated','_needs_flush')}
   if success_mode=='full50' and 'terminated' in allowed:allowed['terminated'][...]=False
   return policy.get_action(allowed,**kw)
 kwargs={'reacher':{'env_name':'swm/ReacherDMControl-v0','task':'qpos_match'},'pusht':{'env_name':'swm/PushT-v1'},**{k:v['world'] for k,v in CONTRACT['CONFIG'].items()}}[task]
 world=None;meter=None;started=time.monotonic();err=None;metrics=None
 try:
  offset=24 if variant=='offset' else 25
  data=CaseData(hf,case,offset,variant=='goal');world=swm.World(**kwargs,num_envs=1,max_episode_steps=100,image_shape=(224,224));world.set_policy(Observed())
  if variant=='angle':
   assert task=='pusht'
   from factor_bindings import old_angle
   snapshot['angle_source_sha256']=old_angle(world.envs.envs[0].unwrapped)
  if task=='cube':
   import importlib.util,mujoco
   path=UPLOAD/'code/harness_reference/r10_execution_code_cube_reset.py';spec=importlib.util.spec_from_file_location('d1_cube_clear',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
   native_reset=world.reset
   def reset(*args,**kw):native_reset(*args,**kw);mod.clear_internal(world.envs.envs[0].unwrapped,mujoco)
   world.reset=reset
  native_step=world.envs.step
  def step(value,*args,**kw):
   result=native_step(value,*args,**kw);actions.append(ar(value[0]));successes.append(bool(result[2][0]))
   if success_mode=='full50':
    z=list(result);z[2]=np.zeros_like(result[2]);result=tuple(z)
   return result
  world.envs.step=step
  meter=PlanMeter(model,lambda:torch.cuda.synchronize(device));meter.start()
  specs=CONTRACT['CALLABLES'].get(task) or CONTRACT['CONFIG'][task]['callables']
  with torch.inference_mode(),torch.autocast(device_type='cuda',enabled=False):metrics=world.evaluate(dataset=data,episodes_idx=[case['source_episode_idx']],start_steps=[case['start_raw_index']],goal_offset=offset,eval_budget=budget,callables=specs,video=None,reset_mode='wait')
  timing=meter.end();assert len(actions)==budget or(success_mode=='any' and any(successes))
  assert [p['anchor_raw'] for p in probes]==list(range(0,len(actions),replan))
 except BaseException as e:
  err={'type':type(e).__name__,'message':str(e),'traceback':traceback.format_exc()};timing={'wall_seconds':time.monotonic()-started}
 finally:
  if meter is not None:meter.close()
  if world is not None:
   from factor_bindings import close_world
   close_world(world)
 np.savez_compressed(out/'trajectory.npz',raw_actions=np.asarray(actions),observed_actions=np.asarray(observed),returned_plans_normalized=np.asarray(plans),successes=np.asarray(successes))
 result=dict(raw_budget=budget,status='COMPLETE' if err is None else 'FAILED',error=err,case_id=case['case_id'],task=task,stream=stream,history_len=history,replan_raw=replan,success_mode=success_mode,executed_raw_steps=len(actions),success_any=int(any(successes)) if successes else None,success_block=int(any(successes[4::5])) if successes else None,success_final=int(successes[-1]) if successes else None,replans=probes,snapshot=snapshot,variant=variant,goal_render_evidence=data.goal_render_evidence,timing=timing,whole_case_wall_seconds=time.monotonic()-started,optimizer_updates=0,phase=phase,condition_id=condition_id)
 dump(out/'result.json',result);dump(out/'COMPLETE.json' if err is None else out/'FAILURE.json',{'sha256':{n:sha(out/n) for n in ['STARTED.json','trajectory.npz','result.json']}})
 if err and phase=='TECH':raise RuntimeError(err['traceback'])
 print(json.dumps({k:result[k] for k in ['status','case_id','task','stream','history_len','executed_raw_steps','timing']}),flush=True);return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--device',default='cuda:0');p.add_argument('--output',required=True);p.add_argument('--case-index',type=int);p.add_argument('--phase',choices=['TECH','FORMAL'],default='TECH');p.add_argument('--condition-id');p.add_argument('--launch-receipt');p.add_argument('--case-start',type=int,default=0);p.add_argument('--case-end',type=int,default=200);p.add_argument('--streams',default='A');p.add_argument('--variants',default='h1,h3');a=p.parse_args()
 torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.set_float32_matmul_precision('highest');torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
 unified=json.loads((ROOT/'prereg/UNIFIED_CASES_V1.json').read_text())['tasks'][a.task]
 tech=json.loads((UPLOAD/f'cases/tech_{a.task}.json').read_text());assert len(tech)==4
 assert not({c['source_episode_idx'] for c in tech}&{c['source_episode_idx'] for c in unified})
 if a.phase=='FORMAL':
  from formal_guard import authorize
  launch=authorize(a.condition_id,__file__,a.launch_receipt)
  row=launch['condition_specs'][a.condition_id]
  assert row['task']==a.task and row['variant']==a.variants and a.streams==row['stream_letters']
  assert 0<=a.case_start<a.case_end<=200
  cases=unified[a.case_start:a.case_end]
 else:cases=tech
 model,identity=build_model(a.task,a.device)
 if a.case_index is not None:cases=[cases[a.case_index]]
 rec=next(r for r in records(a.task) if r['kind']=='dataset');path=ROOT/rec['unpacked_destination']
 assert path.stat().st_size==rec['unpacked_bytes'];assert (ROOT/f'DOWNLOAD_{a.task}_all.json').exists(),'Dataset download/unpack SHA receipt missing'
 with h5py.File(path,'r') as hf:
  for case in cases:
   for letter in a.streams:
    stream=STREAMS[ord(letter)-ord('A')]
    for variant in a.variants.split(','):
     h=3 if variant in ['h3','replan3'] else 1;replan=5 if variant.startswith('replan') else 25;success='full50' if variant=='success' else 'any'
     run_case(model,identity,hf,case,stream,h,replan,success,Path(a.output)/case['case_id']/stream/variant,a.device,variant,a.phase,a.condition_id)
if __name__=='__main__':raise SystemExit('Use step4_worker.py; old main disabled')
