# 私有桌面窗口显隐对照（仅诊断）

准确复用已测 29AF 原生 SMG 夹具的 85 份冻结源码。仅修改 `ContinuousSceneMotionProbe.as`，新增 `SceneWindowVisibilityTrial.as`，构建闭包为 86 份；其余 84 份逐字不变。原来源回执为 `camera-atlas-paged-combat-20261025/probe-builds/probe-source/f298932b38e24919991997c68e0a8b8a/probe-build.json`，必须从旁边存在 `compile.log` 的原构建目录核验，不能把证据目录的复制件当可复用构建入口。

四段各 300 帧，顺序为隐藏、可见、可见、隐藏。只对测试自有的 `NativeWindow.visible` 赋值；仍在独立 Windows 私有桌面，不切换桌面，不调用 activate、focus 或窗口模式操作。保留原生 Shift 输入、六名 SMG10 敌人、玩家 ASSR 开火及自然敌人，不逐帧改位置、速度、AI 或显示对象。没有合图、隐藏地形、叶缓存、RC 采集开关或截图。

每次切换发生在原 `caseBegin` 与连续计时起点之后。1200 个连续间隔保留切换、观察、预绘和长帧成本，不扣首帧或段边界。每帧仅记录实际窗口与 Stage 状态及观察耗时。报告同时保存两对正/反顺序、两臂合并统计、逐段真实射击、活动数量、子弹密度、移动与预绘；负载差异仍需单独解释。

`active`、应用活动窗口身份、`onPause`、Stage 大小、帧率、质量、显示状态、窗口 renderMode 或 bounds 的任何变化均列入 `confounds`，使 `visibilityOnlyAttributionEligible=false`。这不会抹去已完成的真实计时，也不会把焦点/暂停变化算作纯显示成本。所有实际 visible 必须符合段目标，最后必须恢复原 visible、pendingRestore=0、无清理错误。原生负载或观察失败保留原始结果与失败原因，不能因正常退出而当通过。

始终标记 `diagnosticOnly=true`、`performanceEligible=false`。私有非当前桌面上的可见窗口仍不等于用户桌面上的实际呈现；本轮不能建立用户 FPS、有效 GPU 后端、画面等价或产品优化收益。NativeWindow.renderMode 是运行时报告的模式，非硬件后端探测。

运行器沿现有测试登记、唯一 AIR ID/独立存储、私有桌面、仅自有进程清理。启动要求至少 4 GiB 可提交和 2 GiB 物理空余，运行时 512 MiB 提交保护不变。绑定正式 526 项输入（A796 / CS7F1F / RV638E / RC78C）及当前 ADL/runtime 13 文件，构建前后、启动前后与结果输入均核验；不修改正式宿主、模组或共享工具。局部 `run_owned` 副本仅新增该诊断的分类，反向还原必须与原函数逐字相等。

本目录准备阶段未编译、未启动游戏。单次登记运行命令（从游戏根目录执行）：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'mods/ContinuousScene/build/generated/window-visibility-native-20261025/run.py' --name window-visibility-native-20261025-r1 --compile-probe --registry-wait 600
```

只复用本目录生成的原构建回执时，将 `--compile-probe` 换成 `--probe-build '<原 probe-source/<唯一目录>/probe-build.json 的绝对路径>'`；新证据名称必须未存在。不会自动连续运行下一轮。`summary.json` 中的通过仅指这一轮环境诊断完整且恢复成功，不是部署门禁。
