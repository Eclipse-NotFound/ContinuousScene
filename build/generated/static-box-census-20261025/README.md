# 原生路线终态静态 Box 清点（准备中，未编译/运行）

准确来源为已经验证的 29AF 原生 SMG 夹具：`camera-atlas-paged-combat-20261025/probe-builds/probe-source/f298932b38e24919991997c68e0a8b8a/src`，85 份冻结源。来源证据回执 SHA256 `983727AEB832BC586AF3767613B7C9D61564D92DC9D8E2435F972EEBF1D1D5EE`，原探针 `29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5`。复用 `window-visibility-native` 的准确来源验证与已审查隔离运行设施，**不使用其显隐改动**。

闭包只修改 `ContinuousSceneMotionProbe.as` 并新增 `tests/SceneStaticBoxCensus.as`，共 86 份源；其余 84 份逐字节保留。`probe_patch.py` 每条替换要求唯一锚点，反向还原必须与种子 Main 文本完全一致。helper 由 compact_lineage 独立维护，runner 在其最终冻结后绑定 SHA，尚未绑定时拒绝构建。

## 观察内容与坐标

mode 固定 `rcnative`，四段各 300 帧。原生 Shift 输入、六个 SMG10 敌人、玩家开火、AI、物理、镜头和全部显示对象原行为保留；没有 IP/线程采样器，没有可见性切换、合图或摘树。旧运行器默认的进程总 CPU 读取不变。

种子 `tests/SceneNativeCropChecks.as:111` 的真实相机设置明确 `w.visual.x/y = cam.vx/vy + quakeX/Y`、`w.visual.scaleX/Y = scaleV`。仅从 cam.vx/vy 推算会漏震屏及父层变换。本轮读取 `w.visual.transform.concatenatedMatrix` 的副本并求逆，将舞台四个角变换到 `w.visual` 坐标，记录完整 AABB；不会给原矩阵或显示对象赋值。全舞台 AABB 在裁剪/旋转情况下是保守覆盖，宁可多排除箱体。

每个原计时帧在其 `now=getTimer()` 之前记录一次，共 1,200 次；每段开始另存边界视口，共 4 次。每条保留舞台尺寸、逆矩阵六值及 left/top/right/bottom，runner 独立重算四角与全部并集。还记录观察耗时；1200 连续间隔保留记录、分配、预绘、段边界与长帧，不扣减任何时间。

`finish()` 先执行原 `closeProbeTiming(true)`，随后（完整4段且无既有错误时）调用 `tests.SceneStaticBoxCensus.read(w, unpaddedViewportUnion)`。传入 1,204 个视口的未扩张并集，helper 自行外扩 320，终态保存起止时间。runner 核对 helper 使用的原矩形、外扩矩形、计数、结束时间位于最后样本之后，以及只读/上下文保持标记。不能把最后一帧的视口冒充整条路线范围。

helper 已冻结为 `static-box-census-2`，SHA256 `E2653F4431A6242C23F67D1444FDC4346F3AE58CE9401100B84A1AEB497C5AE7`。以 `loc.objs` 数组为归属源，同时交叉读取 firstObj 链，报告 arrayOnly/both/chainOnly 与 in_chain 实际值，不把 false 自动作排除。还保留关键字段类型分布和被排除的多帧主体实例。其限定资格和未知项处理以冻结 helper 为准。零个结构候选也可以是一次完整清点；完整快照不代表摘树安全、多帧时间轴可以停止、玩法保持或性能改善。

## 运行设施与冻结

运行器保留共享登记、唯一 AIR ID/独立存储、私有桌面、只清理本次自有进程。启动内存门槛与运行时 512 MiB 提交保护不变；未导入 IP/线程观察器。局部 `run_owned` 副本仅替换 rcnative 的诊断说明，反向还原必须与公共函数一致；公共脚本不写。

未来获准执行时，构建前后/启动前后冻结并核对：脚本与具体配置、526 项正式输入、ADL/runtime 13 文件、完整85源来源回执与最终86源快照。实际隔离输入只有原登记设施允许的描述符/名单与本轮探针差异；正式宿主与 release 不修改。复用构建必须传原 `probe-build.json`（位于 compile.log 所在目录），不能用证据复制件伪装。

本目录当前仅源码准备与离线检查，没有编译、AIR、部署或正式输入冻结实测回执。后续单轮入口为 `run.py --name <全新证据名> --compile-probe --registry-wait 600`；此说明不表示本轮已执行。summary 始终 `diagnosticOnly=true`、`performanceAcceptance=false`、`detachEligible=false`，不设合格帧率或正样本数量要求。
