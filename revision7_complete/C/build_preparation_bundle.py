from pathlib import Path
import tarfile,json,hashlib,datetime
W=Path(__file__).resolve().parent
exclude={'PREPARATION_BUNDLE_RECEIPT.json','PREPARATION_SHA256.json','THREE_SEED_DRAFT_RECEIPT.json','COMPARE_SELF_CHECK.json','compare_cases_before_confirmation.py','prepare_three_seed_protocols.py'}
files=[p for p in W.iterdir() if p.is_file() and p.suffix in ['.py','.sh','.json','.jsonl','.lock','.md'] and p.name not in exclude]
for folder in ['cases','protocol_main128','protocol_seed42','protocol_seed43','protocol_seed44','ap_source/code/ap']:
 files += [p for p in (W/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and '.egg-info' not in str(p)]
files.append(W/'ap_source/LICENSE');files=sorted(set(files))
manifest={str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(W/'PREPARATION_SHA256.json').write_text(json.dumps(manifest,indent=2));files.append(W/'PREPARATION_SHA256.json')
out=W.parent/'AP_REVISION7_PREPARATION_READY.tar.gz'
assert not out.exists(),'Do not replace an existing ready archive; create a versioned name'
with tarfile.open(out,'w:gz') as t:
 for p in files:t.add(p,arcname='ap_revision7/'+str(p.relative_to(W)))
with tarfile.open(out,'r:gz') as t:
 for p,s in manifest.items():assert hashlib.sha256(t.extractfile('ap_revision7/'+p).read()).hexdigest()==s,p
(W/'PREPARATION_BUNDLE_RECEIPT.json').write_text(json.dumps({'status':'READY_WAITING_AUTHOR_SSH','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cpu_scope_author_confirmed':True,'full_retrieval_entry_gate':'after SSH, before formal','groups_separate':True,'files':len(files),'all_archive_sha_match':True,'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'path':str(out.resolve())},indent=2))
print((W/'PREPARATION_BUNDLE_RECEIPT.json').read_text())
