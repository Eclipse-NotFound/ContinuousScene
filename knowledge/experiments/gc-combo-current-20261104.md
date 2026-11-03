被测技能：remains-runtime-debug / remains-auto-testing / remains-mod-build / remains-release-gate / remains-mod-memory
技能归属：Remains 工作区 `.agents/skills`
测试工作区：D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene

# 2026-11-04 GC 周期回收组合治理：干净负载终局裁定

用户指令：先做 GC 周期回收的组合治理。本轮在当前正式栈（宿主 A9B39CC7、CS 0.9.7 447AE02B、FA 0.4.1、ConditionSystem v0.2.1、RConnect gcfit1）上完成组合部署核对、候选四轮配对与当前栈归因。**结论：组合的部署侧已完成（外部三源全消）；自研 env 泵候选 029DAF34 第四次配对无收益，正式关闭不部署；长帧主体不是 GC（29 个长帧仅 9 个邻近 GC）。**

## 1. 组合部署侧核对（无需新部署）

| 泵 | 状态 | 证据 |
|---|---|---|
| AddictionSystem persist 408/帧 + setParameters ~867/帧 | **已消除** | ConditionSystem v0.2.1 替换；v14b 独立复检 24/24 窗确认三项归零（2026-11-02） |
| RConnect NetHud 139/帧 | **已消除** | gcfit1（8AB94C8B）部署；同上复检 |
| FirearmAttachments persist ~226/帧 + Catalog.clone ~152/帧 | **已消除** | FA 仓库 `bb6b3ac "perf: 0.4.1 消除每帧GC分配主链并部署"`，release = 40235F8A（本轮核实） |

## 2. env 泵候选 029DAF34 四轮配对（干净负载，2026-11-04 02:52–03:02）

协议：v13b 探针（每帧 dtMs + System.totalMemory），base,cand,cand,base 交错，非战斗行走 2048×1123、独占 game、独立 AIR ID/存储、静音私有桌面；formal 全量再基线到当前栈（漂移 2 项记录于 lead-inputs.json）。运行器 `run_pair2_current.py`（base=正式宿主 / cand=envkey-cache-20261102/candidate.swf 029DAF34），编排 `gcombo_orchestrator.py`。

| 轮次 | 证据 | GC 掉落 | 掉落体积 | 均值 ms | P95 | >100ms/分 | 峰值内存 |
|---|---|---:|---:|---:|---:|---:|---:|
| base-r1 | gcombo-base-r1-20261104 | 8 | 521.2MB | 38.94 | 57 | 10.05 | 357.5MB |
| cand-r1 | gcombo-cand-r1-20261104 | 7 | 475.5MB | 35.79 | 47 | 10.93 | 362.3MB |
| cand-r2 | gcombo-cand-r2-20261104-x4 | 8 | 561.9MB | 37.44 | 52 | 20.9 | 364.2MB |
| base-r2 | gcombo-base-r2-20261104-x5 | 8 | 536.2MB | 37.45 | 49 | 13.93 | 361.6MB |

**合并：base 16 次/1057.4MB vs cand 15 次/1037.4MB（−1 掉落、−1.9% 体积，噪声级）；均值/P95/长帧频率无一致方向。** 叠加 2026-11-02 两轮（高负载）与 v13 早期两轮，共 8 轮配对零收益。按部署门禁（整帧无稳定收益不部署），**029DAF34 维持不部署**，候选与回执保留。这是"减分配≠减帧时"的**第四次**独立确证，且本轮是干净负载下的最终权重证据。

## 3. 当前栈归因（gcattrib-current-r2-20261104，v14 探针 23/24 有效窗）

采样 313,162 新对象 / 107,898 当窗死亡。主要分配栈：

1. `Grafon.sceneNativeEnvironment < Location.step`：64,104 新（~2,787/窗，96.1% 即死）——仍是第一分配源；消除它（v14b 已证分配 −10%）不动周期节奏，与配对结果一致。
2. 无栈（native 内部）：61,683 新。
3. `[pre-render]`：45,332 新（仅 4.2% 即死，留存型）。
4. **UnitTurret/animate 显示基础设施链**（FocusManager/addEventListener 24,222 + gotoAndStop 9,252 + Sprite/constructChildren 10,116 等，合计 ~4.4 万/23 窗）：垃圾与留存混合；**留存增长最大**（FocusManager 1.96MB/3,303 对象 + gotoAndStop 1.16MB + Sprite 0.45MB）。该链的"同帧守卫"路线已有 6 轮配对负结果（2026-11-02 关闭）。
5. NativeSceneActivity 装箱 13,145；sceneEnsureUpcoming 键 9,422（62.4% 即死）；TDFC sense 5,035 + snapshot 留存 306KB。

**GC 时间线：9 次掉落（各 67–71MB）；>100ms 长帧 29 个，其中仅 9 个邻近 GC（31%）。**

## 4. 结论与停止条件

- **组合治理的部署侧已由各维护者完成**，本会话未新增部署；正式栈保持 A9B39CC7 / 447AE02B / 1CEA74E2。
- env 泵单源修复在干净负载下无 GC/帧收益，**分配削减路线在本模组内正式关闭**（累计四轮配对 + 三条子路线数学/实测关闭）。
- 长帧主体（20/29）与 GC 无关；其来源按既有调查为原生渲染/显示基础设施/系统调度。继续攻长帧需要新的整帧级证据或新路线（如跨窗中寿命对象追踪——曾被采样器 100k 上限阻止），不再重复已关闭路线。
- 过程记录：两次内存守卫自停（用户 Stellaris/WizTree 会话占 7.9GB+1GB 提交，未动用户进程）；v14 探针完整性检查放宽到 AS 源+SWF 哈希（gcattrib_analysis.py 为本地分析工具，构建后可演进）；编排器索引 bug 与 AssertionError 拥堵判定已当场修复。

## 5. 复算入口

- 配对分析：`python build/generated/stutter-opt-20261103/gcombo_analysis.py`
- 归因分析：`python build/generated/camera-gc-source-v14-20261102/gcattrib_analysis.py gcattrib-current-r2-20261104`
- 证据：`knowledge/experiments/evidence/gcombo-{base,cand}-r{1,2}-20261104*`、`gcattrib-current-r2-20261104`、（中止残迹）`gcattrib-current-r1-20261104`、`stutter-opt-timing-cull-fwd-r2-20261104`
