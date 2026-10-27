# ContinuousScene — 当前快照

## 1. 模组与目标

全图碰撞、敌人、物品预先生成，画面按视野提前绘制，镜头与弹体连续跨房。远处未参战敌人可暂缓，追击者与飞行弹体保持。CS0.9.0另支持可编辑单一地图；原版地图连续模式由设置开关控制。
当前根任务未完成：**解决镜头移动时卡顿，不论敌人是否出现，目标接近原版**。不以暂停世界的帧率冒充实际游玩性能，也不以减少敌人代替镜头修复。

## 2. 用户约定与职责

- 性能根会话01a13816-367b-7261-8e11-ca9152565dd9；中文简洁进度。已允许继续实测，正常测试自行登记/等待，不重复询问已授权事项。
- 已允许必要RV、WB、LAD、TDFC、RC兼容；RC协调已授权，RC由负责人01a086bb-378c-7f60-b8e1-50d90ffa0996集中部署，不并行覆盖。
- 新增明确授权：ModLoader共享测试登记器的CIM创建时间回退修复；已完成，见第3节。其他跨模组写入不自动获准。
- 已接受RGB最大2/255、alpha不变的候选验证；**实战明显提速和功能正常仍是部署前提**。本机通过门禁后直接部署，无需再确认。
- 已接受视野预绘、远处未参战敌人暂缓与纵向镜头缓冲；保留游戏机制和连续跨房。
- 每次游戏测试使用共享game登记、唯一AIR ID/存储、私有桌面、4GB可用提交内存预检；不关闭玩家/外国测试进程，不写真实APPDATA/pfe，不用Ghost。
- 当前会话精确调用、≤10分钟的构建/验证授权仍有效；按既有保护流程逐条登记，不关闭护栏。
- 无AGENT_SCOPE.md；未擅自创建。src/tests/SceneRenderChecks.as是他人WIP，不恢复/提交。
- SceneAlicornAlerts.as.inc仅源码候选，不构建、接入或部署。用户撤回的10月21日下午7D42/5432配方不得复活。

## 3. 当前安装与最近验证

正式文件本轮未变；新增优化均未部署。526正式文件与13运行库输入在完成的各轮保持。

| 文件 | 当前SHA256 |
|---|---|
| root pfe.swf | A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7 |
| CS0.9.0 | 7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F |
| TDFC0.6.4-scene2 | 7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5 |
| ModLoader2.5.0 | 2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2 |
| RV0.33.10 | 638E2D408E2CF46683C41114F75773829A1B4417D74BFFE9D08855A4FE343710 |
| RC0.2.24-animfix1 | 2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621 |

LAD8ADB/WB1411保持。RC当前回执../RConnect/build/m52/a-live-animation-deploy-01/verified.json（5446D95A），不能把旧RC收益当当前候选收益。
A796颜色修复回执state/scene-tint-deployment-20261024.json verified；保留此前ABE2纵向镜头缓冲/80CF遮挡格复用。任何新宿主应精确保留当前其他方法与素材，不能整包覆盖编辑器CS0.9.0。
ModLoader08957b4已提交登记器修复，15测试通过。工具SHA E9F51CB75420C507F6DB1D96BE6B1430374B0B7A797607FF4438A695A717809E；仅普通查询拒绝5时CIM只读核创建时间，不确定仍保留占用。lineage.py只允许旧8B35→E9F5这一变化。

## 4. 最新实测（2026-10-27 屏外高覆盖与原生缓存）

本批前HEAD67214dd，旧快照MEMORY-history-20261027-before-far-live.md。五次AIR、一次编译失败，正式未改。完整报告build/generated/camera-far-live-detach-20261027/RESULTS.md。

- far-live-visibility aad3a030/C86B26EB：旧水平预热在原生纵移往返差36像素/RGB78，尚未选根、0计时、7图释放、清理通过。后继沿已验证的固定完整偏移预热，仍三次独立精确返回，不重试到成功。
- far-live-warm fc17dc65/F8BBBA32：选1189根，第一视角通过、第二视角资格变化，0计时/28图释放。可见性恢复，但资格审计失败，原cleanup.restored=false保留。
- far-live-cohort 7908bdff：AS3动态字符串键前置自减编译错误，未启动AIR；counts仅改显式int赋值。独立compile-review核526正式/13运行库/86源及脚本，原失败保留。
- far-live-counts edb7c70f/2EE930D4：1170根（554滤镜/991多帧，有重叠），960区间原生静20.579/动33.896，隐藏静26.017/动38.008ms；移动两对+4.517/+3.708，约慢12.1%。10视角精确/150图+边界探针释放，25740写入/26审计，停止隐藏方案。完整首组原生/候选PNG已看。
- native-static-cache 3f841ade/A90AE739：1964根中1392已有缓存、281多帧、168隐藏；路线内合格静态矢量根0，7个可缓存根全在路线外。0开关写入/0计时/13图释放、清理通过；不是缓存性能结论，不盲目换目标重跑。
- far-live-detach da814b43/83072C25：暂摘1203根，960区间静20.613→20.971、动34.325→31.921ms（约7%），移动两对−3.017/−1.792，P95 43→39、最大104→161。静止两对方向相反；收益有限且长帧未解决，只有新线索，未部署。
- detach包括560滤镜/1020多帧；343次边界变化、46次根帧变化观测。13233摘下/13233放回、六层兄弟顺序恢复、10组像素精确、150图+边界探针释放；完整候选PNG已看。移出显示树可能影响原生事件/帧调度，不称纯矩阵成本，不声称所有动画时序不变。两有效轮随机对象不同，不能跨轮直接比较隐藏与摘树。
- counts/detach计时前排除不稳定根分支均未触发，不宣称该分支运行通过。五轮各verify_run独立核526正式/13运行库/86源和时间守恒。AIR59784/71668/49352/71384/61700退出，最终登记空；正式与foreign SceneRenderChecks不变。
- 上批native窗口/画质/上层特效详见旧快照及camera-native-effects-overlay-20261027/RESULTS.md：auto同世界明显更慢；desktop MEDIUM/LOW实际全HIGH；上层原生+GPU下层仅4.4%且静止倒退/像素失败，均未部署。该批已提交67214dd。

## 5. 已知边界与停止路线

- 旧wholeworld实验暂停模拟并固定动画；上一批layer实验保持Flash动画、仍暂停模拟。都是预备路线的ENTER_FRAME间隔，**不是无敌人实玩/真实战斗/物理呈现数**。visibility可能被回调观察，不直接叫纯GPU成本。实际AI、子弹、RV、Windows真实混合呈现、SATS及长时生命周期未验。
- 8间隔观测后只停止显式播放/实际变帧者；隐式活动者清理用play，isPlaying可从false变true，不宣称内部播放状态原样恢复。只用于终结式隔离实例，不能复制进产品。帧脚本固定drain仅允许已核bloat_bulk_896的1/55帧；成功轮未触发，不能声称该分支已验证。
- 完整截图/像素图有冷首次差异；固定全偏移原生预备后，仍检查三次独立精确自然往返，不循环拍到通过。mainMenuOff必须真实调用。GPU读回再叠Stage.draw不能当OS窗口截图。
- 已停止：远景缓存约1%混合；视口条带clean慢16%；原生明暗裁剪慢3.7%；透明边缘裁剪慢10.6%；GPU仅背景无收益；静态地形GPU慢11.3%；远处单帧根隐藏慢4.2%；远处不可见地形摘树慢3%；整world scrollRect真正抑制Camera写入后仍无收益，cacheAsBitmap慢14.6%。不换名重跑。
- merged合图暂停移动约15%，实际战斗只约6%/3%且第二轮配对反向/P95变差，保留候选不部署。整world alpha/visible与六对象层隐藏只作归因，不是产品。旧CPU text trace语义未明，不命名为文字或纹理耗时。
- 世界暂停不能保证后台不再新增surface；只读见新节点应按身份/顺序处理，不强摘/复活旧图块。多帧isPlaying=false不是静态证明。完整旧试验链见新归档，避免重走失败。
- 原Monstrik读取、合并Weapon/UnitVisual读取+截图、host tag93补丁/grant、CIM CPU查询、合并PNG枚举/Pt读取被拒绝，禁止转路重试。当前Camera旧缓存缺正式补丁，不可拿build/cache/current-swf/scripts/fe/inter/Camera.as覆盖A796。
- 全地图2–5秒、近原版动态游玩及所有兼容目标仍未完整达到。此前用户撤回的afternoon配方不得复活，旧本体回退不能无条件套用。

## 6. 下一步（保持活动）

1. 摘树仅暂停诊断7%线索，尚无可部署修复。先核真实世界对直接父节点的依赖、原生移除路径、重新入屏/死亡/物品销毁/门/念力/藏身/RV，再决定是否做动态候选；不能把固定暂停控制器直接接入产品。需继续覆盖无敌人/有敌人镜头移动和高速纵移，不用静止收益替代移动目标。
2. 不扩大重复隐藏1170根（慢12%）、已缓存静态根、原生auto、无效画质或上层缓存边界。旧静态根隐藏/地形摘树/少数睡眠敌人摘树均已有反证；本批摘树覆盖1203不同对象是新线索，不能混作此前已验证产品。
3. 实际战斗明显提速、无回退、RGB2/alpha0、原生功能、RV、SATS、跨区颜色及长期资源通过后才部署。当前没有接近原版证据，根目标继续。

## 7. 接续入口

- 本批camera-far-live-{visibility,warm,cohort,counts,detach}-20261027与camera-native-static-cache-20261027，各prepare/probe_patch/run/helper和verify_run；cohort仅编译失败。总报告detach/RESULTS.md；原始evidence同名-r1，配方冻结，后继新目录。Git -text保存编译原字节。
- 本批前快照MEMORY-history-20261027-before-far-live.md。正式未改、没有新部署。本轮读取src/SceneObjectCulling.as仅确认旧逐对象wrapper路线及念力/藏身限制；不复活该已失败实现。

- 本批camera-native-{window-switch,window-audit,window-draw-warm,quality,effects-overlay}-20261027；各prepare/probe_patch/run、AS3 helper、verify及run-review。window-audit/verify_runs核前两失败，其余各verify_run。原始证据同名-r1。所有运行配方冻结，后续新目录；五目录Git -text保留编译原字节。
- 本批前记忆MEMORY-history-20261027-before-native-windows.md。总报告effects-overlay/RESULTS.md；runtime属性无效事实已入共享游戏知识，无全局技能修改。

- 本批7目录camera-actor-{sprites,direct,frames,frames-checked,frames-scan,atlas,atlas-checks}-20261027。总结果在atlas-checks/RESULTS.md，统一独立脚本在frames/verify_actor_runs.py，7份run-review.json；原始evidence同名-r1。所有运行配方冻结，后续新目录。
- 本批前完整快照MEMORY-history-20261027-before-actor-cache.md；下列上一批入口继续有效。首轮简单Bitmap只覆盖1–3个当前可借用根，不能将旧census的78节点误当本轮全部已直接复用。
- 上一批：build/generated/camera-layer-{dirty,tiles,region}-20261027；原始evidence同名-r1。各prepare/probe_patch/run、呈现器、RESULTS、verify_run均保留，已运行配方冻结，后续新目录。完整旧停点state/MEMORY-history-20261027-before-live-layers.md。
- 上一批三轮没有stop/play/goto；第5节旧冻结播放限制只适用于之前wholeworld实验。KB-000108已回读：像素和几何失效分别跟踪，收益须另测。
- 上一批：build/generated/camera-stage3d-region-prune-20261027与camera-native-gpu-20261027的prepare/probe_patch/run、README/RESULTS、verify_run/verify_pair。再前region-refresh/region-items/item-profile、wholeworld{,-late,-nullslots,-observed,-cost,-settle}、viewport-refresh同根；对应knowledge/experiments/evidence/*-r1为原始证据。所有运行过的生成配方冻结，不原地改后重跑；后续另起目录。
- 新旧完整停点归档：state/MEMORY-history-20261027-wholeworld.md；更早MEMORY-history-20261026-2340.md、MEMORY-history-20261023-0818.md。journal顶部本轮和前轮链。
- 85源种子receipt：knowledge/experiments/evidence/camera-atlas-paged-combat-20261025-r1/probe-build.json（983727AE）；frozen f298932b38e24919991997c68e0a8b8a，probe29AF。新变体86源。lineage入口camera-terrain-layers-20261025/lineage.py只允许登记器8B35→E9F5这一变更。
- 隔离调用沿各run.py，先prepare.py生成并校验源码；共享登记game、独立桌面、唯一ID/存储、≥4GiB提交和≥2GiB物理内存。Python在用户.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe，Java在D:/Program Files/Adobe Animate 2024/jre/bin/java.exe，Flex/SWC/ffdec在Sandevistan/build/tools。
- 本轮按已获授权逐条使用会话01a13816精确调用短时grant；未关闭任何保护。工具说明见.agents/skills/remains-{auto-testing,runtime-debug,mod-build,mod-memory,release-gate}/SKILL.md与ModLoader/docs/TEST-REGISTRY.md。
- design/single-map-authoring.md、state/deployment-v090.json为独立编辑器发布；state/scene-tint-deployment-20261024.json为正式A796染色修复。
