"""Generate revision-3 prediction table from sealed Step-4 contrasts.
No result number is typed into the generated table; all estimates and intervals are read
from the read-only sealed CSV.
"""
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / 'd1_execution' / 'step4' / 'resume_01' / 'results' / 'CONTRASTS.csv'
OUT = ROOT / 'tables' / 'table_predictions_revision.tex'
D = pd.read_csv(SRC)
TASK = {'reacher':'Reacher', 'pusht':'PushT', 'tworoom':'TwoRoom', 'cube':'Cube'}
METHOD = {'M01_h1':'Fast-LeWM', 'M03_h1':'Anchored Planning', 'M07_h1':'AD-WM'}

def get(analysis, task, contrast):
    q = D[(D.analysis == analysis) & (D.task == task) &
          (D.contrast == contrast) & (D.cohort == 'HELDOUT100') &
          (D.definition == 'any')]
    if len(q) != 1:
        raise ValueError((analysis, task, contrast, len(q)))
    return q.iloc[0]

def fmt(x):
    return f'{float(x):+.1f}'

def estimate(q):
    return f"{fmt(q.delta_pp)} [{fmt(q.ci95_low_pp)}, {fmt(q.ci95_high_pp)}]"

def tex(s):
    return str(s).replace('&', r'\&').replace('%', r'\%').replace('_', r'\_')

rows = []
# P1: Reacher threshold and three non-Reacher practical-equivalence cells.
for task in ['reacher', 'pusht', 'tworoom', 'cube']:
    q = get('main', task, 'LeWM_h3 - LeWM_h1')
    if task == 'reacher':
        criterion = r'$\widehat{\Delta}\geq+10$ pp and CI lower bound $>0$'
        ok = float(q.delta_pp) >= 10 and float(q.ci95_low_pp) > 0
    else:
        criterion = r'$|\widehat{\Delta}|\leq2$ pp (point-estimate rule)'
        ok = abs(float(q.delta_pp)) <= 2
    rows.append(('P1', TASK[task] + r' (3-frame $-$ 1-frame)', criterion, estimate(q), 'supported' if ok else 'not supported'))
# P2: Fast/AD lower-bound rule and AP point-estimate rule.
for contrast, label in [('LeWM_h3 - M01_h1', 'Fast-LeWM'),
                         ('LeWM_h3 - M07_h1', 'AD-WM'),
                         ('LeWM_h3 - M03_h1', 'Anchored Planning')]:
    q = get('C2', 'reacher', contrast)
    if label == 'Anchored Planning':
        criterion = r'$\widehat{\Delta}<0$ pp (point-estimate rule)'
        ok = float(q.delta_pp) < 0
    else:
        criterion = r'$\widehat{\Delta}\geq0$ pp and CI lower bound $>-5$ pp'
        ok = float(q.delta_pp) >= 0 and float(q.ci95_low_pp) > -5
    rows.append(('P2', 'Reacher: LeWM 3-frame $-$ ' + label, criterion, estimate(q), 'supported' if ok else 'not supported'))
# P3: four method/task gain cells, all requiring a positive CI lower bound.
for task, method in [('tworoom','M03_h1'), ('tworoom','M07_h1'),
                     ('cube','M03_h1'), ('cube','M07_h1')]:
    q = get('main', task, method + ' - LeWM_h1')
    criterion = r'CI lower bound $>0$ pp (gain rule)'
    ok = float(q.ci95_low_pp) > 0
    rows.append(('P3', TASK[task] + ': ' + METHOD[method] + ' $-$ LeWM 1-frame', criterion, estimate(q), 'supported' if ok else 'not supported'))

lines = [r'\begin{table*}[t]',
         r'\centering',
         r'\caption{Preregistered prediction checks, with one row for each independent subcondition on the held-out case set. Estimates are paired percentage-point differences with 95\% case-bootstrap intervals. The rule is evaluated exactly as stated in the preregistration; no Reacher post-success continuation quantity enters these any-step rows.}',
         r'\label{tab:predictions}',
         r'\scriptsize',
         r'\begin{tabularx}{\textwidth}{@{}c p{4.1cm} p{5.0cm} p{2.3cm} c@{}}',
         r'\toprule Prediction & Subcondition & Preregistered rule & Estimate [95\% CI] & Result\\',
         r'\midrule']
for p, sub, rule, est, verdict in rows:
    lines.append(f'{p} & {tex(sub)} & {rule} & {est} & {verdict} \\\\')
lines += [r'\bottomrule', r'\end{tabularx}', r'\end{table*}', '']
OUT.write_text('\n'.join(lines), encoding='utf-8')
print(f'wrote {OUT} ({len(rows)} rows) from {SRC}')
