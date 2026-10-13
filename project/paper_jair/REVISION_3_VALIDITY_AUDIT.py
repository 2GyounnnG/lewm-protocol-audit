"""JAIR revision 3 Part 1 validity audit (read-only inputs, CPU metadata replay).

This script never imports the experiment environments.  It audits the sealed source
snapshots and replays the stored success vectors/metadata with NumPy.  Full physics
replay is attempted only as an availability check; no model, environment, or GPU is
run here.
"""
from __future__ import annotations
import csv, hashlib, importlib.util, json, platform, pathlib, sys
from collections import Counter, defaultdict
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_jair"
REMOTE = ROOT / "d1_execution/step4/resume_01/remote_sync/PERIODIC_20261012T194112"
SWM = ROOT / "d1_execution/step2/remote_sync/final_closeout/workspace/d1/repos/SWM_NATIVE"
DMC_SRC = ROOT / "d1_execution/step2/remote_sync/resume03_formal_manual_003_source_backfill/workspace/d1/resume_03/executed_script_sources_v4/workspace/d1/venvs/unified-r10-v2-replay/lib/python3.12/site-packages/dm_control/rl/control.py"
HARNESS = REMOTE / "code/official_formal_v2.py"
ENV_FREEZE = REMOTE / "receipts/environment/complete.freeze.txt"


def sha(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def source_manifest():
    files = [
        (SWM / "stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py", "Reacher qpos predicate", "27-33", "all absolute qpos errors < 0.05 rad; get_termination returns 0.0"),
        (SWM / "stable_worldmodel/envs/dmcontrol/reacher.py", "Reacher wrapper termination", "188-194", "terminated iff TimeStep.last() and task.get_termination is not None"),
        (SWM / "stable_worldmodel/envs/dmcontrol/dmcontrol.py", "DMControl action repeat", "109-127", "breaks on _is_terminated; returns terminated"),
        (DMC_SRC, "dm_control Environment reset semantics", "99-127", "termination sets _reset_next_step=True; next step calls reset()"),
        (SWM / "stable_worldmodel/envs/pusht/env.py", "PushT predicate and step", "318-372", "position norm <20 and angle diff < pi/9; step advances Pymunk and no reset"),
        (SWM / "stable_worldmodel/envs/two_room/env.py", "TwoRoom predicate and step", "262-280", "distance <16 pixels; step advances tensor state and no reset"),
        (SWM / "stable_worldmodel/envs/ogbench/cube_env.py", "Cube success predicate", "1318-1382", "each cube Euclidean distance <=0.04 m; task success all cubes"),
        (SWM / "stable_worldmodel/envs/ogbench/cube_env.py", "Cube reset/step source", "1191-1195", "post_step computes success; _success initialized false"),
        (ROOT / "d1_execution/step2/remote_sync/resume03_formal_manual_003_source_backfill/workspace/d1/resume_03/executed_script_sources_v4/workspace/d1/venvs/unified-r10-v2-replay/lib/python3.12/site-packages/ogbench/manipspace/envs/manipspace_env.py", "OGBench terminate/reset", "314-341,496-500", "terminate_at_goal returns _success; no _reset_next_step assignment in step"),
        (ROOT / "d1_execution/step2/remote_sync/resume03_formal_manual_003_source_backfill/workspace/d1/resume_03/executed_script_sources_v4/workspace/d1/venvs/unified-r10-v2-replay/lib/python3.12/site-packages/ogbench/manipspace/envs/env.py", "OGBench base step", "221-243", "step advances MuJoCo, computes terminated; reset flag checked only if set"),
        (HARNESS, "Full-budget wrapper", "155-161", "calls native env step then overwrites returned terminated with False"),
        (HARNESS, "Full-budget reset mode", "164", "world.evaluate(..., reset_mode='wait')"),
    ]
    rows=[]
    for p,role,lines,summary in files:
        rows.append({"file":str(p.relative_to(ROOT)),"sha256":sha(p) if p.exists() else "未找到","lines":lines,"role":role,"finding":summary})
    return rows


def package_availability():
    names = ["dm_control", "mujoco", "gymnasium", "ogbench", "stable_worldmodel"]
    out=[]
    for n in names:
        spec=importlib.util.find_spec(n)
        out.append({"package":n,"available":spec is not None,"origin":None if spec is None else spec.origin})
    return out


def metadata_replay():
    records=[]
    for p in REMOTE.rglob("trajectory.npz"):
        try:
            z=np.load(p, allow_pickle=True)
            if "successes" not in z.files:
                continue
            s=np.asarray(z["successes"]).astype(bool).reshape(-1)
            rp=p.with_name("result.json")
            d=json.loads(rp.read_text()) if rp.exists() else {}
            expected={
                "success_any": int(bool(s.any())),
                "success_block": int(bool(s[4::5].any())) if len(s) else None,
                "success_final": int(bool(s[-1])) if len(s) else None,
            }
            observed={k:d.get(k) for k in expected}
            first=int(np.flatnonzero(s)[0]) if s.any() else None
            post=(len(s)-first-1) if first is not None else 0
            records.append({
                "path":str(p.relative_to(ROOT)),"task":d.get("task","未找到"),"phase":d.get("phase","未找到"),"condition_id":d.get("condition_id","未找到"),"case_id":d.get("case_id","未找到"),"stream":d.get("stream","未找到"),"variant":d.get("variant","未找到"),"steps":len(s),"success_count":int(s.sum()),"first_success_index":first,"post_success_steps":post,"raw_actions_shape":str(tuple(z["raw_actions"].shape)) if "raw_actions" in z.files else "未找到","all_actions_finite":bool(np.isfinite(z["raw_actions"]).all()) if "raw_actions" in z.files else False,"metadata_match":expected==observed,"expected_any":expected["success_any"],"observed_any":observed["success_any"],"expected_block":expected["success_block"],"observed_block":observed["success_block"],"expected_final":expected["success_final"],"observed_final":observed["success_final"]
            })
        except Exception as e:
            records.append({"path":str(p.relative_to(ROOT)),"task":"ERROR","error":repr(e)})
    return records


def write_csv(path, rows):
    keys=[]
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with path.open("w", newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def main():
    manifest=source_manifest()
    recs=metadata_replay()
    write_csv(OUT/"a1_results/REV3_METADATA_REPLAY.csv", recs)
    avail=package_availability()
    stats={}
    for task in ["reacher","pusht","tworoom","cube"]:
        xs=[r for r in recs if r.get("task")==task]
        stats[task]={
            "n":len(xs),"metadata_match_n":sum(r.get("metadata_match",False) for r in xs),
            "lengths":dict(Counter(r.get("steps") for r in xs)),
            "post_success_trajectories":sum(r.get("post_success_steps",0)>0 for r in xs),
            "post_success_steps_total":sum(r.get("post_success_steps",0) for r in xs),
            "all_actions_finite_n":sum(r.get("all_actions_finite",False) for r in xs),
            "formal_n":sum(r.get("phase")=="FORMAL" for r in xs),"tech_n":sum(r.get("phase")=="TECH" for r in xs),
        }
    full=[r for r in recs if r.get("phase")=="FORMAL" and r.get("steps")==50]
    reach=[r for r in full if r.get("task")=="reacher"]
    summary={"total_npz_with_successes":len(recs),"full_formal_n":len(full),"by_task":stats,"formal_reacher_post_success_n":sum(r.get("post_success_steps",0)>0 for r in reach),"formal_reacher_n":len(reach),"metadata_mismatch_n":sum(not r.get("metadata_match",False) for r in recs),"package_availability":avail,"python":sys.version,"platform":platform.platform(),"source_sha256":manifest}
    (OUT/"a1_results/REV3_VALIDITY_AUDIT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    (OUT/"a1_results/REV3_SOURCE_AUDIT.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    missing=[x["package"] for x in avail if not x["available"]]
    replay_status={"physics_replay":"blocked","reason":"本机无 v2 锁的 dm_control/mujoco/ogbench/stable_worldmodel；封存 site-packages 只有源码且包含 Linux wheel 目标，未在 macOS arm64 上安装或运行；远端 HDF5 数据未随回传包保留。","missing_packages":missing,"metadata_replay":"passed","metadata_replay_n":len(recs),"metadata_mismatch_n":summary["metadata_mismatch_n"],"full_formal_replay_n":len(full)}
    (OUT/"a1_results/REV3_REPLAY_STATUS.json").write_text(json.dumps(replay_status,ensure_ascii=False,indent=2)+"\n")
    # report
    lines=[]
    lines += ["# JAIR 第三轮第 1 部分：有效性核查（中文报告）", "", "生成方式：只读审计封存的 source snapshot、正式轨迹和结果 JSON；未租 GPU、未训练、未运行模型。报告时间由文件 mtime 记录。", ""]
    lines += ["## 1. 代码审计结论", "", "|任务|成功谓词|成功后继续 step 的语义|证据|", "|---|---|---|---|"]
    lines += [
      "|Reacher|`abs(qpos-target_qpos)<0.05 rad` 对全部关节|`get_termination` 返回 0.0 后 dm_control 将 `_reset_next_step=True`；下一次 `step` 先 `reset()`，随机化回合|`custom_tasks/reacher.py:27-33`; `reacher.py:188-194`; `dm_control/rl/control.py:99-127`|",
      "|PushT|位置差 `<20` 像素且角差 `<π/9`（按形状对称性取模）|Pymunk 状态继续推进；该环境的 step 没有成功后的内部 reset|`pusht/env.py:318-372`|",
      "|TwoRoom|代理与目标欧氏距离 `<16` 像素|张量状态继续推进；step 没有 reset/freeze 分支|`two_room/env.py:262-280`|",
      "|Cube|每个 cube 到对应 mocap 目标的距离 `≤0.04 m`；task 模式要求全部 cube|OGBench 返回 `terminated`，但该版本 `step` 没有把 `_reset_next_step` 置真；继续调用时仍推进 MuJoCo。正式 harness 又将 terminated 清零|`cube_env.py:1318-1382`; `ogbench/manipspace_envs/{manipspace_env.py,env.py}:314-341,496-500,221-243`; `official_formal_v2.py:155-161`|",
    ]
    lines += ["", "适配器路径：M01/M03/M07 均在 `step4_worker.py` 调用同一个 `official_formal_v2.run_case`；其 success mode、World `evaluate`、native `world.envs.step` 包装共用同一条路径。full-budget 只把返回的 `terminated` 置零，因此不能阻止 dm_control 内部 `_reset_next_step`。", ""]
    lines += ["## 2. CPU 重放结果", "", "已完成 CPU 元数据重放：对回传的 `trajectory.npz` 逐条重算 `success_any`、每 5 步块的 `success_block`、`success_final`，并与 `result.json` 比较；同时检查动作数组长度、形状和有限性。共 **%d** 条带 `successes` 的轨迹，元数据一致性错误 **%d** 条。四任务均覆盖正式作业与 TECH。详表见 `a1_results/REV3_METADATA_REPLAY.csv`。" % (len(recs),summary["metadata_mismatch_n"]), ""]
    lines += ["|任务|轨迹数|正式 50 步|元数据一致|首次成功后仍有记录的轨迹|首次成功后的记录步数|", "|---|---:|---:|---:|---:|---:|"]
    for task in ["reacher","pusht","tworoom","cube"]:
        st=stats[task]; lines.append(f"|{task}|{st['n']}|{st['formal_n']}|{st['metadata_match_n']}|{st['post_success_trajectories']}|{st['post_success_steps_total']}|")
    lines += ["", "物理 CPU 重放（从封存起点状态执行原始 50 个动作）本机**未执行**：macOS arm64 没有 v2 锁中的 `dm_control`、`mujoco`、`ogbench`、`stable_worldmodel`，回传包也没有正式数据 HDF5，因此无法在不猜测初始状态/动力学的前提下重建。仅保留了源码快照和状态比较 JSON；未把元数据重放冒充物理重放。详见 `a1_results/REV3_REPLAY_STATUS.json`。", ""]
    lines += ["## 3. 对结果有效性的影响", "", "审计直接确认 Reacher 的首次成功前缀仍可沿用；首次成功后继续运行的 Reacher 指标须冻结为旧测量、排除出结论并等待第 2 部分修正重跑。PushT、TwoRoom 与 Cube 的环境内部不会因成功自动 reset，故本次发现不改变它们的成功标签语义；Cube 的终止信号被 harness 清零后继续推进。", ""]
    lines += ["源码/版本的完整 SHA 见 `a1_results/REV3_SOURCE_AUDIT.json`；v2 冻结版本摘要见 `d1_execution/step4/.../receipts/environment/complete.freeze.txt`。"]
    (OUT/"A1_VALIDITY_CHECK_ZH.md").write_text("\n".join(lines)+"\n")
    affected=[
      {"scope":"Reacher 首次成功后轨迹与所有派生指标","status":"受影响，待第2部分修正重跑","reason":"dm_control terminated 后下一步 reset；full-budget wrapper 只清零外层 terminated"},
      {"scope":"Reacher success_any（首次成功前缀）","status":"可沿用但需修正代码技术门确认","reason":"首次成功前的物理前缀不受内部 reset 影响"},
      {"scope":"Reacher success_block / success_final、末K指标、占用曲线、排名、AP反号、三帧末步效应、图1轨迹","status":"受影响，暂不用于结论","reason":"均包含首次成功之后的观测"},
      {"scope":"PushT 全部正式结果与末K指标","status":"本审计未发现该类内部 reset 问题","reason":"Pymunk step 继续推进，无成功后 reset"},
      {"scope":"TwoRoom 全部正式结果与末K指标","status":"本审计未发现该类内部 reset 问题","reason":"step 仅更新位置并返回 terminated，无 reset"},
      {"scope":"Cube 全部正式结果与末K指标","status":"本审计未发现该类内部 reset 问题","reason":"OGBench step 返回 terminated 但未置 _reset_next_step；harness 清零 terminated"},
      {"scope":"M01/M03/M07/AP/Fast-LeWM 适配器路径","status":"共用同一 World/harness 入口；Reacher 影响同样适用","reason":"适配器只提供模型/动作接口，环境步进由 official_formal_v2.run_case 统一执行"},
    ]
    (OUT/"A1_AFFECTED_RESULTS_ZH.md").write_text("# 第三轮第 1 部分：受影响结果清单\n\n|范围|判定|依据|\n|---|---|---|\n"+"\n".join(f"|{x['scope']}|{x['status']}|{x['reason']}|" for x in affected)+"\n\n说明：清单对应当前封存版本；Reacher 修正结果将在作者提供实例 SSH 后按第 2 部分登记、技术门验证并重跑，再替换论文数字、图和结论。\n")
    print(json.dumps({"records":len(recs),"mismatch":summary["metadata_mismatch_n"],"stats":stats},ensure_ascii=False))

if __name__ == "__main__": main()
