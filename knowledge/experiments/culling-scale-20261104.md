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

`src/SceneObjectCulling.as` / `src/SceneCullEntry.as`（`event-tracked-3`）：

1. **解析式包围盒缩放**。`measure()` 额外缓存"单位缩放下的局部盒" `base*`；此后若某帧的变换满足
   `rotation==0`、`|sx|,|sy|>=1e-3`、有限、且上次记录 `rotation==0`，则新相对盒由
   `base*×scale` 直接算出（负缩放交换左右/上下边界），**不再调用 `child.getBounds(visual)`**。
   数学依据：显示对象只缩放不改旋转时，其子树局部几何不变，`visual` 空间轴对齐盒是局部盒的仿射像。
2. **父链守卫（`bind()` 一次性）**：缓存盒只在"层链无平移、无旋转、无斜切"时才是帧不变的（均匀缩放会被 base 吸收）。绑定层时检查 `layer.parent===visual && matrix.b==0 && c==0 && tx==0 && ty==0`，任一不满足即 `fastPath=false`，整个特性退回逐次 `getBounds`。这样正确性不再依赖"游戏从不给 `visObjs` 设变换"这一外部事实。
3. **摊销重测**：每帧只重测 1 个条目（`refreshBase()`，轮转游标），用来界定"子节点自身动画导致局部盒变化"的缓存陈旧。两条不变式：**不写 `e.x/e.y/sx/sy/rotation`**（主循环用"位置变了"决定是否重判，这里写入会吞掉同帧位移）；**清 `e.checked`**，让刷新后的盒在当帧就被用于判定，而不是等下一次相机/变换变化。
4. **主循环 `for each` → 下标 `for`**（`tracked` 是 `Vector.<SceneCullEntry>`）。
5. `stats()` 版本 `event-tracked-1` → `event-tracked-3`，新增 `scaleSkips`（走算术路径次数）、`baseRefreshes`（摊销重测次数，**每帧复位**，与 `visits`/`boundsReads` 同口径）、`fastPath`（守卫结果）；`boundsReads` 语义不变（只统计真正的 `getBounds`，因此现在每帧至少含 1 次刷新读）。

未改：可见性归属（游戏拥有 `child.visible`，模组只写 `wrapper.visible`）、lurk/念力例外、SATS 截图全显示/恢复、`empty` 保守可见、包装层回填与 `clear()` 还原。

## 2. 证据

### 2.1 确定性差分夹具（离线、无游戏、无存档）

`build/culling-scale-checks.py` → 冻结生产源码副本 → mxmlc → 独立 AIR 应用（`remains.cs.cullchecks.<uuid>`，`visible=false`）→ 结果 JSON。

**48/48 通过**：既有 `SceneCullingChecks` 23 项全过（回归），新 `SceneCullingScaleChecks` 25 项全过（差分）。

新夹具的核心是**独立 oracle**：每帧对每个根节点重新 `getBounds(visual)` 并用同一条 hide 公式算出期望可见性，与生产实现逐帧逐根比对，任何"缓存盒错、镜像错、旋转后复用、平移后漏判"都会变成可见性不一致而不是静默的画面跳动。断言先报不一致、再报帧数，避免"帧数失败"掩盖真实差异。

关键读数（`mixed-scene`，90 帧 / 25 根 / 相机每 7 帧移动 / 含"同帧移动+缩放"分支）：

| 指标 | 值 |
|---|---|
| 变换发生次数 | **1602**（17.8/帧） |
| 算术路径次数（不做 getBounds） | **879（54.9%）** |
| `getBounds` 总数 | **406 = 4.51/帧**（其中 90 次是摊销重测、25 次是首次测量，其余为旋转/零轴回落） |
| 旧实现同场景应为 | 25 + 1602 = 1627 次 ≈ **18.1/帧** |
| 不一致 | **0**（90 帧 × 25 根逐帧比对） |

> 说明：合成场景里旋转变换与"移动+缩放"分支会让一部分变换必须回落到 `getBounds`，所以算术路径约 55%；真实场景（`bulletgrid-gridlive` 实测 35 读取/帧、1578 个跟踪条目）以单位左右转向为主，算术路径覆盖的正是这一类。

其余断言：**镜像场景可翻转**（美术偏在根左侧 −1500..−1420，`scaleX=+1` 时在视口外、`−1` 时镜像到 1420..1500 进视口，逐帧与 oracle 比对并断言判定真的翻转 ≥6 次）；旋转改变必须 measure（`boundsReads≥1`）且清回 0 后复用缓存；`scaleX` 0/0.001/1/−1/0/2/0.0005/NaN 序列与 oracle 一致（除零与 NaN 都不进缓存）；交替传送到 9000px 外**当帧即隐藏**（含摊销重测命中的那一帧）；**层带平移时守卫关闭快速路径**（`fastPath=false`、`scaleSkips==0`）且判定仍与 oracle 一致；美术在静止变换与静止相机下变宽后，**当帧**就被重新判定；空根永不隐藏；`unitsOnly` 切换后其它层还原且判定仍与 oracle 一致。

### 2.1b 变异测试（证明夹具不是空转）

`build/culling-scale-mutations.py`：把 4 种真实缺陷注入源码副本，各自编译成独立 AIR 应用运行，要求**必须失败**且**由指定断言报错**。基线（未变异）同时通过。

| 注入的缺陷 | 期望报错 | 实测 |
|---|---|---|
| `applyScale` 缩放盒但不换边（镜像错） | `transform-remeasured` / `mirror-matches-oracle` | 检出（既有夹具先抓到 `transform-remeasured`） |
| `refreshBase` 刷新盒但不清 `checked`（当帧不重判） | `refresh-rededicates-same-frame` / `art-change-not-redecided` | 检出（`art-change-not-redecided`） |
| `canFastScale` 去掉零轴/极小/NaN 守卫（除零进缓存） | `zero-axis-oracle-agrees` | 检出 |
| `bind()` 父链守卫恒不触发 | `layer-guard-disables-fast-path` | 检出 |

结论：镜像、零轴、守卫、刷新重判四类错误都能被现有断言抓住；不是"两边同时错"的空转。

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

- **缓存陈旧**：`base` 只会在该条目的变换变化或轮到摊销重测时更新；一次全扫 = `tracked` 帧（实机 1578 条 ≈ 53s@30fps）。刷新时**同帧重判**，所以"美术变化后判定不更新"的老缺口也一并消失；即便漏一轮，判定余量也吸收误差：hide 阈值是 `camRight+320+240 = camRight+560`，物体包围盒边缘要越过视口右侧 560px 才隐藏，而单位美术尺寸远小于 560px。
- **父链假设**：`bind()` 一次性守卫（层必须是 `visual` 的直接子节点且无平移/旋转/斜切），不满足即整特性退回测包围盒；在真实宿主里 `visObjs` 都是 `visual` 下 `new Sprite()` 的恒等层，守卫保持 `fastPath=true`（夹具 `mixed-scene` 断言其为 true，另用"层带平移"的世界断言其转 false 且判定仍与 oracle 一致）。
- **旋转**：任何一帧 `rotation!=0` 都回落到 `getBounds`（缓存也作废），旋转物体不会用错缓存。
- **零/极小/非有限缩放**：`sx==0`、`|sx|<1e-3`、NaN/Inf 都回落 `getBounds` 且不写缓存（避免除零/溢出污染）；变异测试证明去掉这条守卫会被夹具抓住。
- **`empty`**：仍按 `getBounds` 的 `width<=0&&height<=0` 判断，空盒永不隐藏（空是缩放不变量，算术路径不会把它改错）。
- **`suspended`（SATS 截图）**：`suspendForCapture`/`resumeFromCapture` 未改动，期间不调用 `update`，新路径不介入。
- **`forget()` 的 tail-pop 与轮转游标**：游标只在"其余所有 `tracked` 变更点之后"被使用，且每次用当次长度取模；尾元素回填只改变轮转次序，不影响安全。
- **统计口径**：`boundsReads` 现在每帧含 1 次刷新读，跨版本比较不能直接对；`scaleSkips`/`baseRefreshes` 都是每帧复位。
- **并发**：本轮实施期间另一个 DSH 会话（`session-9f1f58e1…`）在改 `ContinuousSceneMod.as` / `SceneAimController.as` / `tests/SceneAimChecks.as`（瞄准 V3）。本轮所有写入都在其认领**之外**的文件；第一版产品候选用"钉住其 3 个文件到 HEAD"构建（未覆盖其工作），其部署后经类哈希证明带着本改动上线。

## 5. 复现与门禁

```powershell
cd mods/ContinuousScene
python build/culling-scale-checks.py     # 48/48，独立 AIR，无游戏
python build/culling-scale-mutations.py  # 4 种注入缺陷必须被指定断言抓住
python build/cull-scale-product.py       # 第一版候选 6A538E83…（线上字节即此版）
python build/cull-scale-control.py       # HEAD-only 控制产品 E6567000…
python build/cull-scale-attribution.py   # 逐类归因：只有 2 个剔除类不同
python build/generated/cull-scale-20261104/deploy_merged.py --dry-run --expect-release <当前 release>  # 合并构建 41D61E59…
```

回退：本改动只在源码；`git -C mods/ContinuousScene checkout -- src/SceneObjectCulling.as src/SceneCullEntry.as` 即回到 `event-tracked-1`（若已部署则需重新构建 + 重启）。

## 6. 部署状态（两代：线上 v2，树内 v3 待一次单类升级）

**线上（v2）**：并行会话在 23:22 把 CS 升到 0.9.10 并部署为 **`A4F4C8ED…`**（前值 `D04CD26A`，备份 `build/backups/ContinuousSceneMod-0.9.9-D04CD26A-before-aimv3-20261104-232209.swf`）。按用户选择，本会话不再单独部署第一版。

上线证明不是"源码在树里应该被带上"，而是**类字节码相等**：

| 来源 | `SceneObjectCulling` 导出哈希 | `SceneCullEntry` 导出哈希 |
|---|---|---|
| 第一版候选 `6A538E83`（通过 45/45） | `F59A2915…` | `CDCB935B…` |
| **已部署 `A4F4C8ED`** | **`F59A2915…`** | **`CDCB935B…`** |
| 0.9.9 正式版 `D04CD26A`（旧实现） | `B14DDD97…` | `7B9729CB…` |

**树内（v3，未部署）**：独立复核指出两处应改（摊销刷新改了盒却不重判；父链假设缺守卫），已在源码修正并加变异测试。合并构建候选 `build/generated/cull-scale-20261104/product-merged/ContinuousSceneMod.swf` = **`41D61E59…`**（34796 B）；与线上 `A4F4C8ED` 逐类比对**只有 `SceneObjectCulling` 一个类不同**（`72E5DF9A…` vs `F59A2915…`），瞄准 V3 的 `ContinuousSceneMod`/`SceneAimController` 等完全一致。部署命令：

```powershell
cd mods/ContinuousScene
python build/generated/cull-scale-20261104/deploy_merged.py --expect-release A4F4C8ED4C3158B2721EAC8086A266AA1A43312DB3F53B19C275B91857B2CA3B
```

（脚本会重编产品 → 重跑 48 项夹具 → 校验无 tests/Checks/Probe 泄漏与字节码标记 → 备份 → 原子替换 → 回读；任一步不符即拒绝。**需重启游戏**。）

**生效条件**：需重启游戏（运行中的 AIR 已加载旧 SWF）。**剩余门禁**：尚未做"已部署字节"的实机运行（本改动只写包装层 `visible`，判定逻辑已被离线 oracle + 变异测试覆盖；实机复核建议与下一次游玩一起做，重点看远处单位/道具在视口边缘是否出现突然消失或残影）。
