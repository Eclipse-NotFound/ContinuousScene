# 原生已退战单位恢复休眠资格：只读审查

日期：2026-10-25。状态：仅源码审查及已有样本核对；未实现、未构建、未运行、未部署。当前正式宿主 A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7，CS 7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F。

## 已确认

准确 CS 0.9.0 来源为 `build/generated/activity-telemetry-20261022/original-source/`；其六生产类与 `build/large-map/source-manifest.json` 一致，`state/deployment-v090.json` 为 verified。`NativeSceneActivity.as` SHA256 为 `01182FACDFB7AFBA7A03CCFF1C3C28E14219E8FE654118149C50FCF7261AC0F7`。

`NativeSceneActivity.update` 第 32–44 行只有两种永久参战标记写入来源：

1. 新记录初始化 `engaged:false`；随后 HP 下降、有 `celUnit`、流血 `cut>0` 或中毒 `poison>0` 时置 true。
2. `wake(u)` 第 60–64 行对已有记录置 `engaged=true`。

之后没有置 false、到期或原生 idle 检查。`rooms` 按 Location 弱引用保存；同一 Location 再进入不等于新记录。真正新 Location 才有新记录；这不能单凭源码称作 GC 泄漏。

距离/相机范围、弹体威胁本身只保持活动及 `until=tick+45`，不会设置 engaged。但 engaged 为 true 会每帧再次续这个 45 帧宽限。清除标记后必须保留已有 until，不能立刻无条件暂停。

其余正式保护保持原样：玩家、宠物/友方/NPC/boss、非正常 sost、非满血、stun、bind、levit、t_emerg、effects、交互移动、玩家 1900×1300 范围、视口外扩 600px、弹体威胁及宽限。尸体/已删除单位仍可能残留在 loc.units、因此被 awake 统计；Location.remObj 只移链及移除视觉，不能把 awake 数直接当每帧运行的 AI 数。

Location.step 仍遍历整条 firstObj，并在 sleeping 判断前处理 sceneNativeEnvironment；休眠只跳过 obj.step。休眠停止 u.vis 下正在播放的 MovieClip，但没有隐藏/摘树，独立武器根不在这次递归中。本方案不改这些规则。

## 原生退战判据及范围

公共 1.02 `game-reference/decompiled/1.02/src102/scripts/fe/unit/UnitRaider.as`：第 723–741 行 aiSpok==0 才回状态 0/1；aiSpok>0 是警戒/搜索。第 794–861 行保留看到/听到/丢失目标后的搜索。状态 5 是反应等待，6/7/8 是逃离或突进，不能按无目标冻结。`Unit` 的 aiState/aiSpok 是 PackageInternalNs `fe.unit`，不能从普通动态 public QName 猜读。

最初可只做 exact Raider；补读两个完整参考类后，允许把 **exact `fe.unit::UnitRaider` / `fe.unit::UnitMerc` / `fe.unit::UnitSlaver`** 列为明确资格列表，前提是准确 A796 核验及下列武器保护通过。**不得**用 `u is UnitRaider` 自动纳入所有派生。Slaver 全类只有构造器；Merc 没有 control/actions override，继承同一警戒控制，但改 attack 并有额外投掷武器；Zebra 确有 control override，先排除。Vortex/Mine/Turret/molerat 等不因这份审查取得资格。

核心只读证明是 `aiSpok==0 && 0<=aiState && aiState<=1 && celUnit==null`。但不能把这三个字段直接称为完整“所有延后行为已结束”的证明：

- `priorUnit` 可保留受击目标，必须为 null 才退场。
- Raider 的 `t_chCel>0` 会在下一次感知失败时对 `celUnit2` 再调用 setCel（第 840–843 行）。建议 getter 同时拒绝 t_chCel>0；celUnit2 旧引用本身可长期不清，不能单独要求引用为空。
- `aiAttack` 在 control 末尾由状态更新；建议为 0。`aiAttackT` 只在 attack 中递减，可以留下非活动残值；`aiAttackOch` 是配置的连发长度，`aiVKurse` 是历史认知，不能要求这三者全部清零。
- 武器 `t_attack>0` 仍可能由 Weapon.actions 发出已排队的连发（原生 Weapon.as 第 1178–1195 行）。首版应保守等当前武器的攻击/蓄力及换弹结束，或实际证明原 45 帧宽限覆盖该武器；不能统一假设所有武器 45 帧内结束。未核武器字段/类型返回未知则不退场。
- Merc 特有遗漏风险：构造器第 30–34 行把 `thWeapon=Weapon.create(this,"mercgr")` 加入 childObjs；attack 第 144–154 行按 t_gren 排队它的 attack。WThrow.attack 第 107–111 行设置 t_attack=rapid，之后由继承的 Weapon.actions 真正投出弹体；Unit.step 第 1852 行才跑 childObjs。因此保护必须覆盖所有已核 Weapon 子对象，不能只看 currentWeapon。t_gren 仅在 attack 中减，是下一次投掷的冷却/间隔，不必归零；aiAttackT 同样不当作独立后台发射。未知 childObjs 类型或读取失败保守不释放。Merc 独立 arm 显示根是既有视觉边界，本方案不改它或现有 freeze 递归。
- 不调用 setNull、findCel、look、alarma 来“判断”状态，它们会改变原生记忆、位置、观测或随机数。不得用 dx==0、站立若干帧替代原生警戒字段。

以上 Raider 控制语义来自 1.02 参考，Unit 内部槽命名已在准确 BEFC 中核对且旧 getter 有实测。A796 后续严格补丁未以 Raider 为目标，但**本轮未重新逐指令核对 A796 Raider.control**；实施前须对当前准确 ABC 做针对性核验，不整包重编参考源。

## TDFC 的第二个永久锁与报告时序

准确正式 7ACD 冻结源在 `build/generated/scene-compat-20261024/tdfc-los/original/`，22 文件来源见同目录上层 source-proof.json；本次重算以下 hash 与 proof 一致：

- TdfcRuntime.as `BA051B0061EEA30E7AE1CA82A040A7B0397A04C2000759B98481C0AEC693EF03`
- BrainState.as `D6005B01DF4CB1135975816A8589599CC189C121D942EA0794D612D86A189EDA`
- PerceptionModel.as `43702BD70B6E2F7B89E94E63D32F00AD74DDF3D2B026031A1C0D4F73870963E2`
- TacticalMind.as `61DACDA42C2F38393968C410DA8C4C640BC150CF16F8DC760BBFD843260A03B9`
- ActionExecutor.as `64223CC2E517E3ACE826C100662446A3A55AAE801DBFF25BC223BCD2FCC910A8`

TdfcRuntime 第 54–59 行：只要 sleeping 单位曾有 `remembered.lastSeen>=0` 就调用永久 wake；并不检查记忆年龄。TacticalMind.decide 第 10 行真正“已知目标”是 `tick-lastSeen<profile.memory`；EnemyProfile 的 memory 为 `90+tier*45` 个战术 tick。因此仅在 CS 清 engaged 会被历史目击重新锁住。

最窄修正需双方协作：原生确已退战才清 CS 旧锁；TDFC 用**有期限的活动续保**表达尚在工作的记忆/动作/消息，而不是“曾经见过就永久参战”。其他类型及外部旧 wake 不应在未核调用者时被统一改语义。

续保至少包含：

1. 当前 `tick-lastSeen<profile.memory`，含听觉区域与同伴报告，绝不只看 celUnit。
2. `action.kind=="dodge" && tick<until`；该承诺在 decide 中先于 !known 的 idle 分支返回。其他未完成动作先允许正常 decide/apply 把它收束到 idle，再放开，不在调度器中强行取消。
3. 任何仍可能有效的待送报告，单位是 recipient **或 source** 均须保留。PerceptionModel.deliver 要求两 BrainState 都仍在 all，且相同阵营/有效记忆。不能只判 `p.at>tick`：本帧已到期但尚未 deliver 的条目同样要续保，因为 runtime 先 prune 不 present 的 BrainState，再 deliver。
4. 正在受伤/效果/弹体威胁沿 CS 现有保护继续处理，不靠 TDFC 记忆期限代替。

尚未消化的报告不需要永远保留：可在 PerceptionModel 自己的 pending 队列中按既有 deliver 有效性给出纯查询；不扫描猜外部对象，不提前删除/提前投递报告。当前 REPORT_RANGE=500、REPORT_SPEED=20，排期有限；不要把估算的 61 帧当通用超时，实际以队列 at/seen/接收者 memory 与同帧顺序为准。

还有生命周期陷阱：runtime 对不 present 的 BrainState 会 restore 然后 delete states[u]。直接让睡眠分支 continue 会丢失冷却、知识、报告引用身份，醒来变成新 brain。若要保持行为，应保留休眠 brain 的 identity 和记忆/冷却，仅暂停计算；明确把“本帧没有运行”和“单位真的已离场”分开。若不处理这一点，则放弃既有记忆/冷却属于新的玩法取舍，不能默默当性能优化。ActionExecutor 写过的视角/武器技能/地面承诺须按原 restore 规则归还；不得删除仍被有效 pending 引用的 brain。

## 最小接入建议（未实现）

1. CS 只有上述明确 exact 类列表、原生 getter 严格 true、无当前公共保护/威胁/续保、所有已核武器子对象没有未完排队行为时允许清 engaged；同一帧新受伤/流血/中毒/目标不得被后续清理覆盖。未知 getter/孩子或异常一律不清。保留原 until，不提前删 sleeping/records、不改实体位置/生命/碰撞/目标。
2. 用有期 lease 保留 TDFC 工作中的单位；即使本帧原生 idle 也不得丢掉尚未到达的续保。现有 activity 在 native Location.step、TDFC 在 ENTER_FRAME 回调，须实测两者实际顺序；已有 45 帧 grace 是缓冲，不是未知回调顺序/队列正确性的证明。
3. 若需要宿主公开 getter，最窄为 UnitRaider 增加一个无写入、无随机数、无游戏调用的 Boolean 读方法；只读其真实 internal 槽并可增加上述延后目标保护。新增方法/trait 是显式布局变化，不能声称全类布局逐字未变；审计应只允许这一个新增入口，其余旧方法/初始化器/字段/素材/常量池前缀保持。方法位置与 namespace 要绑定 A796 实际导出。
4. 另一已有验证路径是同包 `fe.unit.ActivityInternalAccess` + external-only Unit 声明，旧 activity-internal 已证明能够读取四字段、不嵌入替代 Unit/Obj/Pt；本轮可先用于观测，不必为观测修改宿主。它尚未覆盖 Raider t_chCel 等，不可直接冒称完整 getter。生产采用哪条方式由主任务定，本文未构建任何一种。

## 观察到的上界，不是收益

`knowledge/experiments/evidence/window-visibility-native-20261025-r1/storage/result.json`：四段活动均值 37.3/38.8/40.1/40.0，期末 45；resident 103→115，单位数组 162→164。末态原因分组 visible-or-near 34、sticky-or-grace-or-projectile 9、interaction 1、nonhostile 1。九个远处未细分单位是 Merc×4、Vortex×3、molerat、Slaver；**没有 exact Raider**，六 Raider 均为附近测试射手。若仅 exact Raider，样本无可释放证据；补充明确 Merc/Slaver 白名单后只得到 5 个“类型匹配”的数量上界，尚未证明它们原生已退战、武器已完或无 TDFC 续保。

末态 census 不读取 private engaged/until、实际弹体匹配，因此不能把九个 unresolved 全称为永久锁。旧 `activity-internal/raw-review.md` 的真实四字段观测只得到 Raider 家族范围远处候选均 4.41 的上界，也未区分 private latch/宽限/弹体；满血无目标的 Merc 确实可仍有 aiSpok 搜索记忆。

terrain resident 随探索增长是正式缓存策略：sceneEnsureUpcoming/sceneRender 不逐出离开视口的已绘块，sceneCullSurfaces 只隐藏，sceneClear 才移除和释放；它按地图格数有界。NativeSceneAdapter 预先合并并复用单位，预绘不重复生成敌人。单个末态显示树 3685 个容器、3594 个 MovieClip、24 个 playing 不能证明探索导致实体显示树无限增长。本文不复活已经失败的 sleeping-root/culling/detach/cache/atlas 路线。

## 尚未验证与最小验证思路

- 先只读记录 exact Raider/Merc/Slaver 逐帧原生 aiState/aiSpok/celUnit/priorUnit/t_chCel/全部已核武器子对象排队状态，CS engaged/until/保护原因和 TDFC memory/动作/待报告引用。必须得到“真参与战斗→失去目标仍搜索→原生回 idle→安全远离→宽限结束”的阳性，不强行 setNull 或清目标制造。Merc 必须有已排队手雷仍正常投出/随后可退场的负例转阳性。
- 负例：追击/仅听见/最后位置搜索、dodge 未完、已到期未投递报告（含 source）、流血中毒/HP 下降、飞行弹体接近、旧 grace、未知类型/派生/读取失败。全部仍运行；原生冷却/消息结果与基线一致。
- 真正睡眠后重新接近、重新受击及跨房追击应自然唤醒，已有子弹继续运行；对动作、碰撞、消息及武器余弹逐项核对。睡眠 brain 的身份/冷却/归还属性要有明确断言。
- 只有功能证明后才做同负载性能对照；当前不知道明确类列表在真实探索中已退战的数量，更没有“明显下降”的证据。若实际可释放数太少就停止，不为凑收益扩大未知类规则。

推测：永久 engaged 是跨房追击保护的保守实现，缺少退出阶段；TDFC 曾见即 wake 放大了这一锁。代码能证明永久性，不能单凭它推断原作者意图或本次卡顿主因。保留真正追击到原生完成搜索、之后暂停远处巡逻，与用户已接受的远处未参战暂缓方向一致；提前缩短搜索/忽略报告/重置冷却则不是本次保守修复范围。
