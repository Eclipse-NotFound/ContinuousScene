# 短窗真实战斗采样

承接 sibling `combat-sampler`。v1 每段60更新得到约72万条总记录，超过100000上限，未形成画像；失败保持原样。

本版只把每段采样起点由age240缩到295，结束仍是age299的MotionProbe.tick前，共5次主要ENTER_FRAME更新。原4×300帧战斗、双方真实开火、按键/物理、十万条上限、溢出判失败、暂停后汇总和finally停止均不变。末帧更晚的低优先级/EXIT_FRAME/RENDER不纳入。

helper A8EFE704CF2904D4CFBDD3F642F66AF77439CBF7479A986C3E0E68E3F913E11F，patch DF1A393717FCFE4B40B2F9AB143B1AB601BDD88B6606BE21E3BCDA7E060D92EC。独立复核限定差异和runner接口。运行后summary额外摘录每段295..299的原生速度、按键、存活弹体和观察到的新弹体；它们是更新后的观察，末帧在pause之后，不等同精确逐帧出膛事件。

结果用于短窗 AS 调用栈调查，不能换算绝对 CPU 时间、完整帧耗时、渲染线程或 GPU 份额。全部采样轮保持 diagnosticOnly=true、performanceAcceptance=false；正式游戏和模组原样复制，保护和独立存储沿用 v1。

## 2026-10-24 实测停点

证据目录：`mods/ContinuousScene/knowledge/experiments/evidence/combat-sampler-v2-20261024-scene-r1/`。`storage/result.json` 的 1200 帧、26 项原战斗断言全部通过，玩家射击 400、敌人射击 1758；这不等于采样器通过。

| 窗口 | 总样本 | 普通 CPU 样本 | 含 fe.* 名称的 CPU 样本 |
|---|---:|---:|---:|
| 0 | 57685 | 333 | 218 |
| 1 | 50778 | 209 | 97 |
| 2 | 53920 | 224 | 104 |
| 3 | 54656 | 216 | 99 |

四窗均完整覆盖约定的 5 次主要更新，枚举数量与报告数量相符，无未知样本类型、溢出或超限，停止与 callback 清理成功。但四窗 `sampleTimesValid=false`，因此原始 `combatSampler.valid=false`、`attributionReady=false`、`incomplete=true` 与 `samplerVerification.passed=false` 保留不变。这里的 gameNames 门禁失败是组合判定结果，不能误读为没有 fe.* 调用栈。

v2 没记录坏时间的样本类型与倒退幅度，不能从这轮解释时间异常；后续只在 sibling v3 增加暂停后的时间诊断，没有降低 v2 门禁或修改原证据。未部署任何优化。

关键 SHA-256（完整冻结源见本证据的 `probe-build.json`）：

| 工件 | SHA-256 |
|---|---|
| 正式宿主 | `A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7` |
| 实测探针 | `C356019160CA32ECC03D575C1BFE7F400115FCBE3DF78145A9F23626E86A6613` |
| `storage/result.json` | `4C6E804375B4073E10B44EB036DEC1F031DEAAE92A247C7B2E8E11A727F174BD` |
| `summary.json` | `C61DD620E6B6EC66BE6ABDF2E23B1CFD383DF998639DDFADCD5C111A11D9651B` |
