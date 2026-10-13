"""Build the concrete D1 protocol timeline used in Appendix A.
All timestamps and hashes are read from sealed local records; no experiment is run.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "d1_execution"
OUT_JSON = ROOT / "a3_results" / "REV2_TIMELINE_AUDIT.json"
OUT_TEX = ROOT / "tables" / "table_timeline_revision.tex"

def sha(p: Path):
    h=hashlib.sha256();
    with p.open('rb') as f:
      for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def j(p): return json.loads(p.read_text())

def main():
    pre = BASE/'prereg'
    v1r=j(pre/'PREREG_D1_V1_RECEIPT.json'); v11r=j(pre/'PREREG_D1_V1_1_RECEIPT.json'); v12r=j(pre/'PREREG_D1_V1_2_RECEIPT.json'); v2r=j(pre/'PREREG_D1_V2_FOLLOWUP_RECEIPT.json')
    scope=BASE/'step4/AUTHOR_SCOPE_REVISION.json'; clar=BASE/'step4/HELDOUT_SCOPE_CLARIFICATION.json'; hseal=BASE/'step4/resume_01/cases/HELDOUT_SEAL.json'; launch=BASE/'step4/resume_01/FORMAL_LAUNCH_RECEIPT.json'; final=BASE/'step4/resume_01/SEAL.json'
    events=[
      {'event':'V1 preregistration','utc':v1r['registered_utc'],'document':'d1_execution/prereg/PREREG_D1_V1.md','sha256':v1r['files']['PREREG_D1_V1.md']},
      {'event':'V1.1 preregistration','utc':v11r['registered_utc'],'document':'d1_execution/prereg/PREREG_D1_V1_1.md','sha256':v11r['files']['PREREG_D1_V1_1.md']},
      {'event':'V1.2 preregistration','utc':v12r['registered_utc'],'document':'d1_execution/prereg/PREREG_D1_V1_2.md','sha256':v12r['files']['PREREG_D1_V1_2.md']},
      {'event':'V2 follow-up preregistration','utc':v2r['registered_utc'],'document':'d1_execution/prereg/PREREG_D1_V2_FOLLOWUP.md','sha256':v2r['sha256']},
      {'event':'Author scope revision before held-out results','utc':j(scope)['utc'],'document':'d1_execution/step4/AUTHOR_SCOPE_REVISION.json','sha256':sha(scope)},
      {'event':'Held-out scope clarification','utc':j(clar)['utc'],'document':'d1_execution/step4/HELDOUT_SCOPE_CLARIFICATION.json','sha256':sha(clar)},
      {'event':'Held-out case manifest sealed','utc':j(hseal)['utc'],'document':'d1_execution/step4/resume_01/cases/HELDOUT_SEAL.json','sha256':sha(hseal),'manifest_sha256':j(hseal)['files']['HELDOUT_CASES_V2.json']},
      {'event':'Formal run launch receipt','utc':j(launch)['utc'],'document':'d1_execution/step4/resume_01/FORMAL_LAUNCH_RECEIPT.json','sha256':sha(launch)},
      {'event':'Formal run / final return','utc':'2026-10-12T18:59:51.968689Z--2026-10-12T20:25:46.842875Z','document':'d1_execution/step4/resume_01/SEAL.json','sha256':sha(final),'return_manifest_sha256':j(final)['return_verification']['final_results_ack']['manifest_sha256'],'return_archive_sha256':j(final)['return_verification']['final_results_ack']['archive_sha256']},
    ]
    deviations=[
      'PushT exact-start override withdrawn; all PushT unified-protocol conditions rerun with the native reset.',
      'The 21 partial PushT conditions produced under the override were archived and excluded; the earlier 572 records were excluded from formal analyses.',
      'The common-protocol A--C comparison is a post hoc stream-matched analysis.',
      'Before held-out data existed, the replanning mechanism grid and the extra mechanism gate were removed, and M03/M07 three-frame conditions were removed; D4 CEM-10 versus CEM-30 was added descriptively.',
      'Gate-1 fidelity evidence was reused only for the 14 unchanged adapter files; the unified environment was rebuilt.',
    ]
    payload={'events':events,'deviations':deviations,'sources':{'step4_seal_sha256':sha(final),'launch_receipt_sha256':sha(launch),'heldout_seal_sha256':sha(hseal)}}
    OUT_JSON.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Keep the table legible: use first 12 hash characters; details in caption and audit JSON.
    rows=[]
    for e in events:
      utc=e['utc'].replace('T',' ').replace('+00:00','Z')
      if '--' in utc: utc=utc.replace('--',' to ')
      rows.append(f"{e['event']} & {utc} & {e['sha256'][:12]} \\\\")
    tex=['\\begin{table*}[t]','\\centering','\\caption{Reproducible protocol timeline. Times are UTC and hashes are the first 12 characters of the SHA--256 for the listed record. The complete hashes and all deviations are in the machine-readable audit file.}','\\label{tab:timeline-revision}','\\scriptsize','\\begin{tabular}{p{4.0cm}p{7.3cm}l}','\\toprule','Event & UTC time or interval & SHA--256 \\\\','\\midrule']+rows+['\\bottomrule','\\end{tabular}','\\end{table*}']
    OUT_TEX.write_text('\n'.join(tex)+'\n',encoding='utf-8')
    print(f'wrote {OUT_JSON} and {OUT_TEX}')
if __name__=='__main__': main()
