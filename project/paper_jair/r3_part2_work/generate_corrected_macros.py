#!/usr/bin/env python3
"""Generate a post-input LaTeX overlay and evidence-based section-7 draft.

Run only after complete corrected analysis. Never edit existing paper files.
Existing non-Reacher numerical macros (including seed-20261012 paired CIs)
are deliberately untouched. Figures/tables belong to update_paper_corrected.py.
"""
from pathlib import Path
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import re

WORK=Path(__file__).resolve().parent
PAPER=WORK.parent
S4=PAPER.parent/'d1_execution/step4/resume_01'


def require(ok,message):
    if not ok:raise ValueError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def f(value):
    value=float(value);require(math.isfinite(value),'Nonfinite input number');return value


def fmt(value,signed=False,digits=1):
    value=f(value)
    # Do not emit negative zero after rounding.
    if abs(value)<.5*10**(-digits):value=0.0
    return format(value,('+' if signed else '')+f'.{digits}f')


def ci(row,digits=1):
    return f"{fmt(row['delta_pp'],True,digits)} [{fmt(row['ci95_low_pp'],True,digits)}, {fmt(row['ci95_high_pp'],True,digits)}]"


def one(rows,**filters):
    rows=[r for r in rows if all(str(r.get(k))==str(v) for k,v in filters.items())]
    require(len(rows)==1,f'Expected one row {filters}; got {len(rows)}')
    return rows[0]


def tau_text(row):
    if row['status']=='DEFINED':return fmt(row['kendall_tau_b'],digits=2)
    require(row['status']=='UNDEFINED_ALL_TIED','Missing or invalid Kendall result')
    return 'undefined (all tied)'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--analysis',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    require(not args.output.exists(),'Choose a new output directory; no overwrite')
    require(args.output.resolve().is_relative_to(WORK),'Output must be below r3_part2_work')
    manifest=json.loads((args.analysis/'ANALYSIS_MANIFEST.json').read_text())
    require(manifest.get('status')=='COMPLETE' and manifest.get('corrected_trajectories')==2700,
            'Need complete 2700-trajectory corrected analysis')
    require(manifest.get('bootstrap',{}).get('seed')==20261011 and
            manifest.get('bootstrap',{}).get('replicates')==5000,'Reacher bootstrap provenance differs from sealed V2')
    inputs={str(args.analysis/'ANALYSIS_MANIFEST.json'):sha(args.analysis/'ANALYSIS_MANIFEST.json')}
    def csv_rows(name):
        p=args.analysis/name
        require(p.is_file() and manifest['outputs'].get(name)==sha(p),f'Analysis output hash mismatch: {name}')
        inputs[str(p)]=sha(p)
        with p.open(encoding='utf-8-sig',newline='') as handle:return list(csv.DictReader(handle))
    ar=csv_rows('ABSOLUTE_RATES.csv');oldar=csv_rows('ABSOLUTE_RATES_OLD.csv')
    ct=csv_rows('CONTRASTS.csv');pair=csv_rows('AP_LEWM_PAIRED.csv')
    kt=csv_rows('KENDALL_TAU.csv');oldkt=csv_rows('KENDALL_TAU_OLD.csv')
    before=csv_rows('OLD_VS_CORRECTED.csv');labels=csv_rows('LABEL_SEMANTICS_COMPARISON.csv')
    raw=csv_rows('TRAJECTORIES.csv')
    originals={}
    for name in ['numbers.tex','revision3_pair_stats.tex']:
        p=PAPER/'a3_results'/name;inputs[str(p)]=sha(p)
        originals.update(re.findall(r'\\newcommand\{\\([A-Za-z]+)\}\{([^}]*)\}',p.read_text()))
    out,provenance={},{}
    def put(name,value,source):
        require(name not in out,f'Duplicate macro assignment {name}')
        out[name]=str(value);provenance[name]=source
    def rate(model,definition='any',old=False,it=30):
        return one(oldar if old else ar,model=model,iterations=it,definition=definition)
    def contrast(name,definition='any',analysis='main'):
        return one(ct,contrast=name,definition=definition,analysis=analysis)
    def paired(definition,version='corrected'):
        return one(pair,version=version,definition=definition)

    for prefix,model in [('ReacherLeWMOne','LeWM_h1'),('ReacherAP','M03_h1'),('ReacherLeWMThree','LeWM_h3')]:
        for definition in ['any','block','final']:
            put(prefix+definition.title(),fmt(rate(model,definition)['rate_pct']),f'ABSOLUTE_RATES: {model}/{definition}/30')
    history=contrast('LeWM_h3 - LeWM_h1')
    for name in ['ReacherHistoryDelta','ReacherHistoryDeltaRevision']:
        put(name,fmt(history['delta_pp'],True),'CONTRASTS: main/h3-h1/any')
    for suffix,field in [('Low','ci95_low_pp'),('High','ci95_high_pp')]:
        put('ReacherHistory'+suffix,fmt(history[field],True),'CONTRASTS: main/h3-h1/any')
    put('ReacherHistoryCI',ci(history),'CONTRASTS: main/h3-h1/any')
    interval=f"[{fmt(history['ci95_low_pp'],True)}, {fmt(history['ci95_high_pp'],True)}]"
    for name in ['ReacherHistoryCIOnly','ReacherHistoryCIRevision']:
        put(name,interval,'CONTRASTS: main/h3-h1/any; interval-only avoids repeating point estimate after 95% CI')
    historyfinal=contrast('LeWM_h3 - LeWM_h1','final')
    put('ReacherHistoryFinalCI',ci(historyfinal),'CONTRASTS: main/h3-h1/final')
    put('ReacherHistoryFinalDelta',fmt(historyfinal['delta_pp'],True),'CONTRASTS: main/h3-h1/final')
    for suffix,model in [('MOne','M01_h1'),('MSeven','M07_h1'),('MThree','M03_h1')]:
        put('Reacher'+suffix+'Delta',ci(contrast('LeWM_h3 - '+model,analysis='C2')),'CONTRASTS: C2/h3-'+model+'/any')
    for name,model in [('ReacherThreeVsFast','M01_h1'),('ReacherThreeVsAD','M07_h1')]:
        put(name,fmt(contrast('LeWM_h3 - '+model,analysis='C2')['delta_pp'],True),'CONTRASTS: C2/h3-'+model+'/any')
    threeap=f(contrast('LeWM_h3 - M03_h1',analysis='C2')['delta_pp'])
    put('ReacherAPVsThree',fmt(-threeap,True),'NEGATIVE of C2 h3-AP: macro means AP minus h3; fixes former negative-below wording')
    put('ReacherThreeVsAP',fmt(threeap,True),'CONTRASTS: C2/h3-AP/any')
    for definition in ['any','final']:
        row=paired(definition)
        for name in ['APReacher'+definition.title()+'Delta','ReacherAPLeWM'+definition.title()+'Delta']:
            put(name,fmt(row['delta_pp'],True),'AP_LEWM_PAIRED: corrected/'+definition)
    for suffix,definition in [('Any','any'),('Final','final'),('Change','final_minus_any_difference_in_differences')]:
        put('APLeWMReacher'+suffix+'CI',ci(paired(definition)),'AP_LEWM_PAIRED: corrected/'+definition)
        put('OldAPLeWMReacher'+suffix+'CI',ci(paired(definition,'old')),'AP_LEWM_PAIRED: old/'+definition)
    for r in kt:
        suffix=''.join(x.title() for x in r['definitions'].split('/'))
        for name in ['TauReacher'+suffix,'ReacherTau'+suffix]:
            put(name,tau_text(r),'KENDALL_TAU: '+r['definitions'])
        old=one(oldkt,definitions=r['definitions'])
        put('OldReacherTau'+suffix,tau_text(old),'KENDALL_TAU_OLD: '+r['definitions'])
    for prefix,model in [('ReacherAOneLeWMOne','LeWM_h1'),('ReacherAOneAP','M03_h1')]:
        outside=rate(model,'outside_fraction_after_first_hit')
        put(prefix+'PostHit',fmt(100-f(outside['rate_pct'])),'100 - ABSOLUTE_RATES outside_fraction_after_first_hit; only observable later-step windows')
        records=[r for r in raw if r['version']=='corrected' and r['model']==('LeWM' if model=='LeWM_h1' else 'M03')
                 and r['history']=='1' and r['iterations']=='30']
        require(len(records)==300,f'Expected one-checkpoint 300 trajectories for {model}')
        hits=sum(f(r['any']) for r in records)
        leave=None if hits==0 else 100*sum(f(r['any'])-f(r['final']) for r in records)/hits
        require(leave is not None,f'No hits for legacy leave macro {model}; explicit undefined handling needed')
        put(prefix+'Leave',fmt(leave),'TRAJECTORIES: corrected hit-but-not-final / any hit; retains original macro estimand')
    q=contrast('LeWM_h1 CEM10 - CEM30',analysis='D4_iterations')
    for suffix,field in [('Delta','delta_pp'),('Low','ci95_low_pp'),('High','ci95_high_pp')]:
        put('DFourReacherHOneAny'+suffix,fmt(q[field],True),'CONTRASTS: D4_iterations/h1/any')
    # Recompute the all-task maximum after replacing only Reacher D4 cells.
    old_path=S4/'results/CONTRASTS.csv'
    expected={r['path']:r['sha256'] for r in json.loads((S4/'SEAL.json').read_text())['files']}
    require(expected['results/CONTRASTS.csv']==sha(old_path),'Frozen other-task contrast hash mismatch')
    inputs[str(old_path)]=sha(old_path)
    with old_path.open(encoding='utf-8-sig') as handle:old_contrasts=list(csv.DictReader(handle))
    cem=[r for r in old_contrasts if r['task']!='reacher' and r['analysis']=='D4_iterations']+[
        r for r in ct if r['analysis']=='D4_iterations']
    require(len(cem)==24,'Expected 4 tasks x 2 histories x 3 success definitions for D4 maximum')
    maxrow=max(cem,key=lambda r:abs(f(r['delta_pp'])))
    put('CEMMaxDelta',fmt(abs(f(maxrow['delta_pp']))),'max |D4 delta| across new Reacher + unchanged sealed other tasks; '+str({k:maxrow[k] for k in ['task','contrast','definition']}))

    # New numerical hooks for the termination correction as a reported result.
    for prefix,model in [('LeWMOne','LeWM_h1'),('LeWMThree','LeWM_h3'),('AP','M03_h1')]:
        for definition in ['any','block','final']:
            put('OldReacher'+prefix+definition.title(),fmt(rate(model,definition,old=True)['rate_pct']),
                f'ABSOLUTE_RATES_OLD: {model}/{definition}/30')
            delta=one(before,model=model,iterations=30,metric=definition)
            put('ReacherCorrection'+prefix+definition.title()+'CI',ci(delta),'OLD_VS_CORRECTED: '+model+'/'+definition)
        for definition in ['block','final']:
            r=one(labels,model=model,iterations=30,metric=definition)
            put('ReacherEndMinusOR'+prefix+definition.title()+'CI',ci(r),'LABEL_SEMANTICS_COMPARISON: '+model+'/'+definition)
    for definition in ['block','final']:
        for version,old in [('Old',True),('New',False)]:
            put('ReacherTerminationLeWM'+definition.title()+version,fmt(rate('LeWM_h1',definition,old=old)['rate_pct']),
                ('ABSOLUTE_RATES_OLD' if old else 'ABSOLUTE_RATES')+': LeWM_h1/'+definition)
    for suffix,definition in [('Any','any'),('Final','final'),('Change','final_minus_any_difference_in_differences')]:
        for title,version in [('Old','old'),('New','corrected')]:
            put('ReacherTerminationAP'+suffix+'Contrast'+title,ci(paired(definition,version)),
                'AP_LEWM_PAIRED: '+version+'/'+definition)
    if threeap>0:
        comparison=f'Three-frame LeWM exceeds AP by {fmt(threeap)} percentage points under any-step success.'
    elif threeap<0:
        comparison=f'Three-frame LeWM is {fmt(-threeap)} percentage points below AP under any-step success.'
    else:
        comparison='Three-frame LeWM and AP have equal any-step point estimates.'
    put('ReacherAPHistoryComparisonSentence',comparison,'CONTRASTS C2: h3 - AP; direction chosen from actual sign')
    intro=None
    if 'INTRO_EXAMPLE_STATES.csv' in manifest['outputs']:
        states=csv_rows('INTRO_EXAMPLE_STATES.csv');candidates=csv_rows('INTRO_CANDIDATES.csv')
        selected=manifest.get('illustrative_example')
        require(selected is not None and len(states)==50,'Incomplete illustration provenance')
        candidate=one(candidates,condition_id=selected['condition_id'],case_id=selected['case_id'],stream=selected['stream'])
        first_end=int(candidate['first_end_hit_step'])
        exits=[int(r['env_step']) for r in states if int(r['env_step'])>first_end and r['step_end']=='False']
        require(exits,'Selected illustrative trajectory has no subsequent recorded departure')
        values={'ReacherIntroCase':candidate['case_id'].replace('_',r'\_'),
                'ReacherIntroStream':candidate['stream'].replace('_',r'\_'),
                'ReacherIntroFirstAnyStep':candidate['first_any_hit_step'],
                'ReacherIntroFirstEndStep':candidate['first_end_hit_step'],
                'ReacherIntroFirstExitStep':str(exits[0]),'ReacherIntroFinalStep':states[-1]['env_step'],
                'ReacherIntroFinalMaxJointError':fmt(max(f(states[-1]['abs_error0']),f(states[-1]['abs_error1'])),digits=3),
                'ReacherJointThreshold':fmt(states[-1]['threshold'],digits=2)}
        for k,v in values.items():put(k,v,'INTRO_CANDIDATES + INTRO_EXAMPLE_STATES (selected actual corrected trajectory)')
        aliases={'IntroFirstHitStep':candidate['first_end_hit_step'],
                 'IntroFirstAnyHitStep':candidate['first_any_hit_step'],
                 'IntroExitStep':str(exits[0]),'IntroFinalStep':states[-1]['env_step'],
                 'IntroFinalState':'inside the target' if states[-1]['step_end']=='True' else 'outside the target'}
        for k,v in aliases.items():put(k,v,'INTRO_EXAMPLE_STATES: first endpoint hit/exit/final endpoint; see ReacherIntro macros')
        intro=dict(candidate=candidate,first_exit_step=exits[0])

    # Every Reacher macro is either replaced above or has an explicit reason
    # to remain sourced from the earlier, unaffected experiment/inventory.
    unaffected={
        'ReacherNoiseRange':'Step-2 ten-stream any-step noise diagnostic; not HELDOUT continuation',
        'ReacherNoiseHalfwidth':'Step-2 registered-function any-step uncertainty',
        'ReacherFifty':'Step-2 any-step noise', 'ReacherHundred':'Step-2 any-step noise',
        'ReacherHundredThree':'Step-2 any-step noise', 'NoiseReacherFifty':'Step-2 any-step noise',
        'NoiseReacherHundred':'Step-2 any-step noise','NoiseReacherHundredThree':'Step-2 any-step noise',
        'ReplanReacherDelta':'Step-3 stream-matched any-step protocol contrast; not rerun scope',
        'LibraryReacherDelta':'Step-3 any-step version factor; not rerun scope',
        'PaperGainRangeReacher':'Published literature inventory', 'ClaimRangeReacher':'Published literature inventory',
        'ReproAPReacherOur':'Step-2 original-protocol reproduction',
        'ReproAPReacherPaper':'Published original-protocol comparison value',
    }
    current_reacher={k for k in originals if 'Reacher' in k}
    require(current_reacher <= set(out)|set(unaffected),
            'Unclassified existing Reacher macros: '+str(sorted(current_reacher-set(out)-set(unaffected))))
    require(not (set(out)&set(unaffected)),'Unaffected macro accidentally rewritten')
    require(all('Reacher' in k or k=='CEMMaxDelta' or k.startswith('Intro') for k in out),'Non-Reacher macro rewrite prohibited')

    # Prose is selected only from actual point estimates/intervals, without a
    # predetermined Reacher reversal or reset-effect conclusion.
    anyrow,finalrow,change=(paired(d) for d in ['any','final','final_minus_any_difference_in_differences'])
    anyv,finv=f(anyrow['delta_pp']),f(finalrow['delta_pp'])
    reversal=anyv*finv<0
    excludes=lambda r:f(r['ci95_low_pp'])*f(r['ci95_high_pp'])>0
    effect_sentence=('The AP--LeWM point estimates reverse sign between the two success definitions.' if reversal else
                     'The AP--LeWM point estimates do not reverse sign between the two success definitions.')
    if reversal and excludes(anyrow) and excludes(finalrow):effect_sentence+=' Both paired intervals exclude zero.'
    h3direction='higher' if threeap>0 else 'lower' if threeap<0 else 'equal'
    lines=[
        '% Suggested section-7 prose, generated only from complete corrected CSVs. Review cross-references after insertion.',
        r'\paragraph{Success timing on continuous trajectories.}',
        f"On the corrected Reacher trajectories, LeWM one-frame attains {fmt(rate('LeWM_h1','any')['rate_pct'])}\\% any-step success, {fmt(rate('LeWM_h1','block')['rate_pct'])}\\% block-boundary success, and {fmt(rate('LeWM_h1','final')['rate_pct'])}\\% final-step success. The corresponding AP rates are {fmt(rate('M03_h1','any')['rate_pct'])}\\%, {fmt(rate('M03_h1','block')['rate_pct'])}\\%, and {fmt(rate('M03_h1','final')['rate_pct'])}\\%. AP minus LeWM is {ci(anyrow)} percentage points under any-step success and {ci(finalrow)} points under final-step success. The change in that contrast, final minus any, is {ci(change)} points, calculated with the same paired case draws. {effect_sentence}",
        '',r'\paragraph{Continuation semantics change the measurement.}',
        f"The released Reacher implementation uses successful joint matching to terminate the dm\\_control episode. Continuing after that termination invokes an internal reset on the next step. The corrected worker records the same success predicate while keeping the physical episode continuous. LeWM one-frame block-boundary success changes from {fmt(rate('LeWM_h1','block',old=True)['rate_pct'])}\\% in the original continuation record to {fmt(rate('LeWM_h1','block')['rate_pct'])}\\%, and final-step success from {fmt(rate('LeWM_h1','final',old=True)['rate_pct'])}\\% to {fmt(rate('LeWM_h1','final')['rate_pct'])}\\%. AP final-step success changes from {fmt(rate('M03_h1','final',old=True)['rate_pct'])}\\% to {fmt(rate('M03_h1','final')['rate_pct'])}\\%. The AP--LeWM final-step contrast changes from {ci(paired('final','old'))} to {ci(finalrow)} points. The original and corrected any-step versus final-step Kendall correlations are {tau_text(one(oldkt,definitions='any/final'))} and {tau_text(one(kt,definitions='any/final'))}, respectively.",
        '',
        f"This comparison includes both continuous post-success dynamics and the registered endpoint-label correction. Within the corrected trajectories alone, changing from microstep-OR to environment-step-END labels changes LeWM one-frame final-step success by {ci(one(labels,model='LeWM_h1',iterations=30,metric='final'))} points and AP final-step success by {ci(one(labels,model='M03_h1',iterations=30,metric='final'))} points. Any-step success retains the OR label; block and final success use END labels.",
        '',r'% Optional history sentence (belongs in history/common-protocol results):',
        f"The corrected final-step rates are {fmt(rate('LeWM_h1','final')['rate_pct'])}\\% with one-frame history and {fmt(rate('LeWM_h3','final')['rate_pct'])}\\% with three frames; their paired difference is {ci(historyfinal)} points. Under any-step success, three-frame LeWM is {fmt(abs(threeap))} points {h3direction} than AP." if h3direction!='equal' else
        f"The corrected final-step history difference is {ci(historyfinal)} points; three-frame LeWM and AP have equal any-step point estimates.",
    ]
    if intro:
        lines+=['',r'% Optional replacement introduction example (actual selected corrected record):',
            f"A corrected held-out Reacher trajectory first satisfies the joint target at an environment-step endpoint at step {intro['candidate']['first_end_hit_step']}, leaves it by step {intro['first_exit_step']}, and is outside it at step {len(states)}. The joint-error trace records this arrival and departure within one continuous physical episode."]
    else:
        lines+=['','% No eligible corrected Reacher illustration was returned. A separately verified PushT example is required; do not reuse the old reset example.']
    args.output.mkdir(parents=True)
    overlay=['% Generated by generate_corrected_macros.py from SHA-verified complete corrected analysis.',
             '% Include AFTER a3_results/numbers.tex and revision3_pair_stats.tex (including corrected asset copies).',
             '% Non-Reacher pair intervals retain their existing seed-20261012 values.']
    for name,value in out.items():
        if name not in originals:overlay.append(rf'\providecommand{{\{name}}}{{}}')
        overlay.append(rf'\renewcommand{{\{name}}}{{{value}}}')
    (args.output/'revision3_corrected_numbers.tex').write_text('\n'.join(overlay)+'\n')
    (args.output/'SECTION7_CORRECTED_DRAFT_EN.tex').write_text('\n'.join(lines)+'\n')
    audit=dict(utc=dt.datetime.now(dt.timezone.utc).isoformat(),status='GENERATED_FROM_COMPLETE_ANALYSIS',
        updated_macros={k:dict(value=v,source=provenance[k],previous_value=originals.get(k)) for k,v in out.items()},
        intentionally_unchanged_reacher_macros=unaffected,
        all_existing_reacher_macros_classified=True,
        non_reacher_pair_ci_policy='Existing PushT/TwoRoom/Cube pair CIs from REVISION_3_PAIR_STATS (seed 20261012) remain byte-for-byte in source files and are not overridden.',
        corrected_reacher_bootstrap='Frozen V2: 5000 replicates, seed 20261011, percentile .025/.975; shared case indices',
        coverage_vs_asset_generator='Full overlay independently covers known main macros; additionally fills missing A1 PostHit/Leave, h3 rates, correction-old/new, label OR/END, and intro macros.',
        semantic_fixes=['ReacherAPVsThree is AP minus h3, matching the name and below-AP construction; use generated direction-aware sentence.',
                        'ReacherHistoryCIRevision is interval-only for the existing 95% CI prose, not point estimate plus interval.'],
        unresolved_numeric_scope=['Correction and total GPU/cost macros need actual run-cost receipts; no cost inferred from the experiment tables. Historical StepTwoGPUHours/FormalGPUHours/TotalGPUHours remain unchanged in this overlay until the cost table is updated explicitly.'],
        inputs=inputs,outputs={p.name:sha(p) for p in args.output.iterdir()})
    inputs[str(Path(__file__))]=sha(Path(__file__))
    (args.output/'CORRECTED_MACRO_AUDIT.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status='COMPLETE',macros=len(out),output=str(args.output)),indent=2))


if __name__=='__main__':main()
