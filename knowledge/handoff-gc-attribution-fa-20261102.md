# 移交报告：FirearmAttachments 每帧垃圾分配归因（可直接取用）

> **写给**：FirearmAttachments 的维护者（或接手该模组的 agent）
> **写自**：ContinuousScene 模组会话，2026-11-02
> **一句话**：实测采样发现你们模组有两条**每帧稳定运行**的分配链（合计 ~390 对象/帧）：其中最大的一条（每帧全量 JSON 存档序列化）**在你们未部署的 v0.4.0 候选源码里已经修好了，只是 release SWF 还是旧代码**——部署它即可消除；另一条（每帧每枪 JSON 深拷贝）在当前源码中仍在。
> **预期管理**（同前两份移交卡）：我们最大单源修复（2,810/帧）单独消除后未带来可测帧率改善；此报告的价值在于降低大场景组合的总分配速率，适合多源组合后统一复测。

---

## 1. 测量环境与口径

与 `handoff-gc-attribution-20261102.md` 相同：正式宿主 A9B3 + 当日全模组组合 + v14 系 flash.sampler 探针（每 90 帧取 1 帧、id 关联"当窗出生且死亡"计数）。本卡数据来自 `evidence/v14b-attrib-r1`（24/24 窗有效）。fa:: 两条链在**每一个采样窗中数量完全恒定**（226/帧与 152/帧，逐窗无波动）——是确定性每帧行为，非事件突发。

## 2. 问题一：每帧全量存档序列化（~226 对象/帧）——已修未部署

**实测栈**（24 窗合计 5,424 新对象，223-226/帧恒定）：

```
JSON$/stringifySpecializedToString < JSON$/stringify < fa::Runtime/persist < fa::Runtime/after < [enterFrameEvent]
```

**根因**（部署版 0.3.5 的 `Runtime.after()`）：

```actionscript
slowStep();persist();          // ← 0.3.5：每个原生 tick 都全量 persist
```

`persist()`（Runtime.as:69）每次执行 **3 次 JSON.stringify**：全部武器装配状态（`{version:1,weapons:states}`）+ 收藏数据（`collection.exportData()`）+ 计时器表。即**每帧把整个"配件数据库"重新序列化成字符串写进 game.triggers**——无论本轮是否有任何变化。类型构成：~118 null 装箱 + ~80 String + ~13 Object + ~12 Array /帧；32.7% 当窗死亡，其余下一帧被新快照替换（延迟一帧的等量垃圾，实际周转为全量）。

**重要**：你们当前源码（v0.4.0 候选，2026-10-15 22:50 提交 `aecdf26`）已改为 `slowStep();persistTimers();`（轻量计时器表）+ 事件驱动 persist（开火/装配/榴弹等时刻）。但 **release SWF（0.3.5）构建于同日 21:25，早于该提交 85 分钟**——线上跑的仍是每帧全量版本。**构建并部署 v0.4.0 即可消除此链**（部署前请按你们的门禁完成验证）。

## 3. 问题二：每帧每枪 JSON 深拷贝（~152 对象/帧，90-100% 当窗死）——当前源码仍在

**实测栈**（24 窗合计 3,648 新对象，152/帧恒定）：

```
JSON$/stringify < fa::Catalog$/clone < fa::Catalog/numbers < fa::Runtime/apply < fa::Runtime/before   (96/帧, 90.6% 死)
JSON$/parseCore < JSON$/parse     < fa::Catalog$/clone < fa::Catalog/numbers < ...                     (56/帧, 100% 死)
```

**根因链**（当前源码仍存在）：

- `Catalog.as:17`：`clone(o) = JSON.parse(JSON.stringify(o))` —— JSON 往返做深拷贝
- `Catalog.as:78` `numbers()` 第一行：`var r:Object=clone(b)` —— 每次调用都全量克隆武器基础数值
- `Runtime.as:167`（`before()`）：`for each(var id:String in owned())apply(id);` —— **每帧对每把持有的武器**走一遍 `apply → numbers → clone`，即使装配与基础数值都没变

`owned()` 本身每帧新建 Array（2/帧）、`bipodSample()` 每帧两个方向各 ~4/帧——小项顺带提及。

**可选修复方向**（语义与平衡由你们把关）：
- `numbers()` 的克隆换成针对已知字段集（FIELDS）的手写浅拷贝——避免 JSON 往返；
- 或对 `apply(id)` 做**脏检查缓存**：state/base/flags 未变时直接复用上次推导结果（`steady>=12`/`deployed` 等少数输入变化时才重算）；
- 或至少仅在武器为 `currentWeapon` 时每帧推导，非当前武器状态变化时才算。

## 4. 量化与优先级

| 项 | 量/帧 | 当窗死亡率 | 状态 |
|---|---:|---:|---|
| 每帧全量 persist | ~226 | 32.7%（+一帧延迟全量） | **v0.4.0 源码已修，待构建部署** |
| Catalog 克隆链 | ~152 | 90-100% | 当前源码仍在 |
| 小项（owned/bipodSample 等） | ~15 | 混合 | 顺带 |
| **合计** | **~393** | | ≈ 我们已修复的 env 泵（2,810）的 1/7 |

量级参考：同为外部模组的 AddictionSystem（现 ConditionSystem）修掉了 ~1,270/帧，RConnect 修掉了 139/帧——都已实测验证归零。

## 5. 证据与复现方法

- 本卡数据：`mods/ContinuousScene/knowledge/experiments/evidence/v14b-attrib-r1/storage/result.json`（`frameCost.windows[].{alloc,garbage,types}`；栈键含 `fa::Runtime`、`fa::Catalog`）
- 探针与分析工具（可直接复用验证你们的修复）：`mods/ContinuousScene/build/generated/camera-gc-source-v14b-20261102/`（FrameCostProbe.as + build.py + run_once.py + gcattrib_analysis.py；运行前请刷新共享测试登记，采样运行用独占 game 资源）
- 版本核对：`git -C mods/FirearmAttachments diff fa2afee..aecdf26 -- src/fa/Runtime.as` 可见 `slowStep();persist();` → `slowStep();persistTimers();` 的修复
- 组合复测：若你们完成修复，可与 ContinuousScene 保留的候选宿主 `029DAF34`（区域键缓存）组成多源组合包做配对测量（工具链 `camera-lead-v13b-gctail-20261102/orchestrate_combo.py`，建议低负载时段）

## 6. 边界声明

- 本报告只含**只读测量与源码阅读**；未触碰你们模组的任何文件。
- 数字适用于当日环境（正式宿主+全组合、随机大场景、非战斗探针路线）；战斗中 persist 链还会因开火事件额外触发。
- 归因 ≠ 责任：原版小房间下无感，是连续大场景组合把每帧成本放大到可见量级。
- 勘误致谢：本卡源于 ConditionSystem 会话的包名纠正（fa:: 归属核实）。
