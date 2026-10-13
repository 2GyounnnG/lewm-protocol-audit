import json,hashlib,datetime
from pathlib import Path
R=Path("/workspace/d1");W=R/"step4/resume_03_reacher"
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
all_specs=json.loads((W/"CONDITION_SPECS.json").read_text())
conds={k:{**v,"status":"PENDING_TECH_GATES"} for k,v in all_specs.items() if v["task"]=="reacher"}
assets={p.name:sha(p) for p in [W/"asset_bindings/AP_NATIVE_ASSETS.json",W/"asset_bindings/M01_reacher.json",W/"asset_bindings/M03_reacher.json",W/"asset_bindings/M07_3072_reacher.json",W/"asset_bindings/M07_4096_reacher.json",W/"asset_bindings/M07_6144_reacher.json"]}
code={}
for p in [W/"code/step4_worker_r3.py",W/"code/official_formal_v3_reacher.py",W/"code/method_formal_v2_reacher.py",W/"code/formal_guard.py",W/"code/native_reset.py",W/"code/factor_bindings.py",W/"code/adapters/common.py",W/"code/adapters/harness.py",W/"code/adapters/model_runtime.py",W/"code/adapters/original_mode.py",W/"code/adapters/swm_api_compat.py",W/"code/adapters/swm_runtime.py",W/"REVISION_3_REACHER_PATCH.py",W/"REVISION_3_REACHER_WORKER_PATCH.py",W/"REVISION_3_REACHER_METHOD_PATCH.py",W/"runtime_checks.py",W/"runtime_checks.json",W/"CORRECTION_REGISTRATION_R3_REACHER.json",W/"ENV_REVISIONS.jsonl"]:
 code[str(p.relative_to(W))]=sha(p)
receipt={"status":"PENDING_TECH_GATES","created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"projected_gpu_hours_with_15pct_reserve":30.0,"heldout_seal_sha256":sha(W/"cases/HELDOUT_SEAL.json"),"condition_specs":conds,"asset_bindings_sha256":assets,"code_sha256":code,"runtime_checks_sha256":sha(W/"runtime_checks.json"),"correction_registration_sha256":sha(W/"CORRECTION_REGISTRATION_R3_REACHER.json"),"formal_scope":{"task":"reacher","cases":100,"streams":"ABC","budget_raw":50,"expected_total_trajectories":2700},"preregistration_unchanged":True}
(W/"FORMAL_LAUNCH_RECEIPT_DRAFT.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"draft_sha256":sha(W/"FORMAL_LAUNCH_RECEIPT_DRAFT.json"),"conditions":list(conds),"assets":assets,"code_count":len(code)},indent=2))
