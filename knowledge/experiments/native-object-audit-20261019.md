---
domain: world-objects
type: experiments
game-version: ["1.02"]
confidence: high
verified: false
discovered-by: ContinuousScene
evidence:
  - kind: decompiled-game-code
    game-version: "1.02"
    symbol: "fe.loc::Box.runVis, fe.loc::Bonus.take, fe.serv::Interact.loot"
  - kind: runtime-experiment
    summary: "原版任务生成前后同对象身份核对，工厂与马哈顿候选各验证原生 E 开箱及碰撞拾取"
date-updated: 2026-10-19
---

# 原版任务大场景的物品完整性核对

用户报告同版本工厂物品堆叠，马哈顿废墟物品稀少；入口为原版任务，已开启连续大场景设置。本次由“大场景 (2)”独立调查，另一“大场景”对话负责现有生产源码与 0.8 合并部署。用户已明确授权本次两对话协调。本调查不覆盖或部署对方的修改。

## 已确认

- 0.7 的 `NativeSceneAdapter.moveObject` 平移逻辑、碰撞及交互坐标，却未同步固定 `Box.vis/shad`、`Bonus.vis`、`Trap.vis/vis2`、`CheckPoint.vis` 等。它们在构造时设置图像坐标，随后不会像常规单位那样每帧更新。多房图像留在各自的局部坐标，叠进同一范围。
- `BackObj.vis/erase/light` 为共享绘制模板，原生 `Grafon` 通过对象 X/Y 的矩阵放置；不能平移模板本身。武器子图形和首领血条亦不能按世界坐标通用递归移动。
- `CheckPoint.area`、`Interact.area` 为独占子区域，不一定进入 `Location.areas`；必须递归迁移逻辑位置和所属场景，并去重。
- `UnitTurret` 通常在原生 `Unit.step -> setVisPos` 时更新位置。旧版马哈顿本次生成的 14 座炮塔均在正确位置，不能把用户“炮塔少”单凭截图归为炮塔生成丢失。

## 观察到

使用实际 `Game.beginMission(random_plant/random_mane)`，在原生 Land 生成完毕、adapter.prepare 之前记录对象身份、分类数组和坐标，prepare 返回后核对同一批引用。不是比较两个不同随机种子的物品数。原生新档、实际已启用模块和当前正式宿主冻结到独立目录；不写正式 pfe 存档。

| 验证轮次 | 合并对象链 | Box 类数 | Box 图像/影子错位 | 马蹄铁数 | 马蹄铁错位 | 炮塔错位 |
|---|---:|---:|---:|---:|---:|---:|
| 旧版工厂 r3 | 493 → 493 | 312 → 312 | 286 | 60 → 60 | 55 | 0 / 1 |
| 旧版马哈顿 | 948 → 948 | 612 | 579 | 125 | 120 | 0 / 14 |
| 0.8 源码候选工厂首轮 | 同源完整性通过 | 315 | 0 | 60 | 0 | 0 / 1 |
| 0.8 源码候选工厂最终 r2 | 458 → 458 | 285 → 285 | 0 | 60 → 60 | 0 | 0 / 1 |
| 0.8 源码候选马哈顿最终 r3 | 908 → 908 | 570 → 570 | 0 | 125 → 125 | 0 | 0 / 14 |

两轮旧版分类数组和对象链未发现新增、遗漏或重复对象。旧版马蹄铁在逻辑位置可以原生碰撞拾取，图像仍留在旧坐标。最终两轮候选均 `result.ok=true`、`merge.ok=true`：同源人口、对象身份、逻辑位置、所属场景、交互坐标、静态图像和影子检查全部通过；Box/Bonus/炮塔入场后图像无错位或脱离舞台。每轮地图随机生成，不把轮次间 Box 数变化当作增减回归。

两轮各验证 7 项互动/覆盖断言。工厂真实远端 `instr1` 容器在 (200,1800)，马哈顿真实远端 `case` 在 (60,1640)，图像均与逻辑位置一致。驱动按下原生 E 后第 6 帧，`cont` 分别从 `instr`、`case` 变为 `empty`；两轮原生马蹄铁碰撞拾取均到 `sost=2`。没有直接调用开箱、取物函数。这里验证的是容器执行原生取物流程，未逐件核对背包内的随机掉落数。

早期 E 红项是测试判据错误：普通容器的 `Interact.loot -> setAct("loot")` 改变 `cont/saveLoot/active` 并设置开箱动画，不会像门那样令 `inter.open=true`。改为验证非空内容变为 `empty` 后，用固定探针重新跑完两图；旧红项与日志保留，不作为游戏开箱故障证据。

马哈顿最终合并瞬间的 `unitVisualMismatch=2` 分别属于 UnitSlaver、UnitAlicorn 的动态图形：此项记录“合并前图像简单平移”与原生 `setVisPos` 重算的差异，不进入静态物体通过判据；本次没有逐一验完所有敌人动态图形。入场后全部 14 座炮塔的图像位置/挂载检查通过。不得把这里扩大为“所有单位图形逐像素一致”。

证据目录均位于 `knowledge/experiments/evidence/`：

- 旧版正式对照：`objects-baseline-plant-r3-20261019`、`objects-baseline-mane-20261019`。
- 候选最终验收：`objects-candidate-plant-r2-20261019`、`objects-candidate-mane-r3-20261019`；各含 `merge.json`、`entry.json`、`result.json`、截图、`hashes.json` 和 `run.json`。
- 候选早期诊断：`objects-candidate-plant-20261019`、`objects-candidate-mane-r2-20261019`，E 判据已由最终两轮替代。

最终固定组合 SHA256：

| 产物 | SHA256 |
|---|---|
| 宿主（正式 0.7 宿主的隔离副本） | `2A4662488BA3B690EB23ACFE4B79ACA3F0D9AE114E5E2DEE7595AF3CABFFB3EA` |
| CS 0.8 源码冻结候选 | `1DB6AE72A3C068A00B28281AA53D835B56ECB84DD664680B9F1FD85EBB6BD2F8` |
| 最终物品探针 | `13CE1BEC0EC8F40B1507E70637FD2C2DBF43573CDED2E10F2CB2CF7231B0EFAF` |

依赖为 RV 0.32.1 `2E7150CF…`、WB 0.5.6-scene `DF9AA072…`、LAD 0.3.1 `514A7671…`，完整启用模块指纹在每轮 hashes.json。最终两轮启动时无其他 AIR，仍仅作为功能验证，不包含性能验收。测试进程正常退出。

## 推测

已复现的静态图像错位足以解释工厂局部拥挤、马哈顿局部稀少；没有证据据此推断所有地图都存在生成数量错误。用户对炮塔稀少的观感，也不能由本次静态物品根因完全解释：所测旧版马哈顿与候选炮塔均未丢失或错位，仍可能受原版随机生成和视野限制影响，未分别证明。

## 独立机制缺陷与待修范围

1. 原生 `Bonus.take` 使用每房 `kolXp/maxXp/unXp/summXp/detecting`。合并仍只保留首房计数，可能提前完成首房奖励，后续计数变负。不能仅汇总全图计数，否则改变每房规则。
2. `Unit.die -> Location.takeXP(...,true)` 将击杀经验钳到 `summXp`；仅保留首房经验池可能让全图后续击杀获得零经验。`Unit.setCel` 的 `loc.detecting=true` 也把每房潜行状态变成全图状态。建议对象到原生奖励房间侧表，分别修正三个结算点，保留原始 `maxXp`。
3. `Interact.isMove` 使用内部 `begX/begY/endX/endY/endX2`；仅改公开 X/Y 不能迁移移动路径，后续 move/bindMove 可能回到旧坐标。需宿主方法级兼容，不能从模组直接读取密封 internal 字段。

这些项已发送负责合并的对话，尚未在本调查中验证最终宿主修复，不能宣称所有原版机关、奖励或完整剧情已正常。

## 测试程序与边界

- 可维护源：`build/object-audit/`，独立运行产物：`build/generated/object-audit-20261019/`。AIR 身份 `pfe-modsettings-continuous-objects-01a151d4`。
- `prepare.ps1` 首次冻结当前正式宿主与启用模块；`-CompileOnly` 仅编独立探针；`-Candidate` 冻结当前 CS 三个源文件后只编 CS 候选，不写共享 runtime。
- `run.ps1 -Map random_plant|random_mane -Variant baseline|candidate`。`-AllowOtherTests` 仅允许与已识别的 RConnect `build/.../coop.xml` 隔离实例并行；不与用户实例或另一 CS 性能实例并行。所有结果只用于功能验证，`performanceEligible=false`。
- 真实 E 通过原生玩家输入、真实生成的无锁/无陷阱/无任务脚本远端箱子验证；不直接调用 `act`。马蹄铁用玩家碰撞原生拾取，不直接调用 `take`。未生成炮塔时会标覆盖为空，不能虚称通过。
- 早期测试驱动问题：跨 SWF 域直接 getDefinitionByName 不能找到 CS 类，改用设置页 API；设置页异步注册须等待；原生 Unit 的 Interact X/Y 可能在生成时未初始化，比较时只要求原先有限的坐标保持平移，不把原生 NaN 算迁移回归。
- `objects-baseline-plant-r2` 期间探针编译时序存在歧义，仅作探索；r3 为后续固定产物的正式旧版对照。后续构建和运行共用独立文件锁，禁止运行中重新编译。
- `run.ps1` 正常执行结束不等于断言通过，必须读 `result.json.ok`；超时或无结果会报错。各项计数仅证明本轮实际生成的对象，不证明未生成类别已被覆盖。

## 尚未验证

全地图每一种机关/脚本、全部炮塔战斗、逐原房奖励恢复、移动平台路径、完整剧情、联机及长期存读档。当前调查不包含性能验收，也不替代正式部署门禁。

## 交接状态

本调查未修改生产源码、正式宿主、正式模组 SWF 或用户存档。当前正式 CS 仍为 0.7（`70C06879A2CFFE85901E5C8E19FC1715028D5C38934975E970569468737309D5`）。上述图像修复属于另一“大场景”对话负责的 0.8 源码，尚未部署；最终候选物品通过不代表其后续性能/宿主修改已验收。已按用户授权发送最终证据和未完成机制项，由该对话统一合并、记忆更新与部署。本对话仅提交独立核对工具和本报告，不纳入对方工作区改动。
