"""Verify an immutable remote archive and every returned file on this computer."""
import argparse,datetime,hashlib,json,tarfile
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--label',required=True);p.add_argument('--stage',type=int)
    a=p.parse_args();root=a.directory;archive=root/(a.label+'.tar.gz')
    external=json.loads((root/(a.label+'.receipt.json')).read_text())
    assert sha(archive)==external['sha256'],'archive SHA mismatch'
    extracted=root/a.label;assert not extracted.exists()
    with tarfile.open(archive) as tf:
        for member in tf.getmembers():
            rel=Path(member.name)
            assert not rel.is_absolute() and '..' not in rel.parts
            assert rel.parts[0]==a.label and not member.issym() and not member.islnk()
        tf.extractall(root)
    assert sha(extracted/'RETURN_MANIFEST.json')==external['manifest_sha256']
    manifest=json.loads((extracted/'RETURN_MANIFEST.json').read_text())
    mismatches=[rel for rel,wanted in manifest['files'].items() if sha(extracted/rel)!=wanted]
    assert not mismatches,mismatches
    mapping={k[len('experiment/'):]:v for k,v in manifest['files'].items() if k.startswith('experiment/')}
    receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status':'VERIFIED_LOCAL_RETURN','label':a.label,'verified_files':len(manifest['files']),
        'mismatch_count':0,'manifest_sha256':mapping,'archive_sha256':external['sha256'],
        'return_manifest_sha256':external['manifest_sha256'],'local_path':str(extracted.resolve())}
    name='PREFORMAL_LOCAL_RETURN.json'
    if a.stage:
        statusname=f'FORMAL_STAGE_{a.stage}_STATUS.json'
        status=json.loads((extracted/'experiment'/statusname).read_text())
        assert status['records_complete']==status['records_expected']
        assert all(mapping[k]==v for k,v in status['artifact_sha256'].items())
        receipt.update(stage=a.stage,stage_status_sha256=sha(extracted/'experiment'/statusname))
        name=f'FORMAL_STAGE_{a.stage}_LOCAL_RETURN.json'
    with (root/name).open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'verified_files':receipt['verified_files'],'mismatch_count':0,'receipt':str(root/name),'receipt_sha256':sha(root/name)}))
if __name__=='__main__':main()
