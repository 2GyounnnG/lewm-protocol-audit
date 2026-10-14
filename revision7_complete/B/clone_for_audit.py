import subprocess,os,json,datetime,concurrent.futures,urllib.request
from pathlib import Path
W=Path(__file__).resolve().parent
repos={'stable_worldmodel_main':'galilai-group/stable-worldmodel','stable_worldmodel_63988116':'galilai-group/stable-worldmodel','lewm':'lucas-maes/le-wm','ap':'daybraeklaxry/Aim-Short-to-Reach-Far','adwm':'ad-wm/ad-wm-code','fast_lewm':'Yuntian-Gao/Fast-LeWorldModel','dino_wm':'gaoyuezhou/dino_wm','tdmpc2':'nicklashansen/tdmpc2','dreamerv3':'danijar/dreamerv3','metaworld':'Farama-Foundation/Metaworld','ogbench':'seohongpark/ogbench','gymnasium':'Farama-Foundation/Gymnasium','dm_control':'google-deepmind/dm_control'}
def run(item):
 name,repo=item;p=W/'repos'/name;url='https://github.com/'+repo+'.git';env=dict(os.environ,GIT_LFS_SKIP_SMUDGE='1',GIT_TERMINAL_PROMPT='0');log=W/(name+'.clone.log')
 try:
  with log.open('w') as f:
   subprocess.run(['git','clone','--depth','1','--filter=blob:none',url,str(p)],env=env,stdout=f,stderr=f,check=True,timeout=240)
   ref=None
   if name=='stable_worldmodel_63988116':
    req=urllib.request.Request('https://api.github.com/repos/'+repo+'/commits/63988116',headers={'User-Agent':'JAIR-read-only-audit'})
    ref=json.load(urllib.request.urlopen(req))['sha']
   if name=='ap':ref='984327424ca7a2e52c75a8279197750d9d0b7c8e'
   if ref:
    subprocess.run(['git','-C',str(p),'fetch','--depth','1','origin',ref],env=env,stdout=f,stderr=f,check=True,timeout=180)
    subprocess.run(['git','-C',str(p),'checkout','--detach',ref],env=env,stdout=f,stderr=f,check=True)
  commit=subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()
  return dict(name=name,url=url,commit=commit,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='CLONED_STATIC_ONLY',path=str(p))
 except Exception as e:return dict(name=name,url=url,status='CLONE_FAILED',error=str(e),log=str(log))
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 out=[]
 for r in ex.map(run,repos.items()):out.append(r);print(json.dumps(r),flush=True)
(W/'REPOSITORIES.json').write_text(json.dumps(out,indent=2))
