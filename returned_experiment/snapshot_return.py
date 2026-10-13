"""Create an immutable, hashed return snapshot outside the experiment tree."""
import argparse, datetime, hashlib, json, shutil, tarfile
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--root',default='/workspace/d1/step4/resume_03_reacher')
    a=p.parse_args();w=Path(a.root);base=Path('/workspace/d1/returns_r3')
    base.mkdir(exist_ok=True);out=base/a.label;out.mkdir()
    manifest={}
    sources=[(w,'experiment'),(Path('/workspace/d1/logs'),'external_logs')]
    for src,prefix in sources:
        for f in sorted(src.rglob('*')):
            if not f.is_file() or f.is_symlink() or '__pycache__' in f.parts:continue
            # Asset datasets and weights live outside these trees; no secrets.
            rel=Path(prefix)/f.relative_to(src);dst=out/rel
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
            manifest[str(rel)]=sha(dst)
    tmp=Path('/tmp')
    # Include only task-named helper source/logs, not unrelated temporary data.
    for pattern in ('*reacher*.py','*r3*.py','*reacher*.sh','*r3*.sh'):
        for f in sorted(tmp.glob(pattern)):
            if not f.is_file() or f.is_symlink():continue
            rel=Path('tmp_scripts')/f.name;dst=out/rel
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
            manifest[str(rel)]=sha(dst)
    record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'label':a.label,'source_root':str(w),'files':manifest,'file_count':len(manifest)}
    (out/'RETURN_MANIFEST.json').write_text(json.dumps(record,indent=2)+'\n')
    archive=base/(a.label+'.tar.gz')
    with tarfile.open(archive,'w:gz') as tf:tf.add(out,arcname=a.label)
    result={'path':str(archive),'sha256':sha(archive),'file_count':len(manifest),
            'manifest_sha256':sha(out/'RETURN_MANIFEST.json'),'bytes':archive.stat().st_size}
    (base/(a.label+'.receipt.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
