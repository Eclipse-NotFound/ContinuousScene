# 旧密集战斗方式的环境对照

只供隔离归因，不部署。原39A探针来自准确B7ED收据的冻结源，不读取当前共享src，不加入cameraHold、隐藏世界或177块新预备。唯一AS差异是测量首尾各一个内存时间记录（Date UTC与getTimer前后夹取），没有新增逐帧分支或写盘。六LMG、ASSR实射、原生Shift、一次定位、四段各300帧及原预热/负载/连续计时门禁不变。

运行预期正式宿主A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7；必须已有verified的scene-tint-deployment回执及通过的正式路径组件结果。CS7F1F、RCDF0F固定，其余实际完整依赖在编译与复用时冻结，变更拒绝混用。相较此前ABE2多了已验证颜色修复，不能声称与历史完全同宿主。

从游戏根执行（由根任务登记并安排；本文准备时未编译/运行）：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'mods/ContinuousScene/build/generated/scene-compat-20261024/environment-control/run.py' --name environment-control-20261024-scene-r1 --mode scene --compile-probe --registry-wait 600
```

第一轮输出准确probe-build.json路径。普通房对照复用该路径：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'mods/ContinuousScene/build/generated/scene-compat-20261024/environment-control/run.py' --name environment-control-20261024-normal-r1 --mode normal --probe-build '<第一轮实际probe-build.json>' --paired-evidence environment-control-20261024-scene-r1 --registry-wait 600
```

normal仍使用原房(2,4)、原路线和地形/视口配对门禁。模式顺序也可反过来。不能把其他来源的probe-build收据或不同正式依赖组合复用进本轮。

外部驱动只包装现有cpu_owned调用，为原有每秒进程CPU样本增加UTC前后时间。原私有AIR、APPID隔离、登记、等待、1秒循环、4GiB提交/2GiB物理启动检查及运行中512MiB提交底线保留。wrapper在finally还原，不改共享脚本。连续1200个间隔包含边界，不删慢帧。

summary.clockAlignment仅累计完整落在测量窗口内的进程CPU间隔，记录UTC/getTimer漂移、末尾记录相对最后样本的延时以及覆盖时长。CPU跨全部线程，不代表主线程；边界不作插值，不从帧时间扣减。该最小驱动不能单独证明整机抢占、缺页、GPU或GC原因。原始测量与失败证据均保留。

预计一次运行约2–5分钟，具体随资源与实测卡顿变化；等待登记不计入。准备阶段只做Python语法、变换可逆和合成时间对齐检查，真实负载结果由根任务执行后判定。
