"""Prepare, do not run, the explicitly new AP cross-cohort check on LeWM appendix cases."""
import csv,json,copy,hashlib
from pathlib import Path
W=Path(__file__).resolve().parent
base=json.load(open(W/'protocol_main128/protocols/main.json'));summary=[]
for r in csv.DictReader(open(W/'cases/lewm_official_repro_source.csv')):
 if r['task']!='reacher':continue
 seed=int(r['seed']);eps=json.loads(r['episode_ids']);starts=json.loads(r['start_steps']);goals=json.loads(r['goal_steps']);assert len(eps)==len(starts)==len(goals)==50
 p=copy.deepcopy(base);rows=[]
 for i,(ep,s,g) in enumerate(zip(eps,starts,goals)):
  assert g-s==24 and 0<=s<g<201
  rows.append({'record_id':f'new-ap-crosscohort-reacher-s{seed}-{i:03d}','episode':ep,'global_start':201*ep+s,'global_goal':201*ep+g,'local_start':s,'horizon':24,'environment_seed':seed,'task':'reacher','cohort_origin':'LeWM appendix identities; new AP evaluation, not released AP main','sample_seed':seed})
 p['studies']['reacher']={'horizon':24,'budget':50,'confirm':rows};p['prefix_sources']=[{'task':'reacher','record_id':x['record_id'],'condition':'clean','source':None} for x in rows]
 excluded=set(eps);old=p['bank_train_episodes']['reacher'];p['bank_train_episodes']['reacher']=[e for e in old if e not in excluded]
 p['revision7_new_check']={'pending_author_approval':True,'offset':24,'budget':50,'environment_seed':seed,'CEM_seed_rule':'unchanged original query_seed(reacher, ordinal)','bank_exclusion_new_episodes':sorted(excluded.intersection(old))}
 d=W/f'protocol_seed{seed}_DRAFT/protocols';d.mkdir(parents=True,exist_ok=True);(d/'main.json').write_text(json.dumps(p,indent=2));(d/'scalers.json').write_bytes((W/'protocol_main128/protocols/scalers.json').read_bytes())
 summary.append({'seed':seed,'n':50,'invalid_if_offset150':sum(s+150>=201 for s in starts),'bank_episodes_removed':len(excluded.intersection(old)),'sha256':hashlib.sha256((d/'main.json').read_bytes()).hexdigest()})
(W/'THREE_SEED_DRAFT_RECEIPT.json').write_text(json.dumps({'status':'DRAFT_NOT_AUTHORIZED','checks':summary,'assumption':'Reacher 10000 episodes each 201 rows; runtime must verify ep_offset and ep_len before use'},indent=2));print(summary)
