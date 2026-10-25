# 原生地形摘树 r1：静态驻留前提不成立

2026-10-25，未通过诊断资格；没有性能结论、像素结论或部署。

证据在 `knowledge/experiments/evidence/native-terrain-detach-20261025-r1`。探针 `056C8CF054475ABB42E33C280B8A620B7CBD6F835E76C786FEEA44D9A1880889` 编译成功；实际自有 AIR 49264 已退出，共享登记 e9170995e36346ffa5e2f97e4f2913e0 已结束。

初始化时有109个 surface、436个原生 Bitmap，资格检查成功。第一段 A 保持原位绑定；第74次 update 检出 surface 数量改变，按严格静态驻留条件中止。原生预绘仍在正常运行，不能冻结预绘或删除这部分帧来取得通过。

- 0个完整300帧段、8条已完成原夹具断言；没有 A/B 对照。
- detaches=restores=held=pendingRestore=0，未执行任何候选摘树。
- helper 累计284ms包含初始化及74次检查，只是诊断自身开销，不是优化幅度。
- 清理释放了自身记录，但 `valid=false`，所以 `restored=false` 保留失败；这不表示留下了离树节点。终态像素检查没有运行。
- runner 实际完成后验：526正式输入、脚本/夹具、13运行库及86冻结源码守恒；`inputsUnchanged`、`runtimeInputsUnchanged` 为 true。未出现其他 AIR 争用或内存中止。

后续仅准备独立 v2，适配已核实的原生尾部追加与 Drop 生命周期，继续严格核对其他节点顺序和位图归属。不得复活原生销毁的数据，不把本轮失败改成通过。

指纹：原始 result `A5B691B4A0F87527FD728DA4DED90F8E0D544CDE7AEA4FE3DF77CAF38F7A65E0`；summary `544EEF6F6F05A9571B0691BF8CC41D745FA4587E080D3FFB86578CFD35A54234`；process-policy `B94B1AA1C0AE04D09C373C2BF7F5E4D26C64CDD1AD2C5C4345F6A57EEDED41BA`。
