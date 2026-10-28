# 当前正式依赖下复用真实战斗镜头对照

静音后继已接入：真正创建AIR前，只为新唯一ID预置原生Snd三项音量0；不覆写任何已有配置，结束回读留存config.sol。原始36字节文件、独立AMF3样本和路径拒绝检查通过，新增种子99字节。该方式仅覆盖原生Snd；没有运行时SoundMixer回读，也不能保证模组绕过Snd直接播放的声音。新prepared包含silence.py；仍须满足游戏内存预检才启动。

仅诊断，未构建新SWF、未运行游戏、未部署。新目录保存后继脚本与回执；旧camera配方、源、编译回执和失败证据不改。

已核对2026-10-28正式CS 0.9.1部署，接受宿主4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75、CS 9A5E24E13AF2E2E211FAEAC038697D2CA2641CD6482766048BC3B9B4A506AA31；RC2C49/RV638E/Loader2050保持。早先准备按A796/7F1F拒绝并发部署，未写prepared.json；本版本在核对部署回执、构建记录和入口后显式接续。新正式版本保留，不回滚。

复用`scene-compat-20261024/camera`已实测的FA2B76CB探针原字节。原始编译回执位于`probe-builds/probe-source/8b7d7fa161524450a7cb2ee803a0460b/probe-build.json`，回执SHA为E10693B0，探针完整SHA为FA2B76CBCF4C5029E006B835C99F3EB67B3B4EA5FD03AC736E37AE4E79BC1B22。

## 负载和镜头

- 原六名LMG敌人、玩家ASSR、真实方向键与Shift、双方原生开火和子弹；自然敌人保留。`fixedEnemies`只指定一次创建的六敌，不冻结AI；不启用`localEnemies`。
- 四段各300间隔：跟随、固定、固定、跟随。`SceneCombatCameraHoldProbe.beginWindow`只切换`cam.moved`；`sample`逐帧核世界活动、镜头实际坐标、玩家/六敌身体与平台均在视口内；`clear`只恢复moved。不写角色位置/速度，不暂停World或时间轴。
- `drawControl=rcnative`在冻结探针中是原生空控制；`nativeCaseMoving`四段都返回true，不按旧enemy-idle名称停下玩家。合图、隐藏层、RC诊断API均不启用。
- 默认RV、LightAndDarkness、WallBlend关闭，正式当前SWF仍原字节装入隔离副本。暂不提供RV开关，避免把未审核的配置塞入本轮；后续RV兼容另建明确后继。
- 原诊断夹具仍有敌人耐久生命/伤害2、玩家godMode及补弹/耐久；不是普通难度验收。保留冲刺、惯性、碰撞、击退、换弹和每帧并发弹体。

## 来源差异与复用资格

| 输入 | 原FA2B编译/实测依赖 | 本次运行要求 |
|---|---|---|
| 宿主 | ABE2B65E | 4E5FAB45（A796上新增alicorn五方法） |
| CS | 7F1F2961 | 9A5E24E1（0.9.1） |
| RC | DF0FA0E2 | 2C49DFD0 |
| RV | 0DBE0D7A | 638E2D40（本轮禁用） |
| ModLoader | BD71B6F3 | 2050E023 |
| 登记器 | 58DB3A59 | E3E43581 |
| 启动器 | 628FFED8 | ECE3ED08，资源模块86D5F280 |

`verify_reuse.py`先调用未修改的原`camera.verify_probe`及其`base.verify_probe`，参数为原回执自己的编译输入。随后单独核当前文件，历史runner输入仅允许上表两项准确工具变更；不是把旧编译回执改成当前组合。

FA2B的86源与10/25历史29AF种子的85源仅四个文件不同：测试主程序、SceneRasterPresentation、SceneEncounter、FA2B独有的镜头helper。82个共同源摘要一致，包括当时的产品ContinuousSceneMod、NativeSceneActivity、NativeSceneAdapter及补丁模板。这不表示0.9.1产品未变。SceneEncounter的已知差异是六LMG/六SMG10；本轮保留六LMG，不与SMG历史绝对时间混算。两种合图类均未在rcnative计时路径启用；仅有未使用对象初始化，不能把这个对照称为无探针生产基线。

0.9.1兼容依据：部署回执2B2CBB6A、构建记录9575560C、宿主审计73AB8EDA及31项实测摘要971B6933全部固定完整摘要。审计记录宿主只改UnitAlicorn五方法，其他5766方法、类布局、旧常量、其他标签不变；构建记录的NativeSceneActivity/Adapter/Walls与FA2B冻结源相同，ContinuousSceneMod与新增SceneAlicornAlerts是明确的新变化。不读取正在并发编辑的生产源码。

FA2B入口为ProbeDoc→MotionMod→Probe.init→MotionProbe，读取当前`ContinuousSceneCarrier.nativeAPI`，不初始化旧ContinuousSceneMod。原执行器从正式release复制9A5E，FA2B仅替换隔离副本的ContinuousSceneMotionMod。已完成的一次只读解压字符串核对显示FA2B不含NativeSceneAdapter/NativeSceneActivity/ContinuousSceneDoc，而9A5E含这些及SceneAlicornAlerts；后续DoABC类标签枚举被PreToolUse保护拒绝，未重试或改途径。原字节与入口证据用于复用判断，未伪造完整类枚举证明。旧探针不设置alicorn选项；独立存储沿新版默认0%，六普通LMG敌人不构成alicorn功能验收。

所有526当前正式输入、13个AIR运行输入、历史输入的实际当前摘要和本目录四文件摘要保存到新的`prepared.json`，与历史正式输入的每项差异也完整列出。执行前后必须精确匹配；未解释的历史编译/源文件变化立即拒绝。

## 执行入口

先在本目录执行`verify_reuse.py --prepare`，只读核对并写本目录prepared.json，不启动AIR或编译。随后由根代理review后执行`run.py --name camera-live-current-20261028-r1 --registry-wait 300`。执行后用`verify_run.py camera-live-current-20261028-r1`独立复核。Python使用工作区现有绑定运行时；无`--compile-probe`入口。当前尚未生成prepared.json；默认静音正在由根代理另一审查线核对，必须完成后再实际AIR，不能沿用历史运行推定已经静音。

运行器沿现有共享game登记、当前私有桌面启动器、唯一AIR ID和隔离存储，不操作玩家。准备前、AIR前及实际创建边界均要求可用提交4GiB/物理2GiB；沿原执行器保留运行中512MiB提交中止线和仅结束自己句柄。核启动策略requested=test、设置及回读errors为空、CPU普通优先级32、内存优先级5、highQoS已回读；没有新增全局CPU查询。现有执行器只读自有句柄的CPU样本保留，不能当主线程或GPU耗时。

## 验证与限制

完整1200个连续间隔、所有长帧和切换成本保留。沿原火力、原生冲刺、多弹体、视口和缓存稳定守卫；另分别确认固定/跟随两臂都有敌人移动、真实冲刺、敌我飞行子弹。原30帧火力摘要漏首间隔的字段保留历史含义，新`complete30FrameFireWindows`用上一窗末累计值精确重建，并要求总数与每段一致。

独立验证要求原始raw.ok=true、error为空、原断言全通过；只有一个loader会话，全部选择模块加载成功且显式包含当前CS与Motion探针；证据目录与本目录均无runner-failure。任何一项失败均保留失败，不输出成功摘要。

镜头固定会改变可见范围相关活动和瞄准/声音环境；两臂实际开火、移动与弹体必须并列解释，不能把全部差额归GPU。`stagePriorityBand`是混合ENTER_FRAME带，不称精确World.step。原预备会同步常驻沿途与原视口图块（旧轮177块、约13.7s）；本轮记录实际数量与准备耗时，不算加载改善或天然探索。计时期间缓存变化/越界/抖动保留失败，不改守卫或拉回角色。当前方案不覆盖自然跳跃、完整RV组合、长距离探索，也未新增具体原生方法计时。

## 本次离线检查

三个Python文件AST解析通过。原FA2B文件和E10693B0回执实算匹配；原camera/base验证器及86源检查通过，与29AF的82个共同源和四项明确差异通过。新增0.9.1兼容门通过：当前526正式输入与13运行库已核；相对原编译正式输入有6项差异，按prepared.json完整记录。执行器未运行、没有新AIR或编译进程。

新`summarize`只读重算旧`camera-combat-20261024-r1/storage/result.json`通过：完整1200间隔、固定/跟随各600、40个完整30帧火力窗守恒；两臂均观察到敌人移动、玩家原生冲刺和敌我飞行弹体。旧历史原值保持，包括跟随122.18ms/固定92.735ms及4060ms尖峰；此离线校验不是当前组合的新性能结果。
