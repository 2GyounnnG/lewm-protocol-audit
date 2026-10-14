"""Paired renderer-only contrast, frozen first50 main identities; saved records only."""
from pathlib import Path
import argparse,json,hashlib,importlib.util,datetime
import numpy as np
W=Path(__file__).resolve().parent;ROOT=W.parents[3];C=W.parent/'C'
p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);a=p.parse_args();assert json.load(open(a.snapshot/'RETURN_VERIFIED.json'))['mismatches']==0
base=a.snapshot/'files';protocol=json.load(open(C/'protocol_main128/protocols/main.json'))['studies']['reacher']['confirm'][:50];ids=[r['record_id'] for r in protocol]
statsfile=ROOT/'d1_execution/step1/upload/code/tools/statistics_d1.py';spec=importlib.util.spec_from_file_location('sealed_stats',statsfile);stats=importlib.util.module_from_spec(spec);spec.loader.exec_module(stats)
ref={r['record_id']:r for r in (json.loads(l) for l in (C/'reference_step2_original128.jsonl').read_text().splitlines())}
rows=[];inputs={}
for case in protocol:
 name=case['record_id'];tr=[]
 for prefix in ['outputs/main128','outputs/diagnostics/egl50']:
  f=base/prefix/'traces/reacher'/(name+'_clean_gaussian_observed.json');inputs[str(f.relative_to(base))]=hashlib.sha256(f.read_bytes()).hexdigest();r=json.load(open(f));assert r['compact']['identity']==case and r['compact']['budget']==300 and r['compact']['horizon']==150 and r['compact']['completed'];tr.append(r)
 x,y=tr;assert x['compact']['optimizer_seed']==y['compact']['optimizer_seed']
 xa=np.asarray(x['actions']);ya=np.asarray(y['actions']);old=np.asarray(ref[name]['actions']);n=min(25,len(xa),len(ya));m=min(25,len(ya),len(old));dx=np.max(np.abs(xa[:n]-ya[:n]),axis=1) if n else np.array([]);do=np.max(np.abs(ya[:m]-old[:m]),axis=1) if m else np.array([])
 rows.append({'case':name,'osmesa':x['compact']['success'],'egl':y['compact']['success'],'old_study':ref[name]['success'],'osmesa_first_hit':len(xa) if x['compact']['success'] else None,'egl_first_hit':len(ya) if y['compact']['success'] else None,'old_first_hit':ref[name]['first_hit_step'],'osmesa_vs_egl_first25_max_abs':float(dx.max()) if n else None,'osmesa_vs_egl_first_divergence':int(np.flatnonzero(dx)[0])+1 if np.any(dx) else None,'egl_vs_old_first25_max_abs':float(do.max()) if m else None,'egl_vs_old_all_actions_equal':bool(np.array_equal(ya,old))})
x=np.array([r['osmesa'] for r in rows],float);y=np.array([r['egl'] for r in rows],float);old=np.array([r['old_study'] for r in rows],float)
images=[]
for case in protocol[:3]:
 name=case['record_id'];d=[];rec=[]
 for backend in ['osmesa','egl']:
  p=base/'outputs/diagnostics/render_probe'/backend;d.append(np.load(p/(name+'.npy'),allow_pickle=False));rec.append(next(r for r in json.load(open(p/'RECEIPT.json')) if r['case']==name))
 physical=all(rec[0][k]==rec[1][k] for k in ['qpos','qvel','physics_time','goal','observation']);assert physical
 diff=np.abs(d[0].astype(float)-d[1].astype(float));images.append({'case':name,'physical_state_exact_equal':physical,'render_does_not_change_state':all(r['render_does_not_change_state'] for r in rec),'image_shape':list(d[0].shape),'different_pixels_pct':float(100*np.any(d[0]!=d[1],axis=-1).mean()),'mean_absolute_rgb_byte_difference':float(diff.mean()),'max_absolute_rgb_byte_difference':float(diff.max()),'osmesa_sha256':rec[0]['image_sha256'],'egl_sha256':rec[1]['image_sha256']})
r={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'n':50,'case_selection':'first50 frozen main128 ordinals, not outcome-selected','only_factor_changed':'OSMesa vs EGL renderer (MUJOCO_GL/PYOPENGL_PLATFORM)','osmesa_successes':int(x.sum()),'egl_successes':int(y.sum()),'old_study_successes':int(old.sum()),'egl_minus_osmesa':stats.paired(y,x),'egl_rate':stats.paired(y,np.zeros_like(y)),'osmesa_rate':stats.paired(x,np.zeros_like(x)),'osmesa_failure_to_egl_success':int(((x==0)&(y==1)).sum()),'osmesa_success_to_egl_failure':int(((x==1)&(y==0)).sum()),'egl_vs_old_success_mismatches':int((y!=old).sum()),'egl_vs_old_first_hit_mismatches':sum(r['egl_first_hit']!=r['old_first_hit'] for r in rows),'egl_vs_old_all_actions_equal_cases':sum(r['egl_vs_old_all_actions_equal'] for r in rows),'reset_image_checks':images,'cases':rows,'input_sha256':inputs,'sealed_statistics_sha256':hashlib.sha256(statsfile.read_bytes()).hexdigest(),'bootstrap_replicates':5000,'bootstrap_seed':20261011}
out=W/'RENDERER_FINAL_ANALYSIS.json';assert not out.exists();out.write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k not in ['cases','input_sha256']},indent=2))
