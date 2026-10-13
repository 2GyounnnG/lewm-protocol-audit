"""Generate evidence-selected manuscript prose from completed corrected analysis."""
import argparse,csv,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as source:
        return list(csv.DictReader(source))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def runtime_replay_narrative(runtime_path,launch_path):
    """Generate replay counts only from the exact evidence bound by launch."""
    runtime=json.loads(runtime_path.read_text());launch=json.loads(launch_path.read_text())
    assert launch['status']=='AUTHORIZED_AFTER_GATES_AND_LOCAL_RETURN'
    assert sha(runtime_path)==launch['verified_evidence']['runtime_checks']['sha256']
    assert runtime['status']=='PASS' and runtime['reacher_replay']['pass']
    record=runtime['reacher_replay']['records'][0]
    assert record['pass']
    before=record['segments']['through_first_success'];after=record['segments']['after_first_success']
    total=int(record['n_actions']);prefix=int(before['n_steps']);later=int(after['n_steps'])
    original=int(before['original_matches'])+int(after['original_matches'])
    preserved=int(before['patched_matches']);different=int(record['post_success_disagreement'])
    assert total==prefix+later and original==total and preserved==prefix
    assert different==later-int(after['patched_matches'])
    sentence=(f'In a recorded held-out trajectory, replay under the original semantics reproduces {original}/{total} recorded success labels. '
              f'With success termination disabled, the within-step OR labels agree on all {preserved}/{prefix} labels through first success; '
              f'{different} of the {later} later labels differ. This label agreement does not assert equality of the environment-step-end state '
              f'at the first hit, because the corrected wrapper completes both microsteps.')
    return {'ReacherRuntimeReplaySentence':sentence},dict(runtime_checks_sha256=sha(runtime_path),
            launch_receipt_sha256=sha(launch_path),runtime_source=str(runtime_path),
            case_id=record['case_id'],stream=record['metadata']['stream'],
            total_labels=total,prefix_labels=prefix,prefix_agree=preserved,later_labels=later,later_differ=different,
            semantics='Patched replay labels are OR of the two microstep predicates; original labels retain native early termination.')
def write_values(output,values,audit):
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('% Generated from verified evidence; no handwritten numerical values.\n'+'\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in values.items())+'\n')
    output.with_suffix('.audit.json').write_text(json.dumps(dict(values=values,**audit),indent=2)+'\n')
def one(data,**filters):
    selected=[r for r in data if all(str(r[k])==str(v) for k,v in filters.items())]
    assert len(selected)==1,(filters,len(selected));return selected[0]
def f(v):return float(v)
def ci(r):return f"{f(r['delta_pp']):+.1f} [{f(r['ci95_low_pp']):+.1f}, {f(r['ci95_high_pp']):+.1f}]"
def main():
    p=argparse.ArgumentParser();p.add_argument('--analysis',type=Path);p.add_argument('--assets',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--runtime-only',action='store_true',help='Generate only the runtime-replay sentence without formal result inputs')
    p.add_argument('--runtime-json',type=Path,default=HERE/'returns/PREFORMAL_VERIFIED/experiment/runtime_checks_final.json')
    p.add_argument('--launch-json',type=Path,default=HERE/'returns/FORMAL_LAUNCH_RECEIPT.json')
    a=p.parse_args()
    if a.runtime_only:
        values,audit=runtime_replay_narrative(a.runtime_json,a.launch_json);write_values(a.output,values,audit)
        print(json.dumps({'macros':list(values),'output':str(a.output)}));return
    if a.analysis is None or a.assets is None:p.error('--analysis and --assets are required unless --runtime-only is used')
    manifest=json.loads((a.analysis/'ANALYSIS_MANIFEST.json').read_text());assert manifest['status']=='COMPLETE'
    assets=json.loads((a.assets/'PAPER_ASSETS_MANIFEST.json').read_text());assert assets['status']=='COMPLETE'
    rates=rows(a.analysis/'ABSOLUTE_RATES.csv');old=rows(a.analysis/'ABSOLUTE_RATES_OLD.csv');pairs=rows(a.analysis/'AP_LEWM_PAIRED.csv')
    rate=lambda data,m,d:f(one(data,model=m,definition=d,iterations=30)['rate_pct'])
    example=manifest['illustrative_example'];assert example,'Need separately verified PushT example if no corrected Reacher candidate'
    states=rows(a.analysis/'INTRO_EXAMPLE_STATES.csv')
    hit=int(example['first_end_hit_step']);exit_step=next(int(s['env_step']) for s in states if int(s['env_step'])>hit and s['step_end']=='False')
    last='outside' if states[-1]['step_end']=='False' else 'inside'
    out={'IntroExampleSentence':f'A continuous held-out Reacher trajectory reaches the joint target at an environment-step endpoint at step {hit}, leaves it by step {exit_step}, and is {last} the target at step 50. Figure~\\ref{{fig:overview}} shows the two joint-error curves from this corrected rollout.'}
    arow=one(pairs,version='corrected',definition='any');fin=one(pairs,version='corrected',definition='final')
    reverse=f(arow['delta_pp'])*f(fin['delta_pp'])<0
    if reverse:
        out['ReacherCorrectedRankingSentence']='Reacher also reverses the AP--LeWM point contrast between any-step and final-step success.'
    elif f(arow['delta_pp'])==0 or f(fin['delta_pp'])==0:
        out['ReacherCorrectedRankingSentence']='In corrected Reacher, at least one AP--LeWM point contrast is zero; there is no strict sign reversal between any-step and final-step success.'
    else:
        out['ReacherCorrectedRankingSentence']='In corrected Reacher, the AP--LeWM point contrast retains the same sign under any-step and final-step success.'
    if reverse and f(arow['ci95_low_pp'])*f(arow['ci95_high_pp'])>0 and f(fin['ci95_low_pp'])*f(fin['ci95_high_pp'])>0:
        out['ReacherCorrectedRankingSentence']+=' Both paired intervals exclude zero.'
    out['ReacherCorrectedRankingSentence']=out['ReacherCorrectedRankingSentence'].replace('AP--LeWM point contrast','AP--one-frame-LeWM point contrast')
    contrasts=rows(a.analysis/'CONTRASTS.csv')
    ha=one(contrasts,contrast='LeWM_h3 - M03_h1',definition='any')
    hf=one(contrasts,contrast='LeWM_h3 - M03_h1',definition='final')
    if f(ha['delta_pp'])*f(hf['delta_pp'])<0:
        out['ReacherCorrectedRankingSentence']+=(f' The comparison with three-frame LeWM does reverse: three-frame LeWM minus AP changes from {ci(ha)} points under any-step success to {ci(hf)} points under final-step success.')
    predictions=assets['prediction_subconditions'];assert len(predictions)==11
    count=sum(r['passed'] for r in predictions)
    out['CorrectedPredictionSummary']=('All three preregistered predictions satisfy their registered rules on the held-out set' if count==11 else f'{count} of the 11 preregistered subconditions satisfy their registered rules on the held-out set')
    oldfin=one(pairs,version='old',definition='final')
    out['ReacherTerminationResultSentence']=(f"For one-frame LeWM, block-boundary success changes from {rate(old,'LeWM_h1','block'):.1f}\\% to {rate(rates,'LeWM_h1','block'):.1f}\\%, and final-step success from {rate(old,'LeWM_h1','final'):.1f}\\% to {rate(rates,'LeWM_h1','final'):.1f}\\%. AP final-step success changes from {rate(old,'M03_h1','final'):.1f}\\% to {rate(rates,'M03_h1','final'):.1f}\\%. The AP--LeWM final-step contrast changes from {ci(oldfin)} to {ci(fin)} points.")
    occ=rows(a.assets/'data/OCCUPANCY_PEAKS.csv');q=one(occ,task='reacher',model='LeWM_h1')
    out['ReacherOccupancySentence']=(f"Corrected one-frame LeWM Reacher occupancy is {f(q['step25_pct']):.1f}\\% at step 25 and {f(q['step50_pct']):.1f}\\% at step 50; its minimum during steps 26--49 is {f(q['middle_min_pct']):.1f}\\% at step {q['middle_min_step']}.")
    write_values(a.output,out,{'analysis_manifest_sha256':sha(a.analysis/'ANALYSIS_MANIFEST.json'),'assets_manifest_sha256':sha(a.assets/'PAPER_ASSETS_MANIFEST.json')})
    print(json.dumps({'macros':list(out),'output':str(a.output)}))
if __name__=='__main__':main()
