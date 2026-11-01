# 移交报告：AddictionSystem / RConnect 每帧垃圾分配归因（可直接取用）

> **写给**：AddictionSystem 与 RConnect 的维护者（或接手该模组的 agent）
> **写自**：ContinuousScene 模组会话，2026-11-02
> **一句话**：在大场景正式模组组合的实测采样中，你们模组各有一个**每帧稳定产生的纯垃圾分配源**（对象当帧生、当帧死）。本报告给出精确定位、证据文件与验证方法，修不修、怎么修由你们自行判断。
> **重要预期管理**：我们自己模组的最大单源垃圾（2,810 对象/帧，比下述任何一项都大）已实现修复并实测——**单独消除它并未带来可测的帧率改善**（GC 回收次数仅 9→8/2.2 分钟）。所以请不要把本报告当作"修了就不卡"的承诺；它的价值是把大场景组合的总分配速率降下来，这是剩余唯一可行方向，适合多源组合削减后统一复测。

---

## 1. 测量环境与口径（先读这段，避免误读数字）

- **环境**：Remains 1.02 正式宿主（pfe.swf `A9B39CC7…`）+ 当日全部 14 个正式启用模组（含 ContinuousScene 0.9.5）+ 诊断探针；隔离运行时、独占测试登记、2048×1123 窗口、随机连续大场景（random_mane，同布局种子）、120fps 帧率上限下的容量测量。
- **工具**：`flash.sampler` 内部采样器探针（FrameCostProbe v2）。每 90 帧取 1 帧，把该帧内**新分配对象**按出生栈归类；并用 **DeleteObjectSample 的 id 关联回出生栈**，统计"当帧出生且当帧死亡"的对象（下称**当窗死亡**，即纯垃圾特征）。
- **口径限制**（如实声明）：
  1. 计数是**对象个数**，不是字节。String 等对象死后无法测尺寸，字节只能估。
  2. "当窗死亡"只覆盖单帧内即死的对象；多帧寿命的对象不计入（所以实际垃圾产出 ≥ 表中数字）。
  3. 采样器自身会增压；数字用于定位与对比，不作性能验收。
  4. 下述数字在基线与候选两次独立运行中**几乎完全一致**（如 11,410/24 窗），说明是稳定速率而非偶发。

## 2. AddictionSystem 的发现（合计 ~1,400 新对象/帧，其中 ~1,000+/帧当窗死亡）

以下均为**每单位每步（per-unit per-step）**触发。测试场景 ~130-146 个单位时测得；数字 = 24 窗合计 ÷ 24（每窗 1 帧）。

### 2.1 每步 JSON 序列化落盘链 — ~408 新/帧，88.7% 当窗死亡

```
JSON$/stringifySpecializedToString < JSON$/stringify < Engine/json < Runtime/persist < Runtime/step < Unit/step < Location/step
```

- 24 窗合计 9,792 新对象、8,688 当窗死亡。约 408 新/帧，其中 ~362 帧/当窗死亡。
- 语义：`Runtime.persist` 在**每个单位每一步**把状态 JSON.stringify 一次。

### 2.2 参数重建链 ×2 — 合计 ~867 新/帧，53.9% / 69.8% 当窗死亡

```
Pers/setSkillParam < Pers/setParameters < AddictionPers/setParameters < Runtime/step < Unit/step   (11,410 新 / 6,150 死)
Pers/setParameters < AddictionPers/setParameters < Runtime/step < Unit/step < Location/step        (9,410 新 / 6,570 死)
```

### 2.3 Catalog 克隆的 JSON 往返 — ~200+ 新/帧，90-100% 当窗死亡

```
JSON$/stringifySpecializedToString < JSON$/stringify < Catalog$/clone < Catalog/numbers < Runtime/apply < Runtime/before   (90.6% 死)
JSON$/parseCore < JSON$/parse < Catalog$/clone < Catalog/numbers < Runtime/apply < Runtime/before                          (100% 死)
```

- 用 JSON.stringify→parse 做"深拷贝"，往返产生的中间字符串全部即弃。

### 2.4 其它小项

- `Effect/getXmlParam < Runtime/beforeParameters`：~83 新/帧，67.6% 死（每次重建 Effect 都重新解析 XML 参数）。

### 可能的优化方向（仅供参考，语义与存档行为由你们把关）

- persist 链是否需要每单位每步执行？（降频/脏标记/仅变化字段）
- 参数重建与 Catalog.clone 是否可缓存或换浅拷贝？
- 我们同场景的自研同类问题（每对象每帧拼字符串键）用**结果缓存**消灭后每帧少 2,810 对象，可作为手法参考：`mods/ContinuousScene/build/generated/envkey-cache-20261102/build_envkey.py`。

## 3. RConnect 的发现 — ~139 新/帧，100% 当窗死亡

```
RCLocale$/fit < NetHud/layout < NetHud/refresh < Session/onTick < Timer/_timerDispatch < Timer/tick
```

- 24 窗合计 3,324 新、**3,324 当窗死亡（100%）**——教科书式纯垃圾。
- 语义：联机会话的定时器每 tick 刷新 NetHud 布局，`RCLocale.fit`（文本适配）产生的对象全部即弃。
- 量级较小（139/帧），优先级低于 AddictionSystem；但 100% 死亡率说明缓存/复用空间明确。

## 4. 完整背景（为什么只点名你们两个）

同一次测量中按大小排序的其余垃圾源：原生渲染 `[pre-render]` 引擎内部（1.0-3.6k/帧，随画面波动，引擎侧）、ContinuousScene 自研区域键泵（2,810/帧，**已修复但未部署**——见预期管理）、炮塔/部件 gotoAndStop 链（引擎行为）、无栈样本（定时器/GC 邻近，不可归因）。**TDFC** 的 `GameBridge.snapshot` 是留存型（387KB 存活、少量分配），不在垃圾泉名单里，无需动作。

## 5. 证据与复现方法

- **原始数据**（直接可读，含每窗完整栈直方图）：
  - `mods/ContinuousScene/knowledge/experiments/evidence/gc-source-attrib-r5/storage/result.json` → `frameCost.windows[].{alloc,garbage,types,liveSizes}`
  - 复核运行：`.../evidence/envkey-gcattrib-r1/storage/result.json`（另一宿主候选下的同构数据，你们的栈数字一致）
- **报告**：`mods/ContinuousScene/knowledge/experiments/gc-source-attribution-20261102.md`（完整排名）、`gc-combo-closure-20261102.md`（上限分析）
- **验证你们自己的修复**：探针与工具链公开在本模组目录，可直接复用——
  - 探针源码：`mods/ContinuousScene/build/generated/camera-gc-source-v14-20261102/`（FrameCostProbe.as 为采样器；build.py 编译；run_once.py 为运行器，改 HOST 指向你们的环境）
  - 分析脚本：同目录 `gcattrib_analysis.py`，输出分配/垃圾/存活三榜与类型直方图
  - 运行前请按工作区规则刷新共享测试登记（`mods/ModLoader/tools/agent-debug.ps1 tests`），采样运行用独占 `game` 资源
- **组合复测**：若你们完成优化，ContinuousScene 侧保留了已验证的候选宿主 `029DAF34`（区域键缓存），可组成"多源组合包"做一轮 v13 配对测量（工具链就绪，`build/generated/camera-lead-v13-gctail-20261102/`）统一裁决帧收益——这是把各方削减变成玩家可感改善的下一步。

## 6. 边界声明

- 本报告只包含**只读测量**结论；未触碰你们模组的任何文件。
- 数字仅适用于当日环境（正式宿主+14 模组组合、随机大场景、~130-146 单位）；换环境需重测。
- 归因 ≠ 责任：你们的模组在原版小房间场景下这些速率可能完全无感；是大场景组合的单位数量（~570 对象/步）把每单位每步的成本放大到了可见量级。
