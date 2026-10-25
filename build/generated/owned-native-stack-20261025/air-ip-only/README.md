# 自有 AIR 活跃线程 IP 观察：仅源码准备

当前未导入本适配器执行、未运行游戏。接口仍是 `OwnedAirSampler(process, expected_exe, expected_descriptor)`、`prepare()`、`sample(max_threads=2)`、`summary()`、`close()`。调用方在新建 HiddenProcess 的 15 秒内绑定，约 35 秒 prepare；既有 runner 负责游戏退出、私有桌面清理与共享测试登记。

## 来源和本轮差异

归属/退出/清理逻辑复用只读冻结的 `../air-owned-v2/adapter.py`，SHA256 `50211888bd0573646bb7be8a125c58a70600ecf6569f18489f41b89b18de01a6`。该来源又固定 `../owned_native_stack.py` SHA256 `91694dd28f399bc198051c50438897bc3165783d658ca8c896124b76ae4515e7`。均在内存中校验/编译加载，不导入旧 runner，不产生缓存文件。来源任一变化直接拒绝；集成 runner 应冻结这三份源，不仅本文件。

沿用 v2 的精确 HiddenProcess 类型/源码位置、原句柄、PID、创建 FILETIME、父 PID、adl64 映像、预期描述符、私有桌面启动名称和 AMD64 校验。沿用实例正常退出竞态记录和 fatal RuntimeError 进入原 runner finally。只关闭本方 OpenThread 句柄，不结束进程。**不调用 GetThreadDesktop**；私有桌面启动得到核验，当前每条线程的桌面未核验，保持原 v2 的限制。

本文件覆盖原 prepare、sample、capture、summary：

- prepare 仅一次线程清单与持久句柄、模块名称/基址/大小清单；不读模块映像字节、不建函数表、不复制栈、不调用任何 unwind。
- 每次 sample 只读所有初始持久线程句柄的 GetThreadTimes，保存每条的读取前后时间、累计用户/内核 CPU、上一次读取点、当前与此前窗口差额。未选线程也保留完整原始行；第一次没有可比增量时返回 pending，不强行选静止线程。
- 第一名取当前窗口 CPU 增量最高的正值线程（并列按 TID）；另一名在其余“当前或上个窗口曾有正 CPU”的线程中按固定 TID 环形顺序公平轮转。完整记录全排名、候选池、入选理由。一次最多两份，实际取到的 RIP 总数上限 160。
- 暂停区只进行 SuspendThread、GetThreadContext(CONTEXT_CONTROL)、读取寄存器 RIP、finally 中一次 ResumeThread；所有缓冲区提前分配。没有 ReadProcessMemory、VirtualQueryEx、栈副本、模块段复制或 StackWalk64 调用。基类定义这些能力不意味着本派生路径会调用它们。
- 初始线程退出时，能读取则保存最终累计 CPU、退出 FILETIME 和区间缺口，随后退役；不重用其 TID、不发现新线程。CPU 读取后至取 IP 前退出会明确记 skip，后续窗口再记录最终计数。
- 每 16 份 IP 在下一回调复查模块清单；变化则中止旧映射并回标最近检查后的样本。未检查尾部与检查间隔内映射继续标未知。

## 可解释范围

这些是主动偏向近期繁忙线程的墙钟位置样本。IP 出现次数不是 CPU 百分比、等待时长或 GPU 证据。上秒繁忙的线程在取样时可能已经等待；独立 CPU 计数与瞬时 RIP 必须分开解释。

“全员 CPU”仅指最初准备时持有句柄的线程，不是整个进程所有生命周期线程。新线程、第一次计数以前、最后计数以后均可能有缺口；原始进程 CPU 计数另存，逐线程读取还有时间错位，不能把两者直接相减称精确漏计。读取本身的起止与总耗时都保留，不作为生产性能验收。

验证停点：只进行 AST 语法检查和源码调用路径检查，尚未执行新适配器。前一版原生栈的成功样本不能当成本版实测，也不再用于推断忙线程调用链。
