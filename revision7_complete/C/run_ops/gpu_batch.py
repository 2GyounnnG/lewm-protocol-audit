"""Native AP sharding only; one locked batch, physical-device-seconds <=6h."""
import argparse,json,os,sys,time,subprocess,signal,fcntl
from pathlib import Path
W=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--output',required=True);p.add_argument('--workers',type=int,choices=[1,2,4],required=True);p.add_argument('--limit',type=int);a=p.parse_args()
assert os.environ.get('AP_GPU_SSH_AUTHORIZED')
lock=(W/'GPU_BATCH.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
old=W/'GPU_BUDGET_LEDGER.jsonl';events=[json.loads(l) for l in old.read_text().splitlines()] if old.exists() else []
assert {e['id'] for e in events if e['event']=='start'}=={e['id'] for e in events if e['event']=='end'},'Unfinished sequential GPU command'
used=sum(e['seconds'] for e in events if e['event']=='end')
for f in (W/'run_ops').glob('BATCH_*.json'):
 r=json.load(open(f));assert r['status'] in ['COMPLETE','FAILED'],'Unfinished batch';used+=r['gpu_seconds']
output=W/a.output;assert not output.exists(),'Never overwrite a batch';output.mkdir(parents=True)
receipt=W/'run_ops'/('BATCH_'+a.output.replace('/','_')+'.json');assert not receipt.exists()
devices=min(a.workers,2);remaining=21600-used;assert remaining>0
r={'status':'RUNNING','root':a.root,'output':a.output,'workers':a.workers,'devices':devices,'start_epoch':time.time(),'prior_gpu_seconds':used,'gpu_seconds':0,'limit':a.limit,'commands':[]}
def save():
 temp=receipt.with_suffix('.tmp');temp.write_text(json.dumps(r,indent=2));temp.replace(receipt)
processes=[];logs=[];start=time.monotonic();save()
try:
 for i in range(a.workers):
  cmd=[sys.executable,'-m','anchored_planning','evaluate','--assets','assets.remote.json','--task','reacher','--study','main','--root',a.root,'--device',f'cuda:{i%2}','--output',a.output,'--shards',str(a.workers),'--shard-index',str(i)]
  if a.limit:cmd+=['--limit',str(a.limit)]
  r['commands'].append(cmd);log=(output/f'worker{i}.log').open('x');logs.append(log)
  processes.append(subprocess.Popen(cmd,cwd=W,stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
 save()
 with (output/'GPU_MEMORY.csv').open('x') as metrics:
  while any(q.poll() is None for q in processes):
   if (time.monotonic()-start)*devices>=remaining:raise TimeoutError('Six GPU-hour cap')
   if any(q.poll() not in (None,0) for q in processes):raise RuntimeError('Native worker failed; retain outputs')
   metrics.write(str(time.time())+'\n');subprocess.run(['nvidia-smi','--query-gpu=index,memory.used,utilization.gpu','--format=csv,noheader,nounits'],stdout=metrics,check=True);metrics.flush();time.sleep(2)
 assert all(q.returncode==0 for q in processes),'Worker failure'
 r['status']='COMPLETE'
except BaseException as e:
 r['status']='FAILED';r['error']=repr(e)
 for q in processes:
  if q.poll() is None:os.killpg(q.pid,signal.SIGTERM)
 for q in processes:
  try:q.wait(timeout=15)
  except subprocess.TimeoutExpired:os.killpg(q.pid,signal.SIGKILL);q.wait()
 raise
finally:
 r.update(elapsed_seconds=time.monotonic()-start,gpu_seconds=(time.monotonic()-start)*devices,end_epoch=time.time(),returncodes=[q.poll() for q in processes]);save()
 for log in logs:log.close()
