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

## 4. 最新实测（2026-10-27 持续合图，仍未部署）

准备阶段已提交99665df；后续新增fullpage/combat/combat-imports三配方和三次AIR。完整报告camera-persistent-fullpage-20261027/RESULTS.md。用户已回复释放内存，实际门槛达标后继续，不再等待该问题。

- checks：89源，probe314AE2E6/frozen52ff2b70/resultF4668346/AIR28268。1920×1080、活跃无敌人/120fps、2880完整区间。移动720/臂native27.853、旧合图25.600、持续绑定23.833ms（约14.4%）。横纵改善，组合26.200→26.546反而略慢。
- fullpage：89源，probeFB11B95D/frozenfc4dd02e/resultFB196E34/AIR66000。相同2880区间，移动native28.585/bound22.647/fullpage22.028ms；保留所有驻留格像素，格跨视口不再重复复制，内容按源/revision更新。强制显示静止17.063/18.913/22.246ms，存在静止额外开销，不只报移动收益。
- 两轮16状态真实Flash夹具均通过，132源图/34截图释放；五实际视角各30截图释放，RGB≤1/alpha0，恢复精确。稳定帧无重绑/复制，跨格13复制可增加5–9ms辅助工作，但174ms尖峰主要帧间。每套200MiB/32张，准备单列，最终零资源；首轮准备307ms。
- combat-r1编译失败，仅缺getQualifiedClassName导入；原冻结99b75b04保留。imports补导入：86源，probe6D90BB3D/frozen421d93c5/result11C49524/AIR12612。实际30fps设置、2032×1084、六SMG敌人、原生冲刺/开火、480完整区间；实际移除菜单并早显私有窗口，无激活事件。
- 战斗native49.721→fullpage45.888ms约7.7%，P95 62→63，四段46.917/47.283/44.492/52.525，一对反向。160玩家/276敌人开火帧，X跨度230/265/269/256，Y固定。终局RGB最大1/alpha0、恢复精确、3截图与32缓存释放。**尚无稳定明显战斗改善，不部署。**
- imports原汇总因内部VERSION仍是旧常量而失败，原配方/失败/登记不改。review_failure.py仅修该验证常量，保留全部其余条件后480区间/负载/像素/资源均通过，review839341D8；不得称原汇总成功。无需仅为改绿重跑。
- quiet verify_runs独立复核526正式/13运行/冻结源与计时，quiet-review76FD97F9；战斗同样复核闭包。三AIR均退出、最后登记空。正式/foreign WIP不动，无新权限拒绝。
- 原初内存失败保留，已解除，不是当前阻塞。所有测量私有桌面，非物理呈现；native为现有大场景，非有效普通房间严格同负载基准；自然纵移/RV/长期资源仍缺。图片已实际查看。

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

1. 候选fullpage无敌人镜头有收益，但实际战斗只有约7.7%且一对反向/P95略差。下一轮增加短周期交替次数（例如20×60），沿相同原生冲刺/开火，保留全部样本/轨迹/负载，核清波动；这是未解对照问题，不挑单次最好成绩。不要再重复暂停/隐藏地形路线。
2. 后继另开目录，不能原地改冻结配方。战斗summary除了base.VERSION还须正确设置base.scope['VERSION']；当前原失败保留，review_failure仅后验修常量。现有runtime编译可复用算法，不必重做已通过的16状态夹具。
3. 有稳定收益后再进行自然纵移、有效原版房间参考、密集内景和RV/SATS/地形破坏/长时资源。外部修改既有Bitmap几何的通知契约仍未解决，不能将诊断类直接部署。
4. 用户已释放内存，当前无待答问题；继续按独立登记/私有桌面/4GiB提交/2GiB物理和会话精确调用授权。根任务活动，不标complete或blocked。

## 7. 接续入口

- 最新fullpage/RESULTS.md总报告；fullpage/verify_runs.py --phase quiet与quiet-review76FD97F9；combat-imports/review_failure.py与review839341D8。五配方camera-persistent-atlas、atlas-checks、fullpage、combat、combat-imports（20261027），原始evidence同名-r1。前快照MEMORY-history-20261027-before-persistent-runtime.md。

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
