"""Thin experiment dispatcher. Formal always HELDOUT and full50; TECH stays TECH."""
import argparse,datetime,json,os,sys,time,traceback
from pathlib import Path
os.environ.setdefault('MUJOCO_GL','egl');os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')
W=Path('/workspace/d1/step4/resume_01');R=Path('/workspace/d1')
sys.path.insert(0,str(R/'upload/code'))
sys.path.insert(0,str(W/'code'))
from adapters.common import STREAMS,sha
p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--task',required=True)
p.add_argument('--history',type=int,default=1);p.add_argument('--iterations',type=int,default=30)
p.add_argument('--train-seed',default='official');p.add_argument('--streams',default='ABC')
p.add_argument('--success-mode',choices=['any','full50'],default='full50');p.add_argument('--phase',choices=['TECH','FORMAL'],default='TECH')
p.add_argument('--case-index',type=int);p.add_argument('--case-start',type=int,default=0);p.add_argument('--case-end',type=int,default=100)
p.add_argument('--budget',type=int,choices=[1,50],default=50);p.add_argument('--condition-id');p.add_argument('--output',required=True);a=p.parse_args()
assert a.iterations in (10,30) and a.history in (1,3)
seal=json.loads((W/'cases/HELDOUT_SEAL.json').read_text());assert seal['status']=='SEALED_BEFORE_ANY_GPU_JOB'
assert sha(W/'cases/HELDOUT_CASES_V2.json')==seal['files']['HELDOUT_CASES_V2.json']
if a.phase=='FORMAL':
 assert a.budget==50 and a.success_mode=='full50' and a.case_index is None and a.streams=='ABC'
 from formal_guard import authorize
 launch=authorize(a.condition_id,__file__,W/'FORMAL_LAUNCH_RECEIPT.json');s=launch['condition_specs'][a.condition_id]
 assert all(str(s[k])==str(getattr(a,k)) for k in ['model','task','history','iterations','train_seed'])
 assert 0<=a.case_start<a.case_end<=100
import torch
torch.set_num_threads(1);torch.set_num_interop_threads(1)
if a.model=='LeWM':
 import h5py,hdf5plugin
 from official_formal_v4_reacher import build_model,run_case,records
 torch.set_float32_matmul_precision('highest');torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;torch.backends.cudnn.benchmark=False
 cases=json.loads((W/'cases/HELDOUT_CASES_V2.json').read_text())['tasks'][a.task][a.case_start:a.case_end] if a.phase=='FORMAL' else json.loads((W/f'cases/tech_{a.task}.json').read_text())
 if a.case_index is not None:cases=[cases[a.case_index]]
 model,identity=build_model(a.task,'cuda:0');rec=next(r for r in records(a.task) if r['kind']=='dataset')
 with h5py.File(R/rec['unpacked_destination'],'r') as hf:
  for c in cases:
   for letter in a.streams:
    stream=STREAMS[ord(letter)-65];out=Path(a.output)/c['case_id']/stream
    run_case(model,identity,hf,c,stream,a.history,25,a.success_mode,out,'cuda:0',None,a.phase,a.condition_id,a.iterations,a.budget)
else:
 assert a.iterations==30 and a.model in ('M01','M03','M07')
 from types import SimpleNamespace
 from method_formal_v3_reacher import run
 assetname=(a.model+'_'+a.train_seed if a.model=='M07' else a.model)+'_'+a.task+'.json'
 args=SimpleNamespace(**vars(a),method=a.model,assets=str(W/'asset_bindings'/assetname),cases=str(W/'cases/HELDOUT_CASES_V2.json'),
    device='cuda:0',prereg_receipt=str(W/'FORMAL_LAUNCH_RECEIPT.json'))
 run(args)
