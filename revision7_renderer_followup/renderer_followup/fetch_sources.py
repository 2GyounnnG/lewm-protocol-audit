from pathlib import Path
import requests,json,concurrent.futures,datetime,re,subprocess
W=Path(__file__).resolve().parent;(W/'sources').mkdir(exist_ok=True);(W/'repos').mkdir(exist_ok=True)
urls={'hf_dataset_card':'https://huggingface.co/datasets/quentinll/lewm-reacher/raw/e70a080d0d04c6072123c9ebd343acf7fff28dbf/README.md','hf_model_card':'https://huggingface.co/quentinll/lewm-reacher/raw/62adae4b71dc474ddf8f794c476ebfe737a743ca/README.md','hf_dataset_api':'https://huggingface.co/api/datasets/quentinll/lewm-reacher','hf_model_api':'https://huggingface.co/api/models/quentinll/lewm-reacher'}
for name,id in [('proworld','2608.01926'),('ppwm','2610.08627'),('keeping','2610.03137'),('decisionmetric','2608.18746'),('singhrepro','2608.10145'),('singhobjective','2608.12959')]:urls[name]='https://arxiv.org/html/'+id+'v1'
def fetch(kv):
 name,url=kv
 try:
  r=requests.get(url,timeout=45);(W/'sources'/(name+'.txt')).write_text(r.text);return dict(name=name,url=url,status=r.status_code,github=sorted(set(re.findall(r'https://github.com/[^\s<>"}]+',r.text))))
 except Exception as e:return dict(name=name,url=url,error=type(e).__name__)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as e:rows=list(e.map(fetch,urls.items()))
(W/'FETCH_RECEIPT.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sources':rows},indent=2));print(json.dumps(rows,indent=2))
repos={'tdjepa':'HKBU-KnowComp/Temporal-Distance-JEPA','deepjepa':'deepjepa/DeepJEPA','tinylab':'joyjeet-singh/tinylab'}
def clone(kv):
 n,r=kv;p=W/'repos'/n
 if not p.exists():
  x=subprocess.run(['git','clone','--depth','1','https://github.com/'+r+'.git',str(p)],capture_output=True,text=True);(W/(n+'_clone.log')).write_text(x.stdout+x.stderr)
 if (p/'.git').exists():return dict(name=n,url='https://github.com/'+r,commit=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip())
 return dict(name=n,error='clone_failed')
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as e:rows=list(e.map(clone,repos.items()))
(W/'REPOSITORIES.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
