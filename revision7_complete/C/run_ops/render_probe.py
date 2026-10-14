"""Three paired reset images, no policy or actions; isolate renderer observation difference."""
import os,json,hashlib
from pathlib import Path
import numpy as np,h5py,hdf5plugin
from anchored_planning import runtime
runtime.configure_runtime()
from anchored_planning import environments
from PIL import Image
W=Path(__file__).resolve().parents[1];backend=os.environ['MUJOCO_GL'];out=W/'outputs/diagnostics/render_probe'/backend;out.mkdir(parents=True,exist_ok=False)
rows=json.load(open(W/'protocol_main128/protocols/main.json'))['studies']['reacher']['confirm'][:3];result=[]
with h5py.File(W/'assets/data/reacher.h5','r') as hf:
 for row in rows:
  states={int(i):np.asarray(hf['observation'][i],np.float32) for i in [row['global_start'],row['global_goal']]}
  env,obs,info,goal=environments._make_live({'task':'reacher','arrays':{'states':states}},row)
  try:
   physics=env.unwrapped.env.physics;before=np.r_[physics.data.qpos.copy(),physics.data.qvel.copy(),physics.data.time]
   rgb=np.ascontiguousarray(env.render());after=np.r_[physics.data.qpos.copy(),physics.data.qvel.copy(),physics.data.time]
   assert np.array_equal(before,after),'Render changed physical state'
   name=row['record_id'];Image.fromarray(rgb).save(out/(name+'.png'));np.save(out/(name+'.npy'),rgb,allow_pickle=False)
   result.append({'case':name,'backend':backend,'qpos':physics.data.qpos.tolist(),'qvel':physics.data.qvel.tolist(),'physics_time':float(physics.data.time),'goal':np.asarray(goal).tolist(),'observation':np.asarray(obs).tolist(),'image_shape':list(rgb.shape),'image_sha256':hashlib.sha256(rgb.tobytes()).hexdigest(),'no_actions':True,'render_does_not_change_state':True})
  finally:env.close()
(out/'RECEIPT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
