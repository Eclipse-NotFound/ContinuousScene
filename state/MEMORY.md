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

## 4. 当前实测停点（2026-10-27）

前轮7次＋本轮3次隔离运行，正式文件未变；完整world绘制出现**固定画面上限收益**，局部动态成本仍未解决，尚未成为合格产品。

- wholeworld初轮25f57170：立即停止22个显式时间轴，预备后24个轴仍变帧；65图释放/0计时/恢复失败。late 99c35ff8：延后停止，遍历空节点，65图释放/0计时/清理通过。nullslots f22d6e66：7444节点/1670多帧，本轮空槽0；24个isPlaying=false的osn/Bloodwing子轴仍变化；7纹理/8临时图/65像素图释放，恢复失败。旧失败均保留，未证明空槽根因。
- observed 3c3ad63c：8间隔实看帧变化，停止47（24隐式），无变化；首视角92738像素差异，604像素RGB≥3、最大112/alpha0/精确恢复，0计时。80像素图/8临时图/7纹理释放。已看完整PNG，发光边缘颜色差异，具体混合原因未证实。
- cost 666d6fb8：明确允许画面不合格的归因计时（visualAccepted=false，**不放宽RGB2部署门槛**），但两个pfe_fla::bloat_bulk_896在下一间隔从55→3并重新播放。源已核frame55 gotoAndPlay(2)、frame1随机gotoAndPlay。0计时，47中45恢复，外部改动的2个未覆盖，恢复失败保留。
- **settle 08eb4372完整960/9**：固定一次已知帧脚本消化＋下一间隔核验；实际drain0，分支重停没有得到动态验证。固定43播放者（25隐式）；7纹理22,626,944字节，整个2392×1444区域预先捕获。原生静止11.229/移动29.658ms，GPU静止11.125/移动12.092ms；两移动配对−16.892/−18.242ms，约59.2%。原生移动多18.429ms，GPU只多0.967ms。中位数29→11，P95 36→16，但106/130ms长帧仍在，不能说卡顿已解决。
- settle的13视角全visualAccepted=false，RGB92–253/alpha0，原生恢复精确；18组自然基线通过。第5视角实看无明显地形缺失，RGB≥3为2509像素，发光线/伤害数字附近不同，28像素≥200。不仅是1/255舍入；数字像素位置差异原因未明。260像素检查图、8临时图、7纹理释放，43播放者恢复，八项计时预绘计数零变化。
- **viewport-refresh 712c32f2完整960/9**：每GPU区间重新draw整个当前视口并上传，原生裁剪保留，计时不分配。原生移动30.988→GPU移动41.333ms，配对+10.808/+9.883ms，约33.4%倒退，停止此实现。480计时重绘24.5ms/次、上传2.9417ms/次。原生/GPU静止13.183/40.604ms；13像素刷新＋480计时=493、上传495、copies494。2纹理/2CPU图/260像素图释放，47播放者恢复。画面仍不合格，非实战，不部署。
- 两份独立复核：wholeworld-settle/verify_runs.py→runs-review.json（前6轮）、viewport-refresh/verify_run.py→run-review.json。每轮526正式/13运行库/86源/脚本保持。AIR58696/68948/64972/65440/30136/41748/21864均退出；实际占用再即时查询。cost/verify_runs.py是未运行的冗余草稿，不作为证据、不提交（删除失败未转路处理）。
- **region-refresh 8aeeac0b完整960/9**：固定所有预备视口交集中的512平方区域，每GPU间隔重画/上传，并以不透明背景清除旧区域再合成。原生移动30.7375→GPU26.0667ms，配对−4.6333/−4.7083，改善15.20%；静止11.6958→26.1208。480次CPU重画11.8875ms/次、上传0.4229；仅一块区域已消耗大部分收益。首PNG实看为密集敌人/数字/地板，133848像素非透明，并非空区。13组RGB77–137/alpha0仍拒绝；原生自然/恢复精确。9CPU/8纹理/260像素图释放，493刷新/501上传/501copies，49播放者恢复（26隐式）。
- **region-items a4b28765超时失败**：试按层序逐对象画区域，只有351区间：原生静止120/移动120/GPU静止111，未到GPU移动，不能作完整配对。GPU静止均770.378ms，已采111更新重画756.315ms/次，其中draw745.640、筛选6.811；每次查询2368、剔除1671、仍draw697。还有一次已执行但未采间隔的更新，独立审核明确保留；不延长/重跑。首区域419像素不同、maxRGB29/alpha32；不合格。13像素/18自然组原生恢复精确，10CPU/8纹理/260图释放，41播放者恢复；生命周期125刷新/133上传/134copies，清理通过。
- **item-profile 95db1be6完成短剖析，0帧率区间**：首区域707次draw共974ms，578根几何界在区外（844ms）。474个带DropShadowFilter的箱子/家具/门共689ms；105 Bitmap带scrollRect共157ms，93个几何界在区外。是失败候选的过度保守剔除和重复draw成本，**不是原生舞台根因证明，几何界也不含滤镜外延**。13整图RGB255仍拒绝；恢复精确。10CPU/8纹理/260图释放，42播放者恢复（23隐式），13刷新/21上传/22copies。
- 新三目录各有RESULTS、verify_run.py→run-review.json，全部正式526/运行13/冻结86源与输入保持；AIR31808/52276/23204均退出，最后登记为空。新候选均不部署；整个任务仍未完成。

## 5. 已知边界与停止路线

- 上述是暂停模拟、固定动画、预备路线的ENTER_FRAME间隔，**不是无敌人实玩/真实战斗/物理呈现数**。visibility可能被回调观察，不直接叫纯GPU成本。实际敌人AI、子弹/动态画面、RV、Windows真实混合呈现、SATS及长时生命周期未验。
- 8间隔观测后只停止显式播放/实际变帧者；隐式活动者清理用play，isPlaying可从false变true，不宣称内部播放状态原样恢复。只用于终结式隔离实例，不能复制进产品。帧脚本固定drain仅允许已核bloat_bulk_896的1/55帧；成功轮未触发，不能声称该分支已验证。
- 完整截图/像素图有冷首次差异；固定全偏移原生预备后，仍检查三次独立精确自然往返，不循环拍到通过。mainMenuOff必须真实调用。GPU读回再叠Stage.draw不能当OS窗口截图。
- 已停止：远景缓存约1%混合；视口条带clean慢16%；原生明暗裁剪慢3.7%；透明边缘裁剪慢10.6%；GPU仅背景无收益；静态地形GPU慢11.3%；远处单帧根隐藏慢4.2%；远处不可见地形摘树慢3%；整world scrollRect真正抑制Camera写入后仍无收益，cacheAsBitmap慢14.6%。不换名重跑。
- merged合图暂停移动约15%，实际战斗只约6%/3%且第二轮配对反向/P95变差，保留候选不部署。整world alpha/visible与六对象层隐藏只作归因，不是产品。旧CPU text trace语义未明，不命名为文字或纹理耗时。
- 世界暂停不能保证后台不再新增surface；只读见新节点应按身份/顺序处理，不强摘/复活旧图块。多帧isPlaying=false不是静态证明。完整旧试验链见新归档，避免重走失败。
- 原Monstrik读取、合并Weapon/UnitVisual读取+截图、host tag93补丁/grant、CIM CPU查询、合并PNG枚举/Pt读取被拒绝，禁止转路重试。当前Camera旧缓存缺正式补丁，不可拿build/cache/current-swf/scripts/fe/inter/Camera.as覆盖A796。
- 全地图2–5秒、近原版动态游玩及所有兼容目标仍未完整达到。此前用户撤回的afternoon配方不得复活，旧本体回退不能无条件套用。

## 6. 下一步（目标保持活动）

1. 完整固定世界有59%上限收益，但整视口刷新倒退、单块512刷新仅15%，逐对象draw更严重倒退，均不得原样重跑。短剖析已指出候选把大量远处DropShadow物件与scrollRect Bitmap逐个画进小区域；下一步研究**可靠效果边界的批量剔除＋一次整树绘制**，或复用原有Bitmap，减少重复原生draw。先验证边界和成本，不能仅凭几何界删除阴影。旧far-singleframe明确未覆盖带滤镜根，但其无收益证据仍保留，不混为同一已证实原因。
2. 仍无完整动态追踪。区域交集/样式资格缓存依赖冻结动画，仅诊断；不能把固定区域当真实动态覆盖。旧/新位置、弹体尾迹、新生/销毁图块、弹痕、门和特效变化都须保留；先证明动态成本与正确性，再谈部署。
3. 画质问题未解决：混合/发光与伤害数字有大于RGB2差异；逐对象区域还出现alpha32，不能忽略透明度变化。需具体定位层和对象；GPU readback尚未证明Windows窗口呈现。完整固定图不是产品，不直接部署。
4. 能够保持动画后，再做有敌人/无敌人的真实输入镜头移动对照；全部区间保留。当前原生近原版基线需同尺寸/同路线，旧2032固定cam(56,42)不是运动基线，不能复用作收益分母。
5. 通过实际门禁才备份、本机部署、安装复验；A796/CS0.9.0已安装版本保持。继续测试前查共享占用，不清理他人游戏。

## 7. 接续入口

- 最新：build/generated/camera-stage3d-{region-refresh,region-items,item-profile}-20261027/的prepare/probe_patch/run、README/RESULTS、verify_run。前轮wholeworld{,-late,-nullslots,-observed,-cost,-settle}与viewport-refresh同根；对应knowledge/experiments/evidence/*-r1为原始证据。所有运行过的生成配方冻结，不原地改后重跑；后续另起目录。
- 新旧完整停点归档：state/MEMORY-history-20261027-wholeworld.md；更早MEMORY-history-20261026-2340.md、MEMORY-history-20261023-0818.md。journal顶部本轮和前轮链。
- 85源种子receipt：knowledge/experiments/evidence/camera-atlas-paged-combat-20261025-r1/probe-build.json（983727AE）；frozen f298932b38e24919991997c68e0a8b8a，probe29AF。新变体86源。lineage入口camera-terrain-layers-20261025/lineage.py只允许登记器8B35→E9F5这一变更。
- 隔离调用沿各run.py，先prepare.py生成并校验源码；共享登记game、独立桌面、唯一ID/存储、≥4GiB提交和≥2GiB物理内存。Python在用户.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe，Java在D:/Program Files/Adobe Animate 2024/jre/bin/java.exe，Flex/SWC/ffdec在Sandevistan/build/tools。
- 本轮按已获授权逐条使用会话01a13816精确调用短时grant；未关闭任何保护。工具说明见.agents/skills/remains-{auto-testing,runtime-debug,mod-build,mod-memory,release-gate}/SKILL.md与ModLoader/docs/TEST-REGISTRY.md。
- design/single-map-authoring.md、state/deployment-v090.json为独立编辑器发布；state/scene-tint-deployment-20261024.json为正式A796染色修复。
