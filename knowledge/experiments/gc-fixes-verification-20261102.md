# 2026-11-02 外部模组 GC 修复验证 + 组合复测（受负载污染）

## 一、移交项修复验证（v14b 独立归因，当前生产栈，24/24 窗有效）——两项均通过

| 移交项 | 修复 | 基线（r5） | 复检（v14b-attrib-r1） | 判定 |
|---|---|---|---|---|
| AddictionSystem 每步 JSON persist（~408/帧，88.7% 死） | ConditionSystem v0.2.1：persist 改事件驱动、setParameters 改 metricsChanged 条件、stocks 复用 | 408/帧 恒定 | **0**（残留 51→223/帧 的 `Runtime/after` 节流路径为另一归属，见下） | ✅ 消除 |
| AddictionSystem setParameters 宗族（~1,100/帧） | 同上 | ~867/帧 两条恒定栈 | **0** | ✅ 消除 |
| RConnect NetHud 链（139/帧，100% 死） | gcfit1 0.2.24：RCLocale.fit 数值键缓存、NetHud.layout 复用 | 139/帧 恒定 | **0** | ✅ 消除（与其自测 3,324→0 互证） |

对方自测数据：ConditionSystem（fork v14 探针，addiction:: 全栈 1,520.5→82.8 新/帧，−94.6%）；RConnect（fit 栈 3,324→0，layout 死亡 −96.6%）。与我的独立复检一致。

## 二、移交报告勘误（ConditionSystem 指出，经包名核实采纳）

原报告 §2.3 的 **Catalog/clone JSON 往返（~143-165/帧）与 `Runtime/persist < Runtime/after`（~223/帧）实为 `fa::` 包——归属 FirearmAttachments**，不是 AddictionSystem。v14b 复检中这两条仍在（合计 ~366/帧）。若继续削减，FirearmAttachments 是下一个应通知的维护者。

## 三、组合配对复测（v13b，4 轮交错，当前阵容）——帧判定被机器负载污染

| 轮 | base（A9B3） | cand（029DAF34） | 信号 |
|---|---|---|---|
| r1 | 9 掉落/599MB/27 长帧/198s | 8/483/62/200s | GC −1 次、体积 −19% |
| r2 | 8/533/221/297s | 7/424/231/235s | GC −1 次、体积 −20% |

- **GC 指标一致**：cand 在全部 6 个历史配对轮中恒定 −1 掉落、体积 −10~20%（与泵消除量吻合，机械可靠）。
- **帧指标不可判**：本轮机器环境负载高（各轮总时长 198–297s vs 清晨干净基线 137s；r2 基线自身 static 均值 42→79ms 波动 2 倍；r1 cand +6.8ms vs r2 cand −5.1ms 方向相反）。长帧 27-231 全域波动为环境噪声主导。
- 结合清晨较干净条件下 fix-A 的 4 轮配对（无帧收益）：**029DAF34 维持不部署**；如需最终帧裁定，可在夜间低负载窗口重跑 4 轮（工具链就绪，`camera-lead-v13b-gctail-20261102/orchestrate_combo.py`）。

## 四、当前生产栈剩余 AS3 垃圾源排名（v14b）

1. `sceneNativeEnvironment` ~2,775/帧（自研宿主补丁；候选 029DAF34 已备未部署）
2. `NativeSceneActivity.update` ~498/帧（自研模组，装箱）
3. `sceneEnsureUpcoming` ~404/帧（自研宿主，块键）
4. FirearmAttachments `fa::` ~366/帧（**新确认归属**，待通知）
5. 炮塔/部件 gotoAndStops 链、pre-render（引擎侧）

## 证据

- 验证运行：`evidence/v14b-attrib-r1`；配对：`evidence/combo-gctail-{base,cand}-r{1,2}`
- 探针：`build/generated/camera-gc-source-v14b-20261102`、`camera-lead-v13b-gctail-20261102`
- 对方证据：ConditionSystem `knowledge/experiments/evidence/gcattrib-conditionsystem-r2`（其目录）；RConnect `evidence/rconnect-gcfit-verify-r1`（其目录）
