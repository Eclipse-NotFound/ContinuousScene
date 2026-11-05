# 质量管理与敌人休眠：负结果报告与回退（2026-11-01）

第五层（LOW 渲染质量）和第六层（mm.stage 质量 + 敌人休眠）均导致回归，已回退到第四层（CA94AF17 = 预算48 + A2 gutter + 屏外单位隐藏）。

## 尝试 1：visFront.stage 质量（第五层，8321E4E7）

- 代码：`this.visFront.stage.quality = "low"`
- 结果：**无效**（跨 3 轮 vs 无质量管理基线无差异，42.7 vs 42.5）
- 原因：`visFront.stage` 可能为 null（visFront 可能不在显示列表上），try-catch 静默吞掉

## 尝试 2：mm.stage 质量 + 敌人休眠（DC88BCCD）

- 代码：`World.w.mm.stage.quality = "low"` + 远处单位 `sleep=true/false`
- 结果：**严重回归 +15ms**（57.0 vs 41.6）
- 原因：`sleep` 是 `fe.unit` 包的 internal 属性，从 `fe.graph` 包访问每个单位都抛异常；139 单位 × 30fps 的异常处理开销约 14ms/帧

## 尝试 3：mm.stage 质量（无休眠，C6EEDFF8）

- 代码：仅 `World.w.mm.stage.quality = "low"` + 可见性管理
- 结果：**严重回归 +10ms**（52.3 vs 42.5）
- 原因推测：AIR 可能把 `"low"` 规范化为 `"4x4"` 等内部值，导致 `quality != "low"` 守卫每帧为 true、每帧重设质量并触发 GPU 缓存清除

## 回退

- 已回退到 `CA94AF17…`（第四层 = 预算48 + A2 gutter + 屏外隐藏）
- 需重启游戏生效

## 关键发现

1. **从 Grafon.sceneTick 设置 stage.quality 不可靠**：
   - visFront.stage 可能 null → 无效
   - mm.stage 每帧重设 → 回归（可能因 AIR 值规范化）
2. **从 CS 模组 ENTER_FRAME 设置 stage.quality 可行**（v11 探针证实 15~17% 改善）：
   - 探针的 `main.stage` 是模组自身根对象的 stage → 就是游戏的 Stage
   - 探针在 ENTER_FRAME 中设置，时序在渲染前
   - 这说明质量管理需要在 CS 模组层面实现，不在宿主 Grafon
3. **敌人 sleep 管理不可行**：AS3 internal 跨包访问的异常开销（139单位×30fps ≈ 14ms/帧）

## 推荐下一步

若要获得 v11 探针证实的 15~17% 质量收益，需要在 **CS 模组**（ContinuousSceneMod.swf）中实现：
- CS 模组的 ENTER_FRAME 处理器中设置 `stage.quality = "low"`
- 进入连续场景时设置，退出时恢复
- 需要从冻结源重建 CS 模组（工程量较大）

## 证据

- 休眠回归：`camera-qs-r1`（57.0ms vs 基线 41.6ms）
- mm 质量回归：`camera-mmq-combat-20261101-r1`（52.3ms）+ `camera-mmq-deployed-verify-20261101-r1`（54.7ms）
- visFront 质量无效：`camera-aq-combat-20261031-r{2,3,4}` pooled 42.7 vs 基线 42.5
- 基线：`camera-vis-clean-host-20261101-r{1,2,3}` pooled 42.5
- 探针级质量收益（有效证据）：`camera-quality-combat-20261101-r1` LOW 38~42 vs HIGH 47~49
