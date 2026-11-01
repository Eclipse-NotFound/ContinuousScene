# 2026-11-02 GC 周期回收来源定位：v14 采样器 id 关联归因（生产栈实测）

## 问题

炮塔守卫终局测量确认 ~65MB 周期性大回收（7–10 次/2.2 分钟）与长帧强相关，但其来源未定位。迭代审查旧采样只有"GC 停顿发生的调用上下文"与存活字节下界，无垃圾归属。

## 方法（v14 探针，`camera-gc-source-v14-20261102`，`AB15B380…`）

- FrameCostProbe v2：`flash.sampler` 每 90 帧取 2 个单帧窗（24 窗全有效、零溢出），新增 **DeleteObjectSample id 关联回出生栈**（当窗出生且死亡的"纯垃圾"计数）、类型直方图；保留存活字节下界与 CPU 栈。
- 生产栈实测：宿主 A9B3 + CS 0.9.5 全 14 模组；独占 game 登记；2048×1123。运行 `gc-source-attrib-r5`（前 4 次被并行会话 AIR 争用正确中止，编排器自动重试成功）。
- 限制：字符串等死后不可测尺寸，垃圾字节为计数×类型估计；采样器自身增压（诊断定位用，不作性能验收）。

## 结果：排名（24 窗聚合，382,817 新对象 / 157,022 当窗死亡）

| # | 分配栈 | 新对象/帧* | 当窗死亡率 | 存活字节 | 归属 |
|---|---|---:|---:|---:|---|
| 1 | **`Grafon.sceneNativeEnvironment < Location.step`** | **~2,812** | **99.7%** | 0 | **CS 宿主补丁（自研）** |
| 2 | `[pre-render]` 原生内部 | ~2,263 | 13.3% | 不可得 | 引擎（多数长存） |
| 3 | 空栈（定时器/异步） | ~2,098 | 10.3% | — | 混合 |
| 4 | 炮塔 animate→gotoAndStop→FocusManager 链 | ~869 | 部分 | 3.7MB 累计存活 | 原生+炮塔（已终局） |
| 5 | **`NativeSceneActivity.update`（CS 0.9.5）** | ~530 | 高 | 0 | **CS 模组（自研）** |
| 6 | **`Runtime.persist→Engine.json→JSON.stringify`（AddictionSystem 每单位每步）** | ~408 | 88.7% | 20KB | **外部模组** |
| 7 | **`Grafon.sceneEnsureUpcoming` 块键字符串** | ~396 | 82.6% | 2.6MB 暖块存活 | **CS 宿主补丁（自研）** |
| 8 | **`Pers.setParameters/setSkillParam`（AddictionSystem）** | ~442+ | 54–70% | 0 | **外部模组** |
| 9 | `RCLocale.fit < NetHud.refresh`（RConnect 定时器） | ~139 | 100% | 0 | **外部模组** |
| 10 | TDFC `GameBridge.snapshot` | 少 | — | 387KB 存活 | 外部模组（留存型，非泵） |

*新对象/帧 = 窗口计数÷24（每窗一帧间隔）。

GC 时间线：10 次 ≥4MiB 掉落（top5 65–73MB）、33 个 >100ms 长帧、10 个邻近 GC。

## 结论

1. **首要垃圾泵是 CS 自己的宿主补丁 `sceneNativeEnvironment`**：`Location.step` 对**每个对象每帧**调用（native_map_patch.py:32），每次做 2× int→String + 字符串拼接区域键（~3–5 个 String/调用 × ~570 对象 ≈ **2,800 纯垃圾 String/帧，99.7% 即生即死，零留存**）。与迭代审查"隐藏世界仍有 0.5MB/帧净增长"完全吻合——它不在渲染里，在这个每帧字符串泵里。字符串对象不可死后计尺寸，按 40–64B 估 **~110–180KB/帧（120fps 下 ~13–21MB/s）**，量级足以主导 ~65MB 周期回收的填充速率。
2. 次要自研源：`sceneEnsureUpcoming` 块键字符串（~396/帧、82.6% 死）与 `NativeSceneActivity.update` 的 threats/deferred 装箱（~530/帧，与 0.9.4 前同量级，非回归）。
3. 外部模组各有一泵：AddictionSystem 每单位每步 JSON 序列化/参数重建（~850/帧级、88.7% 死）、RConnect NetHud 定时刷新（100% 死）。归因报告移交对应负责人，本会话不改他模组。
4. 原生 `[pre-render]` 分配量最大但死亡率低（13.3%）——多为长存显示内部件，不是周期回收主驱动。

## 修复方向（未实施，待授权排期）

- **A（自研、收益最大）**：`sceneNativeEnvironment` 加单元格缓存——记 `lastLoc/lastCX/lastCY`（int 比较），仅跨单元格时拼字符串查表；语义等价（同单元格本就因 `region===last` 早退）。宿主单方法替换（复用 20261102 炮塔候选的构建配方），预期消灭 ~2,800 String/帧 的主要垃圾输入。
- **B（自研、次级）**：`sceneEnsureUpcoming` 的 `x+":"+y` 块键改为 int 复合键缓存（同类手法）。
- **C（模组层）**：`NativeSceneActivity.update` 复用 threats/deferred 数组、减少对象字面量。
- **D（跨模组）**：AddictionSystem/RConnect 的每帧 JSON/布局分配——移交各负责人参考本报告证据。

## 证据

- 运行：`evidence/gc-source-attrib-r5`（24 窗全有效；r1–r4 为并行会话争用中止的残迹，保留）
- 分析：`build/generated/camera-gc-source-v14-20261102/gcattrib-summary.json`
- 探针：同目录 FrameCostProbe.as（v2，id 关联）+ ContinuousSceneMotionMod.as（v14）
