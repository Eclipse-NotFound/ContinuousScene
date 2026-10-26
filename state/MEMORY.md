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

## 4. 当前实验停点（2026-10-26深夜）

- 现有固定池35956，8页×4层×1280²=200MiB，计时前分配，计时不分配；清理全部释放。
- idle候选6651：静止恢复原生并跳过无用同步，移动恢复同步。v1墙面夹具看不到弹痕，完整计时后功能失败；v2改为实际屏幕内可见外墙，960/9通过，原生击墙158像素/破墙2208像素；静止/恢复精确、移动RGB1alpha0。移动30.7292→29.6417ms，仍205ms无工作长帧。不部署。
- empty候选65F4：只有透明外包矩形证明中心完全空时才跳过复制/显示。960/9通过，移动31.7458→28.9458ms，两个配对同向；1588透明检测、632省略复制。固定200MiB不减。仅暂停归因。
- merged候选BC0B：守卫两背景父层相邻、中性和无外部效果，按原顺序合成页背景，前景/水不变；不合格回原生。960/9、36截图和64位图释放、跨页/击墙/破墙/父层alpha回退通过。移动31.6875→26.8417ms约15.3%，不代表实战。
- **merged实战两轮**同冻结4ef9354c，均480/27、六真实SMG10敌人/原生冲刺和碰撞，镜头各窗115–119变化。原生→候选47.0125→44.1958ms、46.2125→44.9833ms；第二轮一对更慢，P95 58→62，长帧156/196仍有。敌火力/预绘不同，收益不稳定，不部署，不重跑同夹具挑好结果。
- 实战终态单视口三图均通过RGB≤2/alpha0/精确恢复，3图释放；未覆盖所有效果和生命周期。合图候选仅保留。
- display-contribution：对象父层alpha恢复后1567像素不同/maxRGB227，计时0帧；停止对象隐藏路线，原失败保留。
- backdrop-contribution：仅远景alpha可精确恢复，960/9、15截图释放。原生34.6375/远景隐藏39.5479ms，四对均更慢；不能去掉远景或推定GPU机制。
- camera-backdrop-raster-r1已完成960/9，冻结22c7adc3，五视口/透明度/清理通过。移动33.6708→33.3167ms仅约1%，静止21.7→22.5625更慢；停止远景缓存，不部署。AIR4072退出，无自有AIR存活。
- 此前完成的八轮AIR均退出。仅以登记器/本轮进程证据确认当前占用，不靠旧PID猜测。

## 5. 已知限制与停止路线

近原版、全地图2–5秒、所有效果/联机/SATS/长时稳定未全面达到。本轮世界暂停测试仍有Flash时间轴/回调，不是无敌人的真实游玩。
原生axis-trace支持镜头运动有显著绘制开销，但重型追踪不是正常FPS，也不证明GPU/GC。stage-cost中相机均.35ms，合图1.26ms；148/140ms长帧准备仅3/0ms，不能命名余量来源。
已停止无稳定收益或像素失败：native cacheAsBitmap远景、scrollRect父缓存、bitmapfill、整树/对象层隐藏、terrain-detach、静态Box摘树、整段远处动画跳过、qualityLOW、鼠标树、活动范围、预算逐帧分配、旧全图合图等。完整边界与原始失败见历史及各RESULTS，不重复换名字试同一路线。
三处旧工具拒绝（Monstrik原始读取、合并Weapon/UnitVisual读取+截图、host tag93补丁/grant）未执行；不转路绕过。trace路线不修改宿主已通过。
当前完整战斗用native-input-motion-3真实输入；早期逐帧Y/速度固定的stableMotion仅诊断。旧34.35/57.33ms原版对照为历史不同组合，不能直接当今日候选差值。

## 6. 下一步与部署约束

远景屏幕缓存无明显收益，已停止。新假设为地形每层视口大小缓存、随镜头平移旧像素并只补新露出的条带；不是旧父层scrollRect/cacheAsBitmap或AIR direct/cpu模式。尚未实现，须先严格像素与移动对照验证，不因猜测部署。
合图只保留为候选。后续需要新的高占比证据或足够收益，不以重复相同实战取最优数值放行。
通过实际门禁才本机部署、备份、安装后复验；当前没有合格的新包。仍以A796正式指纹为准，不运行旧BEFC/80CF/ABE2/afternoon的无条件回退。
外置记忆/报告只追加证据，旧失败和冻结收据不可改写。自己的里程碑可提交，foreign WIP排除。

## 7. 深入入口

- build/generated/camera-atlas-pool-{idle,idle-v2,empty,merged}-20261026/RESULTS.md
- build/generated/camera-atlas-merged-combat-20261026/RESULTS.md
- build/generated/camera-{display,backdrop}-contribution-20261026/RESULTS.md
- build/generated/camera-backdrop-raster-20261026/README.md（新候选）
- 对应knowledge/experiments/evidence/<实验名>-rN内result/summary/process-policy/probe-build是原始证据。
- build/generated/camera-terrain-layers-20261025/lineage.py；camera-atlas-paged-combat-20261025-r1/probe-build.json为85源冻结种子983727AE，探针29AF。
- journal.md；MEMORY-history-20261026-2340.md保存重写前全文，历史更早MEMORY-history-20261023-0818.md仍在。
- .agents/skills/remains-{auto-testing,runtime-debug,mod-build,release-gate,mod-memory}/SKILL.md，ModLoader/docs/TEST-REGISTRY.md。
- design/single-map-authoring.md、state/deployment-v090.json为独立编辑器；state/afternoon-recovery-20261021.json为历史回退，当前不套用。
