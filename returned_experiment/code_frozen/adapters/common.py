"""Pure array contracts shared by all methods; no torch/environment imports."""
import hashlib,time,json
from pathlib import Path
import numpy as np
TASKS=('reacher','pusht','tworoom','cube')
STREAMS=('R3_ORIGINAL','R4_ALT_CEM_1','R4_ALT_CEM_2')+tuple(f'D1_CEM_STREAM_{i}' for i in range(4,11))
def seed(task,case_id,index,stream):
 if task not in TASKS or stream not in STREAMS or not case_id or type(index)!=int or index<0:raise ValueError('Invalid stream identity')
 ns='R3_CEM_CASE_20261002' if stream==STREAMS[0] else stream
 return int.from_bytes(hashlib.sha256(f'{ns}/{task}/{case_id}/{index}'.encode()).digest()[:8],'big')
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(8<<20),b''):h.update(b)
 return h.hexdigest()
def tensor_record(a):
 a=np.ascontiguousarray(a);return dict(dtype=a.dtype.str,shape=list(a.shape),sha256=hashlib.sha256(a.tobytes()).hexdigest())
def first_equal(a,b):
 a=np.ascontiguousarray(a);b=np.ascontiguousarray(b)
 return a.dtype==b.dtype and a.shape==b.shape and a.tobytes()==b.tobytes()
def history_indices(t,h,block=5):
 if h not in (1,3) or t<0 or t%block:raise ValueError('History must land on action-block boundary')
 return list(range(max(0,t-(h-1)*block),t+1,block))
def history(frames,actions,h,scaler,block=5):
 a=np.asarray(actions);t=len(a);ix=history_indices(t,h,block)
 if len(frames)!=t+1:raise ValueError('N raw actions require N+1 real observations')
 f=np.stack([frames[i] for i in ix]);dim=scaler.n_features_in_
 past=(scaler.transform(a[ix[0]:t]).astype(np.float32).reshape(len(ix)-1,block*dim) if len(ix)>1 else np.empty((0,block*dim),np.float32))
 return f,past,ix

def prefix_candidates(future,past):
 a=np.asarray(future);p=np.asarray(past)
 if a.ndim!=4 or p.ndim!=2 or a.shape[-1]!=p.shape[-1]:raise ValueError('Expected B,S,H,D future; P,D observed prefix')
 if not len(p):return a.copy()
 return np.concatenate([np.broadcast_to(p,(a.shape[0],a.shape[1],*p.shape)),a],axis=2)

def check_case(c,offset=None):
 if c['task'] not in TASKS or not c['case_id']:raise ValueError('Case identity missing')
 actual=c['goal_raw_index']-c['start_raw_index']
 if actual!=25:raise ValueError('Main sealed case must have actual offset25')
 if c['task']!='cube' and (type(c.get('reset_seed'))!=int or not 0<=c['reset_seed']<2**32):raise ValueError('Validated uint32 reset seed required')
 return c['start_raw_index']+(actual if offset is None else offset)

def summarize_steps(steps,expected_budget,stop_at_success):
 if not steps:raise ValueError('Missing trajectory is not failure=0')
 any_success=any(s['success'] for s in steps)
 if len(steps)!=expected_budget and not (stop_at_success and any_success) and not steps[-1]['truncated']:raise ValueError('Incomplete delivery')
 return dict(success_any=int(any_success),success_final=int(steps[-1]['success']),raw_steps=len(steps),final_semantics='last executed state; absorbed on first success' if stop_at_success else 'fixed budget terminal state')
class PlanMeter:
 """Count predictor/encoder/action encoder forwards separately; synchronize wall time."""
 def __init__(self,model,synchronize=lambda:None):
  self.counts={};self.batch={};self.sync=synchronize;self.handles=[]
  for name in ('predictor','encoder','action_encoder'):
   module=getattr(model,name,None)
   if module is None:continue
   self.counts[name]=0;self.batch[name]=0
   def hook(module,args,key=name):
    self.counts[key]+=1
    if args and hasattr(args[0],'shape'):self.batch[key]+=int(args[0].shape[0])
   self.handles.append(module.register_forward_pre_hook(hook))
  if 'predictor' not in self.counts:raise ValueError('Predictor hook unavailable')
 def start(self):
  for key in self.counts:self.counts[key]=0;self.batch[key]=0
  self.sync();self.t=time.perf_counter()
 def end(self):
  self.sync();return dict(predictor_calls=self.counts['predictor'],predictor_batch_elements=self.batch['predictor'],module_forward_calls=self.counts.copy(),module_batch_elements=self.batch.copy(),wall_seconds=time.perf_counter()-self.t)
 def close(self):
  for handle in self.handles:handle.remove()
  self.handles=[]

def validate_asset_identity(assets,method,task,manifest):
 expected_method='LeWM_OFFICIAL' if method=='M03' else method
 matches=[r for r in manifest['assets'] if r.get('method')==expected_method and r['task']==task and r['sha256']==assets['checkpoint_sha256'] and r['filename'].endswith(('.ckpt','.pt'))]
 if len(matches)!=1:raise ValueError('Method/task checkpoint not in frozen registry')
 if method=='M07':
  import re
  seed=int(re.search(r'seed(3072|4096|6144)',matches[0]['filename']).group(1))
  if seed!=int(assets['train_seed']):raise ValueError('Training seed/checkpoint mismatch')
 return matches[0]
