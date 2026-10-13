from pathlib import Path
import csv,shutil,hashlib,json
W=Path(__file__).resolve().parent; P=W.parents[1]/'revision3_part2'
src=P/'main.tex'; backup=W/'main_before_revision7.tex'
if not backup.exists():shutil.copy2(src,backup)
s=backup.read_text()
rows=list(csv.DictReader(open(W/'A/SENSITIVITY_CONTRASTS.csv')))
lines=[r'\begin{table}[p]\centering\scriptsize',r'\caption{Threshold and window sensitivity. Paired differences in percentage points with case-bootstrap 95\% intervals (5,000 draws, common indices). Reacher uses recomputed END predicates; PushT retains its saved predicate because physical states were not saved. F denotes final-step success; columns 5--20 give all-$K$ or mean-$K$ occupancy.}\label{tab:sensitivity-r7}',r'\setlength{\tabcolsep}{3pt}',r'\begin{tabular}{llrrrr}\toprule',r'Comparison / threshold & Metric & $K=5$ & $K=10$ & $K=15$ & $K=20$\\\midrule']
for comp,threshold,title in [('LeWM_h3_minus_AP','0.03','Reacher h3--AP / .03'),('LeWM_h3_minus_AP','0.05','Reacher h3--AP / .05'),('LeWM_h3_minus_AP','0.08','Reacher h3--AP / .08'),('AP_minus_LeWM_h1','20','PushT AP--h1 / 20'),('Fast_LeWM_minus_LeWM_h1','20','PushT Fast--h1 / 20')]:
 rr=[r for r in rows if r['comparison']==comp and float(r['threshold'])==float(threshold) and r['status']=='COMPUTED']
 if not rr: print('MISSING',comp,threshold);continue
 def fmt(r):return f"{float(r['delta_pp']):+.2f} [{float(r['ci95_low_pp']):.2f}, {float(r['ci95_high_pp']):.2f}]"
 print(comp,sorted(set(r['metric'] for r in rr)))
 final=next(r for r in rr if r['metric']=='final_END')
 lines.append(title+r' & F & \multicolumn{4}{c}{'+fmt(final)+r'}\\')
 for metric,lab in [('all_window_END','All'),('mean_window_END','Mean')]:
  found=[r for r in rr if r['metric']==metric]
  if not found:continue
  lines.append(' & '+lab+' & '+' & '.join(fmt(next(r for r in found if int(r['window'])==k)) for k in [5,10,15,20])+r'\\')
 lines.append(r'\addlinespace')
lines +=[r'\bottomrule\end{tabular}\end{table}']
(P/'tables/table_sensitivity_revision7.tex').write_text('\n'.join(lines)+'\n')
s=s.replace(r'\input{tables/table_window_intervals.tex}',r'\input{tables/table_window_intervals.tex}'+'\n'+r'\input{tables/table_sensitivity_revision7.tex}')
s=s.replace(r'\subsection{Occupancy over time}',r'Table~\ref{tab:sensitivity-r7} checks threshold and window sensitivity: the Reacher final-versus-all-window reversal retains nonzero intervals at 0.05 and 0.08 rad for $K=5,10,15,20$; at 0.03 rad the all-window interval first touches zero at $K=10$, with zero contrasts at $K=15,20$. PushT AP retains the reversal for all four windows at the recorded threshold, whereas Fast-LeWM leads under both labels; the AP mean-occupancy interval includes zero at $K=5$.'+'\n\n'+r'\subsection{Occupancy over time}')
s=s.replace('The audit covers one world-model family, four simulated tasks, three public method families, and a finite set of planning streams.','The empirical comparisons cover one world-model family, four simulated tasks, three public method families, and a finite set of planning streams. The static continuation audit additionally traces the public code paths in Table~\\ref{tab:code-audit-r7}; that source-code coverage is distinct from empirical validation on those systems.')
s=s.replace('Thresholds are inherited from the released environments.','Main-result thresholds are inherited from the released environments; Appendix~D varies the Reacher threshold, while missing PushT physical states prevent its threshold re-scoring.')
s=s.replace(r'\subsection{Ranking reversals}',r'Table~\ref{tab:code-audit-r7} traces the conditions behind this failure mode in public code. Success termination, an automatic reset, and continued sampling must coincide for post-success observations to cross an episode boundary; clearing an outer vector flag does not clear dm\_control\textquotesingle s internal reset state. Stopping at success or explicitly retaining episode boundaries avoids that interpretation; the table reports static paths, not a re-evaluation of published scores.'+'\n\n'+r'\subsection{Ranking reversals}')
s=s.replace(r'\section{Reacher runtime verification}\label{app:reacher-verification}',r'\section{Reacher runtime verification and continuation code audit}\label{app:reacher-verification}'+'\n'+r'\input{tables/table_code_audit_revision7.tex}')
(P/'main_revision7_ab.tex').write_text(s)
print('Wrote separate revision7 source; active main preserved')
