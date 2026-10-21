被测技能：diagnosing-bugs｜2026-10-08.1｜C:/Users/hello/.agents/skills/diagnosing-bugs/SKILL.md｜SHA-256 755c267af6dcb82d4749429476ed8b56cafc5f2e92d58f168e57b340f18c5a1d；remains-mod-memory
技能归属：用户级（总控维护）及 Remains 工作区级
测试工作区：D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene（本轮仅静态诊断，无测试运行）

# 2026-10-21 天角兽警报与瞬移在大场景中的范围扩大

## 请求、范围与结论

用户报告：大场景中一只天角兽发现玩家后，很多天角兽瞬移过来围攻；明确要求“先不做测试”。本轮只读取源码、已存在的构建审计及发布指纹，未启动游戏、测试、编译或部署，也未修改玩法源码。报告是本次代码调查记录，不是运行验证通过的证明。

代码支持一个与现象高度吻合的兼容缺口：原版依靠 Location（原房间）限制天角兽的群体警报/目标共享；ContinuousScene 将多个房间的单位汇入同一 Location 后，这些无距离限制的操作扩大到整图。已有瞬移能力直接以玩家坐标选点，没有施法者到玩家的距离上限，因此远处已警戒的瞬移型天角兽也可能直接加入战斗。原版地图合并与原生单一大地图都需要考虑这一语义；休眠放大项仅适用于 NativeSceneAdapter 管理的合并地图。

“这次具体有多少只来自远处、多少只新生成、每只触发顺序和时刻”尚未实测，不能把静态分析写成现场复现。

## 直接代码证据

以下原版行号均对应 `game-reference/decompiled/1.02/src102/scripts/`；原版源码为只读参考。

1. **天角兽的警报覆盖整个当前房间，且忽略传入的半径。** `fe/unit/UnitAlicorn.as:386–401` 的 `budilo(param1=500)` 遍历 `loc.units`，只筛选非自身、同阵营、存活、非 unres，然后调用 `alarma(celX,celY)`；没有距离、视线或墙体判断。不能把一般单位 `Unit.as:4271–4295` 的 500 半径/听力规则套给此重写方法。
2. **目标共享也没有距离或接收者视线检查。** `UnitAlicorn.as:403–413` 的 `telepat()` 对同阵营存活、无目标的单位直接调用 `setCel(celUnit)`，并不限于天角兽类型。`control():648–685` 在感知成功且存在目标、`aiTCh % 30 == 1` 时调用它。`Unit.as:4703–4735` 的 `setCel` 检查 `isMeet`，而 `isMeet:4522–4525` 只检查同一 loc 和有效状态，不测距离或视线。接收者不必亲眼看见玩家。
3. **警报本身即可让天角兽进入有战斗计时的状态。** `UnitAlicorn.as:431–450` 的 `alarma` 在空闲/巡逻状态将 `aiState=3`、`aiSpok=maxSpok+10`，并设置 `overLook` 和短暂惊吓。`control():627–638` 在警戒阈值达到时广播 `budilo`；被念力抓住和死亡也有广播入口（517、456）。`control():717–735` 在 `aiSpok>0` 时累加能力准备计时。目标共享与警报不是同一个调用，不能简化成“setCel 立即强制瞬移”。远处单位后续 `findCel` 可能清除目标（`Unit.as:4698`），但警报/坐标和能力计时有独立状态。
4. **具备瞬移能力的是 tr=2 型，原版允许远程警报转成玩家附近落点。** 构造器 `UnitAlicorn.as:157–167` 将 `superSilaTip=2`；准备阈值 `tGotov=90`（37），`superSila():1102–1129` 在 `aiState=2` 调用 `actPort`，或在 `aiState=3 && (rasst2<200² || isrnd())` 时调用。后者的随机分支不限制最远距离，不能将 200 误读为全部瞬移的距离上限。
5. **瞬移选点相对玩家，碰撞只看目的地。** `actPort():1248–1317` 直接取 `World.w.gg`，前四次普通尝试在玩家左右 200–500 像素、接下来五次在左右 200–1000 像素附近找点；后续在整个 `loc.limX/limY` 随机取点。`collisionAll(目标X-X,目标Y-Y)` 检查平移后的身体占用格（`Unit.as:2541–2566`），不检查沿途墙体或距离。成功后移动已有单位（`teleport:2804–2826`），不是复制单位。受击紧急瞬移 `actPort(true)`（422–426）直接走全房随机点分支，合并后其逃离范围也扩大到整图。
6. **大场景确实扩大了上述集合和身份检查。** `src/NativeSceneAdapter.as:15,62–98` 将原房间的 units 等列表合并到 dest；`moveObject:117–124` 把每个单位的 loc 改为 dest。原来隔房不属于同一 `loc.units`、不通过 `isMeet` 的敌人，如今都符合这些检查。当前适配器没有对上述天角兽方法增加本地警报规则。手工单图原本就只有一个 Location，同样没有旧房间提供的天然范围限制。
7. **远处休眠会被共享目标绕过，而且参与状态会保留。** `src/NativeSceneActivity.as:29–45` 发现 `u.celUnit!=null` 就将 `r.engaged=true`，活动判定保留 engaged；这份活动记录没有随后自动清除 engaged 的路径。若共享目标在下一次活动采样时仍存在，远处单位就会醒来并持续运行。该条件受帧内顺序影响，不等于每次共享必然触发；它是放大项，不是警报/瞬移的唯一成因。`NativeSceneAdapter.prepare:27` 排除 `continuous_scene` 手工地图，不能把这一休眠行为泛化到所有大图入口。

## 其他相关机制与归因边界

- **真正的援兵生成另有入口，不能与瞬移混为一谈。** `UnitAlicorn.as:119` 将 `t_alarm` 初始化为约 1500–2100；`579–586` 只在 `aiState==2` 时递减，归零后调用 `loc.enemySpawn(false,false,"alicorn")`。`Location.as:2975–2996` 还要求正的 `kolEnSpawn` 和非空 `enspawn`，并扣一次额度。不是一发现玩家就无限生怪。适配器合并了 enspawn 点、保留 dest 的标量配额，未按原房分别处理这条生成路径；这是后续应一并审查的风险，现无证据证明它造成此次即时围攻。
- **aliAlarm 的跨房持久警戒原本就属于 Land。** 天角兽死亡在 `UnitAlicorn.as:465` 设置 `loc.land.aliAlarm=true`，影响警戒时间与视野。它不应因本次诊断被整体删掉；这是原版全关卡状态，而非合并新创造的全局变量。
- **当前 TDFC 发布线不接管天角兽战术。** 已发布 7ACD 的冻结源 `build/generated/tdfc-threat/EnemyProfile.as:9–15` 只支持 raider/ranger/merc/slaver/zebra/encl；原版 `AllData.as:668–679` 中这些天角兽的 parent 是 alicorn。`TdfcRuntime.as:64,69` 对不支持的兵种跳过感知/动作决策，交还原版。故现有直接证据指向原生天角兽和大图集合语义，不支持把它归因于 TDFC 新增的天角兽瞬移策略；未据此排除全部其他模组的间接影响。

## 安装基线及证据限度

本轮只读核对实际文件 SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| pfe.swf | BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A |
| ContinuousSceneMod.swf | 7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F |
| TDFCMod.swf | 7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5 |

宿主与 `state/performance-deployment-20261020.json`、`build/generated/fog-typed/provenance.json` 匹配；既有 `strict-audit.json` 记录 81C1→BEFC 只改 Location.lighting，其他 4758 个方法不变。`build/objects_native_patch.py` 对 Unit.setCel 的原有改动是检测奖励归属，并未加入远程目标范围过滤。本轮未重新反编译整个正式 SWF，也未运行旧审计脚本；旧审计只是读取的历史证据。

## 建议的修复边界（尚未实施）

保留无缝移动、跨旧房边界追击和天角兽瞬移能力；不要简单恢复旧房间硬边界、禁用全部瞬移、缩小视野或把已真实交战敌人强制休眠。

优先为大场景的 `budilo/telepat` 加入局部传播范围和目标来源记录；接到转述的敌人不能反复把同一警报接力成整图广播。保留原版心灵通信可穿墙的特点，具体范围需按战斗尺度确定。瞬移还需独立约束施法者与目标的有效交战距离，以及全 loc 随机回退/紧急逃离的取点范围。区分亲眼发现、受击/正在追击与仅远程接报，再决定远处单位是否持续活动。这样可覆盖原房合并和手工单图，不依赖编辑器人为切房。

后续验证应区分：附近同伴正常支援、远处未参战天角兽不被全图唤醒、真实跨区追击可继续、普通原版房间行为保留、瞬移并未新增单位、援兵仍遵配额。这里只记录待验边界，本轮不执行。

## 技能实战回流

自然选用 diagnosing-bugs 的范围匹配、分层归因和证据限制：用户禁止测试，静态检查仍获得明确的方法级机制；没有伪造红绿测试或要求用户解除限制。新证据是本任务“明确不做测试”的天角兽范围诊断；全局台账虽有其他只读诊断，未见本问题记录。shared_knowledge 查询返回 partial/无匹配，随后用本区原生 AI 知识与源码核对，未将无命中当成不存在知识。

本次产物为此报告及 MEMORY/journal 接续；[未落盘到公共知识库] 原生天角兽全房广播适用范围留本区静态发现，等待必要的后续证据。没有游戏运行日志，工具读文件与指纹结果留本次对话；无修复效果、性能数字或用户验收反馈。全局台账已去重追加并回读（登记时第 636 行，状态待吸收），交维护侧核对，不更改技能状态。
