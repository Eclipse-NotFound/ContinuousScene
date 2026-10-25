# 活动状态退出修复：候选状态

2026-10-25。只在本目录准备，正式源码及安装未改。性能目标仍是解决镜头移动期间卡顿；本候选只修复已经确认的活动锁存缺口，尚无收益证据，不能替代整个目标。

当前来源：CS7F1F 六类，TDFC7ACD 二十二源；不带入其他任务的 AuthoritySession/B190、天角兽或 SceneRenderChecks 工作。必要跨模组兼容已有用户授权。RConnect 负责人确认 B190 绕过这里的普通 TDFC 循环，本候选不声称覆盖联机权威分支。

当前候选：

- `cs/prepare_cs_v3.py` → `cs/source-v3/`。新增独立有期 lease，旧 wake 保持永久语义。只对严格原生闲置、远处且没有既有保护的准确 Raider/Merc/Slaver 解除旧 engaged。成功解除后每次调度继续复验原生闲置；新 alarma 或未知状态重新保活，覆盖宽限期间和已经休眠后的原生唤醒。每帧最多读取一次闲置判据，保留原宽限。
- `access-v2/` 两个只读 helper、`extern-v2/` 八个外部声明。检查原生内部警戒字段及全部已知 Weapon/WThrow 子对象，保留未完射击/手雷/换弹/回充/后坐；未知状态不解除，另拒绝 rapid<=0。六个宿主 Class 身份已实测相等，30 个真实单位闲置判据为 true；自然退出/再次报警的全生命周期仍未验证。
- `tdfc_transform_v2.py` → `tdfc-candidate-v2/`。保存休眠 brain 的身份、记忆与冷却；报告接收与队形名单仍包含它。任何待投递消息的 source/to 都暂保活，消费与丢弃完全交还原 deliver，避免提前用一新一旧的阵营样本判无效。新版本 CS 缺失时仍走旧 wake。

编译历史：`candidate-builds/ce2578b77528442cbe71edad1adf2ea4/build.json` 已编译 CS 初版 AF646270 和 TDFC v2 A677D3B6；两 helper 的真实原生字段均使用正确 QName，没有把八个原生类打进 SWF。try/catch 包装器的局部 activation 数字槽经完整指令形状核验，不能误称全部字节码没有数字槽。第一轮因审计把局部槽也一律拒绝而失败，保留 `f13a216d.../failure.json`。

**上述已编译 CS 初版已被源码审查发现遗漏再次 alarma 的保护，不得运行或部署。** CS v3 的 Python 时序模型共 29 项通过；它还在判断不能清锁后提前保活，避免对仍参战者多扫弹体。旧目录与产物保留，不改写其结果。

下一验证必须先闭合真实宿主身份、原生搜索结束后暂停与再次 alarma 恢复、Merc 延后手雷、TDFC 到期报告两端与睡眠接收新报告、brain 身份/冷却保持；随后才比较真实战斗与探索路线耗时。不得用清空 AI/目标制造闲置，不根据未知类型扩大暂停范围。


## 最新实测：加载/原生读取有效，尚无释放收益证据

`candidate-builds/76b0b9adac49481b88b9756c27acfd2a/` 为未加观察 API 的 v3 编译候选（CS BA20F42D、TDFC741A2B46）。`0dd3bd018d0c41f89c979a95ff5bbf2a/` 仅额外增加两个 CS 类的只读观察接口，精确逆变换留在回执；实际 CS B0E10AC2、TDFC E8C412C0。SWF 构建本身含时间戳等差异，不靠不同 SWF 哈希推断不同游戏逻辑。两份均无部署资格。

`run_candidate.py` 使用准确 29AF/85 文件，Main 只在最终计时结束后调用新增 `SceneActivityReleaseEnd`，总 86 源。没有改变原生冲刺/射击/击退夹具，也没有复制别的任务的源码。模组是兄弟 ApplicationDomain，观察类通过 CS carrier 取得 helper Class，再和游戏域六个真实 Class 逐个比身份；不假设兄弟域 getDefinitionByName 可见。

实际 `activity-release-native-20261025-r1` 完成 1200 帧、26 项和原生高速/双向真实弹体资格；result SHA256 `670214F806154EF3F560BF15994C5A6963681AA17E2721F2921F5575E338A942`。均52.0567/中50/P95 69/max164ms仅是单轮候选观察，无成对基线，不称优化。玩家400射，敌方819射；各段均52.0767/51.5933/48.76/55.7967ms，活动末值46/38/36/56，负载自然变化。

末态实际159个 record、awake56/asleep104（单位数组还含尚未登记对象，不能把统计直接当AI执行数）。闲置判据30个true、其中5个awake；released=0、releasedSleeping=0，没有engaged且mayRest=true者。12个engaged只有6名近处测试Raider及6个未知家族，不能推断整轮从未释放，也没有本轮释放收益证据。不继续反复同一固定战斗来挑好结果。

原526安装、隔离候选输入及13运行库前后核对保持，AIR31196已退出并释放登记；最低可提交内存约28.9GB。只读观察发生在最后计时之后；它不是报警/报告/手雷/醒来视野生命周期测试，明确 lifecycleVerified=false、performanceAcceptance=false。镜头主成本转回原生执行位置归因；本候选留待有真实退出路径的功能验证，不部署。
