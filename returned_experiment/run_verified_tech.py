"""Finite TECH-only queue, 9 fixed configurations; never launches formal work."""
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import time

W=Path('/workspace/d1/step4/resume_01')
PY='/workspace/d1/venvs/r3-reacher-v3/bin/python'
SPEC=[('LeWM_h1_i30','LeWM',1,30,'official'),('LeWM_h3_i30','LeWM',3,30,'official'),('M01_h1','M01',1,30,'released'),('M03_h1','M03',1,30,'official'),('M07_3072_h1','M07',1,30,'3072'),('M07_4096_h1','M07',1,30,'4096'),('M07_6144_h1','M07',1,30,'6144'),('LeWM_h1_i10','LeWM',1,10,'official'),('LeWM_h3_i10','LeWM',3,10,'official')]
def utc():return dt.datetime.now(dt.timezone.utc).isoformat()
def run(spec,gpu):
 name,model,h,it,seed=spec
 out=W/'tech_verified'/name
 assert not out.exists(),out
 env=dict(os.environ,MUJOCO_GL='egl',CUDA_VISIBLE_DEVICES=str(gpu),PYTHONPATH=str(W)+':'+str(W/'code'))
 args=[PY,str(W/'code/step4_worker_r3_final.py'),'--model',model,'--task','reacher','--history',str(h),'--iterations',str(it),'--train-seed',seed,'--streams','ABC','--success-mode','full50','--phase','TECH','--budget','50','--output',str(out)]
 log=W/'logs_verified'/f'TECH_{name}.log';log.parent.mkdir(exist_ok=True)
 start=time.monotonic();print(json.dumps({'event':'START','utc':utc(),'group':name,'gpu':gpu}),flush=True)
 with log.open('xb') as f:r=subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT)
 record={'group':name,'gpu':gpu,'exit_code':r.returncode,'wall_seconds':time.monotonic()-start,'completed_utc':utc(),'command':args,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest()}
 (W/'logs_verified'/f'{name}_process.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record),flush=True)
 return record
def main():
 runtime=json.loads((W/'runtime_checks_final.json').read_text());assert runtime['status']=='PASS'
 smoke=json.loads((W/'FINAL_BIND_CPU_SMOKE.json').read_text());assert smoke['status']=='PASS'
 record=json.loads((W/'CORRECTION_RECORDING_REVISION_PRETECH.json').read_text())
 for rel,wanted in record['code_sha256'].items():assert hashlib.sha256((W/rel).read_bytes()).hexdigest()==wanted,rel
 q=queue.Queue()
 for spec in SPEC:q.put(spec)
 def worker(gpu):
  rows=[]
  while True:
   try:spec=q.get_nowait()
   except queue.Empty:return rows
   rows.append(run(spec,gpu))
   if rows[-1]['exit_code']!=0:return rows
 with cf.ThreadPoolExecutor(max_workers=4) as pool:
  rows=sum(list(pool.map(worker,range(4))),[])
 report={'utc':utc(),'status':'PROCESSES_COMPLETE_PENDING_T1_T4' if len(rows)==9 and all(r['exit_code']==0 for r in rows) else 'PROCESS_FAILURE','rows':rows,'not_a_technical_gate_receipt':True}
 (W/'TECH_VERIFIED_PROCESS_STATUS.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'event':'DONE','status':report['status'],'groups':len(rows)}),flush=True)
if __name__=='__main__':main()
