"""Released AD-WM: training context3, published eval1, eval3 with real prefix."""
TRAIN_SEEDS=(3072,4096,6144)
def validate_seed(seed):
 if seed not in TRAIN_SEEDS:raise ValueError('All three registered training seeds required; no best-seed selection')
 return seed
class ADCost:
 def __init__(self,model,past_provider):self.model=model;self.past_provider=past_provider
 def get_cost(self,info,candidates):
  import torch
  past=self.past_provider()
  if len(past):
   prefix=torch.as_tensor(past,dtype=candidates.dtype,device=candidates.device)[None,None].expand(candidates.shape[0],candidates.shape[1],-1,-1)
   candidates=torch.cat((prefix,candidates),dim=2)
  assert candidates.shape[2]==5+info['pixels'].shape[2]-1
  return self.model.get_cost(dict(info),candidates)
