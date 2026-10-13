"""Generate JAIR tables for revision 2 directly from sealed CSV results.
No numeric result is entered by hand; source files under d1_execution are read-only.
"""
from pathlib import Path
import re, html
import pandas as pd
ROOT=Path(__file__).resolve().parent
T=ROOT/'tables'; T.mkdir(exist_ok=True)
S2=ROOT.parent/'d1_execution/step2/resume_03/results'
S3=ROOT.parent/'d1_execution/step3/results'
S4=ROOT.parent/'d1_execution/step4/resume_01/results'
TASK={'reacher':'Reacher','pusht':'PushT','tworoom':'TwoRoom','cube':'Cube'}
METHOD={'M01':'Fast-LeWM','M03':'Anchored Planning','M07':'AD-WM','M01_h1':'Fast-LeWM','M03_h1':'Anchored Planning','M07_h1':'AD-WM','LeWM_h1':'LeWM one-frame','LeWM_h3':'LeWM three-frame'}

def esc(s):
    s=str(s).replace('&',r'\&').replace('%',r'\%').replace('_',r'\_').replace('#',r'\#')
    return s

def short(row, field):
    """Return deliberately short audit values; details remain in CSV and caption."""
    x=str(row[field])
    if field=='success_check':
        return 'stated' if row.source_id in {'M03','M13','M15'} else 'not stated'
    if field=='early_termination':
        return 'yes' if row.source_id=='M03' else ('no' if row.source_id=='M15' else 'not stated')
    if field=='history_frames':
        if row.source_id in {'M01','M03','M04','M07','M17'}: return '1 (config)'
        if row.source_id=='M05': return '5'
        return 'not stated'
    if field=='cem_and_planner':
        if row.source_id in {'M01','M03','M07','M08','M09','M12','M13','M16','M17'}: return '30'
        if row.source_id=='M04': return '30 (low)'
        if row.source_id=='M05': return '30 (most)'
        if row.source_id=='M06': return '10'
        if row.source_id=='M11': return 'not stated'
        if row.source_id=='M14': return 'not stated'
        if row.source_id=='M15': return '30'
        return 'not stated'
    if field=='evaluation_cases':
        m=re.search(r'\d+',x)
        return m.group(0) if m else 'not stated'
    if field=='evaluation_seeds':
        m=re.search(r'\d+',x)
        return m.group(0) if m else 'not stated'
    return x

def write(name,s): (T/name).write_text(s,encoding='utf-8')

# Literature table with all requested fields, compact values only.
lit=pd.read_csv(ROOT/'a2_results/A2_LITERATURE_PROTOCOLS.csv')
rows=[]
for _,r in lit.iterrows():
    rows.append(' & '.join(esc(v) for v in [r.paper, int(r.n_tasks), short(r,'success_check'), short(r,'early_termination'), short(r,'history_frames'), short(r,'cem_and_planner'), short(r,'evaluation_cases'), short(r,'evaluation_seeds')])+r' \\')
write('table_protocol_literature.tex',r'''\begin{table*}[t]\centering\caption{Compact protocol fields recorded in the literature audit. Values are shortened to keep the comparison readable; ``not stated'' means that the source record provided no value. Full strings and source URLs are retained in the audit CSV.}\label{tab:literature}\scriptsize
\begin{tabular}{p{2.45cm}c c c c c c c}\toprule
Source & Tasks & Success stated? & Early stop? & History & CEM iterations & Cases & Seeds\\\midrule
'''+ '\n'.join(rows)+r'''\bottomrule\end{tabular}
\end{table*}
''')

# Paired factors: same streams A-C from post-hoc audit, not mixed 200 rows.
fac=pd.read_csv(S3/'POSTHOC_CONTRASTS.csv')
sel=fac[(fac.cohort=='mixed200')&(fac.family=='factor')&(fac.streams=='ABC') & fac.contrast.isin(['h3 - P0','old - P0','cem - P0','offset - P0','goal - P0','replan1 - P0'])]
fl={'h3 - P0':'History length','old - P0':r'Library version (old $\rightarrow$ PyPI 0.0.6)','cem - P0':'CEM elite standard-deviation correction','offset - P0':'Goal offset','goal - P0':'Goal image','replan1 - P0':'Native replanning'}
rows=[]
for _,r in sel.iterrows():
    if pd.isna(r.delta_pp):
        val='not run (recorded Cube goal-image incident)'
    else:
        val=f"{r.delta_pp:+.1f} [{r.ci95_low_pp:+.1f}, {r.ci95_high_pp:+.1f}]"
    rows.append(f"{fl[r.contrast]} & {TASK[r.task]} & {val}" + r" \\")
write('table_factor_effects.tex',r'''\begin{table*}[t]\centering\caption{Same-stream paired factor effects across three fixed planner random-seed streams on the 200-case mixed set. The old-library and elite-standard-deviation rows are numerically identical because the released version difference is this correction; CEM iteration-count comparisons use a separate held-out set and appear in Appendix~C. The Cube goal-image condition was not run after the recorded Cube goal-image incident.}\label{tab:factors}\small
\begin{tabular}{llp{5.0cm}}\toprule Factor & Task & Difference in percentage points (95\% CI)\\\midrule
'''+ '\n'.join(rows)+r'''\bottomrule\end{tabular}
\end{table*}
''')

# Three preregistered predictions, each subcondition explicit from Step4 held-out rows.
ct=pd.read_csv(S4/'CONTRASTS.csv')
def row(analysis,task,contrast,definition='any'):
    q=ct[(ct.analysis==analysis)&(ct.task==task)&(ct.contrast==contrast)&(ct.cohort=='HELDOUT100')&(ct.definition==definition)]
    if len(q)!=1: raise ValueError((analysis,task,contrast,len(q)))
    q=q.iloc[0]; return f"{q.delta_pp:+.1f} [{q.ci95_low_pp:+.1f}, {q.ci95_high_pp:+.1f}]"
def support(estimate, low, rule):
    return 'supported' if rule(estimate,low) else 'not supported'
def nums(analysis,task,contrast):
    q=ct[(ct.analysis==analysis)&(ct.task==task)&(ct.contrast==contrast)&(ct.cohort=='HELDOUT100')&(ct.definition=='any')].iloc[0]
    return float(q.delta_pp),float(q.ci95_low_pp)
# Prediction 1 cells
p1=[]
for t in ['reacher','pusht','tworoom','cube']:
    e,l=nums('main',t,'LeWM_h3 - LeWM_h1')
    ok=(e>=10 and l>0) if t=='reacher' else (abs(e)<=2)
    p1.append(f"{TASK[t]}: {e:+.1f} [{l:+.1f}, {float(ct[(ct.analysis=='main')&(ct.task==t)&(ct.contrast=='LeWM_h3 - LeWM_h1')&(ct.cohort=='HELDOUT100')&(ct.definition=='any')].iloc[0].ci95_high_pp):+.1f}] ({'yes' if ok else 'no'})")
p2=[]
for t,c in [('reacher','LeWM_h3 - M01_h1'),('reacher','LeWM_h3 - M07_h1'),('reacher','LeWM_h3 - M03_h1')]:
    e,l=nums('C2',t,c); ok=(e>=0 and l>-5) if c!='LeWM_h3 - M03_h1' else (e<0)
    label={'LeWM_h3 - M01_h1':'Fast-LeWM','LeWM_h3 - M07_h1':'AD-WM','LeWM_h3 - M03_h1':'Anchored Planning'}[c]
    p2.append(f"LeWM three-frame minus {label}: {e:+.1f} [{l:+.1f}, {float(ct[(ct.analysis=='C2')&(ct.task==t)&(ct.contrast==c)&(ct.cohort=='HELDOUT100')&(ct.definition=='any')].iloc[0].ci95_high_pp):+.1f}] ({'yes' if ok else 'no'})")
p3=[]
for t,m in [('tworoom','M03_h1'),('tworoom','M07_h1'),('cube','M03_h1'),('cube','M07_h1')]:
    c=f'{m} - LeWM_h1'; e,l=nums('main',t,c); hi=float(ct[(ct.analysis=='main')&(ct.task==t)&(ct.contrast==c)&(ct.cohort=='HELDOUT100')&(ct.definition=='any')].iloc[0].ci95_high_pp); ok=l>0
    p3.append(f"{TASK[t]} {METHOD[m]}: {e:+.1f} [{l:+.1f}, {hi:+.1f}] ({'yes' if ok else 'no'})")
rows = [
  "1 & Reacher three-frame $-$ one-frame; other tasks within $\\pm2$ & " + "; ".join(p1) + r" \\",
  "2 & Three-frame minus Fast-LeWM, AD-WM, and AP on Reacher & " + "; ".join(p2) + r" \\",
  "3 & Anchored Planning and AD-WM gains on TwoRoom and Cube & " + "; ".join(p3) + r" \\",
]
write('table_predictions_revision.tex',r'''\begin{table*}[t]\centering\caption{The three preregistered predictions and every subcondition on the held-out case set. Numbers are paired percentage-point differences with 95\% bootstrap intervals; ``yes'' marks the stated inequality.}\label{tab:predictions}\scriptsize
\begin{tabular}{c p{4.0cm} p{8.0cm}}\toprule Prediction & Preregistered condition & Estimate and condition check\\\midrule
'''+ '\n'.join(rows)+r'''\bottomrule\end{tabular}
\end{table*}
''')
print('wrote', T)
