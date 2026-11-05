# 性能优化切口全面搜查（2026-10-31）

针对当前部署宿主 `626DFBC8…`（A80 + 预热预算补丁）。方法：当前宿主重跑帧成本采样（2160 帧、48 采样窗）、复用既有报告、读反编译源。诊断数据不代表性能验收；采样中出现 1 个无效窗（Sample count mismatch），失败原件保留，分析仅用 47 个有效窗。

## 1. 当前帧成本画像（每 8 个采样窗 ≈240 帧的样本数）

| 归属 | CPU 样本（每 8 窗） | 分配样本（每 8 窗） | 说明 |
|---|---:|---:|---|
| `[render]` + `[pre-render]` 原生渲染 | 45–132 | — | 最大 CPU 项，渲染/合成原生 |
| `Grafon.sceneNativeEnvironment` | 5–14 | **~14,900** | 最大分配源；此前 clamp 候选已实测无帧收益 |
| `UnitTurret.animate → gotoAndStop` 链 | 12–17 | 1,050–1,920 | 同帧重复 gotoAndStop，带动子对象/FocusManager 分配 |
| `FocusManager.addFocusables` 链 | 4–8 | 920–1,610 | 与上一条同源 |
| `Sprite/constructChildren` | 0–7 | 665–1,130 | 与 turret 动画帧脚本同源 |
| `Grafon.sceneEnsureUpcoming` | 0 | 1,390–2,430 | 每帧 `x+":"+y` 键串等 |
| JSON 序列化（addiction / fa persist） | 0–5 | 840–1,140 | 其它模组（非 CS） |
| RConnect NetHud fit/layout | 0–3 | 700–1,050（部分窗口） | RC 模组（非本会话写入范围） |
| `Grafon.sceneViewReady` | 0 | 672–760 | 探针 snapshot 调用，产品是否每帧调用待查 |

## 2. 已尝试/已关闭的切口

| 切口 | 状态 | 证据 |
|---|---|---|
| 预热预算上限 24→36ms + 环 ±3 | **已部署**（626DFBC8） | 快速平移 P95 237/238→137/180，max 332/406→221/333，forced 3→2，空洞 0；正常速度 ±0.15ms |
| `UnitTurret.animate` 同帧守卫（仅 `puha.currentFrame != tr` 才 gotoAndStop） | **否定**：两轮配对无帧收益（static/pan/walk 多为 +0.3~2.6ms，非稳定改善） | 候选 `1666FCB1…`，仅该方法变化；运行 `camera-turret-v7-20261031-r{1,2}`；对照 `camera-budget-normal-1031-r1`、`camera-baseline-deployed-20261031-r2` |
| `sceneNativeEnvironment` 分配 clamp | 旧负结果 | 分配 65,312→0 但移动增益仅 2.9%/0.57%，未部署（camera-motion-20261029.md） |
| 显示副本裁块（tile crop） | 旧负结果 | ABBA 中位 51.5/48/46.5/52ms，尾延迟未改善 |
| A2 gutter 快速暖块 | 未部署 | 边界块 −28%，但 gutter 像素近似，WB 门禁未过 |
| A3 有界补绘 | 否定 | 尖峰降低但平均更差、正常相位偶发大帧 |
| 光照、镜头平移 | 已量化 | 光照 ~1.0ms/帧；纯横移 +0.49ms |
| JSON persist / NetHud / TDFC bridge | 其它模组 | 不在本会话写入范围，仅记录分配占比 |

## 3. 结论与建议

1. **分配数不等于帧时间**：本轮再次验证——turret 链有 ~125–240 次/帧分配，但去掉同帧重复 gotoAndStop 后帧时间没有可重复改善；`sceneNativeEnvironment` 的分配 clamp 也一样。继续做“只减分配”的切口性价比低。
2. **剩余最大 CPU 是原生渲染**（`[render]/[pre-render]`），要动只能改绘制分层/分辨率/合成方式，属于视觉风险方向；此前裁块/分层切换均无稳定尾收益。
3. **真正影响体验的仍是长帧尾部**（forced 完成、同步补块、战斗 A/I）。已部署的预算是目前唯一有同日成对证据的视觉中性收益。
4. 若继续，优先方向应是：
   - 深入长帧成因（forced/同步补块的具体调用与可分摊边界），而不是平均分配；
   - 与其它模组负责人协作处理 JSON persist / NetHud 的每帧分配；
   - 评估 GPU/渲染层（需视觉门禁与用户取舍），本会话不单方面改。

## 4. 证据

- 采样：`evidence/camera-frame-cost-20261031-r1/`（47/48 窗有效，1 无效窗原件保留）
- 转塔候选：`build/generated/camera-turret-animate-20261031/{candidate-build.json,candidate.swf,candidate.xml}`
- 运行：`camera-turret-v7-20261031-r1`、`-r2`；对照 `camera-budget-normal-1031-r1`、`camera-baseline-deployed-20261031-r2`
- 分析脚本：`camera-frame-cost-20261031/analyze_partial.py`、`camera-lead-v7-20261030/{turretcmp.py,turretcmp2.py}`
- 既有：`camera-light-warm-lead-20261029.md`、`chunk-cost-attribution-20261030.md`、`visual-neutral-budget-20261031.md`
