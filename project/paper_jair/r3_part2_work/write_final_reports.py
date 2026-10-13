from pathlib import Path
import json,csv,datetime,hashlib
W=Path(__file__).resolve().parent;P=W.parent/'revision3_part2';A=W/'analysis_final';R=Path('/Volumes/MyProj/d1_reacher_revision3_part2_20261013/returns')
def read(p):return json.loads(p.read_text())
def csvs(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
execd=read(W/'execution_report_final_v2/COMPLETION_REPORT_STATUS_DRAFT.json');am=read(A/'ANALYSIS_MANIFEST.json');assets=read(W/'paper_assets_final_v2/PAPER_ASSETS_MANIFEST.json');now=datetime.datetime.now(datetime.timezone.utc).isoformat()
rates=csvs(A/'ABSOLUTE_RATES.csv');changes=csvs(A/'OLD_VS_CORRECTED.csv');cons=csvs(A/'CONTRASTS.csv')
assert all(float(r['delta_pp'])==0 for r in changes if r['metric']=='any')
# Use generated macro strings for the identical paper/report contrasts.
m=assets['new_macro_values']
text=f'''# JAIR Revision 3 Part 2 中文完成报告

生成 UTC：{now}。本报告接续旧 Revision 3 核查报告；旧稿、旧封存目录和错误轨迹均保留。

## 完成范围与核心结论

Reacher 全部 **{am['corrected_trajectories']} 条正式轨迹**完成：9 条件 × 100 个相同留出 case × A–C 三流，涵盖 LeWM 一／三帧、CEM 30／10 次、Fast-LeWM、AP、AD-WM 三个公开 checkpoint。正式数据仅使用 `formal_verified`，全部 9,300 个相关文件先封存后分析；最终回传快照共 **11,739 文件，SHA 零差异**。

修正明确取消了底层成功终止所导致的隐式 reset。任一步口径取逐微步 OR；块边界、末步、占用曲线和末 K 步取第二微步 END。全部正式轨迹保留 tracker.events、OR 和 END 两套标签、每环境步 physics.time/qpos/qvel/target_qpos、reset 计数及 internal_reset_events。旧 `successes` 字段不能用于新的 END 指标。

- LeWM 一帧任一步 **{m['ReacherLeWMOneAny']}%**、最后一步 **{m['ReacherLeWMOneFinal']}%**；AP 分别 **{m['ReacherAPAny']}% / {m['ReacherAPFinal']}%**。
- 三帧历史任一步增益 **{m['ReacherHistoryCI']} pp**。三条预登记预测的 **{len(assets['prediction_subconditions'])} 个子条件全部满足**；成功时刻反号属于描述性分析，不是这些预测之一。
- AP − 一帧 LeWM：任一步 **{m['APLeWMReacherAnyCI']} pp**、末步 **{m['APLeWMReacherFinalCI']} pp**。因此旧 Reacher AP／一帧反号消失；同一 bootstrap 的“末步差 − 任一步差”为 **{m['APLeWMReacherChangeCI']} pp**。
- 修正后的三帧 LeWM 与 AP 仍出现成功时刻反号（数值列于下表）；PushT 的反号保留，标题可继续使用 *Same Trajectories, Different Rankings*，最终标题由作者定。
- 所有已比较 Reacher 配置的任一步率修正前后相同；首次成功后的派生量统一替换。对旧／新末步变化的解释同时包含取消 reset 与明确 END 口径，不能全部归因于 reset。另表在相同修正轨迹内隔离 OR／END 标签差。

| 三帧 LeWM − AP | 差值及 95% 配对区间（pp） |
|---|---:|
'''
for d in ['any','final']:
 r=next(r for r in cons if r['contrast']=='LeWM_h3 - M03_h1' and r['definition']==d)
 text+=f"| {d} | {float(r['delta_pp']):+.2f} [{float(r['ci95_low_pp']):+.2f}, {float(r['ci95_high_pp']):+.2f}] |\n"
text+='''
## 技术门与运行时核查

最终记录代码重跑 TECH，T1–T4 均为 **108/108 PASS**，不是仅凭进程退出或输出完整判定：

| 门 | 数字证据 | 判定 |
|---|---|---|
| T1 动作前缀 | 首次成功之前 3,397 动作；含首次成功动作 3,497；逐位差异 0 | PASS |
| T2 reset | wrapper/dm_control/initialize 每轨迹各 1 次；internal reset 0；pending reset 微步 0 | PASS |
| T3 物理连续性 | 5,400 环境步／10,800 微步；每微步 0.02 s；独立 CPU 重放各状态／时间／目标最大误差 0，容差 1e−12 | PASS |
| T4 谓词与两套标签 | 10,800 谓词比较，0 不一致；OR／END 在 78 个环境步不同；派生指标按登记核对 | PASS |

补充 §2 的两项运行时核查均通过：

1. 四环境继续运行：原版 Reacher 成功后内部重置；补丁 Reacher、PushT、TwoRoom 保持记录的状态连续性；Cube 在成功后继续推进物理时间。Cube 证据范围是继续推进测试，不能写成完整四任务逐动作物理重放。
2. 同一旧 HELDOUT Reacher 轨迹的 50 个原始动作双重放：原语义 **50/50** 标签复现；补丁语义到首次成功为 **6/6** 一致，其后 **36/44** 一致、**8/44** 不同。由于补丁完整执行第二微步，不能宣称首次成功环境步的末状态也逐位相同。

环境为 Python 3.12.3、4×RTX 4090、驱动 595.84、CUDA 12.8；与最终 v2 冻结清单逐项核对，pip check 无冲突。未训练或租新卡。

## 时间线、排除与回传

有效登记和正式启动前的完整时间线及 SHA 前缀见论文附录 F。曾把输出完整误判为技术门通过而提前产生的 **33 条完成记录／133 文件**已保留归档、撤销其启动回执并全部排除；本次所有统计仅来自最终数值门和最终代码 SHA 之后的 `formal_verified`。此偏离没有隐去。

'''
text+='| 阶段 | 记录 | 完成 UTC | 回传核验 UTC | 正式 GPU h |\n|---|---:|---|---|---:|\n'
for s in execd['stages']:text+=f"| {s['stage']} | {s['complete_records']} | {s['completion_utc']} | {s['return_utc']} | {s['allocated_gpu_hours']:.6f} |\n"
text+=f'''
有效正式进程总计 **{execd['valid_formal_gpu_hours_verified_stages']:.6f} GPU 小时**。整台四卡实例从 {execd['instance_start_utc']} 到 stop 请求接受 {execd['cost_cutoff_utc']}，共 **{execd['instance_elapsed_hours']:.4f} 小时**，以整实例 **${execd['instance_rate_usd_per_hour_for_all_4_gpus']:.6f}/h** 估算 **${execd['instance_cost_estimate_usd']:.2f}**；包含安装、等待和回传，不再乘四，不含未核实的后续费用及最终账单调整。

**停机请求于 {execd['stop_receipt']['response_utc']} 被实例自身身份明确接受（无 401），随后 SSH 关闭。平台最终状态及最终计费截止未独立核实。** 作者随后表示自行 destroy；没有再访问实例，也没有由本代理执行 destroy。

## 统计与论文修改

- 每个 checkpoint 轨迹先计算非线性指标，再在 case 内平均三流与 AD-WM 三 checkpoint；100 case 为重抽单位。正式修正分析调用封存统计函数，5,000 次配对 bootstrap、种子 20261011，各方法／定义共用 case 索引。其余任务旧 AP 配对表保留原分析区间；缺少的绘图区间另由同一封存函数补算，并写入资产 manifest。
- 修正全部 Reacher 数值宏、预测表、成功率、旧／新对照、排名、占用、末 K 步、三 seed 三流表和 CEM 10／30 比较。其他三任务正式主统计校验不变。其他任务的补充末 K 步表也改为逐 checkpoint 计算非线性指标后平均；首次命中仅在第 50 步的轨迹不进入“命中后退出”分母。
- 图 1 使用修正后真实轨迹及逐关节误差：第 16 步首次到达、第 18 步离开、第 50 步在目标外；不再使用旧重置轨迹。
- 删除重复成功率表的排版调用，补齐附录 C 三口径 CEM 数值区间表；附录 E 保持复现清单，F 为运行时验证与完整时间线，G 为成本。
- 新稿在 `revision3_part2/`；旧 `main.tex`、旧 PDF 与旧 SEAL 未覆盖。参考文献沿用上一轮逐原始页面核验的版本；本轮没有虚称再次联网逐条核验。
- 首次图表生成尝试因旧汇总缺少部分非 Reacher 末步对比而失败，失败产物保留于 `paper_assets_final/`；只修分析生成器，成功版本为 `paper_assets_final_v2/`，没有改轨迹或登记。排版检查和最终封存清单随交付包提供。

## 交付及作者决定

新 PDF、LaTeX 源码、图表、逐条 CHANGES、作者决定清单和最终 SEAL 位于 `paper_jair/revision3_part2/`。MyProj 的 `delivery/` 保存交付副本；`JAIR_R3_PART2_MATERIALS.tar.gz` 是本地待发布复现材料包，包含必要的旧／新轨迹、版本与案例清单、分析和图表脚本、封存与回传证据。公开权重／数据大文件以来源清单和 SHA 标识，不重复分发。材料包 SHA 与逐文件核验结果另见 `DELIVERY_RECEIPT.json`。

尚需作者决定：最终标题、作者／贡献／AI 使用声明、仓库与许可证、数据再分发范围、归档 DOI 及投稿时机。未投稿、未公开发布，未删除文件。
'''
(P/'REVISION_3_PART2_REPORT_ZH.md').write_text(text)
(W.parent/'REVISION_3_PART2_REPORT_ZH.md').write_text(text)
changes='''# Revision 3 Part 2 逐项修改说明

本文件接续、替代旧修改说明中“等待 SSH／Reacher provisional”的状态；旧说明保留为历史记录。

| 指令 | 本轮处理 | 状态与边界 |
|---|---|---|
| §1 有效性 | 最终 CPU runtime 证据进入附录 F：四环境继续推进、旧 Reacher 双语义重放 | 采纳；按补充指令替代原要求的全量四任务物理重放，不冒充全量重放 |
| §2 更正登记／重跑 | 最终代码数值门、登记、回传、启动 SHA 链；全 2700 轨迹；33 条提前结果明确排除 | 完成；原错误测量保留对照 |
| §3 估计量 | checkpoint 轨迹先求指标、case 内平均、同索引 bootstrap；预测 11 子条件逐行 | 采纳；区间与数字由脚本生成 |
| §3 主结论区间 | AP−LeWM 任一步／末步及差中差；三帧−AP 的反号；旧新标签区别 | 采纳；撤回旧一帧 Reacher 反号，不保留过时叙事 |
| §3 末 K 步 | 四任务逐 trajectory 非线性指标；无后续步的末步首达不计退出分母 | 采纳；属于补充描述性统计 |
| §3 噪声精度 | 既有 case/流设计说明与半宽保留，不改为显著性判定所有文献 | 部分采纳；不把半宽等同最小可检测效应 |
| §4 相关工作 | PPWM/Singh/AP 定位、Vesessook 机制区分、版本和选择范围保留 | 沿用上一轮原始页面核验；不新增未经核实事实 |
| §5 可读性 | 方法映射、cohort、模型／原始步解释保留；真实图1与关节误差；补 CEM 数值表；删重复表调用 | 完成，原文件不删除 |
| §6 标题及力度 | 保留 Same Trajectories, Different Rankings；Reacher 修正结果直接陈述，旧反号撤回 | 标题仍由作者最终决定 |
| §7 JAIR | 清单位于附录 E；本地待发布材料；Data availability 继续占位 | 发布、许可证、DOI 待作者 |
| 补充 §2 runtime | 原语义 50/50；补丁首次成功前6/6、之后36/44，Cube为时间推进测试 | 证据范围如实陈述 |
| 补充 §3 两套标签 | ANY=微步OR，block/final/occupancy=END；两套原始标签均保存 | 最终代码 TECH 数值门后运行 |
| 补充 §4 收尾 | MyProj逐文件SHA、实例自身身份stop接受、最终状态未独立核实 | 未再次连接、未由代理destroy |

生成器首次失败与排版编译错误的日志保留；修复只涉及分析输入覆盖、成本截止说明和排版。最终论文数字与分析 manifest、结果 SEAL 绑定。
'''
(P/'CHANGES_ZH.md').write_text(changes)
(P/'AUTHOR_DECISIONS_ZH.md').write_text('''# 作者决定清单

实验及本地论文收尾不等待以下决定：

1. 确认最终标题；当前为 *Same Trajectories, Different Rankings: Success Timing and Protocol Choices in Latent World-Model Planning*。
2. 确认作者姓名、单位、ORCID、贡献、资金／利益冲突和 AI 使用声明准确且可发表。
3. 选择代码／数据仓库、许可证、公开材料范围、归档 DOI；先核对上游数据与权重的再分发许可。当前只是本地待发布包，没有上传。
4. 决定何时投稿；Data availability 的 URL／DOI 占位须在发布后替换。
5. 平台生命周期由作者处理：stop 已明确接受，但最终状态与账单未独立核实；作者曾表示自行 destroy。本代理不再连接实例。

无需新 GPU，也没有新增训练请求。
''')
print('reports written',now)
