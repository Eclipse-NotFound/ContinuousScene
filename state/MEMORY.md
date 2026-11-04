# ContinuousScene — 当前快照

<!-- proof-activity-live-20261104 -->
> **2026-11-04 证明策略实机接续：按需建威胁表候选保留，未部署。** 同源0.9.8最小候选真实AIR诊断28/28（含12夹具），1,075次读取边界/独立状态比较零差异；移动/开火/瞄准各450帧、38项检查通过，但q=0均0%，没有省一次建表。旧A/A初态/顺序/负载不匹配，修正对照遇其他AIR；**有效性能配对0，局部与整帧收益未判定**。本批冻结A9B39CC7、1280×800/scale2/3，不能外推新宿主或用户全屏。正式核心与CS release未改。报告 [run-03](D:/活/AI/测试运行/remains-proof-strategy-20261104/run-03/REPORT.md)；模组记录 `knowledge/experiments/proof-activity-live-20261104.md`。继续需先确认自然q=0价值及可重复原生初态，不直接加不匹配计时样本。
<!-- /proof-activity-live-20261104 -->

<!-- round3-verdicts-20261104 -->
> **2026-11-04 两项裁决（本轮实测）：逐出+复用 = 负结果不部署；B-P2 = 不实施**。
> - **逐出+复用（cap=96）负结果**：同探索线路 1149 帧，均值 41.8→39.9、P95 65→62，但**最大帧 171→568ms**、同步补画 22 次/1044ms → **30 次/1997ms**。失败机制已定位：**相机跳变（换窗口/传送）那一帧要同步补画所有被逐缺口**（`dt=568` 出现在 phase 45 换窗口 age=0，`syncCount` 跳 25）。→ **不部署**；要根治需“异步补块+占位呈现”，另立项。更保守的上限（160 块）按峰值 181 只省 ~12% 分配，收益/风险不成比例，也不做。候选产物 `build/generated/opt-20261104/cap-diag-v2`（9 方法）保留，**未部署**；正式宿主仍是 **1D2004AB**。
> - **B-P2 不实施**：`alicorn4-alicorn-n1`（900 帧、14/14）实测：地图 faction-1 单位 50 只；一次交战把带目标单位 **1→最多 9**（age≈100 起），但**唤醒按每帧 1 只的预算节奏**、`awake` 只在 28–43、整场帧时无抬升（前/后 100 帧 34.5/34.9ms）；仅“高活跃帧”慢 **+4.9ms**（≈0.7–1ms/额外活跃单位）。现状 `wakeBudget=1`+2200×1600 leash 已把这条链压到 +5ms 量级，再改要冒把交战单位误判为弱信号的风险 → **不做**。夹具内 `visBmp.filters` 全程 0（无念力持握相位）。
> - 报告：`knowledge/experiments/alicorn-count-probe-20261104.md` §6、`knowledge/experiments/long-frame-memory-20261104.md` §6-§7。
<!-- /round3-verdicts-20261104 -->

<!-- cap-candidate-20261104 -->
> **2026-11-04 逐出+复用候选已编码，待构建/验证（玩家在游戏中，未抢资源）**：`build/generated/opt-20261104/patch_host.py` 新增 `cap_patch`（3 个方法：`sceneDrop` 入池 ≤8 块缓冲、`sceneBeginWarm` 从池取并 `fillRect` 清零、`sceneTick` 末尾按离视口最远逐出到 `World.w.visual.root["sceneChunkCap"]`，默认 96 块≈246MB）。**dry-run 已通过**（`cap-dryrun.as`，3 方法改动、锚点唯一），FFDec 构建与实测待机器空闲。
> - **关键前置已核对**：呈现层 `SceneEventBitmapFill` 第 64-66 行的失效条件**本来就含 `evictions != grafon.sceneEvictions`**，`refreshBindings()` 每次从 `sceneSurfaces()` 整体重建并对消失位图 `restoreRecord` → **逐出是设计时已留钩子的路径**，不是未支持路径。仍需实测：折返重预热代价、逐出瞬间 1 帧残影。
> - **构建/验证命令**：`python build\generated\opt-20261104\patch_host.py cap cap-diag`（诊断版，带相位计时）→ `PHASE_HOST_DIR=<cap-diag> PHASE_PROBE=probe-v5 PHASE_LABEL=cap python build\generated\phase-20261104\run_phase2.py explore 14` → `analyze_phase.py cap-explore-n1`；对照基线 `phase2-explore-n1`（resident 49→181、13 帧 >100ms）。通过后再建 `cap-clean` 走部署门禁。
<!-- /cap-candidate-20261104 -->

<!-- long-frame-memory-20261104 -->
> **2026-11-04 长帧归因反转（重要）**：本轮相位探针三次运行逐帧对照 `System.totalMemory` 与长帧：**≥100ms 帧里 85%（11/13）、92%（12/13）、100%（3/3）与一次 >1MB 的内存回落同帧**，回落中位数 **50–72MB**（单次最大 165MB）；回落 >3MB 的帧平均 **98–131ms**。`resident` 同帧仍在增长，说明回收的不是地块缓冲而是大块临时内存。逐帧样例：`89→90` 帧 462MB→297MB、dt 143ms。
> - **机制**：每块新地块在 `sceneBeginWarm` 分配 4×2.56MB、约 1.8 块/秒 ≈ **18MB/s 分配量**，且缓冲**从不复用**（`sceneDrop` 只在换图/verify 调用、无逐出）。AIR 的回收由分配量推动，约每 **80 帧（2.7s）**回收 50–165MB，把该帧拉到 100–171ms。→ 这解释了此前四次“减分配≠减帧时”：被削减的是小垃圾，触发回收的是**大地块分配量**。
> - **新候选（原 P3，理由已更新）**：远处逐出 + 缓冲复用（`sceneDrop` 入池 ≤8 块、`sceneBeginWarm` 从池取并清零、`sceneTick` 按离视口最远逐出到 `sceneResident` 上限 96 块≈246MB，可用 `World.w.visual.root["sceneChunkCap"]` 运行时改）。预期把分配速率降到近 0 → 回收变稀 → 长帧按比例下降。
> - **必须先验的风险**：全屏 `scaleV=1` 下 CS 呈现层（`SceneEventBitmapFill`）是否持有被逐块缓冲的引用；折返时是否转为同步补画（31–178ms）。验证用同一相位探针 + 回头路路线。
> - 口径差别：v14 用插桩 GC 回调曾得“29 个长帧仅 9 个邻近 GC（31%）”；本轮用逐帧 `totalMemory` 回落（含 mark-sweep 与缓冲/显存释放），更贴近玩家感受的冻结，两者不矛盾。报告 `knowledge/experiments/long-frame-memory-20261104.md`。
<!-- /long-frame-memory-20261104 -->

<!-- alicorn-count-20261104 -->
> **2026-11-04 天角兽只读计数探针（B-P1）：工具就绪，首轮不支持“警报拉活”假设**。探针 `build/generated/phase-20261104/alicorn-v3`（原生 `UnitAlicorn("1",100,null,{tr:1})` 生成 + 逐帧 alert/unicorn 计数）；首轮 `alicorn2-alicorn-n1`（900 帧、14 项检查通过）：均值 34.4ms、仅 3 帧 >100ms；`awake` 33→27（27–35）、`asleep`→112，**900 帧内只唤醒 11 次、交战前 30 帧 0 次**，交战后帧时无持续抬升 → **本夹具未出现成批拉活**。判别字段（cel/f1/filters）因首版 `UnitPlayer.visBmp` #1069 丢失，v3 已修但运行被并发会话占用 AIR 挡住（n1–n10 全 `Existing AIR`/`Other AIR`，未动他人进程）。报告 `knowledge/experiments/alicorn-count-probe-20261104.md`。**下一步**：等干净窗口跑 `alicorn-v3` 取 cel/awake 跳变；若无跳变则关闭 B1/B-P2 方向。
<!-- /alicorn-count-20261104 -->

<!-- phase-decompose-20261104 -->
> **2026-11-04 补充：帧三分与用户三项决定**。在相位探针数据上再拆一层（`dt` = CS 管线 + 从 501 处理器到下一帧 -1000 的窗口（渲染/调度，记作 R）+ 其余游戏逻辑）：
> - 探索 1149 帧（均值 41.8ms）：**CS 5.67 / R 21.78 / 逻辑 14.37 ms**；≥100ms 帧 13 个里 **CS 21% / R 61% / 逻辑 19%**。
> - 战斗 1299 帧（均值 41.4ms）：**CS 3.00 / R 20.53 / 逻辑 17.89 ms**；≥100ms 帧 13 个里 **CS 8% / R 53% / 逻辑 39%**。
> - → 全屏下 CS 只占 7~15%；**主项是 R 桶（约 20ms/帧）与游戏自身逻辑**。R 桶的边界依赖“501 之后到下一帧不含游戏 step”的假设（1149 帧里有 56 帧出现负逻辑值，属边界噪声），不要当成纯渲染读数。
> - **一次无效实验（勿引用）**：用 `--draw-control world` 想验证 R 桶是否为世界层渲染，但本相位探针不消费 `motion-controls.json`，世界层并未真正隐藏（结果 mean 40.6 vs 41.4 属噪声）。要做得先在探针里实现隐藏层。
> - **用户决定（2026-11-04）**：①实际游玩用**大窗口/全屏**（`scaleV=1`）→ 地形双线性在物理上无收益（1:1 无重采样），方案 ① 作废；②**不做** `zoom100`；③**批准**相位探针（已执行）。
> - 结论：CS 侧可做的低风险项到此为止（P2 已装、P4/P1/P3 已按实测否定或降级）；进一步改善必须转向 R 桶与游戏逻辑侧，那已跨出本模组范围，需另立工作流或交相应模组负责人。
<!-- /phase-decompose-20261104 -->

<!-- phase-attribution-deploy-20261104 -->
> **2026-11-04 相位归因实测完成，并部署首个据证据实施的优化**：宿主 `pfe.swf` **A9B39CC7 → 1D2004AB**（只改 `fe.graph.Grafon.sceneApply`：`decal` 不再 `sceneCancelWarm`；`classesUnchanged`）；CS 仍 0.9.8、`scene.xml` 不变；**需重启生效**。备份 `build/backups/pfe_before_decal_nocancel_20261104-133604.swf`，回执 `build/generated/opt-20261104/deploy-receipt.json`，报告 `knowledge/experiments/phase-attribution-implementation-20261104.md`。
> - **测量（本轮最要紧的结论）**：探针在 `Camera.calc→sceneTick` 内部拆相位。探索 1149 帧：CS 管线 **5.67ms/帧**（预热 4.97、同步 0.07、剔除 0.06、弹痕 0.03、块启动 0.48/峰值 80ms），**其它 36.2ms/帧**；**≥100ms 帧 13 个里 CS 只占 20.6%，2/13 帧 CS 为零**。战斗 1299 帧：CS 3.00ms/帧，**≥100ms 帧 CS 仅 7.8%**。→ **长帧主体不在 CS**。
> - **已装补丁的机制量**：同调度 1300 帧，`cancelCount 10→0`、`cancelWork 302ms→0`，每块预热工时 45.6→43.3ms；清洁候选冒烟 1300 样本/13 项检查通过。**跨轮整帧均值不可比，未主张帧时收益。**
> - **据实测否定的候选**：拆 `drawKusok`（`maxStepMs` 仅 20–25ms，非 125ms）、弹痕空间索引（`markMs` 0.03ms/帧）、`sceneApply` 空间索引（566 次 apply 共 5.9 万次相交）、`sceneApplyCompactDecal` 分配修正（减分配≠减帧时）、压预热预算（实测自适应 2–25ms）。**不要再按旧方案重提。**
> - **仍成立但未做**：驻留块无逐出，探索 38s 内 `resident 47→181`（+343MB），全图上限 ≈1.2GB；若做需“远处逐出+缓冲复用”，并用同一探针验证回头路不造同步风暴。天角兽 B-P2 仍缺只读计数证据。
> - 工具：诊断宿主编译器 `tools/stutter_host.py` 的 `phase` 种类；探针 `build/generated/phase-20261104/probe-v5`；运行器 `run_phase2.py`（手写隔离 manifest，因启动器保存被沙箱拒绝）；分析器 `analyze_phase.py`。**首次失误**：手写 manifest 时误拷贝根 `application.xml`（`<id>pfe</id>`），一次运行写入玩家真实存储（日志与 `MSWConfig.sol`/`ModLoader.sol` 被重写；**存档 `PFEgame0.sol` 与 `config.sol` 未动**），已改为改写模板并重跑。
<!-- /phase-attribution-deploy-20261104 -->

<!-- investigation-v2-20261104 -->
> **2026-11-04 三项问题复核（Lead 会话，只调查未改产品）**：可执行方案 → [design/scene-combat-camera-optimization-plan-v2-20261104.md](../design/scene-combat-camera-optimization-plan-v2-20261104.md)；证据 → `knowledge/experiments/scene-combat-camera-investigation-20261104/`（探索链 / 天角兽 / 镜头视觉 / 离线微基准四份）。
> - **下一步必须先做**：相位归因探针。模组 ENTER_FRAME 计时**不含**宿主 `Camera.calc→sceneTick` 驱动的 ensure/预热/同步/剔除，既往"CS 只占 6.4%"只是**下界**（43ms 同步补画那帧 handler 仅记 4ms）；真实游玩 38 个长帧至今无相位分解。
> - 已确证量级：同步整块补画 **31–178ms/次**（28/29 在入口首屏）；`drawKusok` 单步峰值 **125ms**（占 ≥8ms 单步 94%，**不是**滤镜）；`resident=155`≈397MB 无逐出、每发弹扫 118 块；弹痕重放（step 24）**从未单独计时**。
> - 天角兽：旧四条根因全部降级（`findBox` 0.05–0.6 次/秒且 ≤0.5ms；玩家被抓走 `levitFilter2→vis.osn.filters` 而非 `vis.filters`；`actPort` 每次 ≤12 次瓦片检查；alilight 约 90% 命中在 `sceneApply` 入口早退、0.4–0.5 发/秒）。**唯一有量级的链条 = 警报/目标共享拉活同房同阵营单位**（+1.5–2.0ms/帧/单位，既有实测），默认接力 0% 只断多跳、不阻止首发直接通知。
> - 镜头/模糊：**动态模糊实测否决**（最便宜单向 BlurFilter 15.5–19.5ms、挂容器 23–59ms，预算 33.3ms）；2048×1123 时 `cam.scaleV=1` 无重采样，1264×681 时 0.6583 可开双线性（+3.9–7.2ms/帧，1:1 零成本）。0.6583 是**镜头缩放**不是 stage 缩放；int 截断不致爬行；原版已有纵向缓动。
> - 0.9.8 新风险待验：aim pan 最多偏移 700px 且写回 `cam.vx`，快速横扫可能触发视口 miss → 同步补画；验收需覆盖"按住瞄准横扫"。
<!-- /investigation-v2-20261104 -->

<!-- aim-look-v098-20261104 -->
> **2026-11-04 已部署 CS 0.9.8 瞄准模式（Aim-Look）**：正式 release → **285625F4**（0.9.8），宿主 **A9B39CC7** 与 scene.xml **1CEA74E2** 不动；需重启游戏生效。回退=备份 `build/backups/ContinuousSceneMod-0.9.7-447AE02B-before-aimlook-20261104-045116.swf` 覆盖 release + 重启；回执 `state/aim-look-deployment-20261104.json`。
>
> 功能：按住左 Alt（默认；设置页可改左 Ctrl / 自定义组合键 / 长按或切换）时视角朝鼠标方向平滑延展，松开回中——恢复单房间模式的远距视野，用于远程交火与侦察。参数：150px 死区、^1.4 幂律、横 700/纵 380px（滑块 50–150%）、三档速度、单帧 50px 硬限、地图边界钳制；七类互锁（SATS/覆盖层/Pip-Buck/剧情运镜/原版分号探头/控制台/失焦/非大场景）即时复位。设置页新增 6 项，偏好写入 `ContinuousScene.preferences.json`（旧文件向后兼容）。nativeAPI 暴露 `aimStats/aimController`。
>
> 实现：`src/SceneAimController.as`（新增）+ 入口接线（`onFrame` ENTER_FRAME -200，原生 `Camera.calc` 之后、物体剔除**之前**注入；异常仅自禁用）。**调查新增事实：`fe.inter.Camera.vx/vy/celX/celY` 是 int，写入分数被静默截断**——控制器写后回读类型化值再同步 `visual/celX`；假世界夹具测不出，已加 `tests/FakeIntCamera.as` 回归。
>
> 验证：确定性 **44/44**（`tests/SceneAimChecks.as`）；隔离实机 **9/9**（正式 13 模组+探针、私有桌面、工厂大图内真实按 Alt：平移 616.8px / 一致性 0 违例 / 松开归中 / stats applied=224）。工具链 `build/generated/aim-look-20261104/`（`run_live.py` 可重跑）。**未完成**：玩家重启实机主观验收（手感/狙击/平移中无剔除空洞）；武器倍镜联动、受击回中、边缘定位线未做。设计 `design/aim-look-system.md`，报告 `knowledge/experiments/aim-look-20261104.md`。
<!-- /aim-look-v098-20261104 -->

<!-- gc-combo-final-20261104 -->
> **2026-11-04 GC 周期回收组合治理终局（用户指令）**：组合部署侧已由各维护者完成——ConditionSystem（408+867/帧→0）、RConnect gcfit1（139→0）、**FA 0.4.1（bb6b3ac，~393/帧→0，本轮核实 release=40235F8A）**。自研 env 泵候选 029DAF34 **干净负载四轮配对（base,cand,cand,base，02:52–03:02）：base 16 次/1057MB vs cand 15 次/1037MB，帧指标无一致方向——第四次"减分配≠减帧时"，正式关闭不部署**（累计 8 轮配对零收益）。当前栈归因（v14，23/24 窗）：env 泵仍为第一分配源（64,104 新/96.1% 即死）但消除不动 ~67–71MB 周期；UnitTurret/FocusManager 显示链 ~4.4 万新 + 最大留存增长（~3.6MB/轮）；**29 个长帧仅 9 个邻近 GC（31%）——长帧主体不是 GC**。分配削减路线在本模组内关闭；继续攻长帧需新证据/新路线（跨窗中寿命对象追踪曾被采样器 100k 上限阻止）。正式栈 A9B39CC7/447AE02B/1CEA74E2 未动。报告 `knowledge/experiments/gc-combo-current-20261104.md`；复算 `gcombo_analysis.py` / `gcattrib_analysis.py`。两次内存守卫自停系用户 Stellaris/WizTree 会话（7.9GB+1GB 提交），未动用户进程。
<!-- /gc-combo-final-20261104 -->

<!-- event-culling-deploy-20261104 -->
> **2026-11-04 已部署 CS 0.9.7：事件驱动增量剔除（方案 Phase 1）**。正式 CS release → **447AE02B**（宿主 A9B39CC7 不动、scene.xml 1CEA74E2 不变）；需重启游戏生效。回退=备份 `build/backups/ContinuousSceneMod-0.9.6-F16890C9-before-eventculling-20261104-005240.swf` 覆盖 release + 重启；回执 `state/event-culling-deployment-20261104.json`。
>
> 改动仅模组层：`SceneObjectCulling` 由每帧全层 `getChildAt` 轮询改为 ADDED/REMOVED 事件队列维护根（每 120 帧审计兜底）、`SceneCullEntry` 缓存边界/变换/显隐、仅变换变化时重取边界、仅显隐翻转时写 wrapper.visible；包装层可见性职责与 SATS 暂挂/念力/潜伏/换父层语义不变。入口版本 0.9.7、暴露 `objectCullingController`。
>
> 验证（双进程正反序配对 + 同进程开关，全部 game 登记、独立 AIR ID/存储、静音私有桌面）：**qualification-v6 原宿主与 cleanup-v1 宿主各 14/14**——修正后的命中夹具证明**屏外命中在 A9B3 上原生正常**（无目标弹 627/509 伤害 vs 显式对照 596/624、miss=false）；sceneCU 从未生效（MainFE 密封读 #1069，Bullet 回退 loc.units），旧“镜头列表漏屏外目标”不是现行缺陷。**timing-cull 正/反序各 2350 完整间隔、23/23 剔除断言、2,202,688 像素零差异**：整帧均值 **−7.9%/−7.8%**（52.99→48.80、58.60→54.05ms）、CS 局部 **−60.5%/−62.1%**（4.58→1.81、5.01→1.90ms）、max −10.5%/−11.9%、P95 −12.5%/−6.1%、>100ms/分 −41%/−5%。左右行方向一致。**尾部指标受 RV 并行负载波动，未达方案 §5 终局目标（P95 −15~20%、长帧 −50%），低负载复测前不宣布总体解决。**
>
> **验收终局（2026-11-04 02:30，五轮配对合并）**：CS 局部处理 **5/5 轮稳定 −57~−66%**（机制指标，无例外）；整帧均值 4/5 轮更优（−5.9%~−11.4%，1 轮 +2.2% 出现在污染最重的 rev-r3：均值 ~60ms、>100ms 33 次/分）；**开火合并 3680+3680 帧：均值 56.01→53.38（−4.7%）、中位 53→50、P95 80→77（单轮 P95 从不变差）**；**>100ms 合并频率 18.34→18.33（不变）**、P99 116→125——**长帧不由剔除驱动，是 GC/环境事件**，§5 尾部目标（P95 −15~20%、长帧 −50%）对本修复不适用、按证据重新定标；长帧根因沿 GC 调查史（三次"减分配≠减帧时"）指向环境与周期回收，渲染侧选项已尽。**Phase 1 验收通过**（专项门禁：局部 ≥60% + 配对整帧收益）。低负载复测由"等内存"重试完成（fwd-r3/rev-r3，02:24/02:29，其间用户 Stellaris 占 7.6GiB 提交造成 r2 中止与多次重试）。
>
> **补充验证**：①不开火对照（nofire-r10，920+920 帧、0 开火帧）：均值 −11.4%、P95 −31%、>100ms −71%、CS −66%，普通移动无退化；②冷态探索 + 因果分析（cold-r3 + `analyze_cold_causality.py`）：82s 内 cancel 11 次/431ms、sync 29 次/1985ms、单步 max 125ms、warm 仅 2.4ms/帧；**196 事件配对 0/29 同块**——Phase 2 无因果支撑降级缓办，28 次 sync 为入口冷启动填充（真实游玩被载入遮蔽），行进中仅 1 次 sync；**Phase 3a（余量钳制）证据不足且有饿死预绘的反效果风险，不实施**（详见计划 §7.3）。
>
> **未完成/下一步**：①玩家重启游戏实测主观流畅度（最终验收）；②cleanup-v1 定量（估计每弹 #1069 异常 + 每帧无效列表 ~0.1–0.5ms，待窗口）；③Phase 4（弹痕空间索引）需长局增长证据（cold-r3 仅 82s，markScanned 30,947 未按局时增长验证）。
<!-- /event-culling-deploy-20261104 -->

<!-- stutter-implementation-20261103 -->
> **2026-11-03 用户已授权按方案优化；候选已实现，当时未部署，内存不足阻止剩余验收**（该停点已被 2026-11-04 段落取代：447AE02B 已部署）。正式仍 A9B39CC7 / CS 0.9.6 F16890C9 / scene.xml 1CEA74E2。新 CS 0.9.7 候选 `event-v3` **447AE02B**：事件队列维护显示根、typed entry/向量、变换不变时跳过边界计算、显隐变化才写入；仍逐帧检查坐标，未做静态分桶。23 项生命周期、13 项夹具、同帧 2,202,688 像素零差异通过。
>
> 第一轮诊断（cull-r2）完整间隔 121.72→91.82ms、P95 244→171ms，CS 局部 15.44→4.70ms；高开销且负载很慢，**不是发布性能证据**。反序 timing-r2 遇 668s 执行间断，整轮排除。精简 timing-cull-v2 / timing-nofire-v1 已编译待两进程重复。新的真实长走廊 x6080–8920,y2960；cold-r2 被“完全空闲”准备条件卡住，不算探索；cold-v2 已修成初始视口就绪后出发，后两次因内存不足未启动。最近承诺余量约 0.8–1GiB、物理负载 91–92%，无 AIR，不降低门槛或清其它进程。
>
> **更正 sceneCU**：MainFE 实测封闭，读取 #1069，不能沿用此前“镜头列表有效”的推断。清理无效列表/异常路径的宿主候选 `cleanup-v1` **5B409966** 仅改 Grafon.sceneTick 与 Bullet.run，类布局/其它方法不变，未运行、不可部署。命中夹具三次失败依次是未捕获属性错误、无活跃屏外自然目标、临时目标未核对阵营/重叠；最后一项不能归因 sceneCU。源码现已补空闲位置/敌对阵营/接触对象记录，下一步构建 qualification-v6 并在原宿主/cleanup-v1 对照。
>
> [实施记录与接续命令](../knowledge/experiments/stutter-optimization-implementation-20261103.md)。工作根 `build/generated/stutter-opt-20261103`，正式输入/开工源码 frozen baseline 已留存；构建器 `tools/stutter_{opt,probe,host}.py`，分析器 `tools/stutter_analyze.py`。生产源码是候选；release 未替换。原六份未提交源码、其它报告和期间并发改写的方案正文保留；自有运行已结束，无后台继续承诺。弹痕保留、帧预算、历史索引尚未取得实施资格，不能当已优化。
<!-- /stutter-implementation-20261103 -->

<!-- stutter-investigation-20261103 -->
> **2026-11-03 当前调查结论与下一步**：用户条件已明确为**马哈顿废墟、轻机枪、大窗口、RV/WB/光暗效果关闭**。本轮仅调查与制定方案，未实施性能修复或部署。正式宿主仍 **A9B39CC7**、CS 0.9.6 **F16890C9**、scene.xml **1CEA74E2**。以下旧条目的“头号嫌疑”“待选回退”和“数学上不可能优化”不是当前裁定。
>
> 真实游玩记录筛除加载/菜单后 196.364 秒、5143 帧、38 次 >100ms；新增三轮登记隔离诊断 **7980 间隔（7770 玩家屏内）**，11 项夹具检查各通过。两轮同路回走开火比不开火约慢 8ms；未见 presenter 拆建或成批唤醒解释这些慢帧；显示/逻辑位置差 <0.05px，但未做像素级视觉验收。第三轮开关剔除使 CS 处理从约 6–8ms 降至约 0.3ms，整帧配对并非全部同向，**优先候选为增量剔除，不能直接停用或声称获得等额帧收益**。
>
> 新区域取消→重做→同步补画链在当前源码仍存在，48ms 预绘上限也不是整帧余量；本轮深走堵墙，尚未计量自然探索中的取消废工，需先补合格路线/计数。当前 marks 已有相交剪枝但仍全表扫描。额外确认 `sceneCU` 按镜头选 Bullet 目标且缺场景/帧资格，有屏外命中和跨图陈旧列表风险，未做新反例实测，需纳入正确性前置。
>
> 下一步按 [执行方案](../design/stutter-optimization-plan-20261103.md)：固定准确部署来源/有效路线 → 增量物体剔除候选 → 条件触发的弹痕预绘保留 → 帧余量调度/空间查询索引；每项独立整帧验收。当前 Grafon 正确回读入口为 `build/generated/envkey-cache-20261102/host-export`（A9B3 回执），勿用旧 .inc 或 camera-spatial 的部分旧方法整包重建。完整证据、未验条件和复算入口见 [调查报告](../knowledge/experiments/stutter-investigation-20261103.md)。六份既有未提交源码与其它报告保留；自有测试/登记已结束。
<!-- /stutter-investigation-20261103 -->

<!-- regression-bisect-20261102 -->
> 2026-11-02（十一）**用户报告镜头移动退化，三臂版本切分调查完成（深夜）**：v13b 探针 10 轮交错（v93/v94/v95/v96，同布局种子，host A9B3+当前阵容恒定），负载经相位比值+干净子集（static≤40ms）双重降噪后：**scale-1 非战斗配置下无可测退化——v96(1.425 pan比) 反而最快，v93=1.555、v94≈v93、v95=1.600（单轮干净样本，+3~6% 边缘噪声）**。平滑唤醒（v94）确认无罪。**头号未验嫌疑 = 0.9.6 拴绳的战斗中休眠/唤醒振荡**（玩家风筝时敌人跨 2200px 反复 freeze 树遍历+重唤醒——非战斗探针覆盖不到，且 0.9.6 部署时零计时验证）；战斗对照首跑因外部负载在路线预热超时，工具链就绪待低负载重跑。**未排除用户侧变量：窗口模式（探针 2048×1123 scale1 vs 默认小窗 scale⅔ 呈现/震屏路径全惰性）、战斗/探索场景、游玩时段机器负载。**用户选项 A 维持待测 / B 回退 0.9.3 / C 回退 0.9.4 / D 建 0.9.7 剔除默认关（需与未提交源码会话协调）——报告 `camera-regression-bisect-20261102.md`；证据 `csver*`、`cscombat-v93-r1`（超时残迹）。
<!-- /regression-bisect-20261102 -->

<!-- leash-v096-20261102 -->
> 2026-11-02（十）**已部署 CS 0.9.6 脱战+威胁分级+震屏容忍（开火/多实体优化方案 Phase 1，design/combat-motion-optimization-plan.md）**：正式宿主 A9B39CC7 不变；CS release → **F16890C9**。需重启游戏生效；回退=备份 `build/backups/ContinuousSceneMod-0.9.5-1A66B1F4-before-leash-20261102-152416.swf` 覆盖 release，回执 `state/leash-v096-deployment-20261102.json`。
>
> 改动（全部模组层）：①`NativeSceneActivity` 脱战拴绳——`engaged` 150 帧无战斗信号且超出 2200×1600 追击半径即重置（leashed 允许受伤远处敌人重新休眠，until=0 即时生效；wake() 同步刷新期限；stats `leash-wake-2` 加 leashed 计数）；②弹道威胁双盒——命中走廊（path±explRadius+40）立即唤醒保留、400px 警戒晕圈只给 active 走 wakeBudget（实现为弹道走廊制而非方案原文视口制：threatened 只对视口外单位计算，视口制会全量非紧急并破坏既有断言）；③呈现协调器+EventBitmapFill 容忍 |quake|≤25，分数平移仅在震屏激活时接受（Camera 平移整个世界容器，节点同移，无需注入变换）。
>
> 验证：`leash-v096-mechanics-r2` **29/29**（旧阵容：14模组+探针shim；原27+新增 `engagement-expires-for-far-units`/`leashed-unit-reengages-on-approach`，断言用 gg 移位构造确定性远距）+ `leash-v096-issues-r1` **16/16**；正式阵容变更后补 `leash-v096-mechanics-r3` **29/29**（ConditionSystem 替换 AddictionSystem/PermanentInjury 的当前 13 模组正式组合）。均 game-coexist 登记。**无计时声明**。
>
> **Phase 2（弹痕剪枝）执行时撤销**：部署宿主 `sceneRestoreMarks` 已有 decal 空间剪枝（sceneDecalBounds+区域绘制；冻结源 build/generated/camera-spatial-20261101/source/fe/graph/Grafon.as 可证）；原诊断基于过时 `src/patches/GrafonChunks.as.inc`（本轮编辑已回退）。**.inc 与部署谱系分叉=源码卫生债**：未来全量构建直接用它会让宿主回退剪枝，需择机以冻结源反向同步。Phase 3（炮塔守卫 6AC6C692）已由并行会话 GC/长帧配对测量负结果关闭（见（三）turret-guard-gctail 段）。
>
> 测试设施教训：`build/runtime` 模组选择被并行会话改动致首轮超时（探针不在名单）；恢复=启动器 `--only` + `ContinuousSceneMotionMod` shim（清单/注册入口名必须 \*Mod）；loaded-module-hashes 源自清单而非实际加载。
<!-- /leash-v096-20261102 -->

<!-- handoff-gc-fa-20261102 -->
> 2026-11-02（九）**FirearmAttachments 移交卡已成文**：`knowledge/handoff-gc-attribution-fa-20261102.md`。fa:: 两条每帧恒定链根因定位（源码级）：①**部署版 0.3.5 `after()` 每个原生 tick 全量 `persist()`（3×JSON.stringify 全装配库+收藏+计时器，~226/帧）——其 v0.4.0 候选源码（aecdf26）已改为 persistTimers+事件驱动，但 release SWF 构建于该提交前 85 分钟，未部署**；②`before()` 每帧对每把持有武器 `apply→numbers→clone`，`Catalog.clone=JSON.parse(JSON.stringify(o))`（~152/帧，90-100% 即死）——当前源码仍在，给了脏检查/手写浅拷贝/仅当前武器三个可选方向。合计 ~393/帧 ≈ env 泵 1/7。逐窗数据完全恒定（226+152/每窗）证明确定性每帧行为。零新增游戏运行（用 v14b 既有证据+源码 diff）。
<!-- /handoff-gc-fa-20261102 -->

<!-- gc-fixes-verification-20261102 -->
> 2026-11-02（八）**外部修复验证通过 + 组合复测受负载污染**。阵容变更：AddictionSystem+PermanentInjury 合并为 **ConditionSystem**（v0.2.1，自测 addiction:: −94.6%）；RConnect gcfit1。我方 v14b 独立复检（24/24 窗）：**persist 408/帧→0、setParameters ~867/帧→0、NetHud 139/帧→0，三项全部确认消除**。勘误采纳：原移交 §2.3 Catalog/clone 与 Runtime/after 两条（合计 ~366/帧）实为 **FirearmAttachments（fa::）**，下一个应通知的维护者。组合配对（v13b 4 轮）：GC 一致（cand 6/6 轮 −1 掉落、体积 −10~20%），帧指标被日间负载污染（轮时长 198–297s vs 干净 137s）不可判；结合清晨 fix-A 无帧收益，**029DAF34 维持不部署**；最终帧裁定可夜间重跑（`camera-lead-v13b-gctail-20261102/orchestrate_combo.py`）。报告 `gc-fixes-verification-20261102.md`。
<!-- /gc-fixes-verification-20261102 -->

<!-- handoff-gc-20261102 -->
> 2026-11-02（七）**外部移交报告已成文**：`knowledge/handoff-gc-attribution-20261102.md`——可直接交给 AddictionSystem/RConnect 维护者的自包含报告，含精确栈、每帧量级、口径限制、预期管理（自研最大单源修复未带来帧收益的前车之鉴）、证据文件指针与复现/组合复测方法（v14 探针 + v13 配对工具链路径）。未触碰他人文件。AddictionSystem 合计 ~1,400 新/帧（JSON persist 408、参数重建 867、Catalog 克隆 ~200+，54-100% 当窗死）；RConnect NetHud 139/帧 100% 死。
<!-- /handoff-gc-20261102 -->

<!-- gc-combo-closure-20261102 -->
> 2026-11-02（六）**GC 组合路线终局：B/C 用每窗分布数据关闭，未消耗运行**。v14 每窗构成显示：修复 A 的 env 泵在窗级完美清零（~2,810→0）；warm/块键栈稳态仅 ~400/帧（此前 9k 为 23 窗累计的误读）= A 的 1/6，而 A 已被配对证明动不了帧指标——**B/C 数学上不可能过门禁，不构建**。AS3 层垃圾削减路线整体关闭（工作区第三次且最终验证"减分配≠减帧时"）。剩余杠杆：AddictionSystem ~1,200/帧（外部，最大项）、RConnect ~139/帧（外部）、pre-render 引擎侧（画质取舍已否定）、中寿命对象（采样器 100k 上限使跨窗追踪不可行）。修复 A 候选 `029DAF34` 保留备用。移交卡已写入报告。`gc-combo-closure-20261102.md`。
<!-- /gc-combo-closure-20261102 -->

<!-- envkey-cache-20261102 -->
> 2026-11-02（五）**修复 A 终局：机制成功、帧收益不足，不部署**。`sceneNativeEnvironment` 逐单元格结果缓存候选 `029DAF34`（单方法替换、state.cellCache int 稀疏数组、双向兼容旧模组、类布局不变）：功能 27/27+16/16 通过；v14 归因复测**首要泵完全消失**（采样分配 382,817→344,613）；但 v13 四轮配对 GC 掉落仅 9→8（−11%）、长帧不一致、均值混合——**未达部署门禁**。再次验证"减分配≠减帧时"：~65MB 周期回收由总分配速率驱动（区域键仅占 ~10–15%），其余来自原生渲染（46k/窗）、炮塔/部件链、AddictionSystem JSON（外部）及中寿命对象。生产 A9B3/CS0.9.5 未动；候选与证据保留。GC 停顿要有意义改善须**组合削减多源**（B 键缓存+外部模组+原生侧）并先配对验证。构建含反编译残渣修复经验：宿主导出源的 §§findproperty/§§push 须改为等价可编译写法（仅目标方法移植，其余字节码不变）。报告 `envkey-cache-20261102.md`。
<!-- /envkey-cache-20261102 -->

<!-- gc-source-attribution-20261102 -->
> 2026-11-02（四）**GC 周期回收来源已定位（v14 采样器 id 关联归因，生产栈实测）**：24 窗全有效、38.3 万新对象/15.7 万当窗死亡。**首要垃圾泵 = CS 自研宿主补丁 `Grafon.sceneNativeEnvironment`**——Location.step 每对象每帧调用（native_map_patch.py:32）拼区域键字符串，**~2,800 纯垃圾 String/帧、99.7% 即生即死、零留存**（~110–180KB/帧），量级足以主导 ~65MB 周期回收；与"隐藏世界仍 0.5MB/帧净增长"旧观察吻合。次要自研：sceneEnsureUpcoming 块键（~396/帧）、NativeSceneActivity 装箱（~530/帧，非回归）。外部泵：AddictionSystem 每单位每步 JSON/参数（~850/帧级）、RConnect NetHud（100%死）——移交各负责人。原生 [pre-render] 死亡率仅 13.3%，非周期回收主驱动。**修复方向 A–D 已列未实施**：A=sceneNativeEnvironment 单元格 int 缓存（宿主单方法替换，收益最大）、B=块键缓存、C=模组层数组复用、D=跨模组移交。报告 `gc-source-attribution-20261102.md`；证据 `gc-source-attrib-r5`（r1–r4 并行争用残迹）；探针/分析在 `camera-gc-source-v14-20261102`。本轮未部署、未改生产文件。
<!-- /gc-source-attribution-20261102 -->

<!-- turret-guard-gctail-20261102 -->
> 2026-11-02（三）**Phase 3 终局：炮塔守卫 GC/长帧尾部配对测量为负结果，维持不部署**。v13 探针（每帧 totalMemory+dtMs）四轮配对（base/cand 交错、同布局种子、CS0.9.5 全栈、独占 game）：GC 掉落 7–9 次/轮两臂无差、单次 ~65MB 周期回收照旧、长帧 r1 更差 r2 略好无一致方向、r1 均值 +11%。叠加旧两轮共 6 轮零收益。机理修正：**炮塔同帧 gotoAndStop 不是 GC 周期的有效驱动**（休眠炮塔不调 animate；采样最大存活来源≠回收可削减来源）。该方向均值+GC/尾部均已测量关闭，GC 方向应转向周期性大回收的真实来源（原生渲染/display 基础设施）。报告 `turret-guard-gctail-20261102.md`；证据 `turret-gctail-{base,cand}-r{1,2}`；分析+探针在 `camera-lead-v13-gctail-20261102`。候选 6AC6C692 保留不部署。玩家游戏期间自动等待，未干扰。
<!-- /turret-guard-gctail-20261102 -->

<!-- object-culling-v095-20261102 -->
> 2026-11-02（二）**已部署 CS 0.9.5 状态保真物体剔除（优化方案 Phase 4）**：正式宿主 A9B39CC7 不变；CS release → **1A66B1F4**（0.9.5 = 0.9.4 平滑唤醒 + 包装层剔除）。需重启游戏生效；回退=备份 `build/backups/ContinuousSceneMod-0.9.4-DF3B6812-before-culling-20261102-004010.swf` 覆盖 release，回执 `state/object-culling-deployment-20261102.json`；运行时开关 `nativeAPI.objectCullingEnabledSet(false)`。
>
> 设计：透明包装 Sprite 只切包装层 visible，**游戏独占每个对象自身 visible 语义**（UnitSpectre/隐身/剧情显隐不受影响，这是 CA94 回退教训的正解）；SATS 截取窗口挂起/恢复（SatsVisibleGuard.capture 挂接）；空边界不隐藏；剔除故障仅自禁用不打倒入口。兼容性依据：Pt.remVisual 用 `vis.parent.removeChild`（父相对删除）与包装层共存；teleObj/潜伏箱保持直挂。
>
> 验证（均登记 game-coexist，A9B3 宿主 + 14 模组 + 探针）：mechanics 27/27（smooth-wake-v095-mechanics-r1）、issues 16/16 含三门/边界×3缩放/Bonus·Trap·CheckPoint·UnitTurret 固定视觉（smooth-wake-v095-issues-r1）；截图存档+程序化健全性通过（本会话模型不能读图，**像素级人工复核仍开放**）。无计时声明：剔除的帧收益未测量，不引用已回退 CA94 的 0.6ms 旧值。
>
> **Phase 3 候选已备未部署**：UnitTurret.animate 同帧守卫在 A9B3 重建为 `6AC6C692`（`build/generated/camera-turret-animate-20261102/`，仅该方法变化，类布局不变），候选宿主冒烟 27/27 含 10 炮塔 0 错位（turret-guard-v095-mechanics-r1）。~~部署仍被旧否定结论的门禁挡住~~ **2026-11-02（三）GC/长帧尾部配对测量完成：负结果，维持不部署，方向关闭**（见顶部段落）。当前宿主 A9B3 的 `sceneCU` 空间碰撞与 Bullet 过滤不受影响。
<!-- /object-culling-v095-20261102 -->

<!-- smooth-wake-v094-20261102 -->
> 2026-11-02 **已部署 CS 0.9.4 分帧平滑唤醒（优化方案 Phase 1）**：正式宿主 A9B39CC7 不变；CS release → **DF3B6812**（0.9.4），WB FE3、RV AEA、RC6906 等其余 13 模组不变。需重启游戏生效；回退=备份 `build/backups/ContinuousSceneMod-0.9-3-D8A68A4C-before-smooth-wake-20261102-000448.swf` 覆盖 release，回执 `state/smooth-wake-deployment-20261102.json`。
>
> 改动仅在模组层：`NativeSceneActivity.update` 将唤醒拆为紧急（掉血/交战/弹道威胁/状态/非敌对/功能关闭，保持即时）与预期性（邻近/视口边界）两类，后者走每帧预算（默认 1 个/帧、最近者优先、其余保持冻结跳步），摊平镜头扫过敌群时的同帧 resume+step+gotoAndStop 风暴；stats 加 budget/version，nativeAPI 加 activityBudget。隔离验证 `smooth-wake-v094-mechanics-r1`（登记 game-coexist，A9B3+14模组+探针）**27/27 断言通过**（8 项调度语义+机制/门/奖励池）。无计时声明：平滑削峰的实测收益待玩家/后续探针反馈。
>
> 优化方案 Phase 2（AI 索敌分频）、Phase 3（animate 防抖/GC）、Phase 4（状态保真屏外剔除）**未实施**——均需宿主方法替换与独立验证；Phase 4 必须先过 UnitSpectre 显隐回归教训（camera-iteration-review-20261101）。
<!-- /smooth-wake-v094-20261102 -->

<!-- quality-and-dense-20261101 -->
> 2026-11-01 画质取舍及多敌人续查结束：**本轮无新部署、性能目标未达成**。正式根宿主仍9D8662F6，CS D8A、WB FE3、RV AEA、RC6906等14模组及application.xml保持。全部自有测试结束。
>
> 用户接受同时尝试移动时变软/减少边缘平滑，补充多敌人也卡顿。本轮11次实际AIR运行：7次运行检查完成、4次失败/争用终止；另一次编译排队超时未启动。完成的非采样时序共19860区间，其中16638玩家保持在屏内。v21–23玩家invulner导致敌人不选中它，只有移动实体、不能称交战；v24有开火但玩家被击退出屏，不满足画面内交战资格。v27/28视口检查正确拦下。v29/30改在预绘之后生成六敌、测试玩家fixed；所有测量帧≥3可见敌人、六敌存活、逐窗真实出膛，明确不含玩家运动物理验收。
>
> 停止路线：全景逐帧低分辨率/低抗锯齿合成显著更慢；地形0.5/0.75缓存无稳定收益；原生MEDIUM无稳定改善，LOW少量变化伴阴影损失；每帧切换质量更慢；请求GPU模式未见可采用收益。v30隔2/3帧半分辨率重画+镜头平移缓存中，3帧档横移66.927→65.399ms仅约2.3%，>100ms长帧14→26且动画滞后；不部署。别重复仅挑均值/快窗或把诊断上限120fps当正式30fps验收。
>
> 新能力更正：桌面AIR不是绝对不支持LOW/MEDIUM；隔离描述符allowLowQuality=true可解锁，正式描述符未改。共享事实desktop-stage-quality-limit已更正。v29合格交火12/12 CPU/分配采样中1157 CPU记录有359条GC上下文，不能将GC触发处全归因AI；采样本身增压且有18片新预绘。快照复用/区域键/炮塔guard已有负结果，不能凭栈再次直接采用。
>
> 完整限制、负结果及画面对照见[本轮报告](../knowledge/experiments/quality-and-dense-enemies-20261101.md)；冻结清单/汇总在build/generated/quality-evaluation-20261101。后续需要新的完整帧收益证据；尚不能准确分摊多敌人中的原生呈现、AI与回收净成本，不声称耗尽所有优化空间。他人源码/状态/13份报告保留。
<!-- /quality-and-dense-20261101 -->


<!-- lossless-cut-survey-20261101 -->
> 2026-11-01 无损切口普查：本轮正式文件未变，宿主仍 **9D8662F6**、CS D8A、WB FE3、RV AEA、RC6906等14模组保持；前轮显隐回归修复仍在。完成10次隔离游戏运行，含1次保留的预热超时，计时共29892有效间隔；另有一次排队超时未启动。所有自有实例/登记已结束。
>
> 已核对地形、物体显示树/缓存、时间轴/焦点、环境查询、AI快照与调度、其它模组分配、GC和运行库。快照复用、不同中性分组及缓存、主动GC和新版运行库未取得可部署的稳定明显收益；没有新性能产物进入正式安装。各自像素/时序边界与失败见[普查报告](../knowledge/experiments/lossless-cut-survey-20261101.md)及build/generated/lossless-cut-survey-20261101/summary.json。
>
> 保持原画质、原生隐藏、追击和屏外命中。普通Box本已cacheAsBitmap；桌面cacheAsBitmapMatrix不支持，不能重复包装成新切口。120fps容量/离屏像素不能冒充正式30fps/原生Stage验收。不声称已接近原版或数学意义耗尽所有无损空间；新渲染实现仍需新的整帧收益和等价证据，不能仅换参数重跑已否定实现。他人状态/源码/报告保留。
<!-- /lossless-cut-survey-20261101 -->


<!-- camera-optimization-20261101 -->
> 2026-11-01 后继优化已实测：正式宿主 **9D8662F6**（14:58从CA94只撤掉sceneTick无条件单位显隐，前三层A2/预绘预算保留）；CS **D8A68A4C**、WB **FE3E7A84**、RV **AEA30314**、RC **69060487**等14模组组合保持。回执：build/generated/camera-object-clip-v7-20261101/visibility-fix-deployment.json。原生UnitSpectre隐藏复验通过。这是显隐回归修复，不是已证实性能提升；重启生效。下方旧安装表与迭代条目是历史记录，当前以本段为准。
>
> 9次独立游戏运行，7次时序实验15740个有效间隔；所有自有实例/登记已结束。整层裁剪、物体缓存、炮塔guard、既有地形节点缓存均无稳定收益。旧局部phase在真实0.658333缩放alpha失败；禁止凭旧2/3测试放行。屏幕像素缓存v13两窗十图合格，但小窗28.018→27.202ms仅约2.9%且长停顿更多，大窗35.190→39.166ms更慢，停止、不部署。没有新性能候选进入正式文件。炮塔goto栈可能执行全局帧脚本，不等于炮塔重建；90帧片段与GC周期错位不能当P99收益。
>
> 远处活动范围旧候选缺少内部警戒/延后攻击保护，未运行或部署；保持追击和屏外命中。性能目标尚未达到近原版。详见 [本轮报告](../knowledge/experiments/camera-optimization-followup-20261101.md) 及 generated/camera-optimization-review-20261101/summary.json。后续不重复上述已停止路线；需要新的整帧成本证据，而不是扩大预绘预算或放宽画面要求。他人的SceneRenderChecks、既有状态和13份报告保持。
<!-- /camera-optimization-20261101 -->


> 2026-11-01 当前迭代审核：正式仍 CA94/D8A/FE3，RV实际为AEA30314；本轮未覆盖任何正式产物。新增单位显隐在原版UnitSpectre上复现 false→true，A80阴性对照保持false，第四层不能判“零视觉影响”。4轮12684间隔：补绘稳定后横纵移动仍增加呈现成本；大窗物体层隐藏4/4变快，光照层无稳定收益；35次>100ms中32次伴随明显堆回落。12/12分配采样又指向炮塔gotoAndStop/构造子显示对象/FocusManager链及TDFC快照。旧“纯镜头基本无成本、主要是战斗”的排他结论不再沿用。详见 [迭代审查](../knowledge/experiments/camera-iteration-review-20261101.md)。调查未等于修复：优先安全撤掉无条件显隐，再验证物体呈现、缩放地形和回收尾部；不直接复活旧质量/sleep/炮塔候选。所有本轮自有实例和登记已结束；他人 SceneRenderChecks、MEMORY/journal原修改与报告均保留。


## 1. 模组与当前任务

全图碰撞、敌人、物品预生成，画面按视野准备，镜头与弹体连续跨房；远处未参战敌人可暂缓。当前CS0.9.4（分帧平滑唤醒）另含单地图编辑、天角兽局部报警/接力概率、SATS按视野截图及有条件的地形呈现复用，原版连续模式由设置开关控制。

性能任务仍未完成。用户明确优先镜头移动，并补充V开启SATS延迟；入口为普通游戏／模组启动器。SATS已修复部署；2026-10-29 02:58又部署有限镜头优化，真实产品横移约11.7%、纵移约9.7%、原生移动交战约6%平均间隔改善，但长停顿仍有，不宣称近原版或完整解决。不能用暂停世界、删敌或探针局部helper数字冒充真实产品收益。当前没有goal对象。

此前用户报告马哈顿废墟载入 `Unit.run #1010 / Error unit 鼹鼠`。已完成两侧边缘确定性复现、四处列读取守护、六次普通/连续进入和144正常运动状态一致，修复先部署B84F、现保留于A80。详见 unit-prestep-boundary-20261028.md。

## 2. 约定与权限

- 中文简洁进度；性能会话01a13816-367b-7261-8e11-ca9152565dd9。已允许实测；通过相应门禁后可本机部署，不重复确认。
- 已允许必要RV、WallBlend、LAD、TDFC、RConnect兼容。RC由负责人01a086bb-378c-7f60-b8e1-50d90ffa0996集中部署，本会话不并行覆盖。
- 已允许修复ModLoader共享测试登记器；2026-10-29又明确优先修复原启动器和多会话测试路径，已完成并部署。其他跨模组写入不自动扩大。
- 接受视野预绘、远处未参战敌人暂缓、纵向镜头缓冲；保留追击者和飞行弹体。允许RGB最多2/255、alpha不变的实验，仍须真实明显提速与功能正常才部署。
- 当前完整大场景性能测试保持4GiB提交/2GiB物理预检、512MiB运行中止；有界等待采用3次间隔5秒均≥5GiB。此为该夹具保护，不是所有离线操作统一门槛。低内存离线构建独立限制自身512MiB，不改变游戏保护。
- 测试先登记，唯一APP ID/存储、私有桌面，默认静音；不写真实APPDATA/pfe，不停玩家或外部实验，不用Ghost。跨会话协调不能超出用户已授权的具体消息。
- 一次10分钟实验协调已使用，对方无安全自然暂停点，窗口未开始；不重复发送或干预外部进程。当前无自有Java/AIR/等待句柄。
- 已授权按本会话逐条登记≤10分钟精确构建调用授权，不关闭护栏。hooks当前exec映射Bash，载荷command；根functions store有cs_exact_grant_template（上下文丢失时按hooks README重建）。
- 无AGENT_SCOPE；不创建。src/tests/SceneRenderChecks.as是他人WIP，不恢复或提交。2026-10-28另一用户授权任务已取消天角兽旧“仅候选”限制并部署，不能回退其更新。10月21日下午被撤回7D42/5432配方仍不可复活。

## 3. 当前正式安装

天角兽任务2e828d8、A796染色/纵向缓冲、B84F预跑边界和180d46f的SATS修复均保留。2026-10-29 02:58:52已安装CS0.9.3及WB0.5.10-scene；本任务未再改根宿主A80、DLC或配置，RV BD64与RC6906由其它任务更新并保留，RC仍归负责人。新回执state/camera-presentation-deployment-20261029.json为installed/readback通过；备份build/backups/camera-presentation-20261029-025849-fe3f35922315。旧SATS回执描述旧380产品，不能当当前正式产品。

| 文件 | SHA256 |
|---|---|
| 根pfe.swf | **1D2004AB4C972F199FDD6BCA708C8F483C8314FED77AEA477FB9544F33AB02F3（2026-11-04 13:36 弹痕不废预热；需重启；回退备份 build/backups/pfe_before_decal_nocancel_20261104-133604.swf）**；前值 A9B39CC742078D7A7D9F289EE408EDAE11C3AAC376A43246B306B91AC7AD2D94（2026-11-01 空间分区碰撞+预算48+A2；无屏外隐藏（并行会话回退）；备份 pfe_before_spatial_collision_20261101-225837.swf → pfe_before_budget48_20261031-171254.swf → pfe_before_a2_gutter_20261031-163909.swf → pfe_before_visualneutral_budget_20261031-121918.swf） |
| CS0.9.7（当前） | 447AE02B5AC1E038E44DA2488C4BDB2D5945C1BCFBAE36C86AB9F0D6FEC0E2EF（2026-11-04 事件驱动增量剔除；需重启生效；回退备份 `ContinuousSceneMod-0.9.6-F16890C9-before-eventculling-20261104-005240.swf`；回执 state/event-culling-deployment-20261104.json） |
| CS0.9.6 | F16890C959D86E305B5D3AC91CC31B8689E347179722A2F0CC07E8CB45B7E123（2026-11-02 脱战拴绳+威胁双盒+震屏容忍；已被 0.9.7 取代；旧 0.9.5 = 1A66B1F4…5612，0.9.4 = DF3B6812…C8426，0.9.3 = D8A68A4C…2E677） |
| WB0.5.10-scene | FE3E7A84753F6F3614440F69F8725E6E8639AEE4755ACF878AAFCFEDB95AC2E6 |
| TDFC | 7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5 |
| ModLoader2.5 | 2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2 |
| RV（其他任务更新） | BD64B5BBFE5A07A0B5BFF38E4C344652E1DF526CFD5C308D63B607123CE4A9AD |
| RC（其他任务更新；非本任务部署） | 690604878BD8707007A99E3AD14F8F5F3F55CDD4948C8DEBE6CC87363AFD38C9 |

最新安装只同步CS四源（入口/SATS清理钩子及新增SceneEventBitmapFill、ScenePresentationCoordinator）和CS/WB两份产物。WB沿准确13源生产配方，仅增加启用前同步恢复钩子；其HEAD仍不是完整生产源，不直接构建覆盖。准确源位于build/generated/camera-event-fill-product-20261029/{frozen-product-src,wallblend/frozen-product-src}。旧0.9.2/0.5.9为380/141，备份保留。LAD8ADB及其它配置未改，外来SceneRenderChecks.as未碰。
共享工具本轮更新：air_test_process 010597B0、launch_integrity 6EEBD3CD、test_registry 8E052672、mod_debugger 86AEAE63；test_resources仍86D5F280。资源只设自有子进程normal CPU、memory5、HighQoS，不能改全局或外部进程。

## 4. 最新接续：启动与测试路径已恢复，三层缩放候选仍待性能验收

2026-10-30 三项镜头实验完成（本会话）：①战斗走动 +11.6ms 对应用户 +11.2ms 走动差，战斗/AI 为运动差主体；②默认窗口 1280×720（scale0.6583、回退原生）与 scale1 近同速；③块归因双风格组=2×单组，候选 A2（C33A2FBC，仅 sceneBeginWarm）边界块 78.8→56.7ms、中心像素不变；候选 A3（A2CB22A7，再改 sceneEnsureUpcoming）快速平移最大帧 343→161、forced 3→0，代价极端速度 21/55 帧空洞。均为 81C1 诊断宿主、未部署；需 A80 移植+WB/空洞门禁+用户取舍。报告 `camera-combat-window-lead-20261029.md` / `chunk-cost-attribution-20261030.md` / `chunk-fastwarm-candidate-20261030.md` / `chunk-forced-spike-candidate-20261030.md`。

2026-10-30 A80 移植判定：A2-A80 `7180CD1A`（仅 sceneBeginWarm）、A3-A80 `5E318EC6`（再改 sceneEnsureUpcoming）在 A80 上单方法替换、载入运行通过；控制实验证明 A80↔81C1 该原方法字节相同、FFDec 重编译原方法字节不变。快速平移 v8：基线 78.93ms/P95 204/max 343/forced 3/空洞0；A2 71.73/179/309/3/0；A3 117.07/206/255/0/24。同日 v7 基线：A2 正常相位 ±1.6ms、跨新块 39.28→37.03；A3 在无 misses/预绘/空洞时仍 +3~9ms（两次复跑一致，原因未完全定位）。用户条件“空洞若实证大幅提升则接受”不满足：**不部署**，A80/D8A 等均未改。报告 `a80-fastwarm-port-20261030.md`，证据 `camera-a80-*`、`camera-baseline-now-20261030-r1`。

2026-10-31 A3 慢帧定位 + 视觉中性候选：v9 计时探针手动 `g.sceneTick()` 三宿主均 0.07–0.65ms，A3 正常相位落后实为偶发大帧（pan 45.7ms，剔除前 8 帧 34.1ms，含 1817ms 单帧），A3 不再推进。新候选仅改 A80 `sceneEnsureUpcoming`（预热环 ±3、预算上限 36ms，`626DFBC8`）：绘制路径未动，front/voda 中心像素 0 差异；快速平移两轮 P95 237/238→137/180、max 332/406→221/333、mean −4~5ms、forced 3→2、空洞 0；正常速度 ±0.15ms；默认窗口冒烟通过。代价极端场景驻留 +14~19 块（≈36–49MB）。**未部署**，报告 `visual-neutral-budget-20261031.md`。

2026-10-31 **已部署**：根 `pfe.swf` A80ED32B→`626DFBC8`（同上单方法补丁）；备份 `pfe_before_visualneutral_budget_20261031-121918.swf`，回执 `build/host-patch-receipt-visualneutral-budget-20261031.json`。安装后隔离字节探针通过（10 断言；与 RConnect 并发，相位偏慢不作性能证据）；性能证据为安装前同日成对轮。回退=备份覆盖根 `pfe.swf`；CS 模块/WB/RV/RC 未动。需重启游戏生效。

2026-10-31 性能切口全面搜查（当前宿主）：帧成本采样确认原生 `[render]`/`[pre-render]` 为最大 CPU（45–132 样本/8 窗）；`sceneNativeEnvironment` ~14,900 分配/8 窗（旧 clamp 已否定）；`UnitTurret.animate→gotoAndStop` 链 ~1,050–1,920 分配 + 12–17 CPU，守卫候选 `1666FCB1` 两轮配对无帧收益→否定；“减分配≠减帧时”再次成立。剩余大切口是原生渲染（视觉风险）与其它模组的每帧 JSON/NetHud 分配。报告 `performance-cut-survey-20261031.md`。

2026-10-31 **已部署 A2 gutter 快速暖块**：根 `pfe.swf` 626DFBC8→`8EAAE4EE`（仅 `sceneBeginWarm`）；备份 `pfe_before_a2_gutter_20261031-163909.swf`，回执 `build/host-patch-receipt-a2-gutter-20261031.json`。快速平移两轮 mean −4~5%、P95 −9~35%、max −35~45%、forced 3~4→0~1、misses→15~17、零空洞；正常速度 ±0.7ms；front/voda 中心像素 0 差异（back 为动画噪声）。视觉代价仅 gutter 近似（伤害/WB 边界采样；当前 WB 关闭）。报告 `a2-current-deploy-20261031.md`；需重启生效，回退=备份覆盖。

2026-10-31 **已部署预算上限 48ms**（三层完成）：根 `pfe.swf` 8EAAE4EE→`9D8662F6`。快速平移两轮 misses 17→9~10、forced→0、P95 156→122~140。三层累计：mean −5~9%、P95 −18~29%、max −40~46%。报告 `budget48-deploy-20261031.md`。

2026-11-01 **已部署屏外单位可见性管理**（四层完成）：根 `pfe.swf` 9D8662F6→`CA94AF17`（仅 `sceneTick`：视口外 500px 单位 `vis.visible=false`）。宿主干净 A/B（3 对）pooled +1.4%（0.6ms）；探针级 13~21% 为高估。正常战斗走动 ~42-44ms（vs 33ms 目标）；剩余瓶颈为战斗/AI 与原生渲染。报告 `unitvis-deploy-20261101.md`。

2026-11-01 **已部署 LOW 渲染质量**（五层完成）：根 `pfe.swf` CA94AF17→`8321E4E7`（仅 `sceneTick`：连续场景 `quality="low"`，退出恢复 `"high"`）。v11 同轮 A/B 15~17%（4 项一致 −7.4~−8.3ms）；跨轮不显著（噪声）；探针 beforeNative 覆盖宿主使验证困难。视觉代价：单位/特效边缘略粗糙（地形位图不变）。报告 `lowquality-deploy-20261101.md`。

用户要求先修复基础设施，已完成：[ModLoader本轮证据](../../ModLoader/knowledge/experiments/startup-test-path-2026-10-29/README.md)。确认根Remains.exe/adl64.exe继承Low标签，普通运行器启动后子进程降至4096；同字节Medium副本通过39项，再修复四个入口标签，文件/DACL不变。原启动器主窗口正常；共享工具以指纹核对方式复用普通标签ADL，保留隔离库/应用ID/存储。68项工具检查、双AIR78项、两个独立CLI真实菜单并行通过，全部自有进程/登记结束。默认功能两组并行，性能`game`仍独占；不需要重做已否定的TEMP/可见窗口尝试。本轮无CS源码或SWF部署，3686890F候选尚未计时。

最新报告`knowledge/experiments/camera-pacing-phase-20261029.md`。A473当前产品30/120真实对照4320完整区间：30纵移汇总41.406→41.064ms，前后方向反转，不是稳定改善；120容量不能当正式30fps体验。局部相位F03/round全四层均2/3五图alpha最大2，已停止。分层切换诊断不能独自充当首次绘制合格。

独立mask7候选37F397BA仅接管Front/Back/Back2，水层原生。FA568367纯首次绘制15图（2/3、.5、1各5）RGBA全精确、创建清理平衡；同布局但自然玩家位置/单位数不同，不跨轮宣称解释旧全部误差。后继A283两轮计时前因出生点贴下边缘无法同时满足±96纵移及玩家屏内而正确失败、0样本。新3686890F平台夹具已编译：只在测前把隔离玩家放到现有净空地板一次，正常站稳45帧，再测完整2160区间；没有地图/敌人修改，不假装全程未移位。尚未执行到AS层，没有性能收益、未集成生产。

此前13:55后AIR在游戏代码前0xC0000142退出；原启动器同时报临时路径访问被拒、日志停在09:16。此前换TEMP与可见样例未恢复的事实留原报告，现已用令牌/标签及同字节恢复实验归因并修复。用户确认Remains.vbs仍可进入游戏，不据此否定入口标签问题；也不能把所有0xC0000142一概归因为此。

用户仅额外允许一次约10秒可见小样例，已使用；该授权不延伸到全图可见测试。后续默认继续私有桌面测试。运行环境已恢复，下一步可测3686890F；不部署仅图像通过的候选。不改外来SceneRenderChecks及camera-light-warm-lead的.dshclaim。下述前轮缩放/屏外结论仍有效。

2026-10-29 后续用户强调横纵镜头与卡顿相关，并要求攻击命中屏幕外和 RV 遮住的敌人。新增 `offscreen-hits-20261029.md`：A80/D8A 不改，两轮真实 Bullet 组件已证实屏外自然休眠敌人能受伤，下次调度唤醒；RV关闭20项、开启21项；实墙/到期阴性通过，其他119/111睡眠者未醒。短弹道在敌人附近生成，不是枪口全射程、光束、爆炸或AI后续动作验收。实际依赖 RV BD64（D56）/RC6906由其它任务更新，收尾仍为该值，不能恢复旧638/239。第三轮屏内RV隐藏候选 AE055F7F 已编译，首次运行启动前低于4GiB保护线失败，无AIR，补查仍约2–3GiB。

轻量 `cell-sampling-mini-20261029-r1` 使用合成400×400图，无游戏载入；18组合、72自有输出释放、原生重复和源不变通过。scale1/.5各6项精确，2/3六项world/local fill均RGB/alpha最大255；**单格局部Sprite锚定不能修复此取样误差，停止该修正，不生产化**。根已查看参照/局部图片；不是游戏Stage/拼缝或性能证据。2GiB/1GiB预检只属此轻量夹具，不放宽完整地图门槛。两次游戏AIR和一次组件AIR全部退出，所有自有登记结束，无后台承诺。本轮仅测试/文档，无部署；镜头仍未解决。

用户要求继续深入优化，并确认大窗口与默认小窗口都明显卡顿。报告`knowledge/experiments/camera-scale-coverage-20261029.md`。正式A80/D8A/FE3回读保持；四次实际AIR及一次启动前失败均结束，无自有进程或等待。

- 1280×720实际进入时isZoom2、scale2/3、原帧率30。当前呈现只支持scale1，旧.5/.8检查仅验证回退；这是适用覆盖缺口，不能解释大窗口卡顿或称唯一主因。
- 缩放v1-r1独立APPDATA权限失败，未启动；r2 AIR79304在暖图玩家投影条件失败，候选updates0；像素专用v2 AIR20740允许镜头离开玩家，但根getter与concat量化差使资格回退。均无像素性能结论，原失败保留。
- v3 AIR44040/56E0E91A实际完成10图：2/3五图RGB146–191、alpha255不合格；.5五图RGBA精确；.8在拼接矩阵资格处停止，未做候选图。独立partial-pixel-review验证原生重复/恢复、实际矩阵及4280次alpha/40节点清理平衡，不把整体失败改通过。根已查看PNG。**停止直接放宽缩放资格**，不继续放宽.8资格，不据.5图像证明性能或部署。
- 完整预绘环memo：当前3259 C5D891D9/1655字节核实；诊断569B3CB5只加可选回调，保留5770方法/1016类/其它tag及逆编辑。全±2环阳性存在证明守字典/对象/尺寸/resident/evictions，无job/退出时原路径。诊断宿主禁止部署。
- upcoming-r1 AIR38148/61ABBEF1：2160完整区间/28断言，168模拟缺格检查；逐2161观察验证A每帧0回调、B每帧1，1080调用=1076命中+4证明，266格读取、0miss。静23.203→22.472、横35.658→32.228、纵31.444→33.339ms；纵慢6.02%。横原路径最后一窗52.011ms/36长帧，保留不删，不作9.62%严格因果提速。**停止memo候选，不生产化**。
- 上轮七次测试、环境键/炮塔/透明阴影等停止结论仍有效，详见camera-motion-20261029.md与本次归档MEMORY-history-20261029-before-scale-coverage.md，不重做。

本轮图像是零计时组件实验，memo是120fps容量实验、玩家可离屏；五张开关图不执行upcoming，168项非真实冷态回归。不能当自然跳跃/30fps节奏/视觉全开或近原版验收。没有改生产src/release/根SWF、配置或真实存档，外来SceneRenderChecks保持。

**已部署里程碑仍有效：**CS0.9.3真实product-camera横约11.7%/纵9.7%、product-live约6%平均差且有自然负载差异；长帧并未消失。1213产品检查、7原生V、14SATS像素用例通过。呈现仅scale1/native320/无震屏且RV enabled/wallbright、WB、LAD全关时启用，否则回原生；开效果只证明回退兼容。SATS早前同图开启842/891/713→144/235/184ms已安装，鼹鼠边缘预跑#1010也已修复。

## 5. 累积活动线索与停止路线

NativeSceneActivity的engaged永久锁尚未被针对性证伪。旧range第13窗awake43→85，后续83–87，总单位167；末态近处43、远处仍有目标22、历史标志/宽限/弹体混合14。不能把14全归旧锁。activity-release实际released=0、engagedMayRest=0，没有目标路径阳性。
调度自身约0.54–0.63ms不能代表另约4.05–5.12ms的单位step。awake可能含离链单位，须先统计链内存活、保活原因位集、实际step次数/耗时；本轮没有改变休眠资格。

已停止的具体呈现方案不换名重做：farparking确实管理Box1202/Bonus125个vis/shad显示根，不是Box对象数或仅睡眠敌人；range每个候选帧至少711个Box根已移出显示父层，整帧仅约2.15%且四对反向。range的frameChanges=0是未更新默认字段，不是时间线不变证据；严格静态Box普查603经资格筛选剩0，未到屏外判断。内景合图4.37%且横向反退；RV后继约1.59%；视口条带、透明裁剪、GPU地形、wholeworld缓存等详见历史快照。暂停角色缓存不是动态渲染全部无效的证明。lighting2旧热点已由80CF解决，decal准备只约0.06ms而绘图约3ms，旧图章/副本路线已停止。
A796/4E5F实际sceneTick无每帧setZoom，不能用陈旧Grafon/Camera源码整包覆盖。
SATS整数格批量draw再copyPixels已由旧33C1实测否定：7组像素失败，RGB最大3/alpha2；此前只读复核，未重新生成/运行。当前全源可见性不同仍不足证明会消除旧误差；A80宿主保留逐格方案，CS当前D8A。
曾被拒的Monstrik、合并Weapon/UnitVisual+截图、UnitPlayer/SceneObjectCulling组合、Pt+PNG枚举、tag93遥测补丁、CIM CPU查询不转路重试；历史上的更细FA2B DoABC类标签枚举亦被保护拒绝并停止。未请求新授权，兼容结论仅用其他已允许来源。

## 6. 下一步与未完成边界

以镜头移动为核心，正常模拟、完整间隔、长帧和真实画面不能省略。最新证据仍指向可见地形/物件的原生合成成本；局部CPU、分配次数、透明节点数下降均未稳定转成整帧改善。不能据此宣称找到唯一根因、近原版或优化完成。

后继若有新的可检验呈现假设，先与已停止路线及当前准确产品核对；不自动重做环境键、炮塔同帧守护、透明阴影、Math.max clamp、节点cache/combo、远景缓存、全世界缓存、旧Box摘树等；最新完整环memo和直接放宽非整数缩放资格也已停止。对象层细分的错误在计时后摘要，现有完整数据已独立核验，不为修报告重跑同一套2700区间。普通房间、自然纵移/长探索、效果开启与全图2–5秒加载仍未全面达标。

旧活动范围候选只编译、未运行，其旧宿主/源码不等于当前A80/D8A，不是待补做债务。本轮透明阴影普查已运行，撤销旧“未运行”停点；其后继候选结果为不部署。不要恢复已撤回的下午配方或覆盖天角兽/染色/SATS/鼹鼠修复。

保持登记排队、独立静音存储和4GiB/2GiB游戏创建线；不关闭玩家、外部实验或其他任务进程，不重复泛泛索要内存。所有本轮自有实例与登记已结束，没有goal对象，不按旧blocked计数操作不存在的goal。没有后台继续测试的承诺。

## 7. 深入入口

- 最新缩放/扫描：`knowledge/experiments/camera-scale-coverage-20261029.md`；scaled-v3的partial-pixel-review与upcoming的callback-observation-review保留整体失败/容量边界。
- 上轮镜头接续：`knowledge/experiments/camera-motion-20261029.md`；各r1完整证据和独立失败计时复核；完整上一快照`state/MEMORY-history-20261029-before-camera-motion.md`。
- 最新镜头/SATS：camera-sats-current-20261028.md；evidence/camera-nearplayer-layer-split-20261028-r1/{camera-layer-review.json,storage/result.json,process-policy.json}；evidence/camera-nearplayer-tail-20261028-r3/{camera-tail-review.json,camera-nearplayer-tail-inputs.json,camera-air-wait-result.json}；evidence/sats-visible-product-checks-v3-20261028-r1；build/generated/sats-visible-release-20261028/{verification.json,host-audit.json,product-build.json}；state/sats-visible-deployment-20261028.json。keycache v2/v3失败目录与鼠标RESULTS保持原件。
- 当前event-fill：state/camera-presentation-deployment-20261029.json；build/generated/camera-event-fill-product-20261029/{verification.json,verify_deploy.py,product-build.json}；evidence/camera-event-fill-product-{live,camera,checks-v3,memory}-20261029-r1/RESULTS.md。前3项是本次产品证据，memory仅观察且高开销。v1/v2实验和反序结果仍在旧目录，不能取代当前产品结果。
- 停止node-cache：build/generated/camera-event-fill-node-cache-camera-20261029/RESULTS.md及同名evidence后缀-r1；失败live见camera-event-fill-node-cache-20261029/RESULTS.md。不与9D8F纯像素复用混同。
- v2像素组件：build/generated/camera-event-fill-pixel-checks-v3-20261029/RESULTS.md及同名evidence后缀-r1；旧pixel-checks-r1失败原件保留。组件通过不等于动态收益。
- 历史真实战斗详情见camera-live-reassessment-20261028.md；当时参照evidence/camera-dense-reference-rc2-20261028-{normal,scene}-r1/summary.json；tail/build.json、runs；activity-range-current/BUILD-RUN.md；binary/RESULTS.md、audit-proof.json；live/verify_run与paired/RESULTS.md。
- 之前完整快照MEMORY-history-20261028-before-live-reassessment.md保留全部停止路线、源码种子和历史入口；journal顶部按时间接续。
- 原生单次镜头旧证据camera-native-once-20261028：base-r1 AIR24656、cache-r1 AIR70412已退出；2F7B探针、冻结源9b56efbf、pair-review A5471DA2，所有原始输入冻结。
- 85源种子camera-atlas-paged-combat-20261025-r1/probe-build.json SHA983727AE；F15旧候选F15B8CE8与428字节算法来源仍保留，不部署。
- Python C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe；Java D:/Program Files/Adobe Animate 2024/jre/bin/java.exe；Flex/SWC/FFDec在mods/Sandevistan/build/tools，只读依赖。
