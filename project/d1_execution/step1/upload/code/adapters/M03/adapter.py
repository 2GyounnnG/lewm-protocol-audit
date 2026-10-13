"""AP-CEM keeps native nearest observation target and 5-raw replanning.
Uses native Gaussian planner and ObservationsBank, not a replacement algorithm.
"""
import numpy as np
from adapters.common import history

def excluded_episodes(cases):
 return {int(c['source_episode_idx']) for c in cases}
def filter_bank(episodes,cases):
 all_ep=list(map(int,episodes));bad=excluded_episodes(cases)
 if len(all_ep)!=len(set(all_ep)):raise ValueError('Duplicate bank episode IDs')
 selected=[e for e in all_ep if e not in bad]
 if set(selected)&bad:raise AssertionError('Evaluation episode leakage')
 if not selected:raise ValueError('Empty retrieval bank')
 return selected
class APPlanner:
 def __init__(self,native,bank,pixels,low,high,retrieval_encoder,history_len=1):
  from anchored_planning.planners import TargetGaussian
  self.retrieval_encoder=retrieval_encoder;self.native=native;self.bank=bank;self.h=history_len;self.past=np.empty((0,5*native.action_dim),np.float32);self.context=None
  self.gaussian=TargetGaussian(native,pixels);self.gaussian.set_action_bounds(low,high)
  original=getattr(native,"_d1_base_latent_cost",native.latent_cost);native._d1_base_latent_cost=original
  owner=self
  class HistoryLatentCost:
   def get_cost(self,info,candidates):
    import torch
    # Native current_latent caches only current frame; for h3 use real images and the original JEPA encoder.
    if owner.context is not None and owner.context.shape[1]>1:
     info=dict(info);info.pop('current_latent',None)
     info['pixels']=owner.context[:,None].expand(-1,candidates.shape[1],-1,-1,-1,-1)
     p=torch.as_tensor(owner.past,dtype=candidates.dtype,device=candidates.device)[None,None].expand(1,candidates.shape[1],-1,-1)
     candidates=torch.cat((p,candidates),2)
    return original.get_cost(dict(info),candidates)
  native.latent_cost=HistoryLatentCost()
  from stable_worldmodel.planning.solver import CEMSolver
  import stable_worldmodel as swm
  import gymnasium as gym
  self.solver=CEMSolver(cost=native.latent_cost,batch_size=1,num_samples=300,var_scale=1,n_steps=30,topk=30,device=native.device,seed=0)
  self.solver.configure(action_space=gym.spaces.Box(-1,1,shape=(1,native.action_dim)),n_envs=1,config=swm.PlanConfig(horizon=1,receding_horizon=1,action_block=5))
 def plan(self,frames,actions,goal_latent,goal_record,remaining,seed):
  import torch
  f,self.past,ix=history(frames,actions,self.h,self.native.scaler)
  self.context=torch.cat([self.native.pixels(x) for x in f],dim=1)
  current=self.retrieval_encoder(np.asarray(frames[-1])[None]);sources,costs=self.bank.nearest_topk(current,goal_latent,max(5,remaining),8)
  # Unified common CEM: same300/30/30, sigma1, std correction0, no candidate clip.
  # Preserve AP observed successor target and5-raw replanning; native original mode is separate.
  target,miss=self.gaussian.encoding(int(sources[0][0])+5)
  now=self.native.encode_rgb(frames[-1])
  info=dict(pixels=self.native.pixels(frames[-1]),current_latent=now[:,None,:],subgoal_latent=target)
  self.solver.torch_gen.manual_seed(seed)
  out=self.solver.solve(info,init_action=None)
  norm=out['actions'][0].numpy().reshape(5,self.native.action_dim)
  plan=self.native.scaler.inverse_transform(norm).astype(np.float32)
  meta=dict(target_index=int(sources[0][0])+5,target_kind='observed',native_successor_encodings=miss,unified_cem='63988116 std correction0')
  meta.update(history_raw_indices=ix,history_effective=len(ix),retrieved_rows=sources[0].tolist())
  return plan,meta
