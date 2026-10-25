# 原生闲置字段访问方案

2026-10-25。状态：只读核查与隔离源码草案；未编译、未运行、未部署。本文不把“字段可读”视为调度或收益已通过。

## 结论与已有证据

可以沿旧 `activity-internal` 的同包 helper + external-only 存根路线访问，不必给宿主增加 getter。`fe.unit.NativeSceneIdleAccess` 读取 Unit / UnitRaider 的同包 internal 槽；武器的 internal 槽属于另一个包，须由很小的 `fe.weapon.NativeSceneWeaponIdleAccess` 读取，不能用 `new Namespace("fe.weapon")` 或动态 public 属性猜读。

旧目录 `build/generated/combat-near-native-20261023/logic-profile-audit/activity-internal` 的 `compiled-review.md`、`prepared/c0a79ab5b3cf4e298145339ca6f9d09b/bytecode-audit.json` 已核真实指令：四个 Unit 读取是 QName、PackageInternalNs `0x17 / fe.unit` 的 `getproperty`，无数字槽访问、无宿主写入；最终探针未包含 Unit/Obj/Pt 定义。旧 `SceneActivityInternalProbe.bind` 还比较 helper 的 Unit Class 与宿主 applicationDomain 的 Class 身份。`raw-review.md` 对应真实 1200 帧、44 次采样，证明该四字段路径确实运行；这是 BEFC 当时的证据，不冒充本次新增 Raider/Weapon 字段已实测。

当前 A796 已有准确导出：`build/generated/scene-compat-20261024/tint/product/pfe.xml`，回执给出 SHA256 `1D2642C7D55D1F97121738E6AE84996A140EBFEFF686E6706C88CEF82A7338DA`。本轮没有重读/重导出大型 XML 或游戏 SWF。可复用的小审计链为：

| 输入→输出 | 已审唯一变化 | 小回执位置 |
|---|---|---|
| BEFC→80CF | Location.lighting | `combat-near-native-20261023/logic-profile-audit/fog-last-blocker-production-minimal/{build,semantic-audit}.json` |
| 80CF→ABE2 | Camera.calc | `vertical-camera-band-20261023/{build,semantic-audit}.json` |
| ABE2→A796 | Grafon 两个实体颜色方法 | `scene-compat-20261024/tint/product/{build,semantic-audit}.json` |

三步均保留 1016 个类布局、无新增字段/方法；没有 Unit、Raider 或 Weapon 变化。因此旧 BEFC 布局证据仍有来源链。**本次未针对 A796 重新解码 Raider/Weapon 字段与方法；后续编译审计必须针对上述现成导出核这些 QName/类型，不凭存根布局放行。**

## 最小草案与接入契约

`access/` 只含两个新 helper；`extern/` 含最小声明，不含实现。沿旧构建方案单独编译 extern SWC，并仅列入 probe/CS 的 `external-library-path`；绝不把 extern 目录放入目标 source-path、`include-sources` 或静态链接包。需要的外部类为 Pt、Obj、Unit、UnitRaider、UnitMerc、UnitSlaver、Weapon、WThrow。

- 主入口 `fe.unit.NativeSceneIdleAccess.mayRest(value:*):Boolean`：仅 exact UnitRaider / UnitMerc / UnitSlaver；未知类、未知孩子、读取失败返回 false。它不改任何原生字段、不调用 AI、物理、攻击或重置方法。
- `nativeClasses():Array` 顺序固定为 Unit、UnitRaider、UnitMerc、UnitSlaver、Weapon、WThrow。接入前应逐项与真实宿主 applicationDomain 的六个 Class 严格相等；不接受只匹配类名。
- `fe.weapon.NativeSceneWeaponIdleAccess.mayRest(value:*, owner:Unit):Boolean` 只接受 exact Weapon / WThrow，且 owner 必须是当前单位。主 helper 同时检查 currentWeapon 和全部非空 childObjs；重复对象最多读两次，不复制数组、不修改枚举顺序。null child 与原生 Unit.step 一样忽略；非 Weapon 孩子保守拒绝。
- 这些只是解除旧 engaged 锁的必要条件。CS 仍须独立保留本帧伤害/目标、公共保护、距离/视口、弹体、externalWake、有效 lease 和原 until 宽限；不以 helper 替代任何一项，也不在 helper 清目标或结束 TDFC 行为。

## 原生判据与不能误用的字段

以下行号均为 `game-reference/decompiled/1.02/src102/scripts/`，结合上述保留链使用。

| 条件 | 依据与边界 |
|---|---|
| aiState 恰为 0/1，aiSpok==0 | UnitRaider 723–743：无警戒才回闲置/巡逻；794–861 保留感知与搜索。其他家族枚举不同，不纳入。 |
| celUnit/priorUnit 为空，aiAttack==0，t_chCel==0 | UnitRaider 840–843 可用 celUnit2 恢复目标；1441–1452 按状态开始 attack。celUnit2 旧引用不必为空，不能据其残留永久阻止。 |
| 六个公开活动计时为零 | Weapon 50–62、1178–1276：t_attack 可在 actions 排队真实 shoot，t_prep/t_reload/t_rel/t_shoot/t_auto 仍有未完工作。草案对负计时也保守拒绝。 |
| 非回充中 | Weapon 1254–1263 的实际条件是 recharg!=0 且 hold<holder；t_rech 在构造与每次回充后被设为 recharg，满弹时也可能大于零，不能单用 t_rech>0。 |
| is_attack/is_pattack 均 false，t_ret==0，rotUp 有限且为零 | Weapon 1201–1215、1239–1251、1275–1276。回弹 t_ret 与 rotUp 不由公开攻击计时完整涵盖；rotUp 还参与 1495 的弹道角，不能把它只称为画面状态。45 tick 不是任意回弹/堆叠后座的普遍上界。 |
| reloadMult 有限且舍入后的 reload 检查阈值为正 | Weapon 1271：阈值若为零，公开 t_reload==0 仍命中 reloadWeapon 调用。草案拒绝这一非通常配置，不猜测其无效。 |

`aiAttackT` 只在 attack 中递减，可留下无后台调用的残值；`aiAttackOch` 是配置；`aiVKurse` 是历史认知，不能要求全部清零。`is_shoot` 在 Weapon 中只见置 true，不能作为持续忙碌标志。`ready` 是使用资格，不是排队行为。

Merc 构造 30–34 把额外 `mercgr` 投掷器加入 childObjs，attack 144–154 才按 t_gren 调它的 attack。WThrow.attack 107–111 设置 t_attack，实际发射仍经 Weapon.actions；Unit.step 1846–1856 最后逐个跑 childObjs。只看 currentWeapon 会漏手雷。t_gren 只在 attack 中递减，不是独立后台发射倒计时。

Slaver 全类只有构造器；Merc 不覆盖 control/actions，但改 attack。Zebra 另有 control 与消隐计时（UnitZebra 36–113），本次排除；不扩到炮塔、地雷、怪物或其他武器派生类。此前被护栏拒绝的 Monstrik 读取本轮未重试。

## 后续必须验证的最小范围

1. **实际字节码和身份**：两个 helper 的 internal 读取分别绑定 PackageInternalNs `fe.unit` / `fe.weapon`；public 槽绑定 public；禁止 getslot/setslot 数字槽、原生字段写入、随机数和游戏方法调用。确认八个外部原生类定义均未打入产物；六 Class 宿主身份实际相等。旧外部存根成功不自动证明新增成员成功。
2. **功能反例到阳性**：正在追击、仅听声/丢目标搜索、t_chCel 延后恢复、已排队手雷/连发、换弹/回充、后坐尚未归零都 false；同一真实个体自然完成这些状态再转 true。不要 setNull/清 AI 造阳性。未知子类、未知 child、owner 不符、缺字段与异常应 false。
3. **调度相位**：update 在原生控制前读的是上次完成状态；TDFC 后续动作/待报告须由 lease 保留，旧 external wake 仍永久保护。clear engaged 后也保留原 until，不把 helper true 解释为立刻冻结。
4. **重新进入与收益**：保留真实搜索完成、跨区追击、子弹和 TDFC brain/消息；自然重接近/受击可醒。先测实际可释放数量，再测同负载收益。本草案没有证明性能改善，也没有证明所有原生音效/动画队列均已清空。
