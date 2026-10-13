"""CPU-only simulator component check on the real source case; not full AP evaluation."""
import os,json,time,hashlib
from pathlib import Path
os.environ['MUJOCO_GL']='disable'
import numpy as np
from anchored_planning.runtime import check_simulator_versions,versions
from anchored_planning.environments import _make_env
W=Path(__file__).resolve().parent
p=W/'ap_source/data/project_demos/traces/reacher/confirm_ap-fresh-reacher-000_clean_gaussian_observed.json'
src=json.load(open(p));state=np.array(src['trajectory'][0]['physics']);target=np.array(src['true_goal']);started=time.monotonic()
check_simulator_versions('reacher');env=_make_env('reacher');env.reset(seed=32823,options={'target_qpos':target[:2]});env.unwrapped.set_state(state[:2],state[2:]);states=[]
for t in range(5):
 obs,reward,terminated,truncated,info=env.step(np.zeros(2,np.float32));states.append({'qpos':np.asarray(info['qpos']).tolist(),'terminated':bool(terminated),'truncated':bool(truncated)})
env.close()
(W/'CPU_PHYSICS_COMPONENT_RECEIPT.json').write_text(json.dumps({'status':'PASS_COMPONENT_ONLY','case':src['compact']['identity'],'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'steps':states,'dependencies':versions(),'elapsed_seconds':time.monotonic()-started,'full_original_AP_case_passed':False,'no_renderer_no_model_no_retrieval':True},indent=2))
print('PASS physics component only, not full AP case')
