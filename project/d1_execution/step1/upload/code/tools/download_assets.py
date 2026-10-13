"""STEP2 ONLY. Pinned HF downloads + SHA; optional safe streaming data unpack.
Nothing executes at import. Never load a checkpoint or simulator.
"""
import argparse,json,urllib.request,re,hashlib,shutil,tarfile
from pathlib import Path
from adapters.common import sha

def download(record,root):
 path=(root/record['destination']).resolve()
 if not path.is_relative_to(root.resolve()):raise ValueError('Destination escape')
 if not re.fullmatch('[0-9a-f]{64}',record['sha256']):raise ValueError('Unresolved asset hash')
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():
  if sha(path)!=record['sha256']:raise ValueError('Existing asset differs; retain and investigate')
  return path
 part=path.with_suffix(path.suffix+'.part');h=hashlib.sha256();n=0
 with urllib.request.urlopen(record['url'],timeout=120) as src,part.open('xb') as out:
  for chunk in iter(lambda:src.read(8<<20),b''):out.write(chunk);h.update(chunk);n+=len(chunk)
 if h.hexdigest()!=record['sha256'] or (record.get('bytes') and n!=record['bytes']):raise ValueError('Downloaded asset differs; partial retained')
 part.rename(path);return path

def unpack(record,path,root):
 import zstandard
 dest=root/record['unpacked_destination'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():
  if sha(dest)!=record['unpacked_sha256']:raise ValueError('Existing dataset differs')
  return
 part=dest.with_suffix('.part');h=hashlib.sha256();n=0
 with path.open('rb') as f,zstandard.ZstdDecompressor().stream_reader(f) as stream,part.open('xb') as out:
  if record['filename'].endswith('.tar.zst'):
   tar=tarfile.open(fileobj=stream,mode='r|');members=0
   for member in tar:
    if member.isfile() and member.name.endswith('.h5'):
     members+=1
     if members>1:raise ValueError('Multiple dataset members; explicit audit needed')
     src=tar.extractfile(member)
     for b in iter(lambda:src.read(8<<20),b''):out.write(b);h.update(b);n+=len(b)
   if members!=1:raise ValueError('Dataset member missing')
  else:
   for b in iter(lambda:stream.read(8<<20),b''):out.write(b);h.update(b);n+=len(b)
 if h.hexdigest()!=record['unpacked_sha256'] or n!=record['unpacked_bytes']:raise ValueError('Unpacked source identity differs')
 part.rename(dest)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--root',required=True);p.add_argument('--task',required=True);p.add_argument('--kind',choices=['weights','dataset','all'],default='weights');p.add_argument('--unpack',action='store_true');p.add_argument('--step2-authorized',action='store_true');a=p.parse_args()
 if not a.step2_authorized:raise SystemExit('Not permitted in step1; explicit step2 invocation required')
 root=Path(a.root).resolve();root.mkdir(parents=True,exist_ok=True);records=json.loads(Path(a.manifest).read_text())['assets'];done=[]
 for r in records:
  if r['task']!=a.task or (a.kind!='all' and r['kind']!=a.kind):continue
  path=download(r,root)
  if a.unpack and r['kind']=='dataset':unpack(r,path,root)
  done.append(dict(path=str(path),sha256=r['sha256']))
 (root/f'DOWNLOAD_{a.task}_{a.kind}.json').write_text(json.dumps(done,indent=2))
