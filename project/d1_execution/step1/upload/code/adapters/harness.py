"""D1 rollout interface for a reset-bound single environment and method planner.
Environment creation/reset is isolated in swm_runtime; no imports execute it.
"""
import numpy as np
from adapters.common import seed,tensor_record,summarize_steps,first_equal

def run_case(env,planner,case,stream,goal,success_fn,budget=50,replan_raw=25,stop_at_success=True,reference_first=None,meter=None,initial_frame=None):
 frames=[np.ascontiguousarray(env.render() if initial_frame is None else initial_frame).copy()];actions=[];steps=[];plans=[];first_raw=None
 while len(actions)<budget:
  if meter:meter.start()
  raw,meta=planner(frames,actions,goal,seed(case['task'],case['case_id'],len(plans),stream))
  if meter:meta.update(meter.end())
  raw=np.asarray(raw)
  if raw.ndim!=2 or len(raw)==0 or not np.isfinite(raw).all():raise ValueError('Invalid plan')
  if not plans:first_raw=raw.copy()
  if not plans and reference_first is not None and not first_equal(raw,reference_first):raise RuntimeError('FIRST_PLAN_BITWISE_GATE')
  meta=dict(meta,raw_t=len(actions),raw_plan=tensor_record(raw));meta.pop('normalized_plan',None);plans.append(meta)
  for a in raw[:min(replan_raw,budget-len(actions))]:
   obs,reward,terminated,truncated,info=env.step(a.copy())
   success=bool(success_fn(obs,info));actions.append(a.copy());frames.append(np.ascontiguousarray(env.render()).copy())
   steps.append(dict(t=len(actions),success=success,terminated=bool(terminated),truncated=bool(truncated)))
   if (stop_at_success and success) or truncated:break
  if steps[-1]['truncated'] or (stop_at_success and steps[-1]['success']):break
 return dict(case_id=case['case_id'],task=case['task'],stream=stream,steps=steps,plans=plans,first_raw_plan=first_raw,raw_actions=np.asarray(actions),**summarize_steps(steps,budget,stop_at_success))
