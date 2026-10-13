"""Generate the descriptive CEM-10 versus CEM-30 figure from sealed results."""
from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
src=ROOT.parent/'d1_execution/step4/resume_01/results/CONTRASTS.csv'
df=pd.read_csv(src)
df=df[(df.analysis=='D4_iterations')&(df.cohort=='HELDOUT100')&(df.streams=='ABC')]
tasks=['reacher','pusht','tworoom','cube']; labels={'reacher':'Reacher','pusht':'PushT','tworoom':'TwoRoom','cube':'Cube'}
models=['LeWM_h1','LeWM_h3']; mlabels={'LeWM_h1':'LeWM one-frame','LeWM_h3':'LeWM three-frame'}
colors={'any':'#286090','block':'#d18f00','final':'#2b7a4b'}
fig,axs=plt.subplots(1,4,figsize=(10,2.8),sharey=True)
for ax,task in zip(axs,tasks):
    sub=df[df.task==task]; y=np.arange(len(models)); offs={'any':-.22,'block':0,'final':.22}
    for definition in ['any','block','final']:
        z=[]
        for m in models:
            r=sub[(sub.contrast==f'{m} CEM10 - CEM30')&(sub.definition==definition)].iloc[0]
            z.append((float(r.delta_pp),float(r.ci95_low_pp),float(r.ci95_high_pp)))
        vals=[a[0] for a in z]
        lo=[a[0]-a[1] for a in z]; hi=[a[2]-a[0] for a in z]
        ax.errorbar(vals,y+offs[definition],xerr=[lo,hi],fmt='o',color=colors[definition],capsize=2,label=definition)
    ax.axvline(0,color='.5',lw=.8); ax.set_title(labels[task],fontsize=9); ax.set_yticks(y); ax.set_yticklabels([mlabels[m] for m in models],fontsize=7); ax.set_xlabel('CEM 10 - CEM 30 (pp)',fontsize=7); ax.grid(axis='x',alpha=.2)
axs[0].set_ylabel('Configuration'); axs[-1].legend(frameon=False,fontsize=6,loc='lower right')
fig.suptitle('Descriptive CEM iteration comparison',fontsize=10)
fig.tight_layout(rect=[0,0,1,.92])
for ext in ['pdf','png']:
    fig.savefig(ROOT/'figures'/f'FIG_APPENDIX_CEM_ITERATIONS.{ext}',bbox_inches='tight',dpi=300 if ext=='png' else None)
plt.close(fig)
print('wrote FIG_APPENDIX_CEM_ITERATIONS')
