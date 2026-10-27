# ContinuousScene — 当前快照

## 1. 模组与目标

全图碰撞、敌人、物品预先生成，画面按视野提前绘制，镜头与弹体连续跨房。远处未参战敌人可暂缓，追击者与飞行弹体保持。CS0.9.0另支持可编辑单一地图；原版地图连续模式由设置开关控制。
当前根任务未完成：**解决镜头移动时卡顿，不论敌人是否出现，目标接近原版**。不以暂停世界的帧率冒充实际游玩性能，也不以减少敌人代替镜头修复。

## 2. 用户约定与职责

- 性能根会话01a13816-367b-7261-8e11-ca9152565dd9；中文简洁进度。已允许继续实测，正常测试自行登记/等待，不重复询问已授权事项。
- 已允许必要RV、WB、LAD、TDFC、RC兼容；RC协调已授权，RC由负责人01a086bb-378c-7f60-b8e1-50d90ffa0996集中部署，不并行覆盖。
- 新增明确授权：ModLoader共享测试登记器的CIM创建时间回退修复；已完成，见第3节。其他跨模组写入不自动获准。
- 已接受RGB最大2/255、alpha不变的候选验证；**实战明显提速和功能正常仍是部署前提**。本机通过门禁后直接部署，无需再确认。
- 已接受视野预绘、远处未参战敌人暂缓与纵向镜头缓冲；保留游戏机制和连续跨房。
- 每次游戏测试使用共享game登记、唯一AIR ID/存储、私有桌面、4GB可用提交内存预检；不关闭玩家/外国测试进程，不写真实APPDATA/pfe，不用Ghost。
- 当前会话精确调用、≤10分钟的构建/验证授权仍有效；按既有保护流程逐条登记，不关闭护栏。
- 无AGENT_SCOPE.md；未擅自创建。src/tests/SceneRenderChecks.as是他人WIP，不恢复/提交。
- SceneAlicornAlerts.as.inc仅源码候选，不构建、接入或部署。用户撤回的10月21日下午7D42/5432配方不得复活。

## 3. 当前安装与最近验证

正式文件本轮未变；新增优化均未部署。526正式文件与13运行库输入在完成的各轮保持。

| 文件 | 当前SHA256 |
|---|---|
| root pfe.swf | A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7 |
| CS0.9.0 | 7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F |
| TDFC0.6.4-scene2 | 7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5 |
| ModLoader2.5.0 | 2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2 |
| RV0.33.10 | 638E2D408E2CF46683C41114F75773829A1B4417D74BFFE9D08855A4FE343710 |
| RC0.2.24-animfix1 | 2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621 |

LAD8ADB/WB1411保持。RC当前回执../RConnect/build/m52/a-live-animation-deploy-01/verified.json（5446D95A），不能把旧RC收益当当前候选收益。
A796颜色修复回执state/scene-tint-deployment-20261024.json verified；保留此前ABE2纵向镜头缓冲/80CF遮挡格复用。任何新宿主应精确保留当前其他方法与素材，不能整包覆盖编辑器CS0.9.0。
ModLoader08957b4已提交登记器修复，15测试通过。工具SHA E9F51CB75420C507F6DB1D96BE6B1430374B0B7A797607FF4438A695A717809E；仅普通查询拒绝5时CIM只读核创建时间，不确定仍保留占用。lineage.py只允许旧8B35→E9F5这一变化。

## 4. 最新实测（2026-10-27 多轮战斗/读取兼容，未部署）

前阶段fbbbe7f。最新七配方repeated/jump/jump-steer/pagesize/readers/rv/rv-pixels均在build/generated/camera-persistent-<名称>-20261027；完整报告rv-pixels/RESULTS.md。用户内存回复已落实，实际预检约10–12GB可用提交，非当前阻塞。

- repeated：20×60真实横向冲刺/六SMG/玩家开火，原绘制61.950→1280整页54.045ms，约12.76%，十对九对改善；P95 87→78，>100ms9→10，尖峰仍在。实际400/943玩家/敌人开火帧，Y固定。200MiB准备318ms。1129差异像素RGB1/alpha0，恢复/资源通过。review E6689604；probe ABD683AF，result4812B44E，AIR52952。已查看真实PNG。
- jump：真实跳跃输入每90帧按4帧，原生受击/空中惯性越原已核平台，9完整窗口后失败。jump-steer预看地面4/空中30帧，暖场越左界，0窗口失败。未修改物理或放宽边界；不当性能验收，不继续同平台盲调转向。
- pagesize：活跃无敌人/脚本原生镜头/2880区间，移动native28.136/1280页23.806/2560页22.846ms。较大页仅约4%，反向纵移/组合变慢，内存200→400MiB，不采用。196源/34截图/16状态/5真实视角通过，RGB≤1/alpha0。不要重启此加大页路线。
- readers纯功能92源：明确旧RV D44读取显示树，在原始地形改变而合图未同步时读旧像素。新增只读nativeTerrainSources接口，原图列表按本帧视口和显示顺序返回，不切换可见性。四态旧法仅第二态差1600像素，新法全部精确，12图释放；原16缓存状态/5实际视角也通过。仅在CS隔离复制RV类，未修改正式RV。前五轮统一review 9EF4773E；每轮全部526正式/13运行/冻结源和实际加载复核。
- rv完整current候选：正式D44冻结六源→CS内派生候选，只有源提供/读取选择与诊断接口；只替换隔离运行目录RV，记录显式候选SHA。1200读取/583提供，真实1200间隔95.710→92.180ms仅3.69%。终局原图→候选1555像素、→恢复807像素，最大99/alpha0，全部>2在x1404–1461/y610–642小型实体，原汇总失败保留。probe498E2CDE/result104F6923/RV44C14F35，AIR30584。PNG已查看。
- rv-pixels只改终局为固定7图：原生初次/第二/第三、合图/恢复、再合图/恢复。原生重复与两次恢复精确，两个合图均991像素RGB2/alpha0，7图释放，全部1200间隔/负载/完整RV通过。**本轮初次也相同，未重现旧807像素，不能说已证明首次绘制是原因。**均值107.898→106.187ms仅1.59%，十对五对改善，>100ms325→342，不部署。1200读取/588提供，400/1061玩家/敌人开火帧。probeDA395BCC/result720CD517/RVC349BD3B，AIR66852。RV两候选六源一致、独立编译SHA不同，不称同字节。
- RV两轮verify_runs.py独立review BF3779496C10128B530280FCAC3FBA8A6E2561563BBECEF908A68D06F9248C28；第一原失败不改绿，第二实际通过。两轮正式RV仍638E、其他526/13输入不变。当前全视觉性能目标仍未达。
- 七轮都是私有桌面，不是物理帧率；native是当前大场景，非普通房间有效同负载基准。旧fbbbe7f三轮及汇总常量失败详见前快照与fullpage/RESULTS.md，不重跑改绿。

## 5. 已知边界与停止路线

- 旧wholeworld实验暂停模拟并固定动画；上一批layer实验保持Flash动画、仍暂停模拟。都是预备路线的ENTER_FRAME间隔，**不是无敌人实玩/真实战斗/物理呈现数**。visibility可能被回调观察，不直接叫纯GPU成本。实际AI、子弹、RV、Windows真实混合呈现、SATS及长时生命周期未验。
- 8间隔观测后只停止显式播放/实际变帧者；隐式活动者清理用play，isPlaying可从false变true，不宣称内部播放状态原样恢复。只用于终结式隔离实例，不能复制进产品。帧脚本固定drain仅允许已核bloat_bulk_896的1/55帧；成功轮未触发，不能声称该分支已验证。
- 完整截图/像素图有冷首次差异；固定全偏移原生预备后，仍检查三次独立精确自然往返，不循环拍到通过。mainMenuOff必须真实调用。GPU读回再叠Stage.draw不能当OS窗口截图。
- 已停止：远景缓存约1%混合；视口条带clean慢16%；原生明暗裁剪慢3.7%；透明边缘裁剪慢10.6%；GPU仅背景无收益；静态地形GPU慢11.3%；远处单帧根隐藏慢4.2%；远处不可见地形摘树慢3%；整world scrollRect真正抑制Camera写入后仍无收益，cacheAsBitmap慢14.6%。不换名重跑。
- merged合图暂停移动约15%，实际战斗只约6%/3%且第二轮配对反向/P95变差，保留候选不部署。整world alpha/visible与六对象层隐藏只作归因，不是产品。旧CPU text trace语义未明，不命名为文字或纹理耗时。
- 世界暂停不能保证后台不再新增surface；只读见新节点应按身份/顺序处理，不强摘/复活旧图块。多帧isPlaying=false不是静态证明。完整旧试验链见新归档，避免重走失败。
- 原Monstrik读取、合并Weapon/UnitVisual读取+截图、host tag93补丁/grant、CIM CPU查询、合并PNG枚举/Pt读取被拒绝，禁止转路重试。当前Camera旧缓存缺正式补丁，不可拿build/cache/current-swf/scripts/fe/inter/Camera.as覆盖A796。
- 全地图2–5秒、近原版动态游玩及所有兼容目标仍未完整达到。此前用户撤回的afternoon配方不得复活，旧本体回退不能无条件套用。

## 6. 下一步（目标仍未完成）

1. 持续1280页在RV关闭真实横向战斗约13%且9/10配对改善，但RV/current下仅3.7%/1.6%，不满足整体接近原版。不要再加大页/重复暂停隐藏路线。优先区分静止与镜头移动的显示成本、RV额外计算；没有足够证据时不跳过敌人或删除视觉效果。
2. RV新版只读地形接口已由Flash正反控制与完整current流程证实被调用；仍是隔离候选，不在正式CS/RV。完整功能还缺classic/WB/SATS/地形破坏/地图往返/缩放及任意图块几何失效。WB有独立前/背景叠层，当前背景陌生子节点会回退原生；不能称WB性能兼容已完成。
3. 两个自然跳跃试验均原生受击/惯性越固定平台，保留失败。下次需先准备适合自然纵移的真实路线及碰撞验证，不能继续调同一短平台或放宽界限凑通过。原脚本轴对照不是自然跳跃证据。
4. 第二RV轮Y固定、X往返，objectsScanned约1073–1087未持续增加；后段优先级1000→-50区段约50→65ms，包含RV等回调，不能叫纯World或凭此证明探索累积。D44源码hideEnemies/hideWorldEffects全loc.units/对象链扫描，没有原生sleep接口调用，是否热点尚未测；先量实际分段再决定兼容改法，不凭猜测跳过遮罩。
5. 前轮终局807像素自身恢复差异没有在后继重现，原因仍未确证。固定7图新轮严格通过不覆盖旧失败，也不意味着所有战斗帧正确；保留两轮原图。
6. 用户已释放内存，无待答问题；继续独立登记/私有桌面/4GiB提交+2GiB物理门槛。登记未结束ended为null，状态查询用null/空值或state，别用ended==空字符串；真正驱动始终通过登记锁及AIR独立检查。根目标active，不标complete或blocked。

## 7. 接续入口

- 本批七配方和原始evidence同名-r1；rv-pixels/RESULTS.md总报告。前五轮readers/verify_batch.py→9EF4773E；两RV轮rv-pixels/verify_runs.py→BF377949；repeated/verify_run.py→E6689604。所有已运行配方冻结，后继新目录。前快照MEMORY-history-20261027-before-persistent-rv.md。
- RV派生仅在CS目录的rv-src/rv-builds，正式RV来源必须是其build/combat-render-output/production-final2/src六源，并核原build.json。不要用包含authority的当前src替代。RV当前运行层入口通过RVExplorationAPI.api.terrainReadStats记录验证；CS nativeAPI.terrainSources只在测试期挂载并移除。

- 前批fullpage/RESULTS.md总报告；fullpage/verify_runs.py --phase quiet与quiet-review76FD97F9；combat-imports/review_failure.py与review839341D8。五配方camera-persistent-atlas、atlas-checks、fullpage、combat、combat-imports（20261027），原始evidence同名-r1。前快照MEMORY-history-20261027-before-persistent-runtime.md。

- 准备阶段两目录camera-persistent-atlas{,-checks}-20261027；当时offline-review DB4E5C6A尚未构建。后续checks已经实测，当前结果见最新总报告；前快照MEMORY-history-20261027-before-persistent-atlas.md保留准备历史。

- 最新五目录camera-visible-tree-audit、camera-border-cache、camera-visible-components、camera-opaque-tiles、camera-empty-native-tiles（均-20261027）。各prepare/probe_patch/run/helper配方冻结；components/RESULTS.md总报告、verify_batch.py与review_failed_summary.py后验复核，batch-review9EC414B0。原始evidence同名-r1。前快照MEMORY-history-20261027-before-visible-components.md。
- 上批camera-active-quiet-{axis,bands}、camera-native-{near,visible}-groups-20261027；visible-groups/RESULTS.md与bands/verify_batch.py保留六轮及黑区纠正。原报告不能用新结论覆盖。

- 本批七目录camera-live-parking{,-return,-window,-math,-groups,-safe-groups,-range}-20261027。range/RESULTS.md总报告，range/movement_audit.py核实际水平位移；groups/review_runs.py可核失败的完整1200区间，math/review_batch.py可核内存中止。已运行配方全部冻结；后继新目录。
- 本批前快照MEMORY-history-20261027-before-live-parking.md。没有新部署。共同86源来自原29AF种子，仅驱动和测试helper改变；不触碰正式CS编辑器或SceneAlicornAlerts候选。无新共享事实/技能修改。

- 本批camera-far-live-{visibility,warm,cohort,counts,detach}-20261027与camera-native-static-cache-20261027，各prepare/probe_patch/run/helper和verify_run；cohort仅编译失败。总报告detach/RESULTS.md；原始evidence同名-r1，配方冻结，后继新目录。Git -text保存编译原字节。
- 本批前快照MEMORY-history-20261027-before-far-live.md。正式未改、没有新部署。本轮读取src/SceneObjectCulling.as仅确认旧逐对象wrapper路线及念力/藏身限制；不复活该已失败实现。

- 本批camera-native-{window-switch,window-audit,window-draw-warm,quality,effects-overlay}-20261027；各prepare/probe_patch/run、AS3 helper、verify及run-review。window-audit/verify_runs核前两失败，其余各verify_run。原始证据同名-r1。所有运行配方冻结，后续新目录；五目录Git -text保留编译原字节。
- 本批前记忆MEMORY-history-20261027-before-native-windows.md。总报告effects-overlay/RESULTS.md；runtime属性无效事实已入共享游戏知识，无全局技能修改。

- 本批7目录camera-actor-{sprites,direct,frames,frames-checked,frames-scan,atlas,atlas-checks}-20261027。总结果在atlas-checks/RESULTS.md，统一独立脚本在frames/verify_actor_runs.py，7份run-review.json；原始evidence同名-r1。所有运行配方冻结，后续新目录。
- 本批前完整快照MEMORY-history-20261027-before-actor-cache.md；下列上一批入口继续有效。首轮简单Bitmap只覆盖1–3个当前可借用根，不能将旧census的78节点误当本轮全部已直接复用。
- 上一批：build/generated/camera-layer-{dirty,tiles,region}-20261027；原始evidence同名-r1。各prepare/probe_patch/run、呈现器、RESULTS、verify_run均保留，已运行配方冻结，后续新目录。完整旧停点state/MEMORY-history-20261027-before-live-layers.md。
- 上一批三轮没有stop/play/goto；第5节旧冻结播放限制只适用于之前wholeworld实验。KB-000108已回读：像素和几何失效分别跟踪，收益须另测。
- 上一批：build/generated/camera-stage3d-region-prune-20261027与camera-native-gpu-20261027的prepare/probe_patch/run、README/RESULTS、verify_run/verify_pair。再前region-refresh/region-items/item-profile、wholeworld{,-late,-nullslots,-observed,-cost,-settle}、viewport-refresh同根；对应knowledge/experiments/evidence/*-r1为原始证据。所有运行过的生成配方冻结，不原地改后重跑；后续另起目录。
- 新旧完整停点归档：state/MEMORY-history-20261027-wholeworld.md；更早MEMORY-history-20261026-2340.md、MEMORY-history-20261023-0818.md。journal顶部本轮和前轮链。
- 85源种子receipt：knowledge/experiments/evidence/camera-atlas-paged-combat-20261025-r1/probe-build.json（983727AE）；frozen f298932b38e24919991997c68e0a8b8a，probe29AF。新变体86源。lineage入口camera-terrain-layers-20261025/lineage.py只允许登记器8B35→E9F5这一变更。
- 隔离调用沿各run.py，先prepare.py生成并校验源码；共享登记game、独立桌面、唯一ID/存储、≥4GiB提交和≥2GiB物理内存。Python在用户.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe，Java在D:/Program Files/Adobe Animate 2024/jre/bin/java.exe，Flex/SWC/ffdec在Sandevistan/build/tools。
- 本轮按已获授权逐条使用会话01a13816精确调用短时grant；未关闭任何保护。工具说明见.agents/skills/remains-{auto-testing,runtime-debug,mod-build,mod-memory,release-gate}/SKILL.md与ModLoader/docs/TEST-REGISTRY.md。
- design/single-map-authoring.md、state/deployment-v090.json为独立编辑器发布；state/scene-tint-deployment-20261024.json为正式A796染色修复。
