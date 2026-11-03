# 镜头移动时背景粗糙的成因与动态模糊代价（只读调查）

2026-11-04。任务：只读调查用户第三项反馈“镜头移动时背景（墙壁等）移动的视觉效果较粗糙”，并对“引入动态模糊”给可量化判断。本文不含任何游戏运行、构建或部署；所有数字来自本仓已有实测或源码。

> **2026-11-04 更新**：本轮收尾时同目录出现了 `blur-benchmark-lead.md`（Lead 的 AIR 离线微基准，2048×1123，直接测了 `applyFilter` BlurFilter、累积合成与双线性采样），它**直接测到了**我以前只能外推的量级。本文 §2.3、§3、§4①、§5 已按它更正；凡引用处标注“离线代理”，因为它不是游戏进程内数值（见该文 §3 方法学限制）。

标注约定：
- 【确证·文件:行号】= 我本轮直接读到的源码/证据，行号可核。
- 【已有实测·报告相对路径】= 本仓报告里的实测数字（报告路径统一相对 `mods/ContinuousScene/knowledge/`，行号给到）。
- 【推测】= 由前两者推理、尚无本仓直接测量的结论，必须实测才能成立。

## 0. 结论速览

**一句结论（必答 5 的正面回答）**：**现在不能判定“粗糙”来自哪一项**——现有证据只能排除 (c) 相机整数截断（最多 1 屏幕像素，且 scaleV=1 时正落在像素网格上），并把 (b) 最近邻采样限定为“只在 scaleV≠1 的窗口存在”（2048×1123 下 scaleV=1，最近邻重采样根本不发生），于是 (a) 30fps 与 (d) 帧时抖动是始终存在的底噪、只有 1280×720（scaleV≈0.6583）才叠加 (b)；要定主因，必须先在同一路线记录 `scaleV` 并做一次 smoothing 开/关对照，而这一步在本仓从未做过。

各必答的短答案：

1. **相机链路**：`X/Y/vx/vy` 全是 `int`；世界容器 `visual.x` 一共只有 4 处赋值，除 `quakeX/quakeY` 外全是整数；`scaleV≠1` 是**世界整体缩放**（`visual.scaleX=scaleV`），而 game stage 本身是 `noScale`（无舞台缩放），所以 0.6583 是**镜头缩放**不是 stage 缩放。**整数截断不会造成亚像素爬行**，整数截断只把相机量化到 1 屏幕像素。
2. **地块位图**：宿主所有地形地块 Bitmap 都是 `new Bitmap(data)` → `smoothing=false, pixelSnapping=auto`（默认值），只有 SATS 快照与光照图开了 smoothing；CS 呈现层的 bitmap fill 也原样传 `smooth=false`。开 `smoothing=true` **不会**触发任何额外离屏 pass 或缓存失效（这些位图根本没设 `cacheAsBitmap`），代价只在既有逐像素采样里；但会被现有“逐像素相等”门禁全部判失败，需要新验收口径。40px gutter 在几何上远够（双线性只需 ±1 texel），但**预热快速路径的 gutter 内容是近似的**（A2），开平滑会把近似变成块边可见像素。
3. **动态模糊**：**不做**。Lead 的离线微基准（2048×1123）直接测到：单方向 `BlurFilter` **15.5～19.5ms/次**（半径 2→16 几乎不变）、双向 quality1 **20.3～22.3ms**、quality2/3 **30～83ms**；把模糊挂到世界容器上单次绘制 **23.0～58.7ms**（无滤镜时 4.4～11.9ms）。30fps 预算只有 33.3ms、当前整帧已 33～45ms：加一次全屏模糊 → **48～64ms（约 16～21fps）**，挂到容器上 → **56～104ms（多数组合 <15fps）**。累积拖影的混合本身只要 **2.2～3.2ms/帧**，但“把当帧画面抓进缓冲”才是贵的那一步（游戏内实测半分辨率整景合成 **+16～19ms/帧**），且拖影会一并污染 UI/准星。旧方案里的“BlurFilter 35~85ms”“全屏 BitmapData.draw 10~18ms”“smoothing <0.4ms”在本仓都**没有出处**，前两个已被基准量级取代、第三个被基准否证（见 §3）。
4. **替代改法**：①只对地形层开双线性 —— **按基准在 `scaleV≈0.6583` 时要 +3.9～7.2ms/帧（33.3ms 预算的 12～22%）**，不是免费，且只在 scaleV≠1 有意义（1:1 下双线性零收益零成本）；②相机亚像素化（必须与①配对，否则会加重闪烁）；③轻度阻尼/插值（只改手感，不解决采样）；另有一个**零渲染改动**选项：把默认窗口改成 scaleV=1（`zoom100`），直接消灭重采样，代价是视野变小。详见 §4。
5. **最小诊断**：一次 1–2 分钟的“同路线、两窗口、smoothing 开关、慢移/快移、长帧标记”被动记录即可判别四者，不需要重建宿主（smoothing 可由模组层运行时改），详见 §5。

---

## 1. 必答 1：相机链路

### 1.1 类型与截断点

参考源码 `game-reference/decompiled/1.02/src102/scripts/fe/inter/Camera.as`（下称 `Camera.as`），与两份 **CS 宿主构建源** 逐项对照：

- `mods/ContinuousScene/build/generated/scripts/fe/inter/Camera.as`（下称 `Camera.build.as`，2026-10-19 全量构建源）：含 §1.2 的 setZoom 改造与 §1.3 的 `calc→sceneTick` 一行。
- `mods/ContinuousScene/build/generated/vertical-camera-band-20261023/source/fe/inter/Camera.as`（下称 `Camera.band.as`，2026-10-23 已部署的纵向镜头带补丁源，最接近 A9B39CC7 谱系）：除上述两项外，大场景里还把 Y 钳制在玩家附近 `±csVCBand`（`:294-295`）。**也就是说当前相机已经有“纵向带内不服随”的既有缓动，不是硬跟随。**

（部署宿主的 Camera 我只能看到派生构建源、没有 A9B3 的逐字节回读；但 §1.2 的 1280×720 实测 `scaleV=0.6583=1264/1920` 与 `experiments/camera-combat-window-lead-20261029.md:46` 只可能由“大场景按 1920×1000 求倍率”这条改造产生，故运行时行为已被实测反证。）

| 成员 | 类型 | 行号 | 说明 |
|---|---|---|---|
| `screenX / screenY` | `int` | Camera.as:16,18 | 初值 1280/800，`setLoc` 里被 `swfStage.stageWidth/Height` 覆盖（Camera.as:76-77） |
| `X / Y` | `int` | Camera.as:20,22 | 相机中心（屏幕空间量纲，见 1.2） |
| `vx / vy` | `int` | Camera.as:24,26 | 世界容器平移 |
| `ovy` | `int` | Camera.as:28 | 上一帧 Y（纵向缓动用） |
| `otryv` | `Number` | Camera.as:44 | 观察者偏置 |
| `quakeX / quakeY` | `Number` | Camera.as:46,48 | 唯一让容器平移带小数的量 |
| `scaleV` | `*`（赋值为 Number） | Camera.as:52 | 世界容器缩放 |
| `scaleS` | `*` | Camera.as:54 | HUD 缩放（与本问题无关） |

截断点（写入即截断，读回是 int）：

- `Camera.as:218`、`Camera.as:225`：`this.X = param1.X * this.scaleV;` / `this.Y = param1.Y * this.scaleV;` —— 玩家浮点坐标乘 `scaleV` 后写入 int。
- `Camera.as:207-208`、`212-213`：观察者/鼠标偏置分支同样写 int。
- `Camera.as:219-222`：纵向“跳跃缓动”分支，`this.Y = this.ovy - (this.ovy - param1.Y*this.scaleV)/4;`（写入 int，取整后失去 1/4 缓动的细粒度）——**原版本来就有纵向阻尼**，所以旧方案“相机完全无缓动硬跟随”的说法不准确。
- `Camera.as:236` / `252`：`this.vx = -this.X + this.screenX / 2;`、`this.vy = -this.Y + this.screenY / 2 + 100;` —— int 赋值，`screenX/2` 在奇数分辨率（如 2048×1123 的 `1123/2=561.5`）也会被截断成常数偏移。
- `Camera.as:100-101`（`setKoord`）：`param1.x = param2*this.scaleV + this.vx` —— 这里**可以**是小数（单位/物件用），也就是说单位能拿到亚像素位置，而**相机与地形容器不能**（下面 1.3）。

### 1.2 `scaleV` 的来源：它是镜头缩放，不是 stage 缩放

- stage 没有缩放：`game-reference/.../scripts/MainFE.as:20-21` 明确 `stage.scaleMode = "noScale"; stage.align = TOP_LEFT;`，`Camera.as:76-77` 直接取 `stageWidth/stageHeight`，`World.as:784-811`（resizeScreen）里没有对世界容器做比例修正。所以 **任务背景里“默认窗口 scale≈0.6583，stage 缩放”这个表述需要更正：0.6583 是 `cam.scaleV`，作用于 `w.visual`（世界容器）**。【确证·MainFE.as:20-21 / Camera.as:76-77 / World.as:784-811】
- `scaleV` 的算法：`Camera.setZoom`（Camera.as:104-160）。`isZoom==1` → 取 `max(screenX/maxsx, screenY/maxsy)`；`isZoom==2` → 取 `min(...)`；其余 → 1；随后 `if(scaleV>0.98) scaleV=1`（Camera.as:132-135）；`maxvx = maxsx*scaleV - screenX`、`maxvy` 同理（Camera.as:136-137）；`visual.scaleX=visual.scaleY=sats.vis.scaleX/Y=scaleV`（Camera.as:138）。【确证】
- 当前宿主里 `setZoom` 被 CS 改成：大场景时倍率一律以**原版 1920×1000 参考尺寸**求（`Camera.build.as:106` 用 `loc.spaceX>World.cellsX || loc.spaceY>World.cellsY` 判大场景，`Camera.build.as:122,126` 用 `sceneLarge?1920:maxsx` / `?1000:maxsy`），而边界仍用全图（`Camera.build.as:137-138` 的 `maxvx = maxsx*scaleV - screenX`）。`World.cellsX=48, cellsY=25`（World.as:40,42）→ 原版房间=1920×1000。这条设计与设计文档一致：【确证·Camera.build.as:106,122,126,137-138 / World.as:40,42】【已有实测·experiments/experience-v05-20261015.md:32】（“移除两处强制归零，0/1/2 三档沿原版 1920×1000 参考尺寸计算；实际全图边界不变”）。
- `isZoom` 默认就是 2：`World.as:602-613`，`zoom100` 默认 false → `cam.isZoom = 2`。所以**默认玩家的镜头就是“2 档”**，这也解释了实测“进入时 isZoom=2”。【确证·World.as:210,602-613】【已有实测·experiments/camera-scale-coverage-20261029.md:9】【已有实测·experiments/camera-combat-window-lead-20261029.md:46】
- 于是实际缩放只取决于窗口与 1920×1000 参考：
  - 2048×1123：`min(2048/1920, 1123/1000)=1.0667 > 0.98` → **`scaleV=1`（无重采样）**。【推测=公式代入，但与本仓“大窗 scale1”实测一致：experiments/camera-optimization-followup-20261101.md:19、experiments/quality-and-dense-enemies-20261101.md:10】
  - 1264×681：`min(1264/1920, 681/1000)=0.6583` → **`scaleV=0.6583`**；1280×720 内容区被测为 1280 宽时是 0.6667（2/3）。【已有实测·experiments/camera-combat-window-lead-20261029.md:46】【已有实测·experiments/camera-scale-coverage-20261029.md:9】
- **重要推论**：`scaleV=0.6583` 意味着世界被整张缩小 1.52:1 后显示（可视世界区域 = 1264/0.6583 × 681/0.6583 ≈ 1920×1034，正好一个原版房间的视野）。此时“背景粗糙”的第一嫌疑是重采样，而不是相机。

### 1.3 `w.visual.x` 的全部赋值位置

全仓 grep `visual.(x|y|scaleX|scaleY)\s*=` 在 1.02 反编译源只有 5 处，全部在 Camera：【确证·Camera.as】

| 位置 | 赋值 | 是否可能为小数 |
|---|---|---|
| Camera.as:88-89（`setLoc`） | `visual.x = sats.vis.x = vx` | 否（vx 是 int） |
| Camera.as:138（`setZoom`） | `visual.scaleX/Y = scaleV` | 是（缩放本身） |
| Camera.as:285-286（`calc`，每帧） | `visual.x = sats.vis.x = vx + quakeX` | **仅 quake 时**是小数 |

宿主构建源里多了一行：`Camera.band.as:368` 在 `366-367` 的 `visual.x/y` 之后调用 `this.w.grafon.sceneTick()`（把逐帧 chunk 补齐/剔除挂在相机更新之后）。模组层也会写同一个字段：`src/SceneAimController.as:186-187`（按住瞄准键时 `w.visual.x = ax + cam.quakeX`，且 `:180-183` 注释明确记录“Camera 声明 vx/vy/celX/celY 是 int，写分数被静默截断”）。【确证·Camera.band.as:366-368 / src/SceneAimController.as:180-187】

**quake 叠加的边界**：`World.quake(x,y)` 把 `quakeX/quakeY` 累加到 `Camera` 上并钳制 ±20（`World.as:1419-1446`），且 `loc.sky`（飞行/室外）时直接 return（`:1421-1424`）；`Camera.calc` 每帧做乘法衰减（约 80% 概率乘 `-(0.3~0.8)`），`|q|<1` 时归零（`Camera.as:263-284`）。也就是说**震屏是唯一让世界容器亚像素平移的来源，且只在开火/受击后约十几帧内存在**——如果用户说的“粗糙”在射击时明显更重，这一项要单独算，但它不是 CS 引入的（原版同逻辑）。【确证·World.as:1419-1446 / Camera.as:263-284】

### 1.4 判断：“整数截断导致非整数缩放下的像素爬行”成立吗？

**不成立，这是两件事被混在一起。**【推测，但推理链完全由 §1.1–1.3 的确证事实组成】

1. 相机平移在无震屏时是**整数屏幕像素**（`vx:int`；`visual.x = vx + quakeX`，quake=0 → 整数）。整数平移本身**不产生亚像素相位变化**，它只把相机量化到 1 屏幕像素。
2. 在 30fps、玩家常态速度下每帧位移是若干像素（旧方案的数字“150–300px/s → 5–10px/帧”【推测，本仓未实测玩家速度】），1px 的量化误差被更大的每帧步进掩盖，肉眼不会额外感知。
3. 真正制造**亚像素相位不稳定**的是 `visual.scaleX = 0.6583` 这个**非整数缩放**：最近邻采样下，屏幕第 k 列取源 `floor((k-tx)/scale)`；相机 `vx` 每帧加 1，采样相位就跳 `1/0.6583 = 1.52` 个源像素（非整数），于是**同一块墙每帧被抽掉的源像素列/行都不同** → 高频边缘闪烁、爬行。量化到 int 的相机只是决定了“每帧跳几格”，不是爬行的来源。
4. 反过来：`scaleV=1` 时（2048×1123 窗口），`vx` 整数 + 世界 1:1 → 采样落在整像素上，**根本没有重采样**，墙壁只会“整像素跳”，不会“爬”。
5. 附带更正两点旧方案表述：原版**已有**纵向 1/4 缓动（Camera.as:219-222），CS 又加了“大场景纵向带”（`Camera.band.as:294-295` 把 Y 钳在玩家 `±csVCBand` 内）；相机也**不是**“硬绑定玩家”，`otryv` 的观察者/鼠标偏移分支（Camera.as:176-228）本来就在。

---

## 2. 必答 2：地块位图、smoothing 与 gutter

### 2.1 宿主里地块 Bitmap 的创建处与真实属性

宿主连续场景实现：`mods/ContinuousScene/build/generated/envkey-cache-20261102/host-export/scripts/fe/graph/Grafon.as`（下称 `Grafon.as`，A9B3 回执对应的导出源）。

| 创建处 | 代码 | smoothing | pixelSnapping |
|---|---|---|---|
| 常规块 `sceneRender` | `Grafon.as:760-761` `clone()` + `new Bitmap(data)` | **false（默认）** | **auto（默认）** |
| 常规块裁剪 | `Grafon.as:762` `bitmap.scrollRect = new Rectangle(gutter,gutter,side,side)`；`763-764` `x=cx*side, y=cy*side` | — | — |
| 预绘全图 `scenePreloadAll` | `Grafon.as:2568-2572` `new BitmapData(size,size)` + `new Bitmap(data)` + scrollRect | false | auto |
| 区域/批次绘制 | `Grafon.as:1974-1977`、`Grafon.as:2102-2105` 同型 | false | auto |
| 预热块应用 | `Grafon.as:3531-3534` 同型 | false | auto |
| SATS 快照 | `Grafon.as:1247` `new Bitmap(data,"auto",true)` | **true** | auto |
| 光照图 | `Grafon.as:370` `new Bitmap(this.lightBmp,"auto",true)`；`:481` 再设 `smoothing=true` | **true** | auto |
| 非大场景的四层合成位图 | `Grafon.as:353,356,359,362` `new Bitmap(...)` | false | auto |

CS 侧测试也把“地块 = 透明 + auto + 非平滑”当作契约来断言：【确证·src/tests/SceneBackgroundCompositeProbe.as:169】`b.bitmapData.transparent && b.pixelSnapping=="auto" && !b.smoothing`。其余 `pixelSnapping`/`smoothing` 出现处都是“保存/恢复原值”（`src/native/scene-crop-presentation.as.inc:33-34,69-70`、`src/SceneRasterPresentation.as:49`、`src/SceneRasterRowsPresentation.as:89-93`），没有任何产品代码把地形 smoothing 设为 true。【确证】

### 2.2 CS 呈现层：fill 与矩阵

- 资格：呈现器**只在 `scaleV==1` 时接管**（`src/SceneEventBitmapFill.as:106`、`src/ScenePresentationCoordinator.as:66`），并要求世界容器矩阵是整数平移（`SceneEventBitmapFill.as:114-120`；震屏 ≤25px 时容忍小数平移），还要 RV/WB/LAD 四个开关全关（`ScenePresentationCoordinator.as:91-104`）。实测印证：小窗返回 `zoom-or-shake`、大窗 `presented=true`。【已有实测·experiments/camera-iteration-review-20261101.md:69】
- 绘制：`SceneEventBitmapFill.as:243-244` `node.graphics.beginBitmapFill(item.data, new Matrix(1,0,0,1,item.x-item.gutter,item.y-item.gutter), false, item.smooth)` + `drawRect(item.x,item.y,CELL,CELL)`；`item.smooth` 就是原 Bitmap 的 `smoothing`（`:178,180`），即 **false**。
- 因此**默认窗口（scaleV=0.6583）下走的不是这条 fill 路径，而是宿主原生的每块 4 张 Bitmap**（`Grafon.as:761`）——即 smoothing=false 的最近邻。这一点决定了：讨论“开 smoothing”必须改的是**宿主的四条块创建路径**（`Grafon.as:761/2569/1974/2102/3531`），或由模组层在运行时遍历 `grafon.sceneSurfaces()` 改属性；改 `SceneEventBitmapFill` 对默认窗口无效。

### 2.3 开 `smoothing=true` 到底会发生什么

- **不会**增加离屏 pass、**不会**让缓存每帧失效：这些 Bitmap 都没有 `cacheAsBitmap`（全文件只有 `ramT/ramB/ramR/ramL` 设了 true：`Grafon.as:376,4255`，另有 `Grafon.as:4283` 设 false）。`smoothing` 只是光栅器的采样核从“最近邻 1 点”换成“双线性 4 点”，**重采样本来每帧都在发生**（因为父容器 scale≠1），开平滑不改变 pass 数，只改变每像素采样成本。【确证·Grafon.as 全部创建工作 + AS3 属性语义】【推测·成本方向】
- 成本量级：本仓**没有游戏内**的 smoothing 直接 A/B，但同目录的 Lead 离线微基准**直接测了等价形状**（2048×1123，离屏 BitmapData，非舞台合成）：
  1. **4 层全屏 ×0.6583 最近邻 13.55/2.08ms → 双线性 20.70/6.02ms**，即 **+3.9～+7.2ms/帧**（两轮差异来自本机并发负载，取区间）；逐块路径“每层 28 块 400px 源/320 裁剪”最近邻 26.96/4.49 → 双线性 39.89/6.33，即 **+1.8～+12.9ms/层**。【已有实测·同目录 blur-benchmark-lead.md:26-31,54（离线代理）】
  2. **1:1（scaleV=1）时双线性不增加成本**（12.13 vs 12.40、1.97 vs 2.22，噪声内）。【同上:28-29,55】
  3. 把地形容器加 `cacheAsBitmap=true` **更慢**（11.91→19.96、4.42→7.27），再次否掉缓存方向。【同上:32-33,60】
  → 因此旧方案“**全屏 4 层 <0.4ms**”**被否证**（原文 `design/scene-combat-camera-optimization-plan.md:301`、`state/journal.md:14`）：在 0.6583 下双线性是 **4～7ms 级**（33.3ms 预算的 12～22%），不是亚毫秒；只有在 1:1 时才接近免费——而 1:1 时它本来也不改变画面。这条修正**改变了方案①的可行性判断**（见 §4①）。
- **门禁含义**（容易被忽略的实施成本）：本仓所有呈现相关门禁都是“同帧逐像素 RGBA 相等”（例如 `ScenePresentationChecks`、`SceneNativeCropChecks`、`SceneAtlasChecks` 全图零差；实测口径见 `experiments/camera-optimization-followup-20261101.md:49,59,63`）。开平滑是**故意改变像素**，必须像 v21/v25 那样另立“允许软化”的验收口径（例：只要求无 1px 线缝、无色偏、块边 2px 内差异有界），否则任何实现都会被判失败。
- 一个会真实变差的点：`scrollRect` 裁剪 + 平滑下，块边最后一列像素是否采样到 gutter **取决于 Flash 是先采样后裁还是先裁后采样**——本仓没有证据。【推测】但从 `src/tests/SceneEmptyTerrainProbe.as:14` 的记录（“centre with occupied gutters does NOT qualify: smoothing may sample them”）看，本仓的既有认识是**平滑会采样 gutter**。这意味着 40px gutter 的**内容正确性**变成前提，见 2.4。

### 2.4 40px gutter 够不够避免接缝

- 几何上**远够**：双线性只需要目标像素左右各 1 个源 texel；CS 的块位图是 `320+2*40=400`（`Grafon.as:206` `sceneGutter=40`、`:204` `sceneSide=320`），显示时用 scrollRect 只露中心 320（`Grafon.as:762`），fill 路径还特意保留 `x-gutter` 的采样偏移（`SceneEventBitmapFill.as:241-244` 注释“retain the 40px sample offset”）。【确证】
- 真正风险不是“没有数据”，而是“**gutter 的数据是近似的**”：A2 快速暖块为了省时间，把只覆盖 gutter 的风格整绘跳过了，gutter 像素按中心组近似（部署记录明确“cost is gutter pixels approximated by the centre group… 伤害贴花/WallBlend 在块边界的采样可能偏差”）。【已有实测·experiments/a2-current-deploy-20261031.md:3,51】当前 smoothing=false + scrollRect 裁掉 gutter，所以这个近似**看不见**；一旦开平滑，块边 1–2px 可能采到近似像素 → 表现为每 320px 一条**风格/亮度轻微偏差的竖线**（不是透明缝）。【推测】这正是 §4 方案①必须配“块边像素检查”的原因。
- 另外，2/3 缩放下“像素吸附（pixelSnapping）”**不是**差异来源：小组件实测 `auto` 与 `never` 的 12/12 结果完全相同、`always` 全部失败。【已有实测·experiments/camera-pacing-phase-20261029.md:56】所以不必把 `pixelSnapping` 当主因；开平滑时顺手设 `NEVER` 只是把 A/B 变量减到一个。

---

## 3. 必答 3：动态模糊的真实代价

### 3.1 旧数字的出处问题

`design/scene-combat-camera-optimization-plan.md:267-281` 写“BlurFilter 单帧 35~85ms → 8~12fps”、“全屏 BitmapData.draw 10~18ms”，`:301` 写“4 层 smoothing 增加 <0.4ms”。这三个数在 `state/journal.md:14` 被原文复述，但**本仓没有任何实验报告测量过它们**（我按 `BlurFilter|blur|模糊|BitmapData.draw` 普查了 knowledge 与 design，未见对应计时）。它们属于“**无出处的估计**”，不能作为决策依据。下面 §3.2 是 Lead 在本轮补做的**直接微基准**，§3.3 是游戏内实测的相邻操作，§3.4 才是外推。

### 3.2 Lead 离线微基准：直接测到的数字（2048×1123）

性质见 `blur-benchmark-lead.md:5-8`：AIR SDK 51.3 + `adl64.exe`、隐藏窗口、离屏 `BitmapData`、每项内循环摊薄 + 15 轮均值、两轮独立运行取区间。**这是“同一组原语的离线代理测量”，不是游戏进程内数值**，用来定生死量级，不能直接当帧时增减。【已有实测·同目录 blur-benchmark-lead.md】

| 测量项 | ms/操作（轮1 / 轮2） | 说明 |
|---|---|---|
| 全屏 `fillRect` / `copyPixels` | 0.66/0.81、0.52/0.80 | 基准：整屏 2.3M 像素写/拷 |
| 全屏 `copyPixels`+`draw`(alpha 0.6)（残影累积的**混合**） | 2.16 / 3.18 | 混合本身很便宜（见下） |
| `applyFilter BlurFilter(2,0,1)` 单方向 | 15.63 / 19.13 | 半径 4/8/16 几乎同价（15.5~19.5）→ 瓶颈是整帧带宽，不是卷积核 |
| `BlurFilter(8,8,1)` 双向 | 20.34 / 22.30 | quality 1 |
| `BlurFilter(8,8,2)` / `(8,8,3)` | 30.31 / 50.65 与 83.15 / 31.20 | quality 2/3 更糟 |
| 世界容器（≈30 个地块 Bitmap）无滤镜绘制 | 11.91 / 4.42 | 参照 |
| 同上 + 容器 `BlurFilter(6,0,1)` | 58.65 / 23.68 | “给世界容器挂模糊” |
| 同上 + 容器 `BlurFilter(3,0,1)` | 56.00 / 23.03 | 半径降到 3 几乎不便宜 |
| 同上 + 容器 `cacheAsBitmap=true` | 19.96 / 7.27 | 比不加滤镜还慢 |
| 已就绪全屏缓冲 1:1 呈现 | 0.66 / 0.65 | 呈现便宜、**产出**贵 |

关键判读：

- **最便宜的模糊也要 15～19ms/帧**，挂在容器上更高（23～59ms）。30fps 预算 33.3ms、当前整帧均值 33～45ms：加一次全屏模糊 → 整帧 48～64ms（约 16～21fps）；容器模糊 → 56～104ms（多数组合 <15fps）。**都不可接受。**
- “半径调小就便宜”不成立 → 不必再试 quality/半径档位。
- 累积拖影的**混合**只要 2.2～3.2ms，但每帧仍必须先把当帧画面**抓进**全屏缓冲，而“抓”这一步在游戏内实测是 16～19ms（半分辨率）/33～78ms（单次 1×），见 §3.3——且拖影对全屏生效，会一并拖脏 UI、准星、角色与弹道。

### 3.3 游戏内实测的相邻操作（这些是“相邻操作”，不是 blur 本体）

| 操作 | 窗口 | 实测成本 | 出处 |
|---|---|---|---|
| 每帧把整个世界按 0.5 画入复用 BitmapData 再放大（半分辨率整景合成） | 1264×681（0.86MP） | 静止 29.964→47.749、横移 36.006→52.106、纵移 33.670→52.536（**+16.1～18.9ms/帧**；报告正文归纳为“额外合成约 22–32ms/帧”，含恢复/切换开销） | 【已有实测·experiments/quality-and-dense-enemies-20261101.md:16,20-26】 |
| 1× 分辨率 + drawWithQuality(low) 合成 | 同上 | 静止 57.897、横移 55.626、纵移 54.902（**+19.6～27.9ms/帧**） | 同上:20-24 |
| 隔 2/3 帧半分辨率重画 + 平移缓存 | 同上 | 3 帧档横移 66.927→65.399（仅 −2.3%）但 P95 106→160、>100ms 14→26；**单次合成 33–78ms** | 同上:82-88 |
| 屏幕像素增量缓存（少画整帧的一部分） | 小窗 | 28.018→27.202（≈2.9%）；大窗 35.190→39.166（更慢 11.3%） | 【已有实测·experiments/camera-optimization-followup-20261101.md:36-37】 |
| 地形 0.5/0.75 分辨率缓存 | 小窗 | 方向反转、无稳定收益、画面明显变软 | 【已有实测·experiments/quality-and-dense-enemies-20261101.md:50-58】 |
| 原生 GPU 描述符（renderMode=gpu） | 大窗 | 43.120/48.182/47.645ms，未见可采用收益 | 同上:42-44 |
| `cacheAsBitmapMatrix` | 桌面 | 官方不支持 | 【已有实测·experiments/lossless-cut-survey-20261101.md:20,77】 |

### 3.4 组合起来看一次“真正的动态模糊”要多少（外推，标注清楚）

- 2048×1123 = 2.305MP，是 1264×681（0.861MP）的 **2.68 倍**。按像素面积线性外推：一次“全屏级捕获/合成” → 约 **43～51ms**（半分辨率整景口径）或 **59～86ms**（22–32ms 口径）；单次捕获 33–78ms → **88～209ms**。
- 一次可用方案的最小成本 = ①把当帧画面抓进全屏缓冲（游戏内实测：小窗 16～28ms，2048 外推 43～75ms）+ ②模糊（基准直接测：15～22ms）+ ③回贴（基准：0.65～0.87ms）≈ **小窗 32～50ms、2048 约 60～98ms 的额外开销**。在 26～30fps 的现有帧时上叠加 → **≤10～12fps**，且长帧会被拖影放大。
- 更彻底的问题：**BlurFilter 是各向同性空间模糊**，不是沿运动方向的模糊；真正像“运动模糊”的做法只有“上一帧以低 alpha 叠加”（累积缓冲）——它的混合便宜（2–3ms），但同样要每帧捕获（贵）且污染 UI。两条路都不成立。
- 视觉上也不划算：本仓实测真实游玩 **26.19 FPS 均值**（193 窗/196.364s/5143 帧），移动窗 25.84 FPS、静止窗 28.27 FPS，另有 38 次 >100ms、最大 242ms 的长帧。【已有实测·experiments/stutter-investigation-20261103.md:31-32,39】【已有实测·design/stutter-optimization-plan-20261103.md:23】把帧时再推高 1–2 倍，残影长度会随帧时抖动而忽长忽短（长帧拖影更长），主观上更晃。

**判断：动态模糊在 AIR CPU 软光栅下不做。** 旧“35~85ms”是无出处估计（方向对、数值无据）；用本仓实测重新表述为：**“`applyFilter` 一次单向模糊 15～19ms、双向 quality1 20～22ms、挂到世界容器上单次绘制 23～59ms（2048×1123 直接测量）；再加上每帧捕获画面的 16～28ms（小窗实测）/43～75ms（2048 外推），最小可用方案额外开销 32～50ms（小窗）～60～98ms（2048），必然 ≤10～12fps。”** 累积拖影（2–3ms 混合）虽然价格可谈，但它换不到帧率、还会拖脏 UI，只能作为**默认关闭的观感选项**，不属于优化。

---

## 4. 必答 4：三个（+1）候选改法

### 方案 ①：只给地形层开双线性（最便宜的真修复）

- **改哪里**：宿主 `Grafon.sceneRender`（`Grafon.as:761` 之后）、`scenePreloadAll`（`:2569`）、区域绘制（`:1974`、`:2102`）、预热应用（`:3531`）——统一改成 `bitmap.smoothing = this.sceneSmooth; bitmap.pixelSnapping = PixelSnapping.NEVER;`（或加一个 helper 只改一处逻辑）。**零宿主重建的试验路径**：在模组层用 `w.grafon.sceneSurfaces()`（`Grafon.as:394-402`）遍历每块的 `bitmaps[0..3]`，在 resident/revision 变化时设 `smoothing=true`（约 40 块×4=160 次属性写/变更，不是每帧）。【确证·Grafon.as:394-402,761,2569,1974,2102,3531】
- **A/B 测法（1–2 分钟）**：同一条固定走廊（现存 `camera-optimization-followup` 用的 ±160/±96 往返即可），在同一实例内交错“原样/smoothing”各 3 段（每段 90 帧），窗口跑**两个**：1264×681 与 2048×1123。指标：整帧 mean/P95/>50ms 计数、CS 局部 `presenter.updateMs`、以及**块边像素检查**（静止时在 320px 网格两侧各取 2 列，要求无新增 1px 线缝/无色偏）。
- **成本预期（有基准了，不再是“免费”）**：`scaleV≈0.6583` 时 4 层双线性 **+3.9～7.2ms/帧**（33.3ms 预算的 12～22%），逐块路径 **+1.8～12.9ms/层**；**`scaleV=1` 时双线性零额外成本、也零视觉变化**。【已有实测·同目录 blur-benchmark-lead.md:26-31,54-55（离线代理）】这意味着：**2048×1123 窗口下这个方案不是“便宜”，而是“无事可做”**——它只能帮到默认小窗那类 0.6583 的场景，而且要以 4～7ms 为代价。
- **失败判据**：实测增量超过基准区间上限（>8ms）或 P95 +>10% 或 >100ms 增多；任一块边出现可见近似线/缝；或出现“文字/HUD 变模糊”（不该发生，若发生说明改错了层）。
- **回退**：模组层开关（沿用 `nativeAPI` 的 `…EnabledSet` 模式，见 `src/ContinuousSceneMod.as:56-57,316-318`）；宿主侧回退=用 `build/generated/envkey-cache-20261102/host-export` 的原字节恢复该方法。
- **预期**：默认窗口（0.6583）下能降低“爬行/闪烁”，代价 4～7ms；2048 窗口**应完全无视觉变化**（1:1 采样，平滑无意义）——这本身就是一个对照，也是判断用户到底在哪个窗口玩的最便宜实验。

### 方案 ②：相机亚像素化（**必须与①配对**）

- **改哪里**：宿主 `Camera.calc` 的 `Camera.band.as:366-367`——保留 int 的 `X/Y/vx/vy`（玩法/AI/瞄准都依赖这些 int 语义），但写容器时加小数：`subX = -(param1.X*scaleV - X)`（即取整损失的那部分），`visual.x = vx + quakeX + subX`。**零宿主重建的试验路径**：模组层已有一个“原生 `Camera.calc` 之后”的钩子——`SceneAimController` 在 ENTER_FRAME -200 写 `visual.x = ax + cam.quakeX`（`src/SceneAimController.as:186-187`），把小数项加在这里即可。【确证·Camera.band.as:366-367 / src/SceneAimController.as:186-187】
- **关键耦合**：一旦容器平移带小数，`SceneEventBitmapFill.unsupported()` 会在“非震屏 + 小数矩阵”时返回 `fractional-or-non-unit-geometry` 并回退原生（`src/SceneEventBitmapFill.as:114-120`）→ 等于**白白丢掉**现在 scaleV=1 下的地形合并收益。所以②必须同时放宽该判据（并用 `beginBitmapFill` 的小数 tx 测试）或宣布②只在 smoothing 场景启用。【确证·SceneEventBitmapFill.as:114-120】
- **A/B 测法**：三级速度阶梯（约 0.25 / 1 / 3 屏幕 px/帧 的往返），每级在 smoothing 开的状态下比“亚像素开/关”。指标：**帧时（预期 ±0）**、块边/整屏静止像素差（应只在移动时不同）、主观“慢速移动是否还在跳”；另记录 `w.celX/celY` 与鼠标命中是否一致（`Camera.as:289-290` 用 vx 反算，必须用真实相机位置而不是加过小数的值）。
- **失败判据**：smoothing 关闭时亚像素化让闪烁**更明显**（这是预期，若用户觉得更差就停）；瞄准/准星偏移 >1px；上方呈现器回退（性能退化）；地图边缘 `ramL/R/T/B` 出现半透明缝。
- **回退**：同①的开关；这一项纯模组层即可完成，风险局限于画面。

### 方案 ③：轻度阻尼/插值（只改手感）

- **改哪里**：宿主 `Camera.calc` 的 X/Y 目标赋值（`Camera.as:218,225`；纵向带源对应 `Camera.band.as:287` 起的同逻辑）加一阶低通（如 `vx += (target-vx)*0.85`），或模组层在 `SceneAimController` 的同一钩子里对 `visual.x` 做平滑。注意原版已有纵向 1/4 缓动（`Camera.as:219-222`），**只缺横向**。
- **A/B 测法**：记录“按键到画面开始移动”的帧数、速度阶跃后的位置曲线、以及帧时（应不变）；主观只判两件事：起步/刹车是否更顺、长距离移动是否“跟不上”（这正是 30fps 下阻尼最容易翻车的地方）。
- **失败判据**：输入延迟 >2–3 帧、跑动/闪避手感变化、瞄准跟随偏移、碰撞/跳跃落点感知变化 → 任一条即停。**注意**：阻尼会降低每帧位移（有利于 judder），但在 **smoothing 关闭**时会增加“慢速爬行”的可见时间；因此③优先与①一起评估。
- **回退**：开关即可。

### 方案 ④（零渲染改动）：把默认窗口变成 scaleV=1

- **改哪里**：不改代码——`World.zoom100`（`World.as:210,602-613`，选项页 `PipPageOpt.as:594-615`）打开时 `isZoom=0` → `scaleV=1`。1280×720 窗口下就是 1:1 采样，**重采样彻底消失**；代价是可视世界区域从 1920×1034 降到 1264×681（每轴 2/3，面积 44%），即“更近的视野”。
- **A/B**：同路线在两个窗口 × `zoom100` 开/关 四组合下各 20s；指标：帧时（应基本不变）+ 主观 + “可视距离是否影响战斗”（可用 CS 0.9.8 的 aim-look 弥补远视野）。
- **失败判据**：视野太小影响交战/探索被用户否决；边界 `ram*` 表现异常。
- **回退**：选项页改回。（这一项是**唯一能确定性地消除 (b)** 且零渲染成本的做法。）

### 已否定、不要再做的相邻路线

- 每帧半分辨率整景合成 / 隔帧重画（更慢，且 P95 与长帧恶化）【experiments/quality-and-dense-enemies-20261101.md:16-26,82-88】；
- 地形 0.5/0.75 分辨率缓存（画面变软、无收益）【同上:50-58】；
- 每帧切 `stage.quality`（57.391/55.257/60.726ms，明显更慢）【同上:34-40】；
- 整层/物体/四层呈现节点缓存（无收益或更慢）【experiments/camera-optimization-followup-20261101.md:31-37】；
- 屏幕像素增量缓存（小窗 2.9%、大窗更慢）【同上:36-37】；
- `cacheAsBitmapMatrix`（桌面不支持）【experiments/lossless-cut-survey-20261101.md:20】。

---

## 5. 必答 5：现在能不能判定？最小诊断方案

### 5.1 逐项证据现状

| 候选成因 | 现有证据 | 判断 |
|---|---|---|
| (a) 30fps 低帧率本身 | 真实游玩 26.19 FPS 均值、移动窗 25.84 / 静止窗 28.27；走动 50.6ms vs 静止 39.4ms（+11.2ms），且“窗口内位移与帧时线性相关仅 0.033” | **确定存在**，是底噪；但注意：真实游玩里“移动”本身也伴随更多战斗/预绘，+11.2ms 不能全归 30Hz 步进【experiments/camera-light-warm-lead-20261029.md:56-60】【experiments/stutter-investigation-20261103.md:31-32,39】 |
| (b) 最近邻采样 | 只在 `scaleV≠1` 时发生；2/3 缩放下本仓反复测到采样相位差异（局部 fill 需 +1 源像素才 12/12 精确；换算系数 0.999404898）与真实图 1911–2465 像素差；基准实测 0.6583 下双线性可把 4 层合成从 13.55→20.70/2.08→6.02ms 且 1:1 下双线性零成本零变化 | **确定存在但仅在 1264×681 类窗口**；2048×1123 下 `scaleV=1`，**不存在**（也因此 smoothing 在该窗口连“效果”都没有，是个天然对照）【experiments/camera-pacing-phase-20261029.md:56,60-62,70-76】【experiments/camera-combat-window-lead-20261029.md:46】【同目录 blur-benchmark-lead.md:26-29,53-55】 |
| (c) 相机整数截断 | `X/Y/vx/vy= int`；容器平移无震屏时为整数；`scaleV=1` 时正好落在像素网格 | **基本可排除**（最多 1 屏幕像素，30fps 下不可察）【Camera.as:24-26,218,236,285-286】 |
| (d) 帧时抖动/长帧 | 5143 帧里 38 次 >100ms、最大 242ms；“29 个长帧仅 9 个邻近 GC（31%）”；长帧成簇且与预绘/场景切换/环境有关 | **确定存在，是偶发分量**（连续感被切断的地方）【experiments/stutter-investigation-20261103.md】【design/stutter-optimization-plan-20261103.md:23】【experiments/camera-light-warm-lead-20261029.md:52,60】 |

所以 §0 的结论句成立：**(c) 可排除，(a)+(d) 常驻，(b) 只在 scaleV≠1 的窗口叠加，缺的是“同路线 + 记 scaleV + smoothing 开/关”的对照。**

### 5.2 最小诊断（一次 1–2 分钟被动记录，几乎不改代码）

目标：在一轮里同时拿到判别四者所需的全部量。可直接复用本仓已有的被动记录设施（ModLoader 的 FrameRecorder 实测已能给出逐帧间隔与长帧分布，见 `experiments/camera-light-warm-lead-20261029.md:56`；探针可用 `ENTER_FRAME` 优先级 1000/-1000 的既有写法，例如 `src/ContinuousSceneProbe.as:82`、`src/ContinuousSceneMotionProbe.as:120-124`）。

1. **记录（每帧一行，写文件或内存环形缓冲）**：`stageWidth/Height`、`cam.isZoom`、`cam.scaleV`、`visual.scaleX/Y`、`cam.vx/vy`（int）、`quakeX/Y`、`gg.X/Y`、`getTimer()` 差、`grafon.sceneResident/sceneMisses/sceneRedraws`、`presenter.stats().presented/lastFallback`。这能直接回答“用户看到的到底是不是 scaleV≠1、呈现器有没有在跑”。
2. **同一条 20s 路线跑两次窗口**：1264×681 与 2048×1123（两个都是本仓已验证可启动的尺寸）。若小窗明显更“毛”、大窗只剩“跳”，则 (b) 是小窗主因。
3. **同实例内 smoothing 开关**：模组层遍历 `grafon.sceneSurfaces()` 设 `bitmaps[i].smoothing=true`，A/B 各 10s，记录**帧时（基准预期 +4～7ms，仅在 scaleV≠1 时）与主观**。这是判别 (b) 的决定性一步：smoothing 让画面明显变稳 → (b) 成立；完全无感 → (b) 不是主因（此时只可能是 (a)/(d)）。注意在 2048×1123（scaleV=1）下“无感”是**理论预期而非结论**——这个组合就是天然对照组。
4. **速度阶梯**：在同一窗口下用探针把相机以约 0.25 / 1 / 3 屏幕 px/帧 三级匀速平移（各 5s）：
   - 慢速最“毛/沸腾”、快速只是“跳” → **(b)**；
   - 慢速也很干净、快速才顿 → **(a)**；
   - 顿挫与长帧同时出现（见第 5 步）→ **(d)**。
5. **长帧标记**：跑一次真实游玩（FrameRecorder 即可），在画面角落叠一个“本帧 >50ms”的计数/闪标（探针画一个 1px 边框即可）；若用户感觉“卡”的时刻与标记重合 → (d)；若全程“一直有点毛”而标记很少 → (a)/(b)。
6. **（可选，最客观）**：在 3 个固定相机位置各截 1 帧（`BitmapData.draw`，一次约 10–20ms，只截 3 次），对比 smoothing 开/关的块边 ±2 列像素：若出现新增的 1px 线缝 → gutter 近似问题成立，方案①需要缩小到非块边的层或改用中心 320 的 fill（`SceneEventBitmapFill` 路径）。

判据汇总：**先看用户实际窗口的 `scaleV`**——若是 1（2048×1123 类），(b) 在物理上不存在，粗糙只能是 (a)/(d)，此时不要动渲染（smoothing 无变化、blur 不可能负担），直接走帧时/长帧路线；若是 0.6583（默认小窗那类），再比“smoothing 开关的观感改善”与“窗口切换的观感改善”哪个大——smoothing 明显更稳就从 (b) 下手（方案①，接受 4～7ms），否则优先方案④（零成本消灭重采样）或先做 (a)/(d)。

---

## 6. 证据索引与边界

**本轮直接读过的源码**（均在 `D:\Program Files\Steam\steamapps\common\Remains` 下）：

- `game-reference/decompiled/1.02/src102/scripts/fe/inter/Camera.as`（1.02 相机原版）
- `mods/ContinuousScene/build/generated/scripts/fe/inter/Camera.as`（2026-10-19 全量构建源的 Camera：sceneLarge/1920×1000 + calc 内 sceneTick）
- `mods/ContinuousScene/build/generated/vertical-camera-band-20261023/source/fe/inter/Camera.as`（2026-10-23 已部署的纵向镜头带源；最接近 A9B3 谱系，`visual.x/y`+sceneTick 在 366-368、Y 带钳制在 294-295）
- `game-reference/decompiled/1.02/src102/scripts/fe/World.as`（cellsX/Y=48/25、zoom100→isZoom、quake ±20、resizeScreen）
- `game-reference/decompiled/1.02/src102/scripts/MainFE.as:20-21`（noScale/TOP_LEFT）
- `game-reference/decompiled/1.02/src102/scripts/fe/inter/PipPageOpt.as:594-615`（zoom100 切换 setZoom(0/2)）
- `mods/ContinuousScene/build/generated/envkey-cache-20261102/host-export/scripts/fe/graph/Grafon.as`（A9B3 的 Grafon 导出源）
- `mods/ContinuousScene/src/SceneEventBitmapFill.as`、`ScenePresentationCoordinator.as`、`SceneAimController.as`、`SceneRasterPresentation.as`、`SceneRasterRowsPresentation.as`、`native/scene-crop-presentation.as.inc`、`tests/SceneBackgroundCompositeProbe.as`、`tests/SceneEmptyTerrainProbe.as`
- `mods/ContinuousScene/design/scene-combat-camera-optimization-plan.md`（§3 原文）、`design/runtime.md`、`design/stutter-optimization-plan-20261103.md`、`state/journal.md:14`
- 报告（相对 `mods/ContinuousScene/knowledge/`）：`experiments/quality-and-dense-enemies-20261101.md`、`experiments/lossless-cut-survey-20261101.md`、`experiments/camera-optimization-followup-20261101.md`、`experiments/camera-scale-coverage-20261029.md`、`experiments/camera-pacing-phase-20261029.md`、`experiments/camera-iteration-review-20261101.md`、`experiments/camera-combat-window-lead-20261029.md`、`experiments/camera-light-warm-lead-20261029.md`、`experiments/a2-current-deploy-20261031.md`、`experiments/experience-v05-20261015.md`、`experiments/lowquality-deploy-20261101.md`、`experiments/stutter-investigation-20261103.md`、`experiments/visual-neutral-budget-20261031.md`
- **同目录**：`experiments/scene-combat-camera-investigation-20261104/blur-benchmark-lead.md`（Lead 的 AIR 离线微基准；本文 §2.3/§3.2/§4①/§5 的 blur 与 smoothing 成本数字来自它，性质是离线代理）

**本文的边界**：
- 没有运行游戏/AIR、没有构建或部署、没有改任何 `src/`、`release/`、`game-reference/` 文件。
- 2048×1123 的 `scaleV=1` 是**公式代入 + 本仓大窗实测（1904×1041/2032×1084 均为 scale1）**的一致推论，尚未在该尺寸上直接回读 `scaleV`——这正是 §5.2 第 1 步要补的一行日志。
- `BlurFilter` 与“双线性 4 层”的数字现在有**直接测量**（离线代理，`blur-benchmark-lead.md`），§3.4 里的“游戏内组合开销/2048 捕获外推”仍是**外推**，读数时请分开。
- smoothing 在**游戏内**的真实增量、以及“平滑是否采到 gutter”仍无游戏内直接测量，§2.3/2.4 的相应结论已标【推测】。
