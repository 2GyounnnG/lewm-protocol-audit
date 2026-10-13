import json,argparse,hashlib
from pathlib import Path

def export(folder,task,out):
 traces=[]
 for f in sorted((Path(folder)/'traces'/task).glob('*_gaussian_observed.json')):
  d=json.loads(f.read_text());c=d['compact']
  if c['condition']!='clean':continue
  identity=c['identity'];raw=json.dumps(identity,sort_keys=True).encode()
  traces.append(dict(case_id=identity['record_id'],raw_actions=d['actions'],success=c['success'],reset_sha256=hashlib.sha256(raw).hexdigest(),goal_sha256=hashlib.sha256(str(identity['global_goal']).encode()).hexdigest()))
 if len(traces)<4:raise ValueError('Four clean AP-CEM traces not found; check original protocol condition label')
 Path(out).write_text(json.dumps(traces[:4],indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--task',required=True);p.add_argument('--output',required=True);a=p.parse_args();export(a.folder,a.task,a.output)
