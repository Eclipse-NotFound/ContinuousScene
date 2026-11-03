# 探索卡顿调查：预热 / 同步补画 / 取消链（CS 0.9.7，宿主 A9B39CC7）

调查对象：已部署宿主的可编译还原源 `mods/ContinuousScene/build/generated/envkey-cache-20261102/host-export/scripts/fe/graph/Grafon.as`（4864 行，下文简称 `Grafon.as`）。
原版机制参考：`game-reference/decompiled/1.02/src102/scripts/`（只读）。
实测复算：直接读 `knowledge/experiments/evidence/stutter-opt-explore-cold-r3-20261104/storage/result.json`（1300 帧样本 + 196 条诊断事件），不运行游戏、不构建。
标注约定：**【确证·Grafon.as:行号】**＝当前源码可逐字核对；**【已有实测·路径】**＝他人已落盘证据；**【实测复算·cold-r3 result.json】**＝本轮从该文件重新统计（结论基于原始数据，但统计口径由我给出，可复核）；**【推测】**＝无实测支撑的推断。

---

## 0. 结论速览

| 问题 | 结论 | 依据 |
|---|---|---|
| 预算是硬上限吗 | 不是。只在「每个 step 之间」比较 `getTimer()-start < sceneWarmBudget`，单步可任意越界；实测单步最大 **125ms** | 【确证·Grafon.as:3358】+【实测复算·cold-r3】 |
| 哪一步最贵 | `drawKusok`（step 7/8，每个材质一次调用）：≥8ms 的 156 次单步里占 144 次 / 1804ms（94%），单步峰值 125ms | 【实测复算·cold-r3 result.json events】 |
| 同步补画一次多大 | 1 块 = 4 层 ×400×400 px = 640,000 px = **2.56MB**；整段 `drawLoc` 不可中断；实测 31–178ms/次（均值 68ms） | 【确证·Grafon.as:725,760,3683】+【已有实测·stutter-optimization-implementation-20261103.md:73】 |
| 每发命中都触发 cancel 吗 | 不是。`decal(null,null)` 在 sceneApply 开头早退；且只有落在「正在预热的块 ±80px」内才 cancel；82 秒 650 开火帧共产出 836 次 apply、仅 11 次 cancel | 【确证·Grafon.as:1093,1116,3055】+【实测复算·cold-r3】 |
| 取消的代价 | 每次丢 `job.work`（实测 19–71ms）+ 4 个输出位图（2.56MB）重新分配 + 下一次从第一步重来；82 秒累计废弃 **431ms**（≈预热总时间 7.4%） | 【确证·Grafon.as:3059-3068】+【实测复算·cold-r3】 |
| 冷块分配 | 2.56MB/块；入口一次 24–28 块（61–72MB）；无逐出，实测驻留 155 块 ≈ **397MB** | 【确证·Grafon.as:760,2568,3260】+【实测复算·cold-r3 finalCounters】 |
| 对象池值得做吗 | 为「帧时」不值得（已有三次减分配实验无收益）；为「内存/逐出」才值得，但那是另一件事 | 【已有实测·implementation-20261103.md:73】+ §4.3 |
| 长帧是不是 CS 驱动的 | cold-r3 的 47 个 ≥100ms 帧共 5975ms，落在帧内的 CS 事件合计仅 **385ms（6.4%）**；**32/47** 帧内一个 ≥8ms 的 CS 事件都没有（仅 15 帧命中事件） | 【实测复算·cold-r3 samples×events 时间窗配对】 |

**一句话**：代码链能解释「为什么单帧会突然变长」（不可中断单步 + 同步整块补画），但**现有证据不支持**「预热/取消/同步是真实游玩长帧的主因」；真实游玩的长帧画像仍缺一次带相位归因的测量（§6）。

---

## 1. `sceneAdvanceWarm` 的预算语义

### 1.1 `sceneWarmBudget` 怎么算

【确证·Grafon.as:2398-2399】

```
demand  = (|travelX| * 视口行数 + |travelY| * 视口列数) / 320
budget  = max(2, min(48, ceil(sceneWarmMean * demand * 1.35 + 1)))
```

- `travelX/travelY` = 本帧视口左上角相对上帧的位移（px）；位移 >80px 或 <0.5px 时改用 `loc.gg.dx/dy`（2390-2397）。所以**站桩≈2ms，正常步行≈5–11ms，快速平移才逼近 48ms**。
- `sceneWarmMean` 是「**整块**总工时」的 EWMA（初值 48，`mean = mean*0.8 + min(200, job.work)*0.2`，3556 行；286 行），**不是**每帧耗时。也就是说预算的物理含义是「按本帧推进速度，允许花多少毫秒去追一整块的缺口」。
- 实测终值：`sceneWarmBudget=22`（入图时 2，行军中 20–22）【实测复算·cold-r3 finalCounters/phaseMarks】。
- 预算**只**约束循环何时停：`while(force || getTimer() - start < sceneWarmBudget)`（3358 行）在每个 step 之前比较一次，**执行中的 step 无法中断**。因此「预算 8ms」与「本帧实际耗时 125ms」并不矛盾。

### 1.2 force 路径

【确证·Grafon.as:3337-3340, 3358】`force=true` 时 `while(force || …)` 恒真，循环一直跑到 `complete` 或异常。即：

- force **不是**「只把当前 step 做完」，而是**把该块剩余的所有 group/step/合成一次性跑完**；
- 代价上界 = 一整块栅格化（实测均值 59ms/块，最坏 296ms 的 `sceneMaxDrawMs`）；
- 实测 `sceneWarmForced=1`、`forcedMs=7`：force 路径在冷态探索里几乎没被用到（§2.3 解释）。

### 1.3 单步粒度：`sceneDrawSteps` 的 25 个 step

【确证·Grafon.as:2661-3043】每个 group（一种区域样式）新建一份 steps 数组，0 基下标：

| idx | 行号 | 内容 | 成本量级 |
|---:|---|---|---|
| 0 | 2683 | 绑定 loc/res/transpFon | 极小 |
| 1 | 2695 | `sceneConfigureBorders`（非重绘时） | 小 |
| 2 | 2702 | lock 4 缓冲 + 6×`fillRect`（400×400） | ~1–3ms【推测】 |
| 3 | 2730 | 新建 4 个 Sprite、清材质 used | 小 |
| 4 | 2747 | 扫 tile：`(400/40+4)²≈196` 格 `getTile`+`tileKontur`+按需 `new tileFront()` | 中，波动大 |
| 5 | 2812 | `vodaBmp.draw(voda)` + `frontBmp.draw(front)`（≤196 个 tile 子节点） | 中 |
| 6 | 2817 | `drawBackWall`：整张地图尺寸的 `beginBitmapFill` 矩形再 `draw` 进 400×400 | 小（实测 ≥8ms 仅 2 次） |
| **7** | 2821 | **`drawKusok(front 材质)`：每次调用画 1 个材质**（增量） | **最贵之一，实测 ≥8ms 83 次/1038ms，峰值 30ms** |
| **8** | 2845 | **`drawKusok(back 材质)`：每次 1 个材质**（增量） | **最贵，实测 ≥8ms 61 次/766ms，峰值 125ms** |
| 9 | 2869 | `satsBmp.copyChannel(backBmp)`（640KB 通道拷贝） | 小（本轮从未 ≥8ms） |
| 10–15 | 2875-2944 | 按 `bo.sloy=-2..3` 分 6 层画 backdrop；每层都重新 `sceneBackdropObjects()`（桶命中时 O(1)，见 536-548） | 小–中 |
| 16 | 2945 | cTransform + `shadBmp.applyFilter(frontBmp, DropShadowFilter)` | **本轮从未 ≥8ms**（见下方更正） |
| 17 | 2955 | back/back2 colorTransform | 小 |
| 18 | 2972 | `backBmp2.draw(back)` | 中 |
| 19 | 2976 | 硬光合成(colorBmp)+阴影合成(shadBmp)，含 2 次 `copyChannel` | 中 |
| 20 | 2989 | gas 叠加 | 小（却是 1 次 cancel 的落点） |
| 21 | 3003 | `drawKusok(front, …, true)` 第三遍 | 实测 ≥8ms 4 次/38ms |
| 22 | 3027 | `backBmp2.draw(back2)` | 中 |
| 23 | 3031 | unlock 4 缓冲 | 小 |
| **24** | 3038 | **`sceneRestoreMarks()`：重放全部落在本块的弹痕** | 随弹痕数增长，**未单独计时**（§6 缺口） |

> ⚠️ 更正旧方案的一处断言：`design/scene-combat-camera-optimization-plan.md:52` 与 `stutter-optimization-plan-20261103.md:59` 把「复杂滤镜处理」列为 20–35ms 单步。cold-r3 的 196 条事件里 **step 16（applyFilter）一次都没有 ≥8ms**；真正越界的是 step 7/8（`drawKusok`）。旧文里的 20~35ms 是未实测断言，不能作为补丁依据。

### 1.4 最贵的一步：一次 `drawKusok` 为什么会到 125ms

【确证·Grafon.as:4136-4294】对一个材质做：

1. 建 6 个 Sprite（fill/mask × 纹理、边框、地板三套）；
2. 扫本块覆盖的 ≈196 格，把每个匹配格克隆一个 `sceneMask()` 子节点、`setMCT` 写 4 个 `gotoAndStop`，最多 3 套掩码 → 最多 ≈588 个子节点（4186-4235）；
3. `sceneMaterialFill` 用掩码实际包围盒重新 `beginBitmapFill+drawRect`（2308-2330）；
4. `cacheAsBitmap=true` + `_loc7_.mask=_loc8_`（4255-4258）→ 每套材质层都要生成两张缓存位图并做遮罩合成；
5. 若材质带 `param1.F`（材质滤镜；原版 `Material.as:21` 就给材质配了 DropShadow+Bevel），再对整棵 `_loc6_` 套滤镜（4259-4262）；
6. 最后一次性 `frontBmp/backBmp/backBmp2.draw(_loc6_, …)`（4263-4274），随后拆树（4275-4294）。

其中 2、4、5 的规模都由「本块内该材质的格数」和滤镜参数决定，与像素面积 400×400 无关——这解释了为什么同一段代码在有的块是 1ms、在有的块是 125ms。【推测：具体命中的材质与格数未记录，见 §6】

---

## 2. 视口 miss → `sceneAdvanceWarm(true)` → `sceneRender(x,y)`

### 2.1 完整条件链

调用入口：【确证·Grafon.as:801-818】`sceneTick()` → `sceneEnsure(视口)` → `sceneEnsureUpcoming()`（`scenePreload=false` 是生产默认，见 `src/ContinuousSceneMod.as:79`）。视口矩形来自 `(-cam.vx-quakeX)/scale, (-cam.vy-quakeY)/scale, cam.screenX/scale, cam.screenY/scale`。

`sceneEnsureUpcoming` 的缺块分支（【确证·Grafon.as:2414-2425】）：

```
for x in minX..maxX, y in minY..maxY:
    if !sceneChunks[x:y]:
        ++sceneMisses
        if sceneWarmJob != null && sceneWarmJob.cx==x && sceneWarmJob.cy==y:
            sceneAdvanceWarm(true)          // 把该块剩余全部做完
        if !sceneChunks[x:y]:
            sceneRender(x,y)                // 整块同步栅格化
```

三个入口条件缺一不可：**①该块不在 `sceneChunks`；②（可选的便宜路径）正在预热的恰好是这一块；③force 之后仍未落地**才走 `sceneRender`。

之后的预热发起（2435-2496）只允许**一个** job 存在：`if(sceneWarmJob){sceneAdvanceWarm();return;}`；否则按评分挑块（正前方块 `score -= 100000`，2467-2470），`sceneAsyncWarm=true` 时 `sceneBeginWarm+sceneAdvanceWarm`（2485-2489）。

首次进图的另一条捷径 `sceneFirstWindow`（2499）**只在区域数据正好铺满全图时生效**（`area != limX*limY` 直接 return，2531-2534）；不满足就退化成逐块 `sceneRender`。

### 2.2 单次同步绘制量（一块 320+gutter）

【确证·Grafon.as:204-206,697,2546】`sceneSide=320`、`sceneGutter=40`（生产不切 640）→ 缓冲边长 **400×400 = 160,000 px**；32 位下 **640,000 B = 0.61MiB / 层**。

| 项目 | 量 |
|---|---|
| 一块 = 4 层（front/back/back2/voda） | 640,000 px，**2.56MB** |
| 同步路径：`sceneRender` 对 4 个共享缓冲各 `clone()` 一份（760 行） | 4 次整块拷贝 = 2.56MB |
| 若该块跨多种区域样式：`sceneDrawRegionChunk` 每组再整块过一遍（1766-1811） | 每组 +4 层 draw + 4 次 `copyPixels` 进/出 composite（1784/1800/1809） |
| 预热池（一次性）| 7 块临时缓冲 4.48MB（3248-3257）+ 每 job 4 块输出 2.56MB（3260-3264） |
| 组完成时：每个 clip 4 次 `copyPixels`（3382-3392） | 4 × clip 面积 |
| 收尾：step 24 重放全部相交弹痕 | 与弹痕数成正比，未计时 |

**关键差别**：同步路径 `sceneRender → sceneDrawRegionChunk → drawLoc()`（746、1700、3683）是**一整个不可中断调用**，内部没有分步；预热路径才有 25 步分片。所以「同步补画」是比「预热单步」更大的一整块风险。

### 2.3 实测画像（cold-r3，qualified 路线 81.7s）

【实测复算·cold-r3 result.json chunkDiagnostics.events】【已有实测·stutter-optimization-implementation-20261103.md:73-74】

- 29 次 sync，合计 1985ms（均值 68ms，区间 31–178ms）；
- 其中 **28 次集中在 at=30515…32394（1.88s）**，即入口首屏逐块补画（真实游玩被载入/淡出遮蔽）；`sceneMisses=30`、`sceneResident` 从 59 起；
- **行进中只有 1 次**：`at=35629, cx=23, cy=10, 43ms`；
- `forcedMs=7`、`sceneWarmForced=1`：走 force 分支的几乎为零——说明预热挑块（正前方优先）基本躲开了「视口撞上正在预热的同一块」；
- 预热总量：`warmMs=5814`（占采样帧总时长 ≈7.1%）、`warmSlices=595`、`sceneWarmCount=98` → **平均 59ms/块、约 33 次 step 调用/块**。

> 结论：**「同步补画」在结构上确实是 >100ms 帧的最佳候选**（一次 31–296ms 不可中断），但在本路线里它是**入口瞬时事件**，不是行军中的常态；行军长帧得另找原因。

---

## 3. `sceneApply("decal") → sceneCancelWarm(affected)` 的真实条件

### 3.1 affected 是什么矩形

【确证·Grafon.as:1085-1103,926-997】
`affected = sceneDecalBounds(args, stamp)` = 子弹洞/裂纹两张 art 的并集包围盒 ∪ 中心 alpha 盒，再 `inflate(4 + |scale|*2)`（985-986）。典型 40–80px 见方；材质缩放越大越大；异常时退化为整图（995 行）。
→ 它**不是**整块，而是一个小块；用它去和 `entry` 的 400×400 做相交判断（1127）。

### 3.2 cancel 的实际条件

【确证·Grafon.as:1116, 3046-3068】

1. `sceneApply` **无条件**先调用 `sceneCancelWarm(affected)`（decal/paint/gwall/drawWater 都算）；
2. `sceneCancelWarm` 里：`support = job.bounds.clone(); support.inflate(80,80)`（400→**560×560**），
   `if(affected != null && !affected.intersects(support)) return;`
   → 只有落在「正在预热的块向外扩 80px」内的脏区才会真的取消。

取消丢掉的东西（3059-3068）：

- `job.steps = null`（已建好的 25 步闭包全丢）；
- 7 块池缓冲 `unlock`（保留，下次复用）；
- **4 块输出 BitmapData `dispose()`** → 2.56MB 释放，重启时再分配 4 块；
- 已累计的 `job.work` 全部作废（403 行 `sceneCancelWarm` 后由 `sceneBeginWarm` 重建 groups：重新 `sceneRegionSlices` 分组 + 4 块新 BitmapData）。

**重做成本** = 整块从头再来（均值 59ms 级），且此前消耗的每帧预算全部白费。实测 11 次取消、废弃 work 19/19/11/11/22/22/34/42/45/50/51/64/71ms 共 **431ms**（占预热总时长 7.4%），取消时刻分布在 step 7/8/9/20（即预热进行到一半时被子弹打断）【实测复算·cold-r3】。

### 3.3 每发子弹命中是否都触发

**不是。** 完整链：【确证·原版 `Bullet.as:476-493` → `Location.hitTile:2501` → `dyrka:4455` / `tileDie:4368` → `decal:4661-4666` → `sceneApply`】

逐层早退条件：

| 层 | 早退条件 | 行号 |
|---|---|---|
| `hitTile` | `tipDecal==100 && 伤害<=50 && (thre>0 || indestruct)` | `Location.as:2503-2506` |
| `hitTile` | 不可破坏墙（`hp>500 && phis==1`）→ 只调 `dyrka(param5=true)` 后 return | `Location.as:2511-2518` |
| `dyrka` | `param3==0 || param4==0` | `Grafon.as:4463-4466` |
| `decal` | 非大场景 / 正在栅格化 → 走旧直绘，不进 sceneApply | `Grafon.as:4663-4667` |
| **`sceneApply`** | **`args[0]==null && args[1]==null` → 直接 return（无 cancel、无 mark、无扫描）** | **`Grafon.as:1093-1096`** |

双 null 的真实来源举例：`param4==7`（pole 材质，只发粒子不给 art，4579-4582）、`mat=1 + tip 9` 且随机判定失败（4475-4480）、tip 4–6 且 `param5=true` 等。**所以「每发都进 sceneApply」成立，但「每发都有实际绘制」不成立**——早退路径只花一次函数调用+一个数组。

### 3.4 进入正文的每发成本

【确证·Grafon.as:1125-1146,878-924,1011-1043】

1. 线性扫**全部驻留块**（`for each(entry in this.sceneChunks)`）——实测 `applyScanned/applyCalls = 98,628/836 ≈ 118 块/发`；相交判断后才处理（实测每发实际命中 1–2 块）；
2. `sceneApplyCompactDecal`：`area` 若任一边 >320 退回整块 region 重绘；否则 **`new BitmapData(local.right, local.bottom, …)`**（905 行）——注意分配的是**绝对右下角坐标**而不是宽高，所以块中心的一发也要分配 ≈200×200（160KB），角上最多 400×400（**640KB**），随后 2 次 `copyPixels` 回写，再 `dispose`；
3. `sceneDecalPaint`：再分配一张 alpha 临时位图 + `copyChannel` + `draw(art)` + 回写（1025-1033）；
4. 记录 `sceneMarks.push([kind,args,stamp,affected])`（1119 行），**永不裁剪**。

---

## 4. 冷块分配量 vs「对象池」

### 4.1 每块分配多少、一次进几块

【确证·Grafon.as:760, 2568, 3260-3264, 3539-3551】

- 预热路径：每块 4 个输出 `BitmapData(400,400,true)` = **2.56MB**（完成后就是 `entry.nativeBuffers`，长期驻留）；
- 同步路径：每块 4 个 `clone()` = **2.56MB**，外加 7 个共享 scratch（4.48MB，一次性）；
- 入口首屏：视口 1920×1080 → 6 列 × 4 行 = **24 块**（冷态实测 28 次 sync）≈ **61–72MB 一次性**；
- 预热前瞻带：列 `maxX+3`、行 `minY-3…maxY+3`（2454-2457）→ 约 9 列 × 10 行 = **最多 ~90 块 ≈ 230MB** 的候选带。

### 4.2 没有逐出：resident 单调增长

【确证·Grafon.as:510-534, 485-508】`sceneDrop` 只在 `sceneClear`（换地图/房间）和 `sceneWarmVerify` 分支被调用；运行期**没有任何逐出**。
冷态实测：`sceneResident=155`、`sceneEvictions=0`、`sceneWarmCount=98`、`sceneMisses=30` → **155×2.56MB ≈ 397MB** 的 BitmapData【实测复算·cold-r3 finalCounters】。同轮整进程 `memoryBytes` 采样 285–418MB，量级自洽【推测：`memoryBytes` 含 AIR 其他开销，未做拆分】。

推论（【推测】但由代码强约束）：一次大地图长时间的游玩，驻留块数会随「走过的面积」单调上升（地图 30×16=480 块上限 ≈1.2GB），且 `sceneApply` 每发子弹都要扫一遍全部驻留块。

### 4.3 「对象池」值不值得做

判断题，分三种池：

| 池化对象 | 能省什么 | 判断 |
|---|---|---|
| 块输出位图（2.56MB/块） | 只有内存峰值/分配抖动；块本来就要长期驻留，池化省不了分配 | **不值得为帧时做**；要省就做「逐出/上限」，那是另一件事 |
| cancel 丢弃的 4 块输出 | 82 秒 11 次 × 2.56MB 的 alloc/free | 收益极小；**先别做池，先别 cancel**（§5-P2） |
| 每发 decal 的临时位图（≤640KB） | 每发 1–2 次 alloc/free | 已有否定证据：`stutter-optimization-implementation-20261103.md:70-72` 三次「减分配」实验均未换到帧时收益；**不要以帧时为由做** |

结论：把「对象池」当性能补丁是**方向错**；真正有量级的是「把单步切细」与「别把整块补画塞进一帧」。

---

## 5. 可行补丁点（按性价比排序）

### P1（首选）把 `drawKusok` 切成可中断子步

- **改哪里**：`Grafon.as:4136-4294`（step 7/8/21 的每材质调用）；在 `sceneDrawSteps` 里把「扫格建掩码树」单独拆成一个可多次返回 false 的增量 step（例如每 24 格一次），把「fill/mask/滤镜/draw/拆树」留作收尾 step。可顺带把 4259 的 `filters` 与 4265 的 `draw` 拆开。
- **为什么**：step 7/8 占本轮 ≥8ms 单步的 94%（144/156 次、1804/1904ms），单步峰值 125ms；该 125ms 单步落在 at=43561 的 182ms 帧里，**解释掉该帧 69%**。
- **能省**：**尾部延迟**，把最坏单步从 125ms 压到 ~30ms 量级（与 step 7 峰值同级）；**总工时不省**。
- **风险**：增量 step 需要跨帧持有 Sprite/掩码树（现有 step 闭包已有先例，2845/2821）；cancel 路径必须能 dispose 这些中间对象，否则泄漏；`this.m`/`loc` 的保存-恢复已有框架（3427-3450），但新拆的子步必须自己保证不跨帧依赖 `this.loc` 的临时样式。**风险中，需一次像素等价 + 长帧复测。**
- **依据**：【确证·Grafon.as:4136-4294】【实测复算·cold-r3 events】；**「能压到 30ms 量级」为【推测】**。

### P2（次选）弹痕不再废掉进行中的预热

- **改哪里**：`sceneApply` 1116 行去掉/条件化 `sceneCancelWarm(affected)`（至少对 `kind=="decal"` 且 `args[6]=="normal"` 的情况）。
- **正确性论据**：新弹痕在 1119 行已 push 进 `sceneMarks`，而进行中的 job 的最后一个 step 就是 `sceneRestoreMarks()`（3038-3041），重放时按 `sceneRegionPassActive` 走直绘（1604-1608 → 4663-4667 → 4697/4712），会把这块内的全部 mark（含刚发生的那一发）画进正在预热的缓冲。【确证·Grafon.as:1119,3038,1170-1196,1604】
- **能省**：实测 431ms/81.7s 废弃工作（预热总时间的 7.4%）+ 11 次 4 块位图重建；同时消除「取消后从第一步重来」的那部分 ≥30ms 单步。
- **不承诺**：**不保证降长帧**。冷态配对显示 29 次 sync 中 0 次与取消同块（`implementation-20261103.md:74`），即取消并没有被观测到直接转成同步补画。
- **风险**：mark 顺序/重放范围与「区域样式分组」的相互作用需要一次像素等价验证；`paint/gwall` 是否也一并处理要单独判断（它们同样进 marks，但语义上可能要求立刻生效）。**风险低–中。**

### P3（结构性，非帧时）驻留块上限 + `sceneApply` 空间索引

- **改哪里**：`sceneChunks` 增加按「距视口块距」的逐出（例如 >6 块且非当前 job 目标）；`sceneApply` 1125 的 `for each(entry in sceneChunks)` 换成按块索引（弹痕世界坐标 → 块坐标，直接取 1–4 块）。
- **能省**：实测 `applyScanned=98,628 / 836 发 = 118 块/发` 的线性扫描和 ≈397MB 驻留内存；随游玩时长增长的那部分「不可控」也一并消失。
- **风险**：**回头路会重新触发同步补画**（本次路线是直线往返，真实探索会折返）；与 `sceneHistory`/marks 的语义耦合（marks 按 location 保存，逐出块后重进要重放）。**风险中。**
- **依据**：【确证·Grafon.as:1125,510-534】；收益量级【推测】——现有数据没有测过「驻留块数 vs 每发 decal 耗时」的曲线（§6）。

### P4（顺手修）`sceneApplyCompactDecal` 临时位图按宽高分配

- **改哪里**：905 行 `new BitmapData(int(local.right), int(local.bottom), …)` 改为按 `area` 的宽高分配并相应改 906/913 的 copyPixels 目标点。
- **能省**：单发单块分配从「右下角坐标积」降到真实面积；块中心 200×200→约 60×60（~9×），角上 400×400→约 60×60（~40×）。82 秒 836 发 × 1–2 块。
- **不承诺**：与 P4 同类的「减分配」已有三次实验无帧时收益（`implementation-20261103.md:70-72`），所以这只是**去掉明确浪费、降低分配抖动**，不要写成性能收益。
- **风险**：极低（纯局部算式），但必须过一次像素等价。

---

## 6. 还缺什么证据、怎么一次测出来

### 6.1 最大的盲区（本轮新发现，容易被忽略）

【实测复算·cold-r3 samples×events】把 47 个 ≥100ms 帧与 196 条 CS 事件按时间窗配对：

- 帧内 CS 事件总耗时 **385ms / 5975ms = 6.4%**；**32/47 个长帧里一个 ≥8ms 的 CS 事件都没有**（只有 15 帧命中事件，其中 1 帧是那次 43ms 同步补画）；
- 每帧字段 `continuousSceneHandlerMs` 的均值 2.37ms、**最大 13ms**；但 at=35629 那次 **43ms 同步补画**落在 at=35651 的 117ms 帧里，而该帧 `continuousSceneHandlerMs=4`。
- → **结论：`continuousSceneHandlerMs` 量的是模组自己的 ENTER_FRAME(-200) handler，里面不含被 patch 的 `Camera.calc → grafon.sceneTick()` 所驱动的 ensure/预热/同步/剔除。** 任何用「handler 计时」或「帧记录器」去归因 CS 的分析都会系统性漏掉 CS 最大的一块。

所以：**cold-r3 的「CS 只占 6.4%」是下界，不能反过来断言「CS 无罪」**；同理，真实游玩那 38 个长帧目前**根本没做相位归因**。

### 6.2 还缺的具体数据

1. **真实游玩长帧的相位分解**：每个 >100ms 帧里，CS 管线（sceneTick 内部：ensure/预热 step/同步/剔除）占多少、原生游戏 step 占多少、渲染/提交占多少、内存/GC 占多少——现在一个都没有分到。
2. **step 7/8 内部归因**：125ms 是哪张材质、几格、是否带滤镜（`param1.F`）；现在只记了 step 序号和毫秒。
3. **弹痕重放的真实成本**：`markScanned=30,947` 只统计「扫过多少条」，没有「实际重放多少条、多少 ms」，也没有区分预热路径 vs 同步路径。
4. **取消的后续命运**：11 次取消后，同一块最终是靠预热补上还是靠同步补画补上、晚了多少——现有分析只做了「sync 与 cancel 同块配对」。
5. **驻留块曲线**：`sceneResident` 随时间的曲线、以及每发 decal 的 ms 随 resident 的变化（验证 P3）。
6. **低负载基线**：cold-r3 是脚本路线 + 并行负载（p50 帧 59ms、p95 92ms、进程内存 300–418MB），绝对帧值不能外推真实游玩。

### 6.3 一次测出来的方案（单轮 run）

在已部署 CS 0.9.7 + 宿主 A9B39CC7 上，跑 **一次 3–5 分钟自然游玩**（马哈顿废墟、轻机枪、RV/WB/LAD 关闭、后台低负载、登记共享测试表），探针只加**计时**不改行为：

1. 帧壳：沿用 `ContinuousSceneMotionProbe` 已有的 `Event.ENTER_FRAME` 优先级 1000 / -2147483647 与 `RENDER`/`EXIT_FRAME` 钩子，得到 `dtMs`、`eventChainMs`、`renderMs`；
2. **补上最关键的洞**：在 `Camera.calc → sceneTick()` 两侧各打一个时间戳，得到 `scenePipelineMs`，并在 Grafon 内把它拆成 `ensureMs/advanceMs/syncMs/cullMs`；
3. 复用 diagnostic-v2 已有计数器，再补三个：`markApplied`、`markMs`（区分预热/同步路径）、`stepHist[25]`（每 step 的调用数/总时长/峰值，含材质 id 与掩码格数）；
4. 每帧记录 `sceneResident / sceneMarks.length / sceneWarmBudget / memoryBytes`，并保留 **Top-200 帧的完整分解**（dt、四个相位、是否含 sync/step、memory 增量）；
5. 验收方式：对每个 >100ms 帧，**已命名相位之和 / dt ≥ 80%**，且能回答「这 38 个长帧里 CS 管线占几分钟」。分析脚本在 `tools/stutter_analyze.py` 上扩一段 join 即可（本轮 §6.1 的配对逻辑可复用）。

> 若不想开新轮：**至少先把 §6.1 的配对分析补进 `analyze_cold_causality.py`**（把 step/sync/cancel 事件与逐帧 samples 做时间窗 join，并单列「命中长帧的事件毫秒」），零成本就能把 cold-r3 的结论从「29 次 sync 0 次配对」升级成「长帧归因覆盖率」。

---

## 7. 引用与口径

- 源码（唯一权威）：`mods/ContinuousScene/build/generated/envkey-cache-20261102/host-export/scripts/fe/graph/Grafon.as`（4864 行，对应宿主 A9B39CC7）。
- 原版：`game-reference/decompiled/1.02/src102/scripts/fe/weapon/Bullet.as`、`.../fe/loc/Location.as`、`.../fe/graph/Material.as`。
- 实测：`mods/ContinuousScene/knowledge/experiments/stutter-optimization-implementation-20261103.md:66-74`（cold-r3 汇总）；原始数据 `knowledge/experiments/evidence/stutter-opt-explore-cold-r3-20261104/storage/result.json`（`samples` 1300 帧、`chunkDiagnostics.events` 196 条：sync 29 / step 156 / cancel 11）；帧记录器同目录 `storage/frame-recorder/frames-v1.jsonl`。
- 诊断计数器定义：`build/generated/stutter-opt-20261103/diagnostic-v2/source/fe/graph/Grafon.as:787,1135,1183,3074,3401-3405,3482`（`applyScanned` 每扫一块 +1、`markScanned` 每扫一痕 +1、`step` 事件仅记 ms≥8）。
- 旧方案：`mods/ContinuousScene/design/scene-combat-camera-optimization-plan.md`、`design/stutter-optimization-plan-20261103.md`——其中「滤镜 20–35ms」「取消必然转同步补画」「48ms 预算=长帧起因」均**未被本轮实测支持**，本报告不采用。
- 未做：未运行游戏/AIR、未构建 SWF、未改 src/release/game-reference、未 git 提交。
