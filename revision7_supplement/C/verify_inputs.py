from pathlib import Path
import json,hashlib
W=Path(__file__).resolve().parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
for p,s in json.load(open(W/'INPUT_SHA256.json')).items():assert sha(W/p)==s,p
for a in json.load(open(W/'DOWNLOAD_MANIFEST.json'))['assets']:
 p=W/'assets'/a['destination'];assert p.is_file(),p
 assert sha(p)==a['sha256'],p
 if a['kind']=='dataset':
  q=W/'assets'/a['unpacked_destination'];assert sha(q)==a['unpacked_sha256'],q
print('SHA PASS')
