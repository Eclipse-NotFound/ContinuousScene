# TDFC 单条视线内空格复用（仅隔离源码候选）

2026-10-24：准备源码，**未编译、未运行、未证明性能改善、不得部署**。本目录不修改 TDFC 工作源、正式 SWF、配置或宿主。准确当前 TDFC 是 0.6.4-scene2 / `7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5`，并非 HEAD authority-v1。

## 来源和改动

- `../../../tdfc-threat` 的20个AS来自历史正式线 `fb73655 + scene1 bridge + scene2 threat classification`。`source-pins.json`逐件锁定；`prepare.py`只把历史 `tdfc-threat.py.prepare()` 重放到本目录，验证20份源码逐字一致。此证明是来源/源码重放，不冒充尚未执行的候选编译及字节码审计。
- 历史正式安装依据为 `state/performance-deployment-20261020.json` 的 verified TDFC目标；旧 `source-origin.json` 内0324是构建输入，不是7ACD最终产物。当前安装和历史生成SWF均核对7ACD。
- `original/` 是20份冻结原件；`source/` 只改 `GameBridge.as`，另19份逐字保留。反向删除新增import/替换块可还原原文件全部字节。保留 `candidate.diff` 和 `source-proof.json`。
- 默认开关 `sceneLosEmptyCacheEnabled=false`。候选在现有隔离载体 `ContinuousSceneTdfcThreat.api` 即 GameBridge 上可控；无需改 TdfcRuntime 或另建载体。`sceneLosEmptyCacheCalls/Hits/Lookups/FallbackCalls` 是累计计数，可由探针取差，未加逐格计时。默认不开启，正式版本字符串不改，避免伪装发布。

## 小改动及边界

准确源 `GameBridge.as:40–48` 每9px做 `solid→tile→getAbsTile`，没有LOS缓存。现有缓存只用于弹体威胁分类；掩体候选另有15tick节拍/60tick缓存，均保持。原生Location的 `getAbsTile(int,int)` 先整数截断，再除40取格；Tile.phis是public int，实体边界是public Number，无getter。仅当前调用内、已证实非实体格可复用；不开新全图索引、不存跨帧结果。

资格严格匹配当前域原生Location类及40×40 Tile尺寸；端点必须有限、全在地图内，尺寸在有符号int安全范围。整个采样段在有效区域内。每个采样点仍以原 `x+(tx-x)*i/n`、`y+(ty-y)*i/n` 和原顺序计算；用 `int(px)/int(py)` 判断缓存格，不以浮点直接取格替代。没有改视距、反应、追击、警报、听觉或小队机制。

- **实体/半墙**：phis==1仍用原采样点、原短路顺序检查四个phX/phY边界；不能把整格当墙或空格。边界NaN仍由原num默认值处理。
- **负坐标、越界、NaN/±Infinity、未知类/域、非40px格子**：完整回原clear循环，保留原int转换（含NaN/溢出）和otstoy语义。
- **null格/取格异常**：沿原tile捕获异常并返回null；原solid将null视为阻挡，候选同样返回false。实体字段仍使用原num读取/默认值，不吞新增错误以伪造通路。
- **副作用**：缓存只跳过原生只读取格/phis字段读取。同步clear不让出帧，也无用户回调；这段期间不能有门破坏或动态Tile写者。未知实现不使用缓存。初始化只取得本域Class引用，资格失败不改变原调用结果；原生计算、RNG及视觉树均不写。
- **性能风险**：Class身份与输入检查、整数边界判断及诊断计数都有成本；可能比省下的查询更贵。目前不能报告收益。正向线索只是40px格中9px重复取样，实际命中必须观测。

## 下一步最小验证（尚未执行）

1. 用当前宿主准确类检查参考/候选的clear布尔结果：空地、各类半墙、格界±小数、水平/垂直/斜线、短线/零长度、图边、负数、极值、NaN/Infinity；未知模拟Location必须回参考。缓存阳性须Hits>0，阻挡/错误路径不能只测空地。
2. 门开闭/破坏前后分别调用，证明没有跨调用陈旧缓存；原生Tile/地图内容/角色AI状态保持。检查其它19类原样，候选输出未包含fe.*实现。
3. 同进程短ABBA保持全部仿真、相同真实运动/双方火力，计入首次Class解析和切换成本；保留活动人数、预绘、全部长帧。先排除本日环境/调度放大，再判断整帧是否有稳定收益。计数只证明省下查询，不能替代帧时间。

只源准备命令：`python -B prepare.py prepare`；只读冻结检查：`python -B prepare.py check`。脚本没有编译、启动游戏或部署入口。下一步编译由根统一安排登记，未在本步骤执行。

## 终端组件入口（已准备，未执行）

`SceneTdfcLosChecks.as` + `probe_patch.py` + `run.py` 已准备38组、76次原生方法调用。保留空地阳性、实墙/半墙、分数格界、零/短线、真实地图边缘、负数/NaN/Infinity/int溢出回退、null格和取格异常。门用原生Tile碰撞字段关闭→打开→关闭验证无跨调用缓存；不冒充门动画/交互测试。25个Tile的125项字段、列/格引用、onPause及API开关/计数均在finally恢复并回读；候选private Class缓存仅声明保留，随后退出独立进程。

运行器只接受当前A796宿主/CS7F1F/正式TDFC7ACD作为输入，记录完整实际依赖数，不固定525/528。同一登记内把冻结20份候选源码编译到本目录唯一文件夹，另冻结组件探针；只在私有运行副本覆盖TDFC和探针，宿主仍从实际安装复制。保留编译日志、全部输入散列、载体控制、loader结果、失败原始证据；沿原私有桌面/存储及内存保护。没有性能ABBA或发布入口。

探针来源只允许B7ED收据对应39A产物的85文件历史冻结树，`probe-source-pin.json`锁定收据/产物并逐件验证源树；只改MotionProbe入口并新增本helper。初稿读取当前src不符合隔离要求，已在构建前纠正；初稿从未构建/运行。当前src中的他人WIP与source-only候选不读取、不复制、不接入测试。

根审核后可运行（**本次没有执行**）：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'mods/ContinuousScene/build/generated/scene-compat-20261024/tdfc-los/run.py' --name tdfc-los-20261024-components-r1 --compile-candidate --compile-probe --registry-wait 600
```

`component-source-pins.json`锁helper/patch，`component-static-review.json`记录Python语法、唯一入口锚点和计划数量。静态检查不证明AS3已编译、真实返回值相等或性能改善。
