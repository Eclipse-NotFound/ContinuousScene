# 镜头预唤醒范围：独立源候选

本轮只准备源码；按用户选择保留正式游戏，不启动 AIR 或进行游戏测试，不部署；本轮也未编译。本目录不改生产 src/release，不读写 SWF，不叠加 activity-release。

来源是正式 CS 7F1F 的六个准确原类，取自 `activity-telemetry-20261022/original-source`，以 `large-map/source-manifest.json` 的 832319A1… 指纹与每文件完整 SHA 双重核对。新增 `SceneActivityCameraRange.as`，6→7；仅改 `NativeSceneActivity.as` 和 `ContinuousSceneMod.as`。`prepare_source.py --prepare` 只补齐本目录尚不存在的六源；不带参数只校验。输出 JSON 包括所有源指纹、差异集合、逐字保护段与精确反转结果，不覆盖现有文件。

## 接入与算法

默认未配置、mode=false。只有独立 motion AIR id 能调用开关，不提供真实用户设置。Carrier 的 nativeAPI 追加四项：`activityCameraRangeVersion():String`、`activityCameraRangeSet(enabled:Boolean):Object`、`activityCameraRangeVerify():Object`、`activityCameraRangeSnapshot():Object`，版本固定 `activity-camera-range-1`。Set 只改变本 helper 的诊断状态，不调用 activity/wake、不写玩家或镜头。

原调度先计算旧视口外扩 600，再为本次调度计算一次新计划；新计划有效时将候选范围代入原 AABB 相交分支，关闭单独的玩家 ±1900/±1300 近区条件。敌友保护、警戒锁、掉血、状态异常、弹体威胁、45 tick 缓冲、wake、freeze/resume 全部逐字保留，仍在同一原循环 resume/delete sleeping。回退时直接使用原两个近区条件，不 return null、不全图唤醒、不取消战斗保活。

普通跟随使用当前真实 visual.concatenatedMatrix 对应视口，另计算下一次 Camera 的包围：X 为 int(gg.X×scale)，Y 位于 int(min(ovy,gg.Y×scale)) 至 int(max(...))；每个端点按 Camera 的 int 赋值再 clamp、含负 max 的居中分支。震动包围取当前 abs(quake) 各方向加 2 Stage 像素，再除 scale；与当前实际视口并集后外扩 320 世界像素。不会调用 Camera.calc、不会读取随机数或消费 RNG，也不会因非零震动直接全图 active。

初帧、换图/镜头/尺寸/scale 变化、zoom 输入、look/show/otryv/camRun、SATS、未知矩阵或非有限/int 溢出均回旧 near，并记录理由。真实 visual 的父变换必须为单位矩阵，实际 scale 与 Camera 一致且无旋转/倾斜；无法证明的变换不走新范围。稳定缩放仍须全部守卫通过。计划计算不扫描地图；后验为诊断会读取现有 loc.units 检查可见休眠者，其完整开销必须计入对照。

## 后验与局限

Location 的先后顺序为 gg.step、activity、其他对象 step，World 随后调用 cam.calc。activity 之后对象仍可能写玩家位置或新增 quake；包围数学并不能保证这些晚到写入。因此根探针必须在原 cam.calc 之后、计时采样之前每帧 Verify。Verify 只读实际视口和 sleeping 集，任何已应用计划漏包实际视口、可见实体仍休眠或该计划没有后验即进入下一调度，都会锁定 failed 并禁用后继 narrow；下一原调度恢复旧 near。后验不会补走本帧被跳过的 AI，根必须保留失败证据并停止该轮，不得说已补救或已保证兼容。

Snapshot 含 enabled/requestedEnabled/failed/configurationEpoch、计划/应用/回退/核验计数、firstFailure 和 lastPlan/lastVerification。Verify 含 ok/failed/enabled/applied/pending/tick/epoch/reason、planned/actual、viewportContained、visibleSleeping/样例、unitsExamined、errors/checkComplete。B 已应用时仅在原有 sleeping 扫描分支补 `oldNearOnlySleeping` 和至多 8 个数值例：当前对象按计划时旧矩形或玩家 ±1900/±1300 会在 near，但不在新计划中、现为休眠。玩家计划坐标取保存的 scaled/scale，不新增游戏读写。这是候选实际收窄的阳性证据，尚不等于帧率收益。范围结构为 `{left,top,right,bottom}`。开关改变后尚未经过下一 activity 时 pending=true、tick=null，绝不把旧模式计划归入新模式；true→true 不重置 B/B。重复 Verify 返回该计划已有后验，不重复扫描。

ok 表示未发现锁定失败，不等于该帧使用了新算法；applied=false 的回退、checkComplete=false 的未知状态均不能充作新范围验证阳性。所有 B 都只回旧 near 的一轮不能声称覆盖候选或获得收益。资格至少需要真实 applied 与 oldNearOnlySleeping 阳性、逐帧计划/实际包围与 visibleSleeping=0，并核对原生战斗负载、连续帧和恢复。当前无实测、无兼容或提速结论。
