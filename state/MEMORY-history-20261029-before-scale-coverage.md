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

## 4. 最新接续：2026-10-29镜头实测，无新部署

用户要求继续优化镜头表现。正式A80/D8A/FE3保持；七次隔离游戏均退出，无自有JVM/AIR或等待登记。主报告`knowledge/experiments/camera-motion-20261029.md`。本轮没有达到近原版，也没有候选可直接部署。

- frame-cost-r1（AIR12080/DA70F6D1）2160区间采48个短窗，1窗Sample count mismatch，整体采样验收失败照实保留。47有效窗支持移动增加原生pre-render/render；sceneNativeEnvironment分配87582/188846次，但数量不是字节或耗时。16次64–70MiB内存下降关联86–112ms；不能据相关就判所有尖峰为GC。getter隔离：totalMemoryNumber2161次共3ms/max2，privateMemory每次11–17ms，后者禁逐帧性能观察。
- environment-current-r1（AIR39688/B6263E1D，诊断宿主9B73）同实例原/缓存键各静横纵360区间，环境两臂各150×20字段、五图RGB0/alpha0通过。横30.247→29.369ms（2.90%）、纵28.969→28.806（0.57%），正内存增量只降2.6%。**停止环境键候选，不部署**；旧F15跨进程7.7%不再作为更强证据。旧Math.max clamp已有失败，不重做。
- turret-pose-r1（AIR88888/E9BAE774）13炮塔×120自然帧全部枪体/子对象身份保留、正确帧且停止播放；**未证实重复重建炮塔**。goto调用栈可能在执行全局待处理队列。
- turret-guard-r1（AIR43360/CFEBC132，诊断宿主55F8）2160/28通过，仅同帧且停止时跳过goto。静23.100→23.936、横33.083→33.231、纵31.447→31.011ms；Stage观察带少约2ms但整帧不改善。**停止炮塔守护**，不做产品化/额外动画验收；原指令/其他5770方法体与1016类保持，诊断宿主禁止安装。
- object-layers-v2-r1（AIR5600/D0CE79ED）2700完整区间采完后，旧末尾360计数断言失败（正确计划15组各180）；原ok=false及登记failed不改。独立completed-timing-review逐条验证可见掩码/时间/29边界/零新增绘制/恢复，明确fullRunPassed=false、timingEvidenceValid=true、未做末尾像素检查。全显静/横/纵23.256/32.089/31.461ms；暂隐visObjs[0]22.189/28.033/29.411；[1]24.117/30.850/30.594；[2]18.667/29.733/30.911；[3,4,5]21.406/31.878/30.283。隐藏只是归因，含阴影的[0]也包含其他物件，不能把差值全归阴影。v1只编译未运行；v2避免逐帧同值写visible。
- shadow-current-r1（AIR81984/26E9FD60）旧未执行透明阴影普查在当前产品运行，9检查/19ms只读/0性能样本：596独立Box阴影，124个wall2+alpha0+滤镜+挂载visible，无别名/共用。
- shadow-cull-r1（AIR47524/0927DF9E）当前产品+本地诊断helper，原生帧前恢复visible、帧后只隐藏透明且祖先效果中性目标。2160/28通过、124目标各B帧实用、视口包围重叠至少4个、五图RGB/alpha全0；134540次隐藏/恢复平衡，localHelperUpdates2166如实记录。静19.169→19.861、横29.133→29.692、纵29.147→28.167ms；横>50帧1→4。**停止透明阴影方案**，无稳定镜头收益，不移除恢复保护或扩到可见阴影追求数字。

末尾Box.step/runVis只读核对不支持固定静止物件每帧重复写位置，未做setter/cache候选。RV磁盘config为enabled=1/current，仅是当前配置证据；本轮所有计时均隔离关闭RV/WB/LAD，不能声称覆盖开启效果时的体验。

本轮三个优化候选停止；没有改生产src/release/根SWF，没有碰外来SceneRenderChecks。详细旧里程碑原快照归档`MEMORY-history-20261029-before-camera-motion.md`，不丢弃0.9.3产品、SATS、鼹鼠等既有证据。

**已部署里程碑仍有效：**CS0.9.3真实product-camera横约11.7%/纵9.7%、product-live约6%平均差且有自然负载差异；长帧并未消失。1213产品检查、7原生V、14SATS像素用例通过。呈现仅scale1/native320/无震屏且RV enabled/wallbright、WB、LAD全关时启用，否则回原生；开效果只证明回退兼容。SATS早前同图开启842/891/713→144/235/184ms已安装，鼹鼠边缘预跑#1010也已修复。

原始证据统一在`knowledge/experiments/evidence/<上述camera-前缀>-20261029-r1`。可直接回读本轮各generated目录的baseline/probe-build/work/verify或host-audit；输入冻结后不改旧校验器、原result或失败登记。旧安装前380/141验证器正确拒绝当前产品，不能放宽断言或用旧宿主覆盖A80。

## 5. 累积活动线索与停止路线

NativeSceneActivity的engaged永久锁尚未被针对性证伪。旧range第13窗awake43→85，后续83–87，总单位167；末态近处43、远处仍有目标22、历史标志/宽限/弹体混合14。不能把14全归旧锁。activity-release实际released=0、engagedMayRest=0，没有目标路径阳性。
调度自身约0.54–0.63ms不能代表另约4.05–5.12ms的单位step。awake可能含离链单位，须先统计链内存活、保活原因位集、实际step次数/耗时；本轮没有改变休眠资格。

已停止的具体呈现方案不换名重做：farparking确实管理Box1202/Bonus125个vis/shad显示根，不是Box对象数或仅睡眠敌人；range每个候选帧至少711个Box根已移出显示父层，整帧仅约2.15%且四对反向。range的frameChanges=0是未更新默认字段，不是时间线不变证据；严格静态Box普查603经资格筛选剩0，未到屏外判断。内景合图4.37%且横向反退；RV后继约1.59%；视口条带、透明裁剪、GPU地形、wholeworld缓存等详见历史快照。暂停角色缓存不是动态渲染全部无效的证明。lighting2旧热点已由80CF解决，decal准备只约0.06ms而绘图约3ms，旧图章/副本路线已停止。
A796/4E5F实际sceneTick无每帧setZoom，不能用陈旧Grafon/Camera源码整包覆盖。
SATS整数格批量draw再copyPixels已由旧33C1实测否定：7组像素失败，RGB最大3/alpha2；此前只读复核，未重新生成/运行。当前全源可见性不同仍不足证明会消除旧误差；A80宿主保留逐格方案，CS当前D8A。
曾被拒的Monstrik、合并Weapon/UnitVisual+截图、UnitPlayer/SceneObjectCulling组合、Pt+PNG枚举、tag93遥测补丁、CIM CPU查询不转路重试；历史上的更细FA2B DoABC类标签枚举亦被保护拒绝并停止。未请求新授权，兼容结论仅用其他已允许来源。

## 6. 下一步与未完成边界

以镜头移动为核心，正常模拟、完整间隔、长帧和真实画面不能省略。最新证据仍指向可见地形/物件的原生合成成本；局部CPU、分配次数、透明节点数下降均未稳定转成整帧改善。不能据此宣称找到唯一根因、近原版或优化完成。

后继若有新的可检验呈现假设，先与已停止路线及当前准确产品核对；不自动重做环境键、炮塔同帧守护、透明阴影、Math.max clamp、节点cache/combo、远景缓存、全世界缓存、旧Box摘树等。对象层细分的错误在计时后摘要，现有完整数据已独立核验，不为修报告重跑同一套2700区间。普通房间、自然纵移/长探索、效果开启与全图2–5秒加载仍未全面达标。

旧活动范围候选只编译、未运行，其旧宿主/源码不等于当前A80/D8A，不是待补做债务。本轮透明阴影普查已运行，撤销旧“未运行”停点；其后继候选结果为不部署。不要恢复已撤回的下午配方或覆盖天角兽/染色/SATS/鼹鼠修复。

保持登记排队、独立静音存储和4GiB/2GiB游戏创建线；不关闭玩家、外部实验或其他任务进程，不重复泛泛索要内存。所有本轮自有实例与登记已结束，没有goal对象，不按旧blocked计数操作不存在的goal。没有后台继续测试的承诺。

## 7. 深入入口

- 最新镜头接续：`knowledge/experiments/camera-motion-20261029.md`；各r1完整证据和独立失败计时复核；完整上一快照`state/MEMORY-history-20261029-before-camera-motion.md`。
- 最新镜头/SATS：camera-sats-current-20261028.md；evidence/camera-nearplayer-layer-split-20261028-r1/{camera-layer-review.json,storage/result.json,process-policy.json}；evidence/camera-nearplayer-tail-20261028-r3/{camera-tail-review.json,camera-nearplayer-tail-inputs.json,camera-air-wait-result.json}；evidence/sats-visible-product-checks-v3-20261028-r1；build/generated/sats-visible-release-20261028/{verification.json,host-audit.json,product-build.json}；state/sats-visible-deployment-20261028.json。keycache v2/v3失败目录与鼠标RESULTS保持原件。
- 当前event-fill：state/camera-presentation-deployment-20261029.json；build/generated/camera-event-fill-product-20261029/{verification.json,verify_deploy.py,product-build.json}；evidence/camera-event-fill-product-{live,camera,checks-v3,memory}-20261029-r1/RESULTS.md。前3项是本次产品证据，memory仅观察且高开销。v1/v2实验和反序结果仍在旧目录，不能取代当前产品结果。
- 停止node-cache：build/generated/camera-event-fill-node-cache-camera-20261029/RESULTS.md及同名evidence后缀-r1；失败live见camera-event-fill-node-cache-20261029/RESULTS.md。不与9D8F纯像素复用混同。
- v2像素组件：build/generated/camera-event-fill-pixel-checks-v3-20261029/RESULTS.md及同名evidence后缀-r1；旧pixel-checks-r1失败原件保留。组件通过不等于动态收益。
- 历史真实战斗详情见camera-live-reassessment-20261028.md；当时参照evidence/camera-dense-reference-rc2-20261028-{normal,scene}-r1/summary.json；tail/build.json、runs；activity-range-current/BUILD-RUN.md；binary/RESULTS.md、audit-proof.json；live/verify_run与paired/RESULTS.md。
- 之前完整快照MEMORY-history-20261028-before-live-reassessment.md保留全部停止路线、源码种子和历史入口；journal顶部按时间接续。
- 原生单次镜头旧证据camera-native-once-20261028：base-r1 AIR24656、cache-r1 AIR70412已退出；2F7B探针、冻结源9b56efbf、pair-review A5471DA2，所有原始输入冻结。
- 85源种子camera-atlas-paged-combat-20261025-r1/probe-build.json SHA983727AE；F15旧候选F15B8CE8与428字节算法来源仍保留，不部署。
- Python C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe；Java D:/Program Files/Adobe Animate 2024/jre/bin/java.exe；Flex/SWC/FFDec在mods/Sandevistan/build/tools，只读依赖。
