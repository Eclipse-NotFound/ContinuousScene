# 合图成本归因（不作视觉或发布验收）

前一轮 camera-atlas-20261025-r1 的第四视口RGB最大差2，超过RGB1门限，未进入计时。原失败不改写。本独立版本只回答：现有显示结构的完整成本是否值得继续研究。不是收益上限，也不是正常游戏FPS。

仍使用相同原生场景、五视口、120fps暂停世界、连续8×120帧及原SceneRasterPresentation。保留原RGB1门限和每视口passed/withinTolerance；单纯颜色超差记录qualityErrors后继续。alpha差异、恢复不精确、缺块、身份、矩阵、内存、其他AIR等失败仍立即中止。最终视觉不合格时report.passed=false、qualityAccepted=false、顶层result.ok=false和登记failed均保留；另用timingComplete说明是否收全计时。禁止把成本归因通过改写为视觉验收通过。

Main新增独立camera-raster-visual断言。runner只捕获最终精确的Probe failed异常，并核对仅这个断言失败、无其他运行错误，随后核查全部960帧、输入闭包和清理；不是泛化忽略失败。summary与visual-failure同时保留原失败。未触及生产文件、原保存内容或当前其他会话WIP。

helper 40D4CB4A7CD72F8C69932BC003163ABF75A1DE703A2CDF8F81C4A9D8E7426E03。即便计时改善，也需修复视觉问题并经过真实战斗/兼容验收，不能据此部署。

## r1实际结果

探针E68CE893，冻结收据probe-builds/probe-source/138905a7d5744b9eb4da6d16e35bc6de/probe-build.json。完整960帧、总30788ms，八项原生预绘/驻留计数不变、恢复完成、15/15截图释放。原始result SHA3145123E4BED28CB53DCBD21B53D389E8F3381864CB158A7F2F9B85522D4DE22。顶层ok=false、唯一失败camera-raster-visual、登记failed均保留。五视口中四个RGB最大差2，另一个差1，alpha全0、恢复全0。

每组240原始帧，不删首建图146ms或原生181ms尖峰：

| 模式 | 均值ms | 中位ms | P95ms |
|---|---:|---:|---:|
| 原生静止 | 29.1792 | 28 | 39 |
| 合图静止 | 30.9875 | 30 | 35 |
| 原生移动 | 37.0417 | 35 | 45 |
| 合图移动 | 31.0750 | 30 | 38 |

移动两对分别37.9333→30.9917、36.15→31.1583ms，方向一致；平均降低约16.1%。移动相对静止额外均值7.8625→0.0875ms，静止自身略慢。此条件支持继续研究合图显示结构，不能换算成真实战斗提升或近原版已达。

首B窗口1次重建（四张位图）、252次原块复制；两段移动均0重建/0复制。短路线未验证长距离跨缓存边缘与连续弹痕刷新，亦未验RV等组合；不以本轮证明这些无开销。summary/aggregate-review/visual-failure和原数据在同名evidence目录。
