"""Extract only reacher.h5 from verified tar.zst; no archive paths are trusted."""
from pathlib import Path
import hashlib,json,subprocess,tarfile
W=Path(__file__).resolve().parent;r=next(x for x in json.load(open(W/'DOWNLOAD_MANIFEST.json'))['assets'] if x['kind']=='dataset')
archive=W/'assets'/r['destination'];dest=W/'assets'/r['unpacked_destination']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8388608):h.update(b)
 return h.hexdigest()
assert sha(archive)==r['sha256']
if dest.exists():assert sha(dest)==r['unpacked_sha256'];print('Existing expanded data verified');raise SystemExit(0)
dest.parent.mkdir(parents=True,exist_ok=True);part=dest.with_name(dest.name+'.partial');assert not part.exists(),'Partial expansion exists: retain and inspect before retry'
proc=subprocess.Popen(['zstd','-dc',str(archive)],stdout=subprocess.PIPE);found=0;h=hashlib.sha256();n=0
with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
 for member in tar:
  if not member.isfile() or Path(member.name).name!='reacher.h5':continue
  found+=1;assert found==1 and member.size==r['unpacked_bytes']
  with tar.extractfile(member) as src,part.open('xb') as out:
   while b:=src.read(8388608):out.write(b);h.update(b);n+=len(b)
assert proc.wait()==0 and found==1 and n==r['unpacked_bytes'] and h.hexdigest()==r['unpacked_sha256']
part.rename(dest);print('Expanded HDF5 SHA PASS')
