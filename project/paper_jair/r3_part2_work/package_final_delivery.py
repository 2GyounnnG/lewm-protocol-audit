"""Local-only archive and external delivery. Never contacts or controls an instance."""
from pathlib import Path
import hashlib,json,tarfile,io,datetime,shutil,os
ROOT=Path(__file__).resolve().parents[2];W=ROOT/'paper_jair/r3_part2_work';P=ROOT/'paper_jair/revision3_part2'
E=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013');R=E/'returns';D=E/'delivery'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def obj(p):return json.loads(p.read_text())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def add_tree(base):
 for p in base.rglob('*'):
  if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and not p.name.startswith('._'):add(p)
files={}
def add(p):
 p=Path(p)
 if not p.is_file():raise FileNotFoundError(p)
 if p.is_relative_to(ROOT):name='project/'+str(p.relative_to(ROOT))
 elif p.is_relative_to(R/'STAGE3_VERIFIED/experiment'):name='returned_experiment/'+str(p.relative_to(R/'STAGE3_VERIFIED/experiment'))
 elif p.is_relative_to(E):name='return_evidence/'+str(p.relative_to(E))
 else:raise ValueError('Unexpected input location '+str(p))
 files[name]=p
assert Path('/Volumes/MyProj').is_mount(),'MyProj not mounted: no fallback'
assert obj(W/'PDF_QA.json')['status']=='PASS'
assert obj(R/'FORMAL_STAGE_3_LOCAL_RETURN.json')['mismatch_count']==0
# Both generator manifests enumerate actual raw inputs. Recheck every hash before packaging.
checked=0
for rel in ['analysis_final/ANALYSIS_MANIFEST.json','paper_assets_final_v2/PAPER_ASSETS_MANIFEST.json']:
 for name,want in obj(W/rel)['inputs'].items():
  p=Path(name);assert sha(p)==want,('Input changed',name);add(p);checked+=1
# Retain all final code, TECH, runtime, excluded early outputs and formal raw records.
add_tree(R/'STAGE3_VERIFIED/experiment')
for p in R.glob('*LOCAL_RETURN.json'):add(p)
add_tree(E/'STOP_EVIDENCE')
for p in W.iterdir():
 if p.is_file() and p.suffix in ['.py','.json','.md','.log','.txt']:add(p)
for sub in ['analysis_final','paper_assets_final_v2','paper_assets_final','macro_final','execution_report_final','execution_report_final_v2']:add_tree(W/sub)
# Old paper generators and their existing small summary/source inputs; no old files are modified.
for p in (ROOT/'paper_jair').iterdir():
 if p.is_file() and p.suffix in ['.py','.json','.md','.tex','.bib']:add(p)
for sub in ['a1_results','a2_results','a3_results','figures','tables']:add_tree(ROOT/'paper_jair'/sub)
add(ROOT/'paper_jair/jair_kit/extracted/JAIR AuthorKit/JAIR_Example_Template/JAIR_Example_Template.tex')
for sub in ['d1_execution/prereg','d1_execution/step1/upload/code','d1_execution/step4/resume_01/results','d1_execution/step4/resume_01/evidence','d1_execution/step4/resume_01/cases','d1_execution/step2/resume_03/results','d1_execution/step3/results']:add_tree(ROOT/sub)
# Full original held-out trajectories supply source records for all four tasks.
add_tree(ROOT/'d1_execution/step4/resume_01/remote_sync/FINAL_RESULTS/formal')
for sub in ['d1_execution/step1/HF_ASSETS_MANIFEST.json','d1_execution/step1/upload/HF_ASSETS_MANIFEST.json']:add(ROOT/sub)
# New manuscript files are sealed separately first; the seal deliberately excludes itself.
assert not (P/'SEAL.json').exists(),'Final manuscript seal already exists; do not overwrite'
rows=[]
for p in sorted(P.rglob('*')):
 if p.is_file():rows.append({'path':str(p.relative_to(P)),'size':p.stat().st_size,'sha256':sha(p)})
seal={'status':'FINAL_LOCAL_DELIVERY_SEALED','utc':now(),'files':rows,'file_count':len(rows),'raw_result_seal_sha256':sha(W/'CORRECTED_RESULTS_SEAL.json'),'final_return_sha256':sha(R/'FORMAL_STAGE_3_LOCAL_RETURN.json'),'analysis_manifest_sha256':sha(W/'analysis_final/ANALYSIS_MANIFEST.json'),'publication_status':'LOCAL_ONLY_NOT_SUBMITTED_NOT_PUBLISHED','stop':'ACCEPTED_PLATFORM_FINAL_STATE_UNVERIFIED_AUTHOR_HANDLES_DESTROY'}
(P/'SEAL.json').write_text(json.dumps(seal,ensure_ascii=False,indent=2)+'\n')
add_tree(P)
manifest={'utc':now(),'files':{n:{'sha256':sha(p),'size':p.stat().st_size} for n,p in sorted(files.items())},'input_hash_checks':checked,'large_public_assets':'Identifiers, URLs and SHA only; not redistributed','scope':'Local pending-release package; licenses and publication require author decision'}
(W/'MATERIALS_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
D.mkdir(exist_ok=True)
archive=D/'JAIR_R3_PART2_MATERIALS.tar.gz';assert not archive.exists(),'Do not overwrite archive'
print('Packaging',len(files),'files',sum(p.stat().st_size for p in files.values()),'bytes',flush=True)
with tarfile.open(archive,'w:gz',compresslevel=5) as tar:
 for name,p in sorted(files.items()):tar.add(p,arcname=name,recursive=False)
 b=(W/'MATERIALS_MANIFEST.json').read_bytes();info=tarfile.TarInfo('MATERIALS_MANIFEST.json');info.size=len(b);tar.addfile(info,io.BytesIO(b))
print('Verifying archive members',flush=True)
verified=0
with tarfile.open(archive,'r:gz') as tar:
 for member in tar:
  if not member.isfile() or member.name=='MATERIALS_MANIFEST.json':continue
  want=manifest['files'][member.name]['sha256'];h=hashlib.sha256()
  stream=tar.extractfile(member)
  for b in iter(lambda:stream.read(1048576),b''):h.update(b)
  assert h.hexdigest()==want,member.name
  verified+=1
assert verified==len(files)
# Human-readable copy, byte-copy only (no xattrs/resource forks on exFAT).
copy_manifest={}
for p in sorted(P.rglob('*')):
 if p.is_file():
  dst=D/'revision3_part2'/p.relative_to(P);dst.parent.mkdir(parents=True,exist_ok=True)
  with p.open('rb') as a,dst.open('wb') as b:shutil.copyfileobj(a,b)
  assert sha(dst)==sha(p);copy_manifest[str(dst.relative_to(D))]=sha(dst)
receipt={'status':'COMPLETE_VERIFIED_LOCAL_DELIVERY','utc':now(),'archive':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'archive_files_verified':verified,'copy_files_verified':len(copy_manifest),'mismatch_count':0,'manuscript_seal_sha256':sha(P/'SEAL.json'),'copy_manifest':copy_manifest,'materials_manifest_sha256':sha(W/'MATERIALS_MANIFEST.json'),'stop_request_accepted':True,'actual_platform_final_state':'NOT_INDEPENDENTLY_VERIFIED','remote_contact_after_stop':False}
(W/'DELIVERY_RECEIPT.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
(D/'DELIVERY_RECEIPT.json').write_bytes((W/'DELIVERY_RECEIPT.json').read_bytes())
(D/'MATERIALS_MANIFEST.json').write_bytes((W/'MATERIALS_MANIFEST.json').read_bytes())
print(json.dumps({k:v for k,v in receipt.items() if k!='copy_manifest'},ensure_ascii=False,indent=2),flush=True)
