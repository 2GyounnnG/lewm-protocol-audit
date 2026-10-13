"""Generate corrected paper inputs only after final return and accepted stop."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,subprocess,sys
W=Path(__file__).resolve().parent
R=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/returns')
P=W.parent/'revision3_part2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,*args):
    command=[sys.executable,str(W/name),*[str(a) for a in args]]
    print('RUN',name,flush=True)
    subprocess.run(command,check=True,env=dict(os.environ,MPLCONFIGDIR='/private/tmp/r3_mpl',XDG_CACHE_HOME='/private/tmp/r3_xdg',PYTHONPYCACHEPREFIX='/private/tmp/r3_pycache'))
def main():
    final=R/'FORMAL_STAGE_3_LOCAL_RETURN.json'
    receipt=json.loads(final.read_text())
    assert receipt['status']=='VERIFIED_LOCAL_RETURN' and receipt['stage']==3 and receipt['mismatch_count']==0
    stop=json.loads((R.parent/'STOP_EVIDENCE/STOP_CAPTURE_RECEIPT.json').read_text())
    assert stop['stop_request_accepted'], 'Require accepted stop before manuscript CPU work'
    seal=W/'CORRECTED_RESULTS_SEAL.json'
    if not seal.exists():run('seal_corrected_results.py','--return-receipt',final,'--output',seal)
    assert json.loads(seal.read_text())['source_local_return_sha256']==sha(final)
    analysis=W/'analysis_final';assets=W/'paper_assets_final_v2';macros=W/'macro_final'
    if not (analysis/'ANALYSIS_MANIFEST.json').exists():
        run('analyze_corrected_reacher.py','--formal-root',R/'STAGE3_VERIFIED/experiment/formal_verified','--corrected-seal',seal,'--output',analysis)
    am=json.loads((analysis/'ANALYSIS_MANIFEST.json').read_text())
    assert am['status']=='COMPLETE' and am['corrected_seal_sha256']==sha(seal)
    if not (assets/'PAPER_ASSETS_MANIFEST.json').exists():run('update_paper_corrected.py','--analysis',analysis,'--output',assets)
    assert json.loads((assets/'PAPER_ASSETS_MANIFEST.json').read_text())['status']=='COMPLETE'
    if not (macros/'CORRECTED_MACRO_AUDIT.json').exists():run('generate_corrected_macros.py','--analysis',analysis,'--output',macros)
    for name in ('tables','figures','a3_results'):
        for source in (assets/name).rglob('*'):
            if source.is_file():
                target=P/name/source.relative_to(assets/name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    shutil.copyfile(macros/'revision3_corrected_numbers.tex',P/'a3_results/revision3_corrected_numbers.tex')
    run('generate_narrative.py','--analysis',analysis,'--assets',assets,'--output',P/'a3_results/revision3_corrected_narrative.tex')
    run('generate_narrative.py','--runtime-only','--runtime-json',R/'STAGE3_VERIFIED/experiment/runtime_checks_final.json','--launch-json',R/'FORMAL_LAUNCH_RECEIPT.json','--output',P/'a3_results/revision3_runtime_narrative.tex')
    result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'NUMERICAL_ASSETS_INTEGRATED_PENDING_PROSE_AND_PDF_QA','seal_sha256':sha(seal),'analysis_manifest_sha256':sha(analysis/'ANALYSIS_MANIFEST.json'),'assets_manifest_sha256':sha(assets/'PAPER_ASSETS_MANIFEST.json'),'manuscript':str(P)}
    (W/'CPU_PIPELINE_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
