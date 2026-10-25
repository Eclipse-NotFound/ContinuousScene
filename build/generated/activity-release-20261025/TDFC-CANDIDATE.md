# TDFC 有期活动续保：隔离源码初稿

此文件描述历史 v1，当前 v2 及实测边界见 [STATUS.md](STATUS.md)。旧按样本提前判断 pending 的逻辑已撤回，原候选保留。

2026-10-25。仅源码准备，未编译、未加载游戏、未部署，也没有性能收益资格。只面向正式 7ACD 的普通单人循环；不读取或合并 RConnect authority/B190/live 分支。

## 来源与生成

`tdfc_transform.py --prepare` 读取 `scene-compat-20261024/tdfc-los/original`，先验证其 source-pins/source-proof 的固定 SHA，再递归核完整 22 个 AS 文件。输出 `tdfc-candidate/`；只修改 TdfcRuntime.as、PerceptionModel.as，另外 20 个保持原字节（包含两份 locale 依赖）。每处替换锚点唯一、两文件反向转换恢复原字节、11 个缺锚点负例拒绝，证据 `tdfc-source-proof.json` 与 `tdfc-candidate.patch`。

本工具只读原源、写本目录源码/JSON/diff，不调用编译器、Java、AIR 或正式部署入口。未改 BrainState/ActionExecutor/SquadMind/Config，也未新增行为计数器。

## 已同意的 CS 接口（这里没有实现）

- `sceneNativeCall("activityLeaseVersion",[])` 严格返回 `"activity-lease-1"`。
- `sceneNativeCall("activityLease",[unit,45])` 严格 true 表示已在对应 Location 中，对**已有** activity record 延长独立 `leaseUntil`，恢复原动画并从 sleeping 移除。不得置永久 engaged，不得只续普通 until；未知房间/记录返回 false。
- 旧 `wake` 保持原语义。版本缺失/异常时继续原 7ACD sleeping 分支；续保调用 false/异常则尝试旧 wake。此处不会虚构 HP 或创建 native record。

时间都是原有 CS/TDFC 逻辑 tick，不换算毫秒，不对暂停时间减法、不重置冷却。独立 leaseUntil 的实现和原生退战 getter 属另一个 CS/宿主候选，本目录不能单独发布。

## 三个名单

1. `all`：这帧正常更新的 brains，继续原有 sense/assess/decide/apply、观察输出及新报告发送。
2. `pausedBrains` / `pausedUnits`：CS 已暂停、明确 exact Raider/Merc/Slaver、无有效记忆/未完动作/待送消息的既有 brains。首次转入调用原 ActionExecutor.restore，保留 states 中同一对象、key、记忆、冷却与队列引用。后续只按原 hostile 规则确认仍在本房，并更新物理 snapshot；不重算感知或战术。
3. `retainedBrains`：active + paused，顺序仍来自本帧原 loc.units。用于报告接收资格及 squads 的实际队伍人数/最近距离。真正消失或不再 hostile 时才 restore/delete；换图 reset 同时归还两组。

字段 `present` 仍仅标 active；独立 retained 标记用于清除真正离场者，不能拿“本帧没运行”删除睡眠 brain。睡眠者的统计不冒称 active AI。

## 续保及消息时序

记忆按原 `tick-lastSeen<profile.memory`。有效 dodge until、任意尚未由原 decide/apply 收束到 idle 的动作/order/ground/cover、仍观察/听见、未知状态都继续活动。不会由调度器取消它们。每帧正常 apply 后再次查询并续 45 tick，减少 native 先运行造成的空档；实际回调次序仍待游戏验证。

`PerceptionModel.needsActivity` 只读 pending：任何仍符合原 deliver 阵营、seen 年龄、较新信息条件的报告，都保护 source 与 recipient。包含 `at<=tick`、但原 deliver 还没执行的条目。它不提前投递、删除或排序消息。坏字段或异常保守保持活动。对象已经离场的报告可能额外持有到原 due 时被原 deliver 丢弃，这是有限的保守等待。

`schedule` 仅增加可选 recipients 参数，null 时与原逻辑完全相同。发送者仍 active；接收者用 retained，因此已暂停的 idle 同伴仍可收到原规则的新报告，下一 tick 看见 pending 后续保、在原 due 时正常接收。原 REPORT_COOLDOWN、范围、at 计算和 deliver 删除逻辑保持。没有新来源、重复循环或提前排期；停止发送时旧 pending 仍由原 due 清理。是否与真实消息时序一致尚未实测。

## 静态边界与下一验证

- 当前源码没有实施 CS 清 engaged，也没有宿主原生 idle getter。仅搭正式 7F1F 时走旧 wake，不会自动产生退出收益。
- exact 类列表不盲含 Zebra/其他派生。原生 t_chCel/priorUnit、HP/效果/距离/弹体、currentWeapon 与 Merc childObjs 手雷余弹保护仍需由 CS/宿主方案实现，不能用本 TDFC 条件替代。
- 原 restore 的既有错误处理和属性归还保持原样；首次重新活动会用保存的 BrainState 继续原流程。需实测 wake 首帧感知/技能归还、冷却连续、pending source/to due、睡眠中排新消息、阵营变化/离场/reset。当前只有静态字节来源/变换核对，不是行为等价或构建成功。
- 必须先出现真实“搜寻结束→安全暂停→重新唤醒”的阳性，再测同负载收益。不得用 setNull/强清目标制造 idle，不改追击距离或删除敌人。
