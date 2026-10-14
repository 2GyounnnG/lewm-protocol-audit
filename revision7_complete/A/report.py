from pathlib import Path
import pandas as pd
W=Path(__file__).resolve().parent;x=pd.read_csv(W/'SENSITIVITY_CONTRASTS.csv');c=x[x.status=='COMPUTED']
text='''# A：阈值与窗口敏感性（CPU，已保存记录）

没有运行环境、模型或实验。Reacher 使用 600 条修正轨迹（LeWM h3/AP 各 100 case × 3 流）；PushT 使用 900 条正式轨迹（LeWM h1/AP/Fast-LeWM）。逐文件对照封存 SHA 后读取。

所有区间调用封存 statistics_d1.py 的 paired 函数，5,000 次，种子 20261011；逐项核对同一 100×5000 索引向量。先逐轨迹算非线性标签，再在 case 内平均三个流。下列均为百分点差及 95% 区间，修正后描述性分析，不改已有结果。

## 主要结果

- Reacher 三帧 LeWM − AP：末步差在 0.03/0.05/0.08 rad 都为正且区间不含零。全部窗口成功的反号在 0.05 和 0.08 rad、K=5/10/15/20 全部保持，区间均不含零。
- 更严的 0.03 rad 下，全部末 5 步仍为负且区间不含零；K=10 的区间触及零；K=15/20 为零差、退化 [0,0]。平均占据在三个阈值、全部四个 K 下均为负且区间不含零。
- PushT AP − 一帧 LeWM：末步为负，全部窗口成功在 K=5/10/15/20 均为正且区间不含零。平均占据的 K=5 区间含零，K≥10 为正且不含零。
- PushT Fast-LeWM − 一帧 LeWM：末步、全部窗口、平均占据均为正且区间不含零，没有末步/窗口反号。
- PushT 正式记录没有逐步位置/角度状态：官方 NPZ 只有动作、计划和 successes；方法 JSON 的 steps 只有 t/success/terminated/truncated。因此不能做 15/25 像素阈值重判，明确记未计算；20 像素列使用保存的原标签，保留原角度条件。

## 紧凑结果表

'''
for metric in ['final_END','all_window_END','mean_window_END','any_original_OR','any_rethresholded_OR']:
 text+=f'### {metric}\n\n|比较|阈值|K|差值 [95% CI] pp|\n|---|---:|---:|---|\n'
 for r in c[c.metric==metric].itertuples():text+=f'|{r.comparison}|{r.threshold:g}|{r.window}|{r.delta_pp:+.2f} [{r.ci95_low_pp:+.2f}, {r.ci95_high_pp:+.2f}]|\n'
 text+='\n'
(W/'RESULTS_A_ZH.md').write_text(text)
