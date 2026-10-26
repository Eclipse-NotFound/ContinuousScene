# 不合格原型的代价诊断提前退出

2026-10-27，冻结e742a252b24f4d9b84bfaa4e3dca80f3，AIR37692，入图5170毫秒。
原始证据`knowledge/experiments/evidence/camera-world-scroll-cost-20261027-r1`。

五视角自然往返与候选恢复均精确。候选每视角maxRGB3/alpha0，全部明确记为画面
不合格；RGB2标准没有改变。本轮仅允许不合格原型继续代价归因，不是候选验收。

第一段120个原生间隔完成，第一候选间隔之后，下一入口显示状态检查失败。原错误
“Terrain changed during rendered interval”实际核对world位置/裁剪/缓存标志，
不是地形像素。121个部分样本不足以形成成对结论，不报告提速。随后另建帧相位
诊断，不改这次失败。75截图全释放、清理通过，正式526/运行库13和冻结输入保持。

独立复核见`../camera-world-scroll-phases-20261027/verify_batch.py`和`batch-review.json`。
无部署。
