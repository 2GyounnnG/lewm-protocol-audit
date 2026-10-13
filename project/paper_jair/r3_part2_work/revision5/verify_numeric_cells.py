from pathlib import Path
import json,re,pandas as pd,numpy as np
W=Path(__file__).resolve().parent;P=W.parents[1]/'revision3_part2';A=W.parent/'analysis_final';B=W.parent/'paper_assets_final_v2';mac=json.loads((W/'EFFECTIVE_MACROS.json').read_text());checks=[]
def expand(s):
 for _ in range(8):
  new=re.sub(r'\\([A-Za-z]+)(?:\{\})?',lambda m:mac.get(m[1],m[0]),s)
  if new==s:break
  s=new
 return s
models={'LeWM one-frame':'LeWM_h1','LeWM three-frame':'LeWM_h3','Fast-LeWM':'M01_h1','AP':'M03_h1','AD-WM':'M07_h1'}
def rows(f):return [expand(x).split(' & ') for x in (P/'tables'/f).read_text().splitlines() if ' & ' in x]
def nums(c):return [float(x) for x in re.findall(r'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?',c)]
def check(label,got,want):
 assert len(got)==len(want),(label,got,want)
 assert np.allclose(got,want,atol=.05000001,rtol=0),(label,got,want)
 checks.append({'check':label,'numbers':len(want),'status':'PASS'})
rates=pd.read_csv(A/'ABSOLUTE_RATES.csv');old=pd.read_csv(A/'ABSOLUTE_RATES_OLD.csv')
for r in rows('table_success_rates_revision.tex'):
 if r[0]=='Reacher':
  q=rates[(rates.model==models[r[1]])&(rates.iterations==30)].set_index('definition');check('rate '+r[1],[nums(c)[0] for c in r[2:]],q.loc[['any','block','final'],'rate_pct'].tolist())
for r in rows('table_reacher_termination_correction.tex'):
 if r[0] in models:
  want=[]
  for df in [old,rates]:want+=df[(df.model==models[r[0]])&(df.iterations==30)].set_index('definition').loc[['any','block','final'],'rate_pct'].tolist()
  check('invalid/corrected '+r[0],[nums(c)[0] for c in r[1:]],want)
term=pd.read_csv(B/'data/TERMINAL_WINDOWS_ALL_TASKS.csv')
for r in rows('table_terminal_window.tex'):
 if r[0]=='Reacher':
  q=term[(term.task=='reacher')&(term.model==models[r[1]])].iloc[0];keys=['last5_occupancy_pct','last10_occupancy_pct','last5_all_pct','last10_all_pct','exit_after_first_hit_pct','outside_fraction_after_first_hit_pct'];check('terminal '+r[1],[nums(c)[0] for c in r[2:]],[q[k] for k in keys])
win=pd.read_csv(W.parent/'revision4/A_MAIN_WINDOW_TABLE.csv')
for r in rows('table_window_main.tex'):
 if r[0]=='Reacher':
  q=win[(win.task=='reacher')&(win.model==models[r[1]])].iloc[0];check('window '+r[1],[nums(c)[0] for c in r[2:]],[q[k] for k in ['final','last10_occupancy','last5_all','last10_all']])
co=pd.read_csv(A/'CONTRASTS.csv');keys=['LeWM_h3 - LeWM_h1','LeWM_h3 - M01_h1','LeWM_h3 - M03_h1','LeWM_h3 - M07_h1'];i=0
for r in rows('table_predictions_revision.tex'):
 if len(r)>1 and 'Reacher' in r[1]:
  q=co[(co.contrast==keys[i])&(co.definition=='any')].iloc[0];check('prediction '+keys[i],nums(r[3]),[q[k] for k in ['delta_pp','ci95_low_pp','ci95_high_pp']]);i+=1
assert i==4
# Compare all A intervals against the frozen function's generated outputs.
ai=pd.read_csv(W.parent/'revision4/A_WINDOW_PAIRED_INTERVALS.csv')
for i,suffix in enumerate(['One','Two','Three','Four','Five','Six','Seven','Eight']):
 q=ai.iloc[i];check('A interval '+suffix,nums(mac['RfourWindow'+suffix]),[q[k] for k in ['delta_pp','ci95_low_pp','ci95_high_pp']])
for r in pd.read_csv(W/'TABLE16_UNIFIED_SEED.csv').to_dict('records'):
 check('Table16 '+r['macro'],nums(mac[r['macro']]),[r[k] for k in ['delta_pp','ci95_low_pp','ci95_high_pp']])
new=pd.read_csv(W/'FIG5_THREE_LABEL_CONTRASTS.csv').query("metric == 'last10_all'")
for i,r in enumerate(new.to_dict('records')):
 check('Figure5 window '+r['task']+' '+r['model'],nums(mac['RfiveWindow'+chr(65+i)]),[r[k] for k in ['delta_pp','ci95_low_pp','ci95_high_pp']])
report={'status' :'PASS','rows_checked':len(checks),'numbers_checked':sum(x['numbers'] for x in checks),'checks':checks,'tolerance':'0.05 percentage points (one-decimal rendering), exact source float CSVs retained'}
(W/'NUMERIC_CELL_VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');print(report['rows_checked'],report['numbers_checked'],'PASS')
