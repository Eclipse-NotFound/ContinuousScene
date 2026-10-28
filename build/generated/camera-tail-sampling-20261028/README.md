# 尾段采样候选：仅源码，未编译、未运行

独立 `ContinuousSceneTailSamplerMod.init(host:*)`，仅导入 flash.*；不改宿主、FA2B 探针或正式模组，不需要 tag93、mm.cfg、PreloadSwf 或游戏存根。文档类 `TailSamplerDoc` 强引用入口类。`compile-command.json` 是待审参数数组，不能当构建回执；`compiler.xml` 沿用已经成功的 AIR 能力探针配置，Java 最大堆 512MiB（不是进程总内存上限）。当前没有 SWF 产物。

每个窗口在本 Stage 的最低优先级 ENTER_FRAME 开始，在下一最高优先级入口暂停，再汇总、stopSampling、clearSamples、清空回调。仅保留 CPU 完整名称栈聚合、CPU/新增/删除/未知条目数、CPU 时钟边界及自耗时；不读或保留 NewObjectSample.object、对象 ID、私有成员或 Sample/StackFrame/迭代器。每窗上限100000条、最多4窗、计划间隔至少1秒。溢出即失效；上限不是内存字节保证。

旧成功入口：`../scene-compat-20261024/sampler-capability/`；采样遍历和清理依据 `../scene-compat-20261024/combat-sampler-v3/tests/SceneCombatSampler.as`，CPU 单类型时间单调规则依据原 `cpu-occurrence-review.json`。不再要求混合 new/delete/CPU 迭代时间单调，也不要求尾段必须出现 fe.* 栈。`valid` 只表示窗口和清理的结构检查；零 CPU 样本时 `attributionReady=false`，仍保留观察并继续计划，不作任何耗时归因。

## 隔离接入：由主运行器完成，不另造运行框架

1. 新后继运行器复用现有 `m.prepare()`、`m.run_owned(...)`、登记/资源门槛与静音 helper。不要原地修改已执行的 silent/current 配方，也不要将采样结果并入另一代理的无采样基准。
2. `m.prepare()` 返回后，把新编译物复制到 **隔离** `m.RUNTIME/mods/ContinuousSceneTailSampler/release/ContinuousSceneTailSamplerMod.swf`；仅向该副本的 `mods/ModLoader/supported-mods.txt` 加 `ContinuousSceneTailSampler|ContinuousSceneTailSamplerMod|1|0|0`。仿照 `motion-test.py::prepare`，再调用既有 launcher 的 `--root m.RUNTIME --only <原选择加 ContinuousSceneTailSamplerMod，以逗号连接> --no-ui --report <新回执>`。不要手改生产清单或宿主；新清单、SWF、运行时 plan 和本目录5个源/配置文件进入新运行输入闭包。
3. `m.run_owned` 创建唯一 descriptor 后，在已有 `m.HiddenProcess` 包装器的真实创建边界、`original_process(...)` **之前**，从 descriptor 解析 exact app ID，写隔离根的 `tail-sampler-plan.json`。addon 的 plan ID 必须与当前32位UUID的 motion applicationID 全等。沿用前置 `silence.seed(descriptor, m.RUNTIME)` 和资源检查。
4. 计划格式如下。时间是游戏 `getTimer()` 毫秒，**不是距 addon 初始化的延迟**；以下时间仅示例，须按本次无采样基准决定，不能承诺必落在计时段。

```json
{"version":"camera-tail-sampling-plan-1","applicationID":"pfe-modsettings-continuous-motion-<本轮32位小写hex>","tailAtMs":[45000,55000,65000,75000]}
```

5. 原运行器保留 storage 时一起保留 `tail-sampler.json`。独立检查实际 `[startAfterMs,endBeforeMs]` 完全落在已完成的战斗段，按真实 `sampleAtMs` 归段；不能通过计划时间猜测 phase/held。不足覆盖就是未完成。每窗有效须 next-head 序号加1、条目守恒、CPU时间有效/单调、没有溢出/错误、显式 stop/clear/callback 清理；另核 loader 实际成功、addon SWF/plan/宿主输入及原工作负载断言。

## 解释边界与开销

同优先级按注册顺序；旧 FA2B 的最高优先级 absoluteStart 可能在新 addon 的 pause 之前执行。Stage 优先级不能保证所有子 DisplayObject 的广播结束，故只能称“本 Stage 尾入口→下一头入口”，不能称纯渲染、native 或 GPU 独占。

旧五帧采样每窗约5.1–5.4万条、汇总229–274ms，start调用0–3ms、pause整数计时0ms；采样本身总扰动未有无采样对照。新窗口短也不能预报实际成本。JSON保存和汇总都在暂停/停止后；它们仍影响后续游戏间隔，不能从帧率中扣除。saveMs仅能记录先前写盘的耗时，最终一次写盘耗时不在自身JSON中。全轮 diagnosticOnly/performanceEligible=false，不验收帧率。

可观察命名AS调用、排队脚本与[pre-render]/[render]/回收标记的出现情况；不能得到GPU毫秒、所有线程耗时、缓存失效范围或OS真实呈现次数。当前只是候选源码，准确编译语法、独立addon装载和真实单间隔采样尚未验证。
