# ContinuousScene — 当前快照

更新：2026-10-23，战斗优化已部署并复验。此文件是入口；详细历程见 journal.md，先前长快照完整保留于 MEMORY-history-20261023-0818.md。

## 1. 模组与体验

连续大场景把多个原版房间合成一个 Location；全图碰撞、敌人、物品预先生成，镜头与弹体可连续跨房。画面按视野提前分批绘制，远处未参战敌人暂缓行动，追击者和飞行弹体保持运行。CS0.9.0另支持可编辑的单一大地图，原版房间仅作样例素材。入口类 ContinuousSceneMod；正式文件 release/ContinuousSceneMod.swf。

原版任务由设置“以连续大场景载入原版地图”控制，下一次生成/读档生效；基地、后室和挑战保留原入口。普通返回/重新出发/随机图读档分别遵循原版保留、重置和回基地规则。内部相邻房间三角标记已移除，保留地图外沿和真正出口。

## 2. 用户约定与职责边界

- 当前性能任务用户要求持续修复至战斗卡顿明显下降，并测试、部署。2026-10-23最新答复：已退出应用，优先保证任务进行。不要重复问已授权事项。
- 保持原画面、战斗机制及跨房连续性。已允许视野预绘与远处未参战敌人暂缓行动。
- 必要兼容授权包括 RV、WallBlend、LAD、TDFC、RConnect；RC协调已明确授权。RC负责人会话01a086bb-378c-7f60-b8e1-50d90ffa0996集中维护、构建和部署RC，本侧不并行覆盖它。
- 性能根会话01a13816-367b-7261-8e11-ca9152565dd9。所有游戏测试登记、唯一AIR ID、私有桌面、独立存储；不写真实APPDATA/pfe，不关闭用户或其他任务的进程，不用Ghost。
- 用户已要求撤回10月21日下午配方：绝不重新安装7D42/5432宿主或旧整包配方。
- 另一会话天角兽候选仅源码：1bf0e7b、src/patches/SceneAlicornAlerts.as.inc，不构建、测试、接入或部署。候选仅发送者X±960/Y±500（含边界），穿墙/跨旧房可通知；不擅改瞬移/支援人数/记忆。
- src/tests/SceneRenderChecks.as 是其他会话WIP，不恢复、不提交。无AGENT_SCOPE.md文件，未自行创建受保护薄壳。

## 3. 当前安装与候选

本轮仅更新RC离线采集开销，其余保持用户要求回退后的组合：

- root pfe.swf：BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A。
- CS0.9.0：7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F。
- RC0.2.24-offline1：EB3653533CFB305BCCA0B0CFE5E81BC306EA28FA400AAE751AB7B5AE1CFA5FEE。
- TDFC7ACD、LAD8ADB、WB1411；RV由其负责人独立更新，最新已核83D8。每轮须冻结实际依赖，不把其他任务更新归本任务。
- 已测准确生产输入：../RConnect/build/m52/recovery-offline-production-01。部署回执../RConnect/build/m52/recovery-offline-deploy-01/deployment.json，状态deployed-smoke-passed，SHA256 7DB4BDC4F9BF9317A96EC51DB3076A5B8F0D49BBC9254692142BE92F7065EE86。

EB365基于准确574D冻结源，仅三类和版本变化；未联网时跳过两组弹道/身体效果历史采集。首次host/join尝试即永久恢复采集（直到进程重启）；null、异常、非严格true均保守回退。保持墙面、感知、实际呈现、失效刷新和联网路径；生产包无诊断开关。诊断88CC不得部署。

CS编辑器0.9.0已于10月20日安装并复验25+22项：Editor7344、EditorTools02F5、CS7F1F，168固定箱体逐件对应。192×50研发部样例，地图编辑器.vbs→大地图，应用maps/active.xml后重新进入读取；nativeEnabled独立。当前性能任务不重建编辑器。

## 4. 当前任务进展与停点

真实战斗已获得可重复约15%改善，联网门禁、精确部署和安装冒烟全部完成。原574D与EB365各1200帧、90项PASS，原生按键/物理/真实双方开火、同地形及路线：平均69.615→58.866ms，中位64→54，P95 96→80，>100ms帧51→32；五块均值/中位都改善。两轮诊断ABBA另有十块同向支持。收益范围是未尝试联网的单人游玩，测量时LAD/RV/WB关闭，不是所有配置或联网性能保证。

玩家各400射，敌810→884；人口、种类略有差，节点候选少约1.1%，不报纯净单函数因果值。中间三块双方预绘分片均0，仍改善。最大帧306→473ms，候选473ms发生段内nativeBand443ms，不能剔除或断言无未完成预绘，具体来源未定。不称整体近原版或所有尖峰消失。

已完成单实例资格：生命周期7a10b4a47f为56/0、12阶段；真实采集回退f6eece7606为86/0、6阶段（原生喷火弹跨帧历史）。这些不是首次真实双人接入/对侧显示验证；不扩展为修复RC旧四项问题或多人性能承诺。

内存余量已恢复到原双实例6GiB以上，无须重复追问或降低保护。已实际跑：
- 5589fa431d / native-03：driver02在AIR虚拟app:/父目录为空失败，未联网。
- 622039485c / native-04：driver03路径通过，原版rbl没有28格双向射击走廊，未联网；清理全过，安装保持。
- 9b2366ad51/d87d5871bf：实际站位通过；附件正常将200发调整到72/90容量，夹具过早保存耗弹基线，已改为真实attack前一次记录。
- c6c9757ebc：首次联机、两向实弹与最终像素、冻结/解除全完成，但host在join退出后继续检查房间而报终态竞态；原FAIL保留。
- 最终driver07/native08/d0048aff49：两端各39/0、首次attempt各1、hello/welcome、十项coverage全true、finishing确认及所有清理通过。result.json SHA256 C103B58822FBE0547AB226907E0D138633D0A782A5FA4217EC4117356BE6C066；根独立核对，候选仍准确EB365、测试前后22安装项不变。联网功能门禁完成，不再追加无关场景。

RC负责人已完成安装及实际release输入的无诊断驱动冒烟ae58b8049b，原runner/登记PASS。根与子代理独立核对两端新版初始化、tick200、join welcome/unitsync、日志散列和清理；当前22项安装仅RC变化，source/installed同EB365、备份574D。本轮“真实战斗明显下降并部署复验”目标已达到，不把旧资源阻塞当当前状态，也不冒充整体近原版。

## 5. 已知限制与拒绝路线

- 宽屏战斗、高速移动和偶发长帧仍有差距；本轮不声称所有地图2–5秒、全效果近原版或SATS延迟已解决。
- 旧stableMotion逐帧Y/速度重置未真实落地；旧此类数据只作同夹具诊断，不能当原生移动验收。现用native-input-motion-3真实按键。
- atlas像素不等、远处显示根停动画/移树、空地形、bulletblend、Unit.blit复用等未证稳定安全收益，不安装。睡眠小白名单真实对照反而更慢，停止路线。
- 已确认旧compact实验曾被0.8.2配方误带入，但准确对照关闭更慢，不能因历史误带入就直接部署关闭。
- 全剧情、所有机关、联机、512×256最大尺寸与长时运行未全面验证。天角兽原生报警范围会随合图扩大，独立源码候选边界见第2节。

## 6. 下一步、构建与回退

本轮交付完成，下一次正常启动游戏生效。首次联机78/0及实际安装冒烟均通过，无需重跑已完成的性能和功能数据。原版墙面候选不并入本次，后续尖峰、高速/全效果仍可继续针对性归因；不得重启已被证伪的旧配方或将其累成必做事项。

RC本轮回滚点：../RConnect/build/m52/recovery-offline-deploy-01/RConnectMod.before.swf（574D2B51490AE8B25A1396555600F56A301F8A20AE50104C0E35CF2796441AFE）。回滚应核对当前仍为本轮EB365，由RC负责人协调，不覆盖未来版本。用户配置与存档保持。

撤回基线：state/afternoon-recovery-20261021.json verified，51项安装后检查。BEFC来源build/backups/sats-20261021-154054/pfe.swf，回退前5432另存build/backups/afternoon-recovery-20261021-222045。旧SATS/impact回执已rolled-back-by-user。

性能驱动build/rc-native-combat-run.py，冻结probe build/generated/rc-native-combat-20261023/probe-source/3fa568cbe2464a5ca40d6ccb37705e87。不要用旧motion整包构建/回退覆盖CS0.9.0或其他后续修改。历史宿主构建链motion-host incremental→motion-fog --rays→motion-direction不是当前候选发布入口。

## 7. 证据与深入入口

- knowledge/experiments/combat-stable-driver-20261022.md：当前真实性修正、归因、有效收益及失败路线。
- knowledge/experiments/evidence/rc-native-20261023-baseline-r1 与 candidate-r1：准确生产包1200帧对照。
- ../RConnect/build/m52/recovery-offline-{production-01,lifecycle-native-03,collector-native-01,first-connect-*}：候选、功能及首次接入证据。
- knowledge/experiments/afternoon-recovery-20261021.md、combat-recovery-followup-20261021.md：回退及此前11组无收益对照。
- design/single-map-authoring.md、state/deployment-v090.json：独立编辑器状态。
- design/alicorn-alert-range-candidate.md、knowledge/experiments/alicorn-alert-static-20261021.md：仅源码的另一任务。
- journal.md、MEMORY-history-20261023-0818.md：完整历史。旧0.8/0.8.2性能数、依赖与发布回执是历史，不当当前组合结论。
