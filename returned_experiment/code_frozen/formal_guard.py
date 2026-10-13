"""Step4 V2 launch receipt authorization; immutable hashes and budget cap."""
import json
from pathlib import Path
from adapters.common import sha
W=Path('/workspace/d1/step4/resume_01')
def authorize(condition_id,runner,receipt):
 p=Path(receipt);assert p==W/'FORMAL_LAUNCH_RECEIPT.json'
 d=json.loads(p.read_text());assert d['status']=='AUTHORIZED_AFTER_GATES_AND_LOCAL_RETURN'
 assert d['projected_gpu_hours_with_15pct_reserve']<=120 and condition_id in d['condition_specs']
 assert d['condition_specs'][condition_id]['status']=='PASS'
 assert sha(W/'cases/HELDOUT_SEAL.json')==d['heldout_seal_sha256']
 case_seal=json.loads((W/'cases/HELDOUT_SEAL.json').read_text())
 for name,expected in case_seal['files'].items():assert sha(W/'cases'/name)==expected,name
 for name,expected in d['asset_bindings_sha256'].items():assert sha(W/name)==expected,name
 for name,expected in d['code_sha256'].items():assert sha(W/name)==expected,name
 assert str(Path(runner).relative_to(W)) in d['code_sha256']
 return d
