compare_groups.sh 在 0.51 秒内成功完成全部278例比对（STAGE_compare returncode=0）。Supervisor 默认 startsecs=1 把快速正常退出判为启动失败，并尝试重启；run_stage 防重入拒绝重复执行。保留全部日志，新阶段配置改 startsecs=0/startretries=0。没有重跑任何轨迹，也没有更改分析结果。
