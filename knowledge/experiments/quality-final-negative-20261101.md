# 质量管理最终判定：不可行（2026-11-01）

经四轮尝试（宿主 visFront / 宿主 mm.stage / 宿主+sleep / CS 模组），`stage.quality` 降级在 AIR `renderMode="direct"` 下**均导致回归或无效**。

## 尝试汇总

| 方法 | 结果 | 详情 |
|---|---|---|
| 宿主 `visFront.stage` | 无效 | stage 可能为 null；3 轮 vs 基线无差异 |
| 宿主 `mm.stage` | **+10ms 回归** | 可能 AIR 值规范化致每帧重设+缓存清除 |
| 宿主 `mm.stage` + sleep | **+15ms 回归** | AS3 internal 跨包异常 × 139 单位 × 30fps |
| CS 模组 `main.stage` | **+14ms 回归** | 模组 ENTER_FRAME 中设置一次，仍回归 |

## v11 探针 A/B 的 15~17% "改善"是伪象

探针每帧在 `beforeNative` 中设置 `stage.quality`（无论设 "low" 还是 "high"）。**每帧设置 quality 属性本身触发显示列表失效（invalidation）**，导致：
- 设 "low" + 失效 → 重新栅格化时无抗锯齿 → 帧看似更短
- 设 "high" + 失效 → 重新栅格化时有抗锯齿 → 帧看似更长
- **差异来自失效+重栅格化的代价差，不是 LOW 质量的稳态渲染加速**

证据：
- 基线（从不触碰 quality，默认 HIGH，有缓存）= 42.5ms
- 探针 LOW（每帧设 "low"）= 40.4ms — 仅比基线快 2ms，不是声称的 7-8ms
- 探针 HIGH（每帧设 "high"）= 48.3ms — 比基线慢 5.8ms（失效开销）
- CS 模组 LOW（只设一次 "low"，之后不触碰）= 56.5ms — 比基线慢 14ms

**结论**：在 AIR `renderMode="direct"` 下，`stage.quality` 的修改会破坏 GPU 渲染缓存，**任何形式的触碰都导致回归**。此方向应永久关闭。

## 最终状态

根 `pfe.swf` = `CA94AF17…`（四层：预算48 + A2 gutter + 屏外隐藏），不变。
CS 模组 = `D8A68A4C…`（0.9.3 原版），不变。

## 证据

- CS 模组质量回归：`camera-csq-r1`（56.5ms vs 基线 42.5ms）
- 宿主回归：`camera-qs-r1`（57.0ms）、`camera-mmq-combat-20261101-r1`（52.3ms）
- visFront 无效：`camera-aq-combat-20261031-r{2,3,4}` pooled 42.7 ≈ 基线 42.5
- 基线：`camera-vis-clean-host-20261101-r{1,2,3}` pooled 42.5
- v11 探针伪象：`camera-quality-combat-20261001-r1` LOW 40.4 / HIGH 48.3（差 7.9ms 来自失效开销差）
