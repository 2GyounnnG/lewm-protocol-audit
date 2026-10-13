from pathlib import Path
import numpy as np,pandas as pd,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
W=Path(__file__).resolve().parent;ROOT=W.parents[2];P=ROOT/'paper_jair/revision3_part2';F=P/'figures'
plt.rcParams.update({'font.size':9,'axes.titlesize':10,'savefig.dpi':220})
def save(fig,n):
 for ext in ['png','pdf']:fig.savefig(F/(n+'.'+ext),bbox_inches='tight')
 plt.close(fig)
e=pd.read_csv(W.parent/'analysis_final/INTRO_EXAMPLE_STATES.csv')
fig,(l,r)=plt.subplots(1,2,figsize=(13,4.6),gridspec_kw={'width_ratios':[1.5,1]},layout='constrained')
l.set_xlim(-1,53);l.set_ylim(-1.8,6.5);l.set_title('Measurement and decision times (50 raw steps)')
ys=[5.5,4.5,3.5,2.5,1.5,.5];names=['Arrival: OR at every step','Block: END at 5, 10, ..., 50','Final: END at 50','Last 10: mean / all END','LeWM / AD-WM plans','AP re-decisions']
for y in ys:l.hlines(y,0,50,color='#bbbbbb',lw=.7)
l.scatter(np.arange(1,51),np.full(50,ys[0]),s=6,c='#286090')
l.scatter(np.arange(5,51,5),np.full(10,ys[1]),s=20,c='#d18f00')
l.scatter([50],[ys[2]],s=38,c='#2b7a4b')
l.plot([41,50],[ys[3]]*2,lw=7,color='#805399',solid_capstyle='butt');l.scatter(np.arange(41,51),np.full(10,ys[3]),s=12,c='#805399')
l.scatter([0,25],[ys[4]]*2,s=30,marker='^',c='#444');l.scatter([25,50],[ys[4]]*2,s=35,marker='|',c='#444')
l.scatter(np.arange(0,50,5),np.full(10,ys[5]),s=28,marker='^',c='#555')
for x in [25,50]:l.axvline(x,ymin=.22,color='0.6',ls=':',lw=.8)
l.set_yticks(ys,names);l.set_xticks([0,5,10,15,20,25,30,35,40,45,50]);l.set_xlabel('Raw environment step')
l.text(25,-.55,'Reacher: microstep 1 → microstep 2\nOR = either predicate; END = second predicate',ha='center',va='center',fontsize=9,bbox=dict(facecolor='#eef2f6',edgecolor='none',pad=6))
l.text(25,-1.4,'Paired record: case × stream; bootstrap unit: case',ha='center',fontsize=8)
for sp in ['left','right','top']:l.spines[sp].set_visible(False)
for k,col in [(0,'#286090'),(1,'#d66b2f')]:r.plot(e.env_step,e['abs_error'+str(k)],label='Joint '+str(k+1),color=col)
r.axhline(.05,c='#333',ls='--',lw=1,label='0.05 rad threshold');r.axvline(16,c='0.5',ls=':',lw=.8,label='First endpoint hit')
r.set(xlabel='Raw environment step',ylabel='Absolute joint error (rad)',title='One corrected Reacher trajectory',xlim=(1,50));r.legend(frameon=False,fontsize=8);r.grid(alpha=.15)
save(fig,'FIG1_AUDIT_OVERVIEW')
# Use the exact same post-hoc three-stream 200-case rows as Table 6.
c=pd.read_csv(ROOT/'d1_execution/step3/results/POSTHOC_CONTRASTS.csv');q=c[(c.cohort=='mixed200')&(c.family=='factor')]
keys=['h3 - P0','pip - P0','offset - P0','goal - P0','replan1 - P0'];labels=['History length','Library / elite std. correction','Goal offset','Goal image','Native replanning'];tasknames={'reacher':'Reacher','pusht':'PushT','tworoom':'TwoRoom','cube':'Cube'}
inv=pd.read_csv(ROOT/'d1_execution/step0/INVENTORY.csv');fig,axes=plt.subplots(2,2,figsize=(11,6.6));fig.subplots_adjust(wspace=.65,hspace=.5,bottom=.15)
for ax,(task,title) in zip(axes.flat,tasknames.items()):
 sub=q[q.task==task]
 pi=sub[sub.contrast=='pip - P0'].iloc[0];ce=sub[sub.contrast=='cem - P0'].iloc[0]
 for k in ['delta_pp','ci95_low_pp','ci95_high_pp']:assert pi[k]==ce[k]
 vals=[]
 for raw in inv.claimed_gains.dropna():
  try:gs=json.loads(raw)
  except ValueError:continue
  vals.extend(float(g['gain_pp']) for g in gs if g.get('task')==task and isinstance(g.get('gain_pp'),(int,float)))
 if vals:ax.axvspan(min(vals),max(vals),color='.65',alpha=.2,zorder=0)
 for y,k in enumerate(keys):
  z=sub[sub.contrast==k]
  if not len(z):continue
  z=z.iloc[0]
  if pd.isna(z.delta_pp):continue
  ax.errorbar(z.delta_pp,y,xerr=[[z.delta_pp-z.ci95_low_pp],[z.ci95_high_pp-z.delta_pp]],fmt='o',color='#286090',capsize=3)
 ax.axvline(0,color='.5',lw=.8);ax.set_yticks(range(5),labels);ax.set_title(title);ax.set_xlabel('Paired change (percentage points)');ax.grid(axis='x',alpha=.15)
fig.legend(handles=[Patch(facecolor='.65',alpha=.2,label='Published gain range: magnitude reference only')],loc='lower center',bbox_to_anchor=(.5,.015),frameon=False)
save(fig,'FIG2_FACTOR_EFFECTS')
