# ContinuousScene 三项问题：证据分级可执行优化方案（v2 · 2026-11-04）

<!-- implementation-update-20261104 -->
> **实施更新（2026-11-04 14:35）**：本方案已被执行过一轮，结论如下——仍要看细节时以各报告为准。
>
> | 方案条目 | 状态 | 依据 |
> |---|---|---|
> | P0 相位归因探针 | **已完成** | 探针在 `Camera.calc→sceneTick` 内拆相位；探索 CS 5.67ms/帧、战斗 3.00ms/帧；≥100ms 帧里 CS 只占 21%/8% |
> | P2 弹痕不废预热 | **已实施并部署** | 宿主 `A9B39CC7 → 1D2004AB`；同调度 1300 帧 `cancelCount 10→0`、`cancelWork 302ms→0`；回执 `build/generated/opt-20261104/deploy-receipt.json` |
> | P1 拆 `drawKusok` 子步 | **不做（实测否定）** | 三轮 `maxStepMs` 仅 20–25ms，非冷态曾见的 125ms |
> | P3 弹痕/`sceneApply` 空间索引 | **不做（实测否定）** | `markMs` 0.03ms/帧；566 次 apply 合计 5.9 万次矩形相交 |
> | P4 `sceneApplyCompactDecal` 分配修正 | **不做（收益<验证成本）** | 减分配≠减帧时（四次判例） |
> | ① 地形双线性 | **作废（用户窗口）** | 用户用**大窗口/全屏**，`scaleV=1` 时无重采样；`zoom100` 用户明确否决 |
> | **新 P3'：远处逐出 + 缓冲复用** | **本轮新增首要候选** | **长帧归因反转**：≥100ms 帧 85–100% 与一次 50–165MB 内存回落同帧；每块分配 4×2.56MB 且从不复用 ≈18MB/s → 约每 80 帧一次回收，把该帧拉到 100–171ms。见 `knowledge/experiments/long-frame-memory-20261104.md` |
> | B-P1 天角兽计数探针 / B-P2 | 工具就绪，证据未定 | 20.9 探针 `alicorn-v3` 已可跑；首轮 900 帧未见警报拉活（awake 27–35、唤醒 11 次），但判别字段运行被玩家游戏挡住 |
>
> 逐条细节与复跑入口见 `knowledge/experiments/phase-attribution-implementation-20261104.md`、`long-frame-memory-20261104.md`、`alicorn-count-probe-20261104.md`。
<!-- /implementation-update-20261104 -->

> **文件标识**：`mods/ContinuousScene/design/scene-combat-camera-optimization-plan-v2-20261104.md`
> **编制**：2026-11-04，Lead 会话（含 3 名并行调查员 + 1 项 AIR 离线微基准）
> **基线（本轮实测核对）**：宿主 `pfe.swf` = `A9B39CC7…2D94`（未变）；CS release = **0.9.8 `285625F4…8ACF`**（2026-11-04 04:51 部署 aim-look，前一版 0.9.7 = `447AE02B…C2EF`）；`scene.xml` = `1CEA74E2…7A9E`（沿用，本轮未改）。
> **与旧方案的关系**：`design/scene-combat-camera-optimization-plan.md` 定稿于 2026-11-04 03:50，其中多处数字与机制**在本轮被证伪或降级**（见 §6 逐条对照表）。本文件是**证据分级后的可执行版本**；两者冲突处以本文件为准。旧文件同时被另一会话认领校正，合并时请以 §6 的证伪清单为裁决依据。

---

## 0. 三句话结论

1. **探索卡顿**：当前**没有证据**说明长帧由 CS 逻辑驱动（`cold-r3` 里 47 个 ≥100ms 帧共 5975ms，帧内可命名的 CS 事件只占 385ms=6.4%）；但**已有的 CS 归因测量本身有盲区**（模组 ENTER_FRAME 计时不含 `Camera.calc → sceneTick` 驱动的预绘/同步/剔除），所以 6.4% 只是**下界**。真正能把单帧打到 31–178ms 的结构只有一处：**视口 miss 触发的同步整块补画**；能把单帧打到 125ms 的是**不可中断的 `drawKusok` 单步**。下一步必须是**一次带相位分解的测量**，而不是再改一个数。
2. **单只天角兽**：天角兽自身的函数成本 ≪1–2ms/帧（`findBox` 0.05–0.6 次/秒、`actPort` 每次 ≤12 次瓦片检查、`alilight` 0.4–0.5 发/秒且约 90% 命中在 `sceneApply` 入口早退）。**唯一有量级的链条是“警报/目标共享把同一房范围内的同阵营单位拉活”**——每个额外活跃单位约 +1.5–2.0ms/帧（既有实测），3–8 个就能把 35ms 帧推到 45–60ms。默认接力概率 0% **只断“接报者再转发”**，不阻止首发者在 1920×1000 内的直接通知。
3. **背景粗糙 / 动态模糊**：动态模糊在本机 AIR 软光栅上**不可做**——离线微基准直接测到**最便宜的单向模糊 15.5–19.5ms/次**、双向 quality1 20–22ms、挂到世界容器单次绘制 23–59ms（无滤镜时 4.4–11.9ms）；而 30fps 的整帧预算只有 33.3ms。背景“粗糙”的真正来源要**先分清窗口**：`2048×1123` 时 `cam.scaleV=1`，**物理上没有最近邻重采样**，粗糙只能来自 30fps 与帧时抖动；`1280×720` 类窗口 `scaleV≈0.658`，才有“非整数缩放 × 最近邻”的爬行问题（开双线性可改善，代价 +3.9–7.2ms/帧）。

---

## 1. 本轮新增证据（全部可复核）

| 产出 | 位置 | 性质 |
|---|---|---|
| 探索/预热/同步/取消链只读调查（含 cold-r3 逐帧复算） | [explore-warm-sync.md](../knowledge/experiments/scene-combat-camera-investigation-20261104/explore-warm-sync.md) | 源码确证 + 已有实测复算，未运行游戏 |
| 单只天角兽交战只读调查（含旧断言复核表） | [alicorn-combat.md](../knowledge/experiments/scene-combat-camera-investigation-20261104/alicorn-combat.md) | 同上 |
| 镜头背景粗糙 + 动态模糊代价调查 | [camera-visual.md](../knowledge/experiments/scene-combat-camera-investigation-20261104/camera-visual.md) | 同上 |
| **AIR 离线成本微基准**（本轮新做） | [blur-benchmark-lead.md](../knowledge/experiments/scene-combat-camera-investigation-20261104/blur-benchmark-lead.md) | 本机 AIR SDK 51.3 + `adl64`，离屏 `BitmapData`，2048×1123，两轮独立运行 |
| 微基准源码与可复跑产物 | `build/generated/filter-cost-20261104/`（`src/FilterCostMeter.as`、`app.xml`、`app-debug.xml`、`build-bench.ps1`、`FilterCostMeterDebug.swf`、`run2.txt`） | 可复跑 |

**证据分级约定**：【确证·文件:行号】= 本轮逐字读到的源码；【已有实测】= 本仓已落盘报告中的计时；【离线代理】= 本机同原语微基准（不是游戏进程内数值）；【推断】= 由上两者推理，必须实测才能成立。

---

## 2. 问题一：探索新场景时偶发严重卡顿

### 2.1 现状证据（先看这张表，再谈改什么）

| 事实 | 数值 | 出处 |
|---|---|---|
| 真实游玩画像 | 196.364s / 5143 帧，**26.19 FPS**；38 次 >100ms；最大 242ms；移动窗 25.84 FPS / 静止窗 28.27 FPS | 已有实测 `stutter-investigation-20261103.md:31-39` |
| 长帧是不是只在“探索新场景” | **不是**。2048×1123 的**非战斗行走**对照里，>100ms 仍达 **10–21 次/分**（均值 37–39ms、P95 47–57ms） | 已有实测 `gc-combo-current-20261104.md:21-26` |
| 长帧与 GC 的关系 | 29 个 >100ms 帧中只有 **9 个（31%）** 邻近 GC | 已有实测 `gc-combo-current-20261104.md:40` |
| 一次同步整块补画 | **31–178ms/次，均值 68ms**；`sceneMaxDrawMs` 296 | 已有实测 `stutter-optimization-implementation-20261103.md:66-74` |
| 同步补画在何时发生 | cold-r3 共 29 次/1985ms，其中 **28 次集中在入口首屏 1.88s**；行军中仅 1 次（43ms） | 同上 |
| 预热总工时 | 81.7s 内 `warmMs=5814`（7.1%），`warmSlices=595`、`sceneWarmCount=98` → ≈**59ms/块**、≈33 步/块 | 同上 |
| 预算的真实取值 | `sceneWarmBudget` 实测**入图 2、行军中 20–22**（不是 48） | 微基准同目录复算 `explore-warm-sync.md:40` |
| 最大单步 | **125ms**（`drawKusok`）；≥8ms 的单步 156 次/1904ms 里 **144 次/1804ms（94%）是 `drawKusok`** | 同上 `:14-15,78` |
| 旧方案说“滤镜 20–35ms” | **不成立**：step16 `applyFilter` 全程从未 ≥8ms | 同上 `:78` |
| 弹痕取消预热 | 836 次 `sceneApply` 里 11 次真取消，废弃 431ms（预热总时长 7.4%） | 同上 `:18,172` |
| 驻留块 | 无逐出：实测 `resident=155`、`evictions=0` ≈**397MB**（2.56MB/块） | 同上 `:215` |
| 每发子弹扫块 | `applyScanned=98,628 / 836 发` ≈ **118 块/发**（线性扫全部驻留块） | 同上 `:194` |

### 2.2 已被证伪 / 必须停止的旧说法

| 旧说法 | 判定 | 依据 |
|---|---|---|
| “48ms 预算是长帧起因，压到 2–12ms 即可” | **半错**：预算实测只有 20–22（步行），48 只在快速平移时逼近；且**压预算会饿死预绘 → 更多视口 miss → 更贵的同步补画**（31–178ms）。本仓已明确记录该方向“证据不足且有反效果风险，不实施” | `explore-warm-sync.md:38-41`；`state/MEMORY.md:16` |
| “单个背景滤镜 20–35ms” | **证伪**：`applyFilter` 从未 ≥8ms | `explore-warm-sync.md:78` |
| “冷块 GC 停顿是探索卡顿主因，做 BitmapData 池” | **方向错**：块本来就要长期驻留；池化只省分配抖动，已有**四次**配对证明“减分配≠减帧时” | `explore-warm-sync.md:219-231`；`gc-combo-current-20261104.md:28` |
| “取消风暴是开火 8ms 的来源” | **降级**：取消确实存在（431ms/81.7s），但冷态配对显示 **sync 与 cancel 同块 0/29**；它是一个**可去掉的浪费**，不是已证实的长帧来源 | `explore-warm-sync.md:246-249` |
| “弹痕待应用缓冲（pending marks）能救开火卡顿” | **不要再提**：已有 196 事件配对 0/29 同块证据；且新弹痕已在 `sceneMarks` 里、预热最后一步本来就会重放 | `state/MEMORY.md:16`；`explore-warm-sync.md:246` |

### 2.3 根因候选（按“能不能解释一次 >100ms”排序）

| 序 | 候选 | 机制（源码） | 单次量级 | 证据级别 |
|---|---|---|---|---|
| **A1** | **视口 miss → 同步整块补画** | `sceneEnsureUpcoming` 缺块 →（正在预热的同一块则 `sceneAdvanceWarm(true)` 跑完整块）→ 仍缺则 `sceneRender(x,y)`；`sceneRender` 内部 `drawLoc` **一整个不可中断** | **31–178ms** | 【确证·Grafon.as:2414-2425, 725-797】+【已有实测】 |
| **A2** | **`drawKusok` 不可中断单步** | 预算只在 step 之间比较（`:3358`）；`drawKusok` 内部建 6 个 Sprite + ≈588 个掩码子节点 + `cacheAsBitmap` + 材质滤镜 + 一次性 draw | **最大 125ms**，占 ≥8ms 单步 94% | 【确证·Grafon.as:4136-4294】+【已有实测】 |
| **A3** | **弹痕重放 `sceneRestoreMarks`** | 每个新块完成的最后一步（step 24）重放**全部历史弹痕**中相交的那些；每条又做 2–3 次 400×400 级 `BitmapData` 操作；**至今没有单独计时** | 未测（随弹痕数线性增长） | 【确证·Grafon.as:3038-3041, 1161-1191】+【缺口】 |
| **A4** | 常驻块单调增长 + 每发线性扫块 | 无逐出（`sceneDrop` 只在地图切换与 warmVerify 用）；`sceneApply` 每发 `for each(entry in sceneChunks)` | 与 A3 叠加，随游玩时长劣化 | 【确证·Grafon.as:510-534, 1125-1146】+【已有实测 118 块/发】 |
| A5 | 原生渲染 / 显示基础设施 / 系统调度 | 20/29 长帧与 GC 无关，且不落在 CS 事件里 | 未知 | 【已有实测】+【缺口】 |

> **注意**：A1/A2/A3 都能解释“单帧突然变长”，但**都不能解释“为什么真实游玩里 10–21 次/分的长帧大多没有 CS 事件”**——因为那些测量漏掉了 `sceneTick` 相位（见 2.4）。这就是本轮最重要的新发现。

### 2.4 本轮发现的测量盲区（必须先修，否则后面全是盲改）

【确证·`explore-warm-sync.md:269-277`】模组 `ContinuousSceneMod.onFrame`（`src/ContinuousSceneMod.as:96`，ENTER_FRAME 优先级 -200）里计的时间，**不包含**被宿主补丁挂在 `Camera.calc` 里的 `grafon.sceneTick()` → `sceneEnsure` → 预热/同步/剔除 的全部工作。反证：`at=35629` 那次 **43ms 同步补画**落在 `at=35651` 的 117ms 帧里，而该帧 `continuousSceneHandlerMs=4`。

**因此**：任何用“模组 handler 计时”“帧记录器”得出的“CS 只占 X%”都只是**下界**，不能反过来给 CS 脱罪。

### 2.5 可执行方案（严格按“先测量 → 再改”排序）

#### P0（门禁，先做）相位归因探针：给长帧分家

- **目的**：回答“真实游玩的 38 个 >100ms 帧里，CS 管线（ensure/预热 step/同步/剔除）占多少”。
- **做法**（纯诊断，不进 release）：
  1. 宿主侧**诊断构建**：在 `Grafon.sceneTick` 入口/出口、`sceneEnsureUpcoming` 四周、`sceneAdvanceWarm` 的 `while` 内每个 step 前后、`sceneRender` 四周各打时间戳，累计到公开计数器（`scenePipelineMs/ensureMs/advanceMs/syncMs/cullMs/stepHist[25]`）。沿用 `build/generated/envkey-cache-20261102/build_envkey.py` 的**单方法替换配方**（改方法、`classesUnchanged` 审计），**只编不部署**。
  2. 模组侧探针 SWF：沿用 `build/generated/stutter-opt-20261103/` 的探针骨架，每帧记录 `dtMs`、上述 5 个相位、`sceneResident`、`sceneMarks.length`、`sceneWarmBudget`、`System.totalMemory`。
  3. 采集口径：与既有实验一致（马哈顿废墟、LMG、2048×1123、RV/WB/LAD 关、独占登记、独立 AIR ID、静音私有桌面），**3–5 分钟自然游玩**。
- **验收**：每个 >100ms 帧，**已命名相位之和 / dt ≥ 80%**；并输出“长帧总毫秒里 CS 管线占多少”的一个数。
- **判别**：若 CS 管线占 ≥30% → 直接进 P1/P2/P3；若 <10% → 停止在 CS 内找长帧，转 A5（原生渲染/调度）另立课题，**不再改 CS 渲染代码**。
- **成本**：1 次构建 + 1 次 3–5 分钟运行。**这是唯一能把“偶发卡顿”从猜测变成结论的步骤。**

> 零成本先手（不跑游戏也能做）：把 `explore-warm-sync.md` §6.1 的“事件 × 逐帧时间窗 join”补进 `build/generated/stutter-opt-20261103/analyze_cold_causality.py`，把 cold-r3 从“29 次 sync 0/29 配对”升级成“长帧归因覆盖率”。

#### P1 把 `drawKusok` 切成可中断子步（攻 125ms 尾巴）

- **改哪里**：宿主 `Grafon.as:4136-4294`（`drawKusok`）；在 `sceneDrawSteps`（`:2661-3043`）里把“扫格建掩码树”单独拆成一个可多次 `return false` 的增量 step（例如每 24 格一次，`:4186-4235` 的循环），把 `cacheAsBitmap` + 滤镜 + `draw` + 拆树留作收尾 step。
- **为什么是它**：≥8ms 的单步里 94% 是它；125ms 那一步落在一个 182ms 帧里，**单独解释该帧 69%**。
- **预期**：**尾部延迟**下降（最坏单步从 125ms 压到 ~30ms 量级【推断】）；**总工时不变**。
- **风险**：增量 step 需跨帧持有 Sprite/掩码树（现有 step 闭包已有先例 `:2821,:2845`）；`sceneCancelWarm` 必须能释放这些中间对象，否则泄漏；新子步不能跨帧依赖被恢复的 `this.loc` 临时样式（`:3427-3450` 已有保存/恢复框架）。
- **验收**：① 同帧像素等价（沿用 `SceneBackgroundCompositeChecks` 的零差异口径，2,202,688 像素级）；② P0 复测 `stepHist`：`step max` ≤40ms；③ 一个 >100ms 帧集合的 P95 不退化。
- **回退**：宿主回退 = 用 `build/backups/pfe_before_*` 覆盖根 `pfe.swf`；模组回退 = 覆盖 release SWF + 重启。

#### P2 弹痕不再废掉进行中的预热（去掉 431ms 浪费，低风险）

- **改哪里**：宿主 `Grafon.sceneApply:1116` 的 `this.sceneCancelWarm(affected);` → 仅当 `kind != "decal"`（或 `kind=="decal" && args[6] != "normal"`）时才调用。
- **正确性依据**：新弹痕在 `:1119` 已 push 进 `sceneMarks`；进行中的 job 最后一步就是 `sceneRestoreMarks()`（`:3038-3041`），会按 `sceneRegionPassActive` 走直绘把这块内所有 mark（含刚发生那一发）画进正被预热的缓冲（`:1604-1608 → 4663-4667`）。
- **预期**：去掉 7.4% 的预热浪费 + 11 次 4 块位图重建/82s；**不承诺降长帧**（0/29 同块证据）。
- **风险**：中低。`paint`/`gwall`/`drawWater` 保持原语义（仍取消）以免时序依赖被破坏。
- **验收**：① 一次"开火穿越新区块"的像素等价 + 弹痕可见性检查；② 复测 `cancelCount`、`warmMs`、`wastedMs`；③ 若 `warmMs` 不降或出现旧弹痕丢失 → 回退。

#### P3 给 `sceneRestoreMarks` 计时并加空间剪枝（唯一与“探索时长”正相关的未测项）

- **先测**：在诊断构建里给 step 24 单独计时并记 `marksReplayed/ms`（现有 `markScanned` 只数扫描数，不数重放数与毫秒）。
- **若实测 `marks` 重放 ≥5ms/块**：
  - 改 `Grafon.sceneRestoreMarks:1161-1191`：预算与 `sceneApply:1125` 一致的**块坐标索引**（`marksByChunk: Dictionary`，键 `cx+":"+cy`，push 时按 `affected` 覆盖的块登记），把“遍历全表”变成“取本块桶”。
  - 两个方法同源改动，仍按单方法替换配方。
- **若不成立**：记录为负结果，**不做**（避免又一个“减分配式”无效劳动）。
- **风险**：中（`sceneHistory`/换图清理、`sceneMarks` 语义、桶与矩形相交的双重来源要一起迁）。

#### P4 顺手修一个确定的浪费（低风险、不要当性能收益）

- **改哪里**：宿主 `Grafon.sceneApplyCompactDecal:905`
  `new BitmapData(int(local.right), int(local.bottom), true, 0)` → 按**宽高**分配（`area.width/area.height`），并同步 `:906`/`:913` 的 `copyPixels` 目标点。
- **为什么**：现在分配的是“右下角坐标积”，块中心一发也会分配 ≈200×200，角上 400×400（640KB）；实际只需要 40–80px 见方。
- **预期**：单发单块分配降 9–40 倍。**按既有四次“减分配≠减帧时”证据，只算降抖动/降 GC 压力，不算性能收益。**
- **验收**：像素等价 + 分配计数下降（诊断构建），不要求帧时变化。

#### 明确不做（写入停止条件，避免再被重新包装成新方案）

- 压 `sceneWarmBudget` 上限（饿死预绘 → 更多同步补画，31–178ms 比 48ms 贵得多）；
- 地块 `BitmapData` 对象池（只省抖动）；
- 弹痕 pending buffer（已有 0/29 同块证据）；
- 任何形式的“每帧减分配”作为帧时手段（四次配对已关闭）；
- 全景低分辨率/半分辨率每帧合成、每帧切 `stage.quality`、地形降采样缓存、`cacheAsBitmap` 缓存地块（本轮微基准再次显示**更慢**：4.42→7.27ms / 11.91→19.96ms）。

---

## 3. 问题二：与单只天角兽交战卡顿

### 3.1 旧方案四条“根因”全部降级（逐条）

| 旧断言 | 判定 | 复核依据 |
|---|---|---|
| `findBox()` 全图 1200+ 遍历，“交战时高频进入”，单次 **4–10ms**，首要元凶 | **证伪**：真实周期 **660 帧=22s**（tr=2 型 460 帧=15.3s），失败退避 51–150 帧 → **0.05–0.6 次/秒**；单次 = 一次 1200 物体属性遍历（≈0.1–0.3ms）+ 少量 ≤67 步 `isLine` | `alicorn-combat.md:51-89` |
| `GlowFilter` 给**玩家整体容器 `vis`** 挂滤镜、每帧离屏重绘 | **机制错**：被抓玩家走 `levitFilter2` → `vis.osn.filters`，且仅 `f_levit && levit>=1 && fracLevit!=fraction` 时生效；**长期存在的是天角兽自己的 `nomaterFilter`**（150×150 bitmap、blur 15×5、quality 3），只在 `mater=false` 穿墙相位 | `alicorn-combat.md:93-110` |
| `actPort` 20 次“全图 `collisionAll` 脉冲阻塞” | **成本证伪**：每次尝试 ≤12 次瓦片检查、随机取点 O(1)，合计 ≈0.1–0.3ms/次；真问题是**行为**（全图随机落点 → 脱战） | `alicorn-combat.md:121-139` |
| 闪电 `destroy=50` 频繁破坏地形、`destroyTile`/`drawKusok` 全块重绘 | **API 错 + 频率错**：1.02 无 `destroyTile`；`drawKusok` 不在 `hitTile` 链上；`tipdec=11` 约 **90%** 命中为 `decal(null,null)`，在 `sceneApply:1093-1096` 入口早退；默认 hp=1000、每发 50 → 同格 20 发才破 | `alicorn-combat.md:176-189` |
| `rapid=35` → 射速极快 | **证伪**：35 帧冷却 + 蓄力 + AI 门控 → **0.4–0.5 发/秒**（上限 0.75） | `alicorn-combat.md:156-163` |

### 3.2 剩余可疑源（按预期量级）

| 序 | 源 | 预期量级 | 级别 |
|---|---|---|---|
| **B1** | **警报/目标共享把同一房（1920×1000）内的同阵营单位拉进 engaged/awake** | **每额外活跃单位 +1.5–2.0ms/帧**；3–8 个 → +5–16ms/帧，且 2200×1600 内长期活跃 | 【已有实测】`multi-enemy-stutter-20261101.md:12-22` +【确证】`SceneAlicornAlerts.as.inc:31-64`、`NativeSceneActivity.as:49-50,55-57` |
| B2 | 一次性真实地块重绘（10% `fire_soft` 或打穿格） | 3–8ms/次，alilight 下约 1–3 次/分 | 【已有实测】`dense-combat-near-native-20261023.md:139` |
| B3 | 念力滤镜（`nomaterFilter` / 玩家 `levitFilter2`） | 0.3–1.5ms/帧，仅特定相位 | 【推断】 |
| B4 | `actPort` / 瞬移 | 0.1–0.3ms/次（tr=2 型约每 11s 一次） | 【推断】 |
| B5 | 飞行中的 alilight 弹体 | 0.2–0.5ms/帧/弹；同时 ≤1–3 发 | 【已有实测换算】 |
| B6 | `findBox`/`budilo`/`telepat` 循环本身 | 合计 ≪1ms/s | 【推断】 |

> 关键澄清：默认“天角兽接力报警概率 = 0%”**只阻断接报者再转发**，**不阻断首发者在 1920×1000 内的直接通知**（补丁里 `alicornAllow` 对首发者首轮返回 true；`telepat` 只对 `UnitAlicorn` 接收者记账）。所以“把玩家交给附近同阵营单位”这条链在默认配置下仍然生效。

### 3.3 可执行方案

#### B-P0（先决事实，零运行，10 分钟）

1. 核对 `pfe.swf` 仍是 `A9B39CC7…`（本轮已核对：是）；
2. 核对部署宿主回读源里 `sceneApply` 含 `decal(null,null)` 早退（本轮已核对：`host-export/fe/graph/Grafon.as:1093-1096` 存在）；
3. 统计目标存档区域里 **fraction=1 且在这一房范围内的单位数**（用现成的 `NativeSceneActivity.stats()` 与探针）。

#### B-P1 只读计数战斗（1–2 分钟，不编译宿主）

- **做法**：ModLoader 加载**只读探针**（新类放 `package fe.unit` 才能读内部字段，沿用 `src/tests/AlicornAlertProbeMod.as` 的同包读法），每帧记录：
  `dtMs`；`loc.units.length`；`activityStats().awake/asleep/leashed`；`celUnit != null` 的敌对单位列表；每只天角兽的 `mater/teleObj/aiState/aiSpok/t_tele/t_attack`；`visBmp.filters.length`；`gg.vis.osn.filters.length`；`grafon.sceneRedraws/sceneLastDirtyCount`；并发 alilight 弹数；位置跳变。
- **判读**：**只接受同帧/同事件对齐**（工作区已反复证明“平均帧时间差”不可作因果）。
  - `dt` 尖峰与 `awake` 增量/`celUnit` 数同步升高 → **B1 成立**；
  - `dt` 尖峰与 `sceneRedraws` 同步 → **B2**；
  - `dt` 尖峰与 `visBmp.filters.length>0` 或玩家 `osn.filters` 存在同步 → **B3**；
  - 都不对齐 → 转 B-P2。
- **门禁**：≥2700 帧（90s@30Hz）真实交战，两轮顺序互换。

#### B-P2 若 B1 成立：让“仅由目标共享产生的活跃”走预算，而不是立刻紧急唤醒

- **改哪里**（两处，均为模组层，零宿主风险）：
  1. `src/NativeSceneActivity.as:49-50`：把 `combatSignal` 拆成两类——**强信号**（`hp` 下降、`cut>0`、`poison>0`、`stan` 类）与**弱信号**（`celUnit != null` 但本单位既未受伤也未见玩家）。弱信号只延长 `until`，**不**置 `engaged`。
  2. `src/NativeSceneActivity.as:91-96` 的 `urgent` 判据同步改用强信号；弱信号走既有 `wakeBudget`（默认 1/帧，最近优先），并允许按 `distance` 排序。
  3. 可选：把 `disengageTicks`（150 帧）对“弱信号 engaged”缩短到 60–90 帧，并让 leash 半径（2200×1600）对弱信号更小（例如 1400×1000）。
- **预期**：把“一开打就同时唤醒 3–8 个”摊成每帧 1 个，并让它们在脱战后更快休眠。**这是唯一有量级的改动点。**
- **风险**：中。弱/强信号的划分错误会让“真的看见玩家”的单位被延迟 1–3 帧（可接受），但若把“正在向你射击的单位”判成弱信号会导致其短暂站桩——所以 `celUnit != null && 该单位有视线/正在攻击` 必须算强信号。
- **验收**：① `leash-v096` 那套 29 项机制断言全通过（尤其 `engagement-expires-for-far-units`/`leashed-unit-reengages-on-approach`）；② B-P1 复测：同帧 `awake` 增量 ≤1；③ 战斗 2700 帧整帧均值/P95 不退化，且 >100ms 不增加；④ 交战行为录像/截图确认敌人不会“装作没看见”。
- **回退**：模组 SWF 覆盖 + 重启（runtime 开关：`nativeAPI.activityBudget` 已是公开入口，可先做“仅调节”的只读试验）。

#### B-P2' 若 B1 不成立（房里只有这一只天角兽）

- 明确记录为负结果，**不要**去改天角兽函数（`findBox`/`actPort`/滤镜）——它们已被算到 ≪1–2ms/帧；转 B-P1 的 B2/B3 分支或直接归到问题一的 A5。

#### B-P3（可选，仅当 B3 实测 ≥1ms/帧）

- 把 `nomaterFilter`（150×150、blur 15×5、q3）在 `mater=false` 期间换成 `colorTransform` 半透明化（视觉等价性需截图对照）；`teleFilter` 保持不动（它只在 60 帧持握期内、且玩家原本就带 `levitFilter1`）。
- **门禁**：像素/观感对照 + 配对帧时；**若 <1ms 则不做的价值**。

---

## 4. 问题三：镜头移动时背景粗糙 + 动态模糊取舍

### 4.1 先分清两件事（这是本轮最重要的更正）

| 概念 | 事实 | 影响 |
|---|---|---|
| stage 缩放 vs 镜头缩放 | `MainFE.as:20-21` 是 `scaleMode="noScale"`；`0.6583` 是 **`cam.scaleV`**，作用于世界容器 `w.visual.scaleX/Y`（`Camera.as:138`） | “窗口缩放导致重采样”的说法要改成“**scaleV ≠ 1 导致重采样**” |
| 什么时候 scaleV = 1 | 大场景按原版 **1920×1000** 参考尺寸求倍率，且 `>0.98` 直接钳成 1：**2048×1123 → 1.0667 → 1**；**1264×681 → 0.6583**；1280×720 → 0.6667 | 2048×1123 下**没有**最近邻重采样，smoothing 也无事可做 |
| 相机整数截断 | `X/Y/vx/vy` 全是 `int`（`Camera.as:20-26`），容器平移在无震屏时是整数 | **不造成爬行**；最多把相机量化到 1 屏幕像素 |
| 爬行的真因 | `scaleV=0.6583` 时，相机每帧 +1 屏幕像素 → 采样相位跳 `1/0.6583≈1.52` 个源像素（非整数）→ 同一面墙每帧被抽掉的列都不同 | 只在 scaleV≠1 的窗口存在 |
| 原版已有缓动 | 纵向有 1/4 缓动（`Camera.as:219-222`），CS 另加纵向镜头带（`csVCBand ≤160px`，`Camera.band.as:203,294-295`） | “相机硬跟随、需要加阻尼”的说法不准确；缺的只是横向 |

### 4.2 动态模糊：实测否决（本轮直接测到）

| 方案 | 实测成本（2048×1123，两轮） | 结论 |
|---|---|---|
| `applyFilter` 单向 `BlurFilter(2,0,1)` | **15.63 / 19.13 ms** | 最便宜档也要 15ms+ |
| 半径 4 / 8 / 16（单向 q1） | 15.48–19.50 ms | **半径几乎不影响**，“调小半径”不成立 |
| 双向 `BlurFilter(8,8,1/2/3)` | 20.34–22.30 / 30.31–50.65 / 31.20–83.15 ms | quality≥2 更糟 |
| 世界容器挂 `BlurFilter(6,0,1)` 单次绘制 | **23.03–58.65 ms**（无滤镜 4.42–11.91 ms） | 挂容器比 applyFilter 更贵 |
| 累积拖影（copy + alpha0.6 draw） | **2.16–3.18 ms** | 混合便宜，但每帧仍需“抓画面” |
| 抓画面（游戏内实测/外推） | 小窗 16–28ms；2048 外推 **43–75ms** | 才是真成本 |
| 已就绪全屏缓冲呈现 | 0.65–0.87 ms | 呈现不贵，**产出**贵 |

**判定：不做动态模糊。** 30fps 预算 33.3ms、当前整帧已 33–45ms：加一次全屏模糊 → 48–64ms（≈16–21fps）；挂容器 → 56–104ms（多数组合 <15fps）。且 `BlurFilter` 是各向同性模糊，不是沿运动方向的拖影；累积拖影虽只 2–3ms，但会同时拖脏 UI、准星、角色与弹道。**若用户仍想要观感，只能作为默认关闭的独立开关，并明确“它换不来帧率”。**

### 4.3 决策树（按用户实际窗口走，不要一上来就改渲染）

```
第 1 步：记录用户实际窗口的 cam.scaleV（一行日志即可）
├─ scaleV == 1（2048×1123 类）
│   → 粗糙只能来自 (a) 30fps 步进 + (d) 帧时抖动；
│     smoothing / 动态模糊在此窗口**物理上无收益或不可承受** → 走问题一的 P0 帧时路线
└─ scaleV ≈ 0.658（1280×720 类）
    → 先做 §4.4 ①（地形层双线性）的运行时 A/B（模组层开关，可秒回退）
      ├─ 观感明显变稳（用户确认）→ 接受 +3.9–7.2ms，配 ② 亚像素化一起评估
      └─ 观感无改善 → 不要动渲染，回到问题一 P0
    另：§4.4 ④（World.zoom100 → scaleV=1）是**唯一零渲染成本**消灭重采样的做法，
        代价是可视世界面积降到 44%，属于**用户口味取舍**，需用户拍板。
```

### 4.4 四个候选改法（含实施与门禁）

#### ① 只给地形层开双线性（唯一“真修复”）

- **零宿主重建的试验路径（推荐先做这个）**：模组层遍历 `w.grafon.sceneSurfaces()`（`Grafon.as:394-402` 已公开），对每个 `entry.bitmaps[0..3]` 设 `smoothing=true`、`pixelSnapping=PixelSnapping.NEVER`；只在 `entry.revision`/resident 变化时写（约 40 块×4 = 160 次属性写，**不是每帧**）。加 `nativeAPI.terrainSmoothingEnabled/Set` 与设置项，默认关闭，供 A/B。
- **宿主路径（确认有效后再做）**：`Grafon.sceneRender:761`、`scenePreloadAll:2569`、区域绘制 `:1974/:2102`、预热应用 `:3531` 统一改属性（一个 helper）。
- **成本预期（离线代理）**：`scaleV≈0.6583` 时 4 层双线性 **+3.9–7.2ms/帧**（33.3ms 预算的 12–22%）；逐块路径 +1.8–12.9ms/层；**`scaleV=1` 时零成本、零视觉变化**（天然对照组）。
- **门禁变更（容易踩的坑）**：本仓所有呈现门禁都是“同帧逐像素 RGBA 相等”。开平滑是**故意改变像素**，必须另立口径：允许块边 2px 内差异有界、无 1px 线缝、无色偏；否则任何实现都会被判失败。
- **已知风险**：A2 快速暖块**把 gutter 像素按中心组近似**；smoothing=false + scrollRect 会裁掉 gutter，所以现在看不见；开平滑后块边可能采到近似像素 → 每 320px 一条轻微亮/暗竖线【推断，需截图验证】。
- **失败判据**：实测增量 >8ms、P95 +>10%、>100ms 增多、出现可见块边线/文字变糊 → 停。
- **回退**：运行时开关置 false（下一帧写回 `smoothing=false`）；宿主侧用备份覆盖。

#### ② 相机亚像素化（**必须与 ① 配对**，否则只有闪烁更重）

- **改哪里**：宿主 `Camera.calc` 写容器处（`Camera.band.as:366-367`）——保留 `X/Y/vx/vy` 的 int 语义（玩法/瞄准依赖），但写容器时把取整损失补回：`subX = -(param1.X*scaleV - X)`，`visual.x = vx + quakeX + subX`。
- **零宿主重建路径**：`SceneAimController.apply()`（`src/SceneAimController.as:186-187`）已经在同一位点写 `visual.x`，可在那里加小数项。
- **关键耦合（必须先处理）**：`SceneEventBitmapFill.unsupported()` 在“非震屏 + 小数矩阵”时返回 `fractional-or-non-unit-geometry` 并回退原生（`src/SceneEventBitmapFill.as:114-120`）→ 会**白白丢掉** `scaleV=1` 时的地形合并收益。要么同时放宽该判据（并用 `beginBitmapFill` 的小数 tx 做像素测试），要么只在 smoothing 场景启用。
- **门禁**：帧时 ±0；鼠标命中/准星偏移 ≤1px；地图边缘 `ramL/R/T/B` 无半透明缝；块边像素差只在移动时出现。
- **回退**：开关。

#### ③ 横向轻度阻尼（只改手感，不解决采样）

- **改哪里**：`Camera.calc` 的 X 目标赋值（`Camera.as:218`）加一阶低通；纵向已有 1/4 缓动、CS 又有纵向带，**只补横向**。
- **风险**：输入延迟 >2–3 帧、跑动/闪避手感、瞄准跟随偏移——任一即停；且 damping 会在 smoothing 关闭时**延长慢速爬行的可见时间**，所以必须与 ① 一起评估。

#### ④ `World.zoom100`：零渲染改动消灭重采样（需用户拍板）

- **做法**：不改代码，开选项页 `zoom100`（`World.as:602-613`、`PipPageOpt.as:594-615`）→ `isZoom=0` → `scaleV=1`。
- **收益**：1280×720 下 1:1 采样，**重采样与爬行彻底消失，零帧时成本**。
- **代价**：可视世界从 1920×1034 降到 1264×681（每轴 2/3、面积 44%），即视野更近；可用 0.9.8 的 aim-look 部分补偿。
- **这是唯一能确定消除重采样且不加成本的做法**，属于体验取舍，需要用户决定。

### 4.5 另需记录的一个新风险（0.9.8 引入）

`SceneAimController` 在按住瞄准时把视口整体偏移最多 **700px**（X）/380px（Y），并把 pan 写回 `cam.vx/vy`；宿主 `sceneEnsure`/`sceneCullSurfaces` 都读 `cam.vx`，因此**预绘与剔除会跟随 pan**（正确），但：
- 快速横扫时视口以 50px/帧移动，`sceneEnsureUpcoming` 的按方向预热环（±3 块=960px）可能跟不上 → 视口 miss → **同步补画 31–178ms**；
- 该功能 2026-11-04 04:51 才部署，**尚无性能验收**。
- **行动**：把“按住瞄准横向扫射”纳入问题一 P0 的采集脚本（原本只测步行/开火），并在 B-P1 的战斗脚本里也带一次 aim pan；若发现 pan 期间 `sceneMisses`/`syncMs` 上升，优先把预热的前瞻方向改为“pan 方向”（复用 `travelX/travelY` 已有逻辑，把 aim 的 `offX` 加进去）。

---

## 5. 实施顺序（一张表看完）

| 步 | 内容 | 改动面 | 前置 | 验收 | 风险 |
|---|---|---|---|---|---|
| **0** | 相位归因探针（P0）+ 只读天角兽计数探针（B-P1） | 仅诊断构建/探针 SWF | 无 | 长帧相位和 ≥80%；dt 与 5 类计数对齐 | 无（不部署） |
| **1** | P4 分配修正 + P2 弹痕不废预热 | 宿主 2 个方法 | 0 完成（或至少 P4 可先做） | 像素等价 + 取消数下降 | 低 |
| **2** | P1 拆 `drawKusok` | 宿主 2 个方法 | 1 完成 + 0 的 stepHist 基线 | 单步 max ≤40ms，P95 不退化 | 中 |
| **3** | B-P2 弱/强信号分离（若 B1 成立） | 模组 `NativeSceneActivity` | 0 的 B-P1 证据 | 同帧 awake 增量 ≤1；2700 帧不退化 | 中 |
| **4** | ① 地形双线性运行时开关（仅 scaleV≠1 生效） | 模组层（+可选宿主 5 处） | 用户窗口 scaleV 已记录 | +3.9–7.2ms 内且观感改善 | 中低 |
| **5** | ② 亚像素化（与 ① 配对）/ ③ 横向阻尼 | 宿主 `Camera.calc` 或模组钩子 | 4 完成 | 帧时 ±0，准星 ≤1px | 中 |
| **6** | P3 弹痕空间索引（**仅当实测 ≥5ms/块**） | 宿主 2 个方法 | 0 的 markMs | marks 重放耗时下降 | 中 |

**总原则**：每一步**独立候选、独立门禁、独立回滚**；不满足门禁就停在当步并记录负结果，不把它合并进下一步的理由里。**任何“平均帧时变好但 P95/长帧没变好”的改动都不算通过。**

---

## 6. 与旧方案（`scene-combat-camera-optimization-plan.md`）的差异清单

| # | 旧方案位置 | 原说法 | 本轮结论 |
|---|---|---|---|
| 1 | §1.1 / §2.4 | 48ms 预算越界是探索长帧根因；建议压到 2–12ms | 预算实测 20–22；压预算会**增加**更贵的同步补画。**不采纳** |
| 2 | §1.1 | “复杂滤镜单步 20–35ms” | `applyFilter` 从未 ≥8ms；贵的是 `drawKusok`（125ms） |
| 3 | §1.2 | 同步补画 25–45ms | 实测 **31–178ms（均值 68）**，比旧估计更贵，但行军中出现率极低（28/29 在入口首屏） |
| 4 | §1.3 | 冷块分配触发 GC 是长帧主因，建议对象池 | 长帧仅 31% 邻近 GC；池化只省抖动（四次“减分配≠减帧时”） |
| 5 | §1.4 | 取消风暴 → 同步补画 → >100ms | 取消确实浪费 431ms/81.7s，但 **0/29 同块配对**；只作为低风险清理 |
| 6 | §2.1 | `findBox` 4–10ms、每帧高频、首要元凶 | 0.05–0.6 次/秒、≤0.5ms/次。**证伪** |
| 7 | §2.2 | 玩家 `vis` 挂 GlowFilter 导致每帧重绘 | 玩家走 `levitFilter2 → vis.osn.filters`，且只在持握 60 帧内；长期存在的是天角兽自身 150×150 的 `nomaterFilter` |
| 8 | §2.3 | `actPort` 20 次全图 `collisionAll` 脉冲 | 每次 ≤12 次瓦片检查；≈0.1–0.3ms/次 |
| 9 | §2.4 | 闪电 `destroy=50` 频繁破坏地形 → 全块重绘 | 1.02 无 `destroyTile`；`drawKusok` 不在该链；约 90% 命中在 `sceneApply` 早退 |
| 10 | §2.4 | `rapid=35` 射速极快 | 0.4–0.5 发/秒 |
| 11 | §3.2.1 | BlurFilter 单帧 35–85ms → 8–12fps | 方向对、数值无出处；实测最便宜 15.6–19.5ms、挂容器 23–59ms、q3 31–83ms |
| 12 | §3.2.2 | 全屏 `BitmapData.draw` 10–18ms | 实测整屏 `copyPixels/draw` 0.5–0.8ms（2048×1123）；贵的是**半分辨率整景合成** 16–28ms（小窗实测） |
| 13 | §3.3.1 | 开 `smoothing` 全屏 <0.4ms | **否证**：0.6583 下 +3.9–7.2ms；1:1 下零成本 |
| 14 | §3.3.2 | 相机 int 截断导致亚像素爬行；建议改 Number | 爬行来自 scaleV 非整数 × 最近邻；int 只量化到 1px。改字段类型会连带动 `celX/celY` 语义，**收益/风险不划算**，改用“写容器时补小数” |
| 15 | §3.3.3 | 相机无阻尼、需加 Lerp | 原版已有纵向 1/4 缓动 + CS 纵向带；只缺横向 |
| 16 | §5.1 | “单只天角兽交战帧率稳定 ≥27FPS”“长帧减少 60%” | **预期不是证据**；本轮把可用量级算到 ≤1–2ms/帧（+一次性 3–8ms/次），无法支撑该承诺 |
| 17 | §5.1 | 门禁“整帧均值 +≥15%” | 与本仓反复验证的判据不符：只用均值会被长帧/负载掩盖，**必须同时看 P95 与 >100ms 频率** |

---

## 7. 复跑与证据入口

- **离线微基准**：`mods/ContinuousScene/build/generated/filter-cost-20261104/`
  - 编译：按 `blur-benchmark-lead.md` 的 mxmlc 配方（`flexsdk/lib/mxmlc.jar` + `airsdk/.../airglobal.swc`，`-swf-version=32`，debug 编译以便 `trace`）
  - 运行：`adl64.exe app-debug.xml`（cwd 为该目录）；结果从 stdout 的 `RESULT` 行读取
- **cold-r3 原始数据**：`knowledge/experiments/evidence/stutter-opt-explore-cold-r3-20261104/storage/result.json`（samples 1300 帧、events 196 条）；复算脚本见 `explore-warm-sync.md` §6
- **既有配对分析**：`python build/generated/stutter-opt-20261103/gcombo_analysis.py`、`python build/generated/camera-gc-source-v14-20261102/gcattrib_analysis.py gcattrib-current-r2-20261104`
- **宿主回读源（唯一权威）**：`build/generated/envkey-cache-20261102/host-export/scripts/fe/graph/Grafon.as`（对应 A9B39CC7）
- **单方法补丁配方模板**：`build/generated/envkey-cache-20261102/build_envkey.py`（导出源 → 改一个方法 → ffdec 替换 → `changedMethods`/`classesUnchanged` 审计）

---

## 8. 未确认项（写清边界，避免被当成结论）

1. `cold-r3` 是脚本路线 + 并行负载（p50 59ms、p95 92ms），**绝对帧值不能外推真实游玩**；本方案只引用其相对量与事件计数。
2. `2048×1123 → scaleV=1` 是公式代入 + 本仓大窗实测（1904×1041 / 2032×1084 均为 scale1）的一致结论，**尚未在该尺寸直接回读 `scaleV`**（P0 的一行日志即可补上）。
3. 弹痕重放（A3）**至今没有任何计时**；`markScanned=30,947` 只是“扫过多少条”。
4. 天角兽侧所有“ms”都是代码推演 + 既有实测换算，**本轮没有运行时数据**；B1 是否成立取决于房里实际有多少同阵营单位。
5. 相机亚像素化对 `SceneEventBitmapFill` 资格的影响、以及平滑是否采到 A2 近似 gutter，都还是【推断】，必须靠像素/截图验收。
6. 本轮**未运行游戏、未编译部署、未改宿主或 release**；唯一新增产物是离线微基准 SWF（在 `build/generated/`，不参与加载）。
