"""Step2 gate: all paired first raw plans must match dtype, shape and bytes."""
import argparse,json
from pathlib import Path
import numpy as np
from adapters.common import first_equal,sha

def compare(h1,h3,case_ids):
 records=[]
 if len(case_ids)!=len(set(case_ids)) or not case_ids:raise ValueError('Invalid expected cases')
 for case in case_ids:
  a=Path(h1)/(case+'.first_plan.npy');b=Path(h3)/(case+'.first_plan.npy')
  if not first_equal(np.load(a,allow_pickle=False),np.load(b,allow_pickle=False)):raise AssertionError('First-plan mismatch '+case)
  records.append(dict(case_id=case,h1_file_sha256=sha(a),h3_file_sha256=sha(b)))
 return dict(status='PASS',comparison='dtype + shape + raw bytes, no tolerance',cases=records)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--h1',required=True);p.add_argument('--h3',required=True);p.add_argument('--cases',required=True);p.add_argument('--task',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 expected=json.loads(Path(a.cases).read_text());expected=expected['tasks'][a.task] if isinstance(expected,dict) else expected
 Path(a.output).write_text(json.dumps(compare(a.h1,a.h3,[c['case_id'] for c in expected]),indent=2))
