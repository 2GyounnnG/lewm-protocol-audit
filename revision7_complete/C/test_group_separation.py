import json,tempfile,copy
from pathlib import Path
from compare_cases import analyze,W
checks=[]
a=analyze(W/'reference_native_traces','main',W/'reference_step2_original128.jsonl');assert len(a['cases'])==128 and a['paper_comparator_pct']==75.8;checks.append('main full128 verified reference accepted')
try:analyze(W/'reference_native_traces','appendix',W/'reference_step2_original128.jsonl');raise RuntimeError('accepted wrong group')
except ValueError:checks.append('appendix rejects main reference')
with tempfile.TemporaryDirectory(prefix='AP_GROUP_TEST_') as td:
 root=Path(td)
 for seed in [42,43,44]:
  p=json.load(open(W/f'protocol_seed{seed}/protocols/main.json'))
  for r in p['studies']['reacher']['confirm']:
   x={'compact':{'identity':r,'completed':True,'horizon':24,'budget':50,'primitive_steps':50,'success':False,'prelude':{'success':False}},'actions':[[0,0]]*50}
   (root/f"{r['record_id']}_clean_gaussian_observed.json").write_text(json.dumps(x))
 b=analyze(root,'appendix');assert b['paper_comparator_pct'] is None and [x['n'] for x in b['per_seed']]==[50,50,50];checks.append('synthetic schema fixtures preserve appendix50 per seed and no75.8 comparator')
 f=next(root.glob('*.json'));x=json.loads(f.read_text());x['compact']['budget']=300;f.write_text(json.dumps(x))
 try:analyze(root,'appendix');raise RuntimeError('accepted mixed budget')
 except AssertionError:checks.append('appendix rejects budget300 contamination')
assert all(x['max_action_difference']==0 and x['first_hit_step']==x['reference_first_hit_step'] for x in a['cases']);checks.append('main action and first-hit self-check128/128')
(W/'GROUP_SEPARATION_TEST_RECEIPT.json').write_text(json.dumps({'status':'PASS','checks':checks,'synthetic_fixtures_not_experimental_results':True},indent=2));print('PASS',len(checks),'group separation checks')
