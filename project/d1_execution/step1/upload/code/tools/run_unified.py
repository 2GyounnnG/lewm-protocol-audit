"""Step2-only executable. Receives fully resolved asset JSON; refuses unregistered FORMAL runs."""
import argparse,json,sys
from pathlib import Path
import numpy as np
from adapters.common import sha,PlanMeter,STREAMS,validate_asset_identity
from adapters.harness import run_case

def run(a):
 assets=json.loads(Path(a.assets).read_text());cases=json.loads(Path(a.cases).read_text())['tasks'][a.task]
 validate_asset_identity(assets,a.method,a.task,json.loads((Path(__file__).parents[2]/'HF_ASSETS_MANIFEST.json').read_text()))
 if a.phase=='FORMAL':
  prereg=json.loads(Path(a.prereg_receipt).read_text())
  if prereg.get('status')!='REGISTERED_BEFORE_GPU' or prereg.get('cases_sha256')!=sha(a.cases):raise ValueError('Formal preregistration missing or case identity differs')
  if prereg.get('forecast_gpu_hours',float('inf'))>300:raise ValueError('Budget exceeds300')
  if prereg.get('fidelity_status')!='PASS' or prereg.get('history_gate_status')!='PASS':raise ValueError('TECH gates not passed')
 else:
  cases=json.loads((Path(a.cases).parent/f'tech_{a.task}.json').read_text())
  if len(cases)<4:raise ValueError('Four separate TECH cases required')
  cases=cases[:4]
 import torch
 from sklearn.preprocessing import StandardScaler
 from torchvision.transforms import v2
 from adapters.model_runtime import load_object,CEMPlanner
 from adapters.swm_runtime import bind
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
  latents=read_latents(assets['latent_cache']);bank=ObservationBank(dict(lengths=np.asarray(hf['ep_len']),offsets=np.asarray(hf['ep_offset'])),latents,np.asarray(train),5,np.ones(3,np.float32),torch.device(a.device))
  planner=None
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 for case in cases:
  if (out/(case['case_id']+'.json')).exists():raise FileExistsError('Refuse overwrite delivered case')
  env,initial,goal=bind(case,assets['dataset'],assets['dataset_sha256'])
  try:
   meter=PlanMeter(model,lambda:torch.cuda.synchronize(a.device))
   if a.method=='M03':
    low=env.world.envs.single_action_space.low;high=env.world.envs.single_action_space.high
    ap=APPlanner(native,bank,hf['pixels'],low,high,lambda rgb:encode_retrieval(wrapper,rgb,torch.device(a.device)),a.history)
    goal_latent=encode_retrieval(wrapper,goal[None],torch.device(a.device));goal_record=int(hf['ep_offset'][case['source_episode_idx']])+case['goal_raw_index']
    call=lambda frames,actions,g,sd:ap.plan(frames,actions,goal_latent,goal_record,max(5,25-len(actions)),sd)
   else:call=planner.plan
   with torch.inference_mode(),torch.autocast(device_type='cuda',enabled=False):
    r=run_case(env,call,case,a.stream,goal,lambda obs,info:info['_d1_success'],replan_raw=5 if a.method=='M03' else 25,meter=meter,initial_frame=initial)
   r.update(method=a.method,train_seed=assets.get('train_seed','official'),history_requested=a.history,phase=a.phase,cohort=case.get('cohort','TECH'),checkpoint_sha256=assets['checkpoint_sha256'])
   first=r.pop('first_raw_plan');np.save(out/(case['case_id']+'.first_plan.npy'),first,allow_pickle=False)
   actions=r.pop('raw_actions');np.save(out/(case['case_id']+'.actions.npy'),actions,allow_pickle=False)
   (out/(case['case_id']+'.json')).write_text(json.dumps(r,indent=2))
  finally:
   if 'meter' in locals():meter.close()
   env.close()
 if a.method=='M03':hf.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--method',choices=['M01','M03','M07'],required=True);p.add_argument('--task',required=True);p.add_argument('--assets',required=True);p.add_argument('--cases',required=True);p.add_argument('--history',type=int,choices=[1,3],required=True);p.add_argument('--stream',choices=STREAMS,default=STREAMS[0]);p.add_argument('--device',default='cuda:0');p.add_argument('--phase',choices=['TECH','FORMAL'],required=True);p.add_argument('--prereg-receipt');p.add_argument('--output',required=True);run(p.parse_args())
