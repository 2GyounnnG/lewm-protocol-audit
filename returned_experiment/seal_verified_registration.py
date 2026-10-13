"""Seal measured gates and the corrected scope; never launches a GPU job."""
import datetime, hashlib, json, statistics
from pathlib import Path
W=Path('/workspace/d1/step4/resume_03_reacher')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((W/n).read_text())
def write(n,d):
    p=W/n
    with p.open('x') as f:f.write(json.dumps(d,indent=2,allow_nan=False)+'\n')
def main():
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
    gate=read('TECH_GATE_FINAL_T1_T4.json');runtime=read('runtime_checks_final.json')
    assert gate['status']=='PASS' and gate['full_registered_group_coverage']
    assert all(g['status']=='PASS' and g['case_streams_expected']==108 for g in gate['gates'].values())
    assert runtime['status']=='PASS' and read('FINAL_BIND_CPU_SMOKE.json')['status']=='PASS'
    pre=read('CORRECTION_RECORDING_REVISION_PRETECH.json')
    for rel,h in pre['code_sha256'].items():assert sha(W/rel)==h,rel
    procs=read('TECH_VERIFIED_PROCESS_STATUS.json');assert len(procs['rows'])==9
    projections=[]
    for row in procs['rows']:
        assert row['exit_code']==0
        vals=[]
        for p in (W/'tech_verified'/row['group']).rglob('*.json'):
            d=json.loads(p.read_text())
            if 'whole_case_wall_seconds' in d:
                assert d['status']=='COMPLETE' and d['executed_raw_steps']==50
                vals.append(d['whole_case_wall_seconds'])
        assert len(vals)==12
        # One dataset verification/model startup is already in TECH job wall.
        # Use the second-largest case time to exclude that one-time startup,
        # then charge it for all additional 288 formal trajectories.
        steady=max(sorted(vals)[:-1]);seconds=row['wall_seconds']+288*steady
        projections.append({'group':row['group'],'tech_job_seconds':row['wall_seconds'],
            'case_seconds':vals,'steady_upper_seconds':steady,
            'projected_300_seconds':seconds,'projected_300_with_15pct_seconds':seconds*1.15})
    gpu_h=sum(r['projected_300_with_15pct_seconds'] for r in projections)/3600
    assert gpu_h<=120
    throughput={'utc':utc,'status':'PASS','rule':'TECH job wall plus 288 times second-largest complete case wall; 15% reserve; startup counted once per job',
        'projected_gpu_hours_with_15pct_reserve':gpu_h,'rows':projections}
    write('THROUGHPUT_FINAL.json',throughput)
    old=read('CORRECTION_REGISTRATION_R3_REACHER_FINAL.json')
    code={str(p.relative_to(W)):sha(p) for p in (W/'code').rglob('*') if p.is_file() and not p.is_symlink() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts}
    for n in ['REVISION_3_REACHER_RECORDING_PATCH.py','run_verified_formal.py','snapshot_return.py','seal_verified_registration.py']:
        code[n]=sha(W/n)
    code.update(pre['code_sha256'])
    evidence_names=['TECH_GATE_FINAL_T1_T4.json','runtime_checks_final.json','FINAL_BIND_CPU_SMOKE.json','CORRECTION_RECORDING_REVISION_PRETECH.json','THROUGHPUT_FINAL.json','PREMATURE_FORMAL_EXCLUSION.json']
    registration={'status':'SEALED_AFTER_NUMERICAL_GATES_BEFORE_VALID_FORMAL',
        'registration_utc':utc,'prior_invalid_formal_excluded':True,
        'correction_reason':old['correction_reason'],'baseline':old['baseline'],
        'environment':old['environment'],'assets':old['assets'],'formal_scope':old['formal_scope'],
        'code_sha256':code,'final_code_sha256':code,'evidence_sha256':{n:sha(W/n) for n in evidence_names},
        'technical_gates':gate['gates'],'success_semantics':pre['label_semantics'],
        'recording_schema':'reacher_correction_record_v2',
        'recording_fields':['tracker.events','step_any_labels','step_end_labels','physics.time','qpos','qvel','target_qpos','reset_count','internal_reset_events'],
        'termination_correction':'Disable native success termination; preserve exact strict qpos predicate and both microsteps. T1 proves original action prefix unchanged.',
        'logging_revision':'Real reset observation installed before native reset; both label streams and all microstep states; no planner/action changes.',
        'preregistration_unchanged':True,'formal_output_directory':'formal_verified',
        'no_training':True,'no_submission':True,'no_preprint':True}
    write('REVISION_3_REACHER_CORRECTION_REGISTRATION.json',registration)
    seal={'utc':utc,'status':'SEALED','files':{n:sha(W/n) for n in evidence_names+['REVISION_3_REACHER_CORRECTION_REGISTRATION.json']},'code_sha256':code}
    write('CORRECTION_SEAL_FINAL.json',seal)
    print(json.dumps({'registration_sha256':sha(W/'REVISION_3_REACHER_CORRECTION_REGISTRATION.json'),'gpu_hours':gpu_h,'gates':gate['gates']},indent=2))
if __name__=='__main__':main()
