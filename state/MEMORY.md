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
ModLoader08957b4已提交登记器修复，15测试通过，原E9F51仅普通查询拒绝5时CIM只读核创建时间，不确定保留占用。其负责人随后独立加入UTF-8解码，当前E3E43581D677D26C83B7E887C64669634CCC8D901AEFA5A826E1CFED8A5F0CF0；反向唯一解码行逐字恢复E9F51。新启动器ECE3ED08与资源模块86D5F280在owned suspended子进程设置normal CPU/memory priority5/HighQoS再恢复；实测回执记录实际策略，不改变全局或外国进程。本任务未写这些工具，新配方精确接受新指纹，旧配方冻结。

## 4. 最新实测（2026-10-27 环境索引分配已消除，镜头收益待对照）

本轮接续86b7057；前快照MEMORY-history-20261027-before-resource-policy.md。正式安装未改，镜头卡顿仍待解决。

- fog-history-normal-r3已完成，复用D4B5DBE6/614be80b探针，AIR37804退出，960区间和五张原图检查通过。进入前普通房间本地360格已探索、大场景为0；重置后两模式1200格visi/target/opacity/mask/water在五视角及计时两端全部精确相同，全部960镜头坐标仅偏移(5760,3000)。前轮上下遮罩差异可由夹具探索历史解释，不是已证产品错误。随机装饰与灯光仍不同，不称全图像素等价。
- pair-review.json B5DC4EA1已独立核526正式/13runtime/86源和全部时钟；核验在共享启动器后续修改之前完成，旧回执不改。普通房间静/横/纵/组合12.933/17.283/17.583/17.471ms，最大97ms；大场景scene-r2仍有29个>100ms/最大1068ms，不能以两轮均值作稳定性能比较。
- preparation-memory-r2成功完成8阶段含实际副本准备，约7.91s，无Java/AIR。主Python私有内存25,858,048→26,066,944B，峰值46,145,536B；提交余量4,695,973,888→4,645,535,744B。未见本次主进程积累GB，不推论所有子进程瞬时峰值。回执ABC25564，r1失败保留。
- 只读检查玩家旧frame-recorder：2026-10-25 19:08–19:13，共300样本，无相机坐标/产品指纹，不能用角色坐标替代镜头运动。原样副本和review C6E125C7留camera-live-recorder-review-20261027，不作为当前归因。
- sampling-scene-r1在编译前因共享air_test_process.py变动停止，无Java/AIR。原配方冻结。ModLoader任务更新私有桌面启动资源策略，非本任务写入；新配方camera-visible-room-sampling-policy-20261027精确接受启动器ECE3ED08、资源模块86D5F280，并保留登记器E9F51修复。实际启动策略另入回执；不修改旧lineage或放宽任意漂移。
- policy场景18420/普通55324均实际完成；普通房间原运行末检因登记器E9F51→E3E43581失败，保留原失败。allocation-stacks/review_prior.py仅允许逐字反向唯一编码行，复核其余输入/87源/实际运行，5539957F是后验诊断，不改原运行通过状态。
- allocation-stacks-scene-r1 AIR77008完成：40采样区间sceneNativeEnvironment分配65312，全由Location.step调用。EnsureUpcoming22312，其中原生Camera.calc13264、夹具额外calc9048；不能全当真实游戏开销。CPU采样含render/sweep标记，不能直接解释为GPU毫秒。独立review F14FE11E。
- clamp单方法候选887B仅去Math.max，实际AIR41192分配65312→64752，不足1%，停止、未部署。新keycache候选F15B8CE88A500382CA23FF5D387D67997FDB5AE900B78DB09FAF505A014239CA从A796重新开始，缓存区域字符串且每次仍查当前byCell。audit F0A8EE4F核其余5770体/1016类/素材不变。
- keycache-allocation-r1 AIR70744完成，复用原87源59165645探针：同40区间环境分配降为0，总分配约下降40%。独立allocation-review DC3B6B17。只能证明分配，尚不能称镜头提速或部署合格。
- quiet新86源098F3644/冻结ef6149a0：关闭采样，准备阶段150种区域/边界/特殊数/改原点/同键替换检查共3000字段断言。base-r1 AIR39060通过，环境恢复、全部960时钟/坐标通过；移动720区间21.8458ms、中位21/P95 29/max103，保留全部长帧。base-review7E595DC7。
- quiet-cache-r1在AIR前余量2696175616B触发4GiB保护，无游戏。只读定位另一个实验Python83808约6.76GiB，非本任务、未终止；用户选择处理其内存占用。恢复后交替原/候选测试，防背景负载变化误归因；下次cache-r2，同一ef6149a0探针。仍保持4GiB提交/2GiB物理线。

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

1. 先恢复quiet候选对照：run_variant.py --host cache --name camera-environment-quiet-20261027-cache-r2 --probe-build同目录probe-builds/probe-source/ef6149a0dbf649ff960aea4dd817f246/probe-build.json；随后按证据交替base/cache复测。verify_runs.py独立核原始数据和全部960坐标，不能丢弃长帧或拿环境变化当收益。cache-r1是启动前内存失败，保留。
2. keycache候选分配证据充分，但无采样实际提速、候选150环境行为、普通场景/战斗兼容还未完成，不部署。若实测不明显，则停止此分支的帧率宣称，按新的具体证据继续；EnsureUpcoming有夹具额外calc开销，勿重复归因。
3. 原合图内景仅4.37%、横移变慢；旧战斗13%不能推广。RV/current仅3.7%/1.6%，保留候选；鼠标/裁剪/GPU等停止路线不换名重做。Camera原生vx/vy为int，不能未验证就宣称亚像素导致卡顿。
4. RV只读源接口仍为隔离候选，classic/WB/SATS/地形破坏/往返/缩放/几何失效未验；原807像素恢复失败未解释。SceneAlicornAlerts、撤回afternoon、foreign SceneRenderChecks不动。
5. 本轮已有普通房间AIR和内存审计进展；不因稍后的占用或内存不足直接标blocked。继续解决镜头主线，当前无可部署的新性能修复。

## 7. 接续入口

- 本批fog-history/RESULTS.md与pair-review B5DC4EA1；normal-r3已完成。preparation-memory-r2 ABC25564。旧sampling-scene-r1仅输入漂移失败，新policy配方正在接续。旧快照before-resource-policy.md及before-fog-sampling.md保留。

- 最新camera-visible-room-{reference,scout,atlas}-20261027：atlas/RESULTS.md总报告，scout/verify_batch.py、atlas/verify_run.py；evidence为reference-normal-r1、scout-{scene,normal}-r1、atlas-scene-r{1,2}。atlas-r1仅预检中止，其余四AIR回执保留。前快照MEMORY-history-20261027-before-visible-reference.md。

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
