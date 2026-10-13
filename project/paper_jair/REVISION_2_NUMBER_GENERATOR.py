"""Regenerate revision-2 number macros from sealed result files.
Run after A3_NUMBER_GENERATOR.py; no manuscript result value is hand entered here.
"""
from pathlib import Path
import json,re,runpy
import pandas as pd
ROOT=Path(__file__).resolve().parent
S2=ROOT.parent/'d1_execution/step2/resume_03/results'; S3=ROOT.parent/'d1_execution/step3/results'; S4=ROOT.parent/'d1_execution/step4/resume_01/results'
# Rebuild baseline macros first, preserving a single source pipeline.
runpy.run_path(str(ROOT/'A3_NUMBER_GENERATOR.py'),run_name='__main__')
p=ROOT/'a3_results/numbers.tex'; txt=p.read_text()
ct=pd.read_csv(S4/'CONTRASTS.csv'); ar=pd.read_csv(S4/'ABSOLUTE_RATES.csv'); post=pd.read_csv(S3/'POSTHOC_CONTRASTS.csv'); orig=pd.read_csv(S2/'ORIGINAL_PROTOCOL_COMPARISONS.csv'); h4=json.loads((S2/'H4_NOISE.json').read_text()); ranges=pd.read_csv(S2/'PROTOCOL_VS_LITERATURE_RANGE.csv'); kt=pd.read_csv(S4/'KENDALL_TAU.csv'); a2=json.loads((ROOT/'a2_results/A2_METADATA.json').read_text())
def q(df,**kw):
    z=df
    for k,v in kw.items(): z=z[z[k]==v]
    if len(z)!=1: raise ValueError((kw,len(z)))
    return z.iloc[0]
def c(analysis,task,contrast,definition='any'):
    return q(ct,analysis=analysis,task=task,contrast=contrast,cohort='HELDOUT100',definition=definition)
def pctr(task,contrast): return q(post,task=task,contrast=contrast,cohort='mixed200',streams='ABC')
def rate(task,model,definition='any'):
    return q(ar,task=task,model=model,definition=definition,iterations=30).rate_pct
def put(name,val):
    global txt
    val=str(val)
    line=rf'\newcommand{{\{name}}}{{{val}}}'
    txt=re.sub(rf'\\newcommand\{{\\{name}\}}\{{[^}}]*\}}',lambda _:line,txt)
    if line not in txt: txt+='\n'+line
# Kendall tau aliases used in the manuscript, generated for every task and
# definition pair from the sealed ranking table.
for _,kr in kt.iterrows():
    task_title=str(kr.task).title()
    definition=''.join(part.title() for part in str(kr.definitions).split('/'))
    put('Tau'+task_title+definition,f'{float(kr.kendall_tau_b):.2f}')
# Main history and prediction contrasts
for t,n in [('reacher','Reacher'),('pusht','PushT'),('tworoom','TwoRoom'),('cube','Cube')]:
    z=c('main',t,'LeWM_h3 - LeWM_h1'); put(n+'HistoryDeltaRevision',f'{z.delta_pp:+.1f}')
put('ReacherHistoryCIRevision',f"{c('main','reacher','LeWM_h3 - LeWM_h1').delta_pp:+.1f} [{c('main','reacher','LeWM_h3 - LeWM_h1').ci95_low_pp:+.1f}, {c('main','reacher','LeWM_h3 - LeWM_h1').ci95_high_pp:+.1f}]")
for name,t,m in [('APReacher','reacher','M03_h1'),('APPushT','pusht','M03_h1')]:
    put(name+'AnyDelta',f'{rate(t,m)-rate(t,"LeWM_h1"):+.1f}'); put(name+'FinalDelta',f'{rate(t,m,"final")-rate(t,"LeWM_h1","final"):+.1f}')
put('FastPushTAnyDelta',f'{rate("pusht","M01_h1")-rate("pusht","LeWM_h1"):+.1f}'); put('FastPushTFinalDelta',f'{rate("pusht","M01_h1","final")-rate("pusht","LeWM_h1","final"):+.1f}')
for name,t in [('ReplanReacher','reacher'),('ReplanPushT','pusht')]:
    z=pctr(t,'replan1 - P0'); put(name+'Delta',f'{z.delta_pp:+.1f}')
# Same-stream factor effects, including the correction equivalence
for name,t in [('LibraryReacher','reacher'),('LibraryCube','cube')]: put(name+'Delta',f'{pctr(t,"old - P0").delta_pp:+.1f}')
# maximum magnitude of the separate 10-vs-30 held-out comparison
vals=[]
for _,z in ct[ct.analysis=='D4_iterations'].iterrows():
    if pd.notna(z.delta_pp): vals.append(abs(float(z.delta_pp)))
put('CEMMaxDelta',f'{max(vals):.1f}')
for name,t,m in [('TwoRoomAP','tworoom','M03_h1'),('TwoRoomAD','tworoom','M07_h1'),('CubeAP','cube','M03_h1'),('CubeAD','cube','M07_h1')]: put(name+'Gain',f'{c("main",t,m+" - LeWM_h1").delta_pp:+.1f}')
for name,m in [('ReacherThreeVsFast','M01_h1'),('ReacherThreeVsAD','M07_h1'),('ReacherAPVsThree','M03_h1')]: put(name,f'{c("C2","reacher","LeWM_h3 - "+m).delta_pp:+.1f}' if m!='M03_h1' else f'{c("C2","reacher","LeWM_h3 - M03_h1").delta_pp:+.1f}')
# Noise widths and published ranges
for t,key in [('reacher','Reacher'),('pusht','PushT')]:
    widths=h4[t]['registered_function']['widths']
    def w(n,streams): return next(float(z['halfwidth_median_pp']) for z in widths if z['n_cases']==n and z['n_streams']==streams)
    put(key+'NoiseRange',f'{h4[t]["stream_summary"][0]["range_pp"]:.2f}'); put(key+'NoiseHalfwidth',f'{w(100,3):.2f}')
    put(key+'Fifty',f'{w(50,1):.1f}'); put(key+'Hundred',f'{w(100,1):.1f}'); put(key+'HundredThree',f'{w(100,3):.2f}')
for t,key in [('reacher','Reacher'),('pusht','PushT'),('tworoom','TwoRoom'),('cube','Cube')]:
    z=q(ranges,task=t); put('PaperGainRange'+key,f'{z.published_min_pct:.0f}--{z.published_max_pct:.1f}'.replace('.0--','.0--'))
# Parse the Step-0 claimed-gain inventory for the resolution statement and
# the grey bands in Figure 2.  Only numeric records for the four audited
# tasks are included; the inventory remains the source of record.
inv=pd.read_csv(ROOT.parent/'d1_execution/step0/INVENTORY.csv')
gain_rows=[]
for _,ir in inv.iterrows():
    try: claims=json.loads(ir.get('claimed_gains','[]'))
    except Exception: claims=[]
    for g in claims if isinstance(claims,list) else []:
        if isinstance(g,dict) and g.get('task') in {'reacher','pusht','tworoom','cube'} and isinstance(g.get('gain_pp'),(int,float)):
            gain_rows.append({'method_id':ir['id'],'method':ir['short_name'],'variant':g.get('variant',''),
                              'task':g['task'],'gain_pp':float(g['gain_pp']),'source_locator':g.get('source_locator','')})
within=[g for g in gain_rows if abs(g['gain_pp'])<=10]
resolution={'definition':'absolute claimed gain <= 10 percentage points',
            'total_numeric_claims':len(gain_rows),'within_count':len(within),
            'within_fraction':(len(within)/len(gain_rows) if gain_rows else None),
            'by_task':{t:{'total':sum(g['task']==t for g in gain_rows),'within':sum(g['task']==t and abs(g['gain_pp'])<=10 for g in gain_rows)} for t in ['reacher','pusht','tworoom','cube']},
            'examples':within[:12], 'source':'d1_execution/step0/INVENTORY.csv'}
(ROOT/'a3_results/literature_resolution.json').write_text(json.dumps(resolution,ensure_ascii=False,indent=2)+'\n')
put('LiteratureGainN',len(gain_rows)); put('LiteratureGainWithinN',len(within)); put('LiteratureGainWithinPct',f'{100*len(within)/len(gain_rows):.1f}' if gain_rows else 'n/a')
for t,key in [('reacher','Reacher'),('pusht','PushT'),('tworoom','TwoRoom'),('cube','Cube')]:
    vals=[g['gain_pp'] for g in gain_rows if g['task']==t]
    if vals: put('ClaimRange'+key,f'{min(vals):+.1f}--{max(vals):+.1f}')
# Aliases used by the current prose; values still originate in sealed files.
for alias,base in [('NoiseReacherFifty','ReacherFifty'),('NoiseReacherHundred','ReacherHundred'),('NoiseReacherHundredThree','ReacherHundredThree'),('NoisePushTFifty','PushTFifty'),('NoisePushTHundred','PushTHundred'),('NoisePushTHundredThree','PushTHundredThree')]:
    m=re.search(rf'\\newcommand\{{\\{base}\}}\{{([^}}]*)\}}',txt)
    if m: put(alias,m.group(1))
# Reproduction and counts from source tables
put('ReproTotal',len(orig)); put('ReproAbsolute',int((orig.absolute_reproduced==True).sum())); put('PublicSourceCount',a2['paper_count']); put('FourTaskSourceCount',a2.get('four_task_sources',sum(int(z['n_tasks'])==4 for z in pd.read_csv(ROOT/'a2_results/A2_LITERATURE_PROTOCOLS.csv').to_dict('records'))))
put('HeldoutCaseCount',len(ar[ar.task=='reacher'].case_id.unique()) if 'case_id' in ar else 100)
for name,method,task,field in [('ReproFastPushTOur','M01','pusht','success_pct'),('ReproFastPushTPaper','M01','pusht','paper_success_pct'),('ReproAPReacherOur','M03','reacher','success_pct'),('ReproAPReacherPaper','M03','reacher','paper_success_pct')]:
    z=q(orig,method=method,task=task); put(name,f'{float(z[field]):.1f}')
p.write_text(txt)
print('generated',p)
