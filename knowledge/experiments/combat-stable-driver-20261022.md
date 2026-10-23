---
domain: knowledge-validation
type: experiments
game-version: ["1.02"]
confidence: medium
verified: false
discovered-by: ContinuousScene
date-updated: 2026-10-22
evidence:
  - kind: source-and-artifact-audit
    summary: "旧运动驱动存在换房重置副作用；0.8.2构建误带入已拒绝的compact弹痕实验。新的实际交战短窗对照尚在执行，不能宣称优化达标。"
---

# 战斗驱动修正与 compact 路径追查

本轮承接用户“继续尝试解决战斗卡顿，直到卡顿出现明显下降”。正式基线仍是回退后的 BEFC，CS 0.9.0 / 7F1F，不能重新安装下午撤下的 7D42 / 5432。另一会话天角兽 1bf0e7b 只源码，SceneRenderChecks.as 他人 WIP 不接管。本记录不是发布回执。

## 旧驱动的实质限制

ContinuousSceneMotionProbe 原来每帧调用 `UnitPlayer.setLocPos`。原生方法会调用 `setNull`，其中重置武器、动作、攀爬和浮空状态，重设滤镜、alpha，并创建新的 ColorTransform。这是换房定位接口，不是只移动坐标。旧“高速交战”主要证明敌方开火，不能据此断言玩家持续开火的真实帧耗时；逐帧视觉状态重置还可能干扰显示缓存。

这项发现补充限定 `combat-recovery-followup-20261021.md` 以及更早移动驱动的结论。保留原始失败/计时证据，不把改进测试驱动产生的速度变化算作游戏优化。原生 Unit.setPos 只更新坐标、包围盒和目标点；新 `--stable-motion` 使用它，不改武器计时。自动往返依然是隔离测试轨迹，最终还需普通输入/真实玩法验收。

新 `--player-fire` 使用原生 assr，隔离角色豁免装备等级、补弹与耐久，保留原生射速、弹体和伤害。等待换枪 t_work 结束，实际连续开火暖场100帧且至少5个出膛帧后计时。固定6名 autor 敌人在该模式提高HP至100000，以稳定活跃人口；因此不涵盖正常死亡、低血逃跑的性能。

玩家用补弹前实际扣弹确认射击。敌方旧 shots 是 t_attack 上跳（攻击周期）；新增 actualShotFrames 读取公开 gun.b 的新子弹身份，确认 owner/weap，不能把攻击计时或暖场开火冒充测量窗口实际射击。各窗口记录双方实际射击增量、瞄准帧和首尾存活/持枪人数。

## 被拒实验误带入正式构建

实物和方法级核对：

| 产物 | compact helper | sceneApply |
|---|---|---|
| A61，0.8正式 | 不存在 | 904字节，方法代码SHA前后缀 0a2fcb14…78221 |
| 02BF，RC合并后 | 不存在 | 与A61逐字节一致 |
| 914E，被拒实验 | 存在 | 实验分支 |
| 4D9，0.8.2候选 | 566字节，3edf92f2…c09435 | 941字节，acc05351…54b1c |
| 81C1，0.8.2正式 | 同4D9 | 同4D9 |
| BEFC，当前正式 | 同4D9 | 同4D9 |

上述正式链各版 sceneApplyRegionAction 均1453字节、63d26ccf…4427，逐字节相同。BEFC sceneCompactImpacts 槽的 value_kind/value_index 均为11，默认确实为 true。

`scene-v08-20261019.md` 已记载 compact 被拒：移动光栅原点出现像素差异；保留原点的版本虽26项检查通过，400次自制素材调用 ABAB 1060/1023/1007/1011ms 无稳定收益。没有找到旧 full-impact/small-impact 整帧对照实际运行记录，代码存在不等于做过验证。

提交76dd47d的 `build/motion-host.py` 却错误声称该路径已在02BF内，无条件再引入 `decal_compact_experiment.py`。`state/deployment-v082.json` 记录2026-10-20 02:11将02BF部署替换为81C1；BEFC后来完整保留了Grafon此部分。已修正旧配方注释，明确它只是历史0.8.2重现，不是新生产构建入口；本轮尚未改正式方法。

compact每个小弹痕分配临时BitmapData，两次copyPixels后dispose。它临时改变rectX/Y，而跨颜色区 sceneRegionEnsureScratch 按该尺寸匹配，可能释放并重建4张scratch。这是静态存在的次级分配路径，实际命中频率和整帧收益待测。

最小候选应只改 sceneApplyCompactDecal 的方法体，保留交集/isEmpty/整数包围盒，再直接调用 sceneApplyRegionAction。精确参照 BEFC `sceneCompactImpacts=false` 路径；不整体复制A61.sceneApply，因为会丢当前 sceneCancelWarm(affected) 修复。先在同一BEFC实例切公开开关验证，收益成立后再做严格单方法产物。

## 新对照及运行状态

- `shortlayers`：1500帧，五种显示控制、30帧短窗，Williams排列和逆序平衡位置及前序关系。隐藏内容仅作归因；不作完整画面性能验收。第一帧转场排除后，每控制290帧；计时残差不称纯渲染CPU。
- `compactshort`：800帧，100帧对应一个完整往返，开关顺序 true/false/false/true/false/true/true/false。每段排除第一帧，记录99帧及射击负载；画面像素另测。
- 两者要求每窗玩家及敌方真实射击、首尾6名敌人存活持枪、原Location保持、视口无缺块，退出恢复原控制。源指纹和探针指纹一并冻结，拒绝运行过期探针。
- r1：用户正式游戏PID97400运行，启动前拒绝，未编译未运行。
- r2：探针编译成功；私有桌面 CreateDesktopW 被沙箱拒绝，尚未 CreateProcessW。无AIR样本；原失败证据保留，核对无遗留AIR后释放自己的登记 c03c5a4e…faf8。
- r3：使用同一已编译探针，以创建隔离私有桌面所需权限运行。1500帧完整，玩家实际射击500帧，100帧暖场34发；移动方法总1599次仅1ms，无缺块且控制恢复。Python逐窗门禁失败：第1窗及后段多窗敌方未实际开火，不能当持续交战验收。诊断中位/均值：all 53/56.72ms、none 36.5/41.49、boxes 39/41.93、units 51/54.99、effects 43/46.04。该差异指向角色层（含玩家/敌人/武器/独立手臂）的显示开销，不足以单独归因远处敌人。
- `compactshort-player-r1`：800帧、10个游戏断言及逐窗校验通过；玩家实际射击267帧，每99有效帧均33发。true/false/false/true/false/true/true/false窗口中位54/58/58/56/60/54/51/53ms，均值56.79/62.08/61.12/59.37/64.27/56.07/53.38/56.33ms。敌方逐窗实射24/21/20/22/38/20/1/2帧。关闭compact没有收益，前四窗火力相近仍更慢；尾段火力下降须保留。不因历史误带入就贸然部署关闭开关。

旧floorAt各自找最近地面，r3玩家y=4559、敌人分别y=4639/4859/4899，不是共同平台。autor弹匣20、NPC45帧换弹会自动补满，不能用它解释630帧全部停火。movingFrames只是dx/dy非零计数，不排除睡眠残留速度。新夹具须选择真实同层、连续支撑和净空的路线，缩短为400px往返；增加首尾实际坐标、sleeping、武器弹量/换弹/状态观测，保留AI。高HP只用于持续压力诊断，会影响原生受击shok等比例机制，最终真实玩法验收不得仅依赖它。

尚无本轮新候选部署或性能达标结论。下一步先验证修正后的固定交战负载，再据短窗证据选择候选，最后像素、玩法、完整效果、普通房及安装后验证。

## 同层实射路线与屏外角色层归因

新增 SceneCombatRoute 只选择真实地形，不修改地图、强制AI或重置敌人。要求连续完整地板、120px净空、排除实体箱体/梯/水/陷阱，并用原生isLine检查5个玩家位置×6敌人。400px路径所需1200px净空在本图不存在（最长1120px），`unitviewport-route-r1`明确失败；没有静默改用更短路线。随后显式选择200px，玩家x4320..4520,y4119，六敌x4840..5240，同高度、320px安全间隔、80px敌间距。移动4px/帧，100帧往返，不能称高速移动验收。

`unitviewport-route200-r1`1200帧、20断言通过，玩家400次实际射击，敌方暖场101到结束1005，四段增量244/243/203/214，六敌存活。ABBA只在B包装裁剪角色层屏外根，隐藏199/204个；中位63.5/60/57/59ms、均值66.64/63.78/58.38/61.60ms、P95为91/86/71/77ms。第一A仍预绘12块，最大116ms，其他段无预绘，因此不能把初段优势当裁剪收益。包装本身约0.7–0.8ms/帧，结论只是屏外根裁剪收益小且不稳定，不可发布。

此测试RV已由其负责人独立发布为AB461FF3…F23871；与此前7852版本不能跨轮归因。每轮输入指纹保存，全程RV/LAD/WB关闭，root BEFC、CS7F1F未变。本任务未参与这次RV发布。

末尾只读角色层清点完整、无错误：256个根、边界9295×5029，父层normal混合且无滤镜/遮罩/位图缓存。139个单位身体中18屏内/121屏外；85附件中10屏内/46屏外/29空；31未知根中8屏内。玩家身体仍有51个Shape、无Bitmap；子弹根存在screen混合。大父层边界不等于Flash必定分配整父层混合缓冲，仍需对照证据。

夹具随后加强：暖场等待sceneWarmCount至少100帧不变且完成整100帧往返，再计时；phase4各段记录真实敌方出膛增量及30帧窗口人口/开火，不再允许累计暖场射击代替测量段交战。短窗bulletblend诊断仅临时改活跃Bullet.vis根混合，禁用或退出恢复，外部写冲突使结果无效，不改weapon配置或战斗。任何正常混合带来的视觉差异都只能归因，不能作为最终修复。

`bulletblend-route200-r1`仅编译失败（AS3旧编译器要求catch外显式返回），无AIR样本；修正后的r2完成800帧、11断言与逐窗持续射击/6敌人口门禁。暖场400帧/134实射，sceneWarmCount稳定156帧后开始；测量仍有1次后续预绘，发生在第6窗，其余窗零预绘。false/true/true/false/true/false/false/true窗口中位55/56/59/56/60/61/56/56ms，均值57.03/58.97/61.75/58.57/61.16/69.05/58.62/56.80ms。每99有效帧玩家均33实射，敌方30/38/43/43/49/56/50/42。315个screen子弹改为normal并全部恢复，零冲突/错误，探针每窗7–14ms总成本。没有稳定改善，不把它作为候选。

随后复用现存B8C单方法Bullet.run诊断宿主接新夹具，不重建宿主。其精确构建和双审计指纹已核对；旧方法/素材保持结论依据匹配B8C的严格审计，额外逐原始标签检查被保护钩子拦截，未绕过。bullet-segments-run.py新增源/探针指纹冻结、持续实射门禁及完整证据；计时宿主只用于归因。

`bullet-segments-20261022-route200-r1`完整1200帧、24游戏断言通过，外层30帧严格连续射击门禁失败。首个静止段第1/6小窗无敌射击，其首快照分别有5/4名敌人弹匣为0、换弹计时27–42，属于需保留的原生换弹，不能通过强制射击消除。两个移动段所有30帧小窗均实射，六敌存活持枪。原始失败登记和证据保留，不改写通过。

四段玩家每段100实射，敌方155/215/225/103。每段300帧内，单位扫描及命中回调104/126/118/101ms，即约0.34–0.42ms/帧；直接墙面hitTile为325/445/654/669ms（67/52/71/119次），即约1.08–2.23ms/帧。nativeBand16.79/18.45/18.51/21.99ms，但包含ENTER_FRAME优先级1000至-50间的其他监听，不等于严格World.step。直接hitTile属于terrain子项，不能重复相加。每段另有1次预绘。结论仍不支持先重写全单位子弹扫描；需分离World.step与其他监听、主循环内Land/玩家/GUI/SATS等成本。

`shortlayers-route200-r1`完整1500帧、10断言和全部50个30帧窗口双方实射/六敌人口门禁通过，控制完整恢复。每组290有效帧中位/均值/P95：all60/62.02/77ms、none48/49.91/63、boxes49/51.00/63、units57/59.19/73、effects51/54.11/68。每组玩家90实射，敌方122/113/127/148/156。角色层绘制差额仍约9–12ms，但只隐藏它不能作为修复；native段差异约1.6ms，须保留负载不完全相同的限制。

准备精确BEFC World.step分组计时，以区别World与其他帧监听。静态候选为GUI.setHolder每帧无条件重写同一htmlText，setCelObj还重写后立即读宽高；只有实测占比成立才优化。原生两个字段已绑StyleSheet；getter保留输入串的官方依据：https://airsdk.dev/reference/actionscript/3.0/flash/text/TextField.html#htmlText 。若采用，仅保护相同内容赋值，不跳过目标高亮、可见性、坐标、进度条和prevObj；本轮尚未修改GUI或部署。

World.step诊断构建已完成新导出与编译，严格保留阶段拒绝：`Target activation traits require explicit review`。原step已使用activation但没有槽；FFDec将26个新增计时局部变量编为activation slots1..26，原异常err在独立newcatch对象slot1。必须专项证明每次槽访问的接收对象、名字/类型/默认值及原catch语义，不可全面跳过trait检查。现成compiled.xml/SWF保留，待审核后续构建。未启动此诊断AIR。

按既有用户授权向RV和RC各发送一次测试协调消息；RC明确暂缓19:11–19:17，因离线审核尚未结束，已告知其窗口结束可恢复，不持续占用。atlas重新实验使用当前正式BEFC并冻结探针源，只新增独立检查器，不接管SceneRenderChecks.as的他人WIP；需覆盖真实0.5/0.8/1缩放、分数抖动、即时弹痕/墙变化、SATS、WB叠层及关闭后恢复。新runner对自然30帧换弹空窗如实记录，要求每300帧段双方实射及每30帧人口完整，不强迫AI维持射击。

## 单玩家根缓存：像素失败、无稳定收益

原生 raider 已有小 Bitmap，Bloat 的大部分 Shape 也只是位图填充，不能按 Shape 数把所有角色当复杂矢量。玩家本体矢量较多，但 animate 每帧改变头部角度和毛发/尾巴等，整根缓存可能持续失效。ScenePlayerCacheProbe 只控制 gg.vis.cacheAsBitmap，保留原值、对象/父层身份、外部写冲突和恢复证据，未改画质或坐标。

`playercache-pixels-r1` 当前 scale1、玩家x4320.2时出现63个不同像素，最大通道差7，范围61×59；恢复原缓存值后整屏完全相同，零冲突/错误。此候选不能直接发布。Windows桌面不支持cacheAsBitmapMatrix，不能用它假定修正子像素偏差；官方依据 https://airsdk.dev/reference/actionscript/3.0/flash/display/DisplayObject.html#cacheAsBitmapMatrix 。

`playercache-route200-r1`仍作为诊断运行800帧，11断言及每100帧窗双方实射/6敌持枪通过。关闭/开启/开启/关闭/开启/关闭/关闭/开启窗口中位71/81/70/80/84/85/97/115ms，均值74.08/88.54/71.17/84.19/86.94/91.18/105.80/120.03；没有稳定收益。每99有效帧玩家33发，敌方71/75/74/68/59/48/56/53；本轮额外预绘19块、整体有明显随时间恶化，不能跨轮与此前60ms基线直接作因果比较。3次开启全部恢复，无错误。停止此路线，不安装缓存或降低像素门禁。

## Atlas真实变换与World计时宿主

`atlas-20261022-mane-pixels-off-r1`完成153断言，其中10项像素失败。缩放0.5/0.8/1的原点与回程相同；整数横移第0块仅剩1像素宽时，屏幕x0列37/58/77像素差1。分数抖动在0.8下出现较大周期性行取样差：16169像素、最大96，超过2的11213个差异全部位于y%4==2；不能只补分块边缝或声称整数平移全安全。真实Bullet.run地形命中、原生hitTile破墙各改变2个表面，atlas即时更新完全一致；同步SATS、真实V开启快照、关闭恢复也通过。正式文件保持。

下一精确绘制诊断先比原始中心像素，再单独验证整atlas scrollRect是否复现原生裁切路径。`atlas-mane-combat-off-r1`等待共享占用满300秒暂缓，尚无该计时样本；新runner等待上限改为600秒，仍严格单组占用，不停止其他测试。

World第二次retain因导入类布局漂移拒绝：actionDist:*默认double40000.0变int40000，四字段跨过十方法。专项wrapper精确核验并明确丢弃整个导入类/构造器，只复制step方法到BEFC原类；未将不同编码视为普遍等价，旧审计不变。最终C431D1C1…D049465严格通过：仅World.step改变，4758具名方法、5770非目标方法体、1016类布局/脚本初始器保持，原始素材标签保持，26个activation局部与原catch对象严格隔离。retained.audit.json、semantic-audit.json、build.json及原失败provenance均保留。world-step-route200-r1正在隔离运行，尚无结果，不把诊断计时产物当优化候选。


## World计时完成与Atlas真实交战r2

`world-step-20261022-route200-r1`1200帧、24项通过，各300帧段计数完整、无捕获异常或提前退出。四段World总均14.153/15.240/14.197/16.503ms，Land13.027/14.763/13.457/15.093ms，Camera0.927/0.303/0.473/1.200ms，GUI0.127/0.097/0.123/0.097ms。其他分段均约0–0.003ms。每段玩家100发，敌方101/149/142/104次出膛，六名夹具存活持枪。计时是含子调用的诊断，不是渲染CPU。GUI过小，不继续文字赋值缓存路线。

World末段age270活动107/暂停54，age299 census154活动（其中116为历史参战/宽限/弹体兜底）。前段约39活动。末段大量远处满血无目标，包括TDFC不支持类型；不能仅归因TDFC情报永久标记。原activity用所有!off Bullet的未裁墙dx*4/dy*4矩形，停止弹babah仍保留旧速度，可能扩大威胁；但现有result没有弹体字段，尚未证实触发源。下一步在独立冻结CS副本的原循环内累计区间最大威胁、全局开关、参与原因和首次新醒关联，不改实际调度。

`atlas-20261022-mane-combat-off-r2`完成1200帧/24项及双方实际射击、每30帧六敌存活持枪。ABBA每段去掉切换首帧，各299帧，中位73/62/70/79ms，均值77.602/64.839/76.475/93.094ms，P95 103/87/117/173ms，超过100ms 21/4/31/63帧。脚本25.906/25.936/30.308/32.625ms；玩家每段100发、敌方240/161/158/147发；预绘1/1/2/2块。存在潜在显示收益但后段负载也变化，像素未通过，因此performanceEligible=false、acceptance=false、未部署。该轮活动39–52，未复现World全图增长。

同轮CPU通过自有AIR句柄GetProcessTimes采151点，平均每墙钟秒约1549ms CPU、中位1618ms，表示多线程合计约1.55核使用，不得称渲染线程占用；不能由“dt减脚本”推定纯渲染耗时。当前像素r2增加原始ARGB直接对照和完整atlas scrollRect同帧对照，不放宽原像素断言。


## 调度观测与绘制存储对照（20:38）

activity-telemetry-r1仅编译失败，无AIR；旧Flex不接受动态链字段的前置++索引，改为Object局部显式赋值后重试，旧provenance保留。r2编译冻结六个正式生产类（仅NativeSceneActivity诊断插入，可反向移除完全恢复），完整1200帧/24项通过，遥测errors0。补每段activityEnd覆盖270之后尾29帧、activityStart隔离暖场，区间返回值不被后续wake修改；base+threat+grace与awake严格一致。

四段max awake51/46/47/44，base峰40/42/41/41，threat峰10/0/3/4，grace峰10/6/4/4，TDFC外部wake调用全0；真实玩家每段100射，敌188/145/156/128射。记录证明停止autor弹的残留速度确实误唤醒远处敌人：tick512，弹在4341.73,4054.18，dx−169.38/dy−296.54，babah=true/liv3，仍投射到y2468，触发3980,2639的满血slime；另有tick517唤醒y2319的满血scorp。不能据此声称已复现World那次154全图增长，本轮没有极端激光或全局暂停开关变化。下一步使用独立现成已审停止弹诊断候选配新实射夹具测收益，仍不安装旧候选。

Atlas像素r2所有原始ARGB读取严格相同，整atlas scrollRect没有减少取样差；r3外加40pxgutter及相同裁切原点仍未解决。r4新增14项全部通过：独立Sprite的同帧draw确实使用刚设置的scrollRect（含原点、裁切和恢复），0.8-2的180个与1-2的128个原生bitmap同尺寸copyPixels/clone替换、几何不变和恢复全相同。由此将问题缩小到合并后的显示几何/取样相位；不把全部copyPixels都认作有损。官方属性处理时机参考 https://airsdk.dev/reference/actionscript/3.0/flash/display/DisplayObject.html#scrollRect 。后续只对两个代表视角试横条/竖条布局，不降低像素标准。

Location.step诊断host349F04D4…7041C2完成严格审计：仅step改变，5770其他方法体/4758具名方法/1016类和原始素材保持；30新计时局部+3原局部，307槽操作接收对象、独立catch和18个qualified getTimer逐项验证，10负例拒绝。没有导入布局例外或新类成员。尚未运行，不将计时宿主作优化部署。

## Location归因、停止弹新夹具与横条像素（20:59–21:09）

`location-step-20261022-route200-r1`在349F隔离宿主完成1200帧/24项，每段300calls、errorCalls0、六敌存活持枪，玩家各100次实射、敌184/210/183/221，全部40个短窗双方有实射。每帧含子调用平均：player4.160/4.007/3.963/4.097ms，activity0.610/0.603/0.570/0.540，objects5.503/5.663/6.633/6.773（unit1.277/1.393/1.243/1.250，box0.227/0.153/0.203/0.227，bullet1.557/1.637/2.643/3.040，other1.050/0.987/0.873/0.880），原生lighting2.100/2.280/2.313/2.163。objects包含四子组，不重复相加。总12.387/12.560/13.490/13.577ms，仅诊断归因，不能作为优化验收。

`stationary-combat-20261022-route200-r1`复用已审738F，正式CS仍7F1F；新玩家实射、200px路线、暖场先显式禁用候选，ABBA每段300帧排除前60帧宽限。保留中位56/55/59/59ms、均59.104/58.579/62.713/62.108，P95 72/75/82/80；脚本21.197/21.096/22.180/22.983。玩家每段100射、敌181/134/154/188，六敌存活持枪；awake均43.125/42.625/42.000/41.875。没有稳定明显收益，未部署。误唤醒确实存在不等于当前卡顿主因。

Atlas r5（243项）新增横/竖条同帧诊断：0.8-2横条1756像素/max2，竖条38805/max127；1-2横条1570/max2，竖条147/max1。引用、绑定、清理和恢复全同。r6（245项）把横条上下40px边缘直接从每格nativeBuffers复制，结果与原横条逐项相同，排除该边缘来源；不再扩展gutter方案。下一步先测横条真实交战开销再决定是否值得继续解决max2残差。正式像素门禁未放宽。

静态新线索：BEFC UnitPlayer.control 的currentWeapon.attack后，两条返回支路均调用GUI.setWeapon；后者每次重写weapon.htmlText、读取textWidth、写ammo.text并调用setHolder。因此它计入Location.player，而非World.gui.step，之前0.1ms不能排除该支路。正在准备单方法精确诊断，未声称GUI已是主要瓶颈。

## 武器文字排除与整场景显示归因（22:18）

GUI严格诊断最终宿主156681B01C0367366CB83C91F1CF71AE2B5975C5E4A252CA44E4C33DCFC58A5A，单方法170条原指令投影、5770非目标方法体、1016类与原素材保持，新增计时局部无activation。首轮仅因MotionProbe缺两import编译失败，无AIR；补齐后gui-weapon-20261022-route200-r2完成1200帧/37项，四段每帧total0.1133/0.1133/0.0700/0.1033ms，weaponHtml0/0.0067/0.0067/0.0067，textWidth0.0033/0/0.0033/0，ammoText0.0067/0.0033/0.0033/0，holder0.0967/0.0667/0.0500/0.0733。每段300调用、玩家100发、敌126/193/169/160发，所有40窗双方实射。排除此方向，不为微小占比引入生产guard。

计时结束后SceneHudTextChecks以原GUI.style只读拷贝创建离屏文本框；same-value、setStyle颜色/字号、parseCSS、clear、替换样式、外部HTML、无样式、移除样式、晚绑样式共10组最终像素全等，CHANGE事件均0、原GUI.style未改。无样式/外部HTML等正确重写，其他跳过。该结果不能替代实际HUD字体布局或收益验收；保留原始case像素与布局。

world-layers-20261022-route200-r1在正式BEFC/7F1F完成1500帧/10项，五控制各10×30帧，排除各窗切换首帧后各290样本。all/no-fog/no-terrain/no-objects/no-world中位64/62/52/48/40ms，均67.962/65.410/59.945/52.252/44.390，P95 93/89/95/81/68；scriptBeforeProbe19.324/17.886/18.476/18.072/19.990。每组玩家90计入发、敌196/197/176/175/193，50窗均双方实射，六敌存活持枪；可见性重写0，原引用/父层保持、最终恢复。此处只是显示归因，不能用隐藏作为修复或将dt-script称纯渲染CPU。

atlasrows-20261022-mane-combat-off-r1完成1200帧/24项，ABBA中位61/56/58/61ms，均63.602/59.769/61.465/63.064，P95 83/84/85/84；脚本23.292/25.846/25.753/23.077。玩家每段100发、敌220/189/140/94。约5%净收益，helper本身增加约2.5ms，像素max2仍失败；暂停横条进一步精修，不部署。

后续基线必须从nativeEnabled=false的新Land开始，再gotoXY(2,4)，本地玩家480,119往返200px，六敌1000..1400间隔80。不能在已合并的Land内关闭开关切房：原tile与实体已平移，多个loc引用同dest。原版房1920×1000小于本轮实际2032×1084视口，镜头固定居中而大场景继续跟随；只能作同地形/同六敌体验参照，不能把差额全归调度。真实Weapon.shoot通常在Unit.step childObjs链；玩家control中的GUI不解释其约4ms。跳跃时checkShelf可能扫描全loc.objs，平地路线不覆盖，另行区分。

## 同地形原版参照、透明地形和玩家分组（22:32–23:02）

native-combat-20261022-room24-normal-r1 / scene-r1 共用冻结探针和正式依赖，完整48×25房间hash3340386727、100格路线hash1540339216相同。每轮1200帧，玩家每段100发，六敌存活持枪。原版敌205/166/201/127发，中位33/33/33/33ms，均33.257/33.340/33.950/33.497，P95 40/39/41/40，脚本8.849/9.977/10.580/9.577；大场景敌198/151/147/63发，中位55/61/60/51，均59.813/71.593/64.407/53.683，P95 88/115/92/68，脚本22.000/23.477/23.040/21.130。夹具前总单位10对151、镜头固定对跟随，保留人口与镜头限制。原版entryMs8498含gotoXY及20帧settle，不能作为加载时间。

empty-terrain-20261022-route200-r1 完整1200帧/25项，ABBA各299个非切换样本；中位59/61/70/74，均61.903/65.398/72.866/76.355，合并A/B均69.129/69.132。B每帧隐藏55.35个完整400×400、含gutter且全透明的原生层；更新额外约0.73–0.78ms，清理pendingRestore0。没有稳定收益，停止该路线，未验像素/未部署。源码写入首次被保护钩子归为二进制，子会话grant未生效；按已有明确授权用实际root会话同exact digest登记9分钟，原命令成功，未修改保护器或更换写工具。回执generated/empty-terrain-20261022/grant-main-source-write.json，摘要23f17fe5…e83。

player-only Unit.step诊断宿主00A1D7A3…862007严格审计仅改变step、5770其他体/1016类/原CP/素材保持，355条原生指令投影通过，6负例拒绝。scene-r1每段300normalcalls且10组calls各300、early/error0；total4.190/4.347/4.040/3.940ms，animate3.393/3.440/3.233/3.113，children0.573/0.660/0.553/0.613，control0.107/0.123/0.100/0.100，其余小。六敌双方实射全部通过，帧中位54/61/57/53仅诊断数据。

原房normal-r1在启动前因RV独立发布6593→83D8被指纹检查拒绝，无AIR；normal-r2重新冻结后完整1200帧20项，total3.213/2.927/3.047/3.337，animate2.650/2.237/2.360/2.673，children0.440/0.587/0.527/0.507，control0.103/0.077/0.117/0.120。两轮RV都disabled，但依赖不相同，不能当严格配对精确差值。只确认动画绝对成本显著，且原版也有。UnitPlayer没有step override，先前“遗漏其super前后外层”的说法不成立；实际继承Unit.step，分组animate还包括burning，children保留原catch。后续审animate重复gotoAndStop与远处睡眠根摘除候选，正式仍未改。

## 动画分组、睡眠显示根与夹具悬空纠正（23:35）

player-animate-profile严格宿主E498FCEF…FEAC8C，仅UnitPlayer.animate方法1832改变、2041条原指令投影，5770其他方法/1016类/原CP和素材保持，6负例拒绝。r1因TimelineChecks的try内return不满足旧Flex路径检查而仅编译失败；改为finally后return，r2完整1200帧/25项。bodyState均1.403/3.020/2.137/2.850ms，headRotation0/0/0.003/0.003、filters0/0.003/0/0、otherVisual0.030/0.027/0.007/0.013、eyes0.003/0.017/0.007/0.017；total1.437/3.070/2.153/2.887。每段300normal、early/error0，玩家100发、敌181/193/170/174发。分段计时只用于归因。

ScenePlayerTimelineChecks终端实际pinok16、isPlaying=false，空操作与重复gotoAndStop后完整Stage像素、递归树/部件引用、mark和枪口点一致；第一次重复产生67次FRAME_CONSTRUCTED，0新增/移除，故诊断passed=false并保留原始差异。三张位图全部释放、监听清理。游戏和授权模组源码/正式常量未发现该事件的消费者，但不穷尽动态拼接。正式BEFC已有站立同帧复用且保留frame1脚部mark隐藏；新候选只可能扩到静梯和非levit腾空，同帧且已stop才省略，不能用单pinok16覆盖全部帧和换装。

**夹具新缺陷及旧证据边界**：初始spawn=floorY−1合理，但旧stableMotion在全部暖场/测量每帧setPos(x,y0)，并强写dy=0。setPos不改stay；World.ddy=1且collisionTile对Y2+dy<=phY1返回false，因此永远从地面上一像素刚好接触而不能真正落地，下一帧又被重置。真实落地应写Y=phY1、dy=0、stay=true。旧同驱动A/B原始数据仍保留为诊断，不能当普通站立/行走、跳跃或最终性能验收；native-room旧参照亦同受影响。仅保留Y/dy仍可能walk=0和dx低于行走动画阈值，因此新模式使用真实左右键而非水平setPos，记录真实姿态/位移/落地后采样，越出验证走廊失败而不传送补救。

sleeping-root r1精确Raider无合格者，检查失败、实际移出0；日志110other-class是累计事件，不是110唯一单位。r2只增加构造器设parentId/kolTrs的精确Slaver，不泛化到Pon/Merc/Encl。候选76748C8E…ADA0172，来源证明AF87F1EF…8B4629，helperD1E21A03…19ACD。pixels-r2完整1200帧26项：20Slaver/60根实际移出，detach/restore像素0差；实际zero-clips Slaver唤醒在resume前恢复、父层和entry检查通过，最终123次变动/123恢复，0遗留/错误/抛弃。

timing-r2完整1200帧25项，A/B各598非切换样本，合并中位67/59、均72.380/62.873、P95 105/85、>100ms37/17。但四段中位58/56/64/72、均69.12/59.28/66.46/75.64，A0含887ms长帧；脚本23.88/23.53/25.37/28.69ms。A0/B1 awake38–42、敌243/241发、玩家各100，最可比中位仅2ms改善；B2中段awake跃至约90，A3为84–101，预绘0/12/32/59、resident101→120，敌后段200/134发。移出根36→33，callback约0.27/0.32ms，最终39全部恢复0错误。合并13%不能解释为净收益，需真实输入和更短交错重复；所有performanceAcceptance/deployed仍false。

补充来源限制：布局seed并不固定原生自然敌人种类/人口（r1有19活动Alicorn，另一轮0）。原版UnitAlicorn.telepat对同loc同阵营广播无距离、control有30tick触发，可能造成后段远处目标增长；这里只读正式源码调查，不构建或接管其他会话的Alicorn source-only候选。

## 真实输入首轮与独立窄候选（2026-10-23 00:13）

native-input-20261023-sleep-short-r1 已编译并运行，0计时段、失败保留：初始spawn一次，随后0强制定位，以左右键驱动；真实地面Y4120、stay/floorContact确实建立。原6名autor全部在玩家右侧，暖场齐射把玩家dx推到−19.71、X4358.51，越出已验证[4360,4720]走廊，探针按约定失败，没有复位/删除该失败。不是性能结果。下一轮仅调整新夹具到原平台两侧各3敌、玩家路线居中，保留原生击退、AI和原场景人口，重验地面、身体余量和视线；不通过无敌或强写速度掩盖失败。首轮冻结probe f079c09e23b442ea9129c90a82c42d65保留。

两处空中/静梯条件候选B1DB8FD7…F5CA0E2（XML D3FE8F73…2D6168、审计F79A3515…CFD21）仅目标animate改变，5770其他体/1016类/原CP素材保持，6负例拒绝，无新字段/局部/计时器，未运行。复用sceneReuseIdleFrame开关会同时影响既有站立guard，内部开关结果不能单独归功新增两处；最终须正式BEFC true对候选true或精确隔离新增路径。

sleeping-root r3辅助代码仅扩大7个已审非Pon精确类（Slime/Bat/Bloat/Monstrik/Ant/Turret/Vortex），null childObjs只在这些类且currentWeapon===null时允许，保留原null身份；safeTree/屏外余量/父层归属/恢复/零clips唤醒检查原样。builder A924F632…82CB5D、helper210DD1BF…09B8A5、proof7EFEFC21…0FDF26，仅静态prepare/check，未编译/运行。复用r2 CS76748C8E，live及r2helper不变。写builder曾被hook误归SWF写入；root复核原调用只写.py后按已有授权登记9分钟，原样重放写入，预期regex转义AST错误再正常修复。grant20aa7cb6…a660d0，原args/grant保存在generated/player-airframe-20261022；未改护栏。

## 真实输入否定显示根收益，转向离线采集（2026-10-23 01:07）

native-input-20261023-sleep-short-r4 完整1200帧、90项、20/20短窗双方实射；每场只spawn一次、计时0强制定位。r2睡眠Slaver显示根摘除在五个ABBA块均更慢：A/B均65.857/70.125ms、中位63.5/67、P95 80/95，超过100ms为12/22；排除切换前两帧仍65.60/70.11。玩家200/200射、敌304/318射；awake均42.8/43.6、显示节点仅减少约3.2%。216次变动全部恢复，无遗留。停止r2路线，不以旧长窗合并13%继续宣称收益。r2/r3失败记录为目标余量不足、完整平台边界1px错误，r4使用原生真实允许的中心4305..5295含端点。

r3首轮长像素检查在候选启用前被原生战斗抛飞越平台而失败；随后将画面检查拆为首次10帧真实落地后持有10原生帧的独立检查。sleep-r3-early-pixels-r1 出现#1009，3Slaver/9根全部恢复。r4纯诊断第一次仅编译失败（旧Flex try内返回路径），修复后sleep-r4-early-diagnostic-r2 指向UnitVortex / safe-tree / nodeNull=true；不是已确认childObjs错误。保留原失败与冻结源码，暂缓扩类路线。

background-composite-20261023-early-pixels-r1 在整个10帧内均因foreign-child-or-native-scratch-mismatch拒绝，0复制、0显示变动，不能称像素通过。diagnostic-2只增加原生父层/非surface节点详细读数，不放宽拒绝条件，待运行。

正式RC574D冻结源78份经prepared/deployment核验，75份不变，仅Session、RConnectMod、GameBridge三类形成隔离离线采集候选88CC639E…D0E968。首次host/join在stop前永久撤销资格；默认关闭，载体仅唯一测试appID可用。只gate mirror与RENDER两处presentation/bodyEffects采集，保留wall回放、ports、invalidate、onPerceptionFrame、实际呈现和AI。源码可逐字节逆向恢复；构建来源0BE07E23…EC81C。已编译，尚未运行或部署。UnitPresentation的recorded事件只有capture才标endSentAt，离线可能积留，但标准assr/autor在loc.units先采为非recorded，会700ms淘汰，不能把条件性积留泛化为当前普通枪夹具根因。已向RC负责人说明此限制。

探针加入独立probeTiming，分别记录自身工作、census、save、切换和后置监听器。此前afterProbeBand普通帧约5.6ms包含自身和RC后置回调，不能全部归于任一方；19段末100–212ms是诊断负担。当前正式BEFC/CS7F1F/RC574D未改，其他会话RV发布按每轮指纹冻结；未达到明显改善，目标继续。

## 离线采集首轮出现稳定方向，补连续计时（2026-10-23 01:25）

rc-offline-20261023-native-abba-r1 完成1200帧90项、五ABBA，每段60帧；冻结probe bc3a4692377a44119764ee4e255870f2。88CC关闭/开启A/B段内均66.648/57.582ms、中位63/54、P95 86/77，五块中位改善7/10/6/10/11ms。玩家200/200发、敌403/396发，预绘1/3块；探针自身total2.238/2.268ms、后置监听4.820/0.573ms。候选mirror实际跳过600、final1200，errors0，perception保持、cleanupfalse。只有关LAD/RV/WB、首次联网前的条件，尚未正式化或部署。

RC负责人复核源及实际数据，并指出startCase重设last排除了上一段末now到caseBegin的census/save；原摘要“All frames”不应解释成跨段完整连续墙钟。补充timing-boundary-note.md，原始证据保持。下一轮独立sampleAtMs/continuousFramesMs跨段不重置，明确间隔归到结束段、终端末采样后处理不包含；不扣减诊断耗时伪造净收益。正式化须移除carrier/计数器，另对未改574D实测，首次host无人/join失败/leave/重连以及连接瞬间特殊效果仍需验收。RC负责人负责正式整合，本任务不覆盖其工作。

## 连续间隔复验支持收益（2026-10-23 01:33）

rc-offline-20261023-native-abba-r2，冻结probe 8a70233341d64f6fb68b9dd606f56af8，1200帧90项通过。20×60 sampleAtMs逐项差等于continuousFramesMs，跨段无重置且总和等于末点减起点。A/B主均71.645/60.852ms、中位67/56、P9597/83、>100ms26/19；五块中位差14/7/10.5/8/14ms，均值五块全改善。B第3块max286ms大于A197，保留异常不声称所有长帧消失。旧段内均71.030/60.043；连续主统计按间隔终点归组，包含上一段尾处理，末采样之后的最终清理无后继间隔，不补伪样本。

玩家200/200射、敌367/328，20/20窗双向实射；awake均41.8/41.2，预绘4/0块，落地样本378/398（其余为原生受击/跳动）。probe自身总均2.167/2.438ms，work0.157/0.132、save0.702/0.740、startCase1.233/1.490，后置监听5.294/0.667ms；不把后置所有监听当RC单函数精确成本。mirror600/final1200、errors0、资格始终纯离线，末尾off。两轮十ABBA块方向一致，约14–16%中位改善仅为当前关LAD/RV/WB单机战斗场景，需生产形态对原574D及联网/功能验收后再部署。

生产源码建议已交RC负责人，generated/rc-offline-production-proposal-20261023-r1/source-provenance.json EC95927A…DD045。完整78源75不变，三类精确可逆；诊断接口/计数/开关全移除，首次网络尝试永久撤资格，未知/异常资格执行旧路径，版本未定、未编译。此时正式BEFC/CS7F1F/RC574D保持。BG3早检查因WallBlend类status不可访问拒绝，0应用/0复制；这是探针域入口问题，不能称合成像素失败或成功。

## 正式形态直接对照（2026-10-23 01:54）

RC负责人独立构建0.2.24-offline1，准确SWF EB3653533CFB305BCCA0B0CFE5E81BC306EA28FA400AAE751AB7B5AE1CFA5FEE，prepared C15EE493FDFEB804A2DD39C9710B3127C7BA7F458EFD238F6FAB8443EEA6D5E7，compile DA37C6C00D922DF3B900B9B3E4AC4E086A4DD3309989B49D28EAAF8772AE671D。来源为574D的78源/71工具输入，75源保持，三类最小改动及版本更新；prepared.compiled=false是准备时快照，实际编译回执为true、两工具退出0。按负责人verify及完整产物哈希核验，不仅凭版本号。

build/rc-native-combat-run.py新增rcnative空操作模式，整个进程单一RC版本、20×60真实输入与持续开火、不调用RC诊断API、不隐藏显示、index4/6不切效果。同冻结probe-source/3fa568cbe2464a5ca40d6ccb37705e87/probe-build.json用于原574D和产品EB365；两轮正式其他文件与工具输入相同。证据rc-native-20261023-baseline-r1/candidate-r1，各1200帧90项全部通过，逐项时间戳差与连续列一致，跨段尾census/save不漏计；最终末采样之后无虚构间隔。

| 连续指标 | 原574D | 生产候选EB365 |
|---|---:|---:|
| 均值ms | 69.615 | 58.866 |
| 中位ms | 64 | 54 |
| P95 ms | 96 | 80 |
| >100ms帧 | 51 | 32 |
| 最大ms | 306 | 473 |
| 玩家实际出膛 | 400 | 400 |
| 敌实际出膛 | 810 | 884 |

五个240帧块中位原版63/64/63/66/65，候选54/53/55/53/55；均值全部改善。候选火力并未减少，但AI及自然人口非固定种子、各段负载仍需联读，不能把跨进程全部差额宣称为精确净RC成本。存在473ms长帧，仍非近原版流畅度。该真实场景的明显改善另由两轮十ABBA块同向支持，尚不能替代联机生命周期及特殊效果门禁。无正式部署，RC负责人继续真实Session测试并负责最后部署复验。

独立复核：实际输入仅RC SWF不同，冻结探针字节及配置相同；route1184115388、corridor3092338540（104格）、room3340386727全同。60个活动观测均42.57→42.43，范围36–49→39–50。总units147→149，Merc23→13、Zebra1→11、Slaver17→19、Monstrik18→20（末期19）；自然种类不能当同seed固定。显示节点均3705→3665（约-1.1%）。预绘9/40slices→5/22，中间三块（rc-native-4..15）双方slices/warm/forced均0，累计slice基线337、候选326保持不变，均值仍69.88→56.95、67.92→58.98、71.13→57.96。六敌全程存活持枪，40/40半窗双向实射。nativeBand均19.40→19.60稍高，后置监听5.12→0.53、总脚本27.24→22.68，方向符合RC观察减少。候选473ms发生在段内nativeBand约443ms，没有探针保存/清点/段切换，不能删除或解释为段间统计；nativeBand是ENTER_FRAME优先级1000到-50间多监听器墙钟区间，不能单独认定具体原生函数或GC。该帧warm=0/draw=0只证明没有块完成，不能排除未完成分片；该段9次slice并在第55帧完成1块。totalScript错开记录上一帧，后一行444ms才对应此区间。日志/整轮指标未见错误、其他AIR、人口暴增或内存耗尽，但没有逐帧堆/分页指标，尖峰原因未定。综合支持限定场景明显改善（均值约15.4%），不是无混杂精确净收益。反序复测可作后续稳健性检查，本轮优先完成已测产物的功能/网络门禁。诊断代码与记录提交b00ddb1，未纳入他方SceneRenderChecks WIP。


2026-10-23 02:02门禁状态：RC负责人真实Session生命周期7a10b4a47f已56/0、12阶段通过，证据mods/RConnect/build/m52/recovery-offline-lifecycle-native-03/result.json（F97729DB…97D4F1）；前两次准备/清理失败保留，产品EB365未改。该测试不覆盖实际双人画面或实际观察调用。当前可用commit约4.96GiB，未达到既有双实例6GiB门槛；已异步请求用户方便时释放暂不用应用的内存，不结束他人进程、不降低门槛。继续单实例功能验证、正式仍574D，目标active。正式用户pfe私有RC配置autoRole为空，仅只读核对，未改用户存档/配置。


2026-10-23 02:22补充：RC单实例真实采集回退f6eece7606（build/m52/recovery-offline-collector-native-01/result.json）86项/0失败，virgin/null/throws/falseValue/truthyString/afterHost全通过。实际原生喷火弹持续运动，产品历史必须有两个不同时间和位置且匹配独立原生观测；一次readSnapshot的stamp=0不能伪造多帧历史。纯离线原hook不积历史；其余保守分支与首次主持后恢复。全部临时状态清理、安装22项不变，源码复审无阻塞。仅证明玩家弹丸历史采集，不冒充全部body effects或真实两游戏接入。剩余门禁缩为首次真实接入和双向可见事件；内存余量仍约4.95GiB，6GiB双实例门槛保持，未部署。用户释放内存事项已由RC会话集中接续，此处不重复请求。

2026-10-23 07:23首次连接夹具补充审查：当时`experimental/recovery-offline-first-connect/tests/OfflineFirstConnectTestDoc.as`的`observePacket`仅phase==round保留生产包，`render`也仅round观察远端显示；从首次startHost/startJoin至roomReady/prepare/begin(0)的窗口未覆盖。旧事件若在这个窗口短暂重播并消失，后续quietNoReplay可能误通过。peerClass要到ready/prepare才确定，begin(0)清空计数，before在connecting/prepare早退不触发invalidate，均属同一缺口。主代理与只读子代理独立确认，已发RC负责人修正，不改其活动源码。移动稿多次变化，本文不是冻结版本的完整审查或实测结论。最新提交余量2.73GiB，未达到原双实例6GiB门槛；正式BEFC/7F1F/574D复核未动、性能候选EB365保留。恢复后的第2目标回合有具体审查进展，目标active。

07:26纠正与收束：最新只读D65B4345317F2A5824C6B3C10961D6CCB1801E109421244A1B5DEAE7D057DA3E已经覆盖connecting/prepare生产包、peerClass未知回退expectedClass，并在begin(0)前保存/判定；旧包漏检已修。独立子代理曾继续把before提前return当显示检查无可靠驱动，根查准确EB365源码反证：ExplorationSync构造:45注册ENTER_FRAME requestRender，:285只要stage存在即invalidate；GameBridge onMirrorFrame:359也请求。因此“夹具before自身没有invalidate”不能证明实际RENDER不触发，此项意见撤回并同步负责人。显式补触发只属夹具自包含改善，不增设额外必过门禁。尚无双人运行结果。

## 2026-10-23 08:43 — 资源恢复后的真实首连与夹具修复

用户退出暂不用应用并要求优先推进，提交余量恢复超过原双实例6GiB门槛，未修改保护或系统设置。产品仍准确EB365；普通墙面候选不并入此次性能交付。实际连续失败均保留：5589fa431d在AIR虚拟app:/父目录为空处失败；622039485c路径修正通过，但rbl原生空气带被内部竖墙分隔，28格双向走廊不存在。改为原生620,640前位射手、480,640后位接收者分轮换位，保留14格空气带及两次真实位移。

9b2366ad51与诊断d87d5871bf进一步确认不是多射或归属变化：测试提前保存弹药200，附件模组随后正常退回超额弹药，host实际容量72、join90；真实一发后为71/89，owner/weap/gun.b身份全正确。源码FirearmAttachments Runtime.as:127–128及本轮capacity-refund日志相符。驱动改为紧邻真实attack前仅一次记录弹药和弹体基线，不改附件或RC产品，不硬编码容量、不放松严格耗弹断言。

driver06（36DB3C65…86D0906）/native07/c6c9757ebc已完成真实业务全链，独立复核两端准确EB365、首次attempt各1、host hello与join welcome、十项coverage全true。首连至新攻击前host/join分别57/121包及62/72显示帧，旧弹与可播放事件0。host→join原生9位置样本/311像素，对侧10运动样本/313像素/2帧枪口；join→host原生10位置/267像素，对侧10运动样本/283像素/2帧枪口，轨迹对照通过。冻结/解除对侧25/27次身体匹配，像素3310/2731。

本轮整体仍为FAIL：join39/39结束，host38项通过、round4及对侧完成确认之后，join正常断开，host继续房间身份采样触发失败。host.log:65–70明确顺序。不得事后改判PASS；RC负责人仅修终态收尾顺序后再运行，随后按门禁精确部署及实际安装冒烟。正式BEFC/7F1F/574D保持，尚未部署。

08:49最终门禁：driver07/native08/d0048aff49已完整PASS，两端各39项/0失败、attempt各1、真实hello/welcome、十项coverage全true，finishing确认和清理均通过。根直接核对result.json（C103B58822FBE0547AB226907E0D138633D0A782A5FA4217EC4117356BE6C066）及候选EB365原字节，安装22项不变。终态只停止已完成后的游戏观察，保留有界最终确认、全部原断言及清理。联网功能门禁至此完成，RC负责人进入备份/安装/实际安装冒烟；旧FAIL不改写，不额外扩大门禁。

## 本轮交付：EB365已安装，实际安装冒烟通过

2026-10-23 08:58，RC负责人完成准确EB365部署与原运行器双实例冒烟ae58b8049b。回执`mods/RConnect/build/m52/recovery-offline-deploy-01/deployment.json`为deployed-smoke-passed/exit0，SHA256 7DB4BDC4F9BF9317A96EC51DB3076A5B8F0D49BBC9254692142BE92F7065EE86。根和独立子代理复核run.json候选路径指向实际release，双端输入同EB365且无诊断驱动；版本初始化/tick200、join welcome/unitsync及登记PASS，日志散列一致，自有实例清理完成。

当前22项正式安装仅`mods/Rconnect/release/RConnectMod.swf`从574D变EB365；root BEFC、CS7F1F、全部配置及其他模组保持。源产物/正式文件/两端测试字节一致，备份`recovery-offline-deploy-01/RConnectMod.before.swf`为准确574D。部署脚本在共享登记内重核基线、备份并原子替换；失败只回滚自身字节，不覆盖后来者。普通墙面候选未混入。

至此限定的单人真实战斗明显下降与部署复验目标完成；性能依据仍是上文关闭LAD/RV/WB时三轮对照，不是此功能冒烟新测得的帧率或全配置净收益。保留473ms长帧及自然人口差异，整体近原版尚未达到。下次正常启动生效，首次联网尝试后按设计恢复采集，不宣称多人性能同幅改善。
