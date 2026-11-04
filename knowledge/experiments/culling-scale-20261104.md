# 剔除包围盒解析式缩放（SceneObjectCulling event-tracked-2）：实施与证据（2026-11-04）

被测技能：remains-runtime-debug（调查）/ remains-mod-build（编译）/ remains-release-gate（门禁）
工作区：`D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene`

## 0. 本轮基线（未改动）

| 对象 | 指纹 |
|---|---|
| 根宿主 `pfe.swf` | `91F8E10D…`（子弹空间分桶，2026-11-04 18:50 部署） |
| CS release | `D04CD26A…`（0.9.9 瞄准 v2） |
| `scene.xml` | `1CEA74E2…` |

本轮**只改模组层两个类**，宿主与 `scene.xml` 未动。

## 1. 改了什么

`src/SceneObjectCulling.as` / `src/SceneCullEntry.as`：

1. **解析式包围盒缩放**。`measure()` 额外缓存"单位缩放下的局部盒" `base*`；此后若某帧的变换满足
   `rotation==0`、`sx!=0`、`sy!=0`、有限、且上次记录 `rotation==0`，则新相对盒由
   `base*×scale` 直接算出（负缩放交换左右/上下边界），**不再调用 `child.getBounds(visual)`**。
   数学依据：显示对象只缩放不改旋转时，其子树局部几何不变，`visual` 空间轴对齐盒是局部盒的仿射像。
2. **摊销重测**：每帧只重测 1 个条目（`refreshBase()`，轮转游标），用来界定"子节点自身动画导致局部盒变化"的缓存陈旧；它**只更新包围盒与 base，不写 `e.x/e.y`**，所以同帧移动的对象仍然会在主循环里被重新判定。
3. **主循环 `for each` → 下标 `for`**（`tracked` 是 `Vector.<SceneCullEntry>`）。
4. `stats()` 版本 `event-tracked-1` → `event-tracked-2`，新增 `scaleSkips`（走算术路径的次数）、`baseRefreshes`（摊销重测次数）；`boundsReads` 语义不变（只统计真正的 `getBounds`）。

未改：可见性归属（游戏拥有 `child.visible`，模组只写 `wrapper.visible`）、lurk/念力例外、SATS 截图全显示/恢复、`empty` 保守可见、包装层回填与 `clear()` 还原。

## 2. 证据

### 2.1 确定性差分夹具（离线、无游戏、无存档）

`build/culling-scale-checks.py` → 冻结生产源码副本 → mxmlc → 独立 AIR 应用（`remains.cs.cullchecks.<uuid>`，`visible=false`）→ 结果 JSON。

**45/45 通过**：既有 `SceneCullingChecks` 23 项全过（回归），新 `SceneCullingScaleChecks` 22 项全过（差分）。

新夹具的核心是**独立 oracle**：每帧对每个根节点重新 `getBounds(visual)` 并用同一条 hide 公式算出期望可见性，与生产实现逐帧逐根比对，任何"缓存盒错、镜像错、旋转后复用、平移后漏判"都会变成可见性不一致而不是静默的画面跳动。

关键读数（`mixed-scene`，90 帧 / 25 根 / 相机每 7 帧移动）：

| 指标 | 值 |
|---|---|
| 变换发生次数 | 1897 |
| 算术路径次数（不做 getBounds） | 920（48.5%） |
| `getBounds` 总数 | 392 → **4.36/帧**（其中 1/帧是摊销重测） |
| 旧实现同场景应为 | ≈21/帧（每次变换一次） |
| 不一致 | **0**（90 帧 × 25 根逐帧比对） |

> 说明：合成场景里旋转变换约占 6%，它们必须回落到 `getBounds`，所以算术路径占比不是 100%；真实场景（`bulletgrid-gridlive` 实测 35 读取/帧、1578 个跟踪条目）以单位左右转向为主，算术路径覆盖的是这一类。

其余断言：镜像（非对称偏心美术）逐帧与 oracle 一致；旋转改变必须 measure（`boundsReads≥1`）且清回 0 后复用缓存；`scaleX` 0/0.001/1/-1/0/2 序列与 oracle 一致（除零不进缓存）；交替传送到 9000px 外**当帧即隐藏**（含摊销重测命中的那一帧）；美术在静止变换下变宽后，一次扫过即刷新，随后的缩放判定按新盒；空根永不隐藏；`unitsOnly` 切换后其它层还原且判定仍与 oracle 一致。

### 2.2 产品编译与归因（未部署）

- 候选：`build/generated/cull-scale-20261104/product/ContinuousSceneMod.swf` = **`6A538E83…`**，33,175 字节，13 个类，无 `tests.*`/`Checks`/`Probe`/`fe.*` 泄漏；从产物字节码里导出 `SceneObjectCulling`，确认含 `applyScale`/`refreshBase`/`baseLeft`/`event-tracked-2`（证明改动确实进了产物，而不只是源码）。
- 归因（`build/cull-scale-attribution.py`）：把并行会话正在改的 3 个瞄准文件钉到 HEAD 后编译"控制产品" = `E6567000…`，与候选**逐类导出比对**，**只有 `SceneCullEntry` 与 `SceneObjectCulling` 不同**；其余 5 个抽查类（含 `ContinuousSceneMod`、`SceneAimController`）导出字节完全相同。
- 另核：本地编译管线对 `release` 的 7 个抽查类导出与已部署 `D04CD26A` **完全一致**（`controlSize==releaseSize==32677`）；说明控制产品与正式发布在类级字节码上等价，容器哈希差异来自编译器非确定性。

### 2.3 未主张

- **不主张整帧收益**。全屏 2048×1123 实机 `continuousSceneHandlerMs` 均值 1.95ms、`activityMs` 0.538ms、`dtMs` 均值 47ms；这次省的是"每帧几十次 `getBounds`"，量级在零点几毫秒，且从未做宿主/整帧配对计时。
- **不主张解决探索长帧**。见 §3。

## 3. 顺带核清的事实：探索卡顿不是"首次加载敌人"

用户怀疑"首次加载敌人造成额外卡顿"。本轮用代码与既有实机计数核对，结论是**不成立**：

1. **敌人在进图时就全部实例化了**。`Location.setObjects()` → `createUnit()` → `Unit.create()`（构造里 `initBlit()` 从 `getSpriteList` 取共享 SpriteSheet、`Weapon.create`、`addVisual()` 挂层），即 README 所写"全图敌人、物品、碰撞在进入前生成并常驻"。走近敌人不构造实体、不拆 SWF、不建位图。
2. **音效/音乐不是首播代价**。`Snd.initSnd()/loadMusic()` 在启动时把所有 `music/*.mp3` 与 `sound*.swf` 里的 Sound 全部预加载；`playMusic`/`ps` 只在 `bytesLoaded==bytesTotal` 时才播。
3. **实机计数与"首次接触"无关**：`knowledge/experiments/evidence/bulletgrid-gridlive-combat-n1/storage/result.json`（1300 帧）：`activity` 每帧 `woke` 最大值为 **1**（预算生效，66 帧各唤醒 1 只，无成批拉活）；`activityMs` 均值 **0.538ms**、最大 5ms；`culling.boundsReads` 全程 25–55/扫描帧，**没有**随交战出现的尖峰；15 个 ≥90ms 长帧的 `activityMs` 是 0–2ms。
4. **长帧主因仍是内存回收**：`long-frame-memory-20261104.md` 三次运行 85%/92%/100% 的 ≥100ms 帧与 >1MB 的 `totalMemory` 回落同帧（中位 50–72MB），触发源是地块缓冲约 18MB/s 且不逐出的分配量。
5. 因此"走近敌人时的顿挫感"更可能来自三件事的叠加：进入交战那一帧附近**同时**在分配（弹体/枪口/命中特效/弹痕）+ 相机换窗口触发新地块分配 → 把回收提前；以及多个单位同时转向/唤醒带来的几百微秒级脚本增量。前者要动宿主地块调度（"异步补块+占位"），已超出本模组当前范围，且此前"逐出+缓冲复用"实测负结果（最大帧 171→568ms）。

## 4. 风险与边界

- **缓存陈旧**：`base` 只会在该条目的变换变化或轮到摊销重测时更新；一次全扫 = `tracked` 帧（实机 1578 条 ≈ 53s@30fps）。陈旧的影响被判定余量吸收：hide 阈值是 `camRight+320+240 = camRight+560`，即物体包围盒边缘要越过视口右侧 560px 才隐藏，而单位美术尺寸远小于 560px，所以陈旧不会造成"屏内物体被隐藏"的画面缺失。
- **旋转**：任何一帧 `rotation!=0` 都回落到 `getBounds`（缓存也作废），旋转物体不会用错缓存。
- **零/非有限缩放**：`sx==0` 或 `sy==0` 时也回落 `getBounds`，且不写缓存（避免除零污染）。
- **`empty`**：仍按 `getBounds` 的 `width<=0&&height<=0` 判断，空盒永不隐藏。
- **并发**：本轮实施期间另一个 DSH 会话（`session-9f1f58e1…`）正在改 `ContinuousSceneMod.as` / `SceneAimController.as` / `tests/SceneAimChecks.as`（瞄准 V3）。本轮所有写入都在其认领**之外**的文件，产品候选用"钉住其 3 个文件到 HEAD"的方式构建，未覆盖其工作、未改 `release/`。

## 5. 复现与门禁

```powershell
cd mods/ContinuousScene
python build/culling-scale-checks.py     # 45/45，独立 AIR，无游戏
python build/cull-scale-product.py       # 候选产品 6A538E83…
python build/cull-scale-control.py       # HEAD-only 控制产品 E6567000…
python build/cull-scale-attribution.py   # 逐类归因：只有 2 个剔除类不同
```

回退：本改动只在源码；`git -C mods/ContinuousScene checkout -- src/SceneObjectCulling.as src/SceneCullEntry.as` 即回到 `event-tracked-1`（若已部署则需重新构建 + 重启）。

## 6. 部署状态（已随合并构建上线）

**已上线**：并行会话在 23:22 把 CS 升到 0.9.10 并部署为 **`A4F4C8ED…`**（前值 `D04CD26A`，备份 `build/backups/ContinuousSceneMod-0.9.9-D04CD26A-before-aimv3-20261104-232209.swf`）。按用户选择，本会话不再单独部署（原候选 `6A538E83…` 与部署脚本 `build/generated/cull-scale-20261104/deploy_cull_scale.py` 保留备查）。

上线证明不是"源码在树里应该被带上"，而是**类字节码相等**：

| 来源 | `SceneObjectCulling` 导出哈希 | `SceneCullEntry` 导出哈希 |
|---|---|---|
| 本轮候选 `6A538E83`（通过 45/45） | `F59A2915…` | `CDCB935B…` |
| **已部署 `A4F4C8ED`** | **`F59A2915…`** | **`CDCB935B…`** |
| 0.9.9 正式版 `D04CD26A`（旧实现） | `B14DDD97…` | `7B9729CB…` |

源码哈希链同样闭合：夹具冻结副本与产品构建输入同为 `SceneObjectCulling.as B62731BA…`、`SceneCullEntry.as ACC0753E…`。核验回执 `state/culling-scale-verification-20261104.json`。

**生效条件**：需重启游戏（运行中的 AIR 已加载旧 SWF）。**剩余门禁**：尚未做"已部署字节"的实机运行（本改动只写包装层 `visible`，判定逻辑已被离线 oracle 全覆盖；实机复核建议与下一次游玩一起做，重点看远处单位/道具在视口边缘是否出现突然消失或残影）。
