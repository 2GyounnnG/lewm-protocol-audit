"""Real case CPU replay plus original CEM numerical-path smoke; NOT full retrieval evaluation."""
from pathlib import Path
import os,json,time,hashlib
os.environ['MUJOCO_GL']='disable';os.environ['OMP_NUM_THREADS']='2'
import numpy as np,torch
from PIL import Image
from anchored_planning import environments
from anchored_planning.runtime import check_simulator_versions,WorkCounter
from anchored_planning.model import load_model
from anchored_planning.native_adapter import NativeAdapter
from anchored_planning.planners import TargetGaussian
from anchored_planning.gaussian_cem import query_seed
W=Path(__file__).resolve().parent;R=W.parents[3];source=W/'ap_source';started=time.monotonic();torch.set_num_threads(2)
x=json.load(open(source/'data/project_demos/traces/reacher/confirm_ap-fresh-reacher-000_clean_gaussian_observed.json'));state=np.array(x['trajectory'][0]['physics']);goal=np.array(x['true_goal']);ref=[json.loads(l) for l in (W/'reference_step2_original128.jsonl').read_text().splitlines()][0]
check_simulator_versions('reacher');env=environments._make_env('reacher');env.reset(seed=32823,options={'target_qpos':goal[:2]});env.unwrapped.set_state(state[:2],state[2:]);hit=None
for n,action in enumerate(ref['actions'],1):
 obs,_,term,trunc,info=env.step(np.array(action,np.float32));ok=environments._success_now('reacher',obs,info,goal,False,False)
 if ok:hit=n;break
 if term or trunc:break
env.close();assert hit==ref['first_hit_step'],(hit,ref['first_hit_step'])
weight=R/'r8_execution/final_sync/shared_data/r3/official/reacher/weights.pt';h=hashlib.sha256(weight.read_bytes()).hexdigest();assert h=='eb70b1fd5409f8f81875d62f5ee5a20dd220a3128a477de66b5760f475f0f469'
model=load_model(weight,torch.device('cpu'));native=NativeAdapter(None,{'device':'cpu','model':model},'reacher',{'native_action_stats':json.load(open(source/'code/ap/protocols/scalers.json'))},source/'code/ap')
p=source/'docs/assets/demos/reacher-000-goal.jpg';rgb=np.array(Image.open(p).convert('RGB'));assert rgb.ndim==3 and rgb.shape[-1]==3,rgb.shape
planner=TargetGaussian(native,{5:rgb});planner.set_action_bounds(np.full(2,-1.,np.float32),np.full(2,1.,np.float32));counter=WorkCounter(native.model)
with torch.inference_mode():actions,detail=planner.choose('gaussian_observed',rgb,np.array([0]),torch.Generator(device='cpu').manual_seed(query_seed('reacher',0)),5)
assert actions.shape==(5,2) and np.isfinite(actions).all();assert (counter.calls,counter.candidates)==(31,9002);counter.handle.remove()
r={'status':'PASS_COMPONENTS_AND_SAVED_ACTION_REPLAY','full_original_entry_evaluation':False,'case':ref['record_id'],'first_hit_replayed':hit,'first_hit_reference':ref['first_hit_step'],'checkpoint_sha256':h,'public_goal_jpeg_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'numerical_smoke':'original CEM on public goal JPEG as current and target; no retrieval; not a benchmark outcome','predictor_calls':counter.calls,'predicted_candidates':counter.candidates,'elapsed_seconds':time.monotonic()-started,'actions':actions.tolist()}
(W/'CPU_SAVED_CASE_AND_MODEL_RECEIPT.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
