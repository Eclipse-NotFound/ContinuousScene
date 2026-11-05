# 来自 RealisticVision 侧：墙拓扑事件尖峰的归属与建议（2026-11-04）

> 本报告由 RealisticVision（RV）维护者撰写，**直接交付 ContinuousScene（CS）维护者**。
> 数据来自 RV×CS 同开的隔离测量。RV 侧已把自己那部分优化完（见 §4），剩下的主要在
> CS 侧，故按工作区规则以报告形式反馈，**未改动 CS 的 src/release/config**。
>
> 可复用的公共结论另存：
> `shared-knowledge/knowledge-validation/experiments/wall-topology-event-spike-2026-11-04.md`
> 与 `shared-knowledge/rendering/discoveries/mod-object-layer-wrapping-2026-11-04.md`。

## 1. 现象

在 `sceneLarge` 连续大图（random_mane 240×125）里，**一次墙拓扑变化**——墙被破坏、
或门跨过"实心"阈值（瓦片 `opac` 跨越 1.0）——会使那一帧多花 **≈ 100–130ms**。
玩家侧感受就是"打墙/开门时顿一下"。

## 2. 实测归属

同一隔离沙箱、同一风暴脚本、同一地图，只切 RV `enabled` 0/1，交错运行（共 11 次独立
运行、每次 22–32 个事件）：

| 臂 | 每事件中位尖峰 | 均值 |
|---|---|---|
| RV 开 | **+109 / +101** | 114 / 101 |
| RV 关 | **+72 / +70** | 78 / 78 |

⇒ **RV ≈ 34ms，其余 ≈ 70ms 归原生 + CS。**（同臂重复差 ≤8ms。）

RV 的 34ms 内部已被拆到段：墙几何重建 8–16ms，其余是 FOV 重算、雾重画、墙面膜重建、
单位分类的叠加。**CS 侧那 70ms 未拆**——本报告只证明它不在 RV 里。

RV 侧还做了"逐项关闭"对照（关单位遮罩 / 武器遮罩 / 特效裁剪 / `cacheAsBitmap` /
整层雾 / opac 触发的 FOV 重算），**六项全部无效**；而"RV 完全惰性（`mode=vanilla`）"
会回落到 RV 关闭水平 ⇒ 这 34ms 是"活动视效 + 常规分段"的叠加，无单点元凶。

## 3. 给 CS 的两个可查点（按可疑度）

1. **chunk 重绘的粒度**：拓扑变化后，CS 会 `sceneApply`/`sceneRender` 相交 chunk。
   当前交互是否**以"每个相交 chunk 一整块 320px 重绘"**为单位？如果是，一次墙破坏只
   影响极小的像素，却可能触发多个 chunk 的整块重绘（含 `clone()` 新的 BitmapData）。
   可查：单次事件的 `sceneRender` 调用数、每次 `drawLoc` 的耗时、以及 `nativeBuffers
   .clone()` 的分配量（GC 侧）。
2. **与原生 relight 的叠加**：墙 `opac` 变化会让原生 `loc.isRelight/isRebuild` 触发
   整层重新照亮；CS 若在同一帧又重绘 chunk，两者叠加。可查：把 CS 的 chunk 重绘人为
   延后 1 帧 / 合并到下一帧，是否能把尖峰削平（只作诊断，不改语义）。

## 4. RV 侧已经做完的（供你判断"剩下的确实不在 RV"）

- **阶段 A（稳态）**：`fov` 全清→增量、墙角循环→分块桶、分类表→代次戳、墙重填→视口化。
  实测 RV 自报 AS3 **12.63 → 9.95 ms/帧（−21.2%）**，已部署（现版本含该项）。
- **事件侧**：墙/地板掩膜几何改"每行 Shape + 只重画脏行"，离线 **8/8** 掩膜逐像素等价，
  但上机只省 **≈5ms/次**（噪声内）⇒ **未部署**，因为重建的真正成本在 O(map) 的
  `getTile` 扫描与墙表维护，不在掩膜几何。

## 5. 复现方式（用你们自己的夹具也能做）

- 臂定义：窗口内每 10–45 帧，把玩家周边 3 块实心墙 `tile.opac` 在 1↔0 翻转（`phis`
  同步），记录翻转帧号。
- 归因口径（对第 k 次翻转）：
  `spike = max(frameInterval[k-1..k+3]) − median(frameInterval[k-10..k-6])`，
  对多次取中位；**同一批次内交错**不同臂，避免跨批次漂移。
- 关键前提：游戏读的是 `mods/loader-manifest.txt`（不是 `supported-mods.txt`），
  新加的驱动模组必须用 `RemainsModLauncher --root <副本> --all --no-ui --report <副本>/selection.json`
  重新生成清单，否则不会被 requested（我们的第一轮空跑就是这个原因）。
- 环境声明：结论来自隐藏窗口、约 10fps 的沙箱；**不要把它当玩家前台绝对值**，但
  "RV 34ms / 原生+CS 70ms"的**相对结构**在同环境下稳定复现。

## 6. 附：RV 侧可提供的原始数据

- 事件尖峰报告：`mods/RealisticVision/knowledge/experiments/2026-11-04-wall-rebuild-spike.md`
- 测量装置与臂表：`mods/RealisticVision/build/cs-rv-20261104/`（`run_grid.py` 的
  Z/W/Y/V/E*/C1 臂、`analyze_storm_robust.py`）
- 探针（单项关视效 / 墙重建分段）：`mods/RealisticVision/build/csopt-20261104/out/probe-*.swf`
  （**探针不是可部署产物**）
