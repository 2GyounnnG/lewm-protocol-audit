"""Portable saved-record CPU check; never executes a model or environment."""
from pathlib import Path
import argparse,csv,json,hashlib,importlib.util
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--output',type=Path,required=True);p.add_argument('--verify-traces',action='store_true');a=p.parse_args();root=a.root
f=root/'statistics_d1.py';assert hashlib.sha256(f.read_bytes()).hexdigest()=='58855f7cff9188d6dc0c0f2838f3de6c1a5d6e49793bf0166eabe5a814c6abf3'
spec=importlib.util.spec_from_file_location('frozen',f);stats=importlib.util.module_from_spec(spec);spec.loader.exec_module(stats)
rows=list(csv.DictReader((root/'case_outcomes.csv').open()));groups={k:[r for r in rows if r['group']==k] for k in ['main128','appendix42','appendix43','appendix44','egl50']};assert [len(v) for v in groups.values()]==[128,50,50,50,50]
def y(g,key='success'):return np.array([float(r[key]) for r in g])
def rate(g):
 x=y(g);v=stats.paired(x,np.zeros_like(x));return dict(n=len(x),successes=int(x.sum()),pct=v['delta_pp'],ci95_pct=[v['ci95_low_pp'],v['ci95_high_pp']])
main=groups['main128'];egl=groups['egl50'];lookup={r['case_id']:r for r in main};base=[lookup[r['case_id']] for r in egl]
out={'main':rate(main),'appendix_by_case_sampling_seed':{s:rate(groups['appendix'+s]) for s in ['42','43','44']},'main_vs_source_paired':stats.paired(y(main),y(main,'paper_success')),'main_vs_old_study_paired':stats.paired(y(main),y(main,'reference_success')),'egl_minus_osmesa':stats.paired(y(egl),y(base)),'egl_rate':rate(egl),'osmesa_rate':rate(base)}
expected=json.loads((root/'results/C_FINAL_ANALYSIS.json').read_text());renderer=json.loads((root/'results/RENDERER_FINAL_ANALYSIS.json').read_text())
for k in ['main','appendix_by_case_sampling_seed','main_vs_source_paired','main_vs_old_study_paired']:assert out[k]==expected[k],k
assert out['egl_minus_osmesa']==renderer['egl_minus_osmesa']
for key in ['egl','osmesa']:
 for k,v in [('pct','delta_pp'),('ci95_pct',None)]:
  if v:assert out[key+'_rate'][k]==renderer[key+'_rate'][v]
  else:assert out[key+'_rate'][k]==[renderer[key+'_rate']['ci95_low_pp'],renderer[key+'_rate']['ci95_high_pp']]
if a.verify_traces:
 refs={r['record_id']:r for r in map(json.loads,(root/'reference_step2_original128.jsonl').read_text().splitlines())};bitwise=0;checked=0
 for group,rr in groups.items():
  prefix={'main128':'main128','egl50':'diagnostics/egl50'}.get(group,'appendix/seed'+group[-2:])
  for r in rr:
   tr=json.loads((root/'outputs'/prefix/'traces/reacher'/(r['case_id']+'_clean_gaussian_observed.json')).read_text());c=tr['compact'];assert c['completed'] and int(c['success'])==int(r['success']);assert c['identity']['record_id']==r['case_id'];checked+=1
   if group=='egl50':
    x=np.asarray(tr['actions'],dtype='<f8');ref=refs[r['case_id']];z=np.asarray(ref['actions'],dtype='<f8');assert x.shape==z.shape and x.tobytes()==z.tobytes();assert (len(x) if c['success'] else None)==ref['first_hit_step'];bitwise+=1
 assert checked==328 and bitwise==50;out['trace_check']={'checked':checked,'old_egl_all_actions_bitwise_equal':bitwise}
out['all_expected_statistics_exact_equal']=True
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2));print(json.dumps({'all_expected_statistics_exact_equal':True,'trace_check':out.get('trace_check')}))
