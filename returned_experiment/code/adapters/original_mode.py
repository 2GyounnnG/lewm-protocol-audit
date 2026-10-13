"""Invoke native evaluation entrypoints unchanged; instrumentation records their own protocol.
Run each method in its isolated venv. This module does nothing on import.
"""
import runpy,sys,json,hashlib,time
from pathlib import Path
import numpy as np
from adapters.common import tensor_record,PlanMeter

def launch(method,repo,argv,trace,mode='adapter_original',record_limit=0):
 repo=Path(repo).resolve();sys.dont_write_bytecode=True
 if mode not in ('native','adapter_original'):raise ValueError(mode)
 if method=='M03':
  sys.path.insert(0,str(repo/'code/ap'))
  from anchored_planning.__main__ import main
  sys.argv=['anchored_planning']+argv
  main() # Native traces already include all raw actions, success, per-decision work.
  Path(trace).write_text(json.dumps(dict(mode=mode,status='NATIVE_TRACE_DIRECTORY_WRITTEN',arguments=argv,normalization='use export_ap_fidelity.py on the two independent trace directories')))
  return
 sys.path.insert(0,str(repo))
 import stable_worldmodel as swm
 records={};calls=[]
 import torch
 from stable_worldmodel.solver import CEMSolver
 native_solve=CEMSolver.solve
 def measured_solve(solver,*a,**kw):
  meter=PlanMeter(solver.model,torch.cuda.synchronize)
  meter.start()
  try:
   result=native_solve(solver,*a,**kw)
   detail=meter.end();detail['plan_batch']=tensor_record(result['actions'].numpy());calls.append(detail)
   return result
  finally:meter.close()
 CEMSolver.solve=measured_solve
 original_init=swm.World.__init__
 def init(world,*args,**kwargs):
  original_init(world,*args,**kwargs)
  native_step=world.envs.step
  def step(actions,*a,**kw):
   # The evaluator has already set actual start/goal and prepared model inputs.
   info=world.infos
   for i in range(min(record_limit,len(actions)) if record_limit else len(actions)):
    if i not in records:
     records[i]=dict(case_id=f'{method}:native_ordinal:{i}',raw_actions=[],steps=[],success=False,reset_sha256=tensor_record(np.asarray(info['pixels'][i]))['sha256'],goal_sha256=tensor_record(np.asarray(info['goal'][i]))['sha256'])
   ans=native_step(actions,*a,**kw)
   for i,r in records.items():
    if not r['success'] and np.isfinite(actions[i]).all():r['raw_actions'].append(np.asarray(actions[i]).tolist());r['success']=bool(ans[2][i]);r['steps'].append(dict(t=len(r['raw_actions']),success=bool(ans[2][i]),truncated=bool(ans[3][i])))
   return ans
  world.envs.step=step
 swm.World.__init__=init
 # Adapter-original delegates every native selection/solver/default; no unified seed injection.
 sys.argv=[str(repo/'eval.py')]+argv
 try:runpy.run_path(str(repo/'eval.py'),run_name='__main__')
 finally:
  Path(trace).write_text(json.dumps(list(records.values()),indent=2));swm.World.__init__=original_init
  CEMSolver.solve=native_solve
  Path(str(trace)+'.plans.json').write_text(json.dumps(calls,indent=2))

def main():
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--method',required=True,choices=['M01','M03','M07']);p.add_argument('--repo',required=True);p.add_argument('--trace',required=True);p.add_argument('--mode',choices=['native','adapter_original'],required=True);p.add_argument('--record-limit',type=int,default=0);p.add_argument('native_args',nargs=argparse.REMAINDER);a=p.parse_args()
 args=a.native_args[1:] if a.native_args[:1]==['--'] else a.native_args
 launch(a.method,a.repo,args,a.trace,a.mode,a.record_limit)
if __name__=='__main__':main()
