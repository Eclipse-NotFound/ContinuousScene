# 自有进程原生执行位置诊断准备

日期：2026-10-25。范围仅本目录新建的 Python 工作进程；不接受 PID，不启动或读取游戏，不操作已有进程。此工具不是游戏测试、性能收益验收或 CPU 采样分析器。

## 可行性与官方依据

- [GetThreadContext](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadcontext) 要求先暂停目标线程，运行线程的上下文无效。[SuspendThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-suspendthread) 返回原挂起计数；[ResumeThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread) 只撤销本次增加的一次计数。不得用重复 Resume 去清除别人的挂起。
- [StackWalk64](https://learn.microsoft.com/en-us/windows/win32/api/dbghelp/nf-dbghelp-stackwalk64) 接受调用者提供的内存、函数表和模块基址回调；hProcess/hThread 可为自定义标记。这里不初始化符号处理器，不调用 Sym* API，不打开 PDB，不使用符号服务器或网络符号路径。仅从 System32 加载系统 DbgHelp。
- x64 [CONTEXT](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-context) 为 16 字节对齐的寄存器结构。本工具仅支持原生 AMD64 Python/子进程，拒绝 WOW64/ARM64。
- 函数表采用已载入映像中的 [RUNTIME_FUNCTION](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-runtime_function) 三个 RVA 字段；模块和地址输出不依赖函数名称。无 PDB 时不能承诺函数名、源码行或完整调用链。
- [GetThreadTimes](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadtimes) 取得用户态与内核态累计执行时间。该差额单列；暂停时看到的等待栈是墙钟抽样，不能把其频率直接换算成 CPU 百分比。

## 安全和证据边界

1. 唯一入口 `--smoke-owned-child`，只启动同目录 `worker.py`。保存 Popen 原进程句柄，并核对 PID、精确创建 FILETIME、可执行文件、AMD64 架构；每次采样前重新核验。线程句柄还核对所属进程、TID、线程创建 FILETIME 和未退出状态。没有 OpenProcess、按名字找进程、外部 PID 参数。
2. 自有子进程在工作负载开始前加入 KILL_ON_JOB_CLOSE 作业。父进程异常退出时系统也会清理它。正常及异常路径均使用本次原句柄清理；不操作其他进程。
3. 所有缓冲区预分配。每次成功 Suspend 恰好对应 finally 中一次 Resume；已有挂起计数非零则拒绝采样，仍只撤销自己的那次。挂起期间仅 GetThreadContext、VirtualQueryEx 和最多 64 KiB ReadProcessMemory，随后立刻恢复。无文件、符号、等待、游戏调用和目标进程锁操作。
4. 挂起时复制栈；恢复后用该副本解析。模块数据在采样前复制，只限 PE 头及只读映像段，映像段字节预算 128 MiB；PE 头、函数表副本与 Python 对象另占内存，不是严格进程驻留上限。不读堆或可写全局段，不生成全进程转储。调用栈回调只读本地副本，使用不是真实进程句柄的标记，解析阶段不再读目标。原始栈和映像字节不写报告。
5. `StackWalk64` 有界最多 24 步，遇未知/动态地址、读不到数据或解析失败即停止；保留真实 RIP（当前指令地址）。不把 AS3 JIT 地址猜成原生函数，也不把模块名称猜成线程职责。模块清单前后比较；变化时本次整体不通过。
6. 冒烟交替采 busy 与 sleep 两线程，另有一次故意在取上下文后抛错，验证 finally 恢复及恢复后 busy CPU 继续增长。该夹具验证工具能力，不能说明游戏中的任何线程开销或镜头原因。
7. 不使用 SetThreadContext、WriteProcessMemory、DebugActiveProcess、注入、管理员 ETW、桌面切换或联网符号。没有逐调用网络监控，因此“未配置/调用符号服务”与“系统全部网络活动为零”不是同一结论。

## 运行和验收

只允许本轮本目录的能力冒烟；未来接入游戏必须另行实现归属证明、共享测试登记、实例清理以及采样扰动门禁，不能把这里的 fixture 限制直接删掉改成任意 PID。

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene/build/generated/owned-native-stack-20261025/owned_native_stack.py' --smoke-owned-child
```

生成新的 `smoke-<唯一编号>.json`，保留失败而不覆写。重点核对 `balanced_suspensions`、每次挂起耗时与读取字节、故意失败后的 CPU 进展、模块清单稳定、原生执行地址、调用栈是否仅单帧及 `cleanup.child_exited`。即使调用栈不能展开，可靠执行地址仍可用于后续限定模块级调查。

## 本轮能力结果

最终源码冒烟 `smoke-ca3c6aa0e2ae4c8c8f1fbe704a886f56.json`：新建 PID 34572，精确创建 FILETIME 134373877185880956，12 次正常取样全部得到 RIP 及 16–20 层模块/RVA 调用栈；没有模块读取或回调读缺失。只读映像缓存 19,038,493 字节，16 个映像、16 张函数表，前后模块清单一致。

13 次挂起（含一次故意异常）均为原计数 0、恢复前计数 1。正常暂停 0.0464–0.1872 ms，实际栈 2,720–2,960 字节；故意异常路径暂停 0.042 ms，随后 busy 线程又累积 109.375 ms CPU。814.1728 ms 观察窗中 busy 累计 812.5 ms CPU、sleep 为 0。这里只用于检查观察对象区分和异常恢复，不是时间精度或采样开销的统计基准。

finally 已结束本轮子进程，`cleanup.child_exited=true`；退出码 1 来自预定的自有夹具 terminate 清理，不是工作负载自然退出。第一轮 `smoke-3d61c417136d4c3993525dec52d6345a.json` 也通过，保留其修订前源码哈希，不冒充最终版本。

最终 helper SHA256：`91694dd28f399bc198051c50438897bc3165783d658ca8c896124b76ae4515e7`；worker：`f1c886e3a6e15baaa7e6bf41299ad419280cfad1ba40e1e57ef100c6fccdf035`。报告记录与当前两文件一致。没有运行 AIR、读取游戏 SWF 或触及已有进程。本结果仅证明限定夹具上的能力，未知动态/JIT 栈、其他模块布局和真实游戏采样扰动均未验证。
