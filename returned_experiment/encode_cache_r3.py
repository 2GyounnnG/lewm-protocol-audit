import datetime,hashlib,json,os,sys,time
from pathlib import Path
R=Path('/workspace/d1');W=R/'step4/resume_03_reacher';task='reacher'
assert json.loads((W/'cases/HELDOUT_SEAL.json').read_text())['status']=='SEALED_BEFORE_ANY_GPU_JOB'
sys.path.insert(0,str(W/'code'));sys.path.insert(0,str(R/'repos/M03/code/ap'))
os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')
from adapters.swm_api_compat import install
install()
from anchored_planning.__main__ import main
start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
sys.argv=['anchored_planning','encode-cache','--assets',str(W/'asset_bindings/AP_NATIVE_ASSETS.json'),'--task',task,'--device','cuda:0','--batch-size','128']
main()
path=R/f'latent_cache_step4/{task}_official.npy';h=hashlib.sha256(path.read_bytes()).hexdigest()
asset=W/f'asset_bindings/M03_{task}.json';d=json.loads(asset.read_text());d['latent_cache_sha256']=h;asset.write_text(json.dumps(d,indent=2)+'\n')
receipt={'started_utc':utc,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':task,'status':'COMPLETE','cache_sha256':h,'cache_bytes':path.stat().st_size,'wall_seconds':time.monotonic()-start,'optimizer_updates':0}
(W/f'AP_CACHE_reacher_r3.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
