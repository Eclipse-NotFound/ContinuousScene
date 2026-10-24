# TDFC LOS 战斗开关归因（已运行，无明确整体收益，不部署）

2026-10-24：combat-r1编译后因可提交内存不足4GiB在AIR前停止；combat-r2复用同一A170B7EB探针完成1200连续帧、26项检查。关闭/开启均帧61.3067/60.4717ms，玩家全轮400发（两臂各200），敌1010/904发，关闭臂另有4块23次预绘片段、开启臂无预绘。开启臂8129次优化调用、101166次空格复用、44804次查格，证明路径确实运行，但0.835ms差额不能归因于缓存。公开开关完整恢复，正式TDFC未改。原始证据位于 `knowledge/experiments/evidence/tdfc-los-20261024-combat-r2/`，独立核验和边界见 `knowledge/experiments/scene-compat-20261024.md`。

准确 39A 战斗探针的 85 文件冻结源，B7ED 收据逐项验证。只修改 `ContinuousSceneMotionProbe.as`；不使用当前 CS src，也不使用终端组件探针。宿主固定 A796、CS7F1F、RC 78C052、原正式 TDFC7ACD；只有隔离目录 TDFC 换成已通过 38 例原生组件的同一候选（完整递归22份源，21原件不变）。其余实际安装输入完整锁定，数量不硬编码。

RC 来源锁定 roomfix5 正式部署回执 `16EF10BA…EABE4`，核旧 DF0F 备份、新 78C052 候选、实际安装文件及回执前后依赖仅 RC SWF 变化。用户已要求先部署，回执明确 `user-requested-installed`、`smoke_status=pending`；本对照保留 `rcSmokeVerified=false`，不以 TDFC 组件或性能结果为 RC 功能背书。若回执后续更新，即停止并明确重新审查，不静默接受新的 RC 或其它依赖。

RC 部署之后，ModLoader 已独立正式更新 BD71→2050（2.5.0），`recorder-checks.json` 的精确 `9C624ECB…85E63D` 回执中 `deployment.status=verified`，安装后 FrameRecorder.active=true。运行器核当前安装与备份，仅允许 RC 回执 after 列表到当前运行输入中的这一个已证明 ModLoader SWF 变化；全部其它实际运行输入仍完整冻结。新组合带帧记录器，其观测证据来自 ModLoader 部署检查，本探针未新增记录器 API 采样，不把此前 DF0F/BD71 数据作为直接因果对照。使用根在当前组合重新构建并运行成功的组件回执，不修改旧构建回执或创建运行重绑定。

四个原始 dense-native 窗口各 300 帧，按 A/B/B/A 设置 false/true/true/false。真实方向键、加速、冲刺、击退、六个原生 LMG 敌人与玩家 assr 射击均保持原夹具；玩家要求共 400 次原生射击。没有新增全图预热、镜头固定、地形改写、AI 调整或 RNG 调用。

唯一新增战斗控制在窗口边界，读取真实 `ContinuousSceneTdfcThreat.api` 的 public QName 属性并校验版本、carrier/API 身份。计数仅做累计差值，不复位；关闭臂计数不增长不代表原版没有 LOS 调用。正常结束与异常 `finish` 都以 finally 恢复原公开开关；原 API 被第三方替换时只恢复我们实际改过的 API，并拒收本轮。

保留全部 1200 连续区间；开关与段间计数开销在连续时间内，末段最后计时点之后的读数、普查和清理明确在计时外。复用环境对照的两个时钟锚点与进程 CPU 对齐，没有逐帧新增观察。A/B 分别报告墙钟、调用/命中/查格、活动人数、火力、弹体、实际速度和预绘。四个时间段的自然人口与火力并不相同，不能单用汇总均值认定因果改善。

本轮没有数值收益门槛，不作为发布验收。B 必须存在实际优化调用、命中与查格，全部原密集战斗有效性仍必须成立。候选默认关闭，第一次 B 的类身份缓存初始化成本保留在计时中。

根调度命令（本子任务没有执行）：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'mods/ContinuousScene/build/generated/scene-compat-20261024/los-combat/run.py' --name tdfc-los-20261024-combat-r1 --candidate-build '<新RC与ModLoader组合38例已通过的candidate-build.json绝对路径>' --component-evidence tdfc-los-20261024-components-r6 --compile-probe --registry-wait 600
```

重复运行需使用同一 `--probe-build`，新证据名称。`--candidate-build` 必填，脚本没有重新编译 TDFC、发布或改正式配置的入口。
