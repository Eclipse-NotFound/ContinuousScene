# 2026-11-02 CS 0.9.5 状态保真物体剔除（Phase 4）部署 与 炮塔守卫候选（Phase 3）备妥

## Phase 4：包装层物体剔除（已部署）

### 设计（CA94 回退教训的正解）

旧屏外剔除（CA94AF17，已回退）直接覆写 `unit.vis.visible`，破坏 UnitSpectre 等原生隐藏状态（false→true 现形）。本轮改为**透明包装层**：

- 每个对象层直接子节点包进透明 `Sprite`（`SceneObjectCulling`，模组自有、探针验证过的机制），只切换**包装层** `visible`；游戏独占每个对象自身 `visible`/alpha/filter 语义——幽灵、潜地、剧情显隐全部不受影响。
- 源码核实兼容性：`Pt.remVisual()` 用 `vis.parent.removeChild(vis)`（父相对删除），对象被游戏移除时直接从包装层摘除，孤儿检测下一帧清理空壳；`addVisual` 重挂直挂层后由下次 update 重新包装。telekinesis 目标与潜伏(lurk)箱保持直挂不包装。
- SATS 截图绘制完整世界树（`SatsVisibleGuard.capture → data.draw(g.visual)`）：截取窗口内挂起剔除（全部包装置 visible）、finally 恢复——卫星图与原生快照同源。
- 空边界（未测量）不隐藏；剔除自身异常仅自禁用并记日志，不打倒模组入口。
- 观测/开关：`nativeAPI.objectCullingEnabled / objectCullingEnabledSet / objectCullingStats`（tracked/hidden/suspended）。

### 接线与版本

`ContinuousSceneMod` 0.9.5：onFrame 末尾（呈现协调器之后）调用 `objectCulling.update(w, enabled && allStat==1 && t_exit==0)`。改动文件：`SceneObjectCulling.as`（挂起/恢复+空边界+stats）、`SatsVisibleGuard.as`（截取挂接）、`ContinuousSceneMod.as`（接线+API+0.9.5）。

### 验证（隔离运行时，A9B3 宿主 + 14 模组 + 探针，均登记 game-coexist）

| 运行 | 断言 | 覆盖 |
|---|---|---|
| smooth-wake-v095-mechanics-r1 | 27/27 | 调度语义 + 机制/门/奖励池（剔除激活态） |
| smooth-wake-v095-issues-r1 | 16/16 | 门视觉/边界×3缩放/Bonus·Trap·CheckPoint·**UnitTurret** 固定视觉；入口截图 |

截图程序化健全性：1264×761、全帧 1472 色、中心区 1481 色（主色黑为正常战争迷雾），无灾难性缺失。**限制**：本会话模型不能读图，像素级人工/视觉模型复核开放（`evidence/smooth-wake-v095-issues-r1/issues-entry.png`）。**无计时声明**——剔除的帧收益未测量；不引用已回退 CA94 的 ~0.6ms 旧值。

### 部署

- release → `1A66B1F486BD5D8F5AA6B38A9469F1AFC40F598B6CFE9E4624620F490B251612`（0.9.5，含 0.9.4 平滑唤醒）
- 备份：`build/backups/ContinuousSceneMod-0.9.4-DF3B6812-before-culling-20261102-004010.swf`；回执 `state/object-culling-deployment-20261102.json`；需重启生效

## Phase 3：炮塔同帧守卫候选（已备，未部署）

- 依据：`UnitTurret.animate` 每帧无条件 `vis.osn.puha.gotoAndStop(this.tr)`，`tr` 为构造时常量；分配采样指该链为最大存活对象来源（54k 分配/3.85MB），32/35 长帧伴随 GC 回落。
- 在当前宿主 A9B3 重建候选 `6AC6C692992F2483024FDF378B980E434CB4D23D07933CBDF2559006B94937C9`（`build/generated/camera-turret-animate-20261102/`，复用 20261031 配方；审计：仅 `fe.unit.UnitTurret::animate` codeBytes 变化，类布局不变）。
- 候选宿主冒烟：mechanics 27/27（含 10 座炮塔 0 错位），`evidence/turret-guard-v095-mechanics-r1`。
- **不部署**：旧否定（两轮配对无均值收益，`performance-cut-survey-20261031`）仍具约束力；iteration-review 要求的翻案证据是 **GC 频率/长帧尾部配对测量**（camera-lead 驱动），本轮未执行。候选保留待测。

## 证据

- `evidence/smooth-wake-v095-mechanics-r1`、`evidence/smooth-wake-v095-issues-r1`、`evidence/turret-guard-v095-mechanics-r1`
- 构建：`build/generated/camera-turret-animate-20261102/candidate-build.json`
- 驱动：`build/phase_verify.py`（登记包装）；部署回执 `state/object-culling-deployment-20261102.json`
