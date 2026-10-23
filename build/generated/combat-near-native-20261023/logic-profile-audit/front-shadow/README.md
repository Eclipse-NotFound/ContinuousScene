# 前景像素存储分离：实验结果（未部署）

2026-10-23：像素组件与两轮真实交战短交替试验已完成。完整计时中B均值分别低1.7933、2.5050ms，每轮五组中四组较快、一组较慢；交战量、活动人数和实际移动速度仍有差异。这是小幅改善信号，尚不足以证明用户要求的明显提速或接近原版。**本轮不部署，不继续扩大显示缓存；战斗和高速移动卡顿的修复仍未完成。** 保留全部失败、成功证据，不把本候选判为普遍无收益，也不把组件通过当作发布许可。

基于当前正式80CF；Grafon沿用准确BEFC的`motion-direction-rays/source/fe/graph/Grafon.as`，生产80CF仅改变Location.lighting。没有改变正式宿主、CS、RC或共享驱动；接入仅修改冻结探针副本。

## 具体问题

原生`sceneRender`把同一BitmapData交给`entry.nativeBuffers[0]`和前景Bitmap。`sceneApplyCompactDecal`先在未挂树的temporary绘制，末尾copyPixels写回已经显示的像素存储。此草稿仅验证最后写回所引起的显示失效/同步是否昂贵；不会减少sceneDecalPaint的矢量draw，不预认性能收益或所谓GPU成本。

既有`SceneTilePresentation`与native-crop处理四层、改为320×320、去掉scrollRect，像素及收益未通过。本次仅前景，保留原400×400、原320×320/40偏移裁剪、位置、Bitmap和父层。预分配既有驻留块的同尺寸clone，A仍绑定原图，B绑定clone；原生继续即时写入原存储，尾部按revision增量同步完整400×400。与历史重栅格化stamp无关，不使用像素容差。

## 准确输入与源码身份

| 输入 | 版本或 SHA-256 |
|---|---|
| 正式宿主 | `80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D` |
| ContinuousScene | `7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F` |
| RConnect | `DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7` |
| 准确 Grafon 源 | `75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB` |
| [helper](tests/SceneFrontShadowProbe.as) | `front-shadow-diagnostic-1`；`FB4496ED1C7C6234AFA059B168C6B93939447806F0C311F115D32E56E25051B6` |
| [隔离源码接入](probe_patch.py) | `DBD0049FE80CDB2C68A247F9B8075F63042A7B50E943C76C6F7874810C2CA091` |
| [runner](run.py) | `front-shadow-runner-3`；`56810EAC61204A8A557077C0C25C3890A0B01D2D28089F27435485D4FE7B8DE9` |
| r3组件及两轮短交替共用探针 | `9E58E9CF9C389C693C47F92C681429470741C3956A44106FB6C96ECCB2F71676` |

夹具为`dense-sprint-2` / `native-input-dense-sprint-2`，观察策略`dense-observer-lean-2`。以下证据名均带`front-shadow-20261023-`前缀，目录位于本模组`knowledge/experiments/evidence/`；原始`storage/result.json`、`summary.json`、冻结输入、日志均保留。

## 准备阶段的两次失败

| 运行 | 实际结果 | 定位 |
|---|---|---|
| `pixels-r1` | 8项基础检查通过；准备超时；0正式窗口，未start helper | 601暖场帧、600 grounded、342 floorContact，末X=4305、dy≈0.149。没有完整准备条件同时满足的遥测，不能凭累计接地数认为已就绪。 |
| `pixels-r2` | 8项基础检查通过；0正式窗口，未start helper | 516次准备观测，最高连续接地150、最高quiet15；sceneWarmSlices从2到501，计数变化498次。约第500帧预绘才停；quiet未到20，原生击退已令X=5296.77超过核验平台上界5295。 |

两次都发生在影子绑定之前，不是像素错误或候选性能回归。r2只增加准备诊断，没有降低像素、安全平台、接地或预绘门槛。

r3在路线校验后、创建测试敌人和唯一玩家spawn前，通过公开`Grafon.sceneTick`原生同步路径准备所需视野：临时扩大视口并设`sceneAsyncWarm=false`，随后恢复原视口、排空已有warm job。未调用World.step、未开scenePreload、未绘制全图，没有锁定玩家或关闭原生伤害、击退、AI。finally恢复camera/quake/async，校验玩家位置、速度及既有单位数未变。

实际准备矩形`(0,2560,7040,2440)`，地图9600×5000；驻留块28→177，估计上限178、硬上限256。每次3个sceneTick调用。它会改变原生驻留像素、预绘历史/预算及计数；**仅证明相机/async/玩家状态恢复，不声称整个renderer回滚。** 后续稳定门禁和计数变化立即失效仍保留。

| 成功运行 | 单列testPreparationMs | entryMs（不同阶段，不是总载入成绩） |
|---|---:|---:|
| `pixels-r3` | 7833 | 5428 |
| `short-r1` | 7751 | 5702 |
| `short-r2` | 7553 | 5361 |

这7.55–7.83秒属于**计时外的诊断准备**，不算2–5秒载入目标的成果，不能隐藏到性能收益里。组件仍要求连续接地10帧和计数稳定20帧；性能夹具沿用历史连续接地、完整往返及开始时实际落地门禁，不伪称与组件的等待条件完全相同。

## 30帧像素组件

`pixels-r3`为`ok=true`、12项检查通过、0失败。准备第30帧就绪，groundRun/quiet均29；随后站立并真实开火30个native帧、30个匹配tail，不请求跑动，原生击退仍有效。玩家10发、六名测试敌人52发。

B仍绑定时先拍未额外重同步的tailImage，再重复A参考、完整同步B、恢复A。在2032×1084、缩放1、相机`(-3661,-3478)`下，referenceRepeat/tailImage/bindingImage/restoreImage四项均**0差异像素、0最大通道差**。此前真实tailSync为50次；52次revision增量不等于52次前景命中，因为背景和水也增加revision。终点验证另做177次fullSync，不混入此前覆盖计数。

177个clone全部释放；原像素dispose、泄漏、清理错误均0，aborted=false。这证明本次静态驻留视野和实际射击帧的像素一致，不认证小数缩放、SATS、resize、travel或预绘变化后的继续运行。

## 两轮完整20×60主计时

每轮五组ABBA，每窗60个间隔，A/B各600，共1200；两轮均90项检查通过、0失败。20/20窗双方实际开火，原生跑动、并发飞行弹体门禁通过。ASSR玩家、六名LMG敌人保留原生加速、碰撞、击退、装填和体力；夹具仍带既有敌人HP=100000/伤害2、玩家补弹/耐久与godMode。这是耐久交战归因夹具，不是未经调整的普通战斗难度。灯光/RV/WallBlend关闭，2032×1084、缩放1。

`front-shadow-tail-sampling-2`在最高优先级帧头选择并保存row/mode，执行prepare；最低优先级尾部在游戏写入后update并取时间戳。start所在帧尾建立primeTail，所以**全部1200项均为tail→tail**，首项不是较短的head→tail。tick虽会推进index，tail仍归属保存的旧row/mode；最后finish/census延至最后tail之后。

主计时保留所有切换/恢复/同步和跨窗成本，不扣首帧、不删尖峰；初始clone分配和末尾清理单列。旧tick数组/端点另存，未冒充新计时；历史tick端点实验的绝对均值不可直接作精确归因。`qualification.passed=true`只表示工作负载与接入合格，`performanceEligible/performanceAcceptance/deployed`仍为false。

| 运行/臂 | 间隔数 | 均值ms | 中位ms | P95ms | 最大ms | >100ms |
|---|---:|---:|---:|---:|---:|---:|
| r1 A | 600 | 65.0567 | 61 | 90 | 411 | 17 |
| r1 B | 600 | 63.2633 | 61 | 81 | 196 | 5 |
| r1全部 | 1200 | 64.1600 | 61 | 85 | 411 | 22 |
| r2 A | 600 | 64.0100 | 61 | 85 | 214 | 6 |
| r2 B | 600 | 61.5050 | 59 | 78 | 217 | 6 |
| r2全部 | 1200 | 62.7575 | 60 | 81 | 217 | 12 |

r1端点47387→124379ms，总76992ms；r2为43921→119230ms，总75309ms，均等于全部primary求和。r2的B最大值略高于A，>100ms次数也相同，不能说已消除卡顿。

每组120A+120B，玩家每臂每组40发。弹体为测试敌人所属的逐帧在飞数量均值；速度为玩家逐帧绝对dx均值（px/native帧），不是按键值或预期跑速。

| 轮/组 | A均值ms | B均值ms | B−A ms | 敌发射A/B | 弹体A/B | 速度A/B |
|---|---:|---:|---:|---:|---:|---:|
| r1/1 | 68.842 | 65.683 | -3.158 | 247/154 | 7.250/4.442 | 7.869/7.835 |
| r1/2 | 63.058 | 68.358 | +5.300 | 188/252 | 5.900/8.600 | 8.596/8.213 |
| r1/3 | 63.692 | 63.342 | -0.350 | 163/220 | 5.667/8.517 | 7.595/6.250 |
| r1/4 | 64.233 | 59.433 | -4.800 | 121/124 | 4.250/4.950 | 8.296/6.906 |
| r1/5 | 65.458 | 59.500 | -5.958 | 163/113 | 5.517/3.983 | 7.302/7.973 |
| r2/1 | 66.917 | 64.342 | -2.575 | 182/172 | 5.558/4.558 | 9.118/9.309 |
| r2/2 | 60.342 | 63.117 | +2.775 | 151/181 | 4.233/4.892 | 6.378/6.719 |
| r2/3 | 64.342 | 61.992 | -2.350 | 151/200 | 4.767/5.842 | 9.359/7.399 |
| r2/4 | 63.658 | 59.817 | -3.842 | 134/188 | 4.392/5.550 | 5.939/8.931 |
| r2/5 | 64.792 | 58.258 | -6.533 | 197/146 | 7.083/4.458 | 7.789/7.346 |

| 整臂负载 | r1 A | r1 B | r2 A | r2 B |
|---|---:|---:|---:|---:|
| 玩家发射 | 200 | 200 | 200 | 200 |
| 六敌发射 | 882 | 863 | 815 | 887 |
| 定期采样awake均值 | 38.35 | 40.75 | 41.30 | 40.05 |
| 窗尾awake均值 | 38.9 | 41.3 | 41.9 | 39.3 |
| 测试敌人飞行弹体均值 | 5.717 | 6.098 | 5.207 | 5.060 |
| 全部飞行弹体均值 | 6.765 | 7.182 | 6.408 | 6.228 |
| 玩家绝对dx均值 | 7.932 | 7.436 | 7.716 | 7.941 |

两轮全部窗口warm完成数、slice次数、forced次数均0，无新块/丢块/aborted。这次包含slice=0，不是只凭“完成块数=0”推断无预绘。r1 B敌发射略少，但awake/并发弹体更多、移动较慢；r2 B敌发射更多，但awake/并发弹体略少。不能只挑一个计数称两臂等负载，也不能将约2ms全部差值认作缓存净收益。

## 存储、复制与自身成本

每轮额外持有177×400×400×4=**113,280,000bytes，约108.03MiB**的clone像素；不含原生像素、Bitmap/表对象及其它运行时分配。A也持有这些clone并运行观察校验，因此不是完全无观察器的正式原生基线。

| 本探针计数 | r1 A | r1 B | r2 A | r2 B |
|---|---:|---:|---:|---:|
| prepare+update ownMs | 860 | 963 | 875 | 888 |
| 其中updateMs | 851 | 957 | 868 | 879 |
| 其中syncMs（update子项） | 0 | 64 | 0 | 54 |
| 窗口switchMs | 18 | 131 | 19 | 131 |
| revision增量 | 737 | 693 | 583 | 500 |
| 按帧去重changedEntries | 618 | 637 | 556 | 469 |
| 重复revision单位数 | 119 | 56 | 27 | 31 |
| 窗口fullSyncs | 0 | 1770 | 0 | 1770 |
| tailSyncs | 0 | 637 | 0 | 469 |
| 窗口copyBytes | 0 | 1,540,480,000 | 0 | 1,432,960,000 |

每次B开窗（包括B→B）仍完整同步并绑定177块，每轮10个B窗共1770次；加初始177次clone，全程fullSync=1947，总copyBytes分别1,653,760,000和1,546,240,000。B同帧revision合并上界仅56/693≈8.1%、31/500=6.2%；revision含背景/水，不能当作省掉的前景上传次数。整块400×400同步还可能放大原先较小脏区。

r1初始分配148ms、全窗切换149ms，累计setupMs=297、末尾清理22、totalOwnMs=2142；r2对应148/150/298/18/2079。setupMs含switch，但switch已在primary内，**不能重复加或从primary扣除**；sync也不与update重复相加。prepare/update平均约1.4–1.6ms/间隔，成本已保留。两轮均释放177个clone，恢复完整，无泄漏、原像素销毁或清理错误。

## 调用契约

`tests.SceneFrontShadowProbe`为一次性实例，不安装监听器。

1. 预热稳定、尚未计时：`start(w)`。仅支持sceneLarge、320块+40边沿、非preload，最多256块（clone像素至多约156.25MiB）；全部分配计入setupMs，不藏进A/B计时。
2. 每个窗口开始时：`beginWindow(w, enabled)`，false为原绑定A，true为影子B。完整同步和切换耗时单列switchMs，但连续primary包含所有切换/恢复成本，本次没有删首间隔或boundary。
3. 每个native帧开始前调用`prepareFrame(w)`；它在SATS/V、暂停、travel或已观测场景变化时先恢复，不每帧重新绑定。
4. 所有游戏像素写入结束后、实际呈现之前，调用`update(w, enabled)`。须沿主探针已验证的最后尾部通道接入；不能放在仍有后续写入的普通低优先级ENTER_FRAME中便声称安全。调用缺失、A/B状态不符将使探针失效。
5. 读取`snapshot()`后必须`clear()`，保留cleanup回执。实际接入使用上述tail→tail并固定row/mode；包含上帧呈现及本帧原生/脚本工作，不假称单独呈现耗时。首个失效之后整轮不作为静态期有效性能，所有窗口/原始连续间隔仍保存。
6. `verify(w):Object`只在组件或计时终点运行，最终clear。当前若绑定B，先截取现有尾部影子画面（不先重同步），再恢复A并重复截图证明参考稳定，然后完整同步B截图、恢复A截图；逐像素比较完整Stage画布，记录差异像素与最大通道差。valid/equal/restored分别报告，合法像素差异不变成执行异常。tailSyncsObserved=0时不能声称验证过实际命中后的尾部同步。

## 保守退出与恢复

- 实际公开入口是`sceneSurfaces()`，不存在已验证的`sceneTerrainSurfaces()`。记录每个entry、bitmap数组、nativeBuffers数组、前景Bitmap、原BitmapData和parent的身份，不能仅用坐标键认新块。
- 固定`sceneResident/sceneWarmCount/sceneWarmSlices/sceneWarmForced/sceneRedraws/sceneEvictions/sceneMisses`。任何计数变化即恢复原绑定、当前窗口acceptable=false，并锁定整个实例aborted；必须重新start新实例，不能忽略预绘后继续算同一有效窗口。
- 原生批量预绘有不增加revision的copyPixels，因此不能只依赖revision。这里仅允许静态驻留期，检测新块或丢块也作无效；不补齐新块继续测。已有warmJob即使尚未完成，下一次slice计数变化也会在尾部恢复、取消窗口资格。开始前稳定门禁与尾部时序仍由调用者证明。
- 原Bitmap的x/y、transform.matrix、scrollRect、pixelSnapping、smoothing、alpha、blend、mask/cache/filter状态均保存并核对。除bitmapData赋值自动重置smoothing后立即恢复外，不主动改这些属性，也不改visible；原生cull可继续改visible。clear恢复本探针持有的绑定与smoothing，外部实际更改的属性不倒退为旧值；属性冲突意味着窗口失效，不抢回外部控制。
- removed/disposed原对象不复活；如原生已销毁像素，摘掉仍绑定的clone后清理。绝不dispose原nativeBuffers，仅dispose自己clone。clear中的异常和残留必须使整轮无效，不能以像素不再显示就当作清理通过。
- SATS可在native期间捕获世界画面；只靠尾部检查无法修复已拍下的旧图。计时窗口不得触发SATS，prepareFrame必须在原生读取V之前运行；单独功能组件需验证V捕获与恢复，不得把本草稿直接部署。pause/travel/location变化同样退出。

## 输出与最小验证

输出含每窗/累计revisionDelta、changedEntries、multiRevisionEntries（Δ>1）、repeatedRevisionUnits（Δ−1）、maxRevisionDelta、可见变化/重复块、新块/丢块、fullSyncs/tailSyncs、复制像素面积/字节、prepare/update/sync/own耗时。`ownMs=prepareMs+updateMs`，syncMs为update的子项，不重复相加；setupMs/cleanupMs另列，totalOwnMs相加，但都不能从连续墙钟中扣掉。revision包括decal、paint、水等层操作，不等于前景实际命中次数。若先因公开预绘计数拒绝，newBlocks可为0，不能由此断言没有产生新块；拒绝原因优先于后续身份清点。

上述两轮现已补齐逐帧revision/复制记录和本次视野的实际像素验证。小数镜头/缩放、SATS、resize、travel及新驻留块生命周期没有被此次结果认证，静态驻留限制也未解除。约2ms的小幅信号伴随108MiB额外像素和较大复制量，负载仍漂移、长帧仍存在；当前不继续扩建该候选，不将这些未验边界累成下一轮显示缓存工程。整体卡顿修复目标仍未完成。

此实验不能把frame−script余量称为GPU，也不能由尾部复制减少直接推出运行时实际减少上传次数。它只检验像素存储与显示绑定的成本关联，不删实体、不改伤害/碰撞/跨房逻辑。

## 原始证据指纹

下表为`knowledge/experiments/evidence/<名称>/storage/result.json`的SHA-256；相邻summary、probe-build、runner-inputs保留完整提取及冻结来源。

| 名称 | SHA-256 |
|---|---|
| `front-shadow-20261023-pixels-r1` | `52CF85B32E5B574108DA7C8B7D9A0259C0D551D755CC4A5A1E0EDC9C56B6C08B` |
| `front-shadow-20261023-pixels-r2` | `BA1D0E57D834F050B3F30146833899791555088B3CF340991B36BC65DD03A285` |
| `front-shadow-20261023-pixels-r3` | `65B60E00C17777D93F5CD4C5A38490DE30C9E3E38B728E315140BA15A647FA42` |
| `front-shadow-20261023-short-r1` | `2F6D55AF906ABB3D241052C7C442FD90CAE8B2A00CFA8F287FFAB74C5EFA9C1A` |
| `front-shadow-20261023-short-r2` | `A241440D4F882882CF91A49850E3141CABA0C7DACA793A80839776D8FFC91522` |
