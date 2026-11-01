# ContinuousScene — 当前快照

<!-- quality-and-dense-20261101 -->
> 2026-11-01 画质取舍及多敌人续查结束：**本轮无新部署、性能目标未达成**。正式根宿主仍9D8662F6，CS D8A、WB FE3、RV AEA、RC6906等14模组及application.xml保持。全部自有测试结束。
>
> 用户接受同时尝试移动时变软/减少边缘平滑，补充多敌人也卡顿。本轮11次实际AIR运行：7次运行检查完成、4次失败/争用终止；另一次编译排队超时未启动。完成的非采样时序共19860区间，其中16638玩家保持在屏内。v21–23玩家invulner导致敌人不选中它，只有移动实体、不能称交战；v24有开火但玩家被击退出屏，不满足画面内交战资格。v27/28视口检查正确拦下。v29/30改在预绘之后生成六敌、测试玩家fixed；所有测量帧≥3可见敌人、六敌存活、逐窗真实出膛，明确不含玩家运动物理验收。
>
> 停止路线：全景逐帧低分辨率/低抗锯齿合成显著更慢；地形0.5/0.75缓存无稳定收益；原生MEDIUM无稳定改善，LOW少量变化伴阴影损失；每帧切换质量更慢；请求GPU模式未见可采用收益。v30隔2/3帧半分辨率重画+镜头平移缓存中，3帧档横移66.927→65.399ms仅约2.3%，>100ms长帧14→26且动画滞后；不部署。别重复仅挑均值/快窗或把诊断上限120fps当正式30fps验收。
>
> 新能力更正：桌面AIR不是绝对不支持LOW/MEDIUM；隔离描述符allowLowQuality=true可解锁，正式描述符未改。共享事实desktop-stage-quality-limit已更正。v29合格交火12/12 CPU/分配采样中1157 CPU记录有359条GC上下文，不能将GC触发处全归因AI；采样本身增压且有18片新预绘。快照复用/区域键/炮塔guard已有负结果，不能凭栈再次直接采用。
>
> 完整限制、负结果及画面对照见[本轮报告](../knowledge/experiments/quality-and-dense-enemies-20261101.md)；冻结清单/汇总在build/generated/quality-evaluation-20261101。后续需要新的完整帧收益证据；尚不能准确分摊多敌人中的原生呈现、AI与回收净成本，不声称耗尽所有优化空间。他人源码/状态/13份报告保留。
<!-- /quality-and-dense-20261101 -->


<!-- lossless-cut-survey-20261101 -->
> 2026-11-01 无损切口普查：本轮正式文件未变，宿主仍 **9D8662F6**、CS D8A、WB FE3、RV AEA、RC6906等14模组保持；前轮显隐回归修复仍在。完成10次隔离游戏运行，含1次保留的预热超时，计时共29892有效间隔；另有一次排队超时未启动。所有自有实例/登记已结束。
>
> 已核对地形、物体显示树/缓存、时间轴/焦点、环境查询、AI快照与调度、其它模组分配、GC和运行库。快照复用、不同中性分组及缓存、主动GC和新版运行库未取得可部署的稳定明显收益；没有新性能产物进入正式安装。各自像素/时序边界与失败见[普查报告](../knowledge/experiments/lossless-cut-survey-20261101.md)及build/generated/lossless-cut-survey-20261101/summary.json。
>
> 保持原画质、原生隐藏、追击和屏外命中。普通Box本已cacheAsBitmap；桌面cacheAsBitmapMatrix不支持，不能重复包装成新切口。120fps容量/离屏像素不能冒充正式30fps/原生Stage验收。不声称已接近原版或数学意义耗尽所有无损空间；新渲染实现仍需新的整帧收益和等价证据，不能仅换参数重跑已否定实现。他人状态/源码/报告保留。
<!-- /lossless-cut-survey-20261101 -->


<!-- camera-optimization-20261101 -->
> 2026-11-01 后继优化已实测：正式宿主 **9D8662F6**（14:58从CA94只撤掉sceneTick无条件单位显隐，前三层A2/预绘预算保留）；CS **D8A68A4C**、WB **FE3E7A84**、RV **AEA30314**、RC **69060487**等14模组组合保持。回执：build/generated/camera-object-clip-v7-20261101/visibility-fix-deployment.json。原生UnitSpectre隐藏复验通过。这是显隐回归修复，不是已证实性能提升；重启生效。下方旧安装表与迭代条目是历史记录，当前以本段为准。
>
> 9次独立游戏运行，7次时序实验15740个有效间隔；所有自有实例/登记已结束。整层裁剪、物体缓存、炮塔guard、既有地形节点缓存均无稳定收益。旧局部phase在真实0.658333缩放alpha失败；禁止凭旧2/3测试放行。屏幕像素缓存v13两窗十图合格，但小窗28.018→27.202ms仅约2.9%且长停顿更多，大窗35.190→39.166ms更慢，停止、不部署。没有新性能候选进入正式文件。炮塔goto栈可能执行全局帧脚本，不等于炮塔重建；90帧片段与GC周期错位不能当P99收益。
>
> 远处活动范围旧候选缺少内部警戒/延后攻击保护，未运行或部署；保持追击和屏外命中。性能目标尚未达到近原版。详见 [本轮报告](../knowledge/experiments/camera-optimization-followup-20261101.md) 及 generated/camera-optimization-review-20261101/summary.json。后续不重复上述已停止路线；需要新的整帧成本证据，而不是扩大预绘预算或放宽画面要求。他人的SceneRenderChecks、既有状态和13份报告保持。
<!-- /camera-optimization-20261101 -->


> 2026-11-01 当前迭代审核：正式仍 CA94/D8A/FE3，RV实际为AEA30314；本轮未覆盖任何正式产物。新增单位显隐在原版UnitSpectre上复现 false→true，A80阴性对照保持false，第四层不能判“零视觉影响”。4轮12684间隔：补绘稳定后横纵移动仍增加呈现成本；大窗物体层隐藏4/4变快，光照层无稳定收益；35次>100ms中32次伴随明显堆回落。12/12分配采样又指向炮塔gotoAndStop/构造子显示对象/FocusManager链及TDFC快照。旧“纯镜头基本无成本、主要是战斗”的排他结论不再沿用。详见 [迭代审查](../knowledge/experiments/camera-iteration-review-20261101.md)。调查未等于修复：优先安全撤掉无条件显隐，再验证物体呈现、缩放地形和回收尾部；不直接复活旧质量/sleep/炮塔候选。所有本轮自有实例和登记已结束；他人 SceneRenderChecks、MEMORY/journal原修改与报告均保留。


## 1. 模组与当前任务

全图碰撞、敌人、物品预生成，画面按视野准备，镜头与弹体连续跨房；远处未参战敌人可暂缓。当前CS0.9.3另含单地图编辑、天角兽局部报警/接力概率、SATS按视野截图及有条件的地形呈现复用，原版连续模式由设置开关控制。

性能任务仍未完成。用户明确优先镜头移动，并补充V开启SATS延迟；入口为普通游戏／模组启动器。SATS已修复部署；2026-10-29 02:58又部署有限镜头优化，真实产品横移约11.7%、纵移约9.7%、原生移动交战约6%平均间隔改善，但长停顿仍有，不宣称近原版或完整解决。不能用暂停世界、删敌或探针局部helper数字冒充真实产品收益。当前没有goal对象。

此前用户报告马哈顿废墟载入 `Unit.run #1010 / Error unit 鼹鼠`。已完成两侧边缘确定性复现、四处列读取守护、六次普通/连续进入和144正常运动状态一致，修复先部署B84F、现保留于A80。详见 unit-prestep-boundary-20261028.md。

## 2. 约定与权限

- 中文简洁进度；性能会话01a13816-367b-7261-8e11-ca9152565dd9。已允许实测；通过相应门禁后可本机部署，不重复确认。
- 已允许必要RV、WallBlend、LAD、TDFC、RConnect兼容。RC由负责人01a086bb-378c-7f60-b8e1-50d90ffa0996集中部署，本会话不并行覆盖。
- 已允许修复ModLoader共享测试登记器；2026-10-29又明确优先修复原启动器和多会话测试路径，已完成并部署。其他跨模组写入不自动扩大。
- 接受视野预绘、远处未参战敌人暂缓、纵向镜头缓冲；保留追击者和飞行弹体。允许RGB最多2/255、alpha不变的实验，仍须真实明显提速与功能正常才部署。
- 当前完整大场景性能测试保持4GiB提交/2GiB物理预检、512MiB运行中止；有界等待采用3次间隔5秒均≥5GiB。此为该夹具保护，不是所有离线操作统一门槛。低内存离线构建独立限制自身512MiB，不改变游戏保护。
- 测试先登记，唯一APP ID/存储、私有桌面，默认静音；不写真实APPDATA/pfe，不停玩家或外部实验，不用Ghost。跨会话协调不能超出用户已授权的具体消息。
- 一次10分钟实验协调已使用，对方无安全自然暂停点，窗口未开始；不重复发送或干预外部进程。当前无自有Java/AIR/等待句柄。
- 已授权按本会话逐条登记≤10分钟精确构建调用授权，不关闭护栏。hooks当前exec映射Bash，载荷command；根functions store有cs_exact_grant_template（上下文丢失时按hooks README重建）。
- 无AGENT_SCOPE；不创建。src/tests/SceneRenderChecks.as是他人WIP，不恢复或提交。2026-10-28另一用户授权任务已取消天角兽旧“仅候选”限制并部署，不能回退其更新。10月21日下午被撤回7D42/5432配方仍不可复活。

## 3. 当前正式安装

天角兽任务2e828d8、A796染色/纵向缓冲、B84F预跑边界和180d46f的SATS修复均保留。2026-10-29 02:58:52已安装CS0.9.3及WB0.5.10-scene；本任务未再改根宿主A80、DLC或配置，RV BD64与RC6906由其它任务更新并保留，RC仍归负责人。新回执state/camera-presentation-deployment-20261029.json为installed/readback通过；备份build/backups/camera-presentation-20261029-025849-fe3f35922315。旧SATS回执描述旧380产品，不能当当前正式产品。

| 文件 | SHA256 |
|---|---|
| 根pfe.swf | A80ED32BEE50C612CB46EA1E581C8CA9C81072E0B9E6EE1A51E5BACEFBDCBA19 |
| CS0.9.3 | D8A68A4C128E196FD69B50D1CC7F0FFA72669751FB2FCB85D629F30FE622E677 |
| WB0.5.10-scene | FE3E7A84753F6F3614440F69F8725E6E8639AEE4755ACF878AAFCFEDB95AC2E6 |
| TDFC | 7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5 |
| ModLoader2.5 | 2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2 |
| RV（其他任务更新） | BD64B5BBFE5A07A0B5BFF38E4C344652E1DF526CFD5C308D63B607123CE4A9AD |
| RC（其他任务更新；非本任务部署） | 690604878BD8707007A99E3AD14F8F5F3F55CDD4948C8DEBE6CC87363AFD38C9 |

最新安装只同步CS四源（入口/SATS清理钩子及新增SceneEventBitmapFill、ScenePresentationCoordinator）和CS/WB两份产物。WB沿准确13源生产配方，仅增加启用前同步恢复钩子；其HEAD仍不是完整生产源，不直接构建覆盖。准确源位于build/generated/camera-event-fill-product-20261029/{frozen-product-src,wallblend/frozen-product-src}。旧0.9.2/0.5.9为380/141，备份保留。LAD8ADB及其它配置未改，外来SceneRenderChecks.as未碰。
共享工具本轮更新：air_test_process 010597B0、launch_integrity 6EEBD3CD、test_registry 8E052672、mod_debugger 86AEAE63；test_resources仍86D5F280。资源只设自有子进程normal CPU、memory5、HighQoS，不能改全局或外部进程。

## 4. 最新接续：启动与测试路径已恢复，三层缩放候选仍待性能验收

用户要求先修复基础设施，已完成：[ModLoader本轮证据](../../ModLoader/knowledge/experiments/startup-test-path-2026-10-29/README.md)。确认根Remains.exe/adl64.exe继承Low标签，普通运行器启动后子进程降至4096；同字节Medium副本通过39项，再修复四个入口标签，文件/DACL不变。原启动器主窗口正常；共享工具以指纹核对方式复用普通标签ADL，保留隔离库/应用ID/存储。68项工具检查、双AIR78项、两个独立CLI真实菜单并行通过，全部自有进程/登记结束。默认功能两组并行，性能`game`仍独占；不需要重做已否定的TEMP/可见窗口尝试。本轮无CS源码或SWF部署，3686890F候选尚未计时。

最新报告`knowledge/experiments/camera-pacing-phase-20261029.md`。A473当前产品30/120真实对照4320完整区间：30纵移汇总41.406→41.064ms，前后方向反转，不是稳定改善；120容量不能当正式30fps体验。局部相位F03/round全四层均2/3五图alpha最大2，已停止。分层切换诊断不能独自充当首次绘制合格。

独立mask7候选37F397BA仅接管Front/Back/Back2，水层原生。FA568367纯首次绘制15图（2/3、.5、1各5）RGBA全精确、创建清理平衡；同布局但自然玩家位置/单位数不同，不跨轮宣称解释旧全部误差。后继A283两轮计时前因出生点贴下边缘无法同时满足±96纵移及玩家屏内而正确失败、0样本。新3686890F平台夹具已编译：只在测前把隔离玩家放到现有净空地板一次，正常站稳45帧，再测完整2160区间；没有地图/敌人修改，不假装全程未移位。尚未执行到AS层，没有性能收益、未集成生产。

此前13:55后AIR在游戏代码前0xC0000142退出；原启动器同时报临时路径访问被拒、日志停在09:16。此前换TEMP与可见样例未恢复的事实留原报告，现已用令牌/标签及同字节恢复实验归因并修复。用户确认Remains.vbs仍可进入游戏，不据此否定入口标签问题；也不能把所有0xC0000142一概归因为此。

用户仅额外允许一次约10秒可见小样例，已使用；该授权不延伸到全图可见测试。后续默认继续私有桌面测试。运行环境已恢复，下一步可测3686890F；不部署仅图像通过的候选。不改外来SceneRenderChecks及camera-light-warm-lead的.dshclaim。下述前轮缩放/屏外结论仍有效。

2026-10-29 后续用户强调横纵镜头与卡顿相关，并要求攻击命中屏幕外和 RV 遮住的敌人。新增 `offscreen-hits-20261029.md`：A80/D8A 不改，两轮真实 Bullet 组件已证实屏外自然休眠敌人能受伤，下次调度唤醒；RV关闭20项、开启21项；实墙/到期阴性通过，其他119/111睡眠者未醒。短弹道在敌人附近生成，不是枪口全射程、光束、爆炸或AI后续动作验收。实际依赖 RV BD64（D56）/RC6906由其它任务更新，收尾仍为该值，不能恢复旧638/239。第三轮屏内RV隐藏候选 AE055F7F 已编译，首次运行启动前低于4GiB保护线失败，无AIR，补查仍约2–3GiB。

轻量 `cell-sampling-mini-20261029-r1` 使用合成400×400图，无游戏载入；18组合、72自有输出释放、原生重复和源不变通过。scale1/.5各6项精确，2/3六项world/local fill均RGB/alpha最大255；**单格局部Sprite锚定不能修复此取样误差，停止该修正，不生产化**。根已查看参照/局部图片；不是游戏Stage/拼缝或性能证据。2GiB/1GiB预检只属此轻量夹具，不放宽完整地图门槛。两次游戏AIR和一次组件AIR全部退出，所有自有登记结束，无后台承诺。本轮仅测试/文档，无部署；镜头仍未解决。

用户要求继续深入优化，并确认大窗口与默认小窗口都明显卡顿。报告`knowledge/experiments/camera-scale-coverage-20261029.md`。正式A80/D8A/FE3回读保持；四次实际AIR及一次启动前失败均结束，无自有进程或等待。

- 1280×720实际进入时isZoom2、scale2/3、原帧率30。当前呈现只支持scale1，旧.5/.8检查仅验证回退；这是适用覆盖缺口，不能解释大窗口卡顿或称唯一主因。
- 缩放v1-r1独立APPDATA权限失败，未启动；r2 AIR79304在暖图玩家投影条件失败，候选updates0；像素专用v2 AIR20740允许镜头离开玩家，但根getter与concat量化差使资格回退。均无像素性能结论，原失败保留。
- v3 AIR44040/56E0E91A实际完成10图：2/3五图RGB146–191、alpha255不合格；.5五图RGBA精确；.8在拼接矩阵资格处停止，未做候选图。独立partial-pixel-review验证原生重复/恢复、实际矩阵及4280次alpha/40节点清理平衡，不把整体失败改通过。根已查看PNG。**停止直接放宽缩放资格**，不继续放宽.8资格，不据.5图像证明性能或部署。
- 完整预绘环memo：当前3259 C5D891D9/1655字节核实；诊断569B3CB5只加可选回调，保留5770方法/1016类/其它tag及逆编辑。全±2环阳性存在证明守字典/对象/尺寸/resident/evictions，无job/退出时原路径。诊断宿主禁止部署。
- upcoming-r1 AIR38148/61ABBEF1：2160完整区间/28断言，168模拟缺格检查；逐2161观察验证A每帧0回调、B每帧1，1080调用=1076命中+4证明，266格读取、0miss。静23.203→22.472、横35.658→32.228、纵31.444→33.339ms；纵慢6.02%。横原路径最后一窗52.011ms/36长帧，保留不删，不作9.62%严格因果提速。**停止memo候选，不生产化**。
- 上轮七次测试、环境键/炮塔/透明阴影等停止结论仍有效，详见camera-motion-20261029.md与本次归档MEMORY-history-20261029-before-scale-coverage.md，不重做。

本轮图像是零计时组件实验，memo是120fps容量实验、玩家可离屏；五张开关图不执行upcoming，168项非真实冷态回归。不能当自然跳跃/30fps节奏/视觉全开或近原版验收。没有改生产src/release/根SWF、配置或真实存档，外来SceneRenderChecks保持。

**已部署里程碑仍有效：**CS0.9.3真实product-camera横约11.7%/纵9.7%、product-live约6%平均差且有自然负载差异；长帧并未消失。1213产品检查、7原生V、14SATS像素用例通过。呈现仅scale1/native320/无震屏且RV enabled/wallbright、WB、LAD全关时启用，否则回原生；开效果只证明回退兼容。SATS早前同图开启842/891/713→144/235/184ms已安装，鼹鼠边缘预跑#1010也已修复。

## 5. 累积活动线索与停止路线

NativeSceneActivity的engaged永久锁尚未被针对性证伪。旧range第13窗awake43→85，后续83–87，总单位167；末态近处43、远处仍有目标22、历史标志/宽限/弹体混合14。不能把14全归旧锁。activity-release实际released=0、engagedMayRest=0，没有目标路径阳性。
调度自身约0.54–0.63ms不能代表另约4.05–5.12ms的单位step。awake可能含离链单位，须先统计链内存活、保活原因位集、实际step次数/耗时；本轮没有改变休眠资格。

已停止的具体呈现方案不换名重做：farparking确实管理Box1202/Bonus125个vis/shad显示根，不是Box对象数或仅睡眠敌人；range每个候选帧至少711个Box根已移出显示父层，整帧仅约2.15%且四对反向。range的frameChanges=0是未更新默认字段，不是时间线不变证据；严格静态Box普查603经资格筛选剩0，未到屏外判断。内景合图4.37%且横向反退；RV后继约1.59%；视口条带、透明裁剪、GPU地形、wholeworld缓存等详见历史快照。暂停角色缓存不是动态渲染全部无效的证明。lighting2旧热点已由80CF解决，decal准备只约0.06ms而绘图约3ms，旧图章/副本路线已停止。
A796/4E5F实际sceneTick无每帧setZoom，不能用陈旧Grafon/Camera源码整包覆盖。
SATS整数格批量draw再copyPixels已由旧33C1实测否定：7组像素失败，RGB最大3/alpha2；此前只读复核，未重新生成/运行。当前全源可见性不同仍不足证明会消除旧误差；A80宿主保留逐格方案，CS当前D8A。
曾被拒的Monstrik、合并Weapon/UnitVisual+截图、UnitPlayer/SceneObjectCulling组合、Pt+PNG枚举、tag93遥测补丁、CIM CPU查询不转路重试；历史上的更细FA2B DoABC类标签枚举亦被保护拒绝并停止。未请求新授权，兼容结论仅用其他已允许来源。

## 6. 下一步与未完成边界

以镜头移动为核心，正常模拟、完整间隔、长帧和真实画面不能省略。最新证据仍指向可见地形/物件的原生合成成本；局部CPU、分配次数、透明节点数下降均未稳定转成整帧改善。不能据此宣称找到唯一根因、近原版或优化完成。

后继若有新的可检验呈现假设，先与已停止路线及当前准确产品核对；不自动重做环境键、炮塔同帧守护、透明阴影、Math.max clamp、节点cache/combo、远景缓存、全世界缓存、旧Box摘树等；最新完整环memo和直接放宽非整数缩放资格也已停止。对象层细分的错误在计时后摘要，现有完整数据已独立核验，不为修报告重跑同一套2700区间。普通房间、自然纵移/长探索、效果开启与全图2–5秒加载仍未全面达标。

旧活动范围候选只编译、未运行，其旧宿主/源码不等于当前A80/D8A，不是待补做债务。本轮透明阴影普查已运行，撤销旧“未运行”停点；其后继候选结果为不部署。不要恢复已撤回的下午配方或覆盖天角兽/染色/SATS/鼹鼠修复。

保持登记排队、独立静音存储和4GiB/2GiB游戏创建线；不关闭玩家、外部实验或其他任务进程，不重复泛泛索要内存。所有本轮自有实例与登记已结束，没有goal对象，不按旧blocked计数操作不存在的goal。没有后台继续测试的承诺。

## 7. 深入入口

- 最新缩放/扫描：`knowledge/experiments/camera-scale-coverage-20261029.md`；scaled-v3的partial-pixel-review与upcoming的callback-observation-review保留整体失败/容量边界。
- 上轮镜头接续：`knowledge/experiments/camera-motion-20261029.md`；各r1完整证据和独立失败计时复核；完整上一快照`state/MEMORY-history-20261029-before-camera-motion.md`。
- 最新镜头/SATS：camera-sats-current-20261028.md；evidence/camera-nearplayer-layer-split-20261028-r1/{camera-layer-review.json,storage/result.json,process-policy.json}；evidence/camera-nearplayer-tail-20261028-r3/{camera-tail-review.json,camera-nearplayer-tail-inputs.json,camera-air-wait-result.json}；evidence/sats-visible-product-checks-v3-20261028-r1；build/generated/sats-visible-release-20261028/{verification.json,host-audit.json,product-build.json}；state/sats-visible-deployment-20261028.json。keycache v2/v3失败目录与鼠标RESULTS保持原件。
- 当前event-fill：state/camera-presentation-deployment-20261029.json；build/generated/camera-event-fill-product-20261029/{verification.json,verify_deploy.py,product-build.json}；evidence/camera-event-fill-product-{live,camera,checks-v3,memory}-20261029-r1/RESULTS.md。前3项是本次产品证据，memory仅观察且高开销。v1/v2实验和反序结果仍在旧目录，不能取代当前产品结果。
- 停止node-cache：build/generated/camera-event-fill-node-cache-camera-20261029/RESULTS.md及同名evidence后缀-r1；失败live见camera-event-fill-node-cache-20261029/RESULTS.md。不与9D8F纯像素复用混同。
- v2像素组件：build/generated/camera-event-fill-pixel-checks-v3-20261029/RESULTS.md及同名evidence后缀-r1；旧pixel-checks-r1失败原件保留。组件通过不等于动态收益。
- 历史真实战斗详情见camera-live-reassessment-20261028.md；当时参照evidence/camera-dense-reference-rc2-20261028-{normal,scene}-r1/summary.json；tail/build.json、runs；activity-range-current/BUILD-RUN.md；binary/RESULTS.md、audit-proof.json；live/verify_run与paired/RESULTS.md。
- 之前完整快照MEMORY-history-20261028-before-live-reassessment.md保留全部停止路线、源码种子和历史入口；journal顶部按时间接续。
- 原生单次镜头旧证据camera-native-once-20261028：base-r1 AIR24656、cache-r1 AIR70412已退出；2F7B探针、冻结源9b56efbf、pair-review A5471DA2，所有原始输入冻结。
- 85源种子camera-atlas-paged-combat-20261025-r1/probe-build.json SHA983727AE；F15旧候选F15B8CE8与428字节算法来源仍保留，不部署。
- Python C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe；Java D:/Program Files/Adobe Animate 2024/jre/bin/java.exe；Flex/SWC/FFDec在mods/Sandevistan/build/tools，只读依赖。
