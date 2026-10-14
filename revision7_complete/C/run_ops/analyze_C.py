"""Read SHA-verified returned C comparisons; never modify sealed original results."""
import argparse,csv,hashlib,importlib.util,json,datetime
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];W=Path(__file__).resolve().parent;C=W.parent/'C'
p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);a=p.parse_args()
receipt=json.load(open(a.snapshot/'RETURN_VERIFIED.json'));assert receipt['mismatches']==0
statfile=ROOT/'d1_execution/step1/upload/code/tools/statistics_d1.py'
spec=importlib.util.spec_from_file_location('sealed_statistics',statfile);stats=importlib.util.module_from_spec(spec);spec.loader.exec_module(stats)
inputs={};groups={}
for key,file in [('main','MAIN128.json'),('appendix','APPENDIX_42_43_44.json')]:
 f=a.snapshot/'files/comparisons'/file;inputs[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest();groups[key]=json.load(open(f))
def rate(rows):
 y=np.array([r['success'] for r in rows],float);v=stats.paired(y,np.zeros_like(y));return dict(n=len(y),successes=int(y.sum()),pct=v['delta_pp'],ci95_pct=[v['ci95_low_pp'],v['ci95_high_pp']])
m=groups['main']['cases'];ap=groups['appendix']['cases'];assert len(m)==128 and len(ap)==150
protocol=json.load(open(C/'protocol_main128/protocols/main.json'))['studies']['reacher']['confirm'];ordinals={r['record_id']:i for i,r in enumerate(protocol)}
sourcefile=C/'ap_source/data/main_episodes.csv';source={int(r['query_ordinal']):int(r['success']) for r in csv.DictReader(sourcefile.open()) if r['task']=='reacher' and r['controller']=='AP-CEM' and r['condition']=='clean'};assert len(source)==128
src=np.array([source[ordinals[r['record_id']]] for r in m]);new=np.array([r['success'] for r in m],float);old=np.array([r['reference_success'] for r in m],float)
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'main':rate(m),'appendix_by_case_sampling_seed':{str(s):rate([x for x in ap if x['seed']==s]) for s in [42,43,44]},'paper_reported_pct':75.8,'source_recorded_pct':float(src.mean()*100),'main_vs_source_paired':stats.paired(new,src),'main_vs_old_study_paired':stats.paired(new,old),'source_fail_to_new_success':int(((src==0)&(new==1)).sum()),'source_success_to_new_fail':int(((src==1)&(new==0)).sum()),'old_study_success_mismatches':int((new!=old).sum()),'old_study_first_hit_mismatches':sum(x['first_hit_step']!=x['reference_first_hit_step'] for x in m),'old_study_first25_action_mismatch_cases':sum(x['first_action_difference'] is not None for x in m),'old_study_first25_max_absolute_action_difference':max(x['max_action_difference'] or 0 for x in m),'stat_function_sha256':hashlib.sha256(statfile.read_bytes()).hexdigest(),'bootstrap':{'replicates':5000,'seed':20261011,'unit':'case within each cohort, appendix seeds separately'},'input_sha256':inputs,'source_record_sha256':hashlib.sha256(sourcefile.read_bytes()).hexdigest(),'snapshot_receipt':receipt,'no_existing_numbers_changed':True}
out=W/'C_FINAL_ANALYSIS.json';assert not out.exists(),'Keep existing analysis; choose revision explicitly';out.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['snapshot_receipt','input_sha256']},indent=2))
