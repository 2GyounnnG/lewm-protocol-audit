from pathlib import Path
import json,hashlib,csv,datetime,shutil
W=Path(__file__).resolve().parent;P=W.parents[1]/'revision3_part2';now=datetime.datetime.now(datetime.timezone.utc).isoformat();c=json.loads((W/'C1_FULL_AUDIT.json').read_text());d=json.loads((W/'D_FIRST25_SUMMARY.json').read_text());a=list(csv.DictReader((W/'A_WINDOW_PAIRED_INTERVALS.csv').open()));pdf=P/'JAIR_REVISION_4.pdf';shutil.copyfile(P/'build_revision4/main.pdf',pdf);h=hashlib.sha256(pdf.read_bytes()).hexdigest()
rows=[]
for i in range(0,len(a),2):
 x,y=a[i:i+2];names={'M03_h1':'AP','M01_h1':'Fast-LeWM','LeWM_h1':'一帧 LeWM','LeWM_h3':'三帧 LeWM'}
 f=lambda r:f"{float(r['delta_pp']):+.1f} [{float(r['ci95_low_pp']):+.1f}, {float(r['ci95_high_pp']):+.1f}]"
 rows.append(f"| {x['task']}：{names[x['left']]} − {names[x['right']]} | {f(x)} | {f(y)} |")
text=f'''# JAIR Revision 4 中文完成报告

完成 UTC：{now}。执行文件 SHA-256：`23ba028866b6e458e482d3b00e345f3d18680468afab0127269b25efffea92be`。采用替换 v1 的现行指令，A–I 已执行；本轮零 GPU、无模型或环境运行，未租卡、投稿、挂预印本、删除文件或访问 Zenodo/GitHub。`d1_execution/` 与预登记只读。

## 先行结果：C.1 与 D

这两项结果已经在修改正文之前报告给作者。

- **C.1：{c['records']}/2700 记录全部通过；任何检查失败的记录 0，旧／新任一步结果逐 case–stream–checkpoint 不一致 0。**覆盖 {c['environment_steps']:,} 环境步／{c['microsteps']:,} 微步；reset 每轨迹各一次，内部／pending reset 均 0；时间、target、qpos 谓词、OR/END、状态衔接均 0 不一致。微步 0.02 s（环境步 0.04 s），最大时间增量浮点误差 {c['max_time_increment_error']:.4g} s，容差 1e−12。
- 首次成功之前 **{c['actions_before_first_success']:,}** 个动作、含首次成功动作 **{c['actions_through_first_success']:,}** 个，均与封存旧轨迹逐位相同。LeWM 读取原 NPZ，方法 worker 读取其 NPY；不转换 dtype 来伪装逐位相等。
- **D：{d['pairs']}/300 对前 25 步动作完全相同，差异对 0，最大绝对差 0。**前 25 步 OR／END 均 0 不一致，全部首次动作差异发生在第 26 步；两种 history 第 25 步占据均为 22.0%。故正文明确第一段计划经构造与核验相同，+12.7 与 +48.3 pp 来自第二段计划，不据此推断速度或制动机制。
- 正式全量检查是**日志核验**，没有把它写成 2700 条物理重放。物理重放覆盖此前最终代码的 108 条 TECH（9 条件 ×4 case ×3 流）。TECH 重放使用原生未插桩 SWM wrapper，绕过 recorder/continuation wrapper、仅关闭 success termination，比较 qpos/qvel/time/target 的每个微步前后值。它用同一模拟器，不能称独立物理引擎。

## A：新增末窗口配对区间

单位 pp，95% 配对 bootstrap；每 case 内先平均流／checkpoint，封存函数 `statistics_d1.paired`，5,000 次，种子 20261011。同一索引矩阵用于各方法与定义，并与显式索引重算结果核对。完整精度在 CSV，不从舍入值重算。

| 对比 | 末 10 步平均占据差 [95% CI] | 末 10 步全部成功差 [95% CI] |
|---|---:|---:|
'''+ '\n'.join(rows)+f'''

Reacher／PushT 五配置的末步、末10平均、末5／10全部成功已进主文表；完整指标与新增区间在附录 D。三帧 LeWM 的 85.7% 末步与 0.3% 末10全部成功并列，避免把终点占据称为持续保持。

## 与旧稿不一致的数字／事实

| 项目 | 旧稿 | 新稿及来源 |
|---|---|---|
| 表2来源数 | 正文16，表中12 | 统一12；逐行重数实际表，`TABLE2_COUNT.json` |
| 全四任务来源数 | 10 | 8；DeepJEPA含Cube变体且无TwoRoom，不能按5项推断四任务覆盖 |
| Cube AP − LeWM 任一步上界 | 预测表34.7、配对表35.3 | 同索引／种子20261011统一34.7；差27.0，区间[19.7,34.7]。旧配对表使用20261012，差来自重抽，不是新轨迹或点估计变化 |
| LeWM CEM论文设置 | 表2误写10 P/C/T | 附录D：PushT30、其余10；附录B未限定任务写30；发布配置全30。历史3用于PushT/Cube、1用于TwoRoom、Reacher未写明 |
| Fast-LeWM执行前缀 | 五步且未给实际CEM数 | 25原始步（5×5），每25步再决策；候选300、精英30、迭代30。来源：冻结M01任务YAML、solver/cem.yaml、eval.py和本研究adapter |
| 表6／图2重复因素 | library和elite correction分列同值 | 数值相同的两行合并，图使用与表相同的Step3 mixed200三流来源，图例移出绘图区 |
| 全量核验覆盖 | 仅报告108 TECH | 保留108物理重放范围，新增2700正式日志核验／270000微步，未把覆盖扩大为新物理重放 |
| 平台参考文献 | refs.bib已有条目但正文未引用，PDF参考文献未显示 | 正文引用stable-worldmodel平台论文与commit63988116，既有BibTeX逐字不改，不重复添加 |
| 末窗口区间 | 仅点估计 | 新增上表8个区间；旧末窗口点值不变 |
| PDF | 29页 | 新稿页数以PDF_QA_REVISION4.json为准；增加主表、区间、覆盖和说明，旧PDF保留 |

原正式任一步、末步、末窗口点估计与已有 Reacher 配对效应均未改变；+48.3 [42.0,55.0] 原已存在，本轮移入摘要和引言。PushT +0.7 [−5.3,6.7] / −21.7 [−31.3,−11.7] / 变化−22.3 [−31.3,−13.0] 保留其原配对分析区间，并改正“确认双向优势”的措辞。没有用无效续跑值推断哪个控制器更容易离开目标。

## 宏、核验及材料

`a3_results/revision4_numbers.tex` 是当前唯一加载的数字宏文件；旧层保留但不再加载。Reacher表格数值单元已集中到该文件，映射和来源在 `REACHER_MACRO_CELL_MAP.json`；另对32行、131个关键数字直接核对源CSV，全部通过。协议常量、日期、SHA和表号不当作统计估计量。新统计保持完整精度。图1改为50步时间轴，图2无重叠图例。

新稿：`JAIR_REVISION_4.pdf`。SHA-256：`{h}`。编译、页数与渲染检查见 `PDF_QA_REVISION4.json`。旧 `JAIR_REVISION_3_PART2.pdf` 未改；完整上一稿在 `r3_part2_work/revision4/REVISION3_PART2_BEFORE_REV4.tar.gz`。历史 `SEAL.json` 不覆盖，当前新增 `SEAL_REVISION4.json`。

本轮脚本、输出、四份实际补丁diff、最小CPU入口和既有原始材料合入本地 Revision4 材料包；见 `MATERIALS_REVISION4_RECEIPT.json`。只准备本地包，不执行 RELEASE 文件中的任何在线步骤；没有新建仓库、Zenodo草稿或回填未获得的DOI。
'''
(P/'REVISION_4_COMPLETION_REPORT_ZH.md').write_text(text)
changes='''# JAIR Revision 4：A–I 逐条修改说明

依据现行指令 SHA `23ba028866b6e458e482d3b00e345f3d18680468afab0127269b25efffea92be`；旧PDF和全部上一稿快照保留。表号会因新增表自动变化，以下按审稿指令的原表号定位。

| 指令 | 修改与验证 | 状态 |
|---|---|---|
| A 主线与末窗口 | 三类问题改为首次到达、指定终点占据、持续窗口占据；新增Reacher/PushT五配置主表；8个末10指标配对区间；§9.1补第四种具体量尺 | 完成，纯CPU、封存bootstrap、同索引 |
| B 错误归属 | 摘要、引言、§3.1、§7.2归因为本研究早期continuation adapter；明确原发布首次到达评测不受影响；无效测量表及旧对比仅用于fault attribution，OR/END隔离表保留 | 完成；不推断PPWM有同类错误 |
| C.1 全量核验 | 全2700正式记录的reset、时间、target、状态、谓词、OR/END、动作前缀与任一步结果逐记录核验，0失败；先向作者报告后改正文 | 完成，逐记录CSV/JSON+SHA |
| C.2 覆盖与独立性 | 新覆盖表9条件分别列12 TECH／300 FORMAL；重放仅108 TECH；实际代码绕过recording/continuation wrapper、使用相同原生动力学，列出4种状态分量；全量日志不冒充物理重放 | 完成 |
| C.3 平台与复现入口 | 激活已有且核实无误的stable-worldmodel平台文献；正文注明63988116；材料加入4份原件diff、环境freeze出处及最小CPU入口 | 完成；未访问Zenodo/GitHub |
| D 历史长度 | 300对前25步动作逐位相同，首次分歧全在26；+48.3区间进摘要／引言；明确历史含观测与已执行动作块、天花板限制、非保持／制动机制 | 完成；未做可选速度分布分析 |
| E 登记地位 | 原任一步预测依0不一致保留确认性；更正登记是有效正式重跑前冻结方案；终点／窗口／排名为已见case上的描述性分析；independent改separately judged | 完成 |
| F 叙事顺序 | 历史与终点/窗口 → 对齐后增益 → 续跑核验 → 排名；Reacher三帧/AP双区间反号为主例；PushT只说明任一步未分出、末步更低及差值变化；标题不变 | 完成 |
| G 表2 | 重数12来源／8个全四任务，说明DeepJEPA变体；更正LeWM附录D/B/发布配置差异并定义P/C/T/R和rel. | 完成 |
| G 其余一致性 | Cube区间统一34.7；Fast-LeWM实际300/30/30、25步接口/执行/再决策与配置出处；流名改planning stream1/2/3；checkpoint注明公开编号；删Received；AP首次到达复现差异列局限且与reset分离 | 完成 |
| H 计算与正文 | 旧22/23合并，租金／生命周期行和计费脚注撤出论文，硬件软件行补齐；再训练episode来历；噪声是Step2任一步；C.1支持原新任一步相同；时间线加撤销启动及33排除；图1时间轴；AP五步锯齿；图2合并并改图例；AI声明删模型号 | 完成 |
| I 交付 | 新PDF、逐项说明、中文报告、数值一致性报告、差异清单、核验代码/输出及新材料包；旧稿/旧SEAL以快照保留，新封存单独命名 | 完成 |

数字／事实差异逐项见 `REVISION_4_COMPLETION_REPORT_ZH.md`，完整精度与输入SHA见 `r3_part2_work/revision4/`。本轮未改预登记或原始结果。参考文献源文件与上一稿SHA完全相同：平台条目原已在文件中，新增的是正文引用，因此只增加它在生成参考文献中的显示。
'''
(P/'CHANGES_ZH.md').write_text(changes)
(W/'PDF_IDENTITY.json').write_text(json.dumps({'sha256':h,'pdf':str(pdf.resolve()),'generated_utc':now},indent=2)+'\n')
print(h)
