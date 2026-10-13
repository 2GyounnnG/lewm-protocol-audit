#!/usr/bin/env python3
"""CPU-only supplementary metrics for JAIR revision 3.
Reads the derived stepwise table (the sealed D1 result remains read-only) and
writes a small appendix table plus an audit manifest.
"""
from pathlib import Path
import csv,json,hashlib
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'a1_results'/'A1_TRAJECTORY_SUMMARY.csv'
OUT=ROOT/'tables'/'table_terminal_window.tex'
AUD=ROOT/'a3_results'/'REV3_SUPPLEMENT_AUDIT.json'
rows=list(csv.DictReader(SRC.open(encoding='utf-8-sig')))
for r in rows:
    for k in [f'step_{i}' for i in range(1,51)]: r[k]=float(r[k])
    r['first_hit_step']=float(r['first_hit_step']) if r['first_hit_step'] else None
    r['post_hit_leave_rate']=float(r['post_hit_leave_rate']) if r['post_hit_leave_rate'] else 0.0
# paper labels
models={'LeWM_h1':'LeWM one-frame','LeWM_h3':'LeWM three-frame','M01_h1':'Fast-LeWM','M03_h1':'Anchored Planning','M07_h1':'AD-WM'}
tasks=['reacher','pusht','tworoom','cube']
labels={'reacher':'Reacher','pusht':'PushT','tworoom':'TwoRoom','cube':'Cube'}
out=[]
for task in tasks:
  for model,display in models.items():
    z=[r for r in rows if r['task']==task and r['model']==model]
    def tail(k): return sum(all(r[f'step_{i}']>=0.5 for i in range(51-k,51)) for r in z)/len(z)*100
    def occ(k): return sum(r[f'step_{i}'] for r in z for i in range(51-k,51))/(len(z)*k)*100
    # Exit is defined among rows with a first hit and is the complement of occupancy after first hit.
    hit=[r for r in z if r['first_hit_step'] is not None]
    exit_rate=sum(r['post_hit_leave_rate'] for r in hit)/len(hit)*100 if hit else float('nan')
    out.append(dict(task=labels[task],model=display,occ5=occ(5),occ10=occ(10),all5=tail(5),all10=tail(10),exit=exit_rate,n=len(z)))
with OUT.open('w',encoding='utf-8') as f:
 f.write("\\begin{table*}[t]\\centering\\caption{Supplementary terminal-window metrics on the current complete trajectories. Occupancy is the mean success indicator in the final $K$ raw steps; ``all'' is the percentage of case--stream rows successful at every step in that window; exit is the post-first-hit leave rate. Reacher entries will be replaced after the registered termination fix.}\\label{tab:terminal-window}\\scriptsize\\n")
 f.write('\\begin{tabular}{llrrrrr}\\toprule Task & Method & Occupancy $K=5$ & Occupancy $K=10$ & All $K=5$ & All $K=10$ & Exit after hit \\\\midrule\n')
 for i,r in enumerate(out):
   f.write(f"{r['task']} & {r['model']} & {r['occ5']:.1f}\\% & {r['occ10']:.1f}\\% & {r['all5']:.1f}\\% & {r['all10']:.1f}\\% & {r['exit']:.1f}\\% \\\\\n")
   if (i+1)%5==0: f.write('\\addlinespace\n')
 f.write('\\bottomrule\\end{tabular}\\end{table*}\n')
# Convert the literal marker in the first header string to a real newline.
_txt=OUT.read_text(encoding='utf-8').replace('\\n','\n').replace('\\\\midrule','\\midrule')
_txt=_txt.replace('Exit after hit \\midrule','Exit after hit \\\\\\midrule')
OUT.write_text(_txt,encoding='utf-8')
sha=hashlib.sha256(SRC.read_bytes()).hexdigest()
AUD.write_text(json.dumps({'source':str(SRC),'source_sha256':sha,'rows':out,'definition':{'occupancy':'mean success indicator in final K raw steps','all':'all K raw steps successful','exit':'complement of post-hit occupancy among rows with a first hit'},'reacher_status':'provisional until registered termination correction'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('wrote',OUT,AUD)
