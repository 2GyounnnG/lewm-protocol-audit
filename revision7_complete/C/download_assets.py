"""Explicitly invoked, resumable input download with pinned SHA; never starts a model."""
import json,hashlib,subprocess,argparse
from pathlib import Path
W=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);a=p.parse_args()
def sha(f):
 h=hashlib.sha256()
 with f.open('rb') as stream:
  while b:=stream.read(8*1024*1024):h.update(b)
 return h.hexdigest()
for row in json.load(open(W/'DOWNLOAD_MANIFEST.json'))['assets']:
 out=a.destination/row['destination'];out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():assert sha(out)==row['sha256'],f'Existing file differs: {out}';continue
 part=out.with_name(out.name+'.partial')
 subprocess.run(['curl','--fail','--location','--retry','4','--continue-at','-','--output',str(part),row['url']],check=True)
 assert part.stat().st_size==row['bytes'] and sha(part)==row['sha256'],f'SHA/size failed: {part}'
 part.rename(out);print('VERIFIED',out,flush=True)
