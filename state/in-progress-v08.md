# 0.8 当前修复，2026-10-19（尚未部署）

## 16:32 最新停点

原正式0.7对照已复现同一生成错误：native-generation-v07-seed4077752896，宿主2A/CS70/TDFC99/WBDF9，合并关闭、普通48×25，第一次生成成功，第二次Unit.run→stepInvis→preStep #1010/Mole rat。说明该路径本轮前已存在，不是0.8新增，但内部根因未修；不能称无模组原版也已复现。12886已结束，finally恢复A61/B5/032/0BD，LAD514/RV763保留。

当前第二次performance-v08-rv323等待在session52012（尚未启动AIR），即将超时；结束须确认无flags/自有AIR。16:31收到RConnect任务消息，其仍独占双AIR窗口，后续才交回；没有回复（人类用户此前选择不发消息）。暂不新增AIR/部署，与其当前回归保持隔离。用户没有取消或要求暂停本任务；剩余是当前RV无争用native/large射击及3加载、门禁备份安装冒烟。所有候选/功能验证已完成保存，勿把等待说成已交付。

## 16:26 接续（最新）

20483已完成：native-release-r2 51、factory-release34+内容像素10、experience-release113、upcoming-release600帧缺块/补绘0及9830400像素严格相同。原生工厂内容对照前两层11/95像素≤1级差、显著/alpha差0，勿称全图完全相等。

正式RV由其他任务在15:26部署0.32.3/76314B819151FBA6F67F6D740B21030A9EEC8359AF4C9C9DDEB83D4CAF5C46B7；清单33DE189E1209FDD397E811A52E9AC67FF0DEDAEEAE5CFEFF4B7D15D4536EB133仅移除禁用ModSettings，14启用项未变。已同步隔离RV；新组合experience-v08-rv323 113、upcoming-v08-rv323 600帧/像素通过。四个本任务候选不变A61/B5/032/0BD，正式四文件仍2A/70/99/DF9。

LAD细分诊断EFC3完成22检查；未复现此前持续热点，灯具visual已有状态缓存，不改生产。已恢复LAD514。脚本lad-profile.py/build及run-lad-profile.ps1仅诊断。最新探针62017字节（增加native generation复查，生产四文件未重编）。

performance-v08-rv323.ps1在56940等待300秒无10秒空闲，未启动性能实例。接续必须补当前RV的native/large真实射击及3次载入；不得复用旧RV性能说当前已测。upgrade-v08已经绑定新RV/清单和待验新性能，明确仅保留4份旧RV机械证据，尚未Check/Install。

现在session12886跑native-generation-check.ps1：临时切隔离副本到**原正式2A/70/99/DF9**，大场景关闭，固定布局种子4077752896重复最多6次第五阶段原版地图，复查之前Radscorpion错误。finally恢复候选；不要中途运行别的runtime测试/替换。此前部分彩蛋/实体生成仍Math.random，固定布局种子不是完全固定世界。退出后看result/error/suspects，再处理门禁与部署。不发跨任务消息、不停他人AIR。报告scene-v08-20261019已更新，尚未git提交。

## 16:01 接续（优先于下方历史）

正式仍0.7，未部署。最终冻结与runtime均为宿主A61EA4A3、CS B5E8110E、TDFC03243196、WB0BD209A1（0.5.8-scene），LAD已恢复正式514A7671、RV正式2E7150CF。完整指纹见build/candidate-v08-final/frozen-hashes.json。LAD两种实验均无稳定收益，源已恢复；拒绝实验补丁留build/lad-rejected-cache-experiment.patch。不要部署旧872/314、弹痕914E或WB6EF。

当前有效进图：loading-v08-trim-1/2/3，3854/3997/4864ms，无其他AIR、真实原版beginMission、全逻辑预生成。combat-trim待机50/51ms、步枪58ms、加特林70ms，真实40/119发；仍不称全部流畅或原版水平。原版战斗参照遇其他AIR中止，待补。mechanics-release27通过；wall-trim-release-r2双样式24通过，6组各112图片可见像素零差异。动画清点仅3离屏播放剪辑，不继续猜测大量隐藏动画。

两个失败均保留：wall-trim-release第五阶段生成中原生Unit.run/Radscorpion #1010，发生Land构造预步进内、连续合并前，尚未在旧正式复现，不称已修/已证实原版问题。native-v08-release因测试探针早于ModSettings加载读设置#1009；已加实际设置页ready门控，仅重新编译隔离探针（60379字节），宿主/CS不变。native-v08-release-r2及后续factory/experience/upcoming正在session20483。门禁已改用成功wall-r2和待验native-r2，未执行Check/Install。

下一步核对20483结果、factory像素审计，补无争用原版参照，处理验证发现，再按本机授权门禁/备份/部署/正式冒烟；更新各自记忆并只提交本任务改动。无新增子代理/Ghost/跨任务消息，不停止其他AIR。CS没有AGENT_SCOPE.md（已核实目录），沿本任务现有授权与根治理执行，不新建保护文件。

## 14:29 接续

正式仍0.7。完整当前回归 A61/B5/032 + LAD872：native 51、factory34+内容像素10、experience113、upcoming600帧缺块0/补绘0/像素通过；LAD缓存21像素/失效检查通过，但ABAB命中少、无明确帧率收益。门/边框/奖励/移动机关/远敌睡眠已有前述证据。最新干净进图 `loading-v08-current-1` **8862ms**，用户RV关闭，仍未达2–5秒；首屏原生侧4484ms、WB监听区3535ms。绝不拿旧v07三轮4.4秒作当前验收。

弹痕小画布实验已拒绝生产：首次B16因旋转抗锯齿像素差失败；保持原绘制原点的914E候选 `impact-v08-pixels-r2` 26断言全过，但100次ABAB1060/1023/1007/1011ms无稳定收益。已移至显式 `decal_compact_experiment.py`，prepare默认不调用，runtime恢复A61/B5/032（LAD仍872）。不得部署914E或B16。

当前新增仅实验WB隐藏边缘不计算：精确f32+0.5.6生产配方，独立生成 `wb-trim-source` / `candidate-v08-wall-trim`，不构建WB开发HEAD；CAF B36E…04D0D3（完整看文件）已进隔离runtime，版本0.5.8-scene-test。保留原padding用于采样，仅跳过完全落在scrollRect之外的前景tile/背景strip。`issues-v08-wall-trim` 正在session72863，无其他AIR时启动；结束自动清wall-trim/user-vision/stage5 flags。同一场景4次重建比较可见像素和耗时。未验证、未部署；若无收益恢复正式DF9。

目前runtime：A61/B5/032/LAD872/WB CAFB36E6440A5287594A85426BD892313A790E167C1BD4EB04B65F069904D0D3。upgrade-v08草案仍只认A61/B5/032且依赖指纹/加载门槛不满足，不能执行安装。需要继续性能工作、候选决定、门禁、备份部署/冒烟、记忆与提交；本轮未提交。

## 13:43 接续

用户“继续”。正式宿主/CS/TDFC/清单仍 2A/70/99/87E，未部署。冻结 v08 仍 A61/B5/032；当前 runtime 加入 **未验 LAD 候选 0.3.2-scene / 872EC9C0D45B802FB8E3A8619BCF378F5396729ED37E5BFED4825BFF033A9CC5**（其他仍正式）。不要直接部署这个候选。LAD 干净 HEAD a2d28af 上新增精确输入光照图复用与等价遮光哈希循环；仅大场景复用，普通房间保持重画。作者授权来自本会话此前必要 LAD 兼容许可。源/记忆已改，尚未提交/部署。编译在 CS/build/candidate-lad-v032，不改 release。新增 ContinuousSceneLightChecks 的 21 项像素/缓存失效检查，light-controls 四组开关对照，正在独立 session33457，evidence issues-v08-light-cache（DiagnosticsOnly + HighQoS），不能当正式性能。

issues-v08-mechanics-final 当前 A61/B5/032 +正式 LAD：27/27通过，含122远处睡眠、靠近/追击/受击/弹体唤醒、子弹继续运动、关闭恢复，以及奖励池、移动机关。loading-v08-qos-1 被其他 AIR 争用主动中止，无有效结果，后续 combat-qos 未执行。

前一上下文 session18077 已结束：combat-native-r2 与 combat-320 都 ok（加特林已实际119发），但机况波动很大，native待机64/76、射击78/94ms，大场景87/73、112/151ms，不可宣称已达原版。早先40–43ms参考未能稳定复现。

新增 issues-combat-profile.py / issues-combat-build.ps1 从当前候选源做诊断，restore-v08-runtime.ps1 恢复冻结宿主/CS/TDFC（不恢复LAD）。主诊断 issues-v08-combat-profile 无争用但有计时代码：120帧加特林 player.step 2150ms、Bullet973ms，其中sceneApply713ms。detail首轮插桩嵌套try触发FFDec VerifyError1031，只是诊断失败；改为调用点计时后的 detail-r2 通过。后者有并发，仅归因：LAD child tick 待机约5–7ms、开火约16–18ms；弹痕bounds <0.2ms/次，成本主要每块regionAction中的实际绘制。没有修改原生lighting，因为证据显示不是热点。未做碰撞/伤害简化。

新 upgrade-v08.ps1 草案已写（仍绑定三文件旧候选和待跑证据，**未通过/未运行安装**）；installed-smoke 支持TDFC标记；regression-v08.ps1 顺序跑 native/factory/experience/upcoming，尚未启动。若接纳LAD候选，门禁需增第四文件及新哈希/光照测试，不能用旧LAD证据冒充。

精确调用授权新坑已定位：PowerShell ConvertFrom-Json 会把ISO UTC Z日期解析成 DateTime，guard再DateTimeOffset.Parse隐式字符串会丢UTC，导致许可立即“过期”。使用 RFC1123 GMT expires_utc 后 Test-GuardGrant 真且原始命令通过。没有修改guard或关闭hooks。事件文件 build/generated/grant-v08-lad-runtime.json，Bash+command，session01a13816；最新9分钟许可约13:50到期。按既有明确授权登记，后续仍逐条精确绑定，不用别的执行形态绕过。后续应记经验（未贡献共享库）。

## 12:37 最新

当前 runtime 与 candidate-v08-final 已同步：host A61EA4A30F0E4978173F2B92B5F33A02960098D706B810FC6196105278EFA73F，CS B5E8110E11FE2DF8A748B223DFFA6E0EC42E4F61A931D4D4E065CC199EFA2F1B，TDFC 03243196C99D6C4F1A2BE081598DBAE9B5D89A414BCD48E1F860232BCFDDE1E5。host 新增 sceneChunkSide 诊断入口，**生产默认仍320**，sceneOpen 仅允许640实验值。审计4665/1015保持。TDFC正式仍99BF，root正式2A/CS70，未部署。

离屏wrapper原型仅由探针引用，不接生产：`SceneObjectCulling.as`。初次试验因读取内部lurKBox属性1069失败；改为所有Box.lurk>0保留直接父层、念力对象实时解包并置顶。`issues-v08-object-viewport-r2` 无争用、全部通过，四次逐像素一致；全绘/裁剪/全绘/裁剪中位44/44/43/44ms，裁1599图像，脚本11→13ms，**无收益所以拒绝生产接入**。

`issues-v08-combat-640` 无争用：640块待机42/41ms、突击步枪57ms、预热最大329ms（静止已热完16块），未显示足够收益，不启用默认640。加特林0发导致整体失败，不能当完整战斗验收。`issues-v08-combat-native` 原版房间参照（同全部14模组、用户RV enabled0）待机40/42ms、突击步枪45ms；加特林同样0发。查native Weapon.checkAvail确定初始1级角色技能不足，并非枪逻辑/CS故障。

探针现已只为隔离测试将minigun.lvl/perslvl设0，保留原版射速/弹体、每帧补弹和耐久，持续按攻击而不脉冲；采样暖机30帧后计实际弹耗。源中新增native-rooms-controls.flag基准、combat-controls.flag四组、large-chunks-controls.flag实验、user-vision/stage5组合；记录entryMs、chunkSide、预热次数、武器状态。**最新探针已编译56827字节**。

正在执行脚本session18077：先 `issues-v08-combat-native-r2`，成功才接 `issues-v08-combat-320`。两轮顺序、独立AppID，finally清combat/native/user/stage5flags；每次先等稳定空闲10秒（test.ps1已新增，避免其他任务两轮间隙误启动），最多300秒。需要续查结果，别开第二个runtime写入。测试必须escalated，否则存储Error3001且看不到其他AIR；旧result不能冒充新结果。所有控制flags冲突检查已有animation/activity；还可完善其他组合但不要中途重编产物。

后续重点：完成真实战斗对照，以原版同模组40~42ms为参照而非武断宣称33ms。若320开火仍明显差，按热点继续修；现有native暂停收益已实测14~17ms两对。待最终候选固定，重跑mechanics（补动画暂停同步后版本）、NativeMap、Factory/Experience/进图2~5秒/连续移动像素必要回归，再新建v08精确指纹门禁/备份/部署/冒烟。**新门禁仍未写，未部署，不能最终声称完成**。保持用户“不跨任务发消息”限制。

## 12:18 接续（最新）

正式文件仍 untouched。当前 runtime 宿主 ECCEE092…1FA426、CS 5772E80A…BAD92、TDFC 03243196…DE1E5；冻结 candidate-v08-final 的 CS 仍 AB4C…旧副本，**勿直接部署冻结目录**。TDFC 现在带 scene-compat v0.6.4-scene1 日志。CS 睡眠时同步一次 setVisPos，并停止当前正在播放的子动画，唤醒时只恢复未被其他逻辑改帧的播放状态。持续效果/移动机关豁免。

`issues-v08-activity-mechanics` 27断言中26通过，唯一炮塔差1像素。后查为入场地面矫正后、首次step前图像还未同步；加入首次睡眠setVisPos，动态图像改在120帧稳定点核对。该轮所有暂停/唤醒/子弹和奖励/移动机关断言通过。

`issues-v08-activity-stage5-diagnostic` 无其他AIR但标记DiagnosticsOnly，不作正式性能；中断后的旧 animation-controls.flag 遗留导致四组名称被覆盖，实际按activityControls暂停/全运行交替；已删除遗留并新增互斥检查。不能复用错误组名。TDFC heartbeat 30~32单位约3ms vs 全运行152约12ms。

`issues-v08-activity-stage5-r2` 正式无争用、ok true：同世界暂停/全运行/暂停/全运行 median43/57/55/72ms，P95 56/76/68/86，脚本中位11/23/17/20；暂停101/99单位，正常仍81~82单位（含尸体等）；已有CPU收益但还达不到原版30fps。因运行世界逐步变化，不把四组视为完全静态一致快照。

正在验证 `issues-v08-object-viewport`，只在**探针**启用 SceneObjectCulling，CS生产入口尚未调用。用零变换可见性父层控制离屏图像，实际vis的visible/alpha/filters不动；念力/藏身目标保持直接父层，保留原版提升层级。四组ABAB加逐像素比较，若无收益/行为失败不要接入生产。等待脚本 session70882（先等空闲300s）；测试结束后清flags。禁止通过其他API/改指令形式绕过钩子，精确调用授权按既有用户许可登记，刚用 grant-v08-activity.json 已过期。

## 12:00 最新停点（优先于下方历史）

用户已明确接受远处未参战敌人暂缓行动；另明确允许必要 TDFC 大场景兼容。NativeSceneActivity 新增独立调度字典，不改 units/碰撞/disabled，附近和镜头预热区、追击、受伤、持续效果、弹体路径保持活动；追击/受伤粘性保活。Location.step 只跳过睡眠单位，原生子弹和物品照常运行。TDFC 当前源码只增同字典桥接；构建冻结正式源码 fb73655，再注入同一小段桥接，不夹带 HEAD 未发布 authority 工作。

当前 runtime/冻结候选宿主 ECCEE092…1FA426，CS AB4C3FFB…96FD11，TDFC BBFB32BB…69FAAD；RV/WB/LAD 保留正式。宿主审计 4665 方法/1015 类布局/原常量池保留，六个定向原生方法（新增 Location.step；另含 UnitPlayer.animate 同帧重用）。尚无这轮性能成功证据。第一次 idle-reuse 测试误在受限沙箱运行，Error3001、没有新结果，已 Ctrl-C 清理自有实例；不采用旧 result。后续测试须 require_escalated 让独立 AppID 可以写入自身存储，并能看到其他任务 AIR。

已启动 issues-v08-activity-mechanics（独立 PID55344），等待功能结果；包括靠近、追击失视、HP变化、飞行弹体、关闭调度恢复全员，及奖励/移动机关修复。测试结束后做同世界 activity-controls.flag 对照、动画重用对照、stage5/工厂/载入回归。正式文件仍未动，门禁/安装/记忆收尾未完成。

用户反馈：两侧黑边；互动提示在但门图像错位/缺失；静止持续卡顿。用户已保存退出。本轮没有发送跨对话消息、没有启动子代理或 Ghost。沿用既有 CS/RV/WB/LAD 必要兼容及精确构建授权。

基线正式宿主 2A466248…FB3EA / CS 70C06879…09D5 / RV 2E7150CF…07A10 / WB DF9AA072…8F76 / LAD 514A7671…7F6；清单 87E430DC…CBD 已由其他工作调整，不回退旧清单。冻结 build/cache/v08-baseline。

已证实：原版马哈顿 240×125、189 单位、586 物体，98 扇门中 95 扇显示坐标错误；边框 scale 全被预绘重置成 2。baseline / alignment 两轮真实复现，完整结果在 evidence/issues-v08-baseline、issues-v08-alignment。同世界只修 Box 坐标未降低卡顿，不能把显示修复称为性能完成。

当前代码：Box.runVis、Unit.setVisPos、其他 fe.Obj 独有 vis 平移、vis2 平移；BackObj 共享模板明确排除；递归自身 area 和 inter.area；类查找缓存。边框只在 sceneOpen/原版整房初始化，后续 sceneRepaint 不重置。CS 标记 0.8.0。

第一次候选（尚不含后补 area/inter.area 与类查找缓存）：宿主 D530A4EC…EE4FC、CS 9FA668C1…5F9BC。审计 4671 个无关方法、1015 类布局、原常量池保持。issues-v08-rv-profile 16 项通过：103 门、125 Bonus、74 Trap、8 CheckPoint、8 Turret，全部显示坐标正确；入口/稳定/左右三档缩放边框正确。此轮 RV 是诊断副本且存在其他 AIR 争用，只是功能/热点依据，不是生产性能验收。issues-v08-visual-fix 因中途争用被主动终止，仅部分功能结果。

性能：正式旧版本 baseline 静止 median 74/P95 103ms，Location.step 平均约 11.5ms；禁用 RV/WB/LAD 的对照约 47ms（仅诊断）。新视野计时指向 updateWallSurface，120 帧 2163ms；其他 AIR 争用存在，不能据此声称精确收益。正在跑 issues-v08-wall-profile，进一步分解 contour 与采样成本。不要把旧结果文件当当前新采样；检查时间戳/证据目录。

构建：candidate-v08-build.ps1 从 2A 定向重编 Grafon 并审计；DriverOnly 编 CS，ProbeOnly 只编测试；issues-build -Profile 会重置 runtime 为旧正式 CS，仅用于复现。issues-rv-build 只在 CS/build 中复制并诊断准确 RV 0.32.1 冻结生产源，不改 RV 工作树或 release。测试 runtime 串行 session.lock，性能拒绝争用，DiagnosticsOnly 的帧率不验收。test.ps1 支持被动 WaitForIdleSeconds，独立 AppID。

收到另一个“大场景 (2)”任务的已授权单向协作通知：它独占 build/object-audit，仅运行对象功能测试、不修改我们的源码/版本/共享 runtime/部署。不要提交或覆盖该目录。它提示 Bonus 原房 kolXp/maxXp/unXp/summXp、Unit.die 的经验池、detecting、Interact 内部移动端点等合并遗漏，当前仍待核验/修复，不能称完整原版机制全部正常。本任务未回信（当前会话原授权为不发消息）。

## 11:31 接续

当前冻结正式候选（未部署）：宿主 `138D4DF67B24FBA097A9E3125CB3B4AB757B852A18A197201DA20D7184BE09A9`，CS `CEA1654F0C8C10B437CF4B0842CA40E9D3E8BF6129D696E552BFE935EC7B436C`。最新审计保留 4667 个无关方法、1015 类布局、原常量池。Grafon 边框修复，加四个定向原生方法：Interact.move / Bonus.take / Unit.die / Unit.setCel。Adapter.rewardOwners 保留每原房的 kolXp/maxXp/unXp/summXp/detecting，原始敌人追过边界后仍归原池；活动场景新生成敌人原版 xp=0。原生声音/动画/掉落照旧。

`issues-v08-native-mechanics` 奖励/跨区击杀/发现归属及移动机关前进返回均通过，唯一失败为 fixture 初始坐标在等待 120 帧后测量（箱子已受重力下落），已改为 prepare 刚结束时记录，尚待最终候选重跑。测试代码 `ContinuousSceneMechanicsChecks.as`，通过 `mechanics-controls.flag` 启用。

性能配置已明确：正式用户 RealisticVision enabled=0、mode=current、wallbright=0（只读检查，未改）。IssuesProbe 为保留效果主动开三视觉模块，默认墙常亮关闭，另作常亮对照。原 baseline/alignment/profile 初期继承 wallbright=1，不能当用户当前配置。
默认关闭墙常亮后 RV 热点诊断约 11.3ms/帧；常亮约 29ms/帧，二者诊断均有其他 AIR 争用，不能作为正式帧率。默认热点为 full wall-field 约3.1ms、准备遮挡约2.1ms、轮廓约2.1ms、敌人显示约1.6ms。

`issues-v08-final-functional`（宿主29679245/CSC2A01521，含移动端点但不含奖励）16项门/静态物体/所有边界缩放通过；有其他 AIR，仅功能证据。无绘世界对照中位34ms vs 关闭RV/WB/LAD但绘世界47ms；实际游戏逻辑仍运行。

三轮无争用绘制诊断（全部关闭 RV/WB/LAD，只用于拆分，不是产品配置）：`issues-v08-render-controls` baseline50ms→静态一次隐藏离屏1744子图形41ms；整世界scrollRect46ms；隐藏原生光层39ms。`issues-v08-clip-controls-r2` baseline48/整物体层裁剪47/原生光图裁剪45/合并47ms；`r3` baseline57/离屏1921子图形空scrollRect53/光图53/合并53ms。整层或空scrollRect没有稳定足够收益，**未加入生产代码**。初轮clip-controls因读取私有lightBitmap失败，已改读visLight第0个子图形；不把失败轮作为性能证据。隐藏离屏试验只有一次性诊断，尚无安全的逐帧生产实现。

当前 runtime 是**玩家细分诊断宿主** `0A153CA42978C85EFB2115D0174B7BD789C8CC0D8150F53F70F7B618ED6F75F6`，不能部署。`issues-player-build.ps1` 从最终候选生成只供诊断的 Unit 类，记录 player forces/control/run/checkWater/actions/setVisPos/animate。运行中的 `issues-v08-player-profile` 为独立 AIR，结束后应从 candidate-v08-final/pfe.swf 恢复真实候选，再验机制与回归。仍无已证明的游玩性能提升，不得称卡顿修好。

另一个物品调查已提交自有 `4b805eb`（7新文件）。报告 `knowledge/experiments/native-object-audit-20261019.md`，最终 `objects-candidate-plant-r2-20261019` / `objects-candidate-mane-r3-20261019` 同源人口/静态位置/影子/挂载/原生E容器cont变empty/马蹄铁碰撞拾取通过；冻结CS1DB6AE72+旧宿主2A，不能冒充当前宿主验证。该任务用户授权它发送单向协调，本任务未发任何消息。它已释放 AIR，之后不再启动测试。不要修改其已提交报告来扩大覆盖。

后续：完成静止/开火性能优化；真正候选重验奖励、移动机关、工厂/马哈顿（含截图stage5）、入口/交互/连续移动；新 v08 门禁和安装备份尚未写，正式仍0.7；更新 MEMORY/journal 并仅提交本任务文件。其余 RV 性能/阶梯候选仍是它们的 WIP，不整包编译其 HEAD，不覆盖后续正式部署。
