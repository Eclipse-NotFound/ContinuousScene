# 真实战斗采样：时间异常诊断

本版继承 sibling v2 的原 4×300 帧真实战斗，仅采每段 age 295 到 age 299 的 5 次主要更新。暂停点仍在最后一帧的 MotionProbe.tick 之前，末帧之后的低优先级监听、EXIT_FRAME、RENDER 不包含在该窗内。10 万条样本上限、溢出处理、finally 停止、原始时间有效性判定及游戏负载均未改变。

只在暂停后的汇总阶段新增 `timeDiagnostics`：混合迭代序列及每种样本的独立子序列计数、有限/正值/倒退统计、最大倒退、每组前 8 个坏例，以及完整 CPU time 和全局样本序号数组。NaN/±Infinity 用明确字符串保留。`positive` 与 `finite` 是独立分类，不把正无穷称作有限正数。

## 2026-10-24 实测结论

证据目录：`mods/ContinuousScene/knowledge/experiments/evidence/combat-sampler-v3-20261024-scene-r1/`。

`storage/result.json` 记录 1200 帧、26 项原战斗断言全部通过，玩家射击 400、敌人射击 1453；采样器原门禁仍失败，不能把游戏负载通过替换为采样通过。

| 窗口 | 总样本 | CPU 样本 | 混合序列倒退次数 | 最大倒退（微秒） |
|---|---:|---:|---:|---:|
| 0 | 52421 | 234 | 11 | 1000 |
| 1 | 53516 | 204 | 9 | 1000 |
| 2 | 51382 | 255 | 13 | 1642 |
| 3 | 53928 | 263 | 17 | 1000 |

本轮所有时间值均有限且为正；CPU、NewObjectSample、DeleteObjectSample 各自子序列均无倒退，异常出现在类型混合后的全局相邻顺序。枚举数量匹配，无未知样本、溢出或超限，四窗停止和 callback 清理全部完成。这些观察不用于修改或放宽原先的跨类型顺序门禁：原 `sampleTimesValid=false`、`combatSampler.valid=false`、`attributionReady=false`、`incomplete=true` 与 `samplerVerification.passed=false` 均原样保留。

同目录 `cpu-occurrence-review.json` 独立核对原始结果、summary、探针与过程文件指纹，明确 `originalSamplerGatePassed=false`，仅 `cpuOccurrenceCountsUsable=true`。四窗合计 956 个普通 CPU 样本，可用于查看完整调用栈或顶层名称的**出现次数**。这是有限的后验读取结论，不是让失败采样器变为通过；不需要重写 v3 或再建 v4。

例如 `[render]`、`[pre-render]`、`[execute-queued]` 顶层出现次数分别为 205、157、93。名称按原样保留，不解释为 GPU、渲染毫秒或整帧占比。只采了 20 次主要更新，含测试探针与运行时观察开销；inclusive 名称会重叠，不能相加。某个 gotoAndStop 出现在 `[execute-queued]` 的祖先栈，只能定位排空队列的调用点，不能据此认定该对象创建了全部待执行动画。

尾 5 帧的原有按键、速度、存活/新观察子弹记录位于 `sampledWorkload`，是更新后的观察，末帧在 pause 后；不等同精确逐帧枪口事件。没有本轮帧率收益结论，没有生产部署。

## 指纹与位置

实际冻结源和完整工具/依赖闭包见证据目录的 `probe-build.json`、`runner-inputs.json`、`inputs.json`。本次回读核对了 review 所引用的五份证据指纹以及 summary 与原始 combatSampler 内容相同。

| 工件 | SHA-256 |
|---|---|
| `tests/SceneCombatSampler.as` | `23D23346E1ECB5A8FD6F811601A59F1F818A9D9CD4151C6E905E48971B344362` |
| `probe_patch.py` | `7B93483296E2CB793C181F6996E251C9E283DCD989A6CA35B906C82D64549991` |
| 正式宿主 | `A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7` |
| 实测探针 | `D1F7A42B300D4F8F90222F6CEE86B40103C4BA9AC10016B7404C33608A0F5029` |
| `storage/result.json` | `3C8A01DA7421593D64B569FB7E343434227E3AD3781CC8F26E51BB5CB96B2C70` |
| `summary.json` | `E02B1E48838780E81AF15937F9E38827417EA31EDC724BEA8218882EE3344A1A` |
| `cpu-occurrence-review.json` | `778237F70F5C04F419475AE8FD3382696EAE83F34862AA99ADD00A543F36B778` |
