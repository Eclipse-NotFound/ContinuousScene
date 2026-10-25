# 原生远处地形摘树 v2：真实战斗 r1

2026-10-25。**诊断完整通过，但没有明显或稳定的性能收益；停止此路线，不部署。** 原生A均56.185ms，摘树B均56.055ms，差0.130ms（约0.23%）；两对方向相反，不能把这一微小合并差额称为优化。计时内扫描、判断、移树、恢复与观察的全部成本保留，不能事后扣去helper约4ms便宣称更快。

证据：[summary.json](../../../knowledge/experiments/evidence/native-terrain-detach-v2-20261025-r1/summary.json)、[原始result.json](../../../knowledge/experiments/evidence/native-terrain-detach-v2-20261025-r1/storage/result.json)、[process-policy.json](../../../knowledge/experiments/evidence/native-terrain-detach-v2-20261025-r1/process-policy.json)。这些证据路径相对本目录；完整位置为 `mods/ContinuousScene/knowledge/experiments/evidence/native-terrain-detach-v2-20261025-r1/`。

## 原始计时复算

原生SMG10六敌、玩家ASSR、真实Shift移动与物理保持，ABBA各300帧，26项原生断言全过。逐一重算1200个相邻`sampleAtMs`差值与`continuousFramesMs`完全一致；首尾52926→120270ms，总67344ms，没有切换删帧或残段拼接。实际超过步行速度的帧数依次62/59/48/57。视觉效果沿夹具配置 `noLighting=true/noWall=true/vision=false`；模块仍加载，不能把效果关闭写成卸载。无SATS输入，运行中禁止状态检查通过。

| 段 | 模式 | 均值／中位／P95 ms | 最大ms | 玩家射击 | 敌人射击 | 平均awake | 夹具弹平均并发 | 预绘块／分片 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | A原生 | 55.007／53／68 | 142 | 100 | 108 | 38.9 | 1.127 | 3／22 |
| 1 | B摘树 | 53.933／51／67 | 144 | 100 | 46 | 39.0 | 0.533 | 5／40 |
| 2 | B摘树 | 58.177／56／77 | 169 | 100 | 259 | 46.7 | 4.143 | 4／17 |
| 3 | A原生 | 57.363／56／73 | 159 | 100 | 178 | 42.4 | 2.037 | 4／20 |

- 首对B−A为−1.073ms，反向第二对B−A为+0.813ms。
- 合并A/B各600帧：均56.185/56.055，中位均54，P95为71/72，最大159/169，超过100ms为5/4次。所有尖峰保留。
- A/B玩家各200发；敌人286/305发，平均awake约40.65/42.85，夹具弹平均并发约1.582/2.338。A预绘7块42分片，B9块57分片。第一B敌射显著较少，第二B敌射、活动人口与弹并发更多，负载随战斗演化，不能从段差精确分离单一显示成本。
- helper update的段均值为3.503/4.040/4.117/4.283ms；最高优先级head包装均0.027/0.043/0.030/0.020ms。1200帧update合计4783ms、head包装36ms，平均约4.016ms，初始化外层8ms也处在连续起点之后。这些是诊断本身的开销观察，不是可以从最终帧间隔扣除的补偿项。

## 确实执行了什么

开始107个surface、428个原生Bitmap；计时中原生正常预绘新增16块，结束123块、492节点，最大同时离树336节点。16次尾部追加协调通过，四层顺序、非target锚点、原数据及属性检查保持。

计时内716次实际摘下、716次归还，380次归还是B段内原生可见性变为true后的进入恢复；B段确实跨过可见边界，并非空控制。终态像素组件再摘下/归还332个节点，最终累计1048/1048。A末态以及最终clear后held/pendingRestore均0，所有错误数组为空。

`surfacesRetired=nodesRetired=retiredHeld=0`。因此本轮**没有运行覆盖Drop/退休路径**，不能因模型检查或代码存在就称该分支已验。`nodesCreated=492`与`bindingsCleared=492`指观察记录创建/释放，不是新建或dispose原生图像；helper没有复制、替换或销毁权威nativeBuffers。最终映射、数组与观察引用清空，正常计数守恒成立。

## 终态像素与清理

最后连续样本120270ms后，像素组件120273→120495ms；helper内部耗时221ms，全部在性能计时外。用实际世界到Stage矩阵 `(1,0,0,1,-3817,-3477)`，生成2032×1084的原生、摘树、归还三张世界层图片。两项比较均逐像素相同：diffCount=0、maxRGB=0、maxAlpha=0；原图非空，实际摘树332个，3张临时BitmapData全部释放。不是空白图或无摘树的假阳性。

计时末`updates/headChecks=1200/1200`；组件后1202/1200；clear不增加update。终态`valid=true/cleared=true/initialized=false`，held/nodes/surfaces均0，`droppedSkipped=0`，清理报告restored=true。

这只证明终态同帧世界层输出及清理；不等于整条路线逐帧像素验收，也不覆盖SATS、换图、原生整图重绘、特殊视觉模组组合、完整Drop、未知事件监听或存读档。`visualAcceptance/gameplayAcceptance/performanceAcceptance/deployed`仍为false。

## 运行身份与输入证据

隔离AIR PID16324，唯一ID `pfe-modsettings-continuous-motion-5257b15ccf8f480d8baa0a78faeaff5f`，私有桌面 `RemainsTest-814a595ee98f4120a626d343aabbb8eb`。过程记录无其它AIR争用、memoryAbort或runFailure。主执行exit0且自有AIR已退出；共享登记 `f9cfcd3603cd441fbd722d69ed351207` 于18:12:34记为通过并结束，本次复审不重新枚举或控制进程。

运行器已完成前后核验：526正式输入、44脚本输入、3编译输入、10夹具输入、13运行库输入保持；实际隔离输入528项。复审将保留的正式基线与实际隔离清单逐项比较，除预期独立描述符/loader-manifest外均一致；未重新读取游戏或运行库二进制。实际正式宿主仍A796、CS7F1F、RV638E、RC78C。

准确29AF原生SMG的85份冻结源只修改Main并新增helper，形成86份（71个`.as`、15个`.inc`）。本次独立重读这86份冻结文本，全部指纹匹配。原构建回执位于 `probe-builds/probe-source/3cb9de0c91e3453ba29e8bfa2b9c6fdf/probe-build.json`；证据目录的复制回执不代替带相邻编译日志的原路径。

| 文件／工件 | SHA256 |
|---|---|
| helper | `31445D8FB7E96E2822276CE650F42C1B324AF0D3655D169E2CF8598B05F707DD` |
| run.py | `E3EC8531CDF505BE0B85E173F12A1944854DCF4E035BB1073B404A6BB50179DC` |
| probe_patch.py | `BC199A10B5516296AAA766A2067036E246F1F4DB9D7DEB0D06F45B62DFB47BE7` |
| 探针（构建与运行记录） | `40665DD7F9215B9F3A45E08D68078958C614359B49DD2DA6C43FBB7CD464C155` |
| storage/result.json | `BEB611821EA0F8D9C2DDDC90E3E45FF2BCAC43B5A86C14CEDEDC9E041CBB9427` |
| summary.json | `1E485D631E43642252153A8828A88BFF472DFDD68B30BE634A4FA7B9C2776102` |
| process-policy.json | `7AE414C49410A7A7CFB2232627A2C444260F474F8B4C5CD210D8EEE5B17B480B` |
| 证据probe-build.json | `E66B848778C6DBFF30654A497EBD8E691A151BFF8803903F2A91187540FC2F50` |
| runner-inputs.json | `25BA8B844F966CA33BE3699807EBA7E74F1F5C2D94C5A92FD2353690F1210D97` |
| inputs.json | `20EAE9D11D1A4DC442FEBBE8979661517897B810640417DD656868639407108C` |

v1的失败继续保留：109块/436节点，第74次update因正常新增surface而拒绝；0实际摘树、0完整段，不能把那次当负向性能结果。v2解决了该诊断阻断并实际检验远处地形摘树，但结果未达到明显改善门槛，因此不扩建其生产兼容设施，也不重复这一轮挑选有利结果。本次只写本RESULTS，未改冻结代码、旧证据、MEMORY或正式文件。
