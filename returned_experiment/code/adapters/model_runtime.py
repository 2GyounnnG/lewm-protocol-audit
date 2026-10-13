"""Only called on the step2 instance. Never import torch at module import time."""
import sys,importlib
from pathlib import Path
from adapters.common import sha

def load_object(method,repo,checkpoint,expected_sha,device='cuda:0'):
 if method not in ('M01','M07'):raise ValueError(method)
 if sha(checkpoint)!=expected_sha:raise ValueError('Checkpoint SHA256 mismatch')
 # One method per process: pickle globals jepa/module collide across repositories.
 repo=Path(repo).resolve()
 for name in ('jepa','module','utils'):
  if name in sys.modules and not Path(sys.modules[name].__file__).resolve().is_relative_to(repo):raise RuntimeError('Conflicting third-party module namespace; use a separate process')
 sys.path.insert(0,str(repo))
 import torch
 root=torch.load(checkpoint,weights_only=False,map_location='cpu')
 candidates=[m for m in root.modules() if callable(getattr(m,'get_cost',None))]
 if not candidates:raise ValueError('No native get_cost found')
 model=candidates[0]
 # Rehydrate the serialized ViT using the pinned transformers4 class. The
 # explicit bijective key map follows the released AP loader's v5/v4 map.
 from transformers import ViTModel,ViTConfig
 old=model.encoder
 cfg=ViTConfig(**dict(old.config.__dict__))
 if hasattr(old.config,'_output_attentions'):cfg.output_attentions=old.config._output_attentions
 state=old.state_dict();mapping={};converted={}
 replacements=[('layers.','encoder.layer.'),('.attention.q_proj.','.attention.attention.query.'),('.attention.k_proj.','.attention.attention.key.'),('.attention.v_proj.','.attention.attention.value.'),('.attention.o_proj.','.attention.output.dense.'),('.mlp.fc1.','.intermediate.dense.'),('.mlp.fc2.','.output.dense.')]
 for k,value in state.items():
  key=k
  if any(x.startswith('layers.') for x in state):
   for src,dst in replacements:key=key.replace(src,dst)
  if key in converted:raise ValueError('Non-bijective ViT key mapping')
  converted[key]=value;mapping[k]=key
 fresh=ViTModel(cfg,add_pooling_layer=any(k.startswith('pooler.') for k in state),use_mask_token='embeddings.mask_token' in state)
 fresh.load_state_dict(converted,strict=True)
 assert len(state)==len(fresh.state_dict())
 assert all(torch.equal(value,fresh.state_dict()[mapping[k]]) for k,value in state.items())
 model.encoder=fresh
 print({'serialization_vit_rehydration':{'state_keys':len(state),'bitwise_weights_equal':True,'bijective_key_mapping':mapping}},flush=True)
 model=model.to(device).eval().requires_grad_(False);model.interpolate_pos_encoding=True
 if method=='M01':
  # Match released eval defaults, including optional self-consistency disabled.
  ev=importlib.import_module('eval');ev._configure_rollout_consistency(model,0.0,[2,3])
  for m in model.modules():
   if isinstance(m,torch.nn.GRU):m.train()
 return model

class CEMPlanner:
 def __init__(self,method,model,scaler,transform,action_dim,device,history_len):
  import torch
  import gymnasium as gym
  import stable_worldmodel as swm
  from stable_worldmodel.planning.solver import CEMSolver
  from adapters.M01 import FastCost
  from adapters.M07 import ADCost
  self.method=method;self.model=model;self.scale=scaler;self.transform=transform;self.h=history_len;self.device=device;self.past=[]
  cost=FastCost(model) if method=='M01' else ADCost(model,lambda:self.past)
  self.solver=CEMSolver(cost=cost,batch_size=1,num_samples=300,var_scale=1,n_steps=30,topk=30,device=device,seed=0)
  self.solver.configure(action_space=gym.spaces.Box(-1,1,shape=(1,action_dim)),n_envs=1,config=swm.PlanConfig(horizon=5,receding_horizon=5,action_block=5))
 def plan(self,frames,actions,goal,seed):
  import torch,numpy as np
  from adapters.common import history
  f,self.past,ix=history(frames,actions,self.h,self.scale)
  pix=self.transform(torch.from_numpy(np.stack(f)).permute(0,3,1,2)).to(self.device)[None]
  gp=self.transform(torch.from_numpy(goal).permute(2,0,1)).to(self.device)[None,None]
  # Native get_cost removes action from goal dict. It is not the history prefix.
  a=torch.zeros((1,1,self.scale.n_features_in_),dtype=torch.float32,device=self.device)
  info=dict(pixels=pix,goal=gp,action=a)
  self.solver.torch_gen.manual_seed(seed)
  out=self.solver.solve(info,init_action=None)
  norm=out['actions'][0].detach().cpu().numpy()
  raw=self.scale.inverse_transform(norm.reshape(-1,self.scale.n_features_in_)).astype(np.float32)
  return raw,dict(history_raw_indices=ix,history_requested=self.h,history_delivered=len(ix),history_effective=1 if self.method=='M01' else len(ix),normalized_plan=norm)
