"""CPU-only D1 statistics on fully delivered binary results; no model libraries.
Input CSV: case_id, model, train_seed, stream, success. One task/history/cohort per invocation.
Expected grid comes from a frozen JSON {case_ids, models:{name:{train_seeds,streams}}}.
"""
import argparse,csv,json,hashlib
from pathlib import Path
import numpy as np

def matrix(rows,expected,model):
 ids=expected['case_ids'];spec=expected['models'][model];seeds=list(map(str,spec['train_seeds']));streams=spec['streams']
 if not ids or len(ids)!=len(set(ids)):raise ValueError('Expected case identity')
 wanted={(c,s,t) for c in ids for s in seeds for t in streams};found={}
 for r in rows:
  if r['model']!=model:continue
  k=(r['case_id'],str(r['train_seed']),r['stream'])
  if k not in wanted or k in found:raise ValueError('Unexpected or duplicate cell')
  if str(r['success']) not in ('0','1'):raise ValueError('Missing/nonbinary outcome, never impute')
  found[k]=int(r['success'])
 if set(found)!=wanted:raise ValueError('Delivery not100%')
 return np.array([[[found[c,s,t] for t in streams] for s in seeds] for c in ids],float)

def paired(a,b,boot=5000,seed=20261011):
 if a.shape[0]!=b.shape[0]:raise ValueError('Unpaired case counts')
 d=a.reshape(len(a),-1).mean(1)-b.reshape(len(b),-1).mean(1)
 rng=np.random.default_rng(seed);draw=np.empty(boot)
 for start in range(0,boot,250):
  size=min(250,boot-start);draw[start:start+size]=d[rng.integers(0,len(d),(size,len(d)))].mean(1)*100
 lo,hi=np.quantile(draw,[.025,.975]);mean=float(d.mean()*100)
 # Centered bootstrap null distribution; two-sided absolute tail, finite-B correction.
 p=(1+int((np.abs(draw-mean)>=abs(mean)).sum()))/(boot+1)
 return dict(n_cases=len(d),delta_pp=mean,ci95_low_pp=float(lo),ci95_high_pp=float(hi),halfwidth_pp=float((hi-lo)/2),p_centered_bootstrap=p,practically_negligible=bool(lo>=-5 and hi<=5),gain_supported=bool(lo>0),label='实际可忽略' if lo>=-5 and hi<=5 else '增益成立' if lo>0 else '未检出')

def holm(pvalues):
 p=np.asarray(pvalues);order=np.argsort(p);out=np.empty(len(p));running=0
 for i,j in enumerate(order):running=max(running,(len(p)-i)*p[j]);out[j]=min(1,running)
 return out.tolist()

def noise(delta,boot=5000,outer=250,seed=20261011):
 """Cases x10 paired differences, already training-seed averaged; same step0 diagnostic.
 Whole stream subsets fixed within a resampled dataset; empirical interpolation, not new data.
 """
 d=np.asarray(delta,float)
 if d.ndim!=2 or d.shape[1]!=10:raise ValueError('H4 requires10 delivered planner streams; cannot invent7')
 rng=np.random.default_rng(seed);reference=d.mean()*100;rates=[];widths=[]
 for threshold in (5,10,15):
  for direction in ('positive','absolute'):
   eligible=abs(d[:,:3].mean()*100)<=2+1e-9
   single=d[:,:3].mean(0)*100
   hits=int(np.sum((single if direction=='positive' else np.abs(single))>=threshold-1e-9)) if eligible else 0
   rates.append(dict(threshold_pp=threshold,direction=direction,null_mean_ABC_abs_le2=bool(eligible),hits=hits,denominator=3,rate_all_opportunities_pct=hits/3*100,conditional_rate_pct=hits/3*100 if eligible else None))
 for n in (50,100,200):
  for s in (1,3,10):
   vals=[]
   for _ in range(outer):
    streams=rng.choice(10,s,replace=False);x=d[:,streams].mean(1);sample=x[rng.integers(0,len(x),n)]
    draws=sample[rng.integers(0,n,(boot,n))].mean(1)*100
    lo,hi=np.quantile(draws,[.025,.975]);vals.append((hi-lo)/2)
   widths.append(dict(n_cases=n,n_streams=s,halfwidth_median_pp=float(np.median(vals)),halfwidth_p90_pp=float(np.quantile(vals,.9))))
 return dict(reference_delta_pp=float(reference),false_signals=rates,widths=widths,warning='Empirical resampling of delivered10-stream matrix; not a type-I-error theorem')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--expected',required=True);p.add_argument('--method',required=True);p.add_argument('--baseline',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 rows=list(csv.DictReader(open(a.input)));e=json.loads(Path(a.expected).read_text())
 result=paired(matrix(rows,e,a.method),matrix(rows,e,a.baseline));result['input_sha256']=hashlib.sha256(Path(a.input).read_bytes()).hexdigest();result['holm_note']='Combine all12 method×task p values per baseline family; do not adjust one file alone.'
 Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
