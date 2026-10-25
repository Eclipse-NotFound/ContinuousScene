# AIR 自有实例适配器：仅源码，尚未运行

`adapter.py` 不启动程序、不接受 PID、不附加任意进程、不结束进程或桌面。该文件只作根任务独立审查与 runner 集成准备；Python 夹具上的通过不等于这个适配器已在 AIR 验证。

接口：

- `OwnedAirSampler(process, expected_exe, expected_descriptor)`：在调用者新建 `air_test_process.HiddenProcess` 后 15 秒内绑定。可在第一次 `cpu_owned` 回调构造。核对精确类型/源位置、原句柄、OS 映像为预期 adl64、启动参数末尾为预期 XML、创建 FILETIME、父 PID 为当前 runner、私有桌面名称、AMD64。
- `prepare()`：仅一次，可在约 35 秒时执行。一次 Toolhelp 线程清单，逐线程归属/创建时间/私有桌面检查，持久保存线程句柄；有界缓存 PE 只读映像和函数表，并记录完整准备时间/缓存失败。映像段字节预算 128 MiB；PE 头、函数表副本及 Python 对象另占内存，这不是严格进程驻留上限。模块清单在准备末复核。
- `sample(max_threads=2)`：每次 1–2 个线程，按最初清单轮转，总上限 160 份；每份重新核对原进程/线程身份和桌面。原线程退出会记录并退役，不使用同号新线程，不再枚举新线程。挂起、取上下文和最多 64 KiB 栈后恰好恢复一次，所有离线栈展开在恢复后。返回具体时间界限、GetThreadTimes 累计值/距此前样本差额、挂起/恢复计数、暂停时间、IP 和栈、解析耗时与错误。
- `summary()`：读取本地证据，不查询目标进程；进程已退出/已关闭后也可调用。包含初始模块清单及最近成功复查时刻，不声称退出前全程不变。
- `close()`：只关闭本适配器 OpenThread 得到的句柄；不读取或结束原进程，不关闭桌面，不额外 Resume。可在原进程退出后调用。准备失败会立即清理本方部分线程句柄。

每积累 16 份样本，在下一轮开始前复查一次模块清单并单列耗时；变化时把上次成功检查后的样本标为映射失效，抛出 `SamplerFatalError(RuntimeError)` 中止旧缓存采样。两次检查之间可能短暂装卸同一地址，不能证明绝无变化，所有样本都明确标注“最近检查时有效，非逐样本保证”。未知 JIT 地址直接停止，不猜函数角色。

退出竞态单独记录：runner 在 poll 后等待期间，实例可能正常退出。适配器若核实仍是原句柄/PID/FILETIME 且已退出，则返回 `process_exited=true`、`stop_sampling=true` 并保存 lifecycle_events，停止后续采样，不称归属变化或新的运行失败。若目标在取上下文与恢复之间退出，仍保留恰好一次 Resume 尝试及其结果；不能确认恢复计数的样本标 `resume_balance_unverifiable_target_exited`，绝不写成恢复成功。正常退出也不能补齐最后一次模块复查之后的映射证据，末尾样本保留未知标志。

归属不符、已有挂起计数、GetThreadContext/栈读取失败、恢复计数异常均不能静默降级，抛 RuntimeError 进入现有 motion-test 的异常/finally。`sample` 内部保存部分证据后抛出；离线解析失败则保留真实 IP 和明确错误。`motion-test.py` 只吞 OSError 的 CPU 采样错误，因此集成时不得把这个 RuntimeError 再吞掉继续采样。

调用者必须在自己的 finally 中执行 `sampler.close()`，再保存 `sampler.summary()`；已有 `motion-test.py` finally 负责 `process.kill()/wait()/close()` 及登记释放。若构造失败，对象没有线程句柄；若准备/采样失败，仍须让原 runner 清理其自有游戏实例。不复制夹具的 terminate/job 逻辑，也不修改公共 `air_test_process.py`。

建议集成顺序：第一次 CPU 回调绑定 → 35 秒准备（先于测量窗口）→ 后续约每秒轮转两份 → 总数上限或实例退出 → finally close/落证。准备、模块复查、取上下文、栈解析都是观察扰动；此轮应标诊断，不得把测得帧率用于收益验收。只有 CPU 差额可描述区间执行时间，等待栈出现次数不能变成 CPU 百分比。新生线程与首次准备后变化模块均属于局限。

源依赖：同级上层 `owned_native_stack.py` 固定 SHA256 `91694dd28f399bc198051c50438897bc3165783d658ca8c896124b76ae4515e7`；加载时校验，并直接内存编译，不产生缓存文件。它的符号引擎、PDB、网络符号功能均未启用。当前仅 AST 语法检查通过，未导入适配器执行、未运行 AIR。
