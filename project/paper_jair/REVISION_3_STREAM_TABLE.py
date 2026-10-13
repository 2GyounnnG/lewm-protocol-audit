#!/usr/bin/env python3
from pathlib import Path
import pandas as pd, json, hashlib
ROOT=Path(__file__).resolve().parent
SRC=Path(__file__).resolve().parents[1]/'d1_execution/step4/resume_01/evidence/stage2_statistics/RAW_TRAJECTORIES.csv'
OUT=ROOT/'tables/table_adwm_stream_revision.tex'; AUD=ROOT/'a3_results/REV3_ADWM_STREAM_AUDIT.json'
d=pd.read_csv(SRC,low_memory=False)
d=d[(d.model=='M07') & (d.history==1)]
tasks=['reacher','pusht','tworoom','cube']; streams=['R3_ORIGINAL','R4_ALT_CEM_1','R4_ALT_CEM_2']; seeds=['3072','4096','6144']
labels={'reacher':'Reacher','pusht':'PushT','tworoom':'TwoRoom','cube':'Cube'}
out=[]
for task in tasks:
 for seed in seeds:
  for stream in streams:
   z=d[(d.task==task)&(d.train_seed==seed)&(d.stream==stream)]
   row={'task':labels[task],'seed':seed,'stream':stream,'n':len(z),'any':100*z.success_any.mean(),'block':100*z.success_block.mean(),'final':100*z.success_final.mean()}
   out.append(row)
with OUT.open('w',encoding='utf-8') as f:
 f.write('\\begin{table*}[t]\\centering\\caption{AD-WM checkpoint and planner-stream results on the current held-out set. Each row is one checkpoint--stream combination over 100 cases; Reacher rows are provisional until the termination correction.}\\label{tab:adwm-stream}\\scriptsize\n')
 header_break='\\\\\\midrule\n'
 f.write('\\begin{tabular}{llrrrrr}\\toprule Task & Checkpoint & Planner stream & Cases & Any-step (\\%) & Block (\\%) & Final (\\%) ' + header_break)
 for r in out:
  f.write(f"{r['task']} & {r['seed']} & {r['stream'].replace('_','\\_')} & {r['n']} & {r['any']:.1f} & {r['block']:.1f} & {r['final']:.1f} \\\\\n")
 f.write('\\bottomrule\\end{tabular}\\end{table*}\n')
AUD.write_text(json.dumps({'source':str(SRC),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'rows':out,'note':'Reacher rows provisional until registered termination correction'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('wrote',OUT)
