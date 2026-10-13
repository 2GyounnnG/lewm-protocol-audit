"""Compare independently generated native/adapter-original traces; never runs a model.
Each JSON has four episodes {case_id,raw_actions,success,reset_sha256,goal_sha256}.
Step2 launcher creates traces with native eval and instrumented original mode.
"""
import argparse,json
from pathlib import Path
import numpy as np
from adapters.common import first_equal
ATOL=1e-6;RTOL=1e-5

def compare(native,adapt):
 if len(native)!=4 or len(adapt)!=4:raise ValueError('Exactly four original-protocol episodes required')
 if len({r['case_id'] for r in native})!=4:raise ValueError('Duplicate fidelity episodes')
 logs=[]
 for a,b in zip(native,adapt):
  for k in ('case_id','reset_sha256','goal_sha256','success'):
   if k not in a or a[k]!=b.get(k):raise AssertionError('Fidelity metadata '+k)
  x=np.asarray(a['raw_actions']);y=np.asarray(b['raw_actions'])
  if x.size==0 or x.shape!=y.shape or not np.isfinite(x).all() or not np.isfinite(y).all():raise AssertionError('Missing or invalid actions')
  np.testing.assert_allclose(x,y,atol=ATOL,rtol=RTOL)
  logs.append(dict(case_id=a['case_id'],max_abs=float(np.max(np.abs(x-y))),success=a['success']))
 return dict(status='PASS',atol=ATOL,rtol=RTOL,episodes=logs)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--native',required=True);p.add_argument('--adapter',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 r=compare(json.loads(Path(a.native).read_text()),json.loads(Path(a.adapter).read_text()));Path(a.output).write_text(json.dumps(r,indent=2))
