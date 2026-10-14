from pathlib import Path
import json,numpy as np
W=Path(__file__).resolve().parent
root=W/'outputs/tech_profile';r=json.load(open(root/'run_reacher_shard0of1.json'));s=json.load(open(root/'summary_reacher_shard0of1.json'))
assert r['device']=='cuda:0' and r['task']=='reacher' and s['completed'] and s['outcomes']==3
expected={'stable-worldmodel':'0.0.6','mujoco':'3.10.0','dm-control':'1.0.43','torch':'2.7.1+cu128'}
assert all(r['dependencies'][k]==v for k,v in expected.items())
protocol=json.load(open(W/'protocol_main128/protocols/main.json'))['studies']['reacher']['confirm'][:3]
rows=[]
for case in protocol:
 p=root/'traces/reacher'/f"{case['record_id']}_clean_gaussian_observed.json";d=json.load(open(p));c=d['compact'];assert c['identity']==case and c['completed'] and c['budget']==300 and c['horizon']==150
 a=np.asarray(d['actions'],float).reshape(-1,2);assert len(a)==c['primitive_steps']<=300 and np.isfinite(a).all() and (np.abs(a)<=1.000001).all()
 assert c['predictor_calls']==31*c['decisions'] and c['predictor_candidate_blocks']==9002*c['decisions'];assert c['source_prediction_misses']==0 and len(d['decisions'])==c['decisions']
 rows.append({'case':case['record_id'],'success':c['success'],'steps':len(a),'decisions':c['decisions']})
(W/'TECH_ENTRY_GATE.json').write_text(json.dumps({'status':'PASS','checks':['pinned runtime versions','three exact main identities','finite bounded actions and budget','31 predictor batches / 9002 candidate blocks per decision','no source prediction misses','complete native-entry outputs'],'records':rows},indent=2));print('TECH_ENTRY_GATE PASS')
