# ContinuousScene — 当前快照

## 1. 模组与当前任务

全图碰撞、敌人、物品预生成，画面按视野准备，镜头与弹体连续跨房；远处未参战敌人可暂缓。CS0.9.1另含单地图编辑及天角兽局部报警/接力概率，原版连续模式由设置开关控制。

性能任务仍未完成。用户最新反馈：镜头移动明显卡；镜头固定时玩家动作偶发卡；活动敌人/弹体出现时严重卡。目标是接近原版的实际动态游玩，不能用暂停世界、静止无敌对对象或删敌人的数字冒充。历史goal的blocked状态不代表当前工具状态：2026-10-28 12:40 get_goal实际返回null，本轮没有创建/更新goal。

## 2. 约定与权限

- 中文简洁进度；性能会话01a13816-367b-7261-8e11-ca9152565dd9。已允许实测；通过相应门禁后可本机部署，不重复确认。
- 已允许必要RV、WallBlend、LAD、TDFC、RConnect兼容。RC由负责人01a086bb-378c-7f60-b8e1-50d90ffa0996集中部署，本会话不并行覆盖。
- 已允许修复ModLoader共享测试登记器，已完成。其他跨模组写入不自动扩大。
- 接受视野预绘、远处未参战敌人暂缓、纵向镜头缓冲；保留追击者和飞行弹体。允许RGB最多2/255、alpha不变的实验，仍须真实明显提速与功能正常才部署。
- 当前完整大场景性能测试保持4GiB提交/2GiB物理预检、512MiB运行中止；有界等待采用3次间隔5秒均≥5GiB。此为该夹具保护，不是所有离线操作统一门槛。低内存离线构建独立限制自身512MiB，不改变游戏保护。
- 测试先登记，唯一APP ID/存储、私有桌面，默认静音；不写真实APPDATA/pfe，不停玩家或外部实验，不用Ghost。跨会话协调不能超出用户已授权的具体消息。
- 一次10分钟实验协调已使用，对方无安全自然暂停点，窗口未开始；不重复发送或干预外部进程。当前无自有Java/AIR/等待句柄。
- 已授权按本会话逐条登记≤10分钟精确构建调用授权，不关闭护栏。hooks当前exec映射Bash，载荷command；根functions store有cs_exact_grant_template（上下文丢失时按hooks README重建）。
- 无AGENT_SCOPE；不创建。src/tests/SceneRenderChecks.as是他人WIP，不恢复或提交。2026-10-28另一用户授权任务已取消天角兽旧“仅候选”限制并部署，不能回退其更新。10月21日下午被撤回7D42/5432配方仍不可复活。

## 3. 当前正式安装

天角兽任务已提交2e828d8；RC负责人随后部署0.2.24-animfix2/F14A44E7（回执125F9222），其余正式输入保持。本性能回合没有部署任何文件。

| 文件 | SHA256 |
|---|---|
| 根pfe.swf | 4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75 |
| CS0.9.1 | 9A5E24E13AF2E2E211FAEAC038697D2CA2641CD6482766048BC3B9B4A506AA31 |
| TDFC | 7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5 |
| ModLoader2.5 | 2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2 |
| RV | 638E2D408E2CF46683C41114F75773829A1B4417D74BFFE9D08855A4FE343710 |
| RC | F14A44E74AC98EC480875203D4D714ACFBC496141980E5A1D7B0DE0C7AD222FB |

LAD8ADB/WB1411保持；526正式文件/13运行输入。alicorn部署回执state/alicorn-alert-deployment-20261028.json，SHA2B2CBB6A；备份build/backups/alicorn-20261028-121734-7ee3b24f。31项局部报警/概率/设置验证属于另一任务，不是性能验收。A796染色/纵向缓冲/遮挡格复用全部保留。
共享工具：air_test_process ECE3ED08、test_resources 86D5F280、test_registry E3E43581；资源只设自有子进程normal CPU、memory5、HighQoS，不能改全局或外部进程。

## 4. 本轮实际进展与证据

详细记录：knowledge/experiments/camera-live-reassessment-20261028.md。

1. 复核旧F15：环境分配65312→0有效；native-once跨实例移动26.5667→24.5278ms（约7.7%）不是稳定收益。静止也降约4.04ms、驻留133/117不同、内存接近中止线。旧结果不改，不称镜头或战斗修复。
2. 新纯Python构建已真正通过：build/generated/camera-environment-paired-binary-20261028。诊断宿主51C90D997A759E783024CB43F8957D0B97F1241B1C41C064F9ADE12125135115；audit 1E208398。约1.59秒、自有峰值88,756,224B，未用Java/XML/AIR。
3. 先严格证明A796→4E5F只涉及五个Alicorn方法及对应method_info、新增常量；control新增NEED_ACTIVATION，不能误说method_info全不变。再反向还原诊断到4E5F，保留其余5770体/1016类/5038原始tag及五报警方法。新增string8173/8174、QName9717/9718；F15算法只迁移缓存QName。二进制回执诚实标python-direct-abc，非FFDec审计。
4. paired驱动尚未编译/运行。已明确host-root及新部署回执；宿主起末源指纹检查，独立验证同一producer。timingBands明确为outgoing混合区间，边界native属incoming；不报告模式独占原生耗时。115 runner输入/77 fixture输入已核。
5. 新真实战斗后继camera-live-current-20261028复用FA2B六LMG/ASSR原生冲刺；其r1在silent seed因Codex私有存储重定向误判而构造器前失败，无AIR，旧输入与回执冻结。8fa登记核实恢复interrupted。随后camera-live-current-silent-20261028明确只认同UUID的本机确切Codex缓存位置；API15700如实记无包身份。99字节种子实写/回读/拒绝覆盖通过；只清已知构造器前失败的launching。
6. **旧RC2C49真实战斗已完成**：camera-live-current-silent-20261028-r1，AIR39128退出，独立verify_run再次通过。当时526正式/13runtime、1200完整间隔、26原断言、独立原生静音、加载/资源策略均通过；最低提交3,799,351,296B，无外部AIR。follow平均59.398ms/P95 77/最大204，held55.492/P95 74/最大180，各600帧；玩家开火200/200、敌人880/898、敌弹在场5.492/5.533。每帧都有夹具敌人移动，冲刺271/252帧。全部长帧保留。
7. 相机额外约3.907ms（此负载约6.6%），固定镜头600帧仍全部>33.334ms。Stage混合20.163/20.125ms、整个Stage监听段21.496/21.437ms；约34ms未被其覆盖，不能叫纯GPU。图块177常驻、计时warm/draw全0；另预热7610ms。entry5022ms仅该轮，不代表全地图加载达标。
8. **当前RC2普通/大场景参照均完成并独立核验**：camera-dense-reference-rc2-20261028-normal-r1/scene-r1，AIR56856/67024已退出；复用dense-v2探针7F1F0B（不是同名产品7F1F），同原生六LMG/ASSR/200px冲刺，各1200完整间隔。normal均35.510833ms/中位34/P95 46/最大123；scene59.570ms/中位58/P95 75/最大167。Stage监听段10.53211/20.20517ms（各1199条），native带9.05833/18.85917ms（各1200条）。计时无新warm/slices/miss/forced/empty，scene常驻130块、普通0。不同自然群体/镜头边界仍保留，差24.059ms不是纯渲染或GPU因果；旧RC固定55.492ms仍是有效历史，不能冒充当前RC固定镜头数据。
9. 尾段addon camera-tail-sampling-20261028已编译：07CFFC4F48993CA50201EF84DBAA9299E5C1FBA9C78B255F4D2E9A6A47C921EC，5136字节，仅flash依赖。r1在AIR创建前被4GiB资源门拦下，可用1,173,630,976B，无PID、无样本；编译成功不等于采样成功。四窗必须落入实际完整战斗区间，至少两窗CPU阳性且总计≥20才可归因，全轮诊断不验收帧率。
10. camera-activity-range-current-20261028已实际编译：载体D90F01DF6FE2C9777AD19C50A9A941634D4FFFA9F18DB5BAF2680F14EA947189、探针5019EC84CBD4467BAE9C7AF8B5555C4A28CFB09AE2895BD2792A77C8400B703A，builds/r1/build.json。独立离线2GiB/1GiB预检、512MiB堆/180秒/512MiB运行线，最低提交1.55GB，双exit0。manifest5EAA844B，保留CS0.9.1天角兽与Activity保护，仅收窄未参战远处预激活区，不改永久参战锁。尚未AIR；B应用/oldNearOnlySleeping阳性、恢复、观察成本待验。后验仅到Stage -1000，不能保证其后所有显示广播无再写。FA2B及当前参照均不覆盖自然纵移/长探索/RV开启；没有新性能部署。
11. 资源观察曾等到连续三次5GiB以上、末次8.78GB无AIR，但登记往返后tail-r2又在创建前以3,974,184,960B失败，无PID/样本。新有界等待入口准备把资源确认和一次调用连接，不降低AIR保护、不无限重试。

## 5. 累积活动线索与停止路线

NativeSceneActivity的engaged永久锁尚未被针对性证伪。旧range第13窗awake43→85，后续83–87，总单位167；末态近处43、远处仍有目标22、历史标志/宽限/弹体混合14。不能把14全归旧锁。activity-release实际released=0、engagedMayRest=0，没有目标路径阳性。
调度自身约0.54–0.63ms不能代表另约4.05–5.12ms的单位step。awake可能含离链单位，须先统计链内存活、保活原因位集、实际step次数/耗时；本轮没有改变休眠资格。

已停止的具体呈现方案不换名重做：farparking确实管理Box1202/Bonus125个vis/shad显示根，不是Box对象数或仅睡眠敌人；range每个候选帧至少711个Box根已移出显示父层，整帧仅约2.15%且四对反向。range的frameChanges=0是未更新默认字段，不是时间线不变证据；严格静态Box普查603经资格筛选剩0，未到屏外判断。内景合图4.37%且横向反退；RV后继约1.59%；视口条带、透明裁剪、GPU地形、wholeworld缓存等详见历史快照。暂停角色缓存不是动态渲染全部无效的证明。lighting2旧热点已由80CF解决，decal准备只约0.06ms而绘图约3ms，旧图章/副本路线已停止。
A796/4E5F实际sceneTick无每帧setZoom，不能用陈旧Grafon/Camera源码整包覆盖。
曾被拒的Monstrik、合并Weapon/UnitVisual+截图、UnitPlayer/SceneObjectCulling组合、Pt+PNG枚举、tag93遥测补丁、CIM CPU查询不转路重试；本轮更细FA2B DoABC类标签枚举亦被保护拒绝并停止。未请求新授权，兼容结论仅用其他已允许来源。

## 6. 下一步

当前RC2普通/大场景参照已完成；下一步尾段tail采样或activity-range同局候选仍待实测，先核资源与冻结输入，再核窗口覆盖/阳性/恢复，不能只优化相机或微小分配。资源适配只改离线编译自身占用，不降低AIR的4GiB/2GiB启动及512MiB运行保护；不把无PID失败算采样进展。
paired诊断宿主已建成，不再重跑FFDec或改已构建输入。当前通过--host-root指向binary目录；probe尚未编译，使用原生1921计划/1920捕获/零额外calc，150×20双环境断言和20位图/恢复待运行。该宿主绝不能部署。
若缓存没有稳定动态收益，停止性能宣称；当前正式F15旧宿主也不能直接覆盖4E5F。近原版体验、2–5秒全场景加载、完整RV/长探索等仍未全面达到。
不要重复泛泛要求用户释放内存、反复空转等待或自动打断外部实验。当前工具没有goal对象，不沿历史blocked计数自行操作不存在的goal。

## 7. 深入入口

- 本轮详情见camera-live-reassessment-20261028.md；当前参照evidence/camera-dense-reference-rc2-20261028-{normal,scene}-r1/summary.json；tail/build.json、runs；activity-range-current/BUILD-RUN.md；binary/RESULTS.md、audit-proof.json；live/verify_run与paired/RESULTS.md。
- 之前完整快照MEMORY-history-20261028-before-live-reassessment.md保留全部停止路线、源码种子和历史入口；journal顶部按时间接续。
- 原生单次镜头旧证据camera-native-once-20261028：base-r1 AIR24656、cache-r1 AIR70412已退出；2F7B探针、冻结源9b56efbf、pair-review A5471DA2，所有原始输入冻结。
- 85源种子camera-atlas-paged-combat-20261025-r1/probe-build.json SHA983727AE；F15旧候选F15B8CE8与428字节算法来源仍保留，不部署。
- Python C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe；Java D:/Program Files/Adobe Animate 2024/jre/bin/java.exe；Flex/SWC/FFDec在mods/Sandevistan/build/tools，只读依赖。
