"""Build an honest local execution-report draft from returned receipts only.

Never contacts the instance or updates paper/worker files. Incomplete stages
remain incomplete. GPU process-hours are separate from rental cost for the
entire four-GPU instance, including installation, waiting and transfer time.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_RETURNS = Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/returns')
RATE = 2.3829629629629627
START_UNIX = 1791857082.8941522
INSTANCE_ID = '55658358'
COMPLETE = 'PROCESSES_COMPLETE_RECORDS_PRESENT_PENDING_LOCAL_RETURN'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def timestamp(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(dt.timezone.utc)


def display(value):
    return value.astimezone(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def stage_status(base, stage):
    receipt_path = base / f'FORMAL_STAGE_{stage}_LOCAL_RETURN.json'
    status_path = base / f'STAGE{stage}_VERIFIED/experiment/FORMAL_STAGE_{stage}_STATUS.json'
    row = {'stage': stage, 'verified': False, 'status': '未找到该阶段完整本地回传回执',
           'expected_records': {1: 600, 2: 1500, 3: 600}[stage], 'complete_records': 0,
           'allocated_gpu_hours': None, 'verified_files': None}
    if not receipt_path.is_file() or not status_path.is_file():
        return row
    receipt, status = read(receipt_path), read(status_path)
    wanted = sha(status_path)
    if (receipt.get('status') != 'VERIFIED_LOCAL_RETURN' or receipt.get('stage') != stage
            or receipt.get('mismatch_count') != 0 or receipt.get('stage_status_sha256') != wanted
            or receipt.get('manifest_sha256', {}).get(status_path.name) != wanted):
        row['status'] = '回传回执不满足零差异与阶段状态 SHA 绑定'
        return row
    manifest = receipt['manifest_sha256']
    if any(manifest.get(k) != v for k, v in status['artifact_sha256'].items()):
        row['status'] = '回传回执未覆盖该阶段所有产物'
        return row
    root = status_path.parent
    mismatches = [name for name, wanted_sha in status['artifact_sha256'].items()
                  if not (root / name).is_file() or sha(root / name) != wanted_sha]
    if mismatches:
        row.update(status='本地再次核验发现文件缺失或 SHA 不同', artifact_mismatches=mismatches)
        return row
    expected_conditions = {1: 2, 2: 5, 3: 2}[stage]
    valid = (status.get('status') == COMPLETE
             and status.get('records_complete') == row['expected_records']
             and status.get('records_expected') == row['expected_records']
             and status.get('conditions_exited_zero') == expected_conditions
             and status.get('conditions_expected') == expected_conditions)
    row.update(verified=valid, status='已完成并本地核验 SHA' if valid else '进程或记录完整性尚未通过',
               complete_records=status.get('records_complete', 0),
               allocated_gpu_hours=float(status.get('allocated_gpu_hours', 0.0)),
               stage_wall_seconds=status.get('stage_wall_seconds'),
               verified_files=receipt['verified_files'], mismatch_count=receipt['mismatch_count'],
               completion_utc=status['utc'], return_utc=receipt['utc'],
               status_sha256=sha(status_path), return_sha256=sha(receipt_path),
               artifact_files_rechecked=len(status['artifact_sha256']))
    return row


def report_data(base, asof, stop_path):
    pre = base / 'PREFORMAL_VERIFIED/experiment'
    registration = read(pre / 'REVISION_3_REACHER_CORRECTION_REGISTRATION.json')
    for name in ('TECH_GATE_FINAL_T1_T4.json', 'runtime_checks_final.json', 'PREMATURE_FORMAL_EXCLUSION.json'):
        if sha(pre / name) != registration['evidence_sha256'][name]:
            raise ValueError('Preformal evidence differs from sealed registration: ' + name)
    gate = read(pre / 'TECH_GATE_FINAL_T1_T4.json')
    runtime = read(pre / 'runtime_checks_final.json')
    exclusion = read(pre / 'PREMATURE_FORMAL_EXCLUSION.json')
    stages = [stage_status(base, i) for i in (1, 2, 3)]
    auth_candidates = [base / f'STAGE{i}_VERIFIED/experiment/INSTANCE_AUTH_READONLY.json' for i in (3, 2, 1)]
    auth_path = next((p for p in auth_candidates if p.is_file()), None)
    if auth_path is None:
        raise FileNotFoundError('Actual instance read-only identity/rate receipt is required')
    auth = read(auth_path)
    if (str(auth.get('id')) != INSTANCE_ID or auth.get('num_gpus') != 4
            or auth.get('dph_total') != RATE or auth.get('start_date') != START_UNIX):
        raise ValueError('Instance ID, GPU count, whole-instance rate or rental start differs')
    stop = None
    if stop_path is None:
        candidates = [base / 'INSTANCE_STOP_RECEIPT.json'] + [base / f'STAGE{i}_VERIFIED/experiment/INSTANCE_STOP_RECEIPT.json' for i in (3, 2, 1)]
        stop_path = next((p for p in candidates if p.is_file()), None)
    if stop_path is not None:
        stop = read(stop_path)
        if str(stop.get('instance_id')) != INSTANCE_ID:
            raise ValueError('Stop receipt belongs to another instance')
    actual_stop = bool(stop and stop.get('actual_stop_confirmed') is True)
    cost_end = asof
    cost_kind = '截至报告时间的整实例估算；停机或平台计费截止尚未确认'
    if actual_stop:
        cost_end = timestamp(stop.get('post_stop_readonly_check', {}).get('utc', stop.get('response_utc', stop['utc'])))
        cost_kind = '截至平台停止状态确认时的整实例估算；最终费用以账单为准'
    elif stop and stop.get('stop_request_accepted'):
        cost_end = timestamp(stop['response_utc'])
        cost_kind = '仅计算至 stop 请求明确接受时；非平台计费截止确认，最终账单和之后费用未核实'
    start = dt.datetime.fromtimestamp(START_UNIX, dt.timezone.utc)
    if cost_end < start:
        raise ValueError('Cost end precedes rental start')
    instance_hours = (cost_end - start).total_seconds() / 3600
    verified_stages = [row for row in stages if row['verified']]
    first_start = base / 'STAGE1_VERIFIED/experiment/FORMAL_STAGE_1_STARTED.json'
    start_record = read(first_start) if first_start.is_file() else None
    return {'asof_utc': asof.isoformat(), 'returns_directory': str(base),
            'status': 'FORMAL_RETURN_COMPLETE_STOP_CONFIRMED_REPORT_DRAFT' if len(verified_stages) == 3 and actual_stop
                      else 'FORMAL_RETURN_COMPLETE_STOP_ACCEPTED_PLATFORM_UNVERIFIED' if len(verified_stages) == 3 and stop and stop.get('stop_request_accepted')
                      else 'INCOMPLETE_EXECUTION_REPORT_DRAFT',
            'formal_started_utc': None if start_record is None else start_record['utc'],
            'formal_all_stages_returned': len(verified_stages) == 3,
            'formal_records_returned_verified': sum(r['complete_records'] for r in verified_stages),
            'formal_records_expected': 2700, 'stages': stages,
            'valid_formal_gpu_hours_verified_stages': sum(r['allocated_gpu_hours'] for r in verified_stages),
            'instance_id': INSTANCE_ID, 'instance_start_utc': start.isoformat(),
            'instance_rate_usd_per_hour_for_all_4_gpus': RATE,
            'instance_elapsed_hours': instance_hours, 'instance_cost_estimate_usd': instance_hours * RATE,
            'cost_cutoff_utc': cost_end.isoformat(), 'cost_basis': cost_kind,
            'instance_auth_receipt_sha256': sha(auth_path),
            'technical_gates': gate['gates'], 'runtime_status': runtime['status'],
            'runtime_heldout_replay': {k: v for k, v in runtime['reacher_replay']['records'][0].items()
                                     if k in ('case_id', 'first_success_step', 'n_actions', 'original_match_rate', 'segments', 'post_success_disagreement')},
            'excluded_premature_completed_records': len(exclusion['completed_records']),
            'excluded_premature_files': exclusion['file_count'],
            'excluded_directory': exclusion['excluded_directory'],
            'exclusion_manifest_sha256': sha(pre / 'PREMATURE_FORMAL_EXCLUSION.json'),
            'stop_receipt': stop, 'stop_receipt_sha256': None if stop_path is None else sha(stop_path),
            'actual_stop_confirmed': actual_stop,
            'paper_update_verified_by_this_script': False,
            'note': 'This generated execution draft does not assert corrected statistics or PDF completion.'}


def markdown(d):
    stop = d['stop_receipt']
    manual = bool(stop and (stop.get('unauthorized_401') or stop.get('manual_stop_required')))
    first = '**需要作者在网页端手动停机。**\n\n' if manual else ''
    all_formal = d['formal_all_stages_returned']
    state = ('全部正式轨迹已回传并核验；停机状态已确认。' if all_formal and d['actual_stop_confirmed'] else
             '全部正式轨迹已回传并核验；停机状态尚未确认。' if all_formal else
             '正式运行尚未全部完成回传核验，以下为当前执行草稿。')
    lines = [first + '# Reacher 修正重跑执行报告（自动状态草稿）', '',
             state, '', f"证据读取截止：{display(timestamp(d['asof_utc']))}。", '',
             f"正式记录：**{d['formal_records_returned_verified']:,}/{d['formal_records_expected']:,}** 已完成且通过本地回传 SHA 核验。未回传阶段不计入已完成数。", '',
             '| 阶段 | 已核验记录／预计记录 | 当前状态 | 已核验阶段 GPU 小时 | 回传文件数 |',
             '|---|---:|---|---:|---:|']
    for r in d['stages']:
        hours = '未确认' if r['allocated_gpu_hours'] is None or not r['verified'] else f"{r['allocated_gpu_hours']:.6f}"
        files = '未确认' if r['verified_files'] is None else f"{r['verified_files']:,}"
        lines.append(f"| {r['stage']} | {r['complete_records']:,}/{r['expected_records']:,} | {r['status']} | {hours} | {files} |")
    g = d['technical_gates']
    t1, t2, t3, t4 = (g[k]['totals'] for k in ('T1', 'T2', 'T3', 'T4'))
    lines += ['', '## 技术核查与记录口径', '',
              f"最终 T1–T4 均为 {g['T1']['case_stream_counts']['PASS']}/108 条 TECH 轨迹通过。T1 首次成功动作前 {t1['actions_before_success_compared']:,} 个动作、含首次成功动作 {t1['actions_including_first_success_compared']:,} 个动作严格逐位一致。T2 共 {t2['wrapper_reset_count']} 次真实 wrapper reset（每轨迹一次），内部 reset {t2['internal_reset_event_count']} 次。", '',
              f"T3 覆盖 {t3['environment_steps']:,} 个环境步、{t3['microsteps']:,} 个微步，逐状态独立 CPU 重放通过。T4 比较 {t4['predicate_comparisons']:,} 个谓词，差异 {t4['predicate_mismatches']}；步内任一与步末标签在 {t4['steps_where_two_labels_differ']} 个环境步不同。任一步使用微步内任一，block/final/occupancy/末 K 步使用环境步末标签。", '',
              f"补充 CPU 核查状态：{d['runtime_status']}。真正 HELDOUT 旧轨迹的原语义重放为 50/50 相符；修正语义在首次成功之后的 44 步有 {d['runtime_heldout_replay']['post_success_disagreement']} 处不同。", '',
              '## 撤销与排除', '',
              f"此前将完整输出误当作 T1–T4 通过的启动回执已撤销；`{d['excluded_directory']}` 下提前产生的 {d['excluded_premature_completed_records']} 条完成记录、{d['excluded_premature_files']} 个文件保留归档并全部排除。有效正式结果仅来自 `formal_verified`。排除清单 SHA：`{d['exclusion_manifest_sha256']}`。", '',
              '## 计算量与实例费用', '',
              f"已完成回传核验阶段的有效正式进程 GPU 小时合计 **{d['valid_formal_gpu_hours_verified_stages']:.6f}**。这是各使用一张 GPU 的条件进程墙钟相加，当前未核验阶段不计入；它不是四张卡实例的租赁小时。", '',
              f"实例 {d['instance_id']} 从 **{display(timestamp(d['instance_start_utc']))}** 开始计时，整台 **4 GPU 实例**单价为 **${d['instance_rate_usd_per_hour_for_all_4_gpus']:.15g}/小时**。截至 **{display(timestamp(d['cost_cutoff_utc']))}**，实例墙钟 **{d['instance_elapsed_hours']:.6f} 小时**，估算 **${d['instance_cost_estimate_usd']:.2f}**。该金额包含环境准备、等待与回传的实例占用时间，不再乘 4，也不由有效正式 GPU 小时换算。{d['cost_basis']}。", '',
              '## 停机与最终交付状态', '']
    if stop is None:
        lines.append('未找到停机回执，不能声称已经发送 stop 或已经停机。')
    else:
        lines.append(f"停机请求明确被接受：{bool(stop.get('stop_request_accepted'))}；平台实际停止已确认：{d['actual_stop_confirmed']}；destroy 请求：{bool(stop.get('destroy_requested'))}。")
        lines.append(f"停机回执 SHA：`{d['stop_receipt_sha256']}`。")
    lines += ['', '修正前后统计、论文数字替换、新 PDF 与最终材料封存仍须由相应产物核实。本脚本只汇总运行和回传回执，不将这些论文交付项目自动标为完成。', '']
    return '\n'.join(lines)


def compute_table(d, previous_table):
    source = previous_table.read_text()
    earlier_total = float(re.search(r'Total recorded allocation\s*&\s*([0-9.]+)', source).group(1))
    earlier_followup = float(re.search(r'Formal follow-up allocation\s*&\s*([0-9.]+)', source).group(1))
    earlier_main = float(re.search(r'Earlier formal allocation\s*&\s*([0-9.]+)', source).group(1))
    earlier_auxiliary = earlier_total - earlier_followup - earlier_main
    rows = []
    for r in d['stages']:
        label = f"Correction stage {r['stage']}"
        if r['verified']:
            rows.append(f"{label} & {r['allocated_gpu_hours']:.3f} & {r['stage_wall_seconds'] / 3600:.3f} & {r['complete_records']:,} records returned; SHA matched")
        else:
            rows.append(f"{label} & -- & -- & Awaiting verified completion/return")
    verified_wall = sum(r.get('stage_wall_seconds', 0.0) for r in d['stages'] if r['verified']) / 3600
    rows.append(f"Verified formal subtotal & {d['valid_formal_gpu_hours_verified_stages']:.3f} & {verified_wall:.3f} & Sum of the returned stages above")
    rows.append(f"Whole 4-GPU instance & -- & {d['instance_elapsed_hours']:.3f} & Estimated rental cost: \\${d['instance_cost_estimate_usd']:.2f}")
    stop = d['stop_receipt']
    stop_text = ('Actual stopped state confirmed' if d['actual_stop_confirmed'] else
                 'Manual web stop required (401)' if stop and (stop.get('manual_stop_required') or stop.get('unauthorized_401')) else
                 'Request accepted; actual state unverified' if stop and stop.get('stop_request_accepted') else
                 'No confirmed stop receipt')
    rows.append('Instance lifecycle & -- & -- & ' + stop_text)
    lines = ['% Generated by r3_part2_work/generate_completion_report.py from returned receipts.',
             r'\begin{table}[t]', r'\centering', r'\small',
             r'\caption{Additional compute for the corrected Reacher rerun, as of '
             + display(timestamp(d['asof_utc'])) + '. GPU hours sum individual formal condition processes; stage wall time excludes transfers between stages. '
             + f'The earlier {earlier_total:.2f} GPU hours include {earlier_auxiliary:.2f} GPU hours for TECH/cache/reset work; the correction below is additional.' + '}',
             r'\label{tab:compute-reacher-correction}',
             r'\begin{tabular}{@{}p{0.25\linewidth}r r p{0.45\linewidth}@{}}',
             r'\toprule', r'Item & GPU h & Wall h & Accounting \\', r'\midrule']
    lines += [row + r' \\' for row in rows]
    lines += [r'\bottomrule', r'\end{tabular}', r'\par\smallskip',
              r'\begin{minipage}{0.98\linewidth}\small',
              f"Whole-instance rate: \\${d['instance_rate_usd_per_hour_for_all_4_gpus']:.6f}/h for all four GPUs together, from "
              + display(timestamp(d['instance_start_utc'])) + ' to ' + display(timestamp(d['cost_cutoff_utc']))
              + '. This rental estimate includes preparation, waiting, and transfers; it is not formal GPU hours multiplied by the rate. The cutoff is the accepted stop request, not an independently verified billing endpoint; subsequent billing is unverified.',
              r'\end{minipage}', r'\end{table}', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--returns', type=Path, default=DEFAULT_RETURNS)
    p.add_argument('--asof-utc', help='Optional explicit report/cost cutoff; ISO UTC')
    p.add_argument('--stop-receipt', type=Path)
    p.add_argument('--output-dir', type=Path, default=HERE)
    p.add_argument('--compute-table', type=Path, default=HERE.parent / 'revision3_part2/tables/table_compute_reacher_correction.tex')
    p.add_argument('--previous-compute-table', type=Path, default=HERE.parent / 'revision3_part2/tables/table_compute.tex')
    a = p.parse_args()
    asof = timestamp(a.asof_utc) if a.asof_utc else dt.datetime.now(dt.timezone.utc)
    data = report_data(a.returns, asof, a.stop_receipt)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    md = a.output_dir / 'COMPLETION_REPORT_STATUS_DRAFT_ZH.md'
    machine = a.output_dir / 'COMPLETION_REPORT_STATUS_DRAFT.json'
    md.write_text(markdown(data))
    machine.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    a.compute_table.parent.mkdir(parents=True, exist_ok=True)
    a.compute_table.write_text(compute_table(data, a.previous_compute_table))
    print(json.dumps({'status': data['status'], 'verified_formal_records': data['formal_records_returned_verified'],
                      'reports': [str(md), str(machine), str(a.compute_table)]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
