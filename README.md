# ContinuousScene：连续大场景 0.5.0

**0.5.0已部署，安装后原生启动验证15/15通过，无未捕获错误。** 最终Experience 111/111、Factory 34/34及内容/像素审计10/10、完整Lab 68/68与两轮独占无插桩Perf已通过，发布前Check为632/632。当前仍未达到普通房间的稳定流畅度。完整数据、失败记录与修复依据见 [0.5调查记录](knowledge/experiments/experience-v05-20261015.md)。

当前阶段只做大场景运行，地图编辑暂缓。游戏入口使用 **12 个原版工厂房间组成的连续测试场景，192×75 格，即 7680×3000 像素**，保留 444 个物件标记和 603 个背景装饰。场景内没有换房线，玩家、敌人和弹体共用同一个坐标空间。它不是原版随机工厂完整剧情的复刻。

## 游戏内入口

保存并正常重启根目录 1.02 游戏后，打开哔哔小马的 **信息页**，点击顶部的 **大场景 · 工厂**；进入后同一按钮变成 **大场景 · 返回基地**。入口沿用原版旅行限制，受伤、负重或剧情条件不允许旅行时不会强制传送。

正式场景沿用当前角色，按工厂数据生成原版敌人，不自动开新档或注入探针专用敌人。它是运行测试地图，还不是完整关卡。0.5保留RealisticVision、WallBlend效果与玩家已有设置；上述隔离验收使用本轮冻结兼容字节及同期其他模组发布组合。

0.4 修复部分墙边反复出现黑块：第二背景层此前漏减画面块原点，管道、栅栏等重复画到了各块相同位置。现在与其他世界图层使用一致的坐标换算。保留 0.3.1 的菜单暂停点击修复。过程、像素对照和性能限制见 [工厂接入记录](knowledge/experiments/factory-v04-20261015.md)。

## 独立试玩

双击本目录的 **[Start-Scene.cmd](Start-Scene.cmd)** 可打开旧版稀疏走廊，用于独立战斗回归；它与正式入口的工厂不同。完成启动与整图预绘后进入独立测试窗口，每次创建一局新的测试游戏。A/D移动、空格跳跃、鼠标左键攻击、R换弹、I打开物品栏，沿用原版操作。长走廊中放了三只原版鼠怪。关闭游戏窗口退出。

这是简化的运行测试场景：有长走廊、上层平台、竖向通道和混凝土破坏目标。独立试玩额外放置三只鼠怪；正式游戏入口不注入这组三只测试敌人。手动入口与自动测试共用独立应用身份，同一时间只开一个。

隔离产物位于 `build/runtime/`，测试存储为 `%APPDATA%/pfe-modsettings-continuous-scene/Local Store/`。自动验证不读写玩家正式存档；当前玩家游戏未被关闭。生产模组与测试驱动分离，测试驱动没有安装到正式加载清单。

## 现在做到哪里

一个扩大的 `Location`（原版的房间运行对象）承载整个场景。**进入时预绘整张地图，游玩中全部保留**；工厂的 240 个画面块只用于组织像素，没有内部房间切换，也不随镜头卸载。玩家、敌人、子弹和碰撞始终共用全场空间。地形与墙面覆盖层各自共用像素存储，局部弹痕只刷新附近块；原版存档保存地形变化和破坏痕迹。

原版敌人AI、子弹命中和碰撞方法继续执行。RV仅在需要判断可见单位时复制整图视野快照，同帧复用；0.5继续保留完整逻辑扫描，只减少重复取格和调用。实现边界见 [运行设计](design/runtime.md)。

0.5恢复原镜头快捷键的三档缩放，实际移动边界仍是全场景；背景和雾层按真实视口与倍率绘制。信息页地图按真实Location尺寸扩展，首次打开居中，后续保留原生拖动/缩放。源房间的底墙、色调和静态暗度按世界区域裁分到地形、水与弹痕，普通单位和箱子更新基础区域色，保留特殊变色。

开枪时按原生图形、缩放、旋转、滤镜及alpha恢复范围更新相交块，不再固定圈出大片区域。背景装饰在预绘前建立索引，宿主与WB复用相交列表。大场景的持续操作和Y补上与原生首次E一致的实体墙遮挡检查，保留telemaster且portOn的原生例外，Loot/comein仍需可见；普通房间规则保持。原生输入与弹痕像素门禁已通过；后者保留与世界大画布参考的两个世界像素差异，已逐像素证明等于独立原生局部绘制，并非宣称整图完全一致。

正式性能首轮中，工厂进入等待由旧基线约63秒降至25秒；开枪帧间隔中位/P95/最大为43.5/63/202ms（旧基线47/193/325ms），7发开枪最大只更新2块（原20块）。同轮普通房开枪为33/41/108ms。同字节独占复测进入等待约28秒，开枪37/52/154ms，仍为7发、最多2块；首轮完整保留。仍有偶发长帧，首轮关闭RV/WB的诊断阶段也出现313ms尖峰，原因尚未完全分离。两轮进程峰值Private/WorkingSet分别3031/2966MB、2709/2634MB，均高于旧基线2505/2440MB；没有内存降低的结论。随机内容不同，不是严格同种子A/B。

当前限制：

- 当前最终组合已经完成四套隔离验证，历史组合的通过仍不自动转移。所有门、升降台和随机敌人标记尚未逐项验收；联机、更大地图与长时间游玩未验收。
- 两轮独占无计时插桩短测已完成，均有残余长帧，不宣称稳定30帧。历史走廊、工厂与profile阶段数字保留在各调查记录，不用旧走廊成绩或AS3结束时内存代替0.5实际体验与进程峰值。
- 全场景格子、实体和地形画面常驻；尚未做远处实体休眠或场景数据按需读盘。
- 支线后房、跨层剧情及原随机工厂生成器未整体移植。allon/alloff保留单一Location全场供电/断电，防止区域静态样式覆盖动态开关；本轮14项实测通过，未设计十二份独立电路。
- 普通单位基础色更新不覆盖魔法武器、影子或特殊变色；UnitMerc的独立arm附件未另加接点。
- 存读档沿用原版检查点语义；本版补齐大场景地形破坏与弹痕的跨读档保留，并验证新旧存档交替加载。
- SATS常驻画面覆盖已通过本轮Lab；完整战术操作、任意水体变化、动态门、剧情、所有武器和不同窗口尺寸未逐项验收。RV42项与WB三组局部回归另有证据，不能代替真实组合和安装后原生启动。
- 地图编辑器暂缓。`build/factory_scene.py` 从原版 `Rooms/rooms_plant.xml` 生成工厂，原始房间文件只读；测试夹具 `scene-factory.xml` / `scene-lab.xml` 可再生，不能手工编辑后当作正源。

## 构建与自动验证

在游戏根目录的 PowerShell 执行：

```powershell
& './mods/ContinuousScene/build/build.ps1' -BaseHost './pfe_before_ContinuousScene_20261014-181702.swf'
& './mods/ContinuousScene/build/test-mods.ps1' -AllMods
& './mods/ContinuousScene/build/compat-build.ps1'
& './mods/ContinuousScene/build/test.ps1' -Factory -Experience -HighQoS -EvidenceName 'my-experience-run' -TimeoutSeconds 650
& './mods/ContinuousScene/build/test.ps1' -Factory -Perf -HighQoS -EvidenceName 'my-perf-run' -TimeoutSeconds 650
& './mods/ContinuousScene/build/test.ps1' -Factory -HighQoS -EvidenceName 'my-factory-run' -TimeoutSeconds 650
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' './mods/ContinuousScene/build/verify_factory.py' 'my-factory-run'
& './mods/ContinuousScene/build/test.ps1' -HighQoS -EvidenceName 'my-lab-run' -TimeoutSeconds 650
```

`-Factory`检查工厂，否则使用旧走廊；`-Experience`检查原生与大图体验，`-Perf`采集真实帧间隔。性能测试独占运行，不与构建或其他测试并行。正式Lab必须跑完整模式；`-Quick`会跳过长距离往返，仅用于开发短测，`-Streaming`仅作旧策略对照。`-HighQoS`只固定自有测试进程策略，不修改系统电源计划或玩家进程。使用新证据名，不覆盖旧失败。弹痕像素探针只在最后执行后退出，不能随后存档或重绘。

`test-mods.ps1 -AllMods`先复制当前依赖，再运行`compat-build.ps1`生成RV/WB候选。之后仅更新清单用`-AllMods -Prepared`保留兼容候选；依赖发布变化时可用`-RefreshModules`指定刷新并重测，避免复制正式旧版覆盖候选。

只改外部驱动用`build/build.ps1 -ProbeOnly`；只编入口与驱动用`-DriverOnly`。完整构建的`-BaseHost`必须是`C631CBF3…C64867`原源码基线，最终合并另固定为已发布RConnect Map1宿主`BEBEEA8B…4011F`，保留Land新增字段与种子构造流程，不能拿当前根宿主重复套补丁。Grafon整类重编译，其余通过官方FFDec `-replace`移植十个方法；当前审计保留4659个其他具名方法/初始化，并核对Map1 Land布局。MainFE清单加载器保持。方法列表见运行设计。

RV冻结发布源commit为`0735491e49d0d286ea8847017ae2fb64067a3c71`，WB为已发布0.5.3的`f32e4a99643ccc901dc4f8e8caac29a6cde441b4`；兼容候选仅生成在CS的`build/generated/rv-production`、`wb-production`，不发布其他任务WIP。`compat-build.ps1 -Profile`仅诊断使用，最终测试和部署必须重新生成无插桩候选。

## 安装与回退

0.5门禁位于`build/upgrade-v05.ps1`，Check已632/632通过；2026-10-15 16:18安装根宿主、CS入口、RV兼容、WB兼容四项。回执为`build/upgrade-v05-receipt.json`，安装前备份位于`build/backups/upgrade-v05-20261015-161817307-8a1b6645`。工厂XML、共享清单、配置、其他模组与玩家存档保持。安装后用正式路径和独立AIR应用身份完成原生启动验证15/15，无未捕获错误；该检查只覆盖启动与加载链，进图、按钮及玩法由同产物指纹的四套隔离回归覆盖。证据为[InstalledSmoke.json](knowledge/experiments/evidence/pfe-modsettings-continuous-installed-20261015161849/InstalledSmoke.json)。安装或回退后须正常重启。

旧0.3/0.4回执仅作历史。当前宿主含Map1，WB已发布0.5.3，RC/MSW还有后续独立更新；**不要执行旧整体回退或以旧备份覆盖当前组合**。0.5回退须依据本轮安装前备份，只恢复这次实际替换且未被外部再改动的四项。

发布前跑候选完整生命周期、原版绘制对照及视觉模组混装检查，安装后再用正式路径原生启动验证。脚本遇当前宿主或其他模组字节变化会停止，需要核对并重跑受影响组合，不使用旧产物覆盖他人的新版本。

当前工具位于 `mods/Sandevistan/build/tools/`，仅作为共享只读工具链使用；Java 与 Python 路径可通过构建脚本参数覆盖。构建输出和游戏资源副本不入 Git。当前版本仅匹配 2026-10-14 核对的 1.02 宿主，Steam 更新后须重新调查和适配。
