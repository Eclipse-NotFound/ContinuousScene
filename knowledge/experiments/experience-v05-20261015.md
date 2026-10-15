---
domain: rendering
type: experiments
game-version: ["1.02"]
confidence: medium
verified: true
discovered-by: ContinuousScene
evidence:
  - kind: decompiled-game-code
    game-version: "1.02"
    symbol: "fe.graph::Grafon.drawLoc/setLight/decal, fe.inter::Camera.setZoom, fe.loc::Land.createMap, fe.unit::UnitPlayer.actions/crackAction"
  - kind: runtime-experiment
    summary: "保留基线、性能候选、阶段计时、实际输入、像素对照和失败记录；最终Experience 111/111、Factory 34/34及内容/像素审计10/10、Lab 68/68、两轮独占无插桩Perf通过，发布Check 632项通过；四目标已安装，原生启动15/15通过，无未捕获错误"
date-updated: 2026-10-15
---

# 0.5 大场景体验修复调查与发布验证

本文记录2026-10-15的0.5开发与发布过程，**四项产物已部署，安装后原生启动15/15通过，无未捕获错误；仍不能据此宣称达到原版稳定流畅体验**。最终Experience、Factory、完整Lab、两轮独占无计时插桩Perf及发布Check已通过；同一时间其他模组继续独立发布。旧通过记录不自动转移到新组合。`verified: true`表示本文所列实验与发布证据已有效核对，不把下文推测、长期表现或未测玩法升级为已验证事实。

用户要求先让大场景连续加载、运行正常，编辑器暂缓；原版工厂房间仅作连续场景的验证内容。保留镜头连续移动、跨原房间边界的敌人与子弹，进图前一次预生成全图。用户已允许 RealisticVision、WallBlend 必要兼容改动。

## 已确认

### 六类问题及本轮改动

| 用户报告 | 代码和实测确认的原因 | 本轮处理及边界 |
| --- | --- | --- |
| 原版光影、区域外观不对 | 0.4 将不同原房间合成一个 Location，却只用统一 backwall、color、darkness；普通物件和单位也从全图默认色初始化。背景尺寸还错误依赖 400px 暂存图。 | 用原生 `Location.colorFilter` 解析各区颜色，按区域精确裁分四层缓存；补水和弹痕区域颜色、普通动态实体基础色；背景尺寸改按视口处理。视觉暗度与逻辑视线分开核查，不把色调修复等同于全部照明已验收。 |
| 开枪严重卡顿 | 小弹痕固定把中心周围 1024×1024 标为受影响；多数无关块仍重放弹痕。样例每次开枪最多触及 20 块。大图 RV 每帧的全场取格和墙光访问也有稳定成本。 | 按原图形、缩放、旋转、子图形与滤镜求保守包围范围，沿用随机帧并只重放相交块；RV 保留完整逻辑扫描，只减少重复访问与函数调度。不能通过缩小逻辑视野或延迟门/破墙更新换取帧率。 |
| 隔实体墙实际开取 | 原生第一次 E 有 LOS（直线遮挡）门槛，但已开始的 `actions` 只看 active 和计时；玩家移动到墙后仍可完成。`crackAction` 的 Y 路径也没有同等 LOS 门槛。 | 只在大 Location 为持续操作与 Y 补上与首次 E 一致的遮挡规则，保留 telemaster 且 portOn 的原生例外；Loot、comein 仍需要 LOS。普通房间保持原行为。 |
| 镜头缩放快捷键失效 | 补丁在 `Camera.setZoom` 强制 isZoom=0，`sceneTick` 又逐帧调用 setZoom(0)；视口换算未除 scaleV。 | 移除两处强制归零，0/1/2 三档沿原版 1920×1000 参考尺寸计算；实际全图边界不变。缓存与 RV 绘制范围均反算到世界坐标；视口变化仅刷新画面缓存，不强制重跑 FOV 逻辑。 |
| 首次载入过长 | 240 块每块扫描全体 603 个 BackObj，且 WB 再次遍历。全图一次预绘把重复工作集中在入图阶段。 | 原生 setLight 后按实际可见帧建立背景物件空间索引，保持画家顺序与世界坐标；宿主和 WB 复用相交列表。未知图形保守回退到全覆盖，不能丢背景换速度。 |
| 信息页地图和实景均异常 | `Land.createMap` 仍按普通房间网格 48×25 分配，单个大 Location 超出画布。实景另有背景尺寸、缩放换算、区域绘图问题。地图初始左上视图还会受 RConnect 面板遮挡。 | 地图分配取所有 Location 的真实右/下边界，保持原坐标原点和探索逻辑；大地图首次打开时居中，后续原生拖动和缩放保持。实景走上述独立修复，不用信息页修复代替。 |

实现入口分别为 `build/render_camera_patch.py`、`map_patch.py`、`backdrop_patch.py`、`decal_patch.py`、`region_patch.py`、`entity_color_patch.py`、`interaction_patch.py`、`vision_perf_patch.py`；区域辅助代码为 `src/patches/SceneRegions.as.inc`、`SceneEntityColors.as.inc`。字符串替换均要求精确锚点数量，不允许静默漏改。主构建负责整合，普通房间立即走原路径。

### 光照、区域和实体颜色的边界

原生 `Grafon.drawLoc` 使用 `170 + loc.darkness` 生成静态遮暗与层间色变；`setLight` 处理灯具和背景绘图状态。`Location.lighting/lighting2` 处理 `Tile.visi/t_visi`，使用实际空间尺寸；不是把所有照明循环从 48×25 改大就能解决的问题。`retDark`、视距和静态 dark 不是同一概念。所选十二个原工厂区域未发现独立 vis/retDark/noblack/lon 特殊选项，因此本候选未伪造逐区域逻辑视线参数。

区域通过元数据保存原 backwall/color/dark，颜色由原生解析器产生。320px 块与 1000px 原房间高度不整除，不能取块中心的一种颜色覆盖全块：候选按世界区域交集分别渲染再精确拼合四层，保持原纹理取样坐标、背景装饰顺序和块外 40px 邻边。增量弹痕、水层也采用区域裁分；同一次弹痕跨块、跨区使用相同随机帧，不引入整图重绘。进入/退出区域绘制后恢复全局字段。

单位颜色只接在现有 `Unit.setVisPos`、`Box.addVisual/runVis` 点，不逐帧额外扫描所有实体。仅普通 hero=0、ctrans=true 单位及颜色仍属默认/上次区域基础色的对象可更新；严格比较 ColorTransform 八个分量，避免覆盖冻结、念力与高亮。魔法武器 tip=5 排除，影子不染色。`UnitMerc` 独立 arm 附件未额外接宿主方法，属于明确遗留，不据主身体颜色推断所有附件正确。

**全场供电/断电兼容已加入候选，最终Experience中的14项检查全部通过。** 原生 `Location.allon/alloff` 每次修改全局颜色、darkness、lightOn及对象后调用 `World.redrawLoc`。新 `sceneSyncRegionLighting` 在外层sceneOpen进入时，将非零lightOn的全场样式同步到已有区域对象；不在每个临时区域绘制内同步，避免把某一区样式误广播全图。区域绘制的finally恢复全局字段，缓存区域引用的实体能看到新样式；sceneClear重建全部surface，WB按对象身份移除旧pass并重新建立覆盖层。9987C696候选实际验证了开关原生状态、12区域与材质、88个背景物件帧、377个实体基础色、每次240块完整重绘、开/关像素确有差异及测试状态恢复。此测试不等于独立电路、所有电门和开关后长期存读档的完整验证。

兼容目标是保留原生单一Location全场开关语义，不是十二个独立电路。后续若要逐区域电闸，仍需明确设计作用范围和持久化；不能将本轮修复泛化成“全部原版机关兼容”。

### copyChannel小数坐标的独立运行证据

`evidence/copychannel-rounding-20261015-151744` 为首轮，`copychannel-rounding-20261015-152331` 为补充后的165个坐标案例与7个alpha往返案例。使用游戏相同AIR运行时、独立隐藏App ID，不加载宿主。5×5源的每个alpha不同，目标全零；覆盖sourceRect/destPoint各自及组合的x/y/xy，正负0、1、2附近的0.25/0.5/0.75及右下裁切。结果全部精确符合：**sourceRect左/上/右/下四个端点分别取最近整数，恰好半数时取偶；destPoint向零截断；源或目标裁切保留双方映射偏移。** 独立整数模型与165例无不一致，两个进程均退出0。

例如sourceRect.x=0.5、width=3读取x=0..3共4列，而x=1.5、width=3读取x=2..3仅2列。原生decal式的origin=13.5、临时alpha宽4，从源14..17保存，却恢复到目标13..16；跨world chunk原点16时只覆盖其local x=0，并从源world x=17取值。双轴13.5时即使没有draw，4×4及8×8往返也分别改变16和64个alpha像素。因此候选将世界alpha目标框的截断与源采样的取偶分开，先确定全局影响再裁块。此证据说明copyChannel语义，不证明剩余draw像素差异来自抗锯齿。

### 交互复现范围

原生初次 E 已采用 `loc.isLine` 与对象几何中心，并传 owner 保留“门本身不挡对门交互”的例外。大 Location 的 isLine/getAbsTile 使用真实尺寸，未发现因 48×25 截断导致它必然放行。选择高亮、GUI 提示与真正执行应分开观察；提示可见不代表开取成功。

持续开锁的非法路径是先在可见位置开始、再移到同一实体墙后，原计时仍结束；Y 的非法路径直接缺少 LOS。候选只修这两处，并检查当前 action owner 非空且仍在同一 Location。无天赋阻止、telemaster+portOn 允许、portOff 再阻止均纳入测试。实体墙应为原生 `phis==1`；格栅等原生射线可穿过材质不能用来证明该漏洞。SPACE 拾取和已经抓住物体的念力未找到足够证据支持本轮泛化改动，保留原规则。

### 构建保留同期已发布修改

不能直接以 0.4 宿主旧备份最终产物覆盖当前安装。RConnect 已在 13:44 发布 Map1，根宿主由 `2F9FC7FB…A0701` 变为 `BEBEEA8B…4011F`。只看宿主 hash 不足以说明差异；实际比较 `fe.loc.Land` 源码与类布局确认新增了静态 `rconnectSeedSource:Function`、实例 `rconnectLayoutSeed:uint`，构造函数由按地图名固定种子改为新建时随机种子/联机回调，保存最终归一化种子。MainFE loader 未改。不能只把新 constructor 单方法移入缺少字段的老类。

本候选继续用原始宿主 `C631CBF3511B6EE303F533D08D51511FE0EB702F43E5DB17F5241D8576C64867` 作为未改类的源码基线，但 donor 导入、Grafon 整类替换和逐方法合并的输入固定为已发布 Map1 快照 `mods/RConnect/build/m52/a22-map-only-03/native/pfe.swf`，SHA256 `BEBEEA8B3F40A7DB3E7B1BE6F3530D5AF9EA7A3299DECB164BF0DAE107D4011F`。Land 源取该快照的 `native/after/scripts/fe/loc/Land.as`，SHA256 `B1727E83FBEC9863A267B07B5428853CB734C442572D747D592922E8B1EBC060`，然后仅套本轮 createMap 修复。

证据来源：CS `build/generated/baseline.json`、`audit/bytecode-audit.json`；RConnect `state/deployment-a22-map-2026-10-15.md`、`build/m52/a22-map-only-03/prepared.json`、`release-audit.json`、`deployment.json`。Map1 准确源码基线 commit 为 `1a4b683a0be646fc8e53aa4496e016fb6f1be0f8`，冻结树含四文件 map-only 覆盖，不使用其根目录 M51 WIP。

当前静态审计记录候选宿主 `9987C696BEBBEB0626D8F73DA775CF867B2CED4FF626137FD9F161264270F938`，包括世界alpha恢复范围与全场开关样式同步；此前候选为 `2032451D3987BAD8ACAE38776DF1D510C5BABBEBE0AFB505236BB5590EB025A4`，其专项通过保留原组合身份。当前十个必需方法存在，4659个其他具名方法/初始化保持，`rconnectLandLayoutPreserved=true`。`unchangedRequired`允许“必需方法存在且已和目标相同”，不能把缺方法当不需修；本次该数组为空。UnitPlayer.actions的类私有与文件私有命名空间按donor/native实际顺序对应，crackAction保留原actionReady私有访问；不能把donor私有名称直接带入宿主。Grafon是整类替换，不在旧类后追加重复scene字段。

RV 从发布线 commit `0735491e49d0d286ea8847017ae2fb64067a3c71` 叠加本轮兼容，冻结于 `build/generated/rv-production`；不带入 RV HEAD 的 authority WIP。WB 在本轮独立更新到 0.5.3，生产 SHA256 `A6AE7EF3CADA5D4C733A53CE72E2423C35724EF8075CA81393B26EE47F0302CA`，兼容源基于已发布 commit `f32e4a99643ccc901dc4f8e8caac29a6cde441b4`，保留其半格/一击墙和消黑缝改动，不能回退到旧 0.5.1。WB 来源与测试源指纹见 `build/wb-validation/source-provenance.json`；已发布状态见 WB `state/MEMORY.md` 及 `knowledge/experiments/screen-scale-2026-10-15.md`。

记录期间又发现 14:53 的 RConnect fix15 / MSW 独立部署：RC `07B76ED8082462C43EAE7048AF041370FE315A5B6B23CCDF4E600E02ECD443A4`、MSW `DDADA303CD78EF2EA46D0261055B77F48AD72EA99F722555ABCB329DCDE1F9CE`，宿主仍是 Map1。来源 `mods/RConnect/state/deployment-a22-fixes-2026-10-15.md` 与 `build/m52/a22-fixes-15/deployment.json`；源码是准确 Map1 冻结树加 `experimental/a22-fixes` 覆盖。旧 CS 组合中的 RC/MSW 结果不自动代表这两份新文件，最终门禁须核对并测试当前组合，部署和回退均不能覆盖它们。

## 观察到

### 早期性能数据：用于归因，不是最终承诺

原始数据保存在以下 evidence 子目录，均为每阶段 120 个真实帧间隔、原生输入发射 7 次的短测。P95 沿既有 `perf-summary.py` 口径：排序后取下标 `floor(n×0.95)`，不混用其他分位数定义。

| 运行 | 大图首次可操作等待 | 大图开枪帧中位 / P95 / 最大 | 最大受影响块 | 本轮原生单位 |
| --- | ---: | ---: | ---: | ---: |
| `experience-v05-baseline2` | 62,992ms | 47 / 193 / 325ms | 20 | 58 |
| `experience-v05-candidate2` | 41,093ms | 43 / 62 / 131ms | 2 | 60 |
| `experience-v05-profile1` | 22,482ms | 45 / 72 / 194ms | 2 | 56 |

candidate2 相比旧基线的工作量改善与弹痕局部更新一致；profile1 又含 WB 背景筛选和 RV/场景计时插桩，不能作为无插桩最终性能，也不能将三轮差异全部归因于某一个补丁。其大图开枪阶段 RV `prepareOcclusion` 平均约 2.68ms、`refreshWallField` 约 2.23ms，指向重复全场访问成本；保留完整逻辑的 fast path 据此实施。正式无插桩结果另列如下。

三轮单位数和随机内容不同，且不是锁定种子的严格交替 A/B/A。关闭 WB 或 RV 的对照仅用于定位开销，不能作为保留视觉效果时的交付成绩。没有宣称稳定 30fps，重入和长期战斗不能从短测推出。

### 最终发布字节的整体验证与正式性能首轮

`evidence/experience-v05-final`、`factory-v05-final`、`perf-v05-final` 的构建清单均确认宿主为 `9987C696BEBBEB0626D8F73DA775CF867B2CED4FF626137FD9F161264270F938`，入口为 `E977168ED9F1B21FA27A01361E18483D83AAF0808B1A657838F06F6284A81928`，测试探针为 `591CD00297A80535D1557C80086B22E8149C93D26B616F6C6AA1E7F6F3B4245B`；场景XML不变。各目录保留 `loaded-module-hashes.json`，包括本轮RV/WB兼容与同期已发布RC fix15、MSW字节。测试探针仅在隔离运行目录中加载，不能部署到正式游戏。

- **Experience 111/111通过。** 总耗时122,870ms，结束时AS3 `System.totalMemory` 447.6875MB；保存12区域截图、原生/大图地图和三档缩放截图，四组原生输入交互均通过，包含持续E、Y与天赋例外；14项全场供电检查通过。弹痕按下文有独立原生证据约束的判定通过，仍保留 `exactGlobalMatch=false`，不能表述为全图逐像素完全相同。
- **Factory 34/34通过，`verify_factory`内容/像素审计10/10通过。** 总耗时162,881ms，结束时AS3内存500.07421875MB；12个原房间、444原生对象、603背景装饰保留，四层像素审计通过既有门槛。其 `entryMs=38901` 从探针/进程起点累计，包含此前准备，与Perf的旅行到可操作时间不是同一口径，不作加载时间横向比较。
- **完整Lab 68/68通过。** `evidence/lab-v05-final` 为 `mode=full`、`preload=true`，总耗时168,670ms，结束时AS3内存350.484375MB。覆盖实际入口点击和旅行限制、全图预绘、跨三间旧房边界往返、敌人追击与弹体跨界、地形破坏、远块未受局部战斗影响、返回基地恢复原生绘制、同局重入、新旧存档交替及破坏保留。宿主、入口、探针和依赖与最终工厂组合相同；Lab刻意使用走廊夹具XML `8BF1794609AAA3C776566835F87EDFEA8E929BF509A44E797F8B6289E70E59B9`，该测试文件不能替换正式工厂XML。
- **Perf首轮无插桩、独占运行完成且结果通过。** 每个采样阶段120个真实帧间隔，P95继续取排序后下标 `floor(n×0.95)`。总耗时86,966ms；结束时AS3内存431.3671875MB不是进程峰值。普通房4单位，大场景63单位；旧基线大场景58单位，随机内容与组合并非严格同种子A/B。

`build/generated/upgrade-v05-check.json` 于2026-10-15 16:12:28记录 **Check 632/632通过**，核对四套证据、精确运行字节、合并宿主审计及当前安装基线；Check本身未写入正式游戏。632为发布检查项数，不是632次独立运行测试。最初该JSON性能摘要使用另一种离散分位数/中位数取值方式（例如fire p50=43）；门禁汇总函数随后已对齐历史floor P95与标准中位数，逻辑验收条件不变。本文统一从原始帧数组按既有口径计算，偶数样本中位数取中间两数平均（fire=43.5），不混用旧摘要数值。

| 正式首轮采样 | 进入到可操作 | 帧间隔中位 / P95 / 最大 | 发射数 / 最大受影响块 | 120帧中>100ms |
| --- | ---: | ---: | ---: | ---: |
| 原生普通房开枪 | 4,213ms | 33 / 41 / 108ms | 7 / 0 | 1 |
| 大场景静止 | 25,052ms | 38 / 50 / 58ms | 0 / 0 | 0 |
| 大场景开枪 | 同次进入 | 43.5 / 63 / 202ms | 7 / 2 | 1 |
| 大场景开枪后静止 | 同次进入 | 35.5 / 51 / 67ms | 0 / 2（此前弹痕留存统计） | 0 |
| 旧基线大场景开枪 | 62,992ms | 47 / 193 / 325ms | 7 / 20 | 7 |

首轮保留视觉效果时，首次加载、开枪P95与受影响块数均明显改善，但大场景43.5ms中位与202ms尖峰仍弱于普通房，**尚未达到普通房间稳定流畅的体验，不宣称稳定30fps**。同轮诊断性关闭WB和RV后，开枪P95为39ms，仍出现313ms长帧；不能把所有长帧都归因于这两套绘制或认为关闭效果就完全解决。

`process-policy.json` 记录正式Perf首轮进程峰值Private 3031MB、WorkingSet 2966MB；旧基线分别2505MB、2440MB，均增加526MB，**内存没有改善，不能宣称降低**。这些进程数值包含AIR与图像资源等，不能与AS3结束时内存混为一谈。短测不能证明多小时内存稳定性或泄漏不存在。

### 同字节独占性能复测

`evidence/perf-v05-repeat` 为追加复测，未替换首轮。结果通过，总耗时89,337ms；宿主/入口/探针及依赖字节相同，随机生成64单位（首轮63），不是同种子完全相同的战况。普通房进入等待4,381ms，大图27,851ms；结束时AS3内存434.390625MB，进程峰值Private/WorkingSet为2709/2634MB，仍高于旧基线2505/2440MB。

| 复测阶段 | 帧间隔中位 / P95 / 最大 | 120帧中>100ms |
| --- | ---: | ---: |
| 大场景静止 | 42 / 55 / 133ms | 1 |
| 大场景开枪 | 37 / 52 / 154ms | 1 |
| 大场景开枪后静止 | 40 / 54 / 140ms | 1 |

复测仍为7发开枪、最大2个受影响块，两个独立短测均显著低于旧基线开枪P95=193ms，但均存在单次>100ms长帧。首轮202ms及关闭RV/WB后的313ms峰值继续保留；第二轮不同阶段也出现133–154ms峰值，不能宣称尖峰已经消除或完全归因于绘制。两轮证明当前短测改善有重复观察，不证明所有战况或长期稳定流畅。

### 安装回执与当前验证状态

`build/upgrade-v05-receipt.json` 记录2026-10-15 16:18:17四目标安装成功，状态为`installed`。备份目录为 `build/backups/upgrade-v05-20261015-161817307-8a1b6645`，保存本次安装前的当前组合。

| 正式目标 | 安装后SHA256 |
| --- | --- |
| 根 `pfe.swf` | `9987C696BEBBEB0626D8F73DA775CF867B2CED4FF626137FD9F161264270F938` |
| CS入口 | `E977168ED9F1B21FA27A01361E18483D83AAF0808B1A657838F06F6284A81928` |
| RV兼容 | `B7695DF82AA45FDB783C4EB88AFFCB0C34A7674E3A052D2FD128867172A83A49` |
| WB兼容 | `8EAC7B08BABF2631A1897C988C36416BA8B6CF204788256B46F436CACB319BB3` |

工厂XML与正式清单分别保持`1CEA74E2…EB7A9E`、`972764B4…BB7FDF`；其余八个正式模块保持安装前字节，包含RC fix15/MSW同期更新。首轮安装工具失败及完整before状态按下文保留。

安装后原生启动检查已 **15/15通过**，证据为`evidence/pfe-modsettings-continuous-installed-20261015161849/InstalledSmoke.json`及同目录`installed-hashes.json`、各模块日志。使用正式游戏目录中的已安装字节、独立AIR应用身份`pfe-modsettings-continuous-installed-20261015161849`，不使用玩家存储。十一项正式加载器检查、场景原生注册、RV/WB版本及无未捕获错误检查均通过。其范围严格为native startup only：它没有再次操作进图按钮或旅行，相关玩法已由相同宿主/入口/依赖指纹的四套隔离回归覆盖；不能把启动检查说成一次正式玩家存档的全流程游玩。

### 已完成的独立回归

- **RV：42/42。** `SoftHarness` 16、`SharedExplorationHarness` 21、`SceneSightHarness` 5；证据 `evidence/rv-v05-20261015-143227/`。固定候选 SWF 26,176 字节、SHA256 `B7695DF82AA45FDB783C4EB88AFFCB0C34A7674E3A052D2FD128867172A83A49`；源 `RealisticVisionMod.as` 为 `6979263B178B4DEEDF563A88C560614BD867D4FAD89D806484B5A5B851C0D446`。首尾指纹一致。测试仅将 private 改 public、用受控游戏存根编译，并非直接加载该生产 SWF。覆盖 current 遮挡/探索、1000 条门水/越界射线、破墙即时刷新、单位掩膜、classic/current 切换、共享记忆亮度、墙光不扩展当前视野及大图视野向量复用；不代替真实宿主组合验收。
- **WB：三组共470/470。** 独占复跑 Harness 43、Destruction 54、Coverage 373；Coverage 实际覆盖 **4120 个材质组合**，4120 不是额外断言数，也不是宿主编号。证据分别为 `wallblend-test-cs053-harness-20261015144315-2ca765`、`wallblend-test-cs053-destruction-20261015143155-5996e3`、`wallblend-test-cs053-coverage-20261015143316-7a4d64`。宿主均为 `2032451D…025A4`，WB 兼容候选为 `8EAC7B08BABF2631A1897C988C36416BA8B6CF204788256B46F436CACB319BB3`。只将已发布 harness 的精确版本期望由 0.5.3 改为 0.5.3-scene，行为断言不变。独占 120 帧平均更新 3.6ms，通过原有 <8ms 门槛。此处单独列 WB 与 RV，不将不同边界的断言加总成一次完整游戏验收。

`experience-v05-gameplay2` 曾在较早候选组合上通过地图、首次 E 三种天赋条件、三档缩放、背景、水的区域边界像素和十二区域截图；其宿主及 RC/RV/WB 字节与当前最终候选不同，只作为阶段证据。不能把它的通过移算为最新宿主、持续操作/Y、最终地图居中或新模块组合通过。

### 保留的失败与测试判定修正

1. `experience-v05-baseline` 因探针直接 `getDefinitionByName("WallBlendMod")` 找不到类报 #1065；`candidate1` 在设置接口尚未准备好时空引用 #1009。这两轮不是有效性能结果，原始日志保留，后续通过不覆盖它们。
2. `gameplay1` 的 `map-ui-player-aligned` 未过；后续对齐测试补充标记 localToGlobal 与地图坐标的实值。`gameplay3` 再现 x 差 `0.10000000000002274`、y 差约 0.05，而门槛为 0.1，涉及显示坐标量化/浮点边界。最终容差为0.100001，仅覆盖0.1附近的浮点余量，没有扩大到格子级错位；`experience-v05-final`普通、大图和探索后地图标记检查均通过，实际各轴差为0或约0.05。原截图和失败保留。
3. `experience-v05-release` 的旋转缩放弹痕逐像素对照失败，误差曾沿很多块的上边延伸。原测试把一次原生弹痕分别画到所有远处小画布，负 localY 被原生 alpha 恢复区域截到零，制造多条参考图伪差异。参考实现改为在一个足够大的世界局部画布只画一次，再裁给各块；画布外所有像素仍必须不变，增加实际改变范围距画布四边至少64px的断言。没有复制生产包围算法来证明自己。
4. `experience-v05-release2` 使用修正参考后仍在旋转弹痕两块各剩1像素差异，该轮整体仍为失败，不将它追改为通过或全部参考误差。其后的实际修复、独立诊断和最终判定边界见下文，`scene-decal-checks.json` 保留各案例详细结果。该测试会在私有 sceneMarks 留临时图形类，只允许在探针最后执行，然后退出；不能继续存档、旅行或重绘。
5. WB 首轮 `wallblend-test-cs053-harness-20261015142926-844533` 为42/43，120帧平均8.383ms超过原门槛。当时并行游戏/测试负载存在，后续串行独占同字节复跑为43/43、3.6ms。首轮红信号仍保留；没有改代码或放宽8ms，不能宣称并发争用下也达标。
6. 构建曾因区域 helper 注入后出现第二个同文锚点失败，已改为先替换原 sceneRender 调用再注入；也修正过 donor/native 私有命名空间映射。构建保护拒绝时未关闭护栏、未换路径绕过，主线按准确授权处理。成功构建和字节审计是静态证据，仍需真实运行通过。
7. 16:16的首个Install尝试失败：PowerShell把`File.Replace`的第三参数`$null`转换为空字符串。核对四个正式目标和备份均保持before完整状态后，改用`[NullString]::Value`，先以独立txt验证，再新建备份安装成功。失败回执保留在`build/backups/upgrade-v05-20261015-161631185-9290c631/receipt.json`，状态`install-failed`；成功回执不覆盖该记录，不把工具参数失败误写为游戏补丁失败。

后续 `evidence/decal-v05-fixed` 使用9987C696宿主，已消除原大片alpha条纹错误，但**该轮整体仍失败**，当时仍要求alpha对全局参考完全一致。当前剩两个世界像素，在相邻两块的重复gutter中各出现一次：`(4129,2303)` 的预期ARGB为`FFA6B4C2`、实际为`FFA2B0BD`；`(4131,2303)` 的预期为`2E000000`、实际为`28000000`。因此日志含两次alpha差异（同一世界alpha像素在两块重复），最大alpha差6，另一个世界像素的RGB差不超过5。不能把“两个世界像素”误写成全图完全相等，亦不能把旧大片错误与当前小差异混成同一未定位问题。

旧native-local参考仍可能受自身alpha恢复范围影响，不足以独立解释剩余差异。独立诊断 `evidence/decal-v05-pure-native` 已把原生cut+draw与alpha保存/恢复分开取证：240个surface共检查38,400,000个像素，只有上述两个世界像素（包含重复gutter共4次）与世界局部大画布参考不同，且都在原生alpha恢复框 `(3135,931,1410,1338)` 外。两块各自检查的132,400个框外像素中，实际结果与独立原生cut+draw的完整ARGB差异数均为0；两个世界差异像素也逐个完整ARGB相等。对全局参考仍有RGB最大5、alpha最大6的差异，`exactGlobalMatch=false` 保持记录。该诊断沿用此前严格全局alpha判定，因此自身 `result.json` 仍为失败，不能事后改记为通过。

据此，最终验收明确区分原生alpha写入框内外，并保留全局差异统计：框内alpha差必须为0，出现RGB差异的像素必须完整ARGB等于独立native-local参考，且各色通道的预乘差 `abs(A*C-Aref*Cref)` 不超过255；框外每个不同像素必须完整ARGB等于独立pure-native cut+draw，并且对全局参考的A/R/G/B原始通道差各不超过8。整个案例的差异像素数（含重复gutter）还必须不超过64，沿用原Factory测试容差的数量级，最终实测为4。没有取消未解释像素或漏改块检查，也没有把两种参考都不符的像素排除在外。`experience-v05-final`按此边界通过，框内alpha差0，框外接受4个重复计数像素，拒绝像素及未解释比较块均0；`exactGlobalMatch=false`保留。这是基于独立原生证据修订判定规则，不是全局零误差的证明，亦不据此断言引擎抗锯齿或栅格化机理。原release/release2、decal-v05-fixed、decal-v05-pure-native红信号及完整像素诊断均保留，后续通过不得覆盖原记录。

## 推测

弹痕范围和背景索引减少的重复工作，应降低持续射击尖峰及首次预绘时间；正式首轮短测与此方向相符，但残余尖峰、密集敌人和长时破坏场景仍可能受全图物理、对象更新、RV 全场逻辑与 AIR 合成/垃圾回收限制，具体长帧原因尚未完全分离。不能从局部 CPU 下降推出整个游戏已恢复原版流畅度。

初始 E 的明确 LOS 逻辑未能解释用户所有“隔墙开取”情境；持续动作和 Y 已有具体可复现路径，仍应结合用户后续物品类型与输入补充取证。不得因为两条路径被修就宣称所有拾取、念力或自定义物体已验证。

## 发布验证汇总与尚未验证范围

| 发布项 | 当前记录 | 回填要求 |
| --- | --- | --- |
| 最终 Experience | `experience-v05-final` 111/111通过，含14项供电检查与四组实际输入交互 | 已保留截图、指纹、全部断言和exactGlobalMatch=false；原失败不覆盖 |
| 最终 Perf | `perf-v05-final`与`perf-v05-repeat`两轮无插桩独占通过；开枪分别43.5/63/202ms、37/52/154ms | 首轮完整保留，仍未达到原生稳定流畅；两轮进程峰值均高于旧基线，不引用profile1作最终数值 |
| 最终 Factory | `factory-v05-final` 34/34，`verify_factory`10/10通过 | 内容、图层审计和截图已存档；累计entryMs不得与Perf旅行等待直接比较 |
| 最终 Lab | `lab-v05-final` full/preload=true，68/68通过 | 完整往返、追击、弹体、破坏、基地恢复及新旧存档证据已存档；走廊XML只作夹具 |
| 发布前Check | `upgrade-v05-check.json` 632/632通过 | Check本身只检查；安装另有回执，不能混同 |
| 安装与原生启动 | 四项产物已部署，正式路径原生smoke 15/15通过，无未捕获错误 | 独立AIR身份，native startup only；同字节四套隔离回归覆盖进图/按钮/玩法，未部署测试驱动、profile源码或旧sceneXML |

本轮场景 XML 仍为已发布工厂字节 `1CEA74E218A55894D432E12CDFC544952D37CFFF5FF55B256B1B970573EB7A9E`，不借体验修复变更布局。只认证根目录1.02；DLC、多种窗口与OS合成器、完整联机、多小时稳定性、全部剧情/电路/原版模板和编辑器不在本报告已完成范围内。回退必须从本次正式安装前的当前组合备份恢复，不能使用旧0.4整套回退撤销 Map1、WB0.5.3 或后续 RC/MSW 发布。
