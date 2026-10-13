from pathlib import Path
import json,pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
W=Path(__file__).resolve().parent;P=W.parents[1]/'revision3_part2';M=json.loads((W.parent/'revision4/EFFECTIVE_MACROS.json').read_text())
def ci(r):return f"{r['delta_pp']:+.1f} [{r['ci95_low_pp']:+.1f}, {r['ci95_high_pp']:+.1f}]"
tab=pd.read_csv(W/'TABLE16_UNIFIED_SEED.csv')
for r in tab.to_dict('records'):M[r['macro']]=ci(r)
M['RfiveReacherThreeAPAllTen']=ci(json.loads((W/'REVERSAL_ALL10.json').read_text()))
f=pd.read_csv(W/'FIG5_THREE_LABEL_CONTRASTS.csv');names={'LeWM_h3':'LeWM three-frame','M01_h1':'Fast-LeWM','M03_h1':'AP','M07_h1':'AD-WM'}
extras=[]
for i,r in enumerate(f[f.metric=='last10_all'].to_dict('records')):
 k='RfiveWindow'+chr(65+i);M[k]=ci(r)
 extras.append(f"{r['task'].title().replace('Pusht','PushT')} & {names[r['model']]} $-$ LeWM one-frame & All last 10 & \\{k}{{}} \\\\")
path=P/'tables/table_window_intervals.tex';s=path.read_text();s=s.replace(r'\\\bottomrule',r'\\'+'\n'+ '\n'.join(extras)+r'\bottomrule');path.write_text(s)
# Keep the earlier mean-window rows, but avoid duplicate AP/Fast all-window rows.
s=path.read_text().splitlines();s=[l for l in s if not any('\\RfourWindow'+n+'{}' in l for n in ['Four','Six','Eight'])];path.write_text('\n'.join(s)+'\n')
p=P/'tables/table_ap_lewm_intervals.tex';s=p.read_text();a=s.index(r'\caption{');b=s.index(r'}\label',a);s=s[:a]+r'\caption{Paired AP minus one-frame LeWM contrasts from the saved formal trajectories, using the frozen case bootstrap with 5,000 replicates and seed 20261011 for all tasks and labels.'+s[b:];p.write_text(s)
p=P/'tables/table_reporting.tex';s=p.read_text().replace('Held-out Reacher three-frame minus one-frame, any-step','Held-out Reacher three-frame minus one-frame').replace(r'\RfourReportingScaleJ{}',r'\ReacherHistoryDeltaRevision{} pp (any-step), \ReacherHistoryFinalDelta{} pp (final-step)');M['ReacherHistoryFinalDelta']='+48.3';p.write_text(s)
p=P/'main.tex';s=p.read_text().replace('a3_results/revision4_numbers.tex','a3_results/revision5_numbers.tex')
s=s.replace('For the specific three-frame LeWM--AP comparison, the contrast changes from \\RfourReacherThreeAPAny{} points under any-step success to \\RfourReacherThreeAPFinal{} under final-step success; both intervals exclude zero.',r'Corrected descriptive comparisons show reversals for the same controller pair across three labels. In Reacher, three-frame LeWM minus AP is \RfourReacherThreeAPAny{} points for any-step, \RfourReacherThreeAPFinal{} for final-step, and \RfiveReacherThreeAPAllTen{} for all-last-ten success. In PushT, AP minus one-frame LeWM is \APLeWMPushTAnyCI{}, \APLeWMPushTFinalCI{}, and \RfourWindowSix{} points, respectively: the final-step and sustained-window intervals lie on opposite sides of zero.')
old='Success timing then changes the ranking for a specific configuration pair:'
start=s.index(old);end=s.index('\n\n',start)
para=r'The same controller pair can reverse order across three success labels. For three-frame LeWM minus AP in Reacher, any-step, final-step, and all-last-ten contrasts are \RfourReacherThreeAPAny{}, \RfourReacherThreeAPFinal{}, and \RfiveReacherThreeAPAllTen{} points; all three intervals exclude zero, with two opposite orderings. For AP minus one-frame LeWM in PushT, the corresponding contrasts are \APLeWMPushTAnyCI{}, \APLeWMPushTFinalCI{}, and \RfourWindowSix{} points. Any-step success is unresolved, while final-step and sustained-window success establish opposite orderings. These reversals are corrected descriptive results on the same saved trajectories.'
s=s[:start]+para+s[end:]
# Put the requested reversal result in introduction paragraph three.
start=s.index('Common-protocol gains remain large');end=s.index('\n\n',start);common=s[start:end];s=s[:start]+s[end+2:];loc=s.index(para)+len(para);s=s[:loc]+'\n\n'+common+s[loc:]
s=s.replace('The intervention supplies both past observations and two executed action blocks; it does not isolate velocity information or a braking mechanism. Moreover, one-frame any-step success is already \\ReacherLeWMOneAny\\%, leaving only \\APReacherAnyDelta{} points below its ceiling, so comparing the endpoint and any-step effect sizes cannot establish a mechanism.',r'The intervention provides observation and action history, and this study measures its effects without attributing them to a particular mechanism. One-frame any-step success is already \ReacherLeWMOneAny\%, leaving only \APReacherAnyDelta{} points below its ceiling.')
start=s.index('For three-frame LeWM versus AP in Reacher,');end=s.index('\n\n',start)
s=s[:start]+para+r' Figure~\ref{fig:reversal} uses one-frame LeWM as the reference and shows all three labels for every configuration. For PushT, the final-minus-any contrast change is \APLeWMPushTChangeCI{} points. TwoRoom\textquotesingle s any-step and final-step rates and ordering are close.'+s[end:]
s=s.replace('Method differences from one-frame LeWM under any-step and final-step success.','Method differences from one-frame LeWM under any-step, final-step, and all-last-ten success.').replace('Success timing can change the sign of a paired method contrast.','Three success labels can order the same controllers differently.')
p.write_text(s)
(P/'a3_results/revision5_numbers.tex').write_text('% Revision 5: single active numeric macro source.\n'+'\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in M.items())+'\n');(W/'EFFECTIVE_MACROS.json').write_text(json.dumps(M,indent=2)+'\n')
plt.rcParams.update({'font.size':9,'savefig.dpi':240})
fig,axes=plt.subplots(1,2,figsize=(10,4.3),sharey=True)
for ax,t in zip(axes,['reacher','pusht']):
 for i,(d,c,mark,lab) in enumerate([('any','#286090','o','Any-step'),('final','#d66b2f','s','Final-step'),('last10_all','#29824d','^','All last 10')]):
  rs=f[(f.task==t)&(f.metric==d)].set_index('model').loc[list(names)];v=rs.delta_pp.to_numpy();lo=rs.ci95_low_pp.to_numpy();hi=rs.ci95_high_pp.to_numpy()
  ax.errorbar(v,np.arange(4)+(i-1)*.22,xerr=[v-lo,hi-v],fmt=mark,color=c,capsize=3,label=lab,ms=5)
 ax.set_title(t.title().replace('Pusht','PushT'));ax.set_yticks(np.arange(4),list(names.values()));ax.axvline(0,c='.5',lw=.8);ax.grid(axis='x',alpha=.15);ax.set_xlabel('Difference from LeWM one-frame (pp)');ax.set_ylim(-.55,3.55)
fig.legend(*axes[1].get_legend_handles_labels(),loc='lower center',ncol=3,frameon=False,bbox_to_anchor=(.57,.01));fig.tight_layout(rect=(0,.12,1,1))
for ext in ['png','pdf']:fig.savefig(P/'figures'/('FIG5_RANKING_REVERSALS.'+ext),bbox_inches='tight')
print('Revision 5 text, tables, macros and Figure 5 generated')
