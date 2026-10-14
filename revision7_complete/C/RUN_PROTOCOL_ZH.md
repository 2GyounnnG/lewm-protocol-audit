# C 已确认运行协议

作者确认已记录 UTC，见 AUTHOR_CONFIRMATION.json。本机真实case重放与模型组件CPU smoke通过；完整检索入口验证安排在SSH后、正式运行前。未收到SSH不执行GPU。

| 组 | case | 目标偏移 | 原始步预算 | 比较对象 |
|---|---:|---:|---:|---|
| AP 主表协议 | 原128 case | 150 | 300 | 论文75.8%；本研究原协议128条逐case参照 |
| AP 附录复核 | 种子42/43/44各50 case | 24 | 50 | 三种子分别报告，绝不与75.8%混比 |

两组都使用 commit 984327424ca7a2e52c75a8279197750d9d0b7c8e 的原始 anchored_planning 入口，clean / gaussian_observed、每5步再决策、原CEM 300/30/30、std=1/3。入口源码不改。

附录42/43/44是原附录的case抽样种子；AP优化器仍用未改动的原生 query_seed(reacher, ordinal)，不把它重命名为42/43/44。附录不是已发布AP主表，命名为“AP 附录复核”。其bank从原AP bank排除全部附录评测episode并在三组间共享；主表bank完全不动。episode/anchor不变；远端验证每episode201行及offset后才绑定HDF5。

运行次序：安装独立AP锁→压缩/展开数据与checkpoint SHA→原版encode-cache并记录SHA→3个主表case完整入口预检→验证真实入口输出、记录与旧参照差异→吞吐门≤6 GPUh→主表128→附录42/43/44→分组比对。原版入口预检及吞吐门均必须PASS，正式脚本才可启动。任何后续排查仍受6 GPUh总上限约束。

本研究97.7%来自第2步原协议 D1_082_000_128，不是第4步HELDOUT。128条逐文件SHA核验、125次成功；16个AP模块与旧副本一致。比对脚本以 episode/global_start/global_goal 严格匹配，记录成功、首次成功步、前25动作差及首个分歧。

命令：`run_gpu_tech_profile.sh`，然后 `run_main128.sh`、`run_three_seeds.sh`；最后 `compare_groups.sh`。AP_PYTHON必须指向独立Linux环境，AP_GPU_SSH_AUTHORIZED仅在作者给SSH后设置。

每阶段回传不可变快照并逐文件SHA。两项实验可共用核验后的原始数据与权重，但AP与method_hold的环境、检索缓存、结果和协议各自独立。完成回传核验后容器内stop，不destroy；401报告作者网页停机。
