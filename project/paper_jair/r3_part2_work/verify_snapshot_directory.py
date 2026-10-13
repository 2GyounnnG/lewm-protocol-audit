"""Verify all files in a returned immutable snapshot after incremental rsync."""
import argparse,datetime,hashlib,json
from pathlib import Path
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--label',required=True);p.add_argument('--stage',type=int);a=p.parse_args()
    snap=a.directory/a.label
    remote=json.loads((a.directory/(a.label+'.receipt.json')).read_text())
    assert sha(snap/'RETURN_MANIFEST.json')==remote['manifest_sha256']
    manifest=json.loads((snap/'RETURN_MANIFEST.json').read_text())
    mismatches=[k for k,v in manifest['files'].items() if not (snap/k).is_file() or sha(snap/k)!=v]
    assert not mismatches,mismatches
    mapping={k[len('experiment/'):]:v for k,v in manifest['files'].items() if k.startswith('experiment/')}
    stage_status_sha=None
    if a.stage:
        name=f'FORMAL_STAGE_{a.stage}_STATUS.json';status=json.loads((snap/'experiment'/name).read_text())
        assert status['records_complete']==status['records_expected']
        assert status['status']=='PROCESSES_COMPLETE_RECORDS_PRESENT_PENDING_LOCAL_RETURN'
        assert all(mapping[k]==v for k,v in status['artifact_sha256'].items())
        stage_status_sha=sha(snap/'experiment'/name)
    receipt={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'VERIFIED_LOCAL_RETURN',
       'stage':a.stage,'label':a.label,'verified_files':len(manifest['files']),'mismatch_count':0,
       'manifest_sha256':mapping,'stage_status_sha256':stage_status_sha,
       'return_manifest_sha256':remote['manifest_sha256'],'transfer':'rsync from immutable snapshot; complete per-file local SHA verification',
       'local_path':str(snap.resolve()),'remote_archive_sha256_metadata_only':remote['sha256']}
    out=a.directory/(f'FORMAL_STAGE_{a.stage}_LOCAL_RETURN.json' if a.stage else a.label+'_LOCAL_RETURN.json')
    with out.open('x') as f:f.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'status':receipt['status'],'files':len(manifest['files']),'mismatches':0,'receipt':str(out),'sha256':sha(out)}))
if __name__=='__main__':main()
