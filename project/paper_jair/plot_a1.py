import csv,os
from pathlib import Path
import matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
W=Path(__file__).resolve().parent; R=W/'a1_results';F=W/'figures';F.mkdir(exist_ok=True)
rows=list(csv.DictReader((R/'A1_OCCUPANCY_CURVES.csv').open(encoding='utf-8-sig')))
fig,axs=plt.subplots(1,4,figsize=(12,3.8),sharey=True,layout='constrained')
for ax,t in zip(axs,['reacher','pusht','tworoom','cube']):
 for model,color in [('LeWM_h1','#2672ad'),('LeWM_h3','#e69f00'),('M01_h1','#308c61'),('M03_h1','#c44e52'),('M07_h1','#8172b3')]:
  rr=[r for r in rows if r['task']==t and r['model']==model]
  ax.plot([int(r['raw_step']) for r in rr],[float(r['occupancy'])*100 for r in rr],label=model,color=color,lw=1.6)
 ax.set_title(t);ax.set_xlabel('Raw step');ax.set_ylim(-2,102);ax.grid(alpha=.2)
axs[0].set_ylabel('At-target occupancy (%)');axs[-1].legend(fontsize=7,loc='center left',bbox_to_anchor=(1.02,.5));fig.suptitle('HELDOUT occupancy after full-budget execution',fontsize=12)
fig.savefig(F/'A1_OCCUPANCY_CURVES.pdf',bbox_inches='tight');fig.savefig(F/'A1_OCCUPANCY_CURVES.png',dpi=180,bbox_inches='tight');plt.close(fig)
