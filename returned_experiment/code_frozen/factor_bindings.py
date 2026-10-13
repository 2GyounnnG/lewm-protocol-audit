"""Only the explicitly preregistered one-factor interventions; no source edits."""
import ast,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image
class SampleStd:
 output_key='D1_sample_std';history=[]
 def reset(self):self.history=[]
 def start_batch(self):pass
 def end_solve(self):pass
 def __call__(self,**kw):
  kw['var'].copy_(kw['topk_candidates'].std(dim=1,correction=1))
  self.history.append({'iteration':kw['step'],'correction':1})
def old_angle(env):
 p=Path('/workspace/d1/repos/SWM_OLD/stable_worldmodel/envs/pusht/env.py')
 node=next(n for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.FunctionDef) and n.name=='eval_state')
 scope={'np':np};exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),scope)
 import types
 env.eval_state=types.MethodType(scope['eval_state'],env)
 return hashlib.sha256(p.read_bytes()).hexdigest()
def close_world(world):
 for wrapped in world.envs.envs:
  base=wrapped.unwrapped;renderer=base.__dict__.get('_renderer')
  if renderer is not None:renderer.close();base._renderer=None
 world.close()
def isolated_goal(task,goal,case,contract):
 import stable_worldmodel as swm
 from adapters.common import tensor_record
 kwargs={'reacher':{'env_name':'swm/ReacherDMControl-v0','task':'qpos_match'},'pusht':{'env_name':'swm/PushT-v1'},**{k:v['world'] for k,v in contract['CONFIG'].items()}}[task]
 images=[];states=[]
 for repeat in range(2):
  world=swm.World(**kwargs,num_envs=1,max_episode_steps=100,image_shape=(224,224))
  try:
   world.reset(seed=None if task=='cube' else [int(case['reset_seed'])]);env=world.envs.envs[0].unwrapped
   if task=='cube':
    import importlib.util,mujoco
    path=Path('/workspace/d1/upload/code/harness_reference/r10_execution_code_cube_reset.py');spec=importlib.util.spec_from_file_location('d1_goal_cube_clear',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.clear_internal(env,mujoco)
   specs=contract['CALLABLES'].get(task) or contract['CONFIG'][task]['callables']
   for spec in specs:
    args={k:np.asarray(goal[d['value'].removeprefix('goal_')]).copy() if d.get('in_dataset',True) else d['value'] for k,d in spec['args'].items()}
    getattr(env,spec['method'])(**args)
   image=np.array(Image.fromarray(np.ascontiguousarray(env.render())).resize((224,224),Image.Resampling.BILINEAR));images.append(image)
   if task=='reacher':state={'qpos':np.asarray(env.env.physics.data.qpos),'qvel':np.asarray(env.env.physics.data.qvel)}
   elif task=='pusht':state={'state':np.asarray(tuple(env.agent.position)+tuple(env.block.position)+(env.block.angle,)+tuple(env.agent.velocity))}
   elif task=='tworoom':state={'proprio':env.agent_position.cpu().numpy()}
   else:state={'qpos':np.asarray(env._data.qpos),'qvel':np.asarray(env._data.qvel)}
   if task=='pusht':
    from native_reset import describe_pusht
    native=describe_pusht(env,goal['state'],goal['state'])
   else:assert all(np.array_equal(v,goal[k]) for k,v in state.items()),'Isolated goal state differs'
   states.append({k:tensor_record(v) for k,v in state.items()})
  finally:close_world(world)
 assert states[0]==states[1],'Independent isolated post-reset states differ'
 assert np.array_equal(images[0],images[1]),'Independent isolated goal renders differ'
 return images[0],{'two_independent_renders_bitwise':True,'goal_state_exact':all(np.array_equal(v,goal[k]) for k,v in state.items()),'native_goal_reset':True,'native_pusht_evidence':native if task=='pusht' else None,'pixels':tensor_record(images[0]),'state_records':states}
