# AP 差异核查准备包（尚未就绪）

A/B 已完成；C 未运行 GPU，不应租卡后盲跑。

- 独立 CPU 环境已安装，`pip check` 干净；`cpu.freeze.txt` 是本机 Python 3.12 的完整冻结记录。GPU 安装需单独解析 Linux/CUDA wheel，不把 macOS 冻结清单直接当 Linux 锁。
- `ap_source` 是单独执行副本，固定 commit；B 的审计 clone 不执行。
- `DOWNLOAD_MANIFEST.json` 给出 HF 文件 URL、revision、SHA 和展开校验。`INPUT_SHA256.json` 给出主表 case、bank 与 scaler 协议文件的 SHA。
- `run_main128.sh` 原样调用 anchored_planning，只通过外部协议选 clean / gaussian_observed。
- `run_three_seeds.sh` 在作者确认 cohort 解释前阻断。
- `compare_cases.py` 要求身份严格匹配、显式参考动作，不能拿 HELDOUT 结果替代原协议记录。
- `DECISION_PLAN_ZH.md` 给出三种结果分支、逐因素排查顺序、预算门和回传/停机规则。

尚未通过：原版完整 CPU 单 case（缺少原始数据、完整检索缓存及软件渲染配置）。组件检查不等于完整入口通过。待作者答复是否把完整入口门放在 SSH 后。

环境原版要求 torch 2.7.1 / torchvision 0.22.1 / stable-worldmodel 0.0.6 / mujoco 3.10.0 / dm-control 1.0.43，其他直接依赖见源 requirements/native-reacher.txt。预计一张 RTX 4090 24 GB，磁盘 >=160 GB，规划 3–5 小时墙钟；HF 输入23.823 GB，环境和 OS 包另计，尚未实测最终总下载量。
