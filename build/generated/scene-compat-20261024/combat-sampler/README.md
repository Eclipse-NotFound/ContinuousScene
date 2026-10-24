# 当前正式游戏的短时调用栈采样

只用于寻找真实战斗中的 AS 热点，不接受性能、部署或渲染线程/GPU 归因。

使用 B7ED 回执冻结的 39A 探针源码。85 个原文件中仅 MotionProbe 增加可逆采样挂点，另增加 tests/SceneCombatSampler.as；原 4×300 帧真实 Shift 输入、玩家 ASSR、六敌 LMG、连续时间和所有长帧保留。宿主 A796、CS7F1F、RC78C、RVBF4A、TDFC7ACD、ModLoader2050 从正式文件原样复制。

每段 highest ENTER_FRAME 的 age240 开始，age299 的 MotionProbe.tick 第一项暂停，共覆盖60次主要更新；最后一帧更晚的低优先级监听器、EXIT_FRAME、RENDER不含在内。每窗暂停后汇总并停止，不持有已停止缓冲的迭代器。原5秒心跳仅在采样时延后到暂停帧。前三次汇总开销留在下段首个连续间隔中，最后汇总位于末个测量时间戳之后；整轮帧率不能当优化成果。

普通 CPU Sample 保留完整名称栈、栈顶和含该名字的样本次数；new/delete只计数，不读对象引用。保留空栈、匿名、探针、Flash API、literal native标签，不将它们直接当成渲染耗时。关闭内部对象分配采样不等于关闭所有AS分配采样。每窗100000条上限、溢出或未知类型均失去完整性；四窗必须全部有真实fe.*命名栈且完成清理。

先行能力探针 `../sampler-capability/runs/sampler-capability-r2-e5eeb47418764e4a9bce2920051dcb6f/` 已在实际 AIR runtime 下得到222条CPU且全部包含knownHotLoop。r1编译失败完整保留。此能力证明不等同于游戏画像通过。

根使用 run.py 登记、4GiB提交/2GiB物理预检、512MiB运行保护、私有桌面与独立app存储；不得写正式包、真实存档或结束其他实例。

scene-r1失败完整保留：前两窗 reportedSampleCount 为719823/713632，超过100000上限，未枚举、未形成CPU画像。第三段age280玩家X4299.1098越出核验left4305，当时dx=-29.7256，原因未定；没有重置位置掩盖失败。终态清理stopped/callbackCleared为true，active为false。后续缩至每窗5次主要更新的独立方案在 `../combat-sampler-v2/`，本目录及旧冻结源保持。
