from pathlib import Path
import csv,json,hashlib,datetime
W=Path(__file__).resolve().parent
P=W.parent/'revision3_part2'
R=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/returns')
p=P/'tables/table_reacher_correction_timeline.tex'
s=p.read_text()
if 'All corrected formal records complete' not in s:
    rows=[]
    for label,path,key in [('All corrected formal records complete',R/'STAGE3_VERIFIED/experiment/FORMAL_STAGE_3_STATUS.json','utc'),('Final return verified',R/'FORMAL_STAGE_3_LOCAL_RETURN.json','utc'),('Stop request accepted',R.parent/'STOP_EVIDENCE/INSTANCE_STOP_RECEIPT_1.json','response_utc')]:
        obj=json.loads(path.read_text()); dt=datetime.datetime.fromisoformat(obj[key]); h=hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(label+r' & \shortstack[l]{'+dt.strftime('%Y-%m-%d')+r'\\'+dt.strftime('%H:%M:%S.%f')+r'} & \texttt{'+h[:12]+r'} \\')
    s=s.replace(r'\bottomrule','\n'.join(rows)+'\n'+r'\bottomrule');p.write_text(s)
def fmt(v):
    x=float(v)
    return '0.0' if abs(x)<0.05 else f'{x:+.1f}'
rows=list(csv.DictReader((W/'paper_assets_final_v2/data/CONTRASTS.csv').open()))
rows=[r for r in rows if r['analysis']=='D4_iterations']
assert len(rows)==24,len(rows)
lines=[r'\begin{table}[htbp]\centering\small',r'\caption{Ten minus thirty CEM iterations, in percentage points with paired 95\% case-bootstrap intervals. All comparisons are descriptive. Reacher uses corrected continuous trajectories.}',r'\label{tab:cem-numeric}',r'\begin{tabular}{llrrr}\toprule',r'Task & History & Any-step & Block-boundary & Final-step \\\midrule']
for task in ['reacher','pusht','tworoom','cube']:
    for h in [1,3]:
        cells=[]
        for d in ['any','block','final']:
            r=next(r for r in rows if r['task']==task and r['definition']==d and f'LeWM_h{h} ' in r['contrast'])
            cells.append(f"{fmt(r['delta_pp'])} [{fmt(r['ci95_low_pp'])}, {fmt(r['ci95_high_pp'])}]")
        lines.append(' & '.join([{'reacher':'Reacher','pusht':'PushT','tworoom':'TwoRoom','cube':'Cube'}[task],str(h)]+cells)+r' \\')
lines += [r'\bottomrule\end{tabular}\end{table}']
(P/'tables/table_cem_numeric.tex').write_text('\n'.join(lines)+'\n')
p=P/'main.tex';s=p.read_text()
anchor=r'\section{Supplementary terminal-window metrics}'
if r'\input{tables/table_cem_numeric.tex}' not in s:s=s.replace(anchor,r'\input{tables/table_cem_numeric.tex}'+'\n'+r'\clearpage'+'\n\n'+anchor)
p.write_text(s)
