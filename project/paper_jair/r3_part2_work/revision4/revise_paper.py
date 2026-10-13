from pathlib import Path
import re,json,csv,hashlib,datetime
import pandas as pd
W=Path(__file__).resolve().parent;ROOT=W.parents[2];P=ROOT/'paper_jair/revision3_part2';A=W.parent/'analysis_final';B=W.parent/'paper_assets_final_v2';R=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/returns/STAGE3_VERIFIED/experiment')
assert json.loads((W/'C1_FULL_AUDIT.json').read_text())['status']=='PASS'
assert json.loads((W/'D_FIRST25_SUMMARY.json').read_text())['first25_action_mismatch_pairs']==0
mac={}
# Resolve existing macro layers into one authoritative file. Parse balanced braces.
for path in [P/'a3_results'/n for n in ['numbers.tex','revision3_pair_stats.tex','revision3_corrected_numbers.tex','revision3_corrected_narrative.tex','revision3_runtime_narrative.tex']]:
 s=path.read_text()
 for m in re.finditer(r'\\(newcommand|renewcommand|providecommand)\{\\([A-Za-z]+)\}\{',s):
  start=m.end();i=start;depth=1
  while depth:
   if s[i]=='{' and s[i-1]!='\\':depth+=1
   elif s[i]=='}' and s[i-1]!='\\':depth-=1
   i+=1
  if m[1]!='providecommand' or m[2] not in mac:mac[m[2]]=s[start:i-1]
def fmt(x,sign=False):return '0.0' if abs(float(x))<.05 else format(float(x),'+.1f' if sign else '.1f')
def ci(r):return f"{fmt(r['delta_pp'],True)} [{fmt(r['ci95_low_pp'],True)}, {fmt(r['ci95_high_pp'],True)}]"
labels={'LeWM_h1':'LeWM one-frame','LeWM_h3':'LeWM three-frame','M01_h1':'Fast-LeWM','M03_h1':'AP','M07_h1':'AD-WM'}
# A: directly generated table cells and interval macros.
window=pd.read_csv(W/'A_MAIN_WINDOW_TABLE.csv');ints=pd.read_csv(W/'A_WINDOW_PAIRED_INTERVALS.csv')
letters=['One','Three','Fast','AP','AD'];tasks={'reacher':'Reacher','pusht':'PushT'}
rows=[]
for t in tasks:
 for model,l in zip(labels,letters):
  r=window[(window.task==t)&(window.model==model)].iloc[0];cells=[]
  for metric,key in [('final','Final'),('last10_occupancy','OccTen'),('last5_all','AllFive'),('last10_all','AllTen')]:
   name=f'Rfour{tasks[t]}{l}{key}';mac[name]=fmt(r[metric]);cells.append('\\'+name+'{}')
  rows.append(' & '.join([tasks[t],labels[model]]+cells)+r' \\')
(P/'tables/table_window_main.tex').write_text(r'''\begin{table}[t]\centering\small
\caption{Endpoint and sustained-window occupancy on the same trajectories (percent). Means and nonlinear all-window labels are computed per trajectory before case-level checkpoint and stream averaging. These are descriptive corrected comparisons.}
\label{tab:window-main}
\begin{tabular}{llrrrr}\toprule
Task & Configuration & Final step & Mean last 10 & All last 5 & All last 10 \\\midrule
'''+ '\n'.join(rows)+r'\bottomrule\end{tabular}\end{table}'+'\n')
rows=[]
for i,r in ints.iterrows():
 key='RfourWindow'+['One','Two','Three','Four','Five','Six','Seven','Eight'][i];mac[key]=ci(r)
 rows.append(' & '.join([tasks[r.task],labels[r.left]+' $-$ '+labels[r.right],'Mean last 10' if r.metric=='last10_occupancy' else 'All last 10','\\'+key+'{}'])+r' \\')
(P/'tables/table_window_intervals.tex').write_text(r'''\begin{table}[htbp]\centering\small
\caption{Descriptive sustained-window contrasts (percentage points, paired 95\% intervals). The frozen case-bootstrap function uses 5,000 replicates, seed 20261011, and the same index vectors for every definition.}
\label{tab:window-intervals}\begin{tabular}{lllr}\toprule
Task & Contrast & Metric & Difference [95\% CI] \\\midrule
'''+ '\n'.join(rows)+r'\bottomrule\end{tabular}\end{table}'+'\n')
for _,r in pd.read_csv(W/'G_CUBE_PAIRED_INTERVALS.csv').iterrows():mac['APLeWMCube'+{'any':'Any','final':'Final','change':'Change'}[r.metric]+'CI']=ci(r)
# Fixed configuration reversal values, generated from the corrected contrast file.
co=pd.read_csv(A/'CONTRASTS.csv')
for definition,suffix in [('any','Any'),('final','Final')]:
 r=co[(co.contrast=='LeWM_h3 - M03_h1')&(co.definition==definition)].iloc[0];mac['RfourReacherThreeAP'+suffix]=ci(r)
# G inventory counts are computed from precisely the displayed rows.
p=P/'tables/table_protocol_literature.tex';s=p.read_text();data=[x.split(' & ') for x in s.splitlines() if ' & ' in x and not x.startswith('Source')];count=len(data);allfour=sum(x[1]=='4' for x in data);assert(count,allfour)==(12,8)
mac['PublicSourceCount']=str(count);mac['FourTaskSourceCount']=str(allfour)
s=s.replace('10 P/C/T; 30 rel.','30 P; 10 C/T/R (App. D; App. B states 30 without qualification); 30 all (rel. config)')
s=s.replace('Seeds are split by category when identifiable.','Seeds are split by category when identifiable. P/C/T/R denote PushT/Cube/TwoRoom/Reacher; rel. means released. The 12 displayed sources are the complete selected table; eight explicitly cover all four benchmark tasks. DeepJEPA\'s five entries include Cube variants and omit TwoRoom.')
p.write_text(s)
(W/'TABLE2_COUNT.json').write_text(json.dumps({'sources':count,'all_four_tasks':allfour,'rows':[{'source':x[0],'tasks':x[1]} for x in data],'excluded_deepjepa_from_allfour':'cube;cube_double;cube_triple;pusht;reacher; no TwoRoom'},indent=2)+'\n')
p=P/'tables/table_method_mapping_revision.tex';s=p.read_text().replace('Direct long action-prefix interface; five-step executed prefix','Direct 25-raw-step action prefix (5 blocks $\\times$ 5); all 25 executed').replace('Re-decision on the released Fast-LeWM schedule','Re-decision every 25 raw steps (native horizon/receding horizon 1 long block)').replace('Released Fast-LeWM CEM settings','300 candidates, 30 elites, 30 iterations; one 25-action prefix').replace('Native planner settings mapped to the common study interface.','Native planner settings mapped to the common study interface. Fast-LeWM values come from released \\texttt{config/eval/solver/cem.yaml}, task evaluation YAMLs and \\texttt{eval.py}; the adapter packs five five-action blocks into its native long-prefix interface.');p.write_text(s)
p=P/'tables/table_adwm_stream_revision.tex';s=p.read_text();
for i,n in enumerate(['R3\\_ORIGINAL','R4\\_ALT\\_CEM\\_1','R4\\_ALT\\_CEM\\_2'],1):s=s.replace(n,'planning stream '+str(i))
s=s.replace('Checkpoint &','Public checkpoint ID &').replace('AD-WM checkpoint and planner-stream results','AD-WM public checkpoint IDs (3072, 4096, 6144) and planner-stream results');p.write_text(s)
p=P/'tables/table_predictions_revision.tex';p.write_text(p.read_text().replace('independent subcondition','separately judged subcondition'))
p=P/'tables/table_ap_lewm_intervals.tex';p.write_text(p.read_text().replace('intervals for the other tasks retain their original paired analyses.','Cube uses the same seed-20261011 indices as the prediction table; PushT and TwoRoom retain the original seed-20261012 paired analyses.'))
# B fault-only table: invalid and corrected grouped columns, no behavioral inference from invalid data.
old=pd.read_csv(A/'ABSOLUTE_RATES_OLD.csv');new=pd.read_csv(A/'ABSOLUTE_RATES.csv');rows=[]
for model in labels:
 vals=[]
 for frame in [old,new]:
  for d in ['any','block','final']:vals.append(fmt(frame[(frame.model==model)&(frame.iterations==30)&(frame.definition==d)].iloc[0].rate_pct))
 rows.append(' & '.join([labels[model]]+vals)+r' \\')
(P/'tables/table_reacher_termination_correction.tex').write_text(r'''\begin{table}[t]\centering\small
\caption{Fault attribution only: invalid continuation implementation versus corrected continuous rollouts (percent). The change combines removal of the unintended reset with an explicit END convention for block and final labels; it is not evidence about which controller leaves the target. The released first-arrival evaluation is unaffected.}
\label{tab:reacher-correction}\begin{tabular}{lrrrrrr}\toprule
 & \multicolumn{3}{c}{\shortstack{Invalid continuation implementation\\(fault attribution only)}} & \multicolumn{3}{c}{Corrected continuation} \\
Configuration & Any & Block & Final & Any & Block & Final \\\midrule
'''+ '\n'.join(rows)+r'\bottomrule\end{tabular}\end{table}'+'\n')
# H merge duplicate factor rows after verifying numeric identity, preserving source table.
p=P/'tables/table_factor_effects.tex';s=p.read_text();s='\n'.join(x for x in s.splitlines() if not x.startswith('CEM elite standard-deviation correction &'));s=s.replace('Library version (old $\\rightarrow$ PyPI 0.0.6)','Library / CEM elite std. correction').replace('The old-library and elite-standard-deviation rows are numerically identical because the released version difference is this correction;','The library-version and CEM elite-standard-deviation factors are numerically identical and appear once as a combined row;');p.write_text(s+'\n')
# C coverage and replay scope.
c=json.loads((W/'C1_FULL_AUDIT.json').read_text());d=json.loads((W/'D_FIRST25_SUMMARY.json').read_text());mac.update(RfourFormalCount=str(c['records']),RfourMicroCount=f"{c['microsteps']:,}",RfourPrefixCount=f"{c['actions_before_first_success']:,}",RfourPrefixHitCount=f"{c['actions_through_first_success']:,}",RfourDMismatch=str(d['first25_action_mismatch_pairs']),RfourDPairs=str(d['pairs']))
(P/'tables/table_formal_coverage.tex').write_text(r'''\begin{table}[htbp]\centering\small
\caption{Coverage of final-code TECH replay and the full saved-formal-log audit. Every row uses three planning streams. TECH uses four case identities per row; formal uses 100. No new physical rollout was run for this audit.}
\label{tab:formal-coverage}\begin{tabular}{llrr}\toprule
Method/checkpoint & History; CEM iterations & TECH replay & Formal log audit \\\midrule
LeWM & 1; 30 & 12 & 300 \\
LeWM & 3; 30 & 12 & 300 \\
Fast-LeWM & 1; 30 & 12 & 300 \\
AP & 1; 30 & 12 & 300 \\
AD-WM 3072 & 1; 30 & 12 & 300 \\
AD-WM 4096 & 1; 30 & 12 & 300 \\
AD-WM 6144 & 1; 30 & 12 & 300 \\
LeWM & 1; 10 & 12 & 300 \\
LeWM & 3; 10 & 12 & 300 \\\midrule
Total & & 108 & \RfourFormalCount{} \\\bottomrule\end{tabular}\end{table}
''')
# Add revoked authorization and exclusion timestamps from actual records, before final gates.
p=P/'tables/table_reacher_correction_timeline.tex';s=p.read_text();extra=[]
for label,name,key in [('Earlier launch (later revoked)','FORMAL_LAUNCH_RECEIPT_REVOKED_PREMATURE.json','created_utc'),('Revocation; 33 records excluded','PREMATURE_FORMAL_EXCLUSION.json','utc')]:
 x=R/name;j=json.loads(x.read_text());t=datetime.datetime.fromisoformat(j[key]);extra.append(label+r' & \shortstack[l]{'+t.strftime('%Y-%m-%d')+r'\\'+t.strftime('%H:%M:%S.%f')+r'} & \texttt{'+hashlib.sha256(x.read_bytes()).hexdigest()[:12]+r'} \\')
s=s.replace('Final numerical gates &','\n'.join(extra)+'\nFinal numerical gates &');p.write_text(s)
# H unified compute table (no rent or lifecycle rows).
e=json.loads((W.parent/'execution_report_final_v2/COMPLETION_REPORT_STATUS_DRAFT.json').read_text());mac['RfourCorrectionGPU']=f"{e['valid_formal_gpu_hours_verified_stages']:.3f}"
(P/'tables/table_compute_combined.tex').write_text(r'''\begin{table}[htbp]\centering\small
\caption{Compute and reproducibility accounting. The correction is additional to the earlier allocation. GPU hours sum condition-process time; no model training was performed.}
\label{tab:compute}\begin{tabular}{p{0.31\linewidth}p{0.59\linewidth}}\toprule
Item & Recorded value \\\midrule
Earlier formal evaluation & 66.86 GPU h \\
Original held-out evaluation & 8.36 GPU h \\
Earlier TECH/cache/reset work & 2.31 GPU h (included in the 77.53 GPU h earlier total) \\
Corrected Reacher formal evaluation & \RfourCorrectionGPU{} GPU h \\
Original held-out and corrected-run hardware & Both 4 $\times$ RTX 4090; NVIDIA driver 595.84; CUDA 12.8 \\
Experiment software & Python 3.12.3; stable-worldmodel commit \texttt{63988116}; full environment freeze in materials \\
Case bootstrap & 5,000 replicates; frozen statistics function \\
This revision & CPU analysis of saved logs only; no new model or environment execution \\\bottomrule\end{tabular}\end{table}
''')
# The exact platform entry already exists in refs.bib but was uncited. Preserve all entries and activate its citation in main.tex.
assert '2605.21800' in (P/'refs.bib').read_text()
(W/'R4_NEW_MACROS.json').write_text(json.dumps(mac,ensure_ascii=False,indent=2)+'\n')
print('Generated revision tables, count',count,allfour)
