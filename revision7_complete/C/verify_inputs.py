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
# Validate identity-to-row mapping before any model execution.
import h5py,numpy as np
with h5py.File(W/'assets/data/reacher.h5','r') as f:
 lengths=np.asarray(f['ep_len']);offsets=np.asarray(f['ep_offset'])
 assert len(lengths)==10000 and np.all(lengths==201) and np.array_equal(offsets,np.arange(10000)*201)
 assert len(f['pixels'])==2010000
 for root in ['protocol_main128','protocol_seed42','protocol_seed43','protocol_seed44']:
  p=json.load(open(W/root/'protocols/main.json'));q=p['studies']['reacher'];episodes={r['episode'] for r in q['confirm']}
  assert not episodes.intersection(p['bank_train_episodes']['reacher'])
  for row in q['confirm']:
   assert row['global_start']==int(offsets[row['episode']])+row['local_start']
   assert row['global_goal']-row['global_start']==q['horizon'] and row['global_goal']<offsets[row['episode']]+lengths[row['episode']]
print('Episode mapping and bank exclusion PASS')
