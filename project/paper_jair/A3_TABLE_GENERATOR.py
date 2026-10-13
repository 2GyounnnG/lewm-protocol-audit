"""Generate manuscript tables from sealed results; values are never hand-entered."""
import csv,json
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parent;S4=ROOT/'d1_execution/step4/resume_01/results';S2=ROOT/'d1_execution/step2/resume_03/results';O=P/'tables';O.mkdir(exist_ok=True)
def rows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def find(rs,**kw):return next(r for r in rs if all(r[k]==v for k,v in kw.items()))
def n(x):return f'{float(x):.2f}'
def signed(x):
 v=float(x);return '+0.00' if abs(v)<1e-12 else f'{v:+.2f}'
def ci(r):return f'{signed(r["delta_pp"])} [{signed(r["ci95_low_pp"])}, {signed(r["ci95_high_pp"])}]'
a=rows(S4/'ABSOLUTE_RATES.csv');c=rows(S4/'CONTRASTS.csv');d3=rows(S4/'D3_COHORT_COMPARISON.csv');criteria=rows(S4/'CONFIRMATORY_CRITERIA.csv');orig=rows(S2/'ORIGINAL_PROTOCOL_COMPARISONS.csv')
models=['LeWM_h1','LeWM_h3','M01_h1','M03_h1','M07_h1'];tasks=[('reacher','Reacher'),('pusht','PushT'),('tworoom','TwoRoom'),('cube','Cube')]
with (O/'table_success_rates.tex').open('w') as f:
 f.write('\\begin{table*}[t]\\centering\\caption{HELDOUT success rates on full 50-step trajectories. M07 averages three training seeds within case; other rows have 300 trajectories per task. CI is the case bootstrap percentile interval.}\\label{tab:success}\\begin{tabular}{llrrr}\\toprule Task & Model & Any (\\%) & Block (\\%) & Final (\\%)\\\\\\midrule\n')
 for t,tn in tasks:
  for m in models:
   vals=[]
   for df in ['any','block','final']:
    r=find(a,task=t,model=m,iterations='30',definition=df);vals.append(f'{n(r["rate_pct"])}')
   f.write(f'{tn} & {m.replace("_","\\,")} & '+' & '.join(vals)+' \\\\\n')
 f.write('\\bottomrule\\end{tabular}\\end{table*}\n')
with (O/'table_confirmatory.tex').open('w') as f:
 f.write('\\begin{table*}[t]\\centering\\caption{Preregistered HELDOUT criteria. Entries are paired differences in percentage points with 95\\% case-bootstrap intervals.}\\label{tab:confirmatory}\\begin{tabular}{lllrrr}\\toprule Criterion & Task & Contrast & Estimate & Low & High\\\\\\midrule\n')
 for r in criteria:
  f.write(f'{r["prediction"]} & {r["task"]} & {r["contrast"].replace("_","\\,")} & {signed(r.get("delta_pp",0))} & {signed(r.get("ci95_low_pp",0))} & {signed(r.get("ci95_high_pp",0))} \\\\\n')
 f.write('\\bottomrule\\end{tabular}\\end{table*}\n')
with (O/'table_d3.tex').open('w') as f:
 f.write('\\begin{table*}[t]\\centering\\caption{Selected stream-matched contrasts across original, fresh, and HELDOUT case cohorts.}\\label{tab:d3}\\begin{tabular}{llccc}\\toprule Task & Contrast & Original & Fresh & HELDOUT\\\\\\midrule\n')
 selected=[('reacher','LeWM_h3 - LeWM_h1'),('pusht','LeWM_h3 - LeWM_h1'),('tworoom','LeWM_h3 - LeWM_h1'),('cube','LeWM_h3 - LeWM_h1'),('reacher','LeWM_h3 - M03_h1'),('tworoom','M03_h1 - LeWM_h1'),('cube','M03_h1 - LeWM_h1')]
 for t,name in selected:
  vals=[find(d3,task=t,contrast=name,cohort=x) for x in ['original100','fresh100','HELDOUT100']]
  f.write(f'{t} & {name.replace("_","\\,")} & '+' & '.join(ci(x) for x in vals)+' \\\\\n')
 f.write('\\bottomrule\\end{tabular}\\end{table*}\n')
with (O/'table_replication.tex').open('w') as f:
 f.write('\\begin{table}[t]\\centering\\caption{Reproduction of published absolute values under original protocols.}\\label{tab:replication}\\begin{tabular}{lrrc}\\toprule Method & Task & Published (\\%) & Absolute match\\\\\\midrule\n')
 for r in orig:
  f.write(f'{r["method"]} & {r["task"]} & {n(r["paper_success_pct"])} & {"yes" if r["absolute_reproduced"]=="True" else "no"} \\\\\n')
 f.write('\\bottomrule\\end{tabular}\\end{table}\n')
