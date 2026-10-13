#!/usr/bin/env python3
"""CPU-only analysis of COMPLETE, locally returned Revision-3 Reacher runs.

This script refuses partial grids and never imports a model or environment.
It writes only a new analysis directory; it does not update the manuscript.
Corrected endpoint measures use runtime.step_end_labels, never legacy successes.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import importlib.util
import inspect
import itertools
import json
from pathlib import Path

import numpy as np
from scipy.stats import beta, kendalltau, rankdata

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[1]
S4 = ROOT / 'd1_execution/step4/resume_01'
SEALED_STATS = ROOT / 'd1_execution/step1/upload/code/tools/statistics_d1.py'
PREREG = ROOT / 'd1_execution/prereg/PREREG_D1_V2_FOLLOWUP.md'
STREAMS = ['R3_ORIGINAL', 'R4_ALT_CEM_1', 'R4_ALT_CEM_2']
CIDS = ['D1V2_001', 'D1V2_002', 'D1V2_009', 'D1V2_010', 'D1V2_011',
        'D1V2_012', 'D1V2_013', 'D1V2_029', 'D1V2_030']
MAIN_MODELS = ['LeWM_h1', 'LeWM_h3', 'M01_h1', 'M03_h1', 'M07_h1']
DEFS = ['any', 'block', 'final']
METRICS = DEFS + ['last5_occupancy', 'last10_occupancy', 'last5_all', 'last10_all',
    'hit_eligible_for_later_step', 'hit_and_later_step_exit',
    'hit_and_later_outside_fraction', 'hit_and_exit_by_any_endpoint',
    'end_any', 'or_block', 'or_final']


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def bool_vector(value, count, description):
    require(isinstance(value, list) and len(value) == count, f'{description}: expected {count} items')
    require(all(type(x) is bool for x in value), f'{description}: labels must be JSON booleans')
    return np.asarray(value, bool)


def trajectory_metrics(step_any, step_end):
    """Nonlinear metrics are computed per trajectory BEFORE any averaging."""
    first = np.flatnonzero(step_any)
    hit = int(first[0]) if len(first) else None
    eligible = hit is not None and hit < 49
    later = step_end[hit + 1:] if eligible else np.empty(0, bool)
    return {
        'any': float(step_any.any()), 'block': float(step_end[4::5].any()),
        'final': float(step_end[-1]),
        **{f'last{k}_occupancy': float(step_end[-k:].mean()) for k in (5, 10)},
        **{f'last{k}_all': float(step_end[-k:].all()) for k in (5, 10)},
        'hit_eligible_for_later_step': float(eligible),
        'hit_and_later_step_exit': float(eligible and (~later).any()),
        'hit_and_later_outside_fraction': float((~later).mean()) if eligible else 0.0,
        # Captures a first-microstep hit followed by exit in the same env step.
        'hit_and_exit_by_any_endpoint': float(hit is not None and (~step_end[hit:]).any()),
        'end_any': float(step_end.any()), 'or_block': float(step_any[4::5].any()),
        'or_final': float(step_any[-1]), 'first_hit_step': None if hit is None else hit + 1,
    }


def load_statistics():
    spec = importlib.util.spec_from_file_location('sealed_statistics', SEALED_STATS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sig = inspect.signature(module.paired)
    reps, seed = sig.parameters['boot'].default, sig.parameters['seed'].default
    require((reps, seed) == (5000, 20261011), 'Frozen bootstrap parameters changed')
    text = PREREG.read_text()
    require('5,000' in text and '20261011' in text, 'V2 prereg bootstrap source mismatch')
    return module, reps, seed


def expected_corrected_files(specs, case_ids):
    expected=set()
    for cid in CIDS:
        for case,stream in itertools.product(case_ids,STREAMS):
            if specs[cid]['model']=='LeWM':
                expected.update((Path(cid)/case/stream/name).as_posix()
                                for name in ('STARTED.json','trajectory.npz','result.json','COMPLETE.json'))
            else:
                expected.update((Path(cid)/stream/(case+suffix)).as_posix()
                                for suffix in ('.json','.actions.npy','.first_plan.npy'))
    require(len(expected)==9300,'Expected exactly 4800 LeWM and 4500 method artifacts')
    return expected


def validate_corrected_seal(seal, specs, case_ids):
    require(seal.get('status')=='SEALED_VERIFIED_CORRECTED_RESULTS'
            and seal.get('expected_trajectories')==2700 and seal.get('conditions')==9
            and seal.get('cases_per_condition')==100 and seal.get('streams')=='ABC',
            'Corrected result seal scope is not the complete registered grid')
    files=seal.get('files')
    require(isinstance(files,dict),'Corrected seal files must be a relative-path/SHA256 mapping')
    expected=expected_corrected_files(specs,case_ids)
    require(set(files)==expected,
            f'Corrected seal artifact set differs: missing={len(expected-set(files))}, unexpected={len(set(files)-expected)}')
    require(all(isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)
                for v in files.values()),'Malformed corrected SHA256 value')
    # A verified tree may move to external storage. Relative identity and
    # content hashes bind the input; the historical absolute root is metadata.
    return len(expected)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--formal-root', required=True, type=Path,
                    help='Local corrected formal/ directory containing all nine D1V2 condition directories')
    ap.add_argument('--output', required=True, type=Path, help='New directory; existing output is rejected')
    ap.add_argument('--corrected-seal', required=True, type=Path,
                    help='Local seal constructed from the fully SHA-verified final return')
    ap.add_argument('--old-formal-root', type=Path, default=S4/'remote_sync/FINAL_RESULTS/formal')
    args = ap.parse_args()
    require(not args.output.exists(), 'Output already exists; choose a new path (no overwrite/delete)')
    require(args.output.resolve().is_relative_to(WORK), 'Outputs must stay below r3_part2_work')
    inputs = {}
    sealed = {x['path']: x['sha256'] for x in json.loads((S4/'SEAL.json').read_text())['files']}
    corrected_seal=json.loads(args.corrected_seal.read_text())
    require(corrected_seal.get('status')=='SEALED_VERIFIED_CORRECTED_RESULTS'
            and corrected_seal.get('expected_trajectories')==2700, 'Corrected result seal invalid')
    corrected_root=args.formal_root.resolve()
    logical_corrected_root=args.formal_root.absolute()

    def track(path, original=False):
        requested=Path(path).absolute()
        path = requested.resolve()
        require(path.is_file(), f'Missing input: {path}')
        digest = sha(path)
        if original:
            rel = path.relative_to(S4).as_posix()
            require(rel in sealed and digest == sealed[rel], f'Original sealed hash mismatch: {path}')
        elif requested.is_relative_to(logical_corrected_root):
            require(path.is_relative_to(corrected_root),f'Corrected artifact escapes verified root: {requested}')
            rel=requested.relative_to(logical_corrected_root).as_posix()
            require(corrected_seal['files'].get(rel)==digest, f'Corrected sealed hash mismatch: {path}')
        inputs[str(path)] = digest
        return path

    def read(path, original=False):
        return json.loads(track(path, original).read_text())

    specs = read(S4/'CONDITION_SPECS.json', True)
    cases = read(S4/'cases/HELDOUT_CASES_V2.json', True)['tasks']['reacher']
    ids = [x['case_id'] for x in cases]
    require(len(ids) == len(set(ids)) == 100, 'Expected 100 distinct sealed HELDOUT cases')
    require(len({x['episode_id'] for x in cases}) == 100, 'Expected one case per episode')
    require([c for c, s in specs.items() if s['task'] == 'reacher'] == CIDS,
            'Nine-condition correction grid differs from sealed step-4 scope')
    corrected_file_count=validate_corrected_seal(corrected_seal,specs,ids)
    stats, reps, seed = load_statistics()
    track(SEALED_STATS); track(PREREG); track(S4/'SEAL.json'); track(Path(__file__)); track(args.corrected_seal)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(ids), (reps, len(ids)))

    def interval(vector):
        vector = np.asarray(vector, float)
        require(vector.shape == (100,) and np.isfinite(vector).all(), 'Invalid case-level vector')
        draws = vector[indices].mean(1) * 100
        point = float(vector.mean() * 100)
        lo, hi = np.quantile(draws, [.025, .975])
        p = (1 + int((np.abs(draws - point) >= abs(point)).sum())) / (reps + 1)
        return dict(n_cases=100, delta_pp=point, ci95_low_pp=float(lo), ci95_high_pp=float(hi),
                    halfwidth_pp=float((hi-lo)/2), p_centered_bootstrap=p,
                    practically_negligible=bool(lo >= -5 and hi <= 5), gain_supported=bool(lo > 0),
                    label='实际可忽略' if lo >= -5 and hi <= 5 else '增益成立' if lo > 0 else '未检出')

    def ratio_interval(numerator, denominator):
        n, d = np.asarray(numerator), np.asarray(denominator)
        point = None if d.sum() == 0 else float(n.sum()/d.sum()*100)
        bn, bd = n[indices].mean(1), d[indices].mean(1)
        good = bd > 0
        ci = np.quantile(bn[good]/bd[good]*100, [.025, .975]) if good.any() else [None, None]
        return dict(rate_pct=point, ci95_low_pp=None if ci[0] is None else float(ci[0]),
                    ci95_high_pp=None if ci[1] is None else float(ci[1]),
                    eligible_case_equivalents=float(d.sum()),
                    bootstrap_undefined_replicates=int((~good).sum()))

    # Store only numeric summaries and occupancy arrays, not full runtime logs.
    values, occupancy, rows, candidates, example = {}, {}, [], [], None
    checkpoint_identities={}
    for version, base in [('old', args.old_formal_root), ('corrected', args.formal_root)]:
        for cid in CIDS:
            s = specs[cid]
            arrays = {m: np.empty((100, 3), float) for m in METRICS}
            occ = np.empty((100, 3, 50), bool)
            for i, case in enumerate(ids):
                for j, stream in enumerate(STREAMS):
                    rel = (Path(cid)/case/stream/'result.json' if s['model'] == 'LeWM'
                           else Path(cid)/stream/(case+'.json'))
                    path = base/rel
                    original = version == 'old'
                    result = read(path, original)
                    for key, expected in [('status','COMPLETE'), ('case_id',case), ('stream',stream),
                                          ('task','reacher'), ('condition_id',cid), ('phase','FORMAL'),
                                          ('executed_raw_steps',50), ('raw_budget',50), ('success_mode','full50')]:
                        require(result.get(key) == expected, f'{path}: {key} != {expected}')
                    history = result.get('history_len', result.get('history_requested'))
                    require(history == s['history'], f'{path}: history differs')
                    plans=result.get('replans',result.get('plans'))
                    require(isinstance(plans,list),f'{path}: missing plan records')
                    anchors=[x.get('anchor_raw',x.get('raw_t')) for x in plans]
                    require(anchors==list(range(0,50,5 if s['model']=='M03' else 25)),
                            f'{path}: replanning schedule differs')
                    for pi,plan in enumerate(plans):
                        ns='R3_CEM_CASE_20261002' if stream==STREAMS[0] else stream
                        expected_seed=int.from_bytes(hashlib.sha256(f'{ns}/reacher/{case}/{pi}'.encode()).digest()[:8],'big')
                        require(plan.get('seed_uint64')==expected_seed,f'{path}: planning seed differs')
                    if s['model'] == 'LeWM':
                        started=read(path.with_name('STARTED.json'),original)
                        require(started.get('case')==cases[i] and started.get('cem_iterations')==s['iterations']
                                and started.get('history')==s['history'] and started.get('phase')=='FORMAL'
                                and started.get('condition_id')==cid,f'{path}: STARTED condition binding differs')
                        identity={k:started.get('model',{}).get(k) for k in ('weights_sha256','config_sha256')}
                        require(all(isinstance(v,str) and len(v)==64 for v in identity.values()),
                                f'{path}: missing checkpoint identity')
                        complete=read(path.with_name('COMPLETE.json'),original)
                        require({'STARTED.json','trajectory.npz','result.json'}.issubset(complete.get('sha256',{})),
                                f'{path}: incomplete artifact seal')
                        for name,digest in complete['sha256'].items():
                            artifact_path=track(path.with_name(name),original)
                            require(inputs[str(artifact_path)]==digest,f'{path}: artifact seal mismatch for {name}')
                        artifact = track(path.with_name('trajectory.npz'), original)
                        with np.load(artifact, allow_pickle=False) as z:
                            actions = z['raw_actions']
                            legacy = z['successes'].astype(bool) if original else None
                    else:
                        require(str(result.get('train_seed')) == str(s['train_seed']), f'{path}: training seed differs')
                        identity={'checkpoint_sha256':result.get('checkpoint_sha256')}
                        require(isinstance(identity['checkpoint_sha256'],str) and len(identity['checkpoint_sha256'])==64,
                                f'{path}: missing checkpoint identity')
                        artifact = track(path.with_name(case+'.actions.npy'), original)
                        actions = np.load(artifact, allow_pickle=False)
                        first_path=track(path.with_name(case+'.first_plan.npy'),original)
                        first_plan=np.load(first_path,allow_pickle=False)
                        require(hashlib.sha256(first_plan.tobytes()).hexdigest()==plans[0]['raw_plan']['sha256'],
                                f'{path}: first plan artifact differs')
                        legacy = np.array([x['success'] for x in result['steps']], bool) if original else None
                    if cid not in checkpoint_identities:checkpoint_identities[cid]=identity
                    require(identity==checkpoint_identities[cid],f'{path}: checkpoint differs across cases or old/new run')
                    require(actions.shape == (50, 2) and np.isfinite(actions).all(), f'{path}: incomplete actions')
                    runtime = None
                    if original:
                        require(legacy.shape == (50,), f'{path}: old label count')
                        any_labels = end_labels = legacy
                    else:
                        runtime = result.get('reacher_runtime')
                        require(isinstance(runtime, dict), f'{path}: missing runtime record; no legacy fallback permitted')
                        any_labels = bool_vector(runtime.get('step_any_labels'), 50, str(path)+' step_any')
                        end_labels = bool_vector(runtime.get('step_end_labels'), 50, str(path)+' step_end')
                        events = bool_vector(runtime.get('events', runtime.get('tracker_events')), 100, str(path)+' events')
                        require(np.array_equal(any_labels, events.reshape(50,2).any(1)), f'{path}: OR labels disagree with events')
                        require(np.array_equal(end_labels, events.reshape(50,2)[:,-1]), f'{path}: END labels disagree with events')
                        require(runtime.get('reset_count', runtime.get('reset_calls')) == 1, f'{path}: reset count differs')
                        require(runtime.get('internal_reset_events') == [], f'{path}: internal reset observed')
                        states = runtime.get('physics_steps')
                        require(isinstance(states,list) and len(states)==50, f'{path}: missing endpoint states')
                        times=np.asarray([x['physics.time'] for x in states],float)
                        require(np.isfinite(times).all() and (np.diff(times)>0).all(), f'{path}: nonmonotone physics time')
                        q=np.asarray([x['qpos'] for x in states],float)
                        target=np.asarray([x['target_qpos'] for x in states],float)
                        threshold=np.asarray([x['qpos_threshold'] for x in states],float)
                        require(q.shape==target.shape==(50,2) and np.all(threshold==.05), f'{path}: state/threshold mismatch')
                        require(np.array_equal(np.all(np.abs(q-target)<threshold[:,None],axis=1),end_labels),
                                f'{path}: endpoint predicate mismatch')
                    metric = trajectory_metrics(any_labels, end_labels)
                    for m in METRICS: arrays[m][i,j]=metric[m]
                    occ[i,j]=end_labels
                    rows.append(dict(version=version,condition_id=cid,task='reacher',case_id=case,stream=stream,
                                     model=s['model'],history=s['history'],iterations=s['iterations'],
                                     train_seed=s['train_seed'],**metric))
                    if version=='corrected' and cid=='D1V2_001':
                        hits=np.flatnonzero(end_labels)
                        if len(hits) and 5 <= hits[0] < 40 and not end_labels[-1]:
                            candidate=dict(condition_id=cid,case_id=case,stream=stream,
                                           first_end_hit_step=int(hits[0])+1,first_any_hit_step=metric['first_hit_step'],
                                           source=str(path),source_sha256=inputs[str(path.resolve())])
                            candidates.append(candidate)
                            key=(case,stream)
                            if example is None or key<example[0]:
                                example=(key,candidate,[dict(env_step=t+1,step_any=bool(any_labels[t]),
                                  step_end=bool(end_labels[t]),physics_time=float(times[t]),
                                  qpos0=float(q[t,0]),qpos1=float(q[t,1]),
                                  target0=float(target[t,0]),target1=float(target[t,1]),
                                  abs_error0=float(abs(q[t,0]-target[t,0])),abs_error1=float(abs(q[t,1]-target[t,1])),
                                  threshold=float(threshold[t])) for t in range(50)])
            values[version,cid]=arrays
            occupancy[version,cid]=occ
    require(len(rows)==5400, 'Expected 2700 old and 2700 corrected trajectories')

    groups={}
    for cid in CIDS:
        s=specs[cid]; key=(f'{s["model"]}_h{s["history"]}',s['iterations'])
        groups.setdefault(key,[]).append(cid)
    require(len(groups['M07_h1',30])==3, 'Three AD-WM checkpoints required')

    def per_case(version, group, metric):
        # Flow mean within each case/checkpoint, then checkpoint mean. Metrics
        # already evaluated separately on every physical trajectory above.
        return np.mean([values[version,c][metric].mean(1) for c in groups[group]],axis=0)

    def contrast(version,name,a,b,definition='any',analysis='main',**extra):
        return dict(version=version,analysis=analysis,task='reacher',contrast=name,definition=definition,
                    cohort='HELDOUT100',streams='ABC',status='COMPLETE',**interval(a-b),**extra)

    absolute, condition_rates, stream_rows, case_rows, occ_rows = [], [], [], [], []
    for version in ('old','corrected'):
        for cid in CIDS:
            s=specs[cid]
            for metric in METRICS:
                v=values[version,cid][metric]
                condition_rates.append(dict(version=version,condition_id=cid,model=s['model'],history=s['history'],
                     iterations=s['iterations'],train_seed=s['train_seed'],metric=metric,**interval(v.mean(1))))
                for j,stream in enumerate(STREAMS):
                    stream_rows.append(dict(version=version,condition_id=cid,model=s['model'],history=s['history'],
                         iterations=s['iterations'],train_seed=s['train_seed'],stream=stream,metric=metric,
                         **interval(v[:,j])))
        for group,cids in groups.items():
            model,it=group
            for metric in METRICS:
                v=per_case(version,group,metric)
                case_rows += [dict(version=version,model=model,iterations=it,case_id=c,metric=metric,value=float(x)) for c,x in zip(ids,v)]
                stat=interval(v)
                ntraj=300*len(cids)
                raw_success=sum(values[version,c][metric].sum() for c in cids)
                majority=int((v>.5).sum())
                cp_lo=0. if majority==0 else float(beta.ppf(.025,majority,101-majority)*100)
                cp_hi=100. if majority==100 else float(beta.ppf(.975,majority+1,100-majority)*100)
                absolute.append(dict(version=version,task='reacher',model=model,iterations=it,definition=metric,
                    status='COMPLETE',n_cases=100,trajectories=ntraj,successful_trajectories=float(raw_success),
                    rate_pct=stat['delta_pp'],ci95_low_pp=stat['ci95_low_pp'],ci95_high_pp=stat['ci95_high_pp'],
                    degenerate_all_trajectories=raw_success in (0,ntraj),case_majority_successes=majority,
                    case_majority_rate_pct=float(majority),case_majority_cp95_low_pct=cp_lo,case_majority_cp95_high_pct=cp_hi))
            for metric,num,den in [('exit_after_first_hit','hit_and_later_step_exit','hit_eligible_for_later_step'),
                                   ('outside_fraction_after_first_hit','hit_and_later_outside_fraction','hit_eligible_for_later_step'),
                                   ('exit_in_same_or_later_step','hit_and_exit_by_any_endpoint','any')]:
                absolute.append(dict(version=version,task='reacher',model=model,iterations=it,definition=metric,
                     status='COMPLETE',n_cases=100,trajectories=300*len(cids),
                     eligible_trajectories=int(sum(values[version,c][den].sum() for c in cids)),
                     **ratio_interval(per_case(version,group,num),per_case(version,group,den))))
            o=np.mean([occupancy[version,c].mean(axis=1) for c in cids],axis=0)
            for t in range(50):
                occ_rows.append(dict(version=version,model=model,iterations=it,env_step=t+1,**interval(o[:,t])))

    # Check the reconstructed OLD absolute rates against frozen statistics.
    with (S4/'results/ABSOLUTE_RATES.csv').open(encoding='utf-8-sig') as f: frozen=list(csv.DictReader(f))
    track(S4/'results/ABSOLUTE_RATES.csv',True)
    for r in absolute:
        if r['version']=='old' and r['definition'] in DEFS:
            matches=[x for x in frozen if x['task']=='reacher' and x['model']==r['model'] and
                     int(x['iterations'])==r['iterations'] and x['definition']==r['definition']]
            require(len(matches)==1 and abs(float(matches[0]['rate_pct'])-r['rate_pct'])<1e-10,
                    f'Old-result reconstruction mismatch: {r}')
    test=per_case('corrected',('M03_h1',30),'any')-per_case('corrected',('LeWM_h1',30),'any')
    check=stats.paired(test,np.zeros_like(test))
    own=interval(test)
    require(all(abs(check[k]-own[k])<1e-10 for k in ('delta_pp','ci95_low_pp','ci95_high_pp')),
            'Coupled bootstrap differs from frozen function')

    contrasts,ap_rows,label_rows,oldnew,rankings,taus=[] ,[],[],[],[],[]
    for version in ('old','corrected'):
        for df in DEFS:
            base=per_case(version,('LeWM_h1',30),df)
            for model in MAIN_MODELS[1:]:
                contrasts.append(contrast(version,f'{model} - LeWM_h1',per_case(version,(model,30),df),base,df))
            for model in MAIN_MODELS[2:]:
                contrasts.append(contrast(version,f'LeWM_h3 - {model}',per_case(version,('LeWM_h3',30),df),
                                          per_case(version,(model,30),df),df,analysis='C2'))
            for h in (1,3):
                model=f'LeWM_h{h}'
                contrasts.append(contrast(version,f'{model} CEM10 - CEM30',per_case(version,(model,10),df),
                                          per_case(version,(model,30),df),df,analysis='D4_iterations'))
                contrasts.append(contrast(version,f'paper LeWM h{h}/10 - official h1/30',
                         per_case(version,(model,10),df),base,df,analysis='D4_paper',paper_history_unspecified=True))
        for group in groups:
            for a,b in [('block','any'),('final','any'),('final','block')]:
                contrasts.append(contrast(version,f'{group[0]}: {a} - {b}',per_case(version,group,a),
                                          per_case(version,group,b),f'{a}-{b}',analysis='D1_definition',iterations=group[1]))
        ap_any=per_case(version,('M03_h1',30),'any')-per_case(version,('LeWM_h1',30),'any')
        ap_final=per_case(version,('M03_h1',30),'final')-per_case(version,('LeWM_h1',30),'final')
        for label,vector in [('any',ap_any),('final',ap_final),('final_minus_any_difference_in_differences',ap_final-ap_any)]:
            ap_rows.append(dict(version=version,contrast='M03_h1 - LeWM_h1',definition=label,**interval(vector)))
        rates={df:[per_case(version,(m,30),df).mean()*100 for m in MAIN_MODELS] for df in DEFS}
        for df,r in rates.items():
            rankings += [dict(version=version,task='reacher',definition=df,model=m,rate_pct=float(v),rank=float(rank))
                         for m,v,rank in zip(MAIN_MODELS,r,rankdata(-np.round(r,10),method='average'))]
        for a,b in itertools.combinations(DEFS,2):
            tau=kendalltau(np.round(rates[a],10),np.round(rates[b],10),variant='b').statistic
            taus.append(dict(version=version,task='reacher',definitions=f'{a}/{b}',
                             status='DEFINED' if np.isfinite(tau) else 'UNDEFINED_ALL_TIED',
                             kendall_tau_b=float(tau) if np.isfinite(tau) else None,n_models=5))
    for group in groups:
        for metric in DEFS+['last5_occupancy','last10_occupancy','last5_all','last10_all']:
            old,new=(per_case(v,group,metric) for v in ('old','corrected'))
            oldnew.append(dict(model=group[0],iterations=group[1],metric=metric,old_rate_pct=float(old.mean()*100),
                              corrected_rate_pct=float(new.mean()*100),**interval(new-old)))
        for name,or_metric,end_metric in [('any','any','end_any'),('block','or_block','block'),('final','or_final','final')]:
            a,b=(per_case('corrected',group,m) for m in (or_metric,end_metric))
            label_rows.append(dict(model=group[0],iterations=group[1],metric=name,or_rate_pct=float(a.mean()*100),
                                   end_rate_pct=float(b.mean()*100),contrast='END - OR',**interval(b-a)))

    # No files are created until completeness, labels, source hashes, and the
    # frozen-statistics equivalence checks above have all passed.
    args.output.mkdir(parents=True)
    def write_csv(name,data):
        if not data:return
        fields=list(dict.fromkeys(k for r in data for k in r))
        with (args.output/name).open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(data)
    write_csv('TRAJECTORIES.csv',rows)
    write_csv('CONDITION_RATES.csv',condition_rates)
    write_csv('ABSOLUTE_RATES.csv',[r for r in absolute if r['version']=='corrected'])
    write_csv('ABSOLUTE_RATES_OLD.csv',[r for r in absolute if r['version']=='old'])
    write_csv('PER_STREAM_AND_CHECKPOINT.csv',stream_rows)
    write_csv('CASE_METRICS.csv',case_rows)
    write_csv('OCCUPANCY.csv',occ_rows)
    write_csv('CONTRASTS.csv',[r for r in contrasts if r['version']=='corrected'])
    write_csv('CONTRASTS_OLD.csv',[r for r in contrasts if r['version']=='old'])
    write_csv('AP_LEWM_PAIRED.csv',ap_rows)
    write_csv('OLD_VS_CORRECTED.csv',oldnew)
    write_csv('LABEL_SEMANTICS_COMPARISON.csv',label_rows)
    write_csv('RANKINGS.csv',rankings)
    write_csv('KENDALL_TAU.csv',[r for r in taus if r['version']=='corrected'])
    write_csv('KENDALL_TAU_OLD.csv',[r for r in taus if r['version']=='old'])
    write_csv('INTRO_CANDIDATES.csv',candidates)
    if example:write_csv('INTRO_EXAMPLE_STATES.csv',example[2])
    manifest=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),status='COMPLETE',task='reacher',
        cases=100,streams=STREAMS,conditions=CIDS,corrected_trajectories=2700,old_trajectories=2700,
        corrected_artifacts_verified=corrected_file_count,
        corrected_seal_sha256=sha(args.corrected_seal),corrected_seal_recorded_root=corrected_seal.get('root'),
        actual_corrected_root=str(corrected_root),checkpoint_identities=checkpoint_identities,
        aggregation='Compute nonlinear metrics separately per trajectory; mean three streams within each case/checkpoint; mean three AD-WM checkpoints within case; case is resampling unit.',
        bootstrap=dict(replicates=reps,seed=seed,percentiles=[.025,.975],indices_sha256=hashlib.sha256(indices.tobytes()).hexdigest(),
                       shared_across='all old/new methods, streams, checkpoints, definitions, and differences-in-differences',
                       frozen_function_equivalence='PASS'),
        semantics=dict(any='any runtime.step_any_labels (OR over both physical microsteps)',
                       block='any runtime.step_end_labels at environment steps 5,10,...,50',
                       final='runtime.step_end_labels at environment step 50',
                       terminal_window='end labels only; nonlinear all-K computed before seed averaging',
                       exit_after_first_hit='Among hit trajectories with a later env step: any END false after first ANY-hit env step; ratio of case-averaged joint-event to eligible-hit mass',
                       outside_fraction_after_first_hit='Mean fraction END false strictly after first ANY-hit env step, conditional on at least one later step',
                       exit_in_same_or_later_step='Sensitivity: any END false at or after first ANY-hit env step, conditioned on any hit; includes within-step exit',
                       old='sealed legacy successes/step.success labels; post-success reset still present; source label semantics differ from corrected endpoint labels'),
        missing_results='none; partial grids prohibited',
        illustrative_example=example[1] if example else None,
        illustrative_selection='LeWM h1 i30: first END hit in zero-based [5,39], final END false; smallest case_id/stream; if no candidate use separately selected PushT example',
        inputs=inputs,outputs={p.name:sha(p) for p in args.output.iterdir() if p.is_file()},
        warnings=['Old paper REVISION_3_PAIR_STATS.py used seed 20261012; corrected analysis restores sealed seed 20261011.',
                  'Old A1/terminal-window AD-WM union/majority transformations are not used; per-checkpoint trajectory metrics precede averaging.',
                  'OLD_VS_CORRECTED includes both termination correction and registered OR-versus-END endpoint semantics; LABEL_SEMANTICS_COMPARISON separates the latter within corrected trajectories.'])
    (args.output/'ANALYSIS_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':'COMPLETE','output':str(args.output),'corrected_trajectories':2700,'bootstrap_seed':seed},indent=2))


if __name__=='__main__':
    main()
