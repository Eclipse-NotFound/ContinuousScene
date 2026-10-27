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

## 4. 最新实测（2026-10-27 实际水平镜头与交战）

本批前HEAD73f4fa3，旧快照MEMORY-history-20261027-before-live-parking.md。七目录、一次编译失败/八次AIR，正式未改；总报告build/generated/camera-live-parking-range-20261027/RESULTS.md。

- 暂停摘树7%线索进入真实战斗后未得到明显提速。完整窗口均原生输入跑动、六SMG射手/玩家assr、20×60连续区间，2032×1084/zoom1、LAD/RV/WB关闭；不同轮随机对象不同，只各轮内比较。
- window e509fcf4/74E83D09/AIR59916：1327根，最多1086暂存；原生47.258→候选49.658ms，管理0.183/5.875ms，平均慢约5.1%。单视角软件像素精确、原生Location.remObj不复活、清理通过。
- math e5087010/100CC091/AIR61480：1200区间47.443→51.292ms，管理4.182ms，仍慢；终结式新旧坐标审计失败，未保存最大差，不归因于舍入。像素/移除未执行，根恢复通过。此路线停止。
- range 9d760a10/389A5495/AIR21036：82组、活动48–51组/最多840图像，管理降至0.913ms；49.292→48.232ms仅约2.15%，6对较快/4对较慢，P95 69→64，最大138→151。软件像素0差/原生Box移除不复活/清理通过；收益不足，不部署，不继续盲目细调屏外管理。
- range实际玩家400/敌人885开火帧，每窗口相机X跨度206–276px；独立movement_audit确认三完整轮实际水平相机/角色位移，所有Y相机固定。不是无敌人/跳跃纵移/RV/SATS/完整原版基准验收。report.nativeInputMotion.measurement为空占位，实际记录在每窗口nativeInputMotion。
- 保留失败：首live-parking a8a87358编译try/finally返回错误；return 2668ea6a/2EB7 r1在index13/age40后监控347s/1445s空档超时，无最终结果/清理证明；r2晚显示窗口后allStat2，0暂存，清理通过。早显示窗口后成功轮无焦点事件；失焦因果仅有源码支持，不是失败轮事件实证。
- math r1 AIR46488预热phase3/age259、候选未开始，可用提交11.75GB→5MB触发原保护，只停止自有测试；无最终清理证明。后余量恢复到17.8GB才用同冻结SWF复测。
- groups da3a1467/177070F8/AIR61324与safe-groups 5a31a6a2/38741C23/AIR69812分别读取玩家不存在的公开lurkBox/lurk而失败；各1原生窗口、0暂存、清理通过。前述对旧代码的字段解释错误，不能再猜玩家有这些字段。range仅用已确认X/Y/teleObj，保留玩家1024px周边和镜头提前区。
- window/range检查是计时后单视角Stage软件像素，3图+边界探针释放；未保存PNG/目视窗口，不是全路线GPU呈现。Location.remObj验证不是全部伤害死亡/门/藏身/拾取路径。
- 独立审查：window/review_batch、math/review_batch、groups/review_runs、range/movement_audit；526正式/13运行库/86源闭包和完整区间守恒通过。具体失败保持失败；初次超时与内存中止不补造清理成功。
- 本批新增保护拒绝：联合rg读取UnitPlayer.as与SceneObjectCulling.as的lurk字段被PreToolUse拦截；未换路径/工具重试。后继按已运行的数据范围完成候选。先前拒绝边界继续。

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

1. 目标仍未解决。暂停摘树7%不能当实战收益；逐根暂存更慢，区域暂存总收益约2%且混合，停止把屏外管理当主要修复。转向屏内绘制，具体新机制先核证据，再做独立候选；不能复活旧wrapper/actor缓存失败路线。
2. 补真正原版模式、无敌人和纵向镜头基准。当前2032×1084/zoom1接近1920×1000单房尺寸，原版对照须核实际镜头位移而非按键请求；旧未mainMenuOff的原版基准无效。当前完整实测全部水平相机，不能称跳跃问题已验证。
3. 任何可部署方案还须明显实战收益、无回退、像素RGB2/alpha0、原生门/藏身/念力/死亡/拾取、RV/SATS/跨区颜色及长期资源通过。range滤镜外延取整组收集边界，移除外侧节点后内部强滤镜成为边界、动态滤镜扩大尚未保证；1024px提前区不是通用正确性证明。

## 7. 接续入口

- 本批七目录camera-live-parking{,-return,-window,-math,-groups,-safe-groups,-range}-20261027。range/RESULTS.md总报告，range/movement_audit.py核实际水平位移；groups/review_runs.py可核失败的完整1200区间，math/review_batch.py可核内存中止。已运行配方全部冻结；后继新目录。
- 本批前快照MEMORY-history-20261027-before-live-parking.md。没有新部署。共同86源来自原29AF种子，仅驱动和测试helper改变；不触碰正式CS编辑器或SceneAlicornAlerts候选。无新共享事实/技能修改。

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
