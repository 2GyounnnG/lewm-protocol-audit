"""Complete cross-platform pip report using Linux markers, never execute downloaded code."""
import json,concurrent.futures,requests
from pathlib import Path
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name,parse_wheel_filename
from packaging.version import Version
from packaging.markers import default_environment
W=Path(__file__).resolve().parent;report=json.load(open(W/'linux_cuda_resolver_report.json'))
env=default_environment();env.update(platform_system='Linux',sys_platform='linux',platform_machine='x86_64',os_name='posix',python_version='3.12',python_full_version='3.12.3',extra='')
rows={canonicalize_name(r['metadata']['name']):{'name':r['metadata']['name'],'version':r['metadata']['version'],'url':r['download_info']['url'],'sha256':r['download_info']['archive_info']['hashes']['sha256'],'requires_dist':r['metadata'].get('requires_dist',[])} for r in report['install']}
def missing():
 out={}
 for row in list(rows.values()):
  for s in row['requires_dist']:
   req=Requirement(s)
   if req.marker and not req.marker.evaluate(env):continue
   key=canonicalize_name(req.name)
   if key in rows:assert Version(rows[key]['version']) in req.specifier,(row['name'],s,rows[key]['version'])
   else:out[key]=req
 return out
while todo:=missing():
 for name,req in todo.items():
  pins=[x.version for x in req.specifier if x.operator=='=='];assert len(pins)==1,(name,str(req))
  r=requests.get(f'https://pypi.org/pypi/{name}/{pins[0]}/json',timeout=60);r.raise_for_status();x=r.json();eligible=[]
  for f in x['urls']:
   if f['packagetype']!='bdist_wheel' or f.get('yanked'):continue
   _,_,_,tags=parse_wheel_filename(f['filename'])
   if any(t.interpreter in ['py3','cp312'] and t.abi in ['none','cp312'] and (t.platform=='any' or ('x86_64' in t.platform and 'manylinux' in t.platform)) for t in tags):eligible.append(f)
  assert eligible,(name,pins);f=sorted(eligible,key=lambda x:x['filename'])[0]
  rows[name]={'name':name,'version':pins[0],'url':f['url'],'sha256':f['digests']['sha256'],'bytes':f['size'],'requires_dist':x['info'].get('requires_dist') or []}
def size(row):
 if 'bytes' not in row:
  r=requests.head(row['url'],allow_redirects=True,timeout=90);r.raise_for_status();row['bytes']=int(r.headers['Content-Length'])
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:rows=dict(zip(rows,pool.map(size,rows.values())))
lock='\n'.join(r['url']+' --hash=sha256:'+r['sha256'] for _,r in sorted(rows.items()))+'\n'
(W/'linux_cuda_wheels.lock').write_text(lock)
result={'platform':env,'packages':list(rows.values()),'total_wheel_bytes':sum(r['bytes'] for r in rows.values()),'Linux_base_dependency_closure_validated':True,'CUDA_packages_explicit_not_host_marker_omissions':True,'installation_not_performed':True}
(W/'LINUX_DOWNLOAD_MANIFEST.json').write_text(json.dumps(result,indent=2));print(len(rows),'wheels',result['total_wheel_bytes'],'bytes')
