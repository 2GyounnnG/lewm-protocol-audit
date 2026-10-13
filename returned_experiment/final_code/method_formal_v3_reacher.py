"""Step2-only executable. Receives fully resolved asset JSON; refuses unregistered FORMAL runs."""
import argparse,json,sys,time,itertools
from pathlib import Path
import numpy as np
from adapters.common import sha,PlanMeter,STREAMS,validate_asset_identity
from adapters.harness import run_case

def run(a):
 assets=json.loads(Path(a.assets).read_text());cases=json.loads(Path(a.cases).read_text())['tasks'][a.task]
 validate_asset_identity(assets,a.method,a.task,json.loads((Path('/workspace/d1/upload/HF_ASSETS_MANIFEST.json')).read_text()))
 if a.phase=='FORMAL':
  from formal_guard import authorize
  launch=authorize(a.condition_id,__file__,a.prereg_receipt)
  row=launch['condition_specs'][a.condition_id]
  assert row['task']==a.task and row['model']==a.method and int(row['history'])==a.history
  assert row['stream_letters']==a.streams
  assert str(assets.get('train_seed','released' if a.method=='M01' else 'official'))==str(row['train_seed'])
  cases=cases[a.case_start:a.case_end]
 else:
  cases=json.loads((Path(a.cases).parent/f'tech_{a.task}.json').read_text())
  if len(cases)<4:raise ValueError('Four separate TECH cases required')
  cases=cases[:4]
  if a.case_index is not None:cases=[cases[a.case_index]]
 import torch
 from sklearn.preprocessing import StandardScaler
 from torchvision.transforms import v2
 from adapters.model_runtime import load_object,CEMPlanner
 from adapters.swm_runtime_recorded import bind
 torch.set_num_threads(1);torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
 torch.backends.cuda.enable_flash_sdp(False);torch.backends.cuda.enable_mem_efficient_sdp(False);torch.backends.cuda.enable_math_sdp(True)
 n=json.loads(Path(assets['normalization']).read_text())['action'];sc=StandardScaler();sc.mean_=np.array(n['mean']);sc.scale_=np.array(n['scale']);sc.var_=np.array(n['variance']);sc.n_features_in_=len(sc.mean_);sc.n_samples_seen_=n.get('finite_rows',1)
 if sha(assets['normalization'])!=assets['normalization_sha256']:raise ValueError('Normalizer differs')
 transform=v2.Compose([v2.ToImage(),v2.ToDtype(torch.float32,scale=True),v2.Normalize(mean=[.485,.456,.406],std=[.229,.224,.225]),v2.Resize((224,224),interpolation=v2.InterpolationMode.BILINEAR,antialias=True)])
 if a.method=='M07':
  from adapters.M07 import validate_seed
  validate_seed(assets['train_seed'])
 if a.method in ('M01','M07'):
  model=load_object(a.method,assets['repo'],assets['checkpoint'],assets['checkpoint_sha256'],a.device)
  planner=CEMPlanner(a.method,model,sc,transform,len(sc.mean_),a.device,a.history)
 else:
  from adapters.M03 import APPlanner,filter_bank
  sys.path.insert(0,str(Path(assets['repo'])/'code/ap'))
  from anchored_planning.model import load_model,encode_retrieval
  from adapters.swm_api_compat import install
  install()
  from anchored_planning.native_adapter import NativeAdapter
  from anchored_planning.observation_bank import ObservationBank
  from anchored_planning.runtime import read_latents
  import h5py,hdf5plugin
  if sha(assets['checkpoint'])!=assets['checkpoint_sha256']:raise ValueError('Official model identity mismatch')
  wrapper=load_model(assets['checkpoint'],torch.device(a.device));model=wrapper.official
  native=NativeAdapter(None,dict(model=wrapper,device=torch.device(a.device)),a.task,{'native_action_stats':json.loads(Path(assets['ap_scalers']).read_text())},Path(assets['repo'])/'code/ap')
  native.scaler=sc;native.mean=sc.mean_.copy();native.std=sc.scale_.copy();native.transform=transform
  if sha(assets['latent_cache'])!=assets['latent_cache_sha256']:raise ValueError('Retrieval cache differs')
  hf=h5py.File(assets['dataset'],'r');bankmeta=json.loads(Path(assets['bank']).read_text())
  if bankmeta['dataset_sha256']!=assets['dataset_sha256']:raise ValueError('Bank dataset identity')
  original=json.loads((Path(assets['repo'])/'code/ap/protocols/main.json').read_text())['studies'][a.task]['confirm']
  excluded=cases+[dict(source_episode_idx=x['episode']) for x in original]
  train=filter_bank(bankmeta['train_episode_ids'],excluded)
  if train!=bankmeta['train_episode_ids']:raise ValueError('Bank metadata includes evaluation episodes; rebuild')
  latents=read_latents(Path(assets['latent_cache']));bank=ObservationBank(dict(lengths=np.asarray(hf['ep_len']),offsets=np.asarray(hf['ep_offset'])),latents,np.asarray(train),5,np.ones(3,np.float32),torch.device(a.device))
  planner=None
 root_out=Path(a.output);root_out.mkdir(parents=True,exist_ok=True)
 streams=[STREAMS[ord(c)-ord('A')] for c in a.streams]
 for case,stream in itertools.product(cases,streams):
  out=root_out/stream;out.mkdir(parents=True,exist_ok=True)
  started=time.monotonic()
  if (out/(case['case_id']+'.json')).exists():raise FileExistsError('Refuse overwrite delivered case')
  from REVISION_3_REACHER_RECORDING_PATCH import install_nonterminating_reacher
  env,initial,goal=bind(case,assets['dataset'],assets['dataset_sha256'],before_reset=install_nonterminating_reacher if a.task=='reacher' else None)
  r3_tracker=None
  if a.task=='reacher':
   from REVISION_3_REACHER_RECORDING_PATCH import install_nonterminating_reacher
   r3_tracker=install_nonterminating_reacher(env.world.envs.envs[0].unwrapped)
   _native_env_step=env.step
   def _corrected_env_step(action):
    obs,reward,terminated,truncated,info=_native_env_step(action)
    info['_d1_success']=r3_tracker.consume_step()
    return obs,reward,False,truncated,info
   env.step=_corrected_env_step
  try:
   meter=PlanMeter(model,lambda:torch.cuda.synchronize(a.device))
   if a.method=='M03':
    low=env.world.envs.single_action_space.low;high=env.world.envs.single_action_space.high
    ap=APPlanner(native,bank,hf['pixels'],low,high,lambda rgb:encode_retrieval(wrapper,rgb,torch.device(a.device)),a.history)
    goal_latent=encode_retrieval(wrapper,goal[None],torch.device(a.device));goal_record=int(hf['ep_offset'][case['source_episode_idx']])+case['goal_raw_index']
    call=lambda frames,actions,g,sd:ap.plan(frames,actions,goal_latent,goal_record,max(5,25-len(actions)),sd)
   else:call=planner.plan
   raw_call=call
   def observed_call(frames,actions,g,sd):
    raw,metadata=raw_call(frames,actions,g,sd)
    return raw,dict(metadata,seed_uint64=int(sd))
   call=observed_call
   with torch.inference_mode(),torch.autocast(device_type='cuda',enabled=False):
    r=run_case(env,call,case,stream,goal,lambda obs,info:info['_d1_success'],replan_raw=5 if a.method=='M03' else 25,meter=meter,initial_frame=initial,budget=a.budget,stop_at_success=a.success_mode=='any')
   
   assert len(r['steps'])==a.budget or (a.success_mode=='any' and r['success_any'])
   assert [p['raw_t'] for p in r['plans']]==list(range(0,len(r['steps']),5 if a.method=='M03' else 25))
   r.update(raw_budget=a.budget,status='COMPLETE',success_block=int(any(x['success'] for x in r['steps'][4::5])),success_mode=a.success_mode,executed_raw_steps=len(r['steps']),method=a.method,train_seed=assets.get('train_seed','official'),history_requested=a.history,phase=a.phase,cohort=case.get('cohort','TECH'),checkpoint_sha256=assets['checkpoint_sha256'],condition_id=a.condition_id,whole_case_wall_seconds=time.monotonic()-started)
   if r3_tracker is not None:
    record=r3_tracker.export_record();ends=record['step_end_labels']
    r.update(reacher_runtime=record,success_block=int(any(ends[4::5])),success_final=int(ends[-1]),success_semantics={'success_any':'OR of all microsteps','success_block':'environment-step-end at 5,10,...,50','success_final':'environment-step-end at 50'})
    for i,row in enumerate(r['steps']):
     row.update(success_any_in_step=bool(record['step_any_labels'][i]),success_at_step_end=bool(ends[i]))
   if a.task=='pusht':r['native_reset_v12']=env.native_reset_v12
   first=r.pop('first_raw_plan');np.save(out/(case['case_id']+'.first_plan.npy'),first,allow_pickle=False)
   actions=r.pop('raw_actions');np.save(out/(case['case_id']+'.actions.npy'),actions,allow_pickle=False)
   (out/(case['case_id']+'.json')).write_text(json.dumps(r,indent=2))
  finally:
   if 'meter' in locals():meter.close()
   from factor_bindings import close_world
   close_world(env.world)
 if a.method=='M03':hf.close()
if __name__=='__main__':raise SystemExit('Use step4_worker.py')
