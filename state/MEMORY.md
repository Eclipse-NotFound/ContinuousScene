# ContinuousScene — 当前快照

## 1. 模组与当前任务

全图碰撞、敌人、物品预生成，画面按视野准备，镜头与弹体连续跨房；远处未参战敌人可暂缓。当前CS0.9.2另含单地图编辑、天角兽局部报警/接力概率及SATS按视野截图，原版连续模式由设置开关控制。

性能任务仍未完成。用户最新明确优先镜头移动，并补充V开启SATS延迟；此前也报告固定镜头偶发卡、活动敌人/弹体严重卡。SATS已通过产品检查并部署，镜头问题仍未解决。目标是接近原版的实际动态游玩，不能用暂停世界、静止无敌对对象或删敌人的数字冒充。历史goal的blocked状态不代表当前工具状态：2026-10-28 12:40 get_goal实际返回null，本轮没有创建/更新goal。

此前用户报告马哈顿废墟载入 `Unit.run #1010 / Error unit 鼹鼠`。已完成两侧边缘确定性复现、四处列读取守护、六次普通/连续进入和144正常运动状态一致，修复先部署B84F、现保留于A80。详见 unit-prestep-boundary-20261028.md。

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

天角兽任务2e828d8及B84F原生单位预跑边界修复保留。22:55已从B84F/CS0.9.1升级到A80ED32B/CS0.9.2：仅接入通过验证的SATS视野截图与释放修复，没有部署镜头性能候选。RC此前F14A44E7属于历史，本次部署回执锁定并保留负责人已更新的EB6D11E6，不将该变化归于本任务。

| 文件 | SHA256 |
|---|---|
| 根pfe.swf | A80ED32BEE50C612CB46EA1E581C8CA9C81072E0B9E6EE1A51E5BACEFBDCBA19 |
| CS0.9.2 | 380DEC3068938B3E3BA1F2C8DB25A6B3D5FC229E8526E8FC03CA23795961E111 |
| TDFC | 7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5 |
| ModLoader2.5 | 2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2 |
| RV | 638E2D408E2CF46683C41114F75773829A1B4417D74BFFE9D08855A4FE343710 |
| RC | EB6D11E6F20068F76D44D180BC5F579C14BA359CAA46E4706D0506B0D4ABC127 |

LAD8ADB/WB1411保持；用户配置和其他模组未改。最新回执state/sats-visible-deployment-20261028.json，installed及最终回读均true；备份build/backups/sats-visible-20261028-225528-7ef578cb234b保存B84F宿主、9A5E产品、旧ContinuousSceneMod.as。本次同步src/ContinuousSceneMod.as及新增src/SatsVisibleGuard.as，未碰外来测试源码。旧unit-boundary回执/备份（4E5F）及alicorn回执/备份仍留历史；其528输入、31项局部报警检查不是本次性能验收。A796染色/纵向缓冲/遮挡格复用、4E5F天角兽和B84F边界修复全部保留。
共享工具：air_test_process ECE3ED08、test_resources 86D5F280、test_registry E3E43581；资源只设自有子进程normal CPU、memory5、HighQoS，不能改全局或外部进程。

## 4. 本轮实际进展与证据

最新记录：knowledge/experiments/camera-sats-current-20261028.md；此前真实战斗记录camera-live-reassessment-20261028.md及下列历史数字保留。

SATS里程碑：同图原生V顺序ABBAAB，原路径开启842/891/713ms，候选144/235/184ms，截图84/94/95→16/16/16；这是开启耗时，不是整游戏FPS。实际A80/380产品AIR67780退出0，336断言、7次V、视觉全关/全开14像素用例零差异、同Grafon/Location重建28旧副本全部释放，普通模式回退及目标/AP恢复通过。四个宿主方法窄改，其余原始方法/tag保留。初版F64检查器跨域取类1065（1断言、0V）的失败保留；后继只增加统计观察入口，未把失败改称通过。门禁/部署均已回读，无需重跑全矩阵。

镜头停点：旧纯镜头静26.256/横31.183/纵31.822ms（各360间隔）无新增绘制，但后查路线在setZoom同回调读取旧Camera坐标，中心961/2880而玩家1441.8/4320；旧scale未存不能倒填，不能当正确玩家路线验收。keycache v2与已等自然帧修正坐标的v3均六轮预热不收敛、0计时间隔，原因待分析，不宣称收益。自有宽窗口鼠标检查虽消息入队，但原生Stage坐标/世界子节点命中未达到阳性，0样本；不排除热点，也不换路径重试。

新增载入故障里程碑：unit-prestep-boundary-20261028.md。当前宿主Unit.run(method1159)四处垂直列读取在横向墙体修正后可能列越界，受控原生molerat左右边界都复现1010；只加列存在判断，保留1719原指令、其他方法/loader/资源，host-audit46F4BE99。base-r2 AIR83976预期异常通过；fixed-r1 AIR51056边界恢复+马哈顿stage4 seed4077752896普通/连续各3次通过。normal-regression-v2 base/fixed AIR80632/48636各153断言、12动作×12帧严格一致。均已退出；有玩家AIR并行，所有回执明确非性能证据。boundary base-r1未启动，normal-regression v1读取protected shX1导致探针1069，失败原件保留。build/generated/unit-prestep-boundary-20261028/{build_host.py,verify.py,deploy.py,verification.json}为本次可核对入口。已按相同依赖同一产物部署并回读，无需重跑整套矩阵。

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
11. 资源观察曾等到连续三次5GiB以上、末次8.78GB无AIR，但登记往返后tail-r2又在创建前以3,974,184,960B失败，无PID/样本。新camera-benchmark-wait入口22377B33已实际等180.016秒、36次检查，tail-r3等待回执notReady/未调用子runner：最高2,594,689,024B、最后2,083,602,432B。没有降低AIR保护或无限重试，全部自有进程退出。下次tail用新r4名称（r3等待回执保留）；range-r1尚未尝试。

## 5. 累积活动线索与停止路线

NativeSceneActivity的engaged永久锁尚未被针对性证伪。旧range第13窗awake43→85，后续83–87，总单位167；末态近处43、远处仍有目标22、历史标志/宽限/弹体混合14。不能把14全归旧锁。activity-release实际released=0、engagedMayRest=0，没有目标路径阳性。
调度自身约0.54–0.63ms不能代表另约4.05–5.12ms的单位step。awake可能含离链单位，须先统计链内存活、保活原因位集、实际step次数/耗时；本轮没有改变休眠资格。

已停止的具体呈现方案不换名重做：farparking确实管理Box1202/Bonus125个vis/shad显示根，不是Box对象数或仅睡眠敌人；range每个候选帧至少711个Box根已移出显示父层，整帧仅约2.15%且四对反向。range的frameChanges=0是未更新默认字段，不是时间线不变证据；严格静态Box普查603经资格筛选剩0，未到屏外判断。内景合图4.37%且横向反退；RV后继约1.59%；视口条带、透明裁剪、GPU地形、wholeworld缓存等详见历史快照。暂停角色缓存不是动态渲染全部无效的证明。lighting2旧热点已由80CF解决，decal准备只约0.06ms而绘图约3ms，旧图章/副本路线已停止。
A796/4E5F实际sceneTick无每帧setZoom，不能用陈旧Grafon/Camera源码整包覆盖。
曾被拒的Monstrik、合并Weapon/UnitVisual+截图、UnitPlayer/SceneObjectCulling组合、Pt+PNG枚举、tag93遥测补丁、CIM CPU查询不转路重试；本轮更细FA2B DoABC类标签枚举亦被保护拒绝并停止。未请求新授权，兼容结论仅用其他已允许来源。

## 6. 下一步

SATS和马哈顿载入修复已交付；后续镜头性能测量必须保留当前A80ED32B/380DEC30及既有边界/天角兽改动，不能用钉B84F、4E5F或A796的冻结诊断宿主覆盖。先分析keycache预热不收敛，在正常原生帧更新缩放后建立正确路线，取得有效窗口再比较；不能把预热失败或旧路线数字当优化结论。旧性能结果保留原始指纹，旧tail/activity-range也仅是待验路线，不自动成为新优先任务。

按用户要求以镜头移动为核心，同时保持正常世界运行；最终需覆盖实际窗口、自然纵移/长探索及必要视觉组合。本轮资源曾恢复，不沿旧“内存不足”结论空等；登记协调其他agent，玩家并行仅允许功能判断。资源适配只改离线编译自身占用，不降低AIR的4GiB/2GiB启动及512MiB运行保护；不把无PID或0样本失败算性能进展。
paired诊断宿主已建成，不再重跑FFDec或改已构建输入。当前通过--host-root指向binary目录；probe尚未编译，使用原生1921计划/1920捕获/零额外calc，150×20双环境断言和20位图/恢复待运行。该宿主绝不能部署。
若缓存没有稳定动态收益，停止性能宣称；F15等旧宿主不能直接覆盖当前A80。近原版体验、2–5秒全场景加载、完整RV/长探索等仍未全面达到。
不要重复泛泛要求用户释放内存、反复空转等待或自动打断外部实验。当前工具没有goal对象，不沿历史blocked计数自行操作不存在的goal。

## 7. 深入入口

- 最新镜头/SATS：camera-sats-current-20261028.md；evidence/sats-visible-product-checks-v3-20261028-r1；build/generated/sats-visible-release-20261028/{verification.json,host-audit.json,product-build.json}；state/sats-visible-deployment-20261028.json。keycache v2/v3失败目录与鼠标RESULTS保持原件。
- 本轮详情见camera-live-reassessment-20261028.md；当前参照evidence/camera-dense-reference-rc2-20261028-{normal,scene}-r1/summary.json；tail/build.json、runs；activity-range-current/BUILD-RUN.md；binary/RESULTS.md、audit-proof.json；live/verify_run与paired/RESULTS.md。
- 之前完整快照MEMORY-history-20261028-before-live-reassessment.md保留全部停止路线、源码种子和历史入口；journal顶部按时间接续。
- 原生单次镜头旧证据camera-native-once-20261028：base-r1 AIR24656、cache-r1 AIR70412已退出；2F7B探针、冻结源9b56efbf、pair-review A5471DA2，所有原始输入冻结。
- 85源种子camera-atlas-paged-combat-20261025-r1/probe-build.json SHA983727AE；F15旧候选F15B8CE8与428字节算法来源仍保留，不部署。
- Python C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe；Java D:/Program Files/Adobe Animate 2024/jre/bin/java.exe；Flex/SWC/FFDec在mods/Sandevistan/build/tools，只读依赖。
