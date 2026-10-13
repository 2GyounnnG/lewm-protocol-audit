"""Synthetic checks only; does not inspect or analyze formal experiment output."""
import importlib.util
from pathlib import Path
import numpy as np

p=Path(__file__).with_name('analyze_corrected_reacher.py')
s=importlib.util.spec_from_file_location('corrected_analysis',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

# A first-microstep hit can be absent at its environment-step endpoint.
any_label=np.zeros(50,bool);end_label=np.zeros(50,bool);any_label[-1]=True
r=m.trajectory_metrics(any_label,end_label)
assert r['any']==1 and r['final']==0 and r['block']==0
assert r['or_final']==1 and r['hit_eligible_for_later_step']==0
assert r['hit_and_later_step_exit']==0
assert r['hit_and_exit_by_any_endpoint']==1

# All-K is nonlinear: compute per checkpoint, never threshold their average.
seeds=np.zeros((3,50),bool);seeds[0,-5:]=True
per_seed=[m.trajectory_metrics(a,a) for a in seeds]
assert np.mean([x['last5_all'] for x in per_seed])==1/3
assert np.mean([x['any'] for x in per_seed])==1/3
assert m.trajectory_metrics(seeds.any(0),seeds.any(0))['any']==1

# A real hit then departure enters the conditional exit numerator/denominator.
a=np.zeros(50,bool);a[4]=True
r=m.trajectory_metrics(a,a)
assert r['hit_eligible_for_later_step']==1 and r['hit_and_later_step_exit']==1
assert r['hit_and_later_outside_fraction']==1

# Shared case draws reproduce the sealed bootstrap function, including its RNG.
stats,reps,seed=m.load_statistics()
v=np.linspace(-1,1,100)+.071
idx=np.random.default_rng(seed).integers(0,100,(reps,100))
draw=v[idx].mean(1)*100
expected=stats.paired(v,np.zeros_like(v))
lo,hi=np.quantile(draw,[.025,.975])
assert abs(lo-expected['ci95_low_pp'])<1e-12
assert abs(hi-expected['ci95_high_pp'])<1e-12
print('PASS: endpoint semantics, no-observable-future exclusion, per-seed nonlinear metrics, frozen bootstrap RNG')
