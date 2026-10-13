"""Read-only V1.2 PushT reset provenance and post-settle offsets; never mutates physics."""
import hashlib,inspect
from pathlib import Path
import numpy as np
from adapters.common import tensor_record

def describe_pusht(env,start,goal):
 assert '_set_state' not in env.__dict__ and not getattr(env,'_d1_exact_start_installed',False)
 assert env._set_state.__func__ is type(env)._set_state
 source=Path(inspect.getsourcefile(type(env)._set_state))
 assert 'stable_worldmodel' in str(source) and source.name=='env.py'
 actual=np.asarray(tuple(env.agent.position)+tuple(env.block.position)+(env.block.angle,)+tuple(env.agent.velocity),np.float64)
 expected=np.asarray(start);target=np.asarray(env.goal_state);g=np.asarray(goal)
 assert actual.shape==expected.shape and np.isfinite(actual).all()
 assert np.array_equal(target,g),'Native goal identity changed'
 return dict(prereg_version='1.2',procedure='native library _set_state including internal settle step',adapter_override=False,native_setter_module=type(env)._set_state.__module__,native_setter_source=str(source),native_setter_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),post_reset=tensor_record(actual),post_reset_state=actual.tolist(),manifest_start=tensor_record(expected),offset=(actual-expected).tolist(),max_abs_offset=float(np.max(np.abs(actual-expected))),goal_state=tensor_record(target),goal_state_exact=True)
