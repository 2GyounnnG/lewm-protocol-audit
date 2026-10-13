"""Verify A1 any/block/final labels against sealed Step4 RAW_TRAJECTORIES.csv."""
import csv,json,hashlib,datetime
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
rawp=ROOT/'d1_execution/step4/resume_01/results/RAW_TRAJECTORIES.csv'
a1p=ROOT/'paper_jair/a1_results/A1_TRAJECTORY_SUMMARY.csv'
ratep=ROOT/'d1_execution/step4/resume_01/results/ABSOLUTE_RATES.csv'
with rawp.open(encoding='utf-8-sig') as f: raw=list(csv.DictReader(f))
with a1p.open(encoding='utf-8-sig') as f: a1=list(csv.DictReader(f))
lookup={}
for r in raw:
    key=(r['task'],r['model'],r['history'],r['iterations'],r['case_id'],r['stream'])
    lookup.setdefault(key,[]).append(r)
mapm={'LeWM_h1':('LeWM','1','30'),'LeWM_h3':('LeWM','3','30'),'M01_h1':('M01','1','30'),'M03_h1':('M03','1','30'),'M07_h1':('M07','1','30')}
mism=[]; nseed_mism=[]
for r in a1:
    bm,h,it=mapm[r['model']]
    rr=lookup.get((r['task'],bm,h,it,r['case_id'],r['stream']),[])
    if len(rr)!=(3 if bm=='M07' else 1):
        nseed_mism.append({'key':(r['task'],bm,h,it,r['case_id'],r['stream']),'got':len(rr),'expected':3 if bm=='M07' else 1}); continue
    vals={k:np.mean([float(x[k]) for x in rr]) for k in ('success_any','success_block','success_final')}
    for k in ('success_any','success_block','success_final'):
        got=int(float(r[k]))
        exp=int(vals[k]>0) if k!='success_final' else int(vals[k]>0)
        if got!=exp:
            mism.append({'model':r['model'],'task':r['task'],'case_id':r['case_id'],'stream':r['stream'],'field':k,'a1':got,'raw_seed_mean':vals[k],'raw': [x[k] for x in rr]})
# compare aggregate group counts to ABSOLUTE_RATES for every A1 group
with ratep.open(encoding='utf-8-sig') as f: rates=list(csv.DictReader(f))
rateidx={(x['task'],x['model'],x['iterations'],x['definition']):x for x in rates}
agg=[]; rate_mism=[]
for model,(bm,h,it) in mapm.items():
  for task in sorted({x['task'] for x in a1 if x['model']==model}):
    rows=[x for x in a1 if x['model']==model and x['task']==task]
    for d,field in [('any','success_any'),('block','success_block'),('final','success_final')]:
      got=sum(int(float(x[field])) for x in rows)
      # raw trajectory denominator 300; M07 rate table reports 900 seed trajectories,
      # so compare raw successful trajectories and A1 row labels separately.
      target=rateidx.get((task,bm,it,d))
      raw_n=sum(int(float(x['success_'+d])) for x in raw if x['task']==task and x['model']==bm and x['history']==h and x['iterations']==it)
      expected_den=900 if bm=='M07' else 300
      if target and int(target['successful_trajectories'])!=raw_n:
        rate_mism.append({'task':task,'model':bm,'definition':d,'absolute_rates':int(target['successful_trajectories']),'raw':raw_n})
      agg.append({'model':model,'task':task,'definition':d,'a1_case_stream_successes':got,'a1_rows':len(rows),'raw_seed_successes':raw_n,'raw_denominator':expected_den})
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'raw_path':str(rawp),'raw_sha256':hashlib.sha256(rawp.read_bytes()).hexdigest(),'a1_path':str(a1p),'a1_sha256':hashlib.sha256(a1p.read_bytes()).hexdigest(),'raw_rows':len(raw),'a1_rows':len(a1),'row_label_mismatches':len(mism),'seed_count_mismatches':len(nseed_mism),'absolute_rate_mismatches':len(rate_mism),'all_match':not (mism or nseed_mism or rate_mism),'details':{'row_label_mismatches':mism[:20],'seed_count_mismatches':nseed_mism[:20],'absolute_rate_mismatches':rate_mism[:20],'aggregates':agg}}
(ROOT/'paper_jair/a1_results/A1_VERIFY_RAW.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'raw_rows':len(raw),'a1_rows':len(a1),'row_label_mismatches':len(mism),'seed_count_mismatches':len(nseed_mism),'absolute_rate_mismatches':len(rate_mism),'all_match':result['all_match']},ensure_ascii=False))
