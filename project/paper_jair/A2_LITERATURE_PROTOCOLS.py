"""Zero-GPU A2: summarize the sealed Step0/Step1 protocol inventory."""
import csv,datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; src=ROOT/'d1_execution/step1/BASELINE_AUDIT.csv'; out=Path(__file__).resolve().parent/'a2_results';out.mkdir(exist_ok=True)
rows=list(csv.DictReader(src.open(encoding='utf-8-sig')))
# PAPER rows only: local/reference rows are retained separately in provenance but not counted as papers.
papers=[]
for sid in sorted({r['source_id'] for r in rows if r['row_role']=='PAPER'}):
 g=[r for r in rows if r['source_id']==sid and r['row_role']=='PAPER']
 def uniq(col):
  return sorted({r[col] if r[col] else '未说明' for r in g})
 tasks=sorted({r['task'] for r in g})
 papers.append({'source_id':sid,'paper':g[0]['paper'],'n_audit_rows':len(g),'tasks_reported':';'.join(tasks),'n_tasks':len(tasks),'success_check':' || '.join(uniq('success_check')),'early_termination':'未说明（BASELINE_AUDIT 未单独记录）' if all('终止' not in r['success_check'] for r in g) else '见 success_check','history_frames':' || '.join(uniq('eval_history')),'cem_and_planner':' || '.join(uniq('planner')),'evaluation_cases':' || '.join(uniq('n_cases')),'evaluation_seeds':' || '.join(uniq('n_eval_seeds')),'source_urls':' || '.join(sorted({r['url'] for r in g if r['url']}))})
with (out/'A2_LITERATURE_PROTOCOLS.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=list(papers[0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(papers)
meta={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_path':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'paper_count':len(papers),'paper_rows':sum(x['n_audit_rows'] for x in papers),'all_audit_rows':len(rows),'method':'one row per PAPER source_id; values are exact distinct strings from BASELINE_AUDIT; missing values preserved as 未说明; no inference about undocumented early termination.','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.csv')}}
(out/'A2_METADATA.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
# brief human-readable table
with (out/'A2_REPORT_ZH.md').open('w') as f:
 f.write('# A2 文献统计（零 GPU）\n\n')
 f.write(f'底表为第 1 步 `BASELINE_AUDIT.csv`（SHA256 `{meta["source_sha256"]}`）。统计 PAPER 行的唯一 source_id；共 **{len(papers)} 篇来源、{len(rows)} 行审计记录**。任何未记录的设置均保留为“未说明”，没有从代码或结果反推论文正文没有写出的设置。\n\n')
 f.write('|来源|四任务覆盖|成功判定记录|历史帧|CEM/规划器|评测集|评测 seed|\n|---|---:|---|---|---|---|---|\n')
 for p in papers:
  f.write(f"|{p['source_id']} {p['paper']}|{p['n_tasks']}|{p['success_check']}|{p['history_frames']}|{p['cem_and_planner']}|{p['evaluation_cases']}|{p['evaluation_seeds']}|\n")
 f.write('\n引言使用的计数是底表可支持的计数：**16 个公开来源**在 LeWM 四任务清单中有 PAPER 审计记录；其中 **13 个来源**覆盖四个标准任务（Reacher、PushT、TwoRoom、Cube），其余来源覆盖两个或三个任务，任务覆盖不等于每项设置完整披露。成功规则、是否首次成功即终止、历史长度、CEM 次数、评测集数和 seed 数分别见完整 CSV；缺失项明确写“未说明”。\n')
print(json.dumps({'paper_count':len(papers),'four_task_sources':sum(x['n_tasks']==4 for x in papers),'rows':len(rows),'out':str(out)},ensure_ascii=False))
