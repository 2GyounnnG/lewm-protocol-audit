from pathlib import Path
import tarfile,hashlib,json,io,datetime
R=Path(__file__).resolve().parents[3]
W=Path(__file__).resolve().parent
P=R/'paper_jair/revision3_part2'
OLD=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/delivery/JAIR_R3_PART2_MATERIALS.tar.gz')
OUT=W/'JAIR_REVISION4_MATERIALS_VERIFIED.tar.gz'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''): h.update(b)
 return h.hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
assert sha(OLD)=='b784e80859702902f45fa5b29c88336d33ccbf3ea3462dab6221d6149a20c1d8'
assert not OUT.exists(),'Preserve existing package; do not overwrite'
files=[]
for d in [W,P]:
 for p in sorted(d.rglob('*')):
  if not p.is_file() or p.name in ['SEAL_REVISION4.json','MATERIALS_REVISION4_RECEIPT.json'] or any(x.startswith('build') or x=='__pycache__' for x in p.relative_to(d).parts):continue
  files.append(p)
seal={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Revision 4 current manuscript and CPU analysis. Prior SEAL.json remains historical; baseline preserved in REVISION3_PART2_BEFORE_REV4.tar.gz.','files':[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
dump(P/'SEAL_REVISION4.json',seal)
files.append(P/'SEAL_REVISION4.json')
files.append(R/'paper_jair/JAIR_REVISION_4_CODEX_PROMPT_ZH.md')
for pat in ['d1_execution/step0/*INVENTORY*','d1_execution/step1/repos/M01/config/eval/*.yaml','d1_execution/step1/repos/M01/config/eval/solver/cem.yaml','d1_execution/step1/repos/M01/eval.py']:
 files.extend(p for p in R.glob(pat) if p.is_file())
overlay={'project/'+str(p.relative_to(R)):p for p in files}
manifest={}
with tarfile.open(str(OLD),'r|gz') as src,tarfile.open(str(OUT),'w|gz') as dest:
 for m in src:
  if not m.isfile() or m.name in overlay or m.name=='MATERIALS_MANIFEST.json':continue
  f=src.extractfile(m);data=f.read();h=hashlib.sha256(data).hexdigest();dest.addfile(m,io.BytesIO(data));manifest[m.name]={'bytes':len(data),'sha256':h}
 for name,p in sorted(overlay.items()):
  data=p.read_bytes();m=tarfile.TarInfo(name);m.size=len(data);m.mode=0o644;dest.addfile(m,io.BytesIO(data));manifest[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 data=json.dumps({'version':'JAIR Revision 4','base_archive_sha256':sha(OLD),'files':manifest},ensure_ascii=False,indent=2).encode();m=tarfile.TarInfo('MATERIALS_MANIFEST.json');m.size=len(data);dest.addfile(m,io.BytesIO(data))
verified=0
with tarfile.open(str(OUT),'r|gz') as t:
 for m in t:
  if not m.isfile() or m.name=='MATERIALS_MANIFEST.json':continue
  b=t.extractfile(m).read();assert manifest[m.name]=={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()},m.name;verified+=1
assert verified==len(manifest)
receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'path':str(OUT),'bytes':OUT.stat().st_size,'sha256':sha(OUT),'verified_files':verified,'mismatches':0,'base_archive_retained':str(OLD),'publication':'local materials only; no Zenodo or GitHub actions'}
dump(W/'MATERIALS_REVISION4_RECEIPT.json',receipt)
print(json.dumps(receipt,ensure_ascii=False),flush=True)
