# ContinuousScene 开火移动与多实体性能优化可执行方案

> 日期：2026-11-02（同日执行并更新状态）  
> 适用版本：Remains 1.02，ContinuousScene 0.9.5+，宿主 A9B39CC7  
> 目标场景：解决“开火叠加镜头移动时卡顿严重”及“加载敌人数量增多时卡顿大幅加剧”问题。

---

## 0. 执行状态（2026-11-02 15:24 更新）

| 阶段 | 状态 | 结果 |
|---|---|---|
| 1.1 脱战休眠超时 | ✅ **已部署（CS 0.9.6）** | `engaged` 150 帧脱战期限 + 2200×1600 追击保护半径；`leashed` 状态允许远处受伤敌人重新休眠；stats 版本 `leash-wake-2` |
| 1.2 威胁分级节流 | ✅ **已部署（CS 0.9.6）** | 实现为**弹道走廊双盒**而非原文的视口判定（见 §2.1.2 修订说明）：弹道命中走廊（explRadius+40px）内保持立即唤醒，400px 警戒晕圈降级为预算内唤醒 |
| 1.3 震屏柔性容忍 | ✅ **已部署（CS 0.9.6）** | 呈现协调器与呈现器均容忍 \|quake\|≤25；分数平移仅在震屏激活时接受。因 Camera 平移整个世界容器（原生位图与合成节点同移），无需额外注入变换 |
| 2.1 弹痕空间剪枝 | ⛔ **无需实施——已存在于部署宿主** | 部署宿主（A9B3 谱系，冻结源 `build/generated/camera-spatial-20261101/source/fe/graph/Grafon.as`）的 `sceneRestoreMarks` 已实现 decal 空间剪枝（`sceneDecalBounds` + 视口相交跳过 + `sceneApplyRegionAction` 区域绘制）。原诊断基于过时的 `src/patches/GrafonChunks.as.inc` 快照，对正式产品无效；该 `.inc` 与部署谱系的分叉记为源码卫生债 |
| 3.1 炮塔 animate 守卫 | ❌ **已测量关闭（负结果，不部署）** | 并行会话完成要求的 GC/长帧尾部配对测量（`turret-guard-gctail-20261102`，v13 四轮配对共 6 轮零收益；休眠炮塔不调 animate，同帧 gotoAndStop 非 GC 周期有效驱动）。候选 6AC6C692 保留不部署 |

**0.9.6 部署回执**：`state/leash-v096-deployment-20261102.json`（宿主 A9B39CC7 未动；回退 = `build/backups/ContinuousSceneMod-0.9.5-1A66B1F4-before-leash-20261102-152416.swf` 覆盖 release；需重启游戏生效）。

**验证**：`leash-v096-mechanics-r2` **29/29**（原 27 项 + 新增 `engagement-expires-for-far-units`、`leashed-unit-reengages-on-approach`）；`leash-v096-issues-r1` **16/16**（含三门/边界×3缩放/固定视觉）。均登记 game-coexist，隔离运行时 + 15 入口启动器选择。**无计时声明**——削峰/减负的实际帧收益待玩家与后续配对测量反馈。

---

## 1. 现状与根因诊断回顾

根据前期对游戏源码与多轮实验数据的深入取证，当前主要瓶颈可归纳为四大相互放大的子系统缺陷：

1. **休眠状态单向泄露（脱战机制缺失）**：
   - 缺陷位置：`mods/ContinuousScene/src/NativeSceneActivity.as:41`
   - 机制：`s.records[u].engaged` 状态一旦在交火中置为 `true`，没有任何重置分支。被惊动或被流弹波及的敌人永久保持全量逻辑和动画更新，随推图与开火呈单调累积。
2. **开火威胁扩散击穿平滑预算（平滑唤醒失效）**：
   - 缺陷位置：`mods/ContinuousScene/src/NativeSceneActivity.as:30-74`
   - 机制：子弹产生的 `threats` 判定及远距声音警报直接将视口边缘本应进入 `deferred` 队列的敌人标记为 `urgent`，同帧全量唤醒，彻底瓦解了 0.9.4 的 `wakeBudget` 削峰保护。
3. **后坐力震屏与地形呈现层颠簸（Render Pipeline Thrashing）**：
   - 缺陷位置：`mods/ContinuousScene/src/ScenePresentationCoordinator.as:61`
   - 机制：开火产生的后坐力导致 `quakeX/Y != 0`，强行打破了合批呈现门禁，引发 `SceneEventBitmapFill` 在高频震动下反复执行 `clear()`（解除合批、复原 Alpha）与下一帧的 `rebuildCommands()`，造成严重的指令与对象分配抖动。
4. **历史弹痕全量无差别重放（Mark Leaking onto Chunk Baking）**：
   - 缺陷位置：`mods/ContinuousScene/src/patches/GrafonChunks.as.inc:283-295`
   - 机制：开火产生的弹痕/血迹存入全局 `sceneMarks`。镜头移动烘焙新图块时，`sceneRestoreMarks()` 未做空间相交测试，全量遍历历史弹痕，使新图块生成耗时随游戏进行持续增长。

---

## 2. 优化方案分阶段规划（Phased Implementation Plan）

本计划按照 **“改动范围自小至大、优先纯模组层、先安全再深入、每阶段独立验收”** 的原则组织：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 优化实施阶段路线图                                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ Phase 1: 纯模组层修复（ContinuousScene 模组源码）                           │
│   ├─ 1.1: NativeSceneActivity 引入脱战超时机制（解决 engaged 永久泄露）      │
│   ├─ 1.2: 约束开火威胁紧急唤醒的作用半径（防止远距流弹击穿平滑预算）        │
│   └─ 1.3: ScenePresentationCoordinator 容忍轻微 quakeX/Y 震屏（防止管线颠簸） │
│                                                                             │
│ Phase 2: 地形图块补丁层增强（patches / 生成配方）                          │
│   └─ 2.1: sceneRestoreMarks 弹痕图块空间相交过滤（阻断烘焙膨胀）            │
│                                                                             │
│ Phase 3: 宿主层长帧尾部抑制（已备候选验证与推进）                            │
│   └─ 3.1: UnitTurret.animate 同帧守卫配对长帧/GC 验证（抑制 90MB 级停顿）    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 1: 纯模组层逻辑修复与稳态保护（ContinuousSceneMod）

*此阶段完全限制在 `mods/ContinuousScene/src/` 内，无需修改游戏底层 SWF，回滚与构建代价最低。*

#### 1.1 引入脱战休眠超时机制（Leash & Disengage Timeout）
- **目标**：终结活动敌人随开火单调递增的雪崩现象，使远离玩家且丢失目标的敌人能够安全重新休眠。
- **改动文件**：`mods/ContinuousScene/src/NativeSceneActivity.as`
- **具体实施**：
  1. 在 `records[u]` 结构中增加 `disengageTick:int`。
  2. 每一帧更新时检测敌人状态：
     - 若 `u.celUnit != null`（有明确索敌目标）或最近受到有效伤害，刷新 `r.disengageTick = s.tick + 150`（脱战保护约 5 秒）。
     - 若 `s.tick > r.disengageTick` 且与玩家曼哈顿距离超出近战/威胁警戒区（如 `dx > 2200 || dy > 1600`），将 `r.engaged` 重置为 `false`。
  3. 当 `r.engaged` 恢复为 `false` 后，该单位在下一次进入非视口/非近邻区域时，正常结算为 `!active`，进入 `freeze()` 与 `sleeping` 状态。
- **安全约束**：Boss、剧情 NPC、特殊机制单位（Fraction 保护）以及带有特殊状态（眩晕、抓取、移动中机关）的实体保持原有豁免，不可被强制脱战。

#### 1.2 约束开火紧急唤醒判定范围（Strict Threat Radii）
- **目标**：保证玩家在开火时，移动扫过的视口边缘敌人依然受到 `wakeBudget` 的严格节流，不产生群体重启峰值。
- **改动文件**：`mods/ContinuousScene/src/NativeSceneActivity.as`
- **具体实施**：
  1. 区分“视口核心战斗”与“远距/边缘威胁”：
     - 只有当子弹的威胁包围盒（`threats`）与敌人 AABB 的重叠发生在**视口当前可视区域（加 120px 缓冲）内**时，才赋予 `threatened` 紧急标记；
     - 处于视口边缘外或仅被枪声波及的单位，只提升警戒值，不直接赋予 `urgent`，统一保留在 `deferred` 排序列表内，由每帧 `wakeBudget`（默认 1~2 个/帧）有序唤醒。

#### 1.3 呈现协调器对震屏（Camera Quake）的柔性容忍
- **目标**：消除连续开火后坐力导致的地形呈现层 `clear()` 颠簸。
- **改动文件**：`mods/ContinuousScene/src/ScenePresentationCoordinator.as`、`SceneEventBitmapFill.as`
- **具体实施**：
  1. 检查 `eligibility()` 门禁中的震屏判断：原代码严格禁止任何震动 `w.cam.quakeX!=0 || w.cam.quakeY!=0`。
  2. 方案调整：将普通的开火抖动（`Math.abs(quakeX) <= 25 && Math.abs(quakeY) <= 25`）纳入呈现允许范围；
  3. 在 `SceneEventBitmapFill` 更新 Sprite 坐标时，把 `quakeX/Y` 传递给合成节点的变换矩阵，而非直接判定为“不支持并清空整个地形显示”。
  4. 极端震屏（如剧情大地震、重度爆炸 `> 30px`）才触发 `clear()` 回退原生。

---

### Phase 2: 地形图块烘焙历史弹痕空间过滤（patches / 预处理）

> **⛔ 2026-11-02 执行时撤销：已存在于部署宿主，无需实施。**
> 执行核对发现部署宿主（冻结源 `build/generated/camera-spatial-20261101/source/fe/graph/Grafon.as`，即 A9B3 谱系）的 `sceneRestoreMarks` 已实现 decal 空间剪枝：旧存档惰性补算 `sceneDecalBounds`、与当前烘焙矩形不相交即跳过、经 `sceneApplyRegionAction` 做区域化绘制。原 §1 根因 4 基于过时的 `src/patches/GrafonChunks.as.inc` 快照（该文件停留在全量重放版本），对正式产品不成立。
> 遗留动作：`.inc` 与部署谱系的分叉属源码卫生债（未来全量构建若直接使用该 .inc 会**回退**宿主已有的剪枝），应择机以冻结源反向同步；本轮不动。

#### 2.1 ~~`sceneRestoreMarks` 空间相交剪枝~~（原文存档，未实施）
- **目标**：防止新区块在 `drawLoc` 时线性遍历游戏启动以来的上百个历史弹痕。
- **改动文件**：
  - 源码补丁片段：`mods/ContinuousScene/src/patches/GrafonChunks.as.inc`
  - 打包生成脚本：`mods/ContinuousScene/build/prepare.py`
- **具体实施**：
  1. 在记录 `sceneMarks` 时，除类型与参数外，一并保留该标记的作用矩形（例如：`decal` 为以命中点为中心 512×512 矩形，`paint` 为画笔线段外扩 50px 矩形）。
  2. 在 `sceneRestoreMarks()` 执行时，获取当前正在烘焙的目标区域 `targetBounds = new Rectangle(this.sceneX, this.sceneY, this.rectX, this.rectY)`。
  3. **剪枝逻辑**：
     ```actionscript
     for each(var item:Array in this.sceneMarks) {
         var markRect:Rectangle = item[3];
         if(markRect != null && !markRect.intersects(targetBounds)) continue; // 空间不相交直接跳过
         this.sceneStamp = item[2];
         var action:Function = this[item[0]];
         action.apply(this, item[1]);
     }
     ```
  4. 收益：将新区块生成时的弹痕重绘开销从 $O(N_{total})$ 降低至 $O(K_{local})$（仅当前区块内的弹痕），彻底斩断长时间战斗后推图越来越卡的时间累积效应。

---

### Phase 3: 宿主层长帧尾部与高频 GC 抑制（UnitTurret Animate Guard）

*此阶段推进已在 A9B3 宿主上生成的单方法候选，目标解决 32/35 次 `>100ms` 长帧伴随的 90MB 内存回收停顿。*

#### 3.1 炮塔帧动画冗余重设守卫（UnitTurret.animate Guard）
- **现状**：
  - 候选补丁 `6AC6C692` 已在当前宿主 A9B3 上构建完备（`build/generated/camera-turret-animate-20261102/`）；
  - 单方法字节级审计完成（仅 `fe.unit.UnitTurret::animate` 变化，类布局不变）；
  - 冒烟测试 27/27 断言通过（含 10 座炮塔 0 错位）。
- **执行阻碍与前置要求**：
  - 历史复查要求：该候选曾因“两轮均值无明显提升”被搁置，必须提供 **“GC 频率下降 / 长帧尾部时间（P95/P99）显著削减”** 的成对实测证据方可放行部署。
- **执行步骤**：
  1. 使用 `camera-lead` 驱动开展成对对比测试（A9B3 基线 vs `6AC6C692` 候选）；
  2. 统计战斗走动工况下的内存增长速率（MiB/s）、`>100ms` 发生频次以及 P95/P99 尾部帧时；
  3. 若证实成功削减 GC 密集长帧且不破坏炮塔正常动画/受击转向，正式推进宿主替换并备份回执。

---

## 3. 验证与门禁标准（Validation Gates）

按照工作区治理章程（`GOVERNANCE.md` §6）与调试规范执行，所有验证必须在独立沙箱与登记环境下完成：

### 3.1 功能与机制回归门禁（必须 100% 通过）
1. **测试先登记**：运行前调用 `tools/agent-debug.ps1` 刷新共享登记表，采用 `game-coexist` 隔离配置文件。
2. **状态保真断言（Mechanics Check）**：
   - 运行 `smooth-wake-v095-mechanics-r1`：确保 27 项基础机制测试（门、交互、奖励池、休眠唤醒调度）全过；
   - 隐身/潜地单位状态检查：确保 `UnitSpectre`、地下潜伏者（lurk box）在进入和离开脱战范围时，视觉状态不发生错乱。
3. **视觉一致性断言（Visual Integrity）**：
   - 运行 `smooth-wake-v095-issues-r1`：16 项边界门、多比例缩放、固定视觉物体验收通过；
   - SATS 卫星图截取与还原无破损。

### 3.2 性能对比测试工况（Performance Metrics）
以标准战斗走动测试路线（`random_mane` stage 4，同走廊 6~12 名活动敌人，武器持续开火，镜头左右往返）进行成对采集：

| 关键考核指标 | 当前基线（0.9.5 + A9B3） | 目标验收门槛 | 判定标准 |
|---|---|---|---|
| **战斗走动平均帧时** | ~45.0 ms | **≤ 38.0 ms** | 显著缩小与纯走动（34.5ms）的差距 |
| **P95 帧时** | 69.0 ms | **≤ 52.0 ms** | 削减突发长帧峰值 |
| **>100ms 停顿发生率** | 每 200 帧约 14~26 次 | **减少 ≥ 50%** | 有效缓解肉眼可见的“严重顿挫” |
| **开火震动颠簸次数** | 高频 clear / rebuild | **降至接近 0 次** | 地形合批呈现持续在线 |

---

## 4. 回滚与安全应急预案（Rollback Runbook）

在任何阶段若发生断言失败、报错或未达标情况，严格执行单步无损回退：

- **Phase 1 回退**：
  - 恢复 `mods/ContinuousScene/release/ContinuousSceneMod.swf` 为当前 0.9.5 版本（指纹 `1A66B1F486BD5D8F5AA6B38A9469F1AFC40F598B6CFE9E4624620F490B251612`）；
  - 运行时应急禁用：在控制台/代码中调用 `nativeAPI.objectCullingEnabledSet(false)`。
- **Phase 2 回退**：
  - 恢复 `mods/ContinuousScene/src/patches/GrafonChunks.as.inc` 原始文件。
- **Phase 3 回退**：
  - 若候选宿主测试异常，保留现有正式宿主 `A9B39CC7` 不变；若已部署，用备份文件 `pfe_before_spatial_collision_20261101-225837.swf` 覆盖根目录 `pfe.swf`。
