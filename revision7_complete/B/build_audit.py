from pathlib import Path
import json,hashlib,datetime,csv,subprocess
W=Path(__file__).resolve().parent;repos={r['name']:r for r in json.load(open(W/'REPOSITORIES.json'))};rows=[];evidence={}
def ev(repo,path,start,end):
 root=W/'swm_pypi_0_0_6' if repo=='swm006' else W/'repos'/repo;p=root/path;lines=p.read_text().splitlines();assert 1<=start<=end<=len(lines),(repo,path,start,end,len(lines))
 key=f'{repo}:{path}:{start}-{end}'
 url=(json.load(open(W/'SWM_006_SOURCE.json'))['url'] if repo=='swm006' else repos[repo]['url'].removesuffix('.git')+'/blob/'+repos[repo]['commit']+'/'+path+f'#L{start}-L{end}')
 evidence[key]=dict(repo=repo,path=path,start=start,end=end,url=url,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),excerpt='\n'.join(f'{i}: {lines[i-1]}' for i in range(start,end+1)))
 return key
def add(name,repo,answers,proofs,conclusion):
 assert len(answers)==len(proofs)==4
 rows.append(dict(name=name,repository=repo,commit=repos[repo]['commit'] if repo in repos else 'PyPI 0.0.6 wheel SHA / see manifest',q1_success_terminates=answers[0],q2_autoreset=answers[1],q3_eval_flow=answers[2],q4_termination_handling=answers[3],evidence=proofs,interpretation=conclusion))
dmc=ev('dm_control','dm_control/rl/control.py',98,129)
for repo in ['stable_worldmodel_63988116','stable_worldmodel_main']:
 world=ev(repo,'stable_worldmodel/world/world.py',210,250);loop=ev(repo,'stable_worldmodel/world/world.py',430,480);pool=ev(repo,'stable_worldmodel/world/env_pool.py',118,142)
 dm=ev(repo,'stable_worldmodel/envs/dmcontrol/dmcontrol.py',98,127);reach=ev(repo,'stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py',7,33)
 for task,pred,refs in [('Reacher qpos_match','是：每关节误差阈值触发 dm_control LAST',[reach]),('PushT','是：位置与角度联合判据',[ev(repo,'stable_worldmodel/envs/pusht/env.py',318,372)]),('TwoRoom','是：距离小于16',[ev(repo,'stable_worldmodel/envs/two_room/env.py',262,280)]),('Cube','默认依赖 OGBench terminate_at_goal；Cube 继承 ManipSpaceEnv',[ev(repo,'stable_worldmodel/envs/ogbench/cube_env.py',34,53),ev('ogbench','ogbench/manipspace/envs/manipspace_env.py',20,49),ev('ogbench','ogbench/manipspace/envs/manipspace_env.py',496,501)])]:
  add(f'{repo} / {task}',repo,[pred,'EnvPool 无隐式 reset；World auto 模式显式 reset；Reacher 另有 dm_control 内层自动 reset。','dataset evaluate 默认 wait：每个 done 槽冻结，未结束槽继续。','wait 屏蔽已结束槽；auto 是新 episode，不可当同条物理轨迹。'],[refs,[pool,loop,dmc],[world,loop],[loop]],'仅外层清终止而绕过 wait 的续跑不充分；Reacher 必须同时处理内层终止。')
 # Static inheritance coverage: all wrapper modules are included, no other _is_terminated override.
 domains=sorted(p.stem for p in (W/'repos'/repo/'stable_worldmodel/envs/dmcontrol').glob('*.py') if p.stem not in ['__init__','dmcontrol','expert_policy','reacher'])
 add(repo+' / 其余 dm_control 包装',repo,['所列 '+', '.join(domains)+' 不覆写基类成功终止钩子；返回 False。','dm_control 在内部 LAST（含时间上限）后下一步 reset。','默认 World wait 只看到外层 flags；基类 step 不把所有 dm_control LAST 向上传递。','没有额外成功终止需要清除；跨底层时间上限仍须检测内部 LAST。'],[[dm],[dmc],[dm,world],[dm,dmc]],'不能把 qpos_match 特例推广为所有 dm_control 成功任务；同时不保证任意长预算跨时间上限连续。')
old=ev('swm006','stable_worldmodel/world.py',950,965);oldreach=ev('swm006','stable_worldmodel/envs/dmcontrol/custom_tasks/reacher.py',7,33)
add('stable-worldmodel 0.0.6（依赖追溯）','swm006',['qpos_match 内部成功终止；其他四任务沿各环境定义。','外层向量 reset 位被清零；内层 dm_control reset 状态独立存在。','evaluate_from_dataset 跑完整 eval_budget，累计 success OR。','仅清外层 _autoreset_envs；没有在该循环清内层终止。'],[[oldreach],[old,dmc],[old],[old,dmc]],'在 qpos_match 成功后继续调用时，具有内部 reset 的静态风险；这不是对文献数字的错误判定。')
l=ev('lewm','eval.py',136,152)
add('LeWM 最新 eval','lewm',['由所装 stable-worldmodel 的任务定义决定。','由所装依赖及 reset_mode 决定。','调用 world.evaluate(dataset=...)；未显式覆盖 reset_mode。','与本次审计的 World 默认 wait 配对时终止槽冻结。'],[[l,reach],[l,world],[l],[l,world,loop]],'调用链与现代 World wait 保持 episode 边界；不可套用旧 0.0.6 evaluate_from_dataset 的实现。')
a=ev('ap','code/ap/anchored_planning/runtime.py',240,284);ae=ev('ap','code/ap/anchored_planning/environments.py',116,126)
add('AP 原版 anchored_planning','ap',['Reacher 显式检查 qpos；同时读取 terminated/truncated。','单环境逐步调用；依赖的 dm_control 有 LAST 后自动 reset。','while not success and not stopped；每个 primitive 后即检查并 break。','停止成功及非成功 termination，不把下一 episode 接到当前 case。'],[[ae,a],[a,dmc],[a],[a]],'原版这一评测入口没有成功后续跑段。')
f=ev('fast_lewm','eval.py',390,408);fr=ev('fast_lewm','requirements.txt',1,12)
add('Fast-LeWM eval','fast_lewm',['由 pin 的 stable-worldmodel 0.0.6 任务决定。','0.0.6 外层 vector reset 位被清零，内层 dm_control 未因此禁用。','调用 evaluate_from_dataset，固定预算循环。','继承 0.0.6 清外层位做法，未在入口另改内部终止。'],[[fr,oldreach],[old,dmc],[f,old],[f,old]],'与 qpos_match 内部成功终止组合时，固定预算轨迹存在边界处理风险；静态审计不重判已发表成功率。')
ad=ev('adwm','eval.py',1329,1351);adr=ev('adwm','requirements.txt',1,14)
add('AD-WM eval','adwm',['依赖 stable-worldmodel 0.0.6 任务定义。','外层 _autoreset_envs 清零；不等于消除 dm_control 内部 reset。','for eval_budget 调 world.step 并累计 terminated OR。','该循环只清外层向量 reset 位。'],[[adr,oldreach],[ad,dmc],[ad],[ad]],'内部成功终止任务若继续取样，需单独处理内层边界。')
de=ev('dino_wm','planning/evaluator.py',111,127);dr=ev('dino_wm','env/pusht/pusht_wrapper.py',84,119);dp=ev('dino_wm','env/pusht/pusht_env.py',506,537)
add('DINO-WM（追踪 PushT 路径）','dino_wm',['PushT done 被显式置 False，成功另由 eval_state 计算。','该 step_multiple/rollout 路径不调用 autoreset。','执行给定动作序列后计算 rollout 指标。','虽不按 done 截断，但此 PushT 底层没有成功终止。'],[[dp],[dr],[de,dr],[dr,dp]],'被追踪的 PushT 路径不具备成功终止引起自动 reset 的前提；其他环境需各自追踪。')
td=ev('tdmpc2','tdmpc2/envs/dmcontrol.py',50,61);te=ev('tdmpc2','tdmpc2/evaluate.py',74,88);tm=ev('tdmpc2','tdmpc2/envs/dmcontrol.py',96,110)
add('TD-MPC2 dm_control','tdmpc2',['没有统一 success→termination 钩子；奖励任务由 suite 定义。','底层 dm_control 在 LAST 后下一步 reset。','每 action 两个 dm 步，外层返回 done=False；Timeout 限制 episode。','evaluate while not done；包装不转发内部 LAST，应检查任务是否会提前 LAST。'],[[td,tm],[dmc],[td,tm,te],[td,te]],'在常规固定时限 reward 任务和另加提前终止任务之间需区分；不能从外层 False 推断物理连续。')
df=ev('dreamerv3','embodied/envs/from_dm.py',51,77);dd=ev('dreamerv3','embodied/core/driver.py',67,82);da=ev('dreamerv3','embodied/core/wrappers.py',63,73)
add('DreamerV3 dm_control','dreamerv3',['使用 native dm_control LAST/discount，不把所有奖励成功一概当终止。','FromDM 在 reset 请求或 _done 时 reset。','driver 将 is_last 转为下一步 reset；以 episode 为单位推进。','显式 is_first/is_last/is_terminal；ActionRepeat 遇终止 break。'],[[df],[df],[dd],[df,dd,da]],'记录边界后重开 episode，不把它宣称为同条成功后连续轨迹。')
mb=ev('metaworld','metaworld/sawyer_xyz_env.py',629,643);mw=ev('metaworld','metaworld/wrappers.py',217,230);me=ev('metaworld','metaworld/evaluation.py',53,83);mv=ev('metaworld','metaworld/__init__.py',455,468)
add('Meta-World 基类与评测包装','metaworld',['基类成功不终止；TerminateOnSuccess 开关可改为 success→terminated，evaluation 会打开。','benchmark vector 默认 SAME_STEP。','评测在 dones 处分 episode，按 final_info 计成功。','agent.reset(dones)，使用 final_info 而非重置后的 obs。'],[[mb,mw,me],[mv],[me],[me]],'同一库的训练/评测开关不同；官方评测显式处理 episode 边界。')
og=ev('ogbench','ogbench/manipspace/envs/manipspace_env.py',314,341);ot=ev('ogbench','ogbench/manipspace/envs/manipspace_env.py',496,501);oe=ev('ogbench','impls/utils/evaluation.py',74,90);oi=ev('ogbench','ogbench/manipspace/envs/env.py',200,206)
add('OGBench ManipSpace/Cube','ogbench',['terminate_at_goal 默认 True，成功→terminated。','该 step 有初始 pending-reset 分支；返回 terminated 本身未将 _reset_next_step 重新置 True；外层 vector 可另 reset。','官方 evaluate 到 terminated or truncated 即结束。','while not done，下一 episode 显式 reset。'],[[ot,ev('ogbench','ogbench/manipspace/envs/manipspace_env.py',20,49)],[og,oi],[oe],[oe]],'单环境返回 terminated 与外层自动 reset 不能混为一谈；原评测未忽略边界。')
gs=ev('gymnasium','gymnasium/vector/sync_vector_env.py',78,95);ga=ev('gymnasium','gymnasium/vector/async_vector_env.py',132,143);gl=ev('gymnasium','gymnasium/vector/sync_vector_env.py',290,339)
add('Gymnasium Sync/AsyncVectorEnv','gymnasium',['由子环境提供 flags，vector 不定义任务成功。','两者默认 NEXT_STEP；可选 SAME_STEP 或 DISABLED。','通用接口，无固定评价循环。','NEXT_STEP 返回 reset obs；SAME_STEP 提供 final_obs/final_info；DISABLED 要求调用方管理 reset。'],[[gs],[gs,ga,gl],[gl],[gl]],'连续轨迹消费者必须选对模式并保留边界；默认不是关闭自动重置。')
# The optional PPWM source was not found; never substitute another repository.
rows.append(dict(name='PPWM',repository='NOT_FOUND',commit=None,q1_success_terminates='未找到',q2_autoreset='未找到',q3_eval_flow='未找到',q4_termination_handling='未找到',evidence=[[],[],[],[]],interpretation='已查 arXiv 摘要/HTML及按标题和作者的 GitHub 搜索，未找到可核实的作者公开代码。'))
(W/'AUDIT_ROWS.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(W/'CODE_EVIDENCE.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
head='''# B：续跑评测静态代码审计

只读静态审计，所有仓库克隆到本轮新空目录，没有导入或执行被审计库。commit、URL 和获取 UTC 见 REPOSITORIES.json；依赖 0.0.6 wheel 的 SHA 见 SWM_006_SOURCE.json。每个结论只适用于所列版本和被追踪路径；不判断他人的论文数字错误。

## 总结

成功终止、自动重置、评测继续取样三者同时出现时，后续观测可能来自新 episode。清外层 vector autoreset 位不清 dm_control 内层 pending reset。现代 stable-worldmodel dataset evaluate 默认 wait，AP 原入口遇成功/终止退出，Dreamer 与 Meta-World 评测显式处理边界；DINO-WM 被追踪的 PushT 路径不以成功终止，OGBench 官方循环遇 done 停止。0.0.6 的 dataset evaluator、Fast-LeWM 对它的调用、AD-WM 固定预算循环仅清外层 reset 位，须与 Reacher 内层成功终止联合分析。TD-MPC2 的 dm_control 包装不转发内部 LAST，是否会跨越 episode 取决于具体任务和时限。

这扩展了代码审计的覆盖范围，没有把四任务实验结论外推为这些库的实测结果。

'''
text=head
for r in rows:
 text+=f"## {r['name']}\n\n版本：`{r['commit']}`。\n\n"
 for i,(k,title) in enumerate([('q1_success_terminates','成功是否触发终止'),('q2_autoreset','自动重置层'),('q3_eval_flow','评测停止/继续'),('q4_termination_handling','终止处理')]):
  text+=f"{i+1}. **{title}**：{r[k]}\n"
  for e in r['evidence'][i]:text+=f"   - [{e}]({evidence[e]['url']})\n"
 text+='\n'+r['interpretation']+'\n\n'
text+='## PPWM 查询范围\n\n- https://arxiv.org/abs/2610.08627\n- https://arxiv.org/html/2610.08627v1\n- 网页搜索：Parallel Predictive World Models GitHub\n- 网页搜索：PPWM Wanjin GitHub\n\n原始摘要/HTML页面与标题/作者搜索未提供可核实的作者仓库；不使用第三方教学实现代替。\n'
(W/'RESULTS_B_ZH.md').write_text(text)
# Preserve complete cited source files and license files in a small redistributable evidence bundle.
for e in evidence.values():
 root=W/'swm_pypi_0_0_6' if e['repo']=='swm006' else W/'repos'/e['repo'];src=root/e['path'];out=W/'source_evidence'/e['repo']/e['path'];out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(src.read_bytes())
for name,r in repos.items():
 status=subprocess.check_output(['git','-C',r['path'],'status','--porcelain'],text=True);assert not status,(name,status)
 for src in Path(r['path']).glob('LICENSE*'):
  if src.is_file():out=W/'source_evidence'/name/src.name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(src.read_bytes())
(W/'AUDIT_RECEIPT.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rows':len(rows),'cloned_trees':len(repos),'all_git_worktrees_clean':True,'source_files':len({(e['repo'],e['path']) for e in evidence.values()}),'static_only':True,'PPWM':'NOT_FOUND','new_experiments':False},indent=2))
print('B COMPLETE',len(rows),'rows,',len(evidence),'source ranges')
