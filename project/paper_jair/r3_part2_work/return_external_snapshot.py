"""One finite remote snapshot and SHA-verified return to the authorized disk.

No scheduling, stage launch, stop, deletion, or modification of experiment code.
Repeat the same label with --resume only to finish a interrupted transfer.
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
DEST=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/returns')
REMOTE='/workspace/d1/returns_r3'
SSH=['ssh','-o','ConnectTimeout=15','-p','10877','root@ssh9.vast.ai']

def run(args, **kwargs):
    subprocess.run(args,check=True,**kwargs)

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--base-label',required=True);p.add_argument('--stage',type=int,choices=(1,2,3))
    p.add_argument('--resume',action='store_true');a=p.parse_args()
    for label in (a.label,a.base_label):
        assert re.fullmatch(r'[A-Z0-9_]+',label),label
    assert Path('/Volumes/MyProj').is_mount(), 'External volume is not mounted'
    assert DEST.is_dir() and (DEST/a.base_label/'RETURN_MANIFEST.json').is_file()
    out=DEST/a.label
    env=dict(os.environ,COPYFILE_DISABLE='1')
    if not a.resume:
        assert not out.exists(),'Use --resume for an interrupted snapshot'
        run(SSH+['python3 /workspace/d1/step4/resume_01/snapshot_return.py --label '+a.label])
        # copyfile deliberately preserves bytes only: copying macOS xattrs onto
        # exFAT can rewrite a real, archived AppleDouble (._*) source file.
        base=DEST/a.base_label
        out.mkdir()
        # copytree also copies directory xattrs, even with copyfile selected.
        # Create directories without copystat and restore all file bytes only.
        for source in sorted(base.rglob('*')):
            target=out/source.relative_to(base)
            if source.is_dir():target.mkdir(exist_ok=True)
            elif source.is_file():
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(source,target)
    else:
        assert out.is_dir()
    run(['scp','-C','-o','ConnectTimeout=15','-P','10877',
         'root@ssh9.vast.ai:'+REMOTE+'/'+a.label+'.receipt.json',str(DEST)],env=env)
    run(['rsync','-rtz','--compress-level=9','--checksum','--stats',
         '-e','ssh -o ConnectTimeout=15 -p 10877',
         'root@ssh9.vast.ai:'+REMOTE+'/'+a.label+'/',str(out)+'/'],env=env)
    command=[sys.executable,str(HERE/'verify_snapshot_directory.py'),
             '--directory',str(DEST),'--label',a.label]
    if a.stage:command+=['--stage',str(a.stage)]
    run(command,env=env)
    print(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'label':a.label,'stage':a.stage,'status':'RETURNED_AND_VERIFIED',
       'destination':str(out)}),flush=True)

if __name__=='__main__':main()
