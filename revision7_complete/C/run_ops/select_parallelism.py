"""Select concurrency by unchanged trajectories and measured completed-batch throughput."""
from pathlib import Path
import json,numpy as np
W=Path(__file__).resolve().parents[1]
def traces(out):
 return {p.name:json.load(open(p)) for p in (W/out/'traces/reacher').glob('*.json')}
def same(x,y):
 if set(x)!=set(y):return False
 return all(x[k]['compact']['success']==y[k]['compact']['success'] and x[k]['compact']['primitive_steps']==y[k]['compact']['primitive_steps'] and x[k]['compact']['optimizer_seed']==y[k]['compact']['optimizer_seed'] and x[k]['actions']==y[k]['actions'] for k in x)
def batch(n):return json.load(open(W/f'run_ops/BATCH_outputs_parallel{n}.json'))
two=batch(2);assert two['status']=='COMPLETE';x=traces('outputs/parallel2');base=traces('outputs/tech_profile');assert len(x)==4 and len(base)==3
assert same(base,{k:x[k] for k in base}),'Two-way differs from sequential TECH'
four=batch(4);y=traces('outputs/parallel4')
consistent=four['status']=='COMPLETE' and len(y)==4 and same(x,y)
mem=[]
for line in (W/'outputs/parallel4/GPU_MEMORY.csv').read_text().splitlines():
 if ',' in line:mem.append(float(line.split(',')[1]))
headroom=bool(mem) and max(mem)<0.90*49140
faster=four['status']=='COMPLETE' and four['elapsed_seconds']<0.95*two['elapsed_seconds']
n=4 if consistent and headroom and faster else 2
selected=batch(n);rows=[v['compact'] for v in traces(f'outputs/parallel{n}').values()];per=max(r['elapsed_seconds']/r['decisions'] for r in rows if r['decisions'])
# Preserve the original conservative 60 decisions for each of 278 cases, 2x reserve.
# Account both physical devices, and round each sequential cohort's waves up.
waves=sum((count+n-1)//n for count in [128,50,50,50])
future_gpu_seconds=2*per*60*waves*2
old=[json.loads(l) for l in (W/'GPU_BUDGET_LEDGER.jsonl').read_text().splitlines()]
used=sum(r['seconds'] for r in old if r['event']=='end')+sum(json.load(open(f))['gpu_seconds'] for f in (W/'run_ops').glob('BATCH_*.json'))
r={'status':'PASS' if used+future_gpu_seconds<=21600 else 'STOP_ASK_AUTHOR','workers':n,'physical_gpus':2,'two_way_matches_sequential_tech':True,'four_way_matches_two_way':consistent,'four_way_memory_headroom_pass':headroom,'four_way_max_memory_MiB':max(mem) if mem else None,'four_way_at_least_5pct_faster':faster,'two_way_seconds':two['elapsed_seconds'],'four_way_seconds':four['elapsed_seconds'],'prior_gpu_hours':used/3600,'projected_total_gpu_hours_upper':(used+future_gpu_seconds)/3600,'projection':'prior + 2x worst selected-pilot seconds/decision *60*sum(ceil(cohort/workers))*2 physical GPUs','cases_in_each_pilot':4}
(W/'run_ops/PARALLEL_GATE.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));assert r['status']=='PASS','Projected total >6 GPUh; ask author'
