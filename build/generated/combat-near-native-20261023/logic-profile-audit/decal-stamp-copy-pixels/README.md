# 印记 copyPixels 独立组件候选

来源：相邻 `decal-stamp-tolerance/tests/SceneDecalStampProof.as`，冻结 SHA256 `26A20F512816ABF2E8358FD39F36D2BB3931044ACEBC88DF624C11FE2A5D390A`。旧文件和测试证据保持不变。

唯一算法变化：实际路径的印记已经绘好缩放、旋转和颜色变换，最后一步改用 `copyPixels(stamp, stamp.rect, new Point(-ox, -oy), null, null, true)` 合成，替代整数平移的第二次 `draw`。完整源矩形由 API 按 400×400 目标裁切。只允许预绘 BitmapData、normal、无第二次颜色变换、原整数平移；不合条件直接失败。期望路径仍直接绘制原生矢量素材。两条路径仍分别读取和恢复自己的原有 alpha。

172 项原检查全部保留，包括所有原多帧素材、同原点和相邻块、同位重复及交错重叠、已知反例重复 8/32 次。序列只在末尾比较，逐步不会重置颜色；比较仍完整扫描 ARGB，`equal` 只表示严格相同，`tolerancePassed` 仍要求每个 RGB 通道差≤1、alpha 完全相同。实际宿主域、素材身份、隔离应用 ID、宿主引用和完整清理检查不变。

世界边缘、部分源印记、erase/hardlight、改变 alpha 的颜色变换仍未覆盖。这里只替换合成 API，没有放宽容差。准备阶段只做源码与静态核对；后续组件已实测，结果如下。没有战斗性能验收或部署。

## 后续实测：copyPixels 未消除颜色误差

以上为准备阶段状态。主线程随后完成独立组件 `decal-stamp-copy-pixels-20261023-r1`，证据位于 `mods/ContinuousScene/knowledge/experiments/evidence/decal-stamp-copy-pixels-20261023-r1/storage/result.json`（SHA256 `E987CC77B576588CA75F36079C2FE8877A2B3FD4A67E73E4AF849F21D0961FBF`）。172 项全部执行：153 项严格相同，158 项满足 RGB 每通道≤1且 alpha 完全一致，14 项仍超出容差；所有案例的 alpha 差均为 0，最大 RGB 通道差仍为 4。`valid=true` 只表示组件执行有效，`equal=false`、`tolerancePassed=false` 表示画面等价条件未通过。

独立只读对照 `decal-stamp-tolerance-20261023-r2/storage/result.json`（SHA256 `73AE66AD84E27C21734247D9F1B43B163DE8F8E0A7A985490C9550ADCD68BCB0`）：按案例名称、阶段及目标原点逐项匹配，172 项所有案例字段除 `elapsedSinceStartMs` 外完全一致，包括差异数量、各通道最大差、差异边界和记录的失败像素明细。因此本次改为 `copyPixels` 没有改善已记录的误差，不通过缩减素材或放宽容差使其过关。

4 项完整扫描哨兵通过；创建和释放位图均为 2580，残留 0、清理错误 0，所检查的宿主引用/状态保持不变。主线程另确认正式输入保持。组件耗时 1200ms，旧组件为 1482ms；这不是战斗帧率测试，不能解释为游玩提速。没有战斗性能收益结论，没有部署。
