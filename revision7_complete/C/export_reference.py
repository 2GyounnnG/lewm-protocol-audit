from pathlib import Path
import hashlib,json
W=Path(__file__).resolve().parent;R=W.parents[3];index=R/'d1_execution/step2/resume_03/FINAL_ANALYSIS_INPUT_INDEX.json';inputs=json.load(open(index));rows=[];evidence=[]
for key,v in inputs.items():
 if '/formal/D1_082_000_128/traces/reacher/' not in key or not key.endswith('_clean_gaussian_observed.json'):continue
 p=Path(v['local_path']);b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==v['sha256'],p
 x=json.loads(b);c=x['compact'];i=c['identity'];assert c['completed'] and c['budget']==300 and c['horizon']==150
 rows.append(dict(record_id=i['record_id'],episode=i['episode'],global_start=i['global_start'],global_goal=i['global_goal'],success=c['success'],first_hit_step=0 if c['prelude']['success'] else c['primitive_steps'] if c['success'] else None,actions=x['actions']))
 evidence.append({'source':key,'sha256':v['sha256']})
assert len(rows)==128,len(rows)
rows.sort(key=lambda x:x['record_id']);out=W/'reference_step2_original128.jsonl';out.write_text(''.join(json.dumps(r)+'\n' for r in rows))
assert sum(r['success'] for r in rows)==125
old=R/'d1_execution/step1/repos/M03/code/ap/anchored_planning';new=W/'ap_source/code/ap/anchored_planning'
code={p.name:hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256((old/p.name).read_bytes()).hexdigest() for p in new.glob('*.py')}
(W/'REFERENCE_RECEIPT.json').write_text(json.dumps({'source':'Step 2 original-protocol D1_082_000_128, not Step 4 HELDOUT','n':len(rows),'successes':125,'reference_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'code_identity_with_step1_native_AP':code,'inputs':evidence},indent=2))
print('128 SHA-verified records; successes125; unchanged AP modules',sum(code.values()),'/',len(code))
