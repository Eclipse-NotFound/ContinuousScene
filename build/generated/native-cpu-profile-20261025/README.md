# Native CPU offline consumer

仅使用已存在的 Microsoft TraceEvent 3.1.13 公开 API 读取保存的 ETL；不录制、不控制 ETW、不下载符号、不启动游戏。PowerShell 7.6.5 / .NET 10 可加载该 netstandard2.0 库，不需要 SDK。

库：`C:/Users/hello/.nuget/packages/microsoft.diagnostics.tracing.traceevent/3.1.13/lib/netstandard2.0/Microsoft.Diagnostics.Tracing.TraceEvent.dll`，同目录 FastSerialization DLL。`TraceLog.CreateFromEventTraceLogFile` 在全新输出目录生成 ETLX，原 ETL 保持共享只读锁并核前后 SHA；不在原 ETL 旁写派生文件。

调用（以下是接口示例，未录制或验证真实 ETL）：

```powershell
pwsh -NoProfile -File ./read-trace.ps1 -SmokeOnly -OutputDirectory D:/path/new-smoke
pwsh -NoProfile -File ./read-trace.ps1 -TracePath D:/path/saved.etl -TargetProcessId 12345 -StartMs 5000 -EndMs 15000 -OutputDirectory D:/path/new-analysis -Top 30
```

`StartMs/EndMs` 必填，均相对 ETL SessionStartTime，范围 `[StartMs,EndMs)`；不是游戏 getTimer 或 UTC 数值。PID 必须是登记的自有测试进程，保存其身份与采集时间锚点。末点超出 ETL 时长拒绝，不自动裁短。

`smoke.json` 仅证明程序集加载、公开重载、禁符号选项可用，`actualEtlRead=false`。`summary.json` 输出目标 CPU SampledProfile 记录数、原采样间隔、时间覆盖、线程/叶模块/叶地址/前 N 栈、丢事件/截断、无模块/无栈比例。每事件按 1 条计数，payload Count 另记；不直接换算墙钟或 GPU 时间。事件实例不跨迭代保存。

`passed` 要求采样存在、PID 只对应一进程实例、时间有效、无丢事件/截断、原 ETL 未变；不等于栈可用、符号可用、性能优化或游戏验收通过。`stackAttributionAvailable/moduleAttributionAvailable` 另列且无数据不伪通过。异常仍留 summary 和转换日志；原始 ETL/ETLX不删。ETLX 为库对全日志建立的索引，输出统计仅目标 PID/时间段，不输出别的进程详细信息。

当前主会话未获管理员 token，未启动 ETW；本交付只做 API 冒烟，不造假 ETL，不扩展采集器。将来记录需另走测试登记、内存/进程保护与采样完整性检查。WPR CPU.Light 无堆栈；本机 CPU.Verbose.Memory 显示 1615×1024 KiB 系统缓冲，不能未经资源核对直接套用。
