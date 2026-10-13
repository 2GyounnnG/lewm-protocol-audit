"""Step2 environment bridge, uses pinned SWM and sealed exact reset fields.
No module-level simulator imports. No neural model creation during import checks.
"""
import json,importlib.util
from functools import lru_cache
from pathlib import Path
import numpy as np
from adapters.common import check_case,sha

@lru_cache(maxsize=8)
def _verified_file(path,size,mtime_ns,expected):
 if sha(path)!=expected:raise ValueError('Dataset SHA mismatch')
 return True

class BoundWorld:
 def __init__(self,world):self.world=world;self._frame=None
 def render(self):
  if self._frame is None:raise ValueError('Use sealed dataset initial frame before the first primitive step')
  return self._frame
 def step(self,action):
  obs,reward,terminated,truncated,info=self.world.envs.step(np.asarray(action)[None])
  row={k:(v[0] if hasattr(v,'__len__') and len(v)==1 else v) for k,v in info.items()}
  row['_d1_success']=bool(terminated[0])
  pixels=np.asarray(row['pixels']);self._frame=(pixels[-1] if pixels.ndim==4 else pixels).copy()
  return None if obs is None else obs[0],reward[0],terminated[0],truncated[0],row
 def close(self):self.world.close()

def bind(case,h5_path,expected_sha,offset=25,goal_source='dataset',clear_cube=True):
 import h5py,hdf5plugin,stable_worldmodel as swm
 check_case(case);task=case['task']
 if expected_sha!=case['source_asset_sha256']:raise ValueError('Dataset does not match sealed case asset')
 stat=Path(h5_path).stat();_verified_file(str(Path(h5_path).resolve()),stat.st_size,stat.st_mtime_ns,expected_sha)
 contracts=json.loads((Path(__file__).parent/'task_contracts.json').read_text())
 kwargs={'env_name':'swm/PushT-v1'} if task=='pusht' else {'env_name':'swm/ReacherDMControl-v0','task':'qpos_match'}
 if task in ('cube','tworoom'):kwargs=contracts['CONFIG'][task]['world'].copy()
 world=swm.World(**kwargs,num_envs=1,max_episode_steps=100,image_shape=(224,224))
 # Exact sealed fallback0 is an explicit replay convention, not recovered dataset RNG.
 world.reset(seed=None if task=='cube' else [int(case['reset_seed'])])
 env=world.envs.envs[0].unwrapped
 if task=='cube' and clear_cube:
  import mujoco
  f=Path('/workspace/d1/upload/code/harness_reference/r10_execution_code_cube_reset.py')
  spec=importlib.util.spec_from_file_location('d1_cube_reset',f);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.clear_internal(env,mujoco)
 with h5py.File(h5_path,'r') as h:
  ep=int(case['source_episode_idx']);base=int(h['ep_offset'][ep]);start=base+case['start_raw_index'];end=start+offset
  if end>=base+int(h['ep_len'][ep]):raise ValueError('Goal outside source episode')
  specs=contracts['CALLABLES'][task] if task in ('pusht','reacher') else contracts['CONFIG'][task]['callables']
  for spec in specs:
   if not hasattr(env,spec['method']):raise RuntimeError('Missing required reset callable '+spec['method'])
   args={}
   for key,desc in spec['args'].items():
    field=desc['value']
    args[key]=field if not desc.get('in_dataset',True) else np.asarray(h[field[5:] if field.startswith('goal_') else field][end if field.startswith('goal_') else start]).copy()
   getattr(env,spec['method'])(**args)
  initial=np.asarray(h['pixels'][start]);goal=np.asarray(h['pixels'][end])
  if initial.shape[0]==3:initial=np.moveaxis(initial,0,-1);goal=np.moveaxis(goal,0,-1)
 if goal_source!='dataset':raise ValueError('Rendered-goal factor needs a separate cloned target state; must not reuse the start render')
 bound=BoundWorld(world)
 if task=='pusht':
  from native_reset import describe_pusht
  with h5py.File(h5_path,'r') as h:bound.native_reset_v12=describe_pusht(env,np.asarray(h['state'][start]),np.asarray(h['state'][end]))
 return bound,initial,goal
