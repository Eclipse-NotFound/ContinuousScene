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

## 4. 最新实测（2026-10-27）

上一批已提交a79fdc6。旧完整停点已存state/MEMORY-history-20261027-before-live-layers.md。本批三个新候选保持Flash动画，但游戏模拟仍暂停，均未部署。

- layer-dirty 448ed0d2：9层组只在时间轴变化时更新；960区间/9检查。原生静/动23.3375/35.7208ms，缓存47.1500/42.6792；移动两对+8.20/+5.72ms。只有角色组重画480次，更新10067ms（20.973/区间，含上传1826），19177帧变化，无计时分配。13全图RGB132/alpha0拒绝，自然/恢复精确。30CPU图/29纹理/260像素图释放、6910隐藏/恢复。AIR66260，入口4991ms。
- layer-dirty首原生/候选全图已实看，没有整块地形/角色缺失；1975像素RGB≥3、153≥64，最大点(1113,600)从(245,197,150)变(245,146,18)。混合或缓存组合只是待查假设，不能当画质通过。
- layer-tiles bd8ebe9d：按变化角色旧/新范围刷新512块，首7块64ms/上传2ms。完整角色层oracle失败，1364像素RGB128/alpha24，0帧率区间。两完整PNG已看，差异在角色/光晕边缘，具体原因未证。42CPU图/34纹理/79像素图释放、246隐藏/恢复，清理通过。AIR64548，入口5122ms。visualAccepted初始true不是通过，trial.passed=false，原失败保留。
- layer-region fccbb003：固定整图坐标，一次draw中性角色层，clip限定写入后copy到块；独立完整参照仍由world绘制。13角色层oracle RGBA精确，960/9完成。原生静/动25.2042/33.9792ms，缓存34.2750/34.9708，配对+0.967/+1.017ms，无净收益。480次draw4219ms（8.790/次），2397块更新5685ms（11.844/区间，含上传953）；20614帧变化，无计时分配，最多5块，均dirty约143万像素。
- layer-region全图仍13次RGB121–184/alpha0拒绝，自然/恢复精确。局部正确不代表合成正确；同时改源层和坐标，不单独归因其中一个。41CPU图/33纹理/260像素图释放，302隐藏/恢复，CPU峰90,024,776B/GPU71,203,144B。AIR9832，入口5030ms。
- 三目录RESULTS/verify_run→run-review均核526正式/13运行库/86冻结源、工具输入和完整时间戳。AIR66260/64548/9832退出，最后登记空。正式版本保持，根目标继续。
- 旧关键边界：完整冻结world29.658→12.092ms只有上限且画质不合格；整视口重画41.333ms、512区26.067ms、逐对象约770ms、475阴影根剔除26.65ms；原生GPU模式未显示优势。完整旧失败保留在归档，不重复调块尺寸或边距。

## 5. 已知边界与停止路线

- 旧wholeworld实验暂停模拟并固定动画；本轮layer实验保持Flash动画、仍暂停模拟。都是预备路线的ENTER_FRAME间隔，**不是无敌人实玩/真实战斗/物理呈现数**。visibility可能被回调观察，不直接叫纯GPU成本。实际AI、子弹、RV、Windows真实混合呈现、SATS及长时生命周期未验。
- 8间隔观测后只停止显式播放/实际变帧者；隐式活动者清理用play，isPlaying可从false变true，不宣称内部播放状态原样恢复。只用于终结式隔离实例，不能复制进产品。帧脚本固定drain仅允许已核bloat_bulk_896的1/55帧；成功轮未触发，不能声称该分支已验证。
- 完整截图/像素图有冷首次差异；固定全偏移原生预备后，仍检查三次独立精确自然往返，不循环拍到通过。mainMenuOff必须真实调用。GPU读回再叠Stage.draw不能当OS窗口截图。
- 已停止：远景缓存约1%混合；视口条带clean慢16%；原生明暗裁剪慢3.7%；透明边缘裁剪慢10.6%；GPU仅背景无收益；静态地形GPU慢11.3%；远处单帧根隐藏慢4.2%；远处不可见地形摘树慢3%；整world scrollRect真正抑制Camera写入后仍无收益，cacheAsBitmap慢14.6%。不换名重跑。
- merged合图暂停移动约15%，实际战斗只约6%/3%且第二轮配对反向/P95变差，保留候选不部署。整world alpha/visible与六对象层隐藏只作归因，不是产品。旧CPU text trace语义未明，不命名为文字或纹理耗时。
- 世界暂停不能保证后台不再新增surface；只读见新节点应按身份/顺序处理，不强摘/复活旧图块。多帧isPlaying=false不是静态证明。完整旧试验链见新归档，避免重走失败。
- 原Monstrik读取、合并Weapon/UnitVisual读取+截图、host tag93补丁/grant、CIM CPU查询、合并PNG枚举/Pt读取被拒绝，禁止转路重试。当前Camera旧缓存缺正式补丁，不可拿build/cache/current-swf/scripts/fe/inter/Camera.as覆盖A796。
- 全地图2–5秒、近原版动态游玩及所有兼容目标仍未完整达到。此前用户撤回的afternoon配方不得复活，旧本体回退不能无条件套用。

## 6. 下一步（保持活动）

1. 当前方案仍要重新栅格化角色层，停止继续每帧draw调参。下一条应直接复用已有Bitmap/帧图像，先小范围验证身份、是否原地改写像素、颜色/滤镜/旋转/裁剪与层序，再扩展正常动画；不直接重写整个显示树。
2. 旧world-layers-20261022-route200-r1/storage/result.json清点：135单位主体中78个Bitmap节点，119主体离屏、16在屏；玩家53 Shape/0 Bitmap，87附件根/0 Bitmap。只是旧样本线索，当前比例和更新语义未验，不能凭位图身份假定内容不变。
3. 最新只追踪时间轴帧变化；任意位图像素写入、脚本变换、AI/真实弹体、门、场景生命周期尚未接入。含地形组若重画还需处理原生视野裁剪。局部oracle通过不代表GPU合成通过，发光/角色附近大色差仍要定位，不放宽RGB2/alpha0。
4. 小范围可复用后再验有/无敌人真实镜头输入、正常AI/子弹、OS窗口、跨区颜色、RV、SATS和长期释放。通过实际门禁才备份部署复验；本轮三个候选都不部署。

## 7. 接续入口

- 本轮最新：build/generated/camera-layer-{dirty,tiles,region}-20261027；原始evidence同名-r1。各prepare/probe_patch/run、呈现器、RESULTS、verify_run均保留，已运行配方冻结，后续新目录。完整旧停点state/MEMORY-history-20261027-before-live-layers.md。
- 当前三轮没有stop/play/goto；第5节旧冻结播放限制只适用于之前wholeworld实验。KB-000108已回读：像素和几何失效分别跟踪，收益须另测。
- 上一批：build/generated/camera-stage3d-region-prune-20261027与camera-native-gpu-20261027的prepare/probe_patch/run、README/RESULTS、verify_run/verify_pair。再前region-refresh/region-items/item-profile、wholeworld{,-late,-nullslots,-observed,-cost,-settle}、viewport-refresh同根；对应knowledge/experiments/evidence/*-r1为原始证据。所有运行过的生成配方冻结，不原地改后重跑；后续另起目录。
- 新旧完整停点归档：state/MEMORY-history-20261027-wholeworld.md；更早MEMORY-history-20261026-2340.md、MEMORY-history-20261023-0818.md。journal顶部本轮和前轮链。
- 85源种子receipt：knowledge/experiments/evidence/camera-atlas-paged-combat-20261025-r1/probe-build.json（983727AE）；frozen f298932b38e24919991997c68e0a8b8a，probe29AF。新变体86源。lineage入口camera-terrain-layers-20261025/lineage.py只允许登记器8B35→E9F5这一变更。
- 隔离调用沿各run.py，先prepare.py生成并校验源码；共享登记game、独立桌面、唯一ID/存储、≥4GiB提交和≥2GiB物理内存。Python在用户.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe，Java在D:/Program Files/Adobe Animate 2024/jre/bin/java.exe，Flex/SWC/ffdec在Sandevistan/build/tools。
- 本轮按已获授权逐条使用会话01a13816精确调用短时grant；未关闭任何保护。工具说明见.agents/skills/remains-{auto-testing,runtime-debug,mod-build,mod-memory,release-gate}/SKILL.md与ModLoader/docs/TEST-REGISTRY.md。
- design/single-map-authoring.md、state/deployment-v090.json为独立编辑器发布；state/scene-tint-deployment-20261024.json为正式A796染色修复。
