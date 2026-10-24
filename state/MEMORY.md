# ContinuousScene — 当前快照

更新：2026-10-25镜头目标active、未完成。恢复实测后裁块无稳定收益，已停止；原尺寸atlas成本诊断移动37.0417→31.075ms，两对同向，但视觉RGB2未过旧RGB1。pow2首轮通过，随后同场同帧旧/新都RGB2，已否定补尺寸修复并停止。用户现明确接受RGB2/alpha0继续候选验证，仍须真实战斗明显提速且功能正常才部署；原failed不改写。当前原尺寸motion-only r1完整960帧通过：移动41.05→31.5ms，两对同向，static28.32→28.85；首建213ms保留，RGB1/alpha0、恢复精确。新camera-atlas-motion-combat-20261025-r1已登记等待真实1200帧交火，尚无新战斗结果。正式A796/RV BF4A未由本任务改动，原实际战斗57.33/34.35ms基线仍未接近目标。

## 1. 模组与体验

连续大场景把多个原版房间合成一个 Location；全图碰撞、敌人、物品预先生成，镜头与弹体可连续跨房。画面按视野提前分批绘制，远处未参战敌人暂缓行动，追击者和飞行弹体保持运行。CS0.9.0另支持可编辑的单一大地图，原版房间仅作样例素材。入口类 ContinuousSceneMod；正式文件 release/ContinuousSceneMod.swf。

原版任务由设置“以连续大场景载入原版地图”控制，下一次生成/读档生效；基地、后室和挑战保留原入口。普通返回/重新出发/随机图读档分别遵循原版保留、重置和回基地规则。内部相邻房间三角标记已移除，保留地图外沿和真正出口。

## 2. 用户约定与职责边界

- 2026-10-25用户明确接受RGB最大差2/255、alpha不变继续候选验证；实际战斗明显提速与功能正常仍是部署前提。先前RGB1失败保留，不回填通过。无需再为同范围重复询问。
- 当前性能任务用户进一步要求多实体、密集子弹、高速移动战斗接近原版；前轮约15%改善不代表新目标完成。2026-10-23检测到玩家重开游戏后，用户再次答复现在保存并退出。不要重复问已授权事项。
- 保持原画面、战斗机制及跨房连续性。已允许视野预绘与远处未参战敌人暂缓行动。
- 新反馈是跳跃明显卡顿、探索越深越明显，用户尚未试回起点比较。已明确接受纵向镜头缓冲及测试：普通跳跃少移动，持续升降仍连续跟随；这项镜头手感变化无需再问。
- 必要兼容授权包括 RV、WallBlend、LAD、TDFC、RConnect；RC协调已明确授权。RC负责人会话01a086bb-378c-7f60-b8e1-50d90ffa0996集中维护、构建和部署RC，本侧不并行覆盖它。
- 性能根会话01a13816-367b-7261-8e11-ca9152565dd9。所有游戏测试登记、唯一AIR ID、私有桌面、独立存储；不写真实APPDATA/pfe，不关闭用户或其他任务的进程，不用Ghost。
- 用户已要求撤回10月21日下午配方：绝不重新安装7D42/5432宿主或旧整包配方。
- 另一会话天角兽候选仅源码：1bf0e7b、src/patches/SceneAlicornAlerts.as.inc，不构建、测试、接入或部署。候选仅发送者X±960/Y±500（含边界），穿墙/跨旧房可通知；不擅改瞬移/支援人数/记忆。
- src/tests/SceneRenderChecks.as 是其他会话WIP，不恢复、不提交。无AGENT_SCOPE.md文件，未自行创建受保护薄壳。

## 3. 当前安装与候选

当前正式宿主在用户要求回退后的BEFC上保留已验证的遮挡格复用，并新增用户接受的纵向镜头缓冲；CS保持7F1F。RC和RV由各自负责人独立更新，不计作本轮算法改善的收益：

- root pfe.swf：A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7；state/scene-tint-deployment-20261024.json为verified，candidate-r1/installed-r1各20项通过。精确ABE2上仅Grafon.sceneUpdateEntityColor/sceneEntitySameColor变化，5769其他方法体、1016类/初始化器与素材保留。ABE2纵向缓冲和80CF遮挡格复用均继续保留；没有增加生产计时/诊断开关。
- CS0.9.0：7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F。
- RC由负责人独立更新为0.2.24-roomfix5：78C052AEA963F1689B705AE1E14D274916AE1A1F7E81933390CAF8D1A88F4699。installed-smoke.json记录ed2fa23d99单实例启动通过；recovery-room-user-deploy-01/deployment.json的smoke_status仍pending、performance_qualified=false，本侧不代改。旧DF0F/aura1性能证据不重标。
- ModLoader现为2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2，2.5.0/FrameRecorder1.0.0安装回执verified，telemetry enabled:true。此更新由负责人完成；本轮TDFC r6开始按新依赖冻结，旧BD71环境配对仍是历史组合。
- TDFC7ACD、LAD8ADB、WB1411；RV负责人现已独立部署0.33.9-effect-load，BF4AC9CD87272B03FAE7EC22EE67D045F037362F412EE801CAD3F9BA9FE3AFEF。effect-load-v3-output/deployment/receipt.json记录PASS与独立启动清理。新镜头组件r3、跳跃r2和TDFC LOS战斗实际使用的是历史0DBE/0.33.8，不重标成BF4A；更早6DBB亦保留原标签。RV负责人测得自身更新函数约20%/6%改善，但完整战斗帧没有一致显著改善，不计作本任务近原版已达。
- 前轮offline1已测生产输入与部署回执保留：../RConnect/build/m52/recovery-offline-production-01、../RConnect/build/m52/recovery-offline-deploy-01/deployment.json；当时状态deployed-smoke-passed，回执SHA256 7DB4BDC4F9BF9317A96EC51DB3076A5B8F0D49BBC9254692142BE92F7065EE86，不作为当前aura1部署回执。

历史EB365基于准确574D冻结源，仅三类和版本变化；未联网时跳过两组弹道/身体效果历史采集。首次host/join尝试即永久恢复采集（直到进程重启）；null、异常、非严格true均保守回退。保持墙面、感知、实际呈现、失效刷新和联网路径；生产包无诊断开关。其旧对照与门禁保留历史标签，不跨组合计算新收益。诊断88CC不得部署。

CS编辑器0.9.0已于10月20日安装并复验25+22项：Editor7344、EditorTools02F5、CS7F1F，168固定箱体逐件对应。192×50研发部样例，地图编辑器.vbs→大地图，应用maps/active.xml后重新进入读取；nativeEnabled独立。当前性能任务不重建编辑器。

## 4. 当前任务进展与停点

same-frame size-compare-r1（B1FE87）前三view旧/新均RGB1，第四旧/新均560像素/maxRGB2，alpha0、两次restore全0，玩家/计数不变，20/20释放；旧标准failed保留，pow2修复假设否定。新RGB2授权后回原C0E4物理尺寸准备motion-only：仅实际vx/vy/scale变化才呈现合图，静止保留native显示但缓存保留；首造/全部同步逻辑仍在，尚不能宣称解决首次或战斗。helper像素update第三参force=true并断言presented，计时2参+逐帧actual presented门禁。presentation_transform 2A4D350、探针6BBCE1，r1已实测960帧31134ms，实际呈现0/0/0/119/120/1/0/0；五view均RGB1/alpha0、恢复0、15/15释放，八计数/玩家不变。移动两对37.1167→31.0417及44.9833→31.9583；首B213ms、其他138/228ms尖峰全保留，仍只暂停诊断。后续motion-combat r1仅Main+Atlas两源/85文件，真实4×300，已登记等待；逐帧actual/previous呈现、世界坐标/quake、copy/rebuild和终态释放门禁齐全。Camera vx/vy为int，world小数来自震动/缩放；旧0.8+quake大色差仍未解决，RGB2授权不覆盖。

pow2-r1（543030探针）完整960帧31744ms，五视口RGB1/alpha0、恢复0、15/15释放，预绘等八计数零变。移动两对均值35.783→34.333和45.425→35.842；第一对P9543→48变差，第二对65→46，静止新版本31.596ms比原生24.979慢，首建图348ms。四层物理存储前2view256MiB/后3view128MiB。此为不同随机世界，不能和旧r1跨轮归因像素修复。camera-atlas-size-compare正在准备同帧native/旧atlas/restore/pow2/restore，以旧失败新通过的实际反例决定是否继续；内存和静止退化未解决，不部署。

独立成本诊断camera-atlas-cost-20261025-r1（E68CE探针）保留RGB1、alpha0和精确恢复门禁；只允许RGB超差后继续计时，顶层ok=false/唯一camera-raster-visual失败/登记failed不变，timingComplete单列。完整960帧30788ms，五视口中四个RGB2、一个RGB1，alpha全0，全部恢复零差，15/15释放；八计数全零增量。每模式240原帧，native移动37.0417/中35/P9545，atlas31.075/30/38；两对37.933→30.992、36.15→31.158同向，首次146ms构建和原生181ms尖峰均保留。static29.179→30.988；只支持当前暂停整数条件继续查像素。移动窗0重建/0复制，尚不能外推长距离或开火。旧atlas变体没试过右/下透明补尺寸至2幂；这只是尺寸敏感性新假设，不是已证GPU机制。

2026-10-25恢复实测：旧strict r2首视口600像素RGB差1/alpha0，恢复零差，3/3截图释放，未计时。独立容差版701E源仍基于B7ED/39A冻结闭包，五视口532–823像素RGB1/alpha0、恢复全部精确，15/15释放；完整960帧总32397ms，预绘/驻留等八计数全不变、玩家不变。合并每模式240原始样本：native-static29.4667/中28/P9542，crop-static30.2125/28/45，native-moving37.4958/37/47，crop-moving37.8125/35/53；191ms尖峰保留，两个移动窗口方向相反，不能凭中位改善声称加速。guarded crop仅语法候选，未宿主组装或部署，停止推进。

现有SceneRasterPresentation C0E4在相同暂停整数条件下另测camera-atlas-20261025-r1，探针8E14312、入图5388ms。前三视口RGB1，第4视口1078像素不同/maxRGB2，alpha全0、恢复全0、12/12释放；无windows/frames/samples，不作性能结论。原526输入与528隔离输入核对通过。旧atlas/rows原始复制无损但显示合并已出现max2，不重试补gutter/横条/延迟scrollRect。原生屏外根隐藏、摘树与缓存也已有无稳定收益反证，不能仅凭全图对象数量重复开展。源与证据在camera-atlas-20261025及同名evidence目录。

2026-10-25离线候选准备：camera-crop-20261025以冻结75157仅抽六方法；逐方法Compare确认与实际A796一致，未整类重编旧源、未回退tint/lighting。helper163959提供单位整数/仅320资格、可见休眠副本、原生操作层同步/批量强制同步、SATS原图及候选错误计数回退。prepared/c7b27d86dbc54f0ea29b8ac403f66c1b；动态语法检查syntax-builds/c36a9c8fbe9d47699fa67992ef8430e2通过，首轮World桩同文件失败保留。原游戏/画面/性能均未跑，动态字段检查不能当封闭宿主集成验证。受保护RV/滤镜组合和640仍原路径，未解决全部目标。镜头诊断暂停后原生World仍有Camera/GUI/Pip/SATS，helper又调用Camera，不能称纯渲染成本。后续先实际验证679A归因收益，才组装实际宿主候选并验全部未改方法/兼容/战斗。

2026-10-25镜头专项：旧tilecrop两次正向线索与后继nativecrop的像素失败已重新分清，不再与front-shadow混为一条路线。先限定整数平移测呈现成本，未承诺降低缩放/震动画面标准。诊断phase97保存并恢复Camera/显示/暂停/帧率等，Flash时间轴与其他回调仍活跃，结果只归因不当战斗验收。冻结probe-build位于camera-raster-20261024/probe-builds/probe-source/853bd6ac5a0b419db21bea201a463e32；主源CA8C/helper88A4/探针679A。用户保留B190 player-1/player-2窗口（当时88248/91064，后续须核身份，不能只凭旧PID）；只离线准备，不结束玩家实例。恢复实测后才决定是否推进生产裁块/即时同步及原显示回退，当前没有新生产修改。

最新性能停点：sampler-capability实际AIR成功；combat-sampler-v1超过十万记录上限且角色越平台，失败保留。v2/v3各完成1200帧26项，但混合时间顺序失败；v3独立review确认956条CPU样本各自时间与索引严格递增，仅允许栈名称出现次数。顶层[render]/[pre-render]/[execute-queued]205/157/93，含FocusManager39、Turret.animate80，祖先栈可能只是排空全局动画队列，不是分配发起者。turret-timeline组件38组像素/引用一致、每侧141构造事件，未做跨帧，candidateEligible=false；停止炮塔简单选帧guard。focus-control v1/v2因错误空焦点假设而0样本失败；v3实际1200帧26项/44快照/67,492ms连续守恒，A/B均57/55.4867ms、敌740/699、预绘43/1slices，末两段仅差.9ms；整体关闭收益不够且混杂，停止不部署。公共恢复末态通过，唯一焦点循环和35ms重建保留计时。正式A796/CS7F1F/TDFC7ACD不变。

弹壳线索已结束：45条Part.initVis包含栈中40条来自Weapon.shoot→gilza。单帧素材局部三对即时及真实ENTER_FRAME像素/引用通过；精确单方法50D6产物保留RNG及全部其他方法/素材。真实候选两轮分别900/0完整帧后击退越平台，没有完整性能验收，停止且不部署。正式A796的后续黑雾观测也在第四段击退越界，不能单凭候选失败断定其有回归。黑雾33快照均valid，屏内仅1–4显示根、面积和最大16614.545/2032×1084约0.7543%；只读扫描总208ms扰动计时，不作FPS。原始失败、冻结输入和独立审查见occlusion-census/README.md与partial-review.json。

TDFC单条视线复用r6组件38对全等，但combat-r2 A/B均61.3067/60.4717ms，A预绘4块23slices、敌1010/904；收益不足不部署。checkShelf单行Y前置与tdfc-retreat-lazy均仅静态方案，未编译测益，不因现成源码就重复推进。所有诊断新源从B7ED/39A的85文件冻结闭包派生，不使用当前活源重建，保留其他会话WIP。

最新闭环：两方法颜色修复A796已按本机持续授权部署，实际安装文件组件20项通过；三组组件和精确字节码审计见scene-tint-20261024.md。备份build/backups/scene-tint-20261024-110720-c26a0e46/pfe_before_ContinuousScene_tint_20261024.swf为ABE2，仅在正式仍为本候选时可回滚。原始r1比较器失败、内存预检中止和登记工具临时错误均保留。组件直接调用真实方法，不宣称完整跨区行走或长时间游玩验证。

environment-control场景/普通房已各完成1200帧，精确同D972探针与全部输入，地形/路线/视口四项匹配。来源是B7ED收据冻结的39A原测试源，仅增加两次UTC/getTimer内存锚点，无cameraHold或新177块预备。当前A796上大图均71.479/中66/P95 109，普通44.585/41/65ms；脚本墙钟27.260/11.823ms、区间外余量44.232/32.759ms。大图敌1883射/平均夹具弹6.644、普通1316/3.999，初始世界单位151/11，不是等人口因果实验。进程CPU与测量阶段对齐覆盖99.626%/98.303%，均2.001/1.716核；全线程统计不代表主线程或GPU。大图驻留129→137、计时预绘8块/36 slices/521ms，misses/forced0；普通无预绘。近原版未达，不能把今日约107ms全归环境，也不能只归镜头；根任务继续核查TDFC单条视线重复取格的小候选，尚无新性能部署。

camera-no-world-r1已完整1200帧通过；A/B/B/A均137.743/96.917/109.747/83.680ms，隐藏后跟随均110.712/中82，固定103.332/中86，末A反而最快。敌1769射高于可见1254，不能把跨轮差额当渲染净成本。世界可见性与镜头状态完整恢复，计时177块/预绘计数不变。前日/今日可见/隐藏脚本墙钟均22.60/41.63/62.30ms，旧全程CPU含启动而未对齐，不能直接和environment-control的测量期统计比较。三轮实际ModLoader均BD71/2.4，无帧记录器；新增telemetry.json不是已证原因。后续若负责人发布新版仍按实际冻结输入核验，不假设版本永远不变。

2026-10-24本轮：camera-combat-20261024-r1完整4×300跟随/固定/固定/跟随，跟随均122.18/中101，固定均92.735/中81ms；四段玩家各100射，敌430/329/198/297，火力混杂。观察helper均<.31ms；计时resident177/预绘计数不变。4060ms尖峰中1400在nativeBand、2652在所包围脚本区间外，原因未知，不称GPU/GC。随后隐藏世界诊断也已完成，结果如上；两者均不得作为产品安装。它们的准确原输入为ABE2/CS7F1F/RCDF0F/RV0DBE，后续environment-control才使用A796。

颜色基线r1暴露AIR乘数量化：原生green .8/1.16实际显示 .796875/1.15625，sceneEntitySameColor误当外部颜色而拒绝普通跨区更新；另玩家自主悬浮levit1也跳过显示更新。r1测试比较本身亦错，失败保留。r2真实Sprite规范化期望后baseline-r2通过20项，分别重现两缺陷、箱体真实dropTeleObj及外部色保护。build/generated/scene-compat-20261024/tint/product的两个定向方法已完成最终导出、严格审计、candidate与installed各20项组件及发布门禁，A796回执verified；源同步和记录里程碑已提交1eafc99。玩家豁免levit门控，SameColor原快速路径失败后用未入树Sprite实际setter/getter规范化b再严格比较，先拒绝非有限值。早期两次提交余量不足、登记表临时WinError5与短暂SyntaxError完整保留；没有降原生运行保护、绕登记或修改ModLoader工具。

RV0DBE启用路径只读发现current每帧整图遮挡扫描、全单位/物件遍历，classic全图记忆维护/约7.41MiB雾层复制；射线与显示本来已有局部范围，不能重推“只画视野内”。根任务后续已核：RV关闭且字典清空后不再每帧遍历全图，原生findCel也不全图搜索目标，不继续把这两项当成本轮关闭RV负载的原因。RV负责人正在D43密集特效优化，未混入或归功本任务；遮罩交接静态风险组件只准备未运行，因用户澄清主要是性能而暂停。未改RV生产源码/包。所有本轮源/辅助均在scene-compat-20261024目录，foreign SceneRenderChecks与Alicorn不动。

最新真实跳跃工作见knowledge/experiments/vertical-motion-20261023.md。r1首跳含原生水平惯性，第二跳为纯Y；r2补dx=0/左右键释放后仍45.78/44.04ms，静止约33ms。所有测量窗无新块/缺块补绘，纯Y每窗3次150px跳跃、镜头跨度149px。native-r1平台floor120导致原生向上换房，0样本，保留失败不当CS故障。固定镜头ABBA诊断720帧合并A44.1958/B35.2208ms、约20.3%差异；仅诊断，不当产品收益。growth-r2被自设1.5GiB进程预算拒绝；核实系统提交余量14GiB后，r3诊断预算2GiB并新增4GiB提交/2GiB物理预检，512MiB运行保护不变。r3完整1440帧，驻留124→155、private +72.08MB，跳跃43.271→41.521ms，没有复现随此增长恶化，不能当真实探索验证。

用户接受的真实缓冲候选在build/generated/vertical-camera-band-20261023，仅Camera.calc定向方法；动态nativeAPI.verticalCameraState存唯一上下文，不加Camera字段。正常跟随半带≤160px、按screenY与完整碰撞高度缩小，带外硬跟随；缩放/loc/camera/屏幕变化、传送与退出观察时重新定位，原观察/camRun/边界/震屏/sceneTick等保留。ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A已构建，严格保留5770个其他方法、1016类/初始化器与原素材；组件r3共65项/56次实际calc通过。前两轮组件失败分别是探针public静态访问命名空间和DisplayObject小数坐标量化期望，已保留，不改候选迁就断言。真实跳跃三轮每轮720帧/12次150px跳跃：A49.3958、B37.8708、反向A46.0417ms，B镜头不随普通跳跃移动；自然活动28/25/28，不能称精确净提升。普通房/缩放/观察/传送等为组件覆盖，不冒充完整玩法。vertical-activity-20261023的engaged只读观察仍未运行。

密集战斗四轮完整1200帧：A1 61.3308/中58/P9583，B1 66.87/63/95，反向A2 67.7975/63/99，B3 60.9883/57/84ms。A合并均64.5642、B63.9292，中位均60；AI活动/火力/预绘不同，约1%差距不算战斗收益。首B活动49.35比首A40.15多9.2，B3火力低于A2；无持续回退信号，限定放行已验证的跳跃改善。B2完成900帧后实际角色离开平台，原因为何未捕获，不能称已证击退；失败完整保留。release-qualification.json绑定全部8组完整证据及不完整B2，check通过，deploy已完成实际安装65/0验证。总体性能未接近原版，不将此发布作为战斗问题解决。

本轮先前部署80CF的小幅算法改善，ABE2继续保留它，近原版目标仍在进行。此前BEFC低干扰denseV2真实Shift/六LMG/玩家ASSR共探针1200帧：原版均35.573/中34/P9547，大场景均63.253/中59/P9594，双方实射400/2009和400/1109。路线/地形/视口相同，大场景火力更低仍慢；不称近原版。V1原房2659ms尖峰已定位探针startCase2591ms，V2移除段边重复设置/整报告写入，未扣帧伪造速度。

背景长ABBA无收益；短ABBA表面6.24%改善但敌方火力和预绘更少，尚不稳。571次完整扫描无不透明块，停止该缓存。区域合成缓存049DE诊断1200帧目标calls/rebuilds全0，排除本负载热点，不生产构建。详细结果见knowledge/experiments/dense-combat-near-native-20261023.md。

349F单方法Location诊断：大场景总15.7–19.0ms/帧，单位4.1–5.1、子弹3.3–5.2、玩家2.5–3.0、原生lighting2.5；600箱子仅.2–.3。原版同负载总6.5–7.7、单位2.0–2.8、子弹1.3–1.9、lighting.55–.61。B8C子弹分段：hitTile包含1.35–3.25ms/帧，单位遍历.28–.64。RC owner19FF诊断1200帧墙采集仅.37–.46ms/帧，0重建/0compare，不是主因，已回报owner。

后续decal3401诊断1200帧：outer7.4–7.85ms/次、scenePaint2.89–3.19ms/次，素材准备仅.055–.088，降低素材缓存优先级。普通房该轮900帧后真实击退越平台，完整失败保留。休眠显示根缓存短ABBA均63.708→64.468ms，没有稳定净收益，停止。lighting2整数循环BCCF六组组件状态/像素一致，但真实战斗900帧仅16次调用（原4次10ms，新12次12ms），第16窗击退越平台终止；它不解释2.5ms/帧视野成本，停止。clipRect历史已测无稳定收益，不重启。随后CS只读stats快照已完成，见下文；V2原world已记录retDark=false、240×125、lDist1=600/lDist2=2000。未缩范围，这些诊断均未部署。

Location首两轮因系统可提交余量约.4GB中止，未产终态不作有效样本。用户已正常关闭暂不用程序，余量恢复7.16GB后上述分组实测完成；不重复要求退出，不降低512MiB运行保护。全部新驱动/审计在build/generated/combat-near-native-20261023，准确宿主/探针各自独立，不叠加诊断。

只读activity-spatial-20261023-scene-r1已完整1200帧/26项/44快照：159单位、活动均47.16、屏外26，缩为视口+320或玩家±900×700的数量上界均13.86，但搜索状态未观察，不能直接休眠；当前宽限内立即可减0。正式调度不改。

上述fog-terminal已实测并停止：84组/30000格状态像素全等，真实20×60/90项通过但均63.343→64.007ms，视野每次2.743→3.027ms，496810次实际提前拒绝也无净收益，不部署。activity-internal已完整1200帧/26项/44快照，实际域身份一致；无当前目标的Merc仍有state2/3和正警戒值，不能一律暂停。已核平静Raider家族均4.41个只是缩范围上界，engaged/宽限仍保留。

fog-bitmap-lock首次try/finally导入将整个lighting变为67 activation槽，停止保留。独立inline 4A84严格单方法审计与84对像素/状态通过；真实20×60/90项A58.163/B59.793ms、P95 70/75，仍无净收益，停止。A594次调用仅472写像素，B590次1401写、104对称lock/unlock，写入稀少。无生产构建，不再补此诊断的异常清理。

decal-stamp-proof历史停止：r1旧Flex要求显式终末return；r2实际擦除像素不等；r3普通paint的alpha变换差10个RGB像素；r4限定alpha保持后bullet_tre第5帧仍差7个RGB像素（最大通道差1），未进入跨块检查。原失败证据完整保留。用户随后接受测试微小色差，新decal-stamp-tolerance-r2在当前80CF完成172项（1482ms）：153全等、158在每通道RGB≤1/alpha0内、14超界，全部alpha一致；重复32次可出现RGB差2，相邻块最大4。超界53个目标像素，12个alpha255且RGB差2，不能以低alpha反归一解释为≤1。2580/2580临时图释放、宿主引用及525安装输入保持。r1仅比较工具的alpha-only边界哨兵失败、0实际case；r2改为getVector全ARGB扫描并通过4项哨兵。copyPixels独立变体r1（1200ms）172项除耗时外完全相同，仍14超界；两路均停止，未计战斗性能、未生产化。全结果在各新目录RESULTS.md/README.md；可复用比较方法已归档KB-000111修订1。

front-shadow保持原400px前景及原生弹痕算法，只在帧尾复制变更块给同尺寸显示副本。pixels-r1/r2均未进入候选：r2证实早期落地150帧但周边预绘约500帧，随后击退越平台。r3在六名测试敌人创建前用原生sceneTick同步准备测试视野，7833ms单列、不作加载收益；30帧双方10/52射，50次实际同步，四组整屏像素全等，177副本全部释放。冻结探针9E58、helperFB44、patchDBD0、runner5681，均仅隔离使用。

front-shadow-short-r1/r2同探针各20×60、90项通过，实际原生高速移动、六敌LMG+玩家ASSR，玩家各400次，无预绘/缺块/新块/清理异常。r1 A/B均65.0567/63.2633ms、中61/61、P95 90/81，敌882/863；r2均64.010/61.505ms、中61/59、P95 85/78，敌815/887。各五块均值四好一坏，原生AI/速度/同时弹体负载不同；仅小幅改善倾向，不称显著或接近原版，不部署。副本常驻约108MiB，r1B仅56/693次revision是重复合并上界且混有其他层；仍保留全部原生矢量draw。完成两轮后不扩建此诊断设施、不反复同样短测。

fog-last-blocker 38C7已严格审核并通过89对（原86+负visi两对+弱水），不叠加terminal/lock。历史EB365组合真实两轮20×60/90项A/B均61.463/60.572、63.228/61.418ms，10块7块改善；lighting每调用2.694→2.038、2.743→1.975ms。已观察到可重复的函数收益和小幅整帧改善，仍非近原版。独立无计数生产80CF仅在sceneLarge&&bounded&&interiorRay生效；BEFC基线和80CF同冻结探针各91对原生legacy/typed全图状态与像素一致并恢复。生产组件不测缓存命中，另两对sceneLarge=false仅验证标志旁路，不是原版房玩法验收。新生产对照统一RC DF0F/RV6DBB组合，80CF已部署，详见第6节。opacity-call-cache的101对通过，但真实A/B均64.24/64.1083ms，几乎不变，停止该方向。被钩子误拦的stamp驱动源码写入已按此前授权登记10分钟精确补丁完成，未关闭护栏。

80CF生产对照完整保留：baseline-r2均65.795/中63/P95 91，candidate-r1均60.415/中56/P95 80，但敌方出膛1875→1063、活动均46.75→41.55；candidate-r2均56.1975/中54/P95 75、敌方1622。反向baseline-r4已完成1200帧，均58.2075/中56/P95 75、敌方1806；与candidate-r2比较仍有火力/预绘混杂，不报精确净百分比。普通房双1200帧A35.520833/中34/P95 49/max188/敌1651，B34.1925/中33/P95 43/max132/敌1767；旁路未见回退，也不把这个差值当作未启用算法的收益。各完整轮玩家400次。首候选820ms长帧未落在现有计时脚本段，原因未定；baseline-r1预热超过1200帧仍未稳定、0样本，baseline-r3第二段前原生击退越平台、仅1段完成，两次失败保留。

测试工具修正：motion-test.py air_pids改Toolhelp32直接按名称枚举，避免沙箱OpenProcess拒绝被误当无AIR；首次后台桌面权限失败0e722d...已核对本轮进程退出并恢复登记。实际游戏测试需允许私有桌面启动的执行权限；不杀玩家游戏。

真实战斗已获得可重复约15%改善，联网门禁、精确部署和安装冒烟全部完成。原574D与EB365各1200帧、90项PASS，原生按键/物理/真实双方开火、同地形及路线：平均69.615→58.866ms，中位64→54，P95 96→80，>100ms帧51→32；五块均值/中位都改善。两轮诊断ABBA另有十块同向支持。收益范围是未尝试联网的单人游玩，测量时LAD/RV/WB关闭，不是所有配置或联网性能保证。

玩家各400射，敌810→884；人口、种类略有差，节点候选少约1.1%，不报纯净单函数因果值。中间三块双方预绘分片均0，仍改善。最大帧306→473ms，候选473ms发生段内nativeBand443ms，不能剔除或断言无未完成预绘，具体来源未定。不称整体近原版或所有尖峰消失。

已完成单实例资格：生命周期7a10b4a47f为56/0、12阶段；真实采集回退f6eece7606为86/0、6阶段（原生喷火弹跨帧历史）。这些不是首次真实双人接入/对侧显示验证；不扩展为修复RC旧四项问题或多人性能承诺。

内存余量已恢复到原双实例6GiB以上，无须重复追问或降低保护。已实际跑：
- 5589fa431d / native-03：driver02在AIR虚拟app:/父目录为空失败，未联网。
- 622039485c / native-04：driver03路径通过，原版rbl没有28格双向射击走廊，未联网；清理全过，安装保持。
- 9b2366ad51/d87d5871bf：实际站位通过；附件正常将200发调整到72/90容量，夹具过早保存耗弹基线，已改为真实attack前一次记录。
- c6c9757ebc：首次联机、两向实弹与最终像素、冻结/解除全完成，但host在join退出后继续检查房间而报终态竞态；原FAIL保留。
- 最终driver07/native08/d0048aff49：两端各39/0、首次attempt各1、hello/welcome、十项coverage全true、finishing确认及所有清理通过。result.json SHA256 C103B58822FBE0547AB226907E0D138633D0A782A5FA4217EC4117356BE6C066；根独立核对，候选仍准确EB365、测试前后22安装项不变。联网功能门禁完成，不再追加无关场景。

前轮RC负责人完成安装及实际release输入的无诊断驱动冒烟ae58b8049b，原runner/登记PASS。根与子代理独立核对两端新版初始化、tick200、join welcome/unitsync、日志散列和清理；当时22项安装仅RC变化，source/installed同EB365、备份574D。前轮“真实战斗明显下降并部署复验”目标已达到，不把旧资源阻塞当当前状态，也不冒充整体近原版；当前安装与后续任务见第3、6节。

## 5. 已知限制与拒绝路线

- 宽屏战斗、高速移动和偶发长帧仍有差距；本轮不声称所有地图2–5秒、全效果近原版或SATS延迟已解决。
- 旧stableMotion逐帧Y/速度重置未真实落地；旧此类数据只作同夹具诊断，不能当原生移动验收。现用native-input-motion-3真实按键。
- atlas像素不等、远处显示根停动画/移树、空地形、bulletblend、Unit.blit复用等未证稳定安全收益，不安装。睡眠小白名单真实对照反而更慢，停止路线。
- 已确认旧compact实验曾被0.8.2配方误带入，但准确对照关闭更慢，不能因历史误带入就直接部署关闭。
- 全剧情、所有机关、联机、512×256最大尺寸与长时运行未全面验证。天角兽原生报警范围会随合图扩大，独立源码候选边界见第2节。

## 6. 下一步、构建与回退

当前以A796及state/scene-tint-deployment-20261024.json的verified回执为准；environment-control场景/普通房同探针配对已完成。上一镜头里程碑ABE2的state/vertical-camera-band-deployment-20261023.json仍保留verified历史：2026-10-24 00:00备份80CF至build/backups/vertical-camera-band-20261024-000000-9ee00a9c/pfe_before_vertical_camera_band.swf，524依赖保持，安装后65/0、56个calc案例通过，结果SHAF8CC27E86C17FA27802C21ACA4DA447E062EE09FBD4DA17E69B817CBA3E32E38。其rollback只适用于正式仍ABE2时，不能覆盖现在A796。后续实验必须保留当前宿主全部已验证改动并重新冻结输入，不能直接使用旧80CF/ABE2部署或回退入口，也不能混入外部天角兽候选。

80CF按release gate 2026-10-19.1完成本机部署；持续授权无需重复确认。state/fog-last-blocker-deployment-20261023.json状态verified，实际pfe指纹与回执一致；安装后fog-blocker-product-20261023-installed-native-r1为51/0，结果SHA73C7B1804B411E7C1260DAD0A1D6E1EC91AC6FD37A773DC6901EF673D0FD7B99。备份为build/backups/fog-last-blocker-20261023-184722/pfe_before_ContinuousScene_fog_last_blocker_20261023.swf（BEFC），回退前须核当前仍是本次80CF，不能覆盖后续他人改动。

近原版目标仍未完成。2026-10-23用户已接受测试近乎看不出的色差，要求明显提速后再考虑部署；本轮以RGB≤1/alpha0保守验收，图章draw/copyPixels均失败，前景副本虽像素通过但2400帧仅小幅改善，全部不部署。原失败与冻结源保持，不再重跑同一路线来挑好结果。下一轮需新的高占比证据：活动屏外单位的动画与枪口位置/出膛顺序耦合，不能整段跳过；仅body blit可研究但SATS/死亡截图与先blit后推进帧的时序必须保留，尚未测该项成本。sceneApply全驻留粗排除也是小候选，上界不足约1ms/帧，先不扩建索引。当前安装为A796；TDFC单条视线候选已完成组件与真实战斗，但收益不足，停止不部署。当前57.33/34.35ms同组合差距仍在；后续需要新的高占比证据，不能重复已否定路线。前轮RC首次联机及安装冒烟历史已完成，无需重跑无关联网项目。原版墙面候选不并入，不复活旧配方。

RC前轮历史回滚点：../RConnect/build/m52/recovery-offline-deploy-01/RConnectMod.before.swf（574D2B51490AE8B25A1396555600F56A301F8A20AE50104C0E35CF2796441AFE）。当前已是负责人后续DF0F版本，不能直接套用旧EB365回滚；如需回退由RC负责人核对当前版本与对应备份，用户配置与存档保持。

历史撤回基线：state/afternoon-recovery-20261021.json verified，51项安装后检查。BEFC来源build/backups/sats-20261021-154054/pfe.swf，回退前5432另存build/backups/afternoon-recovery-20261021-222045。旧SATS/impact回执已rolled-back-by-user；当前正式已前进至A796，不能再把BEFC当作当前安装。

旧性能驱动（包括build/rc-native-combat-run.py及各BEFC诊断/对照）绑定历史BEFC基线，未来不能直接运行其部署/回退路径覆盖A796；新工作须明确保留当前宿主改动并重新冻结输入。历史probe build/generated/rc-native-combat-20261023/probe-source/3fa568cbe2464a5ca40d6ccb37705e87保持。不要用旧motion整包覆盖CS0.9.0或后续修改；motion-host incremental→motion-fog --rays→motion-direction不是当前发布入口。foreign SceneRenderChecks WIP继续不触碰、不提交。

## 7. 证据与深入入口

- knowledge/experiments/dense-combat-near-native-20261023.md：当前近原版任务、80CF生产组件/普通房与大场景对照/部署复验，含混杂因素及失败样本。
- knowledge/experiments/combat-stable-driver-20261022.md：当前真实性修正、归因、有效收益及失败路线。
- knowledge/experiments/evidence/rc-native-20261023-baseline-r1 与 candidate-r1：准确生产包1200帧对照。
- ../RConnect/build/m52/recovery-offline-{production-01,lifecycle-native-03,collector-native-01,first-connect-*}：候选、功能及首次接入证据。
- knowledge/experiments/afternoon-recovery-20261021.md、combat-recovery-followup-20261021.md：回退及此前11组无收益对照。
- design/single-map-authoring.md、state/deployment-v090.json：独立编辑器状态。
- design/alicorn-alert-range-candidate.md、knowledge/experiments/alicorn-alert-static-20261021.md：仅源码的另一任务。
- journal.md、MEMORY-history-20261023-0818.md：完整历史。旧0.8/0.8.2性能数、依赖与发布回执是历史，不当当前组合结论。
