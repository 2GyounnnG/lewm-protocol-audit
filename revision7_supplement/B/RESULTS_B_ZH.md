# B：续跑评测静态代码审计

只读静态审计，所有仓库克隆到本轮新空目录，没有导入或执行被审计库。commit、URL 和获取 UTC 见 REPOSITORIES.json；依赖 0.0.6 wheel 的 SHA 见 SWM_006_SOURCE.json。每个结论只适用于所列版本和被追踪路径；不判断他人的论文数字错误。

## 总结

成功终止、自动重置、评测继续取样三者同时出现时，后续观测可能来自新 episode。清外层 vector autoreset 位不清 dm_control 内层 pending reset。现代 stable-worldmodel dataset evaluate 默认 wait，AP 原入口遇成功/终止退出，Dreamer 与 Meta-World 评测显式处理边界；DINO-WM 被追踪的 PushT 路径不以成功终止，OGBench 官方循环遇 done 停止。0.0.6 的 dataset evaluator、Fast-LeWM 对它的调用、AD-WM 固定预算循环仅清外层 reset 位，须与 Reacher 内层成功终止联合分析。TD-MPC2 的 dm_control 包装不转发内部 LAST，是否会跨越 episode 取决于具体任务和时限。

这扩展了代码审计的覆盖范围，没有把四任务实验结论外推为这些库的实测结果。

## stable_worldmodel_63988116 / Reacher qpos_match

版本：`63988116d34cde56aea1240d5e58eb158ac67dc0`。

1. **成功是否触发终止**：是：每关节误差阈值触发 dm_control LAST
   - [stable_worldmodel_63988116:stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py:7-33](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py#L7-L33)
2. **自动重置层**：EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。
   - [stable_worldmodel_63988116:stable_worldmodel/world/env_pool.py:118-142](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/env_pool.py#L118-L142)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)
4. **终止处理**：wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)

仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。

## stable_worldmodel_63988116 / PushT

版本：`63988116d34cde56aea1240d5e58eb158ac67dc0`。

1. **成功是否触发终止**：是：位置与角度联合判据
   - [stable_worldmodel_63988116:stable_worldmodel/envs/pusht/env.py:318-372](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/envs/pusht/env.py#L318-L372)
2. **自动重置层**：EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。
   - [stable_worldmodel_63988116:stable_worldmodel/world/env_pool.py:118-142](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/env_pool.py#L118-L142)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)
4. **终止处理**：wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)

仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。

## stable_worldmodel_63988116 / TwoRoom

版本：`63988116d34cde56aea1240d5e58eb158ac67dc0`。

1. **成功是否触发终止**：是：距离小于16
   - [stable_worldmodel_63988116:stable_worldmodel/envs/two_room/env.py:262-280](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/envs/two_room/env.py#L262-L280)
2. **自动重置层**：EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。
   - [stable_worldmodel_63988116:stable_worldmodel/world/env_pool.py:118-142](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/env_pool.py#L118-L142)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)
4. **终止处理**：wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)

仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。

## stable_worldmodel_63988116 / Cube

版本：`63988116d34cde56aea1240d5e58eb158ac67dc0`。

1. **成功是否触发终止**：默认依赖 OGBench terminate_at_goal；Cube 继承 ManipSpaceEnv
   - [stable_worldmodel_63988116:stable_worldmodel/envs/ogbench/cube_env.py:34-53](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/envs/ogbench/cube_env.py#L34-L53)
   - [ogbench:ogbench/manipspace/envs/manipspace_env.py:20-49](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/ogbench/manipspace/envs/manipspace_env.py#L20-L49)
   - [ogbench:ogbench/manipspace/envs/manipspace_env.py:496-501](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/ogbench/manipspace/envs/manipspace_env.py#L496-L501)
2. **自动重置层**：EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。
   - [stable_worldmodel_63988116:stable_worldmodel/world/env_pool.py:118-142](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/env_pool.py#L118-L142)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)
4. **终止处理**：wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L430-L480)

仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。

## stable_worldmodel_63988116 / 其余 dm_control 包装

版本：`63988116d34cde56aea1240d5e58eb158ac67dc0`。

1. **成功是否触发终止**：所列 acrobot, ball_in_cup, cartpole, cheetah, finger, hopper, humanoid, manipulator, pendulum, quadruped, walker 不覆写基类成功终止钩子；返回 False。
   - [stable_worldmodel_63988116:stable_worldmodel/envs/dmcontrol/dmcontrol.py:98-127](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/envs/dmcontrol/dmcontrol.py#L98-L127)
2. **自动重置层**：dm_control 在内部 LAST（含时间上限）后下一步 reset。
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：默认 World wait 只看到外层 flags；基类 step 不把所有 dm_control LAST 向上传递。
   - [stable_worldmodel_63988116:stable_worldmodel/envs/dmcontrol/dmcontrol.py:98-127](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/envs/dmcontrol/dmcontrol.py#L98-L127)
   - [stable_worldmodel_63988116:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/world/world.py#L210-L250)
4. **终止处理**：没有额外成功终止需要清除；跨底层时间上限仍须检测内部 LAST。
   - [stable_worldmodel_63988116:stable_worldmodel/envs/dmcontrol/dmcontrol.py:98-127](https://github.com/galilai-group/stable-worldmodel/blob/63988116d34cde56aea1240d5e58eb158ac67dc0/stable_worldmodel/envs/dmcontrol/dmcontrol.py#L98-L127)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)

不能把 qpos_match 特例推广为所有 dm_control 成功任务；同时不保证任意长预算跨时间上限连续。

## stable_worldmodel_main / Reacher qpos_match

版本：`21446f1ede6d5284e981bd7b47f432b994e6d812`。

1. **成功是否触发终止**：是：每关节误差阈值触发 dm_control LAST
   - [stable_worldmodel_main:stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py:7-33](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py#L7-L33)
2. **自动重置层**：EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。
   - [stable_worldmodel_main:stable_worldmodel/world/env_pool.py:118-142](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/env_pool.py#L118-L142)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)
4. **终止处理**：wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)

仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。

## stable_worldmodel_main / PushT

版本：`21446f1ede6d5284e981bd7b47f432b994e6d812`。

1. **成功是否触发终止**：是：位置与角度联合判据
   - [stable_worldmodel_main:stable_worldmodel/envs/pusht/env.py:318-372](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/envs/pusht/env.py#L318-L372)
2. **自动重置层**：EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。
   - [stable_worldmodel_main:stable_worldmodel/world/env_pool.py:118-142](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/env_pool.py#L118-L142)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)
4. **终止处理**：wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)

仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。

## stable_worldmodel_main / TwoRoom

版本：`21446f1ede6d5284e981bd7b47f432b994e6d812`。

1. **成功是否触发终止**：是：距离小于16
   - [stable_worldmodel_main:stable_worldmodel/envs/two_room/env.py:262-280](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/envs/two_room/env.py#L262-L280)
2. **自动重置层**：EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。
   - [stable_worldmodel_main:stable_worldmodel/world/env_pool.py:118-142](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/env_pool.py#L118-L142)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)
4. **终止处理**：wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)

仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。

## stable_worldmodel_main / Cube

版本：`21446f1ede6d5284e981bd7b47f432b994e6d812`。

1. **成功是否触发终止**：默认依赖 OGBench terminate_at_goal；Cube 继承 ManipSpaceEnv
   - [stable_worldmodel_main:stable_worldmodel/envs/ogbench/cube_env.py:34-53](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/envs/ogbench/cube_env.py#L34-L53)
   - [ogbench:ogbench/manipspace/envs/manipspace_env.py:20-49](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/ogbench/manipspace/envs/manipspace_env.py#L20-L49)
   - [ogbench:ogbench/manipspace/envs/manipspace_env.py:496-501](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/ogbench/manipspace/envs/manipspace_env.py#L496-L501)
2. **自动重置层**：EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。
   - [stable_worldmodel_main:stable_worldmodel/world/env_pool.py:118-142](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/env_pool.py#L118-L142)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)
4. **终止处理**：wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)

仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。

## stable_worldmodel_main / 其余 dm_control 包装

版本：`21446f1ede6d5284e981bd7b47f432b994e6d812`。

1. **成功是否触发终止**：所列 acrobot, ball_in_cup, cartpole, cheetah, finger, hopper, humanoid, manipulator, pendulum, quadruped, walker 不覆写基类成功终止钩子；返回 False。
   - [stable_worldmodel_main:stable_worldmodel/envs/dmcontrol/dmcontrol.py:98-127](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/envs/dmcontrol/dmcontrol.py#L98-L127)
2. **自动重置层**：dm_control 在内部 LAST（含时间上限）后下一步 reset。
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：默认 World wait 只看到外层 flags；基类 step 不把所有 dm_control LAST 向上传递。
   - [stable_worldmodel_main:stable_worldmodel/envs/dmcontrol/dmcontrol.py:98-127](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/envs/dmcontrol/dmcontrol.py#L98-L127)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L210-L250)
4. **终止处理**：没有额外成功终止需要清除；跨底层时间上限仍须检测内部 LAST。
   - [stable_worldmodel_main:stable_worldmodel/envs/dmcontrol/dmcontrol.py:98-127](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/envs/dmcontrol/dmcontrol.py#L98-L127)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)

不能把 qpos_match 特例推广为所有 dm_control 成功任务；同时不保证任意长预算跨时间上限连续。

## stable-worldmodel 0.0.6（依赖追溯）

版本：`PyPI 0.0.6 wheel SHA / see manifest`。

1. **成功是否触发终止**：qpos_match 内部成功终止；其他四任务沿各环境定义。
   - [swm006:stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py:7-33](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)
2. **自动重置层**：外层向量 reset 位被清零；内层 dm_control reset 状态独立存在。
   - [swm006:stable_worldmodel/world.py:950-965](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：evaluate_from_dataset 跑完整 eval_budget，累计 success OR。
   - [swm006:stable_worldmodel/world.py:950-965](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)
4. **终止处理**：仅清外层 _autoreset_envs；没有在该循环清内层终止。
   - [swm006:stable_worldmodel/world.py:950-965](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)

在 qpos_match 成功后继续调用时，具有内部 reset 的静态风险；这不是对文献数字的错误判定。

## LeWM 最新 eval

版本：`8edfeb336732b5f3ce7b8b210d0ba370a09e2cac`。

1. **成功是否触发终止**：由所装 stable-worldmodel 的任务定义决定。
   - [lewm:eval.py:136-152](https://github.com/lucas-maes/le-wm/blob/8edfeb336732b5f3ce7b8b210d0ba370a09e2cac/eval.py#L136-L152)
   - [stable_worldmodel_main:stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py:7-33](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py#L7-L33)
2. **自动重置层**：由所装依赖及 reset_mode 决定。
   - [lewm:eval.py:136-152](https://github.com/lucas-maes/le-wm/blob/8edfeb336732b5f3ce7b8b210d0ba370a09e2cac/eval.py#L136-L152)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L210-L250)
3. **评测停止/继续**：调用 world.evaluate(dataset=...)；未显式覆盖 reset_mode。
   - [lewm:eval.py:136-152](https://github.com/lucas-maes/le-wm/blob/8edfeb336732b5f3ce7b8b210d0ba370a09e2cac/eval.py#L136-L152)
4. **终止处理**：与本次审计的 World 默认 wait 配对时终止槽冻结。
   - [lewm:eval.py:136-152](https://github.com/lucas-maes/le-wm/blob/8edfeb336732b5f3ce7b8b210d0ba370a09e2cac/eval.py#L136-L152)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:210-250](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L210-L250)
   - [stable_worldmodel_main:stable_worldmodel/world/world.py:430-480](https://github.com/galilai-group/stable-worldmodel/blob/21446f1ede6d5284e981bd7b47f432b994e6d812/stable_worldmodel/world/world.py#L430-L480)

调用链与现代 World wait 保持 episode 边界；不可套用旧 0.0.6 evaluate_from_dataset 的实现。

## AP 原版 anchored_planning

版本：`984327424ca7a2e52c75a8279197750d9d0b7c8e`。

1. **成功是否触发终止**：Reacher 显式检查 qpos；同时读取 terminated/truncated。
   - [ap:code/ap/anchored_planning/environments.py:116-126](https://github.com/daybraeklaxry/Aim-Short-to-Reach-Far/blob/984327424ca7a2e52c75a8279197750d9d0b7c8e/code/ap/anchored_planning/environments.py#L116-L126)
   - [ap:code/ap/anchored_planning/runtime.py:240-284](https://github.com/daybraeklaxry/Aim-Short-to-Reach-Far/blob/984327424ca7a2e52c75a8279197750d9d0b7c8e/code/ap/anchored_planning/runtime.py#L240-L284)
2. **自动重置层**：单环境逐步调用；依赖的 dm_control 有 LAST 后自动 reset。
   - [ap:code/ap/anchored_planning/runtime.py:240-284](https://github.com/daybraeklaxry/Aim-Short-to-Reach-Far/blob/984327424ca7a2e52c75a8279197750d9d0b7c8e/code/ap/anchored_planning/runtime.py#L240-L284)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：while not success and not stopped；每个 primitive 后即检查并 break。
   - [ap:code/ap/anchored_planning/runtime.py:240-284](https://github.com/daybraeklaxry/Aim-Short-to-Reach-Far/blob/984327424ca7a2e52c75a8279197750d9d0b7c8e/code/ap/anchored_planning/runtime.py#L240-L284)
4. **终止处理**：停止成功及非成功 termination，不把下一 episode 接到当前 case。
   - [ap:code/ap/anchored_planning/runtime.py:240-284](https://github.com/daybraeklaxry/Aim-Short-to-Reach-Far/blob/984327424ca7a2e52c75a8279197750d9d0b7c8e/code/ap/anchored_planning/runtime.py#L240-L284)

原版这一评测入口没有成功后续跑段。

## Fast-LeWM eval

版本：`2fc3bcafa4396804b0a747878dfe0ebcf14b3fcd`。

1. **成功是否触发终止**：由 pin 的 stable-worldmodel 0.0.6 任务决定。
   - [fast_lewm:requirements.txt:1-12](https://github.com/Yuntian-Gao/Fast-LeWorldModel/blob/2fc3bcafa4396804b0a747878dfe0ebcf14b3fcd/requirements.txt#L1-L12)
   - [swm006:stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py:7-33](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)
2. **自动重置层**：0.0.6 外层 vector reset 位被清零，内层 dm_control 未因此禁用。
   - [swm006:stable_worldmodel/world.py:950-965](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：调用 evaluate_from_dataset，固定预算循环。
   - [fast_lewm:eval.py:390-408](https://github.com/Yuntian-Gao/Fast-LeWorldModel/blob/2fc3bcafa4396804b0a747878dfe0ebcf14b3fcd/eval.py#L390-L408)
   - [swm006:stable_worldmodel/world.py:950-965](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)
4. **终止处理**：继承 0.0.6 清外层位做法，未在入口另改内部终止。
   - [fast_lewm:eval.py:390-408](https://github.com/Yuntian-Gao/Fast-LeWorldModel/blob/2fc3bcafa4396804b0a747878dfe0ebcf14b3fcd/eval.py#L390-L408)
   - [swm006:stable_worldmodel/world.py:950-965](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)

与 qpos_match 内部成功终止组合时，固定预算轨迹存在边界处理风险；静态审计不重判已发表成功率。

## AD-WM eval

版本：`7c27ebfdc4a2ba8e5a16268f2e4aa852fda72144`。

1. **成功是否触发终止**：依赖 stable-worldmodel 0.0.6 任务定义。
   - [adwm:requirements.txt:1-14](https://github.com/ad-wm/ad-wm-code/blob/7c27ebfdc4a2ba8e5a16268f2e4aa852fda72144/requirements.txt#L1-L14)
   - [swm006:stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py:7-33](https://files.pythonhosted.org/packages/77/ac/9618ee77bf0ed0180c67a0645dfb42215f54197de347235c831f65ea6363/stable_worldmodel-0.0.6-py3-none-any.whl)
2. **自动重置层**：外层 _autoreset_envs 清零；不等于消除 dm_control 内部 reset。
   - [adwm:eval.py:1329-1351](https://github.com/ad-wm/ad-wm-code/blob/7c27ebfdc4a2ba8e5a16268f2e4aa852fda72144/eval.py#L1329-L1351)
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：for eval_budget 调 world.step 并累计 terminated OR。
   - [adwm:eval.py:1329-1351](https://github.com/ad-wm/ad-wm-code/blob/7c27ebfdc4a2ba8e5a16268f2e4aa852fda72144/eval.py#L1329-L1351)
4. **终止处理**：该循环只清外层向量 reset 位。
   - [adwm:eval.py:1329-1351](https://github.com/ad-wm/ad-wm-code/blob/7c27ebfdc4a2ba8e5a16268f2e4aa852fda72144/eval.py#L1329-L1351)

内部成功终止任务若继续取样，需单独处理内层边界。

## DINO-WM（追踪 PushT 路径）

版本：`0a9492fa12044b852ae9e001cc74604b79c8bb0c`。

1. **成功是否触发终止**：PushT done 被显式置 False，成功另由 eval_state 计算。
   - [dino_wm:env/pusht/pusht_env.py:506-537](https://github.com/gaoyuezhou/dino_wm/blob/0a9492fa12044b852ae9e001cc74604b79c8bb0c/env/pusht/pusht_env.py#L506-L537)
2. **自动重置层**：该 step_multiple/rollout 路径不调用 autoreset。
   - [dino_wm:env/pusht/pusht_wrapper.py:84-119](https://github.com/gaoyuezhou/dino_wm/blob/0a9492fa12044b852ae9e001cc74604b79c8bb0c/env/pusht/pusht_wrapper.py#L84-L119)
3. **评测停止/继续**：执行给定动作序列后计算 rollout 指标。
   - [dino_wm:planning/evaluator.py:111-127](https://github.com/gaoyuezhou/dino_wm/blob/0a9492fa12044b852ae9e001cc74604b79c8bb0c/planning/evaluator.py#L111-L127)
   - [dino_wm:env/pusht/pusht_wrapper.py:84-119](https://github.com/gaoyuezhou/dino_wm/blob/0a9492fa12044b852ae9e001cc74604b79c8bb0c/env/pusht/pusht_wrapper.py#L84-L119)
4. **终止处理**：虽不按 done 截断，但此 PushT 底层没有成功终止。
   - [dino_wm:env/pusht/pusht_wrapper.py:84-119](https://github.com/gaoyuezhou/dino_wm/blob/0a9492fa12044b852ae9e001cc74604b79c8bb0c/env/pusht/pusht_wrapper.py#L84-L119)
   - [dino_wm:env/pusht/pusht_env.py:506-537](https://github.com/gaoyuezhou/dino_wm/blob/0a9492fa12044b852ae9e001cc74604b79c8bb0c/env/pusht/pusht_env.py#L506-L537)

被追踪的 PushT 路径不具备成功终止引起自动 reset 的前提；其他环境需各自追踪。

## TD-MPC2 dm_control

版本：`e9f59321933cbc8e11a002b842adc7d4ffae8ff1`。

1. **成功是否触发终止**：没有统一 success→termination 钩子；奖励任务由 suite 定义。
   - [tdmpc2:tdmpc2/envs/dmcontrol.py:50-61](https://github.com/nicklashansen/tdmpc2/blob/e9f59321933cbc8e11a002b842adc7d4ffae8ff1/tdmpc2/envs/dmcontrol.py#L50-L61)
   - [tdmpc2:tdmpc2/envs/dmcontrol.py:96-110](https://github.com/nicklashansen/tdmpc2/blob/e9f59321933cbc8e11a002b842adc7d4ffae8ff1/tdmpc2/envs/dmcontrol.py#L96-L110)
2. **自动重置层**：底层 dm_control 在 LAST 后下一步 reset。
   - [dm_control:dm_control/rl/control.py:98-129](https://github.com/google-deepmind/dm_control/blob/c22ec28159c541c8c6b6546cd56d41dcaf7fb33b/dm_control/rl/control.py#L98-L129)
3. **评测停止/继续**：每 action 两个 dm 步，外层返回 done=False；Timeout 限制 episode。
   - [tdmpc2:tdmpc2/envs/dmcontrol.py:50-61](https://github.com/nicklashansen/tdmpc2/blob/e9f59321933cbc8e11a002b842adc7d4ffae8ff1/tdmpc2/envs/dmcontrol.py#L50-L61)
   - [tdmpc2:tdmpc2/envs/dmcontrol.py:96-110](https://github.com/nicklashansen/tdmpc2/blob/e9f59321933cbc8e11a002b842adc7d4ffae8ff1/tdmpc2/envs/dmcontrol.py#L96-L110)
   - [tdmpc2:tdmpc2/evaluate.py:74-88](https://github.com/nicklashansen/tdmpc2/blob/e9f59321933cbc8e11a002b842adc7d4ffae8ff1/tdmpc2/evaluate.py#L74-L88)
4. **终止处理**：evaluate while not done；包装不转发内部 LAST，应检查任务是否会提前 LAST。
   - [tdmpc2:tdmpc2/envs/dmcontrol.py:50-61](https://github.com/nicklashansen/tdmpc2/blob/e9f59321933cbc8e11a002b842adc7d4ffae8ff1/tdmpc2/envs/dmcontrol.py#L50-L61)
   - [tdmpc2:tdmpc2/evaluate.py:74-88](https://github.com/nicklashansen/tdmpc2/blob/e9f59321933cbc8e11a002b842adc7d4ffae8ff1/tdmpc2/evaluate.py#L74-L88)

在常规固定时限 reward 任务和另加提前终止任务之间需区分；不能从外层 False 推断物理连续。

## DreamerV3 dm_control

版本：`e01491fad6434b2245a3b8ca201dd7faedcc458c`。

1. **成功是否触发终止**：使用 native dm_control LAST/discount，不把所有奖励成功一概当终止。
   - [dreamerv3:embodied/envs/from_dm.py:51-77](https://github.com/danijar/dreamerv3/blob/e01491fad6434b2245a3b8ca201dd7faedcc458c/embodied/envs/from_dm.py#L51-L77)
2. **自动重置层**：FromDM 在 reset 请求或 _done 时 reset。
   - [dreamerv3:embodied/envs/from_dm.py:51-77](https://github.com/danijar/dreamerv3/blob/e01491fad6434b2245a3b8ca201dd7faedcc458c/embodied/envs/from_dm.py#L51-L77)
3. **评测停止/继续**：driver 将 is_last 转为下一步 reset；以 episode 为单位推进。
   - [dreamerv3:embodied/core/driver.py:67-82](https://github.com/danijar/dreamerv3/blob/e01491fad6434b2245a3b8ca201dd7faedcc458c/embodied/core/driver.py#L67-L82)
4. **终止处理**：显式 is_first/is_last/is_terminal；ActionRepeat 遇终止 break。
   - [dreamerv3:embodied/envs/from_dm.py:51-77](https://github.com/danijar/dreamerv3/blob/e01491fad6434b2245a3b8ca201dd7faedcc458c/embodied/envs/from_dm.py#L51-L77)
   - [dreamerv3:embodied/core/driver.py:67-82](https://github.com/danijar/dreamerv3/blob/e01491fad6434b2245a3b8ca201dd7faedcc458c/embodied/core/driver.py#L67-L82)
   - [dreamerv3:embodied/core/wrappers.py:63-73](https://github.com/danijar/dreamerv3/blob/e01491fad6434b2245a3b8ca201dd7faedcc458c/embodied/core/wrappers.py#L63-L73)

记录边界后重开 episode，不把它宣称为同条成功后连续轨迹。

## Meta-World 基类与评测包装

版本：`c0dafaf1557f31cad3b96ba2b62462f45638f5a5`。

1. **成功是否触发终止**：基类成功不终止；TerminateOnSuccess 开关可改为 success→terminated，evaluation 会打开。
   - [metaworld:metaworld/sawyer_xyz_env.py:629-643](https://github.com/Farama-Foundation/Metaworld/blob/c0dafaf1557f31cad3b96ba2b62462f45638f5a5/metaworld/sawyer_xyz_env.py#L629-L643)
   - [metaworld:metaworld/wrappers.py:217-230](https://github.com/Farama-Foundation/Metaworld/blob/c0dafaf1557f31cad3b96ba2b62462f45638f5a5/metaworld/wrappers.py#L217-L230)
   - [metaworld:metaworld/evaluation.py:53-83](https://github.com/Farama-Foundation/Metaworld/blob/c0dafaf1557f31cad3b96ba2b62462f45638f5a5/metaworld/evaluation.py#L53-L83)
2. **自动重置层**：benchmark vector 默认 SAME_STEP。
   - [metaworld:metaworld/__init__.py:455-468](https://github.com/Farama-Foundation/Metaworld/blob/c0dafaf1557f31cad3b96ba2b62462f45638f5a5/metaworld/__init__.py#L455-L468)
3. **评测停止/继续**：评测在 dones 处分 episode，按 final_info 计成功。
   - [metaworld:metaworld/evaluation.py:53-83](https://github.com/Farama-Foundation/Metaworld/blob/c0dafaf1557f31cad3b96ba2b62462f45638f5a5/metaworld/evaluation.py#L53-L83)
4. **终止处理**：agent.reset(dones)，使用 final_info 而非重置后的 obs。
   - [metaworld:metaworld/evaluation.py:53-83](https://github.com/Farama-Foundation/Metaworld/blob/c0dafaf1557f31cad3b96ba2b62462f45638f5a5/metaworld/evaluation.py#L53-L83)

同一库的训练/评测开关不同；官方评测显式处理 episode 边界。

## OGBench ManipSpace/Cube

版本：`a977253ce5b88434f4e4f531c50047cc95993a51`。

1. **成功是否触发终止**：terminate_at_goal 默认 True，成功→terminated。
   - [ogbench:ogbench/manipspace/envs/manipspace_env.py:496-501](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/ogbench/manipspace/envs/manipspace_env.py#L496-L501)
   - [ogbench:ogbench/manipspace/envs/manipspace_env.py:20-49](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/ogbench/manipspace/envs/manipspace_env.py#L20-L49)
2. **自动重置层**：该 step 有初始 pending-reset 分支；返回 terminated 本身未将 _reset_next_step 重新置 True；外层 vector 可另 reset。
   - [ogbench:ogbench/manipspace/envs/manipspace_env.py:314-341](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/ogbench/manipspace/envs/manipspace_env.py#L314-L341)
   - [ogbench:ogbench/manipspace/envs/env.py:200-206](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/ogbench/manipspace/envs/env.py#L200-L206)
3. **评测停止/继续**：官方 evaluate 到 terminated or truncated 即结束。
   - [ogbench:impls/utils/evaluation.py:74-90](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/impls/utils/evaluation.py#L74-L90)
4. **终止处理**：while not done，下一 episode 显式 reset。
   - [ogbench:impls/utils/evaluation.py:74-90](https://github.com/seohongpark/ogbench/blob/a977253ce5b88434f4e4f531c50047cc95993a51/impls/utils/evaluation.py#L74-L90)

单环境返回 terminated 与外层自动 reset 不能混为一谈；原评测未忽略边界。

## Gymnasium Sync/AsyncVectorEnv

版本：`8b22ad4a6eeb55a67973d8143dec888efdc1660e`。

1. **成功是否触发终止**：由子环境提供 flags，vector 不定义任务成功。
   - [gymnasium:gymnasium/vector/sync_vector_env.py:78-95](https://github.com/Farama-Foundation/Gymnasium/blob/8b22ad4a6eeb55a67973d8143dec888efdc1660e/gymnasium/vector/sync_vector_env.py#L78-L95)
2. **自动重置层**：两者默认 NEXT_STEP；可选 SAME_STEP 或 DISABLED。
   - [gymnasium:gymnasium/vector/sync_vector_env.py:78-95](https://github.com/Farama-Foundation/Gymnasium/blob/8b22ad4a6eeb55a67973d8143dec888efdc1660e/gymnasium/vector/sync_vector_env.py#L78-L95)
   - [gymnasium:gymnasium/vector/async_vector_env.py:132-143](https://github.com/Farama-Foundation/Gymnasium/blob/8b22ad4a6eeb55a67973d8143dec888efdc1660e/gymnasium/vector/async_vector_env.py#L132-L143)
   - [gymnasium:gymnasium/vector/sync_vector_env.py:290-339](https://github.com/Farama-Foundation/Gymnasium/blob/8b22ad4a6eeb55a67973d8143dec888efdc1660e/gymnasium/vector/sync_vector_env.py#L290-L339)
3. **评测停止/继续**：通用接口，无固定评价循环。
   - [gymnasium:gymnasium/vector/sync_vector_env.py:290-339](https://github.com/Farama-Foundation/Gymnasium/blob/8b22ad4a6eeb55a67973d8143dec888efdc1660e/gymnasium/vector/sync_vector_env.py#L290-L339)
4. **终止处理**：NEXT_STEP 返回 reset obs；SAME_STEP 提供 final_obs/final_info；DISABLED 要求调用方管理 reset。
   - [gymnasium:gymnasium/vector/sync_vector_env.py:290-339](https://github.com/Farama-Foundation/Gymnasium/blob/8b22ad4a6eeb55a67973d8143dec888efdc1660e/gymnasium/vector/sync_vector_env.py#L290-L339)

连续轨迹消费者必须选对模式并保留边界；默认不是关闭自动重置。

## PPWM

版本：`None`。

1. **成功是否触发终止**：未找到
2. **自动重置层**：未找到
3. **评测停止/继续**：未找到
4. **终止处理**：未找到

已查 arXiv 摘要/HTML及按标题和作者的 GitHub 搜索，未找到可核实的作者公开代码。

## PPWM 查询范围

- https://arxiv.org/abs/2610.08627
- https://arxiv.org/html/2610.08627v1
- 网页搜索：Parallel Predictive World Models GitHub
- 网页搜索：PPWM Wanjin GitHub

原始摘要/HTML页面与标题/作者搜索未提供可核实的作者仓库；不使用第三方教学实现代替。
