# 2026-11-02 GC 组合路线终局：B/C 收益上限量化后关闭；剩余杠杆清单

## 背景

修复 A（`029DAF34`，区域键单元格缓存）机制成功但配对无帧收益后，用户批准继续"B（块键缓存）+ C（模组层数组复用）+ 外部模组移交"组合包。本报告用已有 v14 证据的**每窗分布**先量化 B/C 的理论上限，再决定是否构建。

## 每窗构成（每窗 = 1 帧；base = gc-source-attrib-r5，cand = envkey-gcattrib-r1）

| 成分 | base 每窗 | cand 每窗 | 说明 |
|---|---:|---:|---|
| 区域键泵（env） | **~2,810（恒定）** | **0（全部窗口）** | 修复 A 在窗级完全生效 |
| warm/块键栈 | ~350–550（两个补绘突发窗 1.2–2.2k） | 同量级 | **稳态仅 ~400/帧 = A 的 1/6** |
| pre-render 引擎内部 | ~1,000–3,600（随画面波动） | 同量级 | 引擎侧 |
| 窗内垃圾合计 | ~5,000–9,000 | ~2,700–6,100 | 差值≈env 泵 |
| AddictionSystem（JSON+参数） | ~1,200 | ~1,200 | 外部模组，恒定 |
| RConnect NetHud | ~139（100% 死） | 同 | 外部模组，定时器驱动 |

## 判定

1. **B/C 关闭，不构建**：B 稳态上限 ~500 对象/帧、C ~500/帧，合计约为 A（2,810/帧）的 1/3——A 已被四轮配对证明不足以移动帧指标（GC 掉落仅 9→8、长帧不一致）。更小的组合在数学上不可能通过同一门禁。此判定纯用既有数据完成，未消耗运行。
2. **AS3 层垃圾削减路线就此整体关闭**（A=最大单源已证边际；B/C 更小；pre-render/no-stack 为引擎侧）。工作区第三次且最终验证"减分配≠减帧时"。
3. **修复 A 候选保留不部署**（与 lossless-cut-survey 的"纯减分配候选不部署"先例一致），若未来外部模组侧完成大额削减后需要组合复测，可直接复用 `029DAF34`。

## 剩余杠杆（按可行性）

| 杠杆 | 量级 | 归属 | 前置条件 |
|---|---|---|---|
| AddictionSystem 每单位每步 JSON 序列化 + 参数装箱 | ~1,200/帧（≈剩余可归因垃圾的最大项） | 外部模组 | 移交其负责人；单独做也难过帧门禁，宜与其它源组合 |
| RConnect NetHud 定时刷新 | ~139/帧（100% 即死） | 外部模组 | 同上，量级小 |
| pre-render 引擎内部件 | ~1,000–3,600/帧 | 引擎 | 仅在画质取舍（已整体否定）下可动 |
| 中寿命对象（>1 帧窗不可见） | 未知 | 混合 | 采样器 100k 样本上限使跨窗追踪不可行（连续采样必溢出），除非降低采样密度重设计探针 |

## 外部模组移交卡（证据可直接引用）

- **AddictionSystem**：栈 `Runtime.persist → Engine.json → JSON.stringify`（~408 新/帧，88.7% 当窗死）+ `Pers.setParameters/setSkillParam`（~870 新/帧，54–70% 死）+ `Catalog.clone` JSON 往返（~200/帧）。触发频率为每单位每步。证据：`evidence/gc-source-attrib-r5/storage/result.json` 的 frameCost.types（栈键含 `AddictionPers`、`Runtime/persist`）。
- **RConnect**：栈 `RCLocale.fit → NetHud.layout → NetHud.refresh → Session.onTick`（~139 新/帧，**100% 当窗死**），定时器驱动。证据同上（栈键含 `NetHud`）。

## 证据

- 每窗分布分析：由 `evidence/gc-source-attrib-r5` 与 `evidence/envkey-gcattrib-r1` 的 frameCost.windows 直接计算（本文表格）
- 修复 A 终局：`envkey-cache-20261102.md`；候选 `build/generated/envkey-cache-20261102/candidate.swf`（029DAF34）
