from pathlib import Path
import pandas as pd, numpy as np
ROOT=Path(__file__).resolve().parent; T=ROOT/'tables'; T.mkdir(exist_ok=True)
S2=ROOT.parent/'d1_execution/step2/resume_03/results'; S4=ROOT.parent/'d1_execution/step4/resume_01/results'
method={'M01':'Fast-LeWM','M03':'AP','M07':'AD-WM','M01_h1':'Fast-LeWM','M03_h1':'AP','M07_h1':'AD-WM','LeWM_h1':'LeWM one-frame','LeWM_h3':'LeWM three-frame'}
task={'reacher':'Reacher','pusht':'PushT','tworoom':'TwoRoom','cube':'Cube'}
def f(x):
    x=float(x); return f'{x:+.1f}' if abs(x-round(x))>1e-8 else f'{x:+.0f}'
def ci(a,b): return f'{float(a):.1f} [{float(b):.1f}, {float(c):.1f}]'
def write(name,s): (T/name).write_text(s)
# tasks table
write('table_tasks.tex',r'''\begin{table*}[t]\centering\caption{The four benchmark tasks and their success tests.}\label{tab:tasks}\small
\begin{tabular}{p{1.2cm}p{3.0cm}p{7.2cm}p{2.2cm}}\toprule
Task & Controlled system & Success test & Budget/offset\\\midrule
Reacher & Two-joint arm & Both joint-angle errors are below $0.05$ rad. & 50 steps; native goal\\
PushT & Pusher and T-shaped block & Position error below 20 pixels and angle error below $\pi/9$. & 50 steps; native goal\\
TwoRoom & Point agent in two rooms & Euclidean image distance below 16 pixels. & 50 steps; native goal\\
Cube & 3-D manipulation & Environment success signal from the released task interface. & 50 steps; native goal\\\bottomrule
\end{tabular}\end{table*}
''')
# literature compact
lit=pd.read_csv(ROOT/'a2_results/A2_LITERATURE_PROTOCOLS.csv')
rows=[]
for _,r in lit.iterrows():
    def clean(x):
        x=str(x).replace('未找到','not specified').replace('未说明','not specified').replace('（不能据此认定与本地判定一致）','').replace('（BASELINE_AUDIT 未单独记录）','')
        
        x=x.replace('引用套件成功判定','source toolkit rule').replace('具体阈值未找到','threshold not specified').replace('本文/所查配置中','source/configuration ').replace('未单独记录','not recorded').replace('候选','candidates').replace('迭代','iterations').replace('检索','retrieval').replace('训练','training').replace('配置','configuration').replace('短视','short-horizon').replace('执行','execute').replace('动作','action').replace('官方','official').replace('排名','rank').replace('未找到','not specified').replace('未说明','not specified')
        x=''.join(ch for ch in x if ord(ch)<128)
        return x.replace('&','\\&').replace('%','\\%')
    rows.append(f"{clean(r.paper)} & {int(r.n_tasks)} & {clean(r.history_frames)[:38]} & {clean(r.cem_and_planner)[:48]} & {clean(r.evaluation_cases)} & {clean(r.evaluation_seeds)} \\\\")
write('table_protocol_literature.tex','''\\begin{table*}[t]\\centering\\caption{Protocol details reported by the literature audit. “Not specified” means that the cited source or released configuration did not provide a value.}\\label{tab:literature}\\scriptsize
\\begin{tabular}{p{2.2cm}c p{2.4cm}p{3.2cm}p{1.2cm}p{1.0cm}}\\toprule
Source & Tasks & History & Planner/CEM & Cases & Seeds\\\\\\midrule
'''+ '\n'.join(rows)+'''\\bottomrule\\end{tabular}\\end{table*}
''')
# reproduction table
rep=pd.read_csv(S2/'ORIGINAL_PROTOCOL_COMPARISONS.csv')
rows=[]
for _,r in rep.iterrows():
    m=method.get(r['method'],r['method']); t=task[r['task']]
    match='yes' if bool(r['absolute_reproduced']) else 'no'
    rows.append(f"{m} & {t} & {r.paper_success_pct:.1f} & {r.success_pct:.1f} [{r.ci95_low_pct:.1f}, {r.ci95_high_pct:.1f}] & {match} \\\\")
write('table_replication_revision.tex','''\\begin{table*}[t]\\centering\\caption{Reproduction under the protocol stated by each source. Intervals are case-level 95\\% intervals; “yes” means the measured absolute value lies in the source tolerance.}\\label{tab:replication}\\small
\\begin{tabular}{llrrc}\\toprule Method & Task & Published (\\%) & Measured (\\%, 95\\% CI) & Match\\\\\\midrule
'''+ '\n'.join(rows)+'''\\bottomrule\\end{tabular}\\end{table*}
''')
# factors table
fac=pd.read_csv(S2/'CONTRASTS.csv')
sel=fac[(fac.cohort=='mixed200')&(fac.family=='factor') & fac.contrast.isin(['h3 - P0','pip - P0','cem - P0','offset - P0','goal - P0','replan1 - P0'])]
fl={'h3 - P0':'History length','pip - P0':'Library version','cem - P0':'CEM iterations','offset - P0':'Goal offset','goal - P0':'Goal image','replan1 - P0':'Native replanning'}
rows=[]
for _,r in sel.iterrows(): rows.append(f"{fl[r.contrast]} & {task[r.task]} & {r.delta_pp:+.1f} [{r.ci95_low_pp:+.1f}, {r.ci95_high_pp:+.1f}] \\\\")
write('table_factor_effects.tex','''\\begin{table*}[t]\\centering\\caption{Paired effects of protocol factors on the mixed 200-case set.}\\label{tab:factors}\\small
\\begin{tabular}{llr}\\toprule Factor & Task & Difference in percentage points (95\\% CI)\\\\\\midrule
'''+ '\n'.join(rows)+'''\\bottomrule\\end{tabular}\\end{table*}
''')
# rankings
kt=pd.read_csv(S4/'KENDALL_TAU.csv')
rows=[]
for _,r in kt.iterrows(): rows.append(f"{task[r.task]} & {r.definitions.replace('any','any-step').replace('block','block-boundary').replace('final','final-step')} & {r.kendall_tau_b:.2f} \\\\")
write('table_rankings_revision.tex','''\\begin{table}[t]\\centering\\caption{Kendall rank correlations between success definitions.}\\label{tab:rankings}\\small
\\begin{tabular}{llr}\\toprule Task & Pair & $\\tau_b$\\\\\\midrule
'''+ '\n'.join(rows)+'''\\bottomrule\\end{tabular}\\end{table}
''')
# success rates table
ar=pd.read_csv(S4/'ABSOLUTE_RATES.csv'); models=['LeWM_h1','LeWM_h3','M01_h1','M03_h1','M07_h1']; rows=[]
for t in ['reacher','pusht','tworoom','cube']:
 for m in models:
  q=ar[(ar.task==t)&(ar.model==m)&(ar.iterations==30)].set_index('definition')
  vals=[q.loc[d,'rate_pct'] for d in ['any','block','final']]
  rows.append(f"{task[t]} & {method[m]} & {vals[0]:.1f} & {vals[1]:.1f} & {vals[2]:.1f} \\\\")
write('table_success_rates_revision.tex','''\\begin{table*}[t]\\centering\\caption{Success rates on the held-out case set under three labels applied to full 50-step trajectories.}\\label{tab:success}\\small
\\begin{tabular}{llrrr}\\toprule Task & Configuration & Any-step (\\%) & Block-boundary (\\%) & Final-step (\\%)\\\\\\midrule
'''+ '\n'.join(rows)+'''\\bottomrule\\end{tabular}\\end{table*}
''')
# predictions
write('table_predictions_revision.tex',r'''\begin{table*}[t]\centering\caption{Three preregistered predictions evaluated on the held-out case set.}\label{tab:predictions}\small
\begin{tabular}{p{4.2cm}p{4.0cm}p{3.4cm}c}\toprule Prediction & Contrast & Estimate (pp, 95\% CI) & Result\\\midrule
History effect is concentrated in Reacher & Three-frame minus one-frame, Reacher & $+12.7$ [$+8.3,+17.3$] & supported\\
History effect is within two points elsewhere & PushT, TwoRoom, Cube & $+0.0,-0.7,+0.3$ & supported\\
Published gains survive common evaluation & AP/AD-WM on TwoRoom and Cube & $+17.7$ to $+27.0$ & supported\\\bottomrule
\end{tabular}\end{table*}
''')
# reporting table
write('table_reporting.tex',r'''\begin{table}[t]\centering\caption{Minimum reporting fields for a reproducible planner evaluation.}\label{tab:reporting}\small
\begin{tabular}{p{3.2cm}p{6.0cm}p{1.5cm}}\toprule
Item & Why it matters & Observed scale\\\midrule
Success test and check times & Defines whether a transient visit counts & 15--76 pp\\
History construction & Changes state information available to the planner & 13 pp in Reacher\\
Planner budget and replanning & Alters the time at which a target is scored & up to 60 pp\\
Cases and random streams & Sets resolution of paired comparisons & $\pm$5 pp\\
Software and aggregation & Determines numerical behavior and uncertainty & 2--4 pp\\\bottomrule
\end{tabular}\end{table}
''')
# complete result compact table
rows=[]
for t in ['reacher','pusht','tworoom','cube']:
 q=ar[(ar.task==t)&(ar.iterations==30)]
 for m in models:
  z=q[q.model==m]
  rows.append(f"{task[t]} & {method[m]} & {z[z.definition=='any'].rate_pct.iloc[0]:.1f} & {z[z.definition=='block'].rate_pct.iloc[0]:.1f} & {z[z.definition=='final'].rate_pct.iloc[0]:.1f} \\\\")
write('table_complete_results_revision.tex','''\\begin{table*}[t]\\centering\\caption{Complete held-out rates used for the main figures.}\\label{tab:complete}\\scriptsize
\\begin{tabular}{llrrr}\\toprule Task & Configuration & Any-step & Block-boundary & Final-step\\\\\\midrule
'''+ '\n'.join(rows)+'''\\bottomrule\\end{tabular}\\end{table*}
''')

# Revision 2 supersedes the earlier table labels and data-source choices.
# Keep this compatibility entry point so existing build commands regenerate the corrected tables.
if __name__ == '__main__':
    import runpy
    runpy.run_path(str(ROOT/'REVISION_2_TABLES.py'), run_name='__main__')
