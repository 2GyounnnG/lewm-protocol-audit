"""Prepare corrected prose in a new manuscript tree; numeric inputs follow verification."""
from pathlib import Path
P=Path(__file__).parents[1]
source=(P/'main.tex').read_text()
text=source

def paragraph(start,replacement):
    global text
    candidates=[p for p in text.splitlines() if p.startswith(start)]
    assert len(candidates)==1,(start,len(candidates))
    text=text.replace(candidates[0],replacement)

text=text.replace(r'\input{a3_results/revision3_pair_stats.tex}',r'\input{a3_results/revision3_pair_stats.tex}'+'\n'+r'\input{a3_results/revision3_corrected_numbers.tex}'+'\n'+r'\input{a3_results/revision3_corrected_narrative.tex}')
text=text.replace(r'\input{a3_results/revision3_corrected_narrative.tex}',r'\input{a3_results/revision3_corrected_narrative.tex}'+'\n'+r'\input{a3_results/revision3_runtime_narrative.tex}')
text=text.replace('The current Reacher audit gives an any-step success rate of \\ReacherLeWMOneAny\\% for LeWM; its final-step value, rank correlation, and AP reversal are provisional because the released termination path resets the arm after success and awaits the registered correction.',
    'With continuous post-success physics, LeWM reaches \\ReacherLeWMOneAny\\% any-step and \\ReacherLeWMOneFinal\\% final-step success in Reacher. The released termination path instead resets the arm after success, altering endpoint measurements.')
text=text.replace('under the any-step prefix comparison','under any-step success')
paragraph('A concrete held-out Reacher record',r'\IntroExampleSentence{} Any-step success asks whether a controller enters the target before the budget ends; final-step success asks whether it is in the target at the end. On the corrected held-out Reacher trajectories, one-frame LeWM achieves \ReacherLeWMOneAny\% and \ReacherLeWMOneFinal\%, respectively, while AP achieves \ReacherAPAny\% and \ReacherAPFinal\%. Within each method, both labels are calculated from the same trajectory.')
paragraph('The Reacher continuation values',r'Producing a continuous trajectory also requires checking what success does to the simulator. In the released Reacher implementation, success terminates the underlying dm\_control episode; another call to \texttt{step()} resets the arm. Clearing only the outer termination flag does not prevent this reset. We correct that path, verify unchanged actions through first success, and quantify the change in endpoint measurements. PushT supplies a separate comparison reversal on trajectories unaffected by this Reacher implementation issue.')
text=text.replace('; the Reacher reversal is held pending the termination correction','. The Reacher audit additionally exposes how internal termination changes endpoint measurements')
text=text.replace('A case and a planning stream define one paired unit; a protocol factor is changed at one interface at a time, and the resulting 50-step trajectory receives all three success labels.',
    'A case-stream identifies a paired trajectory; the case is the bootstrap unit. The right panel shows a corrected continuous Reacher trajectory, its two absolute joint errors and the 0.05 rad threshold. All three labels are derived after the full trajectory is recorded.')
text=text.replace('Audit flow from public checkpoints through paired cases and seed streams to three trajectory labels and held-out confirmation.',
    'Paired evaluation design and a continuous Reacher example with joint-error curves and success labels.')
paragraph('For Reacher, the current appendix values',r'For Reacher, we preserve the released strict per-joint condition $|q_j-q_j^*|<0.05$ rad but prevent success from terminating the underlying dm\_control episode during the 50-step budget. Both native microsteps are executed for every environment step. We record the original predicate at each microstep, the two step labels, physical time, joint position and velocity, target configuration, and actual reset events. Appendix~\ref{app:reacher-verification} reports the runtime checks and final-code technical gates.')
text=text.replace('the pending Reacher correction will additionally ensure that continuing after success cannot trigger an internal reset.',
    'the corrected Reacher implementation prevents success from triggering an internal reset.')
text=text.replace('emits a 25-step plan and executes a five-step action block before querying again; the next re-decision occurs after five executed blocks (raw steps 25 and 50).',
    'emits and executes a 25-step plan comprising five five-step action blocks, then queries again if budget remains. Steps 5, 10, \\ldots, 50 are action-block boundaries; 25 and 50 are endpoints of LeWM plans.')
text=text.replace('We therefore call 25 and 50 ``two 25-step plan endpoints\'\' and reserve ``re-decision boundary\'\' for every five-step AP query.',
    'An action-block boundary is therefore distinct from a re-decision boundary: LeWM re-decides after 25 steps, whereas AP re-decides after five.')
paragraph('Let $s_t$ indicate',r'Let $e_t$ denote the task predicate at the end of environment step $t$, and let $a_t$ denote whether it holds at any success check within that step. Reacher executes two microsteps, so $a_t$ is their logical OR and $e_t$ is the second microstep predicate; the other tasks use their released step-end check. Any-step success is $\mathbb{1}(\max_{1\leq t\leq50}a_t=1)$, block-boundary success is $\mathbb{1}(\max_{t\in\{5,10,\ldots,50\}}e_t=1)$, and final-step success is $e_{50}$. Occupancy is $100\times\Pr(e_t=1)$, with training-checkpoint and planning-stream averaging inside each case. The OR/end distinction is quantified in Appendix~\ref{app:reacher-verification}.')
paragraph('For method $m$, stream $s$, case $i$',r'For method $m$, checkpoint $k$, stream $s$, case $i$, and success definition $d$, let $Z_{ikmsd}\in\{0,1\}$ denote the label computed on one complete physical trajectory. Define $Y_{imsd}=K_m^{-1}\sum_{k=1}^{K_m}Z_{ikmsd}\in[0,1]$, where $K_m=3$ for AD-WM and $K_m=1$ otherwise. A nonlinear trajectory metric is calculated before checkpoint averaging; the averaged labels are not thresholded again. The estimand is the fixed-checkpoint, fixed-three-stream average over the case distribution, with the planning-stream mean formed inside each case:')
text=text.replace('The current Reacher final-step comparison (about 9\\% versus about 17\\%) is provisional because it includes the discovered post-success reset; it is not used as a conclusion.',
    'Under final-step success, corrected one-frame and three-frame LeWM achieve \\ReacherLeWMOneFinal\\% and \\ReacherLeWMThreeFinal\\%; their paired difference is \\ReacherHistoryFinalCI{} points.')
text=text.replace('while three-frame LeWM is \\ReacherAPVsThree{} points below AP.','\\ReacherAPHistoryComparisonSentence{}')
text=text.replace(', \\ReacherAPHistoryComparisonSentence{}','. \\ReacherAPHistoryComparisonSentence{}')
text=text.replace('The three preregistered predictions are supported on the held-out set (Table~\\ref{tab:predictions}).',
    '\\CorrectedPredictionSummary{} (Table~\\ref{tab:predictions}).')
text=text.replace('These Reacher intervals are the current pre-correction measurement and will be replaced after the registered termination fix. ', '')
text=text.replace('The Reacher final-step point is provisional pending the termination correction and is not a current claim. ',r'\ReacherCorrectedRankingSentence{} ')
text=text.replace("Reacher's any-step versus final-step value is provisional until the termination correction;",r"Reacher's any-step versus final-step value is \TauReacherAnyFinal;")
text=text.replace('Reacher curves are provisional until the termination correction; they are shown to document the discovered behavior, not as corrected performance. ',r'\ReacherOccupancySentence{} ')
text=text.replace('This timing pattern is consistent with the scoring-time failure mode described by Vesessook and Yang \\parencite{vesessook2026}.',
    'These curves describe external success timing. They do not isolate the planner-scoring mechanism studied by Vesessook and Yang \\parencite{vesessook2026}.')
text=text.replace('Each task has its own vertical scale so the low Reacher occupancy remains readable.',
    'Each task has its own vertical scale; Reacher uses the corrected step-end predicate.')
text=text.replace('Occupancy is the proportion of case-stream rows satisfying the task threshold at each step;',
    'Occupancy is the mean per-step predicate, averaging checkpoint and planning-stream indicators within each case;')
text=text.replace('Figure~\\ref{fig:occupancy} reports the proportion of rows occupying the target at each raw step.',
    'Figure~\\ref{fig:occupancy} reports the mean step-end predicate at each raw step, with checkpoint and stream averaging inside each case.')
text=text.replace('TwoRoom is comparatively stable: any-step and final-step rates and the method ordering are close, but some configurations leave and re-enter the target (for example, LeWM one-frame is inside at raw steps 25, 35, and 50 in the occupancy curve).',
    'TwoRoom is comparatively stable: any-step and final-step rates and the method ordering are close.')
text=text.replace("Block-boundary success asks the same question at the planner's execution boundaries.",
    'Block-boundary success asks the same question at the five-step action-block boundaries.')
text=text.replace("Reacher's current any-step measurement","Reacher's any-step success")
text=text.replace('(with the Reacher post-success comparison pending the registered termination correction)',
    'while the Reacher audit shows that internal resets can alter endpoint evaluation')
text=text.replace('Reacher rows are the current pre-correction audit values and will be replaced after the registered rerun.',
    'Reacher rows use corrected continuous trajectories and the sealed bootstrap seed; the original paired analyses for the other tasks are retained.')
text=text.replace('Reacher rows remain provisional until the corrected continuation semantics are run.',
    'Reacher rows use the corrected continuation semantics.')
text=text.replace('Reacher rows are provisional until the termination correction; the other task rows are unchanged by that correction.',
    'Metrics are calculated on each checkpoint trajectory before averaging streams and training seeds. A first hit at the last step has no subsequent observation and is excluded from the conditional exit denominator. The descriptive tables for all tasks use this same aggregation rule.')
anchor='\\subsection{Ranking reversals}'
assert text.count(anchor)==1
text=text.replace(anchor,r'''\subsection{Termination semantics change endpoint measurements}
The released Reacher task reports successful joint matching as a terminal dm\_control step. On a subsequent call, dm\_control resets the arm before executing another action. This behavior survives the outer full-budget wrapper that clears \texttt{terminated}. \ReacherRuntimeReplaySentence{} The corrected run suppresses this internal termination while keeping the predicate, dynamics, actions before first success, cases and checkpoints fixed.

\ReacherTerminationResultSentence{} Table~\ref{tab:reacher-correction} compares the old and corrected measurements; Table~\ref{tab:reacher-correction-contrasts} gives the paired AP contrasts and rank correlations. These are different rollout semantics, not merely different labels on one stored trajectory. The comparison includes both the reset correction and the explicit step-end convention; the separate OR/end table isolates label differences within the corrected trajectories.
\input{tables/table_reacher_termination_correction.tex}
\input{tables/table_reacher_termination_contrasts.tex}

'''+anchor)
anchor='\\section{Compute accounting}'
assert text.count(anchor)==1
text=text.replace(anchor,r'''\section{Reacher runtime verification}\label{app:reacher-verification}
\input{tables/table_reacher_runtime_checks.tex}
\input{tables/table_reacher_microstep_end.tex}
\input{tables/table_reacher_correction_timeline.tex}
The final code was fixed before the valid formal rerun. Earlier outputs produced before the numerical gates were complete are retained in the audit archive and excluded from every corrected estimate. The environment freeze matches the prior evaluation exactly and \texttt{pip check} reports no broken requirements. All final-code TECH trajectories save microstep predicates, both step labels, physical states, and actual reset observations; independent CPU replay verifies their physical continuity.

'''+anchor)
out=P/'revision3_part2/main.tex'
out.write_text(text)
ap_table=P/'revision3_part2/tables/table_ap_lewm_intervals.tex'
if ap_table.exists():
    ap_text=ap_table.read_text()
    ap_text=ap_text.replace('Reacher values are provisional until the registered termination correction.',
        'Reacher values use corrected continuous trajectories; intervals for the other tasks retain their original paired analyses.')
    ap_table.write_text(ap_text)
print(out)
