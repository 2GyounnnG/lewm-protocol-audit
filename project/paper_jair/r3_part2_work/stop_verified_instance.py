"""Run the authorized container stop once, capturing its evidence on MyProj."""
import argparse,datetime,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/returns')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--perform-stop',action='store_true',required=True);p.parse_args()
    assert Path('/Volumes/MyProj').is_mount()
    receipt=json.loads((BASE/'FORMAL_STAGE_3_LOCAL_RETURN.json').read_text())
    assert receipt['status']=='VERIFIED_LOCAL_RETURN' and receipt['stage']==3 and receipt['mismatch_count']==0
    out=BASE.parent/'STOP_EVIDENCE';out.mkdir()
    helper_sha=sha(HERE/'instance_control_v3.py')
    remote=("import pathlib,hashlib,os; p=pathlib.Path('/workspace/d1/step4/resume_01/instance_control_v3.py'); "
            +"assert hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(helper_sha)+"; "
            +"os.execv('/usr/bin/python3',['python3',str(p),'stop'])")
    command=['ssh','-o','ConnectTimeout=15','-p','10877','root@ssh9.vast.ai','python3 -']
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    records=[]
    with (out/'STOP_STREAM.log').open('x') as log:
        proc=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        proc.stdin.write(remote+'\n');proc.stdin.close()
        for line in proc.stdout:
            log.write(line);log.flush();print(line,end='',flush=True)
            try:d=json.loads(line)
            except ValueError:continue
            if 'preflight' in d:
                raw=json.dumps(d['preflight'],indent=2,allow_nan=False)+'\n'
                assert hashlib.sha256(raw.encode()).hexdigest()==d['preflight_sha256']
                (out/'INSTANCE_STOP_PREFLIGHT.json').write_text(raw)
            elif d.get('mode')=='stop' and str(d.get('instance_id'))=='55658358':
                records.append(d)
                (out/f'INSTANCE_STOP_RECEIPT_{len(records)}.json').write_text(json.dumps(d,indent=2)+'\n')
        rc=proc.wait()
    result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'request_started_utc':started,
            'instance_id':55658358,'ssh_exit_code':rc,'helper_sha256':helper_sha,
            'verified_final_return_sha256':sha(BASE/'FORMAL_STAGE_3_LOCAL_RETURN.json'),
            'received_stop_receipts':len(records),'stop_request_accepted':bool(records and records[-1].get('stop_request_accepted')),
            'actual_stop_confirmed':bool(records and records[-1].get('actual_stop_confirmed')),
            'destroy_requested':False,'files':{f.name:sha(f) for f in out.iterdir() if f.is_file()}}
    (out/'STOP_CAPTURE_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
