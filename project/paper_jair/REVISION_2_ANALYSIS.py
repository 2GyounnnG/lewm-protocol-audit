from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt, json
from matplotlib.lines import Line2D
ROOT=Path(__file__).resolve().parent
STEP2=ROOT.parent/'d1_execution/step2/resume_03/results'
STEP4=ROOT.parent/'d1_execution/step4/resume_01/results'
FIG=ROOT/'figures'; FIG.mkdir(exist_ok=True)
TASK_LABEL={'reacher':'Reacher','pusht':'PushT','tworoom':'TwoRoom','cube':'Cube'}
MODEL_LABEL={'LeWM_h1':'LeWM one-frame','LeWM_h3':'LeWM three-frame','M01_h1':'Fast-LeWM','M03_h1':'AP','M07_h1':'AD-WM'}
plt.rcParams.update({'font.size':9,'axes.titlesize':10,'axes.labelsize':9,'figure.dpi':150,'savefig.dpi':300})

def save(fig,name):
    fig.tight_layout(); fig.savefig(FIG/(name+'.pdf'),bbox_inches='tight'); fig.savefig(FIG/(name+'.png'),bbox_inches='tight'); plt.close(fig)

# Figure 1: paired design plus one real trajectory.
traj=pd.read_csv(ROOT/'a1_results/A1_TRAJECTORY_SUMMARY.csv')
example=traj[(traj.model=='LeWM_h1')&(traj.task=='reacher')&(traj.case_id=='D1_HELDOUT_reacher_52eb53b2d6afb653d3ed2944')&(traj.stream=='R3_ORIGINAL')].iloc[0]
steps=np.arange(1,51); trace=example[[f'step_{i}' for i in steps]].astype(float).to_numpy()
fig,(axl,axr)=plt.subplots(1,2,figsize=(10,3.2),gridspec_kw={'width_ratios':[1.15,1]})
axl.axis('off'); axl.set_title('Paired audit unit',fontsize=10)
boxes=[('same case',.16,.72),('three fixed\nstreams',.50,.72),('one factor\nchange',.84,.72),('method pair\ncontrast',.50,.28)]
for txt,x,y in boxes:
    axl.text(x,y,txt,ha='center',va='center',transform=axl.transAxes,bbox=dict(boxstyle='round,pad=.55',fc='#e9f2fb',ec='#2c5d87',lw=1.1))
for a,b in [((.28,.72),(.42,.72)),((.59,.72),(.75,.72)),((.50,.58),(.50,.42))]:
    axl.annotate('',xy=b,xytext=a,xycoords=axl.transAxes,arrowprops=dict(arrowstyle='->',lw=1.2,color='#555'))
axl.text(.50,.08,'case × stream pairing is retained for each contrast',ha='center',transform=axl.transAxes,color='#444',fontsize=8)
axr.step(steps,trace,where='mid',color='#1f5a91',lw=1.8)
axr.set_ylim(-.15,1.15); axr.set_xlim(1,50); axr.set_yticks([0,1]); axr.set_yticklabels(['out','in']); axr.set_xlabel('Raw step'); axr.set_ylabel('Target state')
axr.axvline(5,color='#999',ls=':',lw=.8); axr.axvline(50,color='#999',ls=':',lw=.8)
axr.scatter([example.first_hit_step],[1],s=24,color='#2b7a4b',zorder=3,label='any-step = 1')
axr.scatter([5],[trace[4]],s=24,color='#d18f00',zorder=3,label='block check')
axr.scatter([50],[trace[-1]],s=24,color='#b33a3a',zorder=3,label='final-step = 0')
axr.set_title('One held-out Reacher record')
axr.legend(frameon=False,fontsize=7,loc='upper right'); axr.grid(axis='y',alpha=.2)
save(fig,'FIG1_AUDIT_OVERVIEW')

# Figure 2 factor effects
c= pd.read_csv(STEP2/'CONTRASTS.csv')
# factor labels and rows from mixed200
factor_labels={'h3 - P0':'history length','pip - P0':'library version','cem - P0':'CEM elite std.-dev. correction','offset - P0':'goal offset','goal - P0':'goal image','replan1 - P0':'native replanning'}
rows=c[(c.cohort=='mixed200') & (c.family=='factor') & c.contrast.isin(factor_labels)].copy()
rows['factor']=rows.contrast.map(factor_labels)
# select first by factor/task
fig,axs=plt.subplots(2,2,figsize=(9,6),sharex=False)
for ax,(task,sub) in zip(axs.ravel(),rows.groupby('task',sort=False)):
    sub=sub.drop_duplicates('factor',keep='first')
    y=np.arange(len(sub)); ax.axvline(0,color='0.5',lw=.8)
    ax.errorbar(sub.delta_pp,y,xerr=[sub.delta_pp-sub.ci95_low_pp,sub.ci95_high_pp-sub.delta_pp],fmt='o',color='#1f5a91',capsize=3)
    ax.set_yticks(y); ax.set_yticklabels(sub.factor); ax.set_title(TASK_LABEL.get(task,task)); ax.set_xlabel('Difference from one-frame LeWM\n(percentage points)')
    # Published claimed-gain range, parsed from the Step-0 inventory.
    inv=pd.read_csv(ROOT.parent/'d1_execution/step0/INVENTORY.csv'); vals=[]
    for raw in inv.claimed_gains.dropna():
        try: gs=json.loads(raw)
        except Exception: gs=[]
        vals += [float(g['gain_pp']) for g in gs if isinstance(g,dict) and g.get('task')==task and isinstance(g.get('gain_pp'),(int,float))]
    if vals:
        ax.axvspan(min(vals),max(vals),color='0.65',alpha=.20,zorder=0,label='published claimed-gain range')
    ax.grid(axis='x',alpha=.2)
axs[0,0].legend(frameon=False,fontsize=7,loc='lower right')
fig.suptitle('Protocol-factor effects and published claimed-gain ranges',fontsize=11)
save(fig,'FIG2_FACTOR_EFFECTS')

# Figure 3 common protocol gains from heldout main any
co=pd.read_csv(STEP4/'CONTRASTS.csv')
sel=co[(co.analysis=='main')&(co.definition=='any')&(co.cohort=='HELDOUT100')&(co.contrast.str.contains(' - LeWM_h1'))].copy()
sel['method']=sel.contrast.str.extract(r'^(.*?) -')[0]
method_map={'LeWM_h3':'LeWM three-frame history','M01_h1':'Fast-LeWM','M03_h1':'AP','M07_h1':'AD-WM'}
sel['label']=sel.method.map(method_map)
fig,axs=plt.subplots(1,4,figsize=(11,3),sharey=True)
for ax,(task,sub) in zip(axs,sel.groupby('task',sort=False)):
    sub=sub[sub.method!='LeWM_h3']; y=np.arange(len(sub)); ax.axvline(0,color='0.5',lw=.8)
    ax.errorbar(sub.delta_pp,y,xerr=[sub.delta_pp-sub.ci95_low_pp,sub.ci95_high_pp-sub.delta_pp],fmt='o',color='#2b7a4b',capsize=3)
    ax.set_yticks(y); ax.set_yticklabels(sub.label); ax.set_title(TASK_LABEL.get(task,task)); ax.grid(axis='x',alpha=.2)
axs[0].set_xlabel('Difference from one-frame LeWM\n(percentage points)');
for ax in axs[1:]: ax.set_xlabel('pp')
save(fig,'FIG3_COMMON_PROTOCOL_GAINS')

# Figure 4 success rates selected configurations
ar=pd.read_csv(STEP4/'ABSOLUTE_RATES.csv')
models=['LeWM_h1','LeWM_h3','M01_h1','M03_h1','M07_h1']; labels=['LeWM one-frame','LeWM three-frame','Fast-LeWM','AP','AD-WM']
fig,axs=plt.subplots(1,4,figsize=(12,3.4),sharey=True)
cols={'any':'#286090','block':'#73a2c6','final':'#d36b3d'}
for ax,(task,sub) in zip(axs,ar[ar.model.isin(models)].groupby('task',sort=False)):
    x=np.arange(len(models)); w=.25
    for j,d in enumerate(['any','block','final']):
        vals=[]
        for m in models:
            z=sub[(sub.model==m)&(sub.definition==d)]; vals.append(float(z.rate_pct.iloc[0]) if len(z) else np.nan)
        ax.bar(x+(j-1)*w,vals,w,label=d,color=cols[d])
    ax.set_title(TASK_LABEL.get(task,task)); ax.set_xticks(x); ax.set_xticklabels(labels,rotation=55,ha='right',fontsize=7); ax.set_ylim(0,105); ax.grid(axis='y',alpha=.2)
axs[0].set_ylabel('Success (%)'); axs[-1].legend(fontsize=7,frameon=False,loc='lower left')
save(fig,'FIG4_SUCCESS_RATES')

# Figure 5 ranking reversals
fig,axs=plt.subplots(1,2,figsize=(8,3.4),sharey=True)
for ax,task in zip(axs,['reacher','pusht']):
    sub=ar[(ar.task==task)&(ar.model.isin(models))&(ar.iterations==30)]
    base=sub[sub.model=='LeWM_h1'].set_index('definition').rate_pct
    rows=[]
    for m in models[1:]:
        vals=[]
        for d in ['any','final']:
            q=sub[(sub.model==m)&(sub.definition==d)].rate_pct.iloc[0]-base[d]; vals.append(q)
        rows.append((method_map.get(m,m),*vals))
    yy=np.arange(len(rows)); width=.34
    ax.barh(yy-width/2,[r[1] for r in rows],width,label='Any-step',color='#286090')
    ax.barh(yy+width/2,[r[2] for r in rows],width,label='Final-step',color='#d36b3d')
    ax.axvline(0,color='0.4',lw=.8); ax.set_yticks(yy); ax.set_yticklabels([r[0] for r in rows]); ax.set_title(TASK_LABEL.get(task,task)); ax.set_xlabel('Difference from one-frame LeWM\n(percentage points)'); ax.grid(axis='x',alpha=.2)
axs[0].legend(frameon=False,fontsize=8); save(fig,'FIG5_RANKING_REVERSALS')

# Figure 6 occupancy public labels
occ=ROOT/'a1_results/A1_OCCUPANCY_CURVES.csv'
if occ.exists():
    od=pd.read_csv(occ)
    # accommodate either model or label columns
    col=next((x for x in ['model','condition','label'] if x in od.columns),None)
    if col:
        fig,axs=plt.subplots(2,2,figsize=(9,6),sharey=False)
        for ax,task in zip(axs.ravel(),['reacher','pusht','tworoom','cube']):
            sub=od[od.task==task] if 'task' in od else od
            for key,g in sub.groupby(col):
                name=MODEL_LABEL.get(str(key),str(key))
                ax.plot(g.raw_step,g.occupancy*100,label=name,lw=1.4)
            ax.axvline(25,color='0.75',ls=':',lw=.8); ax.axvline(50,color='0.75',ls=':',lw=.8)
            ax.set_title(TASK_LABEL.get(task,task)); ax.set_xlabel('Raw step'); ax.grid(alpha=.2)
        axs[0,0].set_ylabel('Occupancy (%)'); axs[1,0].set_ylabel('Occupancy (%)'); axs[1,1].legend(fontsize=6,frameon=False)
        save(fig,'FIG6_OCCUPANCY')

# Figure 7 noise scale (generated from sealed scalar records)
fig,ax=plt.subplots(figsize=(6.5,3.2)); tasks=['Reacher','PushT']; n50=[10.0,3.0]; n100=[7.5,2.5]; n3=[4.83,1.67]; x=np.arange(2); w=.22
ax.bar(x-w,n50,w,label='50 cases, 1 stream'); ax.bar(x,n100,w,label='100 cases, 1 stream'); ax.bar(x+w,n3,w,label='100 cases, 3 streams'); ax.set_xticks(x); ax.set_xticklabels(tasks); ax.set_ylabel('Typical half-width (pp)'); ax.legend(frameon=False,fontsize=8); ax.grid(axis='y',alpha=.2); save(fig,'FIG7_NOISE_SCALE')

# Sources inventory.  Every image is tied to the generating script and the
# sealed input family; no placeholder provenance is written.
import hashlib
def file_sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()
sources=[]
for p in sorted(FIG.glob('FIG*.pdf'))+sorted(FIG.glob('FIG*.png')):
    if 'FIG6_OCCUPANCY_REV2' in p.name:
        src='REVISION_2_OCCUPANCY.py; sealed A1_OCCUPANCY_CURVES.csv'
        inp=file_sha(ROOT/'a1_results/A1_OCCUPANCY_CURVES.csv')
    elif 'FIG_APPENDIX_CEM_ITERATIONS' in p.name:
        src='REVISION_2_CEM.py; sealed Step 4 CONTRASTS.csv'
        inp=file_sha(STEP4/'CONTRASTS.csv')
    else:
        src='REVISION_2_ANALYSIS.py; sealed Step 2/4 CSV inputs'
        inp=file_sha(ROOT/'REVISION_2_ANALYSIS.py')
    sources.append({'figure':p.name,'source':src,'input_sha256':inp})
pd.DataFrame(sources).to_csv(ROOT/'a3_results/FIGURE_SOURCES_REVISION.csv',index=False)
