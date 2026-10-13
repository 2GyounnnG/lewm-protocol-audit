"""Fast native interface: [B,S,5,5*A] <-> [B,S,1,25*A], same raw action order.
Three delivered frames do not alter the released model's HS=1 dynamics.
No observed-action prefix is passed as a future Fast action block.
"""
def pack(a):
 if len(a.shape)!=4 or a.shape[2]!=5 or a.shape[3]%5:raise ValueError('Expected five 5-raw blocks')
 return a.reshape(*a.shape[:2],1,5*a.shape[-1])
def unpack(a):
 if len(a.shape)!=4 or a.shape[2]!=1 or a.shape[-1]%25:raise ValueError('Expected one 25-raw block')
 return a.reshape(*a.shape[:2],5,a.shape[-1]//5)
class FastCost:
 effective_history=1
 def __init__(self,model):self.model=model
 def get_cost(self,info,candidates):
  return self.model.get_cost(dict(info),pack(candidates))
