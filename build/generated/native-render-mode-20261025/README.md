# 传统显示列表的 direct / cpu 单臂隔离配方

状态：仅准备。没有编译、游戏样本、像素等价或性能改善结论；不部署。是否执行由主任务结合前景地形归因结果和已协调的空闲时段决定。本入口每次只登记并运行一个模式，不自动排队第二个实例。

准确复用 `camera-atlas-paged-combat-20261025-r1/probe-build.json`：回执 SHA256 `983727AEB832BC586AF3767613B7C9D61564D92DC9D8E2435F972EEBF1D1D5EE`，探针 `29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5`。核验原 85 文件、原配置/编译日志、原 runner/compiler/candidate 输入和 39A→29AF 三文件来源链。保存原回执原字节，不重编、不把本轮输入冒充原构建输入。

相对 `compile.log` 的原验证器明确传入 `probePath.parent/probe-build.json`，先确认其与固定证据回执字节哈希和对象都相同；不能把证据目录的复制件直接当原构建路径。

原生六名 SMG10 射手、玩家 ASSR、真实 Shift/加速/碰撞/击退与 200px 路线均保留。使用既有 `drawControl=rcnative`：冻结 Main 的 507–514/385–389/1021/1044 行仅在 `rcoffline` 才访问 RC API；961 行让 `rcnative` 跳过整个显示干预分支。四窗均原生可见、每窗 300 帧，共 1200 个连续间隔，不调用合图/隐藏层/新观察 helper。既有空 presenter 的 head/cleanup、计时和统计仍是原探针行为。

`rcnative` 的 AS 断言只要求六敌存活并持枪，故 Python 额外要求每窗玩家和敌人实际射击均大于零，保留每 30 帧六敌武器快照、原 SMG 参数、真实移动与并发子弹门禁。四窗全是同一 renderMode，不能当作同进程 direct/cpu ABBA。

只在 `motion-test.run_owned` 写入唯一实例描述文件的位置作本地函数副本适配：原代码先改 ID/窗口尺寸，再把唯一 `<renderMode>direct</renderMode>` 按需换为 `cpu`。逐字反向恢复必须相等，其余描述内容不变。第二个适配点只在原 finally 删除描述前核对哈希，不增加逐帧工作。原 `motion-test.py` 与 `runtime/application.xml` 不改；保留独立 app ID、私有桌面/存储、共享测试登记、原进程清理和运行中 512MiB 提交余量保护，启动沿用 4GiB 提交/2GiB 物理余量门禁。

证据保留 `application-after-prepare.xml`（原字节）、`application-before-mode.xml`（原代码改 ID/尺寸后）、`application-used.xml`（实际启动路径副本）、`descriptor-review.json`（两组差异、反向校验、实际启动 argv、启动/清理前哈希和仅去 ID/mode 的对照指纹）。另冻结 `adl64.exe` 与指定 `runtimes/air/win64` 下所有实际文件，前后严格相等；不改 AIR、全局配置或画质。正式 526 项输入完整前后核验，当前宿主 A796、CS7F1F、RV638E、RC78C 等固定值变化即拒绝。

这只核验**请求的描述模式**和准确运行时文件，没有新增有效硬件后端探针。`rcnative` 原 process-policy 的历史 RC 字样保留并在 summary 明示，本轮仍 `diagnosticOnly=true`、`performanceEligible=false`。不同进程的 AI/火力/预绘有随机差异；即使耗时有变化，也不等于 GPU 时间、产品 FPS、像素验收或已可部署。后续如需反向顺序，由主任务分别手动登记，不在此入口自动循环。

准备执行时使用本机 Python（每次二选一模式；名字不可重复）：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene/build/generated/native-render-mode-20261025/run.py' --mode direct --name native-render-mode-20261025-direct-r1 --registry-wait 600
```

单独 CPU 臂将 `--mode` 改为 `cpu`，并使用新证据名 `native-render-mode-20261025-cpu-r1`。无编译参数，也无自动第二轮。
