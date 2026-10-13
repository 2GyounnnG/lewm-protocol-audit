"""Create/recover a new-version draft of 23350373 and upload one bundle; NEVER publish."""
import os,json,hashlib,argparse
from pathlib import Path
import requests
W=Path(__file__).resolve().parent;p=argparse.ArgumentParser();p.add_argument('bundle',type=Path);a=p.parse_args()
token=os.environ.get('ZENODO_TOKEN');assert token,'ZENODO_TOKEN is unavailable; no API changes made'
s=requests.Session();s.headers['Authorization']='Bearer '+token
receipt=W/'ZENODO_NEW_VERSION_RECEIPT.json'
if receipt.exists(): d=s.get(json.load(open(receipt))['draft_url'],timeout=60);d.raise_for_status();draft=d.json()
else:
 r=s.post('https://zenodo.org/api/deposit/depositions/23350373/actions/newversion',timeout=60);r.raise_for_status();x=r.json();url=x['links']['latest_draft'];receipt.write_text(json.dumps({'draft_url':url,'state':'CREATED_NOT_PUBLISHED'},indent=2));r=s.get(url,timeout=60);r.raise_for_status();draft=r.json()
assert not draft.get('submitted',False),'Draft must not be published'
# Existing inherited files are retained. This adds the revision supplement only.
url=draft['links']['bucket']+'/'+a.bundle.name
with a.bundle.open('rb') as f:r=s.put(url,data=f,timeout=1800)
r.raise_for_status();uploaded=r.json();md5=hashlib.md5(a.bundle.read_bytes()).hexdigest();assert uploaded['checksum']=='md5:'+md5
receipt.write_text(json.dumps({'draft_url':draft['links'].get('self'),'html':draft['links'].get('html'),'id':draft['id'],'reserved_doi':draft.get('metadata',{}).get('prereserve_doi'),'uploaded':uploaded,'sha256':hashlib.sha256(a.bundle.read_bytes()).hexdigest(),'state':'UPLOADED_NOT_PUBLISHED'},indent=2))
print('Draft uploaded; NOT published',draft['id'])
