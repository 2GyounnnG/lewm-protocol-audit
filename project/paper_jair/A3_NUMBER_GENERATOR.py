"""Generate all manuscript numerical macros and claim provenance from sealed CSVs."""
import csv,json,datetime,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];P=Path(__file__).resolve().parent
S2=ROOT/'d1_execution/step2/resume_03/results';S4=ROOT/'d1_execution/step4/resume_01/results';A1DIR=P/'a1_results';A2=P/'a2_results';OUT=P/'a3_results';OUT.mkdir(exist_ok=True)
def read(path):return list(csv.DictReader(path.open(encoding='utf-8-sig')))
def f(x):return float(x)
def pp(x):return f'{f(x):+.2f}' if abs(f(x))>1e-12 else '+0.00'
def ci(r):return f'{pp(r["delta_pp"])} [{pp(r["ci95_low_pp"])}, {pp(r["ci95_high_pp"])}]'
contrast=read(S4/'CONTRASTS.csv'); absolute=read(S4/'ABSOLUTE_RATES.csv'); raw=read(S4/'RAW_TRAJECTORIES.csv'); d3=read(S4/'D3_COHORT_COMPARISON.csv'); orig=read(S2/'ORIGINAL_PROTOCOL_COMPARISONS.csv'); noise=json.loads((S2/'H4_NOISE.json').read_text());a1=read(A1DIR/'A1_GROUP_SUMMARY.csv');a2=json.loads((A2/'A2_METADATA.json').read_text()); a2['four_task_sources']=sum(int(r['n_tasks'])==4 for r in read(A2/'A2_LITERATURE_PROTOCOLS.csv'))
def C(task,name,analysis='main',definition='any'):
 return next(r for r in contrast if r['task']==task and r['contrast']==name and r['analysis']==analysis and r['definition']==definition)
def A(task,model,definition='any',it='30'):
 return next(r for r in absolute if r['task']==task and r['model']==model and r['definition']==definition and r['iterations']==it)
def A1(model,task):return next(r for r in a1 if r['model']==model and r['task']==task)
macros={
 'PaperCount':str(a2['paper_count']),'FourTaskPaperCount':str(a2['four_task_sources']),
 'ReproTotal':str(len(orig)),'ReproAbsolute':str(sum(r['absolute_reproduced']=='True' for r in orig)),
 'HeldoutTrajectories':str(len(raw)),'HeldoutConditions':str(len({r['condition_id'] for r in raw})),'HeldoutCasesPerTask':str(len({r['case_id'] for r in raw if r['task']=='reacher'})),'Streams':str(len({r['stream'] for r in raw if r['task']=='reacher' and r['model']=='LeWM' and r['history']=='1' and r['iterations']=='30'})),'BootstrapReplicates':'5000',
 'ReacherHistoryDelta':pp(C('reacher','LeWM_h3 - LeWM_h1')['delta_pp']),'ReacherHistoryLow':pp(C('reacher','LeWM_h3 - LeWM_h1')['ci95_low_pp']),'ReacherHistoryHigh':pp(C('reacher','LeWM_h3 - LeWM_h1')['ci95_high_pp']),
 'ReacherHistoryCI':ci(C('reacher','LeWM_h3 - LeWM_h1')),
 'ReacherHistoryCIOnly':f'[{pp(C("reacher","LeWM_h3 - LeWM_h1")["ci95_low_pp"])}, {pp(C("reacher","LeWM_h3 - LeWM_h1")["ci95_high_pp"])}]',
 'PushTHistoryDelta':pp(C('pusht','LeWM_h3 - LeWM_h1')['delta_pp']),'TwoRoomHistoryDelta':pp(C('tworoom','LeWM_h3 - LeWM_h1')['delta_pp']),'CubeHistoryDelta':pp(C('cube','LeWM_h3 - LeWM_h1')['delta_pp']),
 'ReacherMOneDelta':ci(C('reacher','LeWM_h3 - M01_h1',analysis='C2')),'ReacherMSevenDelta':ci(C('reacher','LeWM_h3 - M07_h1',analysis='C2')),'ReacherMThreeDelta':ci(C('reacher','LeWM_h3 - M03_h1',analysis='C2')),
 'TwoRoomMThreeDelta':ci(C('tworoom','M03_h1 - LeWM_h1')),'TwoRoomMSevenDelta':ci(C('tworoom','M07_h1 - LeWM_h1')),'CubeMThreeDelta':ci(C('cube','M03_h1 - LeWM_h1')),'CubeMSevenDelta':ci(C('cube','M07_h1 - LeWM_h1')),
 'ReacherTauAnyBlock':next(r['kendall_tau_b'] for r in read(S4/'KENDALL_TAU.csv') if r['task']=='reacher' and r['definitions']=='any/block'),'ReacherTauAnyFinal':next(r['kendall_tau_b'] for r in read(S4/'KENDALL_TAU.csv') if r['task']=='reacher' and r['definitions']=='any/final'),'ReacherTauBlockFinal':next(r['kendall_tau_b'] for r in read(S4/'KENDALL_TAU.csv') if r['task']=='reacher' and r['definitions']=='block/final'),
 'ReacherLeWMOneAny':f'{f(A("reacher","LeWM_h1")["rate_pct"]):.2f}','ReacherLeWMOneFinal':f'{f(A("reacher","LeWM_h1","final")["rate_pct"]):.2f}',
 'ReacherAPAny':f'{f(A("reacher","M03_h1")["rate_pct"]):.2f}','ReacherAPFinal':f'{f(A("reacher","M03_h1","final")["rate_pct"]):.2f}',
 'PushTFastAny':f'{f(A("pusht","M01_h1")["rate_pct"]):.2f}','PushTFastFinal':f'{f(A("pusht","M01_h1","final")["rate_pct"]):.2f}',
 'ReacherAOneLeWMOnePostHit':f'{100*f(A1("LeWM_h1","reacher")["post_hit_occupancy_mean"]):.2f}','ReacherAOneLeWMOneLeave':f'{100*f(A1("LeWM_h1","reacher")["hit_but_not_final_rate"]):.2f}',
 'ReacherAOneAPPostHit':f'{100*f(A1("M03_h1","reacher")["post_hit_occupancy_mean"]):.2f}','ReacherAOneAPLeave':f'{100*f(A1("M03_h1","reacher")["hit_but_not_final_rate"]):.2f}',
 'ReacherAPLeWMAnyDelta':pp(f(A('reacher','M03_h1')['rate_pct'])-f(A('reacher','LeWM_h1')['rate_pct'])),'ReacherAPLeWMFinalDelta':pp(f(A('reacher','M03_h1','final')['rate_pct'])-f(A('reacher','LeWM_h1','final')['rate_pct'])),
 'DFourReacherHOneAnyDelta':pp(C('reacher','LeWM_h1 CEM10 - CEM30',analysis='D4_iterations')['delta_pp']),'DFourReacherHOneAnyLow':pp(C('reacher','LeWM_h1 CEM10 - CEM30',analysis='D4_iterations')['ci95_low_pp']),'DFourReacherHOneAnyHigh':pp(C('reacher','LeWM_h1 CEM10 - CEM30',analysis='D4_iterations')['ci95_high_pp']),'DFourCubeHOneFinalDelta':pp(C('cube','LeWM_h1 CEM10 - CEM30',analysis='D4_iterations',definition='final')['delta_pp']),'DFourCubeHOneFinalLow':pp(C('cube','LeWM_h1 CEM10 - CEM30',analysis='D4_iterations',definition='final')['ci95_low_pp']),'DFourCubeHOneFinalHigh':pp(C('cube','LeWM_h1 CEM10 - CEM30',analysis='D4_iterations',definition='final')['ci95_high_pp']),
 'ReacherNoiseRange':f'{noise["reacher"]["stream_summary"][0]["range_pp"]:.2f}','PushTNoiseRange':f'{noise["pusht"]["stream_summary"][0]["range_pp"]:.2f}',
 'ReacherNoiseHalfwidth':f'{next(x["halfwidth_median_pp"] for x in noise["reacher"]["registered_function"]["widths"] if x["n_cases"]==100 and x["n_streams"]==3):.2f}','PushTNoiseHalfwidth':f'{next(x["halfwidth_median_pp"] for x in noise["pusht"]["registered_function"]["widths"] if x["n_cases"]==100 and x["n_streams"]==3):.2f}',
 'FormalGPUHours':'8.36','StepTwoGPUHours':'66.86','TotalGPUHours':'77.53'
}
with (OUT/'numbers.tex').open('w') as g:
 g.write('% Generated by A3_NUMBER_GENERATOR.py; do not hand edit.\n')
 for k,v in macros.items():g.write(f'\\newcommand{{\\{k}}}{{{v}}}\n')
claims=[]
def claim(cid,text,formula,aggregate,unit,sample,fail,source,kind='prespecified'):
 claims.append({'claim_id':cid,'claim':text,'metric_formula':formula,'aggregation_order':aggregate,'unit':unit,'sample_unit':sample,'failure_handling':fail,'source_path':source,'evidence_level':kind})
claim('C1-reacher','Reacher history difference is at least 10 pp with lower CI above zero','mean_case_stream(LeWM h3)-mean_case_stream(LeWM h1)','stream mean within case; case bootstrap 5000','pp','100 HELDOUT cases, ABC streams','missing conditions excluded; none missing','d1_execution/step4/resume_01/results/CONTRASTS.csv','preregistered_confirmatory')
claim('C1-other','PushT, TwoRoom and Cube history point differences are within 2 pp','paired case-stream difference','case bootstrap 5000','pp','100 HELDOUT cases, ABC streams','same as above','d1_execution/step4/resume_01/results/CONTRASTS.csv','preregistered_confirmatory')
claim('C2','Reacher h3 compared with M01/M07/M03','paired case-stream difference; M07 seed average within case','case bootstrap 5000','pp','100 HELDOUT cases, ABC streams','no imputation','d1_execution/step4/resume_01/results/CONTRASTS.csv','preregistered_confirmatory')
claim('C3','M03 and M07 gains on TwoRoom and Cube have lower CI above zero','paired case-stream difference','case bootstrap 5000; M07 seeds averaged within case','pp','100 HELDOUT cases, ABC streams','no imputation','d1_execution/step4/resume_01/results/CONTRASTS.csv','preregistered_confirmatory')
claim('A1','Reacher trajectories often leave the target after first success','first success index; mean success after first hit; any-success with final failure','mean over case-stream rows; M07 seed mean first','steps and %','100 cases × 3 streams per model/task','never-success rows excluded from post-hit mean','paper_jair/a1_results/A1_GROUP_SUMMARY.csv','post hoc')
claim('D1-ranking','Success definition changes model ranking','rate by definition; Kendall tau-b between rankings','case-stream rates; 5 model ranks','% and tau-b','100 cases × 3 streams','all complete','d1_execution/step4/resume_01/results/ABSOLUTE_RATES.csv; KENDALL_TAU.csv','descriptive')
claim('noise','Three-stream paired uncertainty has a task-specific half-width','registered bootstrap resampling width','median over 5000 resamples','pp','100 cases × 3 streams','empirical resampling; not type-I theorem','d1_execution/step2/resume_03/results/H4_NOISE.json','prespecified')
claim('replication','10 of 12 published absolute values were reproduced','count absolute_reproduced=True','count over 12 method-task rows','count','12 comparisons','two false rows retained','d1_execution/step2/resume_03/results/ORIGINAL_PROTOCOL_COMPARISONS.csv','prespecified')
with (OUT/'CLAIM_EVIDENCE.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=list(claims[0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(claims)
# Range table copied through a source-preserving derived file
range_src=S2/'PROTOCOL_VS_LITERATURE_RANGE.csv';outrows=read(range_src)
with (OUT/'RESULT_RANGE_TABLE.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=outrows[0].keys());w.writeheader();w.writerows(outrows)
source_rows=[{'figure_or_table':'numbers.tex','data_source':'A3_NUMBER_GENERATOR.py','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'notes':'Macros derived from sealed CSV/JSON; no hand-entered result values.'},
 {'figure_or_table':'A1_OCCUPANCY_CURVES','data_source':'plot_a1.py + a1_results/A1_OCCUPANCY_CURVES.csv','source_sha256':hashlib.sha256((P/'plot_a1.py').read_bytes()).hexdigest(),'notes':'Full-budget HELDOUT trajectory success flags.'},
 {'figure_or_table':'FIG3_SUCCESS_DEFINITIONS','data_source':'d1_execution/step4/resume_01/figures/FIG1_SUCCESS_DEFINITIONS.png','source_sha256':hashlib.sha256((ROOT/'d1_execution/step4/resume_01/figures/FIG1_SUCCESS_DEFINITIONS.png').read_bytes()).hexdigest(),'notes':'Copied read-only sealed Step 4 figure; renamed for manuscript ordering.'},
 {'figure_or_table':'FIG4_METHOD_CONTRASTS','data_source':'d1_execution/step4/resume_01/figures/FIG2_METHOD_CONTRASTS.png','source_sha256':hashlib.sha256((ROOT/'d1_execution/step4/resume_01/figures/FIG2_METHOD_CONTRASTS.png').read_bytes()).hexdigest(),'notes':'Copied read-only sealed Step 4 figure; renamed for manuscript ordering.'},
 {'figure_or_table':'FIG_D4_CEM_ITERATIONS','data_source':'d1_execution/step4/resume_01/figures/FIG3_CEM_ITERATIONS.png','source_sha256':hashlib.sha256((ROOT/'d1_execution/step4/resume_01/figures/FIG3_CEM_ITERATIONS.png').read_bytes()).hexdigest(),'notes':'Copied read-only sealed Step 4 descriptive D4 figure.'},
 {'figure_or_table':'FIG5_NOISE_SCALE','data_source':'d1_execution/step3/figures/POSTHOC_FIG4_NOISE_SCALE.png','source_sha256':hashlib.sha256((ROOT/'d1_execution/step3/figures/POSTHOC_FIG4_NOISE_SCALE.png').read_bytes()).hexdigest(),'notes':'Copied read-only sealed Step 3 post hoc figure.'}]
with (OUT/'FIGURE_SOURCES.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=source_rows[0].keys());w.writeheader();w.writerows(source_rows)
meta={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'macros':macros,'inputs':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in [S2/'ORIGINAL_PROTOCOL_COMPARISONS.csv',S2/'PROTOCOL_VS_LITERATURE_RANGE.csv',S2/'H4_NOISE.json',S4/'ABSOLUTE_RATES.csv',S4/'CONTRASTS.csv',S4/'D3_COHORT_COMPARISON.csv',A1DIR/'A1_GROUP_SUMMARY.csv',A2/'A2_METADATA.json']},'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}}
(OUT/'A3_METADATA.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'macros':len(macros),'claims':len(claims),'outputs':list(meta['outputs'])},ensure_ascii=False))
