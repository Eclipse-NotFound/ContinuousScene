# ContinuousScene — 当前快照

## 1. 模组与当前任务

全图碰撞、敌人、物品预生成，画面按视野准备，镜头与弹体连续跨房；远处未参战敌人可暂缓。当前CS0.9.3另含单地图编辑、天角兽局部报警/接力概率、SATS按视野截图及有条件的地形呈现复用，原版连续模式由设置开关控制。

性能任务仍未完成。用户明确优先镜头移动，并补充V开启SATS延迟；入口为普通游戏／模组启动器。SATS已修复部署；2026-10-29 02:58又部署有限镜头优化，真实产品横移约11.7%、纵移约9.7%、原生移动交战约6%平均间隔改善，但长停顿仍有，不宣称近原版或完整解决。不能用暂停世界、删敌或探针局部helper数字冒充真实产品收益。当前没有goal对象。

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

天角兽任务2e828d8、A796染色/纵向缓冲、B84F预跑边界和180d46f的SATS修复均保留。2026-10-29 02:58:52已安装CS0.9.3及WB0.5.10-scene；根宿主A80、DLC、配置和其它模组不变，RC239252DF仍归负责人。新回执state/camera-presentation-deployment-20261029.json为installed/readback通过；备份build/backups/camera-presentation-20261029-025849-fe3f35922315。旧SATS回执描述旧380产品，不能当当前正式产品。

| 文件 | SHA256 |
|---|---|
| 根pfe.swf | A80ED32BEE50C612CB46EA1E581C8CA9C81072E0B9E6EE1A51E5BACEFBDCBA19 |
| CS0.9.3 | D8A68A4C128E196FD69B50D1CC7F0FFA72669751FB2FCB85D629F30FE622E677 |
| WB0.5.10-scene | FE3E7A84753F6F3614440F69F8725E6E8639AEE4755ACF878AAFCFEDB95AC2E6 |
| TDFC | 7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5 |
| ModLoader2.5 | 2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2 |
| RV | 638E2D408E2CF46683C41114F75773829A1B4417D74BFFE9D08855A4FE343710 |
| RC（10月29日最新测试冻结输入；非本任务部署） | 239252DF5EA24EC6DA5005BD80BFEB31A91E393D6B2BFE7B1FD7B371CD4E618C |

最新安装只同步CS四源（入口/SATS清理钩子及新增SceneEventBitmapFill、ScenePresentationCoordinator）和CS/WB两份产物。WB沿准确13源生产配方，仅增加启用前同步恢复钩子；其HEAD仍不是完整生产源，不直接构建覆盖。准确源位于build/generated/camera-event-fill-product-20261029/{frozen-product-src,wallblend/frozen-product-src}。旧0.9.2/0.5.9为380/141，备份保留。LAD8ADB及其它配置未改，外来SceneRenderChecks.as未碰。
共享工具：air_test_process ECE3ED08、test_resources 86D5F280、test_registry E3E43581；资源只设自有子进程normal CPU、memory5、HighQoS，不能改全局或外部进程。

## 4. 本轮实际进展与证据

最新记录：knowledge/experiments/camera-sats-current-20261028.md；此前真实战斗记录camera-live-reassessment-20261028.md及下列历史数字保留。

**真实产品部署证据（2026-10-29）：**
- product-live-r1（AIR90840/225D32EC）：1200完整间隔、26断言，600候选全部呈现；A同产品disabled平均54.2817→B51.05ms（5.95%），P9569→65，但最大164→170、>100ms 2→4。A/B敌射711/856、冲刺283/200、awake45.36/44.303，负载不等同，不称纯因果百分比；玩家、六敌人及平台身体框全程在视口。
- product-camera-r1（AIR71820/54E5DA8）：2160完整间隔、28断言，静23.3→21.7278、横34.7222→30.675、纵33.6528→30.3778ms；P9533→31/45→39/41→35。静/纵>50ms 1→3/3→4仍保留。五视角像素全0，原生30/测试120fps，预热42.422秒不是载入验收。玩家481.8/4320、中心1216/4320，全2161逻辑点在视口，无逐帧身体框或自然跳跃证据。
- product-checks-v3-r1（AIR21012/B60366A7）：1213断言、7次原生V、14SATS像素用例通过；产品同状态像素0。V180/225/293ms为不同大图条件，不能混作同场A/B。RV/LAD自然帧回退、WB同步恢复、同Grafon清理、普通房间回退均通过，48节点/2348alpha平衡。真实窗口0.5/0.8缩放明确zoom-or-shake，恢复原窗后自然启用。

呈现仅在native320、scale1、无震屏、RV enabled/wallbright、WB、LAD全关闭且注册表可识别时启用；否则原生回退。效果开启只验证兼容回退，不声称性能改善。SATS开前、场景清理及WB同步启用前先恢复原位图；借用原生像素、不拥有副本，纯像素revision复用Graphics命令，结构变化仍重建。helper9D8F3A6F，coordinator C98FC0E2。

功能失败保留：checks-r1是原生resize打开pip使allStat2，等待120帧失败；v2误读PipBuck内部vis/page且finish再次抛1069，没有result。AIR88440凭登记/创建时间/父进程/唯一appID精确结束，原runner清理并记录failed。v3改用公开World.vpip及PipBuck.active/currentPage，三次都观察新菜单后只调用一次原生onoff(-1)，下一自然帧allStat1；不直接写暂停标志，不把world-inactive冒作缩放阳性。

额外product-memory-r1（1325E7BF/AIR88968）1200/26通过，仅诊断：三getter合计读取均19.2875ms、最少15ms，明显扰动，不能用于性能验收或把增加的长帧归于产品。全部内存下降和长帧已保留，尚无调用栈证明GC。旧完整live六长帧中四次在nativeBand、两次主要在Stage之外；各窗totalScript不能直接按本窗序号配nativeBand，需展开299+300+300+300对应全局0..1198。

上述证据在knowledge/experiments/evidence/camera-event-fill-<相应后缀>-20261029-r1，产品/门禁在build/generated/camera-event-fill-product-20261029。**旧verify_products及runner锁安装前380/141，现在会正确拒绝；新试验须显式按新部署回执定基线，不能放宽旧断言或覆盖旧证据。** 下述v1/v2及其它旧试验为历史，不表示当前仍未部署。

历史首轮动态结果（2026-10-29，后继产品见上文）：camera-event-fill-live-20261029-r1，A80/380、实际RC239252DF、探针C8025771，AIR41048；1200完整原生跟随/六LMG+ASSR冲刺间隔与26断言通过，玩家/六敌人身体框全程在视口，600候选帧全部启用。原均50.503→49.948ms仅1.10%，P95 63→64、最大149→157；两对1.88%/0.30%，不满足明显提速、不部署。玩家开火各200、敌人794/875、敌弹均4.715/5.802、冲刺111/92帧，保留自然负载差异。helper均0.422ms/最大9，revision592/commands254，最终清理通过；无其他AIR，最低提交9,307,856,896B。原目标未完成。

此前同图纯镜头event-bitmap-fill-r1横15.34%/纵7.92%正收益、五视角像素零差异，仅证明邻近地形呈现；玩家逻辑点静/横全在画外底边80px、纵仅128/720在内，无bodybounds，撤回“宽视口路线玩家始终可见”表述。不得用其11.80%移动合计替代上述真实战斗1.10%。两份RESULTS及旧驱动/回执冻结。

像素复用v2组件：pixel-checks旧r1因原生选点changed=0失败，0计时/原件保留；v3保留helper9D8F、原生有界选点首次成功，屏幕912/516的16×16两色各256像素变化，prime后同一命令连续更新，候选RGB0/alpha0、恢复精确。AIR6496退出0，419组件/15外层断言，7fallback、树事件、55图释放均通过，raw ADA61CFF/review E8ADD640；仅同步BitmapData.draw语义，非自然Stage或性能证明。

v2 live-r1已完成：AIR39012退出0、3B9444CB、1200间隔/26断言独立核验。A53.767→B49.130ms表面8.62%，P95 68→66/max192→150，但>100ms 2→4；敌方1038/775、敌弹6.672/4.633、冲刺129/86，不能归因成纯收益。600候选全启用，helper0.205ms/rebuild36/pixelOnly530/201帧，清理通过，最低提交9,208,688,640B，无其他AIR。后继BAAB独立复核报告记录54.050→50.265ms（7.00%），候选弹量/冲刺较多但醒着单位较少，六预定分箱均正向；结合两顺序支持有限收益，仍不声称精确因果百分比或近原版。见pixel-live-baab/RESULTS.md。当时进入产品生命周期/兼容候选准备；后继产品现已部署，见本节顶部。

节点缓存独立路线已停止：node-cache-camera-r1，AIR67216、44CAE0F1，2160完整间隔/28断言；横34.761→32.722、纵32.686→30.861ms约5.9%/5.6%，静20.081→21.547退7.3%；横纵P95变差、>50ms分别3→11/3→9。五图RGB≤1/alpha0，清理通过；本轮玩家1441.8/4320，2160逻辑投影全在内（未逐帧身体框），不能套旧画外结论。77驻留/预绘计数稳定，但lastDirtyCount有2→0→2；暖图50.834秒非载入验收。旧live-r1因883帧平台超界5px失败不排名，不缩路线重试、不测combo，不与v2纯像素复用混同。完整结果见node-cache-camera/RESULTS.md。

SATS里程碑：同图原生V顺序ABBAAB，原路径开启842/891/713ms，候选144/235/184ms，截图84/94/95→16/16/16；这是开启耗时，不是整游戏FPS。实际A80/380产品AIR67780退出0，336断言、7次V、视觉全关/全开14像素用例零差异、同Grafon/Location重建28旧副本全部释放，普通模式回退及目标/AP恢复通过。四个宿主方法窄改，其余原始方法/tag保留。初版F64检查器跨域取类1065（1断言、0V）的失败保留；后继只增加统计观察入口，未把失败改称通过。门禁/部署均已回读，无需重跑全矩阵。

镜头历史限制：旧纯镜头静26.256/横31.183/纵31.822ms（各360间隔）无新增绘制，但路线在setZoom同回调读取旧Camera坐标，中心961/2880而玩家1441.8/4320；旧scale未存不能倒填，不能当正确玩家路线验收。keycache v2/v3均六轮预热失败、0计时间隔，不能宣称缓存收益。自有宽窗口鼠标检查未达到原生Stage坐标/世界子节点命中阳性，0样本，不排除热点、不换路径重试。

尾段有效证据：camera-nearplayer-tail-20261028-r3，正式A80/380+RC EB6，AIR83080退出0，2160完整区间/18断言/12CPU尾段窗独立核验通过。缩放后等自然帧，中心840/4320经范围夹取仍含玩家481.8/4320；六轮准备44.371秒后计时图块warm/draw零增长，dirtyCount变化2，不是所有绘图零工作。静/横/纵21.972/29.593/29.126ms，Stage7.047/7.129/7.388ms，仅诊断。CPU样本26/50/53，移动增量主要为原生pre-render/render，不能换算GPU耗时。RC单人UI/refresh少量栈已依既有授权发负责人协调，未断言主因。r1/r2启动前占用失败0PID；r3持登记等待3次空闲检查2.078秒成功，无其他AIR，最低提交10.66GB。

前一定位：camera-nearplayer-layer-split-20261028-r1于10月29日完成，AIR76296、2160区间/22断言、独立review有效。2032×1084，A完整/B暂隐4地形/C暂隐6对象按ABCCBA；静/横/纵A20.096/32.896/36.908ms，B22.958/28.117/27.042，C16.208/25.133/26.013。地形与对象都涉及移动呈现开销，但隐藏画面只作归因，不能称优化收益，条件差不可相加。10层2161次状态检查与最终恢复通过、计时无图块warm/draw增长，保留17边界/4条件切换及110ms长帧；无其他AIR、最低提交9.75GB。其后事件驱动候选与已安装产品的实际结果见本节开头。

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
SATS整数格批量draw再copyPixels已由旧33C1实测否定：7组像素失败，RGB最大3/alpha2；本轮只读复核，未重新生成/运行。当前全源可见性不同仍不足证明会消除旧误差，保留A80/380逐格方案。
曾被拒的Monstrik、合并Weapon/UnitVisual+截图、UnitPlayer/SceneObjectCulling组合、Pt+PNG枚举、tag93遥测补丁、CIM CPU查询不转路重试；本轮更细FA2B DoABC类标签枚举亦被保护拒绝并停止。未请求新授权，兼容结论仅用其他已允许来源。

## 6. 下一步

SATS、马哈顿载入修复及有限镜头优化已交付；接续必须按A80/D8A/FE3新基线，不覆盖既有边界/天角兽改动。未解决的是实际长停顿、自然纵移/长探索、效果开启下的性能。若继续内存方向，先分别测getter成本，不能再把已证均19ms的三getter放每帧；内存下降不独自证明GC，应由相同长帧中的有界调用栈确认。透明Box阴影只读census配方仍未运行，不误认已有阳性。node-cache路线已停止，不再缩路线重试或做combo；隐藏图层不是产品方案，不把归因数字当收益。

按用户要求以镜头移动为核心，同时保持正常世界运行；最终需覆盖实际窗口、自然纵移/长探索及必要视觉组合。本轮资源曾恢复，不沿旧“内存不足”结论空等；登记协调其他agent，玩家并行仅允许功能判断。资源适配只改离线编译自身占用，不降低AIR的4GiB/2GiB启动及512MiB运行保护；不把无PID或0样本失败算性能进展。
paired诊断宿主已建成，不再重跑FFDec或改已构建输入。当前通过--host-root指向binary目录；probe尚未编译，使用原生1921计划/1920捕获/零额外calc，150×20双环境断言和20位图/恢复待运行。该宿主绝不能部署。
若缓存没有稳定动态收益，停止性能宣称；F15等旧宿主不能直接覆盖当前A80。近原版体验、2–5秒全场景加载、完整RV/长探索等仍未全面达到。
不要重复泛泛要求用户释放内存、反复空转等待或自动打断外部实验。当前工具没有goal对象，不沿历史blocked计数自行操作不存在的goal。

## 7. 深入入口

- 最新镜头/SATS：camera-sats-current-20261028.md；evidence/camera-nearplayer-layer-split-20261028-r1/{camera-layer-review.json,storage/result.json,process-policy.json}；evidence/camera-nearplayer-tail-20261028-r3/{camera-tail-review.json,camera-nearplayer-tail-inputs.json,camera-air-wait-result.json}；evidence/sats-visible-product-checks-v3-20261028-r1；build/generated/sats-visible-release-20261028/{verification.json,host-audit.json,product-build.json}；state/sats-visible-deployment-20261028.json。keycache v2/v3失败目录与鼠标RESULTS保持原件。
- 当前event-fill：state/camera-presentation-deployment-20261029.json；build/generated/camera-event-fill-product-20261029/{verification.json,verify_deploy.py,product-build.json}；evidence/camera-event-fill-product-{live,camera,checks-v3,memory}-20261029-r1/RESULTS.md。前3项是本次产品证据，memory仅观察且高开销。v1/v2实验和反序结果仍在旧目录，不能取代当前产品结果。
- 停止node-cache：build/generated/camera-event-fill-node-cache-camera-20261029/RESULTS.md及同名evidence后缀-r1；失败live见camera-event-fill-node-cache-20261029/RESULTS.md。不与9D8F纯像素复用混同。
- v2像素组件：build/generated/camera-event-fill-pixel-checks-v3-20261029/RESULTS.md及同名evidence后缀-r1；旧pixel-checks-r1失败原件保留。组件通过不等于动态收益。
- 本轮详情见camera-live-reassessment-20261028.md；当前参照evidence/camera-dense-reference-rc2-20261028-{normal,scene}-r1/summary.json；tail/build.json、runs；activity-range-current/BUILD-RUN.md；binary/RESULTS.md、audit-proof.json；live/verify_run与paired/RESULTS.md。
- 之前完整快照MEMORY-history-20261028-before-live-reassessment.md保留全部停止路线、源码种子和历史入口；journal顶部按时间接续。
- 原生单次镜头旧证据camera-native-once-20261028：base-r1 AIR24656、cache-r1 AIR70412已退出；2F7B探针、冻结源9b56efbf、pair-review A5471DA2，所有原始输入冻结。
- 85源种子camera-atlas-paged-combat-20261025-r1/probe-build.json SHA983727AE；F15旧候选F15B8CE8与428字节算法来源仍保留，不部署。
- Python C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe；Java D:/Program Files/Adobe Animate 2024/jre/bin/java.exe；Flex/SWC/FFDec在mods/Sandevistan/build/tools，只读依赖。
