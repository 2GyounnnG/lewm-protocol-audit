"""Seal corrected results from a complete local SHA return, before statistics."""
import argparse,datetime,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--return-receipt',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    rec=json.loads(a.return_receipt.read_text());assert rec['status']=='VERIFIED_LOCAL_RETURN' and rec['stage']==3 and rec['mismatch_count']==0
    w=Path(rec['local_path'])/'experiment';counts=0
    for i in (1,2,3):
        f=w/f'FORMAL_STAGE_{i}_STATUS.json';assert sha(f)==rec['manifest_sha256'][f.name]
        d=json.loads(f.read_text());assert d['records_complete']==d['records_expected'] and d['conditions_exited_zero']==d['conditions_expected']
        counts+=d['records_complete']
    assert counts==2700
    prefix='formal_verified/'
    files={k[len(prefix):]:v for k,v in rec['manifest_sha256'].items() if k.startswith(prefix)}
    assert len(files)==9300,(len(files),'Expected 4*300*4 LeWM files plus 5*300*3 method files')
    d={'status':'SEALED_VERIFIED_CORRECTED_RESULTS','sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'root':str(w/'formal_verified'),'expected_trajectories':2700,'conditions':9,'cases_per_condition':100,'streams':'ABC',
       'files':files,'source_local_return_sha256':sha(a.return_receipt),
       'correction_registration_sha256':rec['manifest_sha256']['REVISION_3_REACHER_CORRECTION_REGISTRATION.json'],
       'technical_gate_sha256':rec['manifest_sha256']['TECH_GATE_FINAL_T1_T4.json'],
       'excluded_records':'All old formal/ and all TECH directories excluded; only formal_verified/ is admitted.'}
    with a.output.open('x') as f:f.write(json.dumps(d,indent=2)+'\n')
    print(json.dumps({'seal':str(a.output),'sha256':sha(a.output),'files':len(files),'trajectories':counts}))
if __name__=='__main__':main()
