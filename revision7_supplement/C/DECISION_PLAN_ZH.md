# C 运行前处理方案

状态：准备中，未授权 GPU。源码 commit 984327424ca7a2e52c75a8279197750d9d0b7c8e。

1. 约 97%：先复核 128 个身份、原始数据顺序、checkpoint SHA、bank_train_episodes、removed_memory_episodes 与 REPRODUCING.md；仅在资产/协议核实后描述发布资产与论文数字不一致，不推断原因。
2. 约 76%：与研究适配器逐因素配对，用固定 50 case；依次检查动作缩放、每 5 步再决策、检索库排除、CEM 种子和 1/3 std、目标切片、history。每项从同一个原版基准只改一个因素；保留完整动作和首次成功步，定位到翻转因素后停止扩展。
3. 中间区间：报告三种子分布，再采用同一因素排查；不得从多因素共同变化归因。
4. 原版 entry 不改。主表 protocol 文件只选 clean + gaussian_observed，128 个身份、offset 150、budget 300、bank 和 CEM 保持源码定义；这避免默认 3 起点×5 控制器的额外作业。
5. 附录 42/43/44 来自 LeWM 检查，源文件明确说不是 AP 重跑；其实际 offset 24、budget 50。需作者决定新 AP 跨 cohort 检查是否保留这套目标。批准前三种子脚本阻断。
6. 97.7% 的原协议研究结果位于 step2/resume_03，不是 step4 的 HELDOUT 条件。逐 case 比较必须用原协议身份，不能拿 HELDOUT 替代。
7. 第一 GPU 阶段只做原版单 case 与缓存吞吐。记录建库和每 case 墙钟，估计全部主表、三种子、允许的后续检查；预计 >6 GPU 小时即报告并等待。2–3 GPU 小时／3–5 小时墙钟是计划值，尚非测量。
8. 每阶段回传 SHA 核验，完整结果后用该实例自己的容器 ID/密钥 stop；401 报告作者网页停机；不 destroy。

资源：RTX 4090 24 GB，Python 3.12 / CUDA 12.8 镜像。AP 原文环境是 Python 3.11.14 / torch 2.7.1 CUDA 12.6；本轮要求的 Python/CUDA 差异必须记录，不称逐位环境复现。直接依赖沿原版 native-reacher；SWM=0.0.6 独立环境，不能复用统一协议环境。

磁盘建议 >=160 GB：压缩数据23.75 GB + 展开98.91 GB + 缓存0.772 GB + Python/CUDA环境、结果余量。HF资产精确下载总量23,822,907,108 bytes；不含尚未解析的Linux CUDA wheel、OS包与仓库传输。
