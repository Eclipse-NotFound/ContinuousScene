## 2026-11-04 — 剔除包围盒解析式缩放（event-tracked-2）：离线 45/45，已随瞄准 V3 合并构建上线

- 用户要求按方案实施"首次接近敌人卡顿"优化。调查先把前提纠正：敌人在进图时由 `Location.setObjects → createUnit → Unit.create`（`initBlit` 取共享 SpriteSheet、`Weapon.create`、`addVisual`）全量实例化，走近不构造实体、不拆 SWF；音乐/音效在启动时 `initSnd/loadMusic` 全量预加载且只在 `bytesLoaded==bytesTotal` 时播放。实机 1300 帧证据（`knowledge/experiments/evidence/bulletgrid-gridlive-combat-n1`）：`woke` 最大 1/帧（预算生效）、`activityMs` 均值 0.538ms、`boundsReads` 25–55 无交战尖峰、15 个 ≥90ms 长帧的 `activityMs` 0–2ms。长帧仍与 >1MB 内存回落同帧（地块分配推动回收）——**"首次加载敌人"不成立**，原方案里的"唤醒强弱分级/预算收紧"因此不做（与 `alicorn4` 既有计数一致）。
- 实际落地的是可证等价的那一项：`SceneObjectCulling` 缓存"单位缩放局部盒"，纯缩放（`rotation==0`、非零有限）时用算术映射替代每帧 `getBounds`；每帧只摊销重测 1 个条目（**不写 `e.x/e.y`**，避免同帧移动被跳过）；主循环 `for each`→下标 `for`；`stats()` 升 `event-tracked-2` 并加 `scaleSkips`/`baseRefreshes`。
- 验证：独立 AIR（`remains.cs.cullchecks.*`，无游戏/存档）**45/45** = 既有 `SceneCullingChecks` 23/23 回归 + 新 `SceneCullingScaleChecks` 22/22 差分（oracle 每帧 `getBounds` 逐帧逐根比对，覆盖镜像/旋转回落/零轴/同帧传送/美术变化后扫刷新/空根/unitsOnly 切换）。合成场景 1897 次变换 → 920 次算术、`getBounds` 4.36/帧（旧实现 ≈21/帧），不一致 0。
- 产物：`build/generated/cull-scale-20261104/product/ContinuousSceneMod.swf` = **`6A538E83…`**（33175 B，13 类，无 tests/Checks/Probe 泄漏，字节码含 `applyScale`/`refreshBase`/`event-tracked-2`）。归因：把并行瞄准 V3 会话的 3 个文件钉 HEAD 编控制产品 `E6567000…`，逐类导出只差 `SceneCullEntry`+`SceneObjectCulling`；本地管线对已部署 `D04CD26A` 的 7 个抽查类导出完全一致（同 32677 B）。
- **部署结果（本轮收尾核对）**：用户选择"等瞄准 V3 收尾后合并一次部署"。并行会话 23:22 把 CS 0.9.10 部署为 **`A4F4C8ED`**（前值 `D04CD26A`，备份 `build/backups/ContinuousSceneMod-0.9.9-D04CD26A-before-aimv3-20261104-232209.swf`）。从**已部署字节**导出 `SceneObjectCulling`=`F59A2915…`、`SceneCullEntry`=`CDCB935B…`，与通过 45/45 的候选 `6A538E83…` 的两个类**逐字节相同**（0.9.9 的同两类是 `B14DDD97…`/`7B9729CB…`）→ 线上代码就是被验过的代码。源码哈希链闭合（夹具冻结副本 = 产品输入：`B62731BA…`/`ACC0753E…`）。核验回执 `state/culling-scale-verification-20261104.json`；**需重启游戏生效**。
- **环境漂移**：共享 Flex SDK 缺 `frameworks/localFonts.ser`，编译统一加 `-theme=` + `-compiler.fonts.local-fonts-snapshot=`（同 ConditionSystem 做法），未改共享工具目录。报告 `knowledge/experiments/culling-scale-20261104.md`。

## 2026-11-04 — 瞄准注视模式 V3 优化方案成文（脱离修复、连续平滑距离反馈、平行双模）

- 用户实测反馈 3 项核心问题：①按 Alt 导致鼠标脱离游戏，需左键单击一次才能返回；②注视模式移动不平滑，无法建立"鼠标越靠近屏幕边缘看越远"的反馈；③要求保留 0.9.8 的"按住 Alt 注视"作为平行模式。
- **深度调查与根因**：
  1. **按 Alt 鼠标脱离**：Win32 窗口体系中单发 Alt（`VK_MENU`，keyCode 18）为激活系统菜单的全局快捷键（`WM_SYSCOMMAND / SC_KEYMENU`），激活后 Win32 窗口强制解除鼠标捕获（Mouse Capture Lost），进入菜单导航状态，必须点击客户区窗口才能退出并恢复焦点；`SceneAimController` 监听 `KeyboardEvent` 时**从未调用 `preventDefault()`**，导致击键原封不动透传至操作系统底层的 Win32 消息循环；原版 Remains 的 44 个键位完全规避了单发裸 Alt。
  2. **缺少越靠边越看越远反馈与移动不平滑**：0.9.9 边缘 90px 停留 3 帧硬锚定走向极端二值化（中心 80% 区域目标恒为 0，触边 3 帧突然锁死在 700px），彻底切断了连续控制感知；0.9.8 移回视野射击回缩的本质是屏幕坐标与世界坐标的代数环；正解不是硬锁死，而是**连续平滑非线性距离映射（$S(u) = u^{1.25}$，死区 70px）+ 不对称阻尼 / 软滞后保持（Soft Retention）**，外推敏捷（$0.24\text{s}$），瞄准微调同侧高阻尼保持（$0.8\text{s}$），主动拉回中心才回弹（$0.20\text{s}$ 单调无过冲）。
  3. **长按与切换平行模式**：长按（Hold，0.9.8 升级版）具备即时松手回弹的安全感，适合遭遇战快速索敌；切换（Toggle，0.9.9 演进版）解放左手，适合大场景长途行军；两者确立为平行模式，并扩展智能混合模式（Smart，短按切换/长按松开即回），设置项平级可选，偏好向下兼容。
- 完全继承 0.9.9 验证通过的 `syncViewport()`（`Grafon.sceneTick`）视口同步机制（远端墙体 100% 渲染与表面可见）与 `(cursor - vx) / scale` 逐像素渲染恒等式。
- 方案文件定稿于 `design/aim-look-v3-dual-mode-and-input-smoothness-plan.md`。

## 2026-11-04 — 交战卡顿：子弹空间分桶落地（宿主 1D2004AB → 91F8E10D）

- 按方案 C1 实施：删除 `Grafon.sceneTick` 写 / `Bullet.run` 读 `World.w.visual.root["sceneCU"]` 的密封类异常通道，改为每帧整房间 512px 分桶表（存 `World.w.vgui`，`Sprite` 密封不能用），子弹按自身坐标查桶；三道回落闸（targetObj / 单位数变动 / 玩家位移 >256px）。只改 `fe.graph.Grafon::sceneTick` + `fe.weapon.Bullet::run`，类布局不变。
- 离线：16,009 探针点 0 不一致（含一帧陈旧与建表后新增单位）；成本 1.34 → 0.47 ms/帧（40 弹×130 单位）。
- 游戏内 3 次 1300 样本 / 13 检查全通过：分桶 1300/1300 帧生效，单位 122 → 候选 2.7；clean↔clean 对照均值 −0.60ms（候选臂在飞弹更多），第三轮 −2.96ms；**不主张整帧收益**。
- 部署 `pfe.swf` → `91F8E10D`，备份 `build/backups/pfe_before_bulletgrid_20261104-185052.swf`，回执 `build/generated/combat-collision-20261104/deploy-receipt-grid-clean.json`，装后冒烟 5/5。
- 部署后用 0.9.9 自己的 `AimProbe` 实机夹具验证平移互操作：**14/14 通过**（`viewportSyncs` 239/444、`resident 70→110`、`world-map-exact bad 0`、`apply-consistent bad 0`）。同毫秒去重候选 `grid-probe`/`grid-clean-guard` 已建**不部署**（第二次 `sceneTick` 在模组 ENTER_FRAME、晚于游戏 step，`getTimer()` 同毫秒几乎不成立）。
- 按既有证据不做 C2/C3/E1/E2/E3（理由见报告 §8）。陷阱：`decal-nocancel-v2` 诊断宿主两次跑挂；`Sprite` 密封（`#1056`）差点让 `sceneTick` 每帧抛错，被离线探针挡下。
- 过程：`knowledge/experiments/evidence/` 曾被外部清理删除 789 个已跟踪文件，已 `git checkout` 全量恢复；本轮未跟踪的原始 result 目录无法找回（数字在报告、矩阵可重跑）。认领锁被"活着但空闲"的会话钉死，处置阶梯记在 `knowledge/discoveries/file-claim-lock-deadlock-20261104.md`。
- 报告 `knowledge/experiments/bullet-collision-20261104.md`；方案实施状态见 `design/exploration-and-combat-stutter-optimization-plan-20261104.md`。

## 2026-11-04 — 已部署 CS 0.9.9：边缘锚定瞄准、临界阻尼平移、平移视口重确保

- 按 `design/aim-look-and-offscreen-combat-optimization-plan.md` 实施并部署。正式 CS release **285625F4（0.9.8）→ D04CD26A（0.9.9）**；宿主 `1D2004AB`、`scene.xml` `1CEA74E2` 未动；需重启游戏生效。回退=备份 `build/backups/ContinuousSceneMod-0.9.8-285625F4-before-aimv2-20261104-184530.swf`；回执 `state/aim-look-v2-deployment-20261104.json`。工作根 `build/generated/aimv2-20261104/`。
- **远端墙体不加载**：确认是"平移后没有重跑视口确保/裁剪"。宿主 `Camera.calc` 用**未平移**的 `cam.vx` 调 `sceneTick`（ensure+cull），模组随后才平移，且从不补跑；下一帧原生又把 `vx` 写回玩家中心。修法：`apply()` 末尾调 public 的 `w.grafon.sceneTick()`，让它用平移后的 `cam.vx` 重新 ensure + cull（private 的 `sceneEnsure`/`sceneCullSurfaces` 不能直调）。复核部署版 `sceneEnsureUpcoming` 后确认它**没有逐出逻辑**，因此不存在"模组补画后被原生逐出"的抖动，问题只是视口用错。实机证据：平移后 `sceneResident 70 → 109`，`panned-view-resident` 通过。
- **镜头急促**：旧一阶 lerp 首帧兑现全部误差（≈154px），再被 `MAX_STEP=50` 切成匀速硬冲。改为按帧固定 `dt=1/30` 的临界阻尼积分（推进 0.40/0.26/0.17、回中 0.30/0.20/0.13，速度上限 700/1000/1400 px/s，`MAX_STEP=90` 仅安全网）。实测首帧 ≈20px、峰值 ≈49px、零过冲、回中单调。
- **注视与移动/射击解耦**：旧模型 pan 随准星到屏幕中心的距离变化，准星移回视野打敌人时镜头必然缩回。改为**边缘锚定**：准星压住屏幕边缘带（90px）停留 3 帧即锁定方向与距离，之后准星在延展视野内任意位置瞄准射击都不缩回；压另一条边缘重锚。停留计时**跨"视野内移动"累计**，只有回中或换边才复位——这同时让隔离探针（自备光标）与入口自身调用（真实光标）不会互相清零。默认改为**切换模式**（按一次进、再按一次退），左手解放；旧偏好文件无 `aimVersion` 时迁移一次到新默认。
- **顺带修正两处既有缺陷**：①`cam.celX` 预移（供下帧原生 `(celX-vx)/scale`）本身正确，但 0.9.8 又用**已平移**的 `vx` 算本帧 `w.celX`，等于把 pan 算两遍；统一为 `w.celX=(cam.celX-nativeVx)/scale`，与渲染恒等式 `(cursor-vx)/scale` 一致（实机 `world-map-exact` 0 违例）。②同帧二次 `update()` 会叠加平移，加"识别自己上一笔写入"的基准保护。
- **验证**：确定性夹具 `src/tests/SceneAimChecks.as` 重写后 **61/61**（独立 AIR `remains.cs.aimchecks`，无游戏无存档）；隔离实机（私有桌面、独立 AIR id、正式 13 模组 + 探针、候选 CS + 候选宿主）**14/14**。实机私有桌面把真实光标固定在 (0,0)（左边缘带），因此走"被动驱动"腿；主动重锚腿只在自备光标模式跑，重锚本身由确定性夹具覆盖。
- **宿主候选已备未部署**：`noscenecu/candidate.swf` = **9FAB2AEF**（删 `Grafon.sceneTick` 的 `sceneCU` 建表 + `Bullet.run` 的读取）。先建 `control`（仅 decal 免取消）**逐字节复现 1D2004AB**，证明谱系与"只改 3 个方法、类布局不变"。**未部署**：另一会话（`combat-collision-20261104`）同时在造 `scu-remove-clean` 与子弹空间网格，覆盖同一宿主改动；避免同时替换 `pfe.swf` 互相回退。部署命令见 `deploy_host_noscenecu.py`。
- **未完成**：玩家主观手感验收；武器倍镜联动、受击回中。

## 2026-11-04 — 瞄准远端墙体加载、镜头动力学、移动射击解耦与屏外命中优化方案成文

- 完成针对瞄准模式（Aim-Look）远端墙体加载、镜头移动平滑度、移动射击解耦交互及屏幕外命中保障的全面系统性调查，定稿优化设计文件：`design/aim-look-and-offscreen-combat-optimization-plan.md`。
- **调查关键发现与根因确证**：
  1. **远端墙体不加载**：时序倒置缺陷。宿主在每帧原生主循环 `Camera.calc` 中以未偏移的玩家中心坐标调用 `Grafon.sceneTick`（触发 `sceneEnsure` 与 `sceneCullSurfaces`）；模组 `SceneAimController` 在其后的 ENTER_FRAME -200 注入最多 700px 镜头平移但未更新宿主视口，下一帧又被原生覆写。远端区块因此未加载，或被表面裁剪判定出屏设为不可见，造成空洞。
  2. **镜头移动急促顿挫**：动力学物理缺陷。一阶线性 lerp（`k=0.22`）使第 1 帧瞬时速度达峰值 154px/frame（加速度无限大），被 `MAX_STEP=50` 截断产生 1500px/s 匀速冲击，缺少加减速 S 曲线与速度连续性。
  3. **注视远处与射击移动冲突**：输入绑定死锁。镜头偏移量被绑定为鼠标距屏幕中心的绝对距离；玩家为了开火将鼠标移向敌人时，鼠标靠近中心导致镜头骤然回缩丢失目标；移动时鼠标晃荡拉扯视野；长按 Alt 占用拇指受制于系统键。
  4. **屏幕外命中支持机制**：原版 `Bullet.run` 天然支持屏外 AABB 碰撞；历史补丁试图按相机视口筛选单位（`sceneCU`）严重破坏了屏外命中，虽因 MainFE #1069 侥幸回退但留下每发异常；实体调度休眠需要与弹道走廊（Threat Corridor）协同穿透。
- **方案架构**：
  - 视口确保：`SceneAimController.apply` 写入位移后主动驱动 `sceneEnsure` 与 `sceneCullSurfaces`，配置 320px 缓冲带杜绝黑边。
  - 动力学重构：升级为 `SmoothDamp` 临界阻尼平滑模型，实现有限加速度与自然 Ease-In-Out，单帧位移软约束。
  - 解耦交互：视线朝向向量锁定（Directional Look Anchor），鼠标在半球视野内作为自由准星射击不缩回；WASD 移动平滑跟随；支持切换（Toggle）模式。
  - 屏外战斗：彻底解耦子弹碰撞与摄像机视口，清理 #1069 异常路径，维护弹道威胁走廊即时受击唤醒。
- 正式基线仍为宿主 1D2004AB、CS 0.9.8 `285625F4`、scene.xml 1CEA74E2，本轮只调查与成文，未改动生产产物。

## 2026-11-04 — 深入探索与全敌人交战卡顿深度调查与方案文件成文

- 完成针对深入探索与全敌人交战（各敌人类型通用）偶发卡顿的系统性调查，定稿优化方案：`design/exploration-and-combat-stutter-optimization-plan-20261104.md`。
- **调查关键发现与根因确证**：
  1. **探索卡顿**：长帧主体不在日常 CS 预热（日常 2~5ms 仅占 ~13.6%），而在两处硬阻塞：① 视口越界触发的强制同步补画（`sceneRender` 单次耗时 31–178ms，均值 68ms）；② 地块掩码单步（`drawKusok` 588 个掩码子节点构建，峰值 125ms）；地块常驻膨胀至 181 块(+343MB)抬升系统 GC 压力；简单 Cap 逐出已证明会因镜头跳变引起 568ms 补画风暴（负结果关闭）。
  2. **全敌人交战卡顿**：① 宿主 `sceneCU` 视口碰撞过滤实测因 `fe.MainFE` 为密封类而引发 `#1069` 运行时异常，每发子弹每帧抛异常 + 回退全量 130+ 单位遍历，造成 O(n²) 碰撞检测风暴（30~60 子弹 × 130 单位 = 3900~7800 次 AABB/帧，每敌人贡献 +1.5~2.0ms）；② `NativeSceneActivity` 的警报与索敌锁死使被共享目标的敌人被判定为 `combatSignal` 与 `urgent`，同 1 帧内绕过 `wakeBudget` 被成批唤醒，触发大量敌人并发步进、gotoAndStop 骨骼刷新和 DDA 穿墙视线检测；③ 拴绳在 2200×1600 边缘缺乏迟滞导致风筝时反复冻结/解冻振荡。
- **方案架构**：
  - 支柱 C（战斗）：C1 修复子弹空间分桶索引（消除 #1069 异常，O(n)→O(1)）+ C2 敌人唤醒信号强弱分级与平滑排队 + C3 双阈值脱战迟滞防抖。
  - 支柱 E（探索）：E1 动态自适应视口缓冲（Aim-Look 前馈预测消除视口 miss）+ E2 `drawKusok` 增量分步状态机（125ms 压平至 ≤25ms）。
- 正式基线仍为宿主 1D2004AB、CS 0.9.8 `285625F4`、scene.xml 1CEA74E2，本轮只调查与成文，未改动生产产物。

## 2026-11-04 — 证明策略实机接续：按需建表行为检查通过，收益未判定、不部署

- 同一0.9.8源闭包构建A/B最小候选，104项生成源核对；真实AIR原生大地图修正诊断28/28（含12夹具），1,075次读取边界/独立状态比较零差异。三动作各450帧，38项功能检查通过；q=0均0%，每帧仍建表。
- 有效性能配对0：旧同A字节对照初态/异步顺序/T负载/菜单显示条件不合格；修正对照启动前见其他AIR；共存三动作只作功能/分布观察。局部与整帧均未判定，不把操作计数当毫秒，不部署。
- 隔离冻结A9B39CC7，正式宿主另轮变更1D2004AB不混用；本轮未改正式核心、入口、CS release。旧失败、预热菜单、探针修正和未覆盖的全屏/新宿主均如实留存。本轮自有测试进程均结束，未动他人进程。
- 返回报告：[run-03/REPORT.md](D:/活/AI/测试运行/remains-proof-strategy-20261104/run-03/REPORT.md)；案例：[proof-activity-live-20261104.md](../knowledge/experiments/proof-activity-live-20261104.md)。接续先核对自然q=0价值与可重复初态，再考虑既定性能矩阵；未自动发往其他对话。

## 2026-11-04 — 逐出+复用实测为负结果（不部署）；B-P2 以计数证据关闭；宿主仍 1D2004AB

- 玩家 14:42 退出后抢到窗口：① 构建并实测逐出+复用候选 `cap-diag-v2`（9 方法，carrier 存池/上限，避开 sealed 类动态属性 #1069）；② 跑通天角兽 v3 计数探针。
- **逐出+复用负结果**：均值 41.8→39.9、P95 65→62，但**最大帧 171→568ms**、同步补画 22 次/1044ms→**30 次/1997ms**、驻留封顶 181→96、内存峰值 462→395MB。机制：**相机跳变那帧要同步补画被逐缺口**（568ms 落在 phase 45 换窗口 age=0，syncCount 跳 25）。**不部署**；更保守上限(160)只省 ~12% 分配，也不做。根治需异步补块+占位，另立项。
- **B-P2 关闭**：`alicorn4-alicorn-n1` 900 帧/14/14：faction-1 单位 50；带目标单位 1→最多 9（age≈100 起），唤醒按每帧 1 只、`awake` 28–43、整场帧时不抬升（前/后 100 帧 34.5/34.9ms），仅高活跃帧 +4.9ms。现状预算+leash 已够用 → **不做**。
- 正式栈：宿主 **1D2004AB**、CS 0.9.8、scene.xml 1CEA74E2 均未动；本轮候选全部 `deployed=false`。

## 2026-11-04 — 逐出+复用候选编码完成（dry-run 通过）；呈现层已含 evictions 钩子；玩家在游戏中未抢资源

- `patch_host.py` 增 `cap_patch`：`sceneDrop` 缓冲入池(≤8 块)、`sceneBeginWarm` 取池并清零、`sceneTick` 按离视口最远逐出到 `sceneChunkCap`（默认 96 块≈246MB）。dry-run 生成 `cap-dryrun.as`，3 方法改动、锚点唯一、语法待编译验证。
- **前置核对（重要）**：`src/SceneEventBitmapFill.as:64-66` 的失效条件本来就有 `evictions!=grafon.sceneEvictions`，`refreshBindings()` 从 `sceneSurfaces()` 整体重建并对消失位图 `restoreRecord` → 逐出是设计已留钩子的路径。
- 玩家 13:57 起在游戏中（窗口 Remains，写到玩家真实存储），**未做 FFDec 构建、未跑测试**；候选与验证命令已写入 MEMORY。方案 v2 顶端已加实施更新表。

## 2026-11-04 — 长帧归因反转：≥100ms 帧 85~100% 与 50~165MB 内存回落同帧；新候选=逐出+缓冲复用

- 用相位探针三次运行（探索/战斗/单天角兽）逐帧对照 `System.totalMemory` 与长帧：**11/13、12/13、3/3 的 ≥100ms 帧与 >1MB 回落同帧**，回落中位 50–72MB（最大 165MB），回落 >3MB 的帧平均 98–131ms；`resident` 同帧仍增长。
- 机制：每块 4×2.56MB、约 1.8 块/秒 ≈18MB/s 分配且**从不复用**（无逐出）→ AIR 每约 80 帧回收 50–165MB，把该帧拉到 100–171ms。此前“减分配≠减帧时”削的是小垃圾，不是这个量。
- 新候选（原 P3 换理由）：`sceneDrop` 入池(≤8 块) + `sceneBeginWarm` 从池取并清零 + `sceneTick` 按离视口最远逐出到上限 96 块（`World.w.visual.root["sceneChunkCap"]` 可运行时改）。**先验风险**：呈现层是否引用被逐缓冲、折返是否转同步补画。
- 报告 `knowledge/experiments/long-frame-memory-20261104.md`。天角兽 v3 计数运行仍被玩家游戏（13:57 启动，窗口名 Remains）占用，未跑；未动玩家进程。

## 2026-11-04 — 天角兽只读计数探针（B-P1）：工具就绪；首轮未见“警报拉活”

- 新探针 `alicorn-v3`（基于 cold-v2，原生生成一只 `UnitAlicorn("1",100,null,{tr:1})`，逐帧记 units/cel/f1/awake/asleep/leashed/filters/projectiles + 天角兽 mater/aiState/aiSpok/t_tele/teleObj）。首版因 `UnitPlayer.visBmp` #1069（密封类）丢整段计数，v3 改为逐项 try/catch。
- `alicorn2-alicorn-n1`（900 帧、14/14 检查）：均值 34.4ms、>100ms 仅 3 帧；`awake` 27–35、`asleep`→112，**900 帧唤醒 11 次、交战前 30 帧 0 次**，交战后帧时无持续抬升 → 本夹具**不支持** B1（成批拉活）。
- 未完成：v3 的 cel/awake 判别运行被另一会话持续占用 AIR 挡住（n1–n10 全失败），已停止重试、未动他人进程；真实对齐还需 `tr=2`（会 actPort）与更密的同阵营分布。
- 报告 `knowledge/experiments/alicorn-count-probe-20261104.md`。

## 2026-11-04 — 帧三分：CS 只占 7~15%，主项是渲染/调度窗口与游戏逻辑；用户三项决定落档

- 在相位探针数据上再拆一层：`dt` = CS 管线 + （501 处理器→下一帧 -1000 的窗口，记 R）+ 其余游戏逻辑。探索 1149 帧（mean 41.8ms）：**CS 5.67 / R 21.78 / 逻辑 14.37**；≥100ms 帧 13 个里 **CS 21% / R 61% / 逻辑 19%**。战斗 1299 帧（mean 41.4ms）：**CS 3.00 / R 20.53 / 逻辑 17.89**；≥100ms 帧里 **CS 8% / R 53% / 逻辑 39%**。
- **无效实验（勿引用）**：`--draw-control world` 想验证 R 桶，但相位探针不消费 `motion-controls.json`，世界层未被隐藏（40.6 vs 41.4 为噪声）。要做需先在探针内实现隐藏。
- **用户三项决定**：①大窗口/全屏（`scaleV=1`）→ 地形双线性作废（1:1 无重采样）；②不做 `zoom100`；③批准相位探针（已执行）。
- 结论：CS 侧低风险项到此为止（P2 已部署、P4/P1/P3 已按实测否定/降级）；继续改善必须转向 R 桶与游戏逻辑侧，已超出本模组范围。

## 2026-11-04 — 相位归因实测：CS 管线仅占长帧 1/5~1/3；部署「弹痕不再取消预热」（宿主 A9B3→1D2004AB）

- 用户指令"按方案进行优化"。先补上方案 P0 的测量盲区：把相位计时打进宿主补丁的 `Camera.calc→sceneTick` 内部（诊断宿主 `phase-v3`，7 个 Grafon 方法，类布局不变，不部署），探针逐帧取 `tick/ensure/warm/sync/cull/mark/beginWarm/missLoop/step` 快照，运行器手写隔离 manifest（启动器保存被沙箱命名互斥体拒绝）。
- **关键结果**：探索 1149 帧 CS 管线 **5.67ms/帧**（预热 4.97 为主），其它 36.2ms/帧；**≥100ms 帧 13 个里 CS 只占 20.6%，2/13 帧 CS 为零**。战斗 1299 帧 CS 3.00ms/帧，**≥100ms 帧 CS 仅 7.8%**。→ 长帧主体（≥2/3）在原生 step/渲染/调度，不在 CS；CS 的稳态成本是每帧 3~6ms 的预热税。
- **据实测否定的候选**（写进 MEMORY 防重提）：拆 `drawKusok`（`maxStepMs` 20–25ms，不是冷态曾见的 125ms）、弹痕空间索引（0.03ms/帧）、`sceneApply` 空间索引（5.9 万次相交）、`sceneApplyCompactDecal` 分配修正、压预热预算（实测自适应 2–25ms）。
- **已部署（P2）**：`Grafon.sceneApply` 对 `decal` 不再 `sceneCancelWarm`——新弹痕在取消前已入 `sceneMarks`，预热最后一步 `sceneRestoreMarks` 会重放。同调度 1300 帧：`cancelCount 10→0`、`cancelWork 302ms→0`、每块预热工时 45.6→43.3ms；清洁候选冒烟 1300 样本/13 项通过。宿主 **A9B39CC7 → 1D2004AB**，备份 `build/backups/pfe_before_decal_nocancel_20261104-133604.swf`，回执 `build/generated/opt-20261104/deploy-receipt.json`，**需重启**。
- **仍成立但未做**：驻留块无逐出（探索 38s `resident 47→181`≈+343MB，全图上限 ≈1.2GB）——要做就是"远处逐出+缓冲复用"，须用同一探针验证回头路不造同步风暴。天角兽 B-P2 仍缺只读计数证据；地形双线性只在 `scaleV≠1` 有意义，本轮窗口 `scaleV=1`。
- **过程失误（如实记录）**：手写 manifest 时误用了根目录真实 `application.xml`（`<id>pfe</id>`），导致一次运行写入玩家真实存储（模组日志与 `MSWConfig.sol`/`ModLoader.sol` 被重写；**存档与 `config.sol` 未动**）；已改为改写模板为 `pfe-modsettings-continuous-scene` 后重跑。另清理了本会话因低完整性启动被拒留下的一次 `needs-check` 租约。
- 报告 `knowledge/experiments/phase-attribution-implementation-20261104.md`；工具 `tools/stutter_host.py`(phase)、`build/generated/phase-20261104/{probe-v5,run_phase2.py,analyze_phase.py}`、`build/generated/opt-20261104/`。

## 2026-11-04 — 三项问题复核：三份只读深度调查 + 动态模糊离线微基准；v2 证据分级方案成文（旧方案多条断言被证伪）

- 用户委托"详细调查 + 可执行优化方案"（探索卡顿 / 单只天角兽交战卡顿 / 背景粗糙与动态模糊）。本轮**只调查与成文**：未改宿主、未改 release、未运行游戏；唯一新产物是离线微基准 SWF（`build/generated/filter-cost-20261104/`，不参与加载）。
- 产出：[v2 方案](../design/scene-combat-camera-optimization-plan-v2-20261104.md) + 四份证据（`knowledge/experiments/scene-combat-camera-investigation-20261104/`：探索链、天角兽、镜头视觉、微基准）。
- 关键新证据：①**测量盲区**——模组 ENTER_FRAME 计时不含宿主 `Camera.calc→sceneTick` 驱动的预绘/同步/剔除，故既往"CS 只占 6.4%"只是**下界**（43ms 同步补画那一帧 handler 只记 4ms）；②长帧块因是 `drawKusok` 不可中断单步（占 ≥8ms 单步 94%，峰值 125ms），**不是**滤镜（`applyFilter` 全程从未 ≥8ms）；③同步整块补画实测 **31–178ms/次**（旧估 25–45ms 偏低），但 29 次里 28 次在入口首屏；④无逐出、`resident=155`≈397MB、每发弹扫 118 块。
- 天角兽：旧方案四条根因全部降级（`findBox` 实际 0.05–0.6 次/秒、≤0.5ms/次；玩家被抓走 `levitFilter2→vis.osn.filters` 而非 `vis.filters`；`actPort` 每次 ≤12 次瓦片检查；alilight 约 90% 命中在 `sceneApply` 入口早退；`rapid=35` 实际 0.4–0.5 发/秒）。**唯一有量级的链条 = 警报/目标共享把同房（1920×1000）同阵营单位拉活**（每额外活跃单位 +1.5–2.0ms/帧，既有实测），默认接力 0% 只断多跳、不阻止首发直接通知。
- 镜头/模糊：**动态模糊实测否决**——最便宜单向 `BlurFilter` 15.5–19.5ms/次、挂世界容器 23–59ms（无滤镜 4.4–11.9ms），30fps 预算仅 33.3ms；`cacheAsBitmap` 反而更慢。粗糙来源须先分窗口：2048×1123 时 `cam.scaleV=1`（**无**最近邻重采样），1264×681 时 0.6583（开双线性 +3.9–7.2ms/帧，1:1 时零成本）。更正两处旧说法：0.6583 是镜头缩放非 stage 缩放；int 截断不致爬行、原版已有纵向缓动。
- 下一步（门禁式）：先做**相位归因探针**（sceneTick 内拆 ensure/advance/sync/cull + stepHist）与**只读天角兽计数探针**，再按证据决定是否实施 P1 拆 `drawKusok`/P2 弹痕不废预热/P4 分配修正/B-P2 弱信号走预算。**不再重提**预算钳制、对象池、弹痕 pending buffer、任何"减分配"式帧时手段。

## 2026-11-04 — 实现并部署瞄准模式（Aim-Look）：CS 0.9.8，真实相机平移验证通过

- 用户报告"视角固定居中导致大场景可视距离缩短"，初步设想按住某键 + 鼠标推移视角。机制调查：原版 `Camera.setLoc` 对单房间走 `moved=false`（镜头静止、一眼看到头），CS 大场景强制 `moved=true` 且 `vx=-X+screenX/2` 把玩家锁死屏幕中心，前方视野只剩半屏；原版 `keyLook`（分号键探头）键位反人类、无死区无平滑。设计并实现 `SceneAimController`（纯模组层，无宿主改动）：150px 死区 + ^1.4 幂律 + 横 700/纵 380px×幅度(50–150%) + 指数平滑三档 + 单帧 50px 硬限 + 世界边界钳制 + 七类互锁（SATS/覆盖层/Pip/剧情运镜/原版分号探头/控制台/失焦/非大场景）。
- 交互调查：裸修饰键（Alt/Ctrl）不可进 Loader keybind（`normalize` 明确排除 16/17/18/91-93），内建槽位用滑块（0=左Alt 1=左Ctrl 2=关）+ 可选自定义 keybind；鼠标侧键 AIR 不派发 X1/X2 事件，已从设计移除。瞄准精度：按**实际生效**平移量预移 `cam.celX/celY`，射击/拾取映射保持像素一致。
- **实机验证抓到真实产品缺陷**：`fe.inter.Camera.vx/vy/celX/celY` 声明为 `int`，写入分数平移被静默截断（0.4px），`visual/celX` 与 `cam.vx` 脱节（首测 402/201 帧）。修复=写后回读类型化值并以其为准；确定性假世界夹具（Number 语义）测不出，只有隔离实机暴露——已加 `tests/FakeIntCamera.as` 回归。首测的"钳制失败"反证世界边界钳制生效（工厂出生点在地图左上角）。
- 验证：确定性 **44/44**；隔离实机 **9/9**（正式 13 模组+测试探针、私有桌面/唯一 AIR ID；进工厂大图真实按 Alt：平移 616.8px、一致性 0 违例、松开归中、applied=224）。部署 release → **285625F4**（0.9.8），备份 `ContinuousSceneMod-0.9.7-447AE02B-before-aimlook-20261104-045116.swf`，回执 `state/aim-look-deployment-20261104.json`；宿主 A9B3 与 scene.xml 1CEA74E2 不动，重启生效。
- 过程：共享登记两条中间态记录已按协议核对恢复（首次启动前 HiddenProcess 参数错误、第二次等待期主动终止）；工具坑（HiddenProcess 需文件对象、Registration 异常留 needs-check、adl `System.exit` #2018）记入报告。未完成：玩家重启主观验收；武器倍镜联动/受击回中/边缘定位线留作后续。证据与复跑入口 `build/generated/aim-look-20261104/`、报告 `knowledge/experiments/aim-look-20261104.md`。


- 用户报告三项核心体验缺陷：①探索新场景偶发严重卡顿；②单只天角兽交战严重卡顿；③镜头移动背景粗糙（考虑引入动态模糊）。完成系统性排查与技术评估，定稿可执行方案 `design/scene-combat-camera-optimization-plan.md`。
- 根因定位（源码与机制级确证）：
  1. **探索新场景卡顿**：宿主 48ms 激进预绘与单步不可中断绘制，视口 miss 触发主线程全量同步补画（`sceneRender` 20~40ms 阻塞）；新区块大批量 `BitmapData` 分配撞上 AIR 阈值触发 Mark-Sweep 全量 GC 停顿（50~100ms）；移动开火相交取消预绘风暴。
  2. **单只天角兽交战卡顿**：`fe.unit.UnitAlicorn.findBox` 在连续大场景中对全图 1200+ 个物体线性全量遍历，并高频对候选物体执行昂贵的 DDA 穿墙射线检测（`loc.isLine`）；念力抓取给物体挂 `GlowFilter` 导致 AIR 软光栅管线每帧全向发光重绘；闪电武器 `destroy='50'` 破坏墙面频繁触发背景同步重绘（`drawKusok`）；`actPort` 20 次大跨度盲测 `collisionAll`。
  3. **镜头移动背景粗糙与动态模糊评估**：人眼对 30fps 低采样率高对比度纹理移动产生生理频闪与锯齿阶梯感；地块位图 `smoothing=false`（近邻采样）与 `pixelSnapping=auto` 导致像素离散硬跳变；Camera 坐标强制 `int` 截断且硬跟随无阻尼。**评估彻底否定在 CPU 渲染管线下引入全屏动态模糊**（原生 `BlurFilter` 耗时 35~85ms 导致掉到 8~12fps 幻灯片，全屏残影 Buffer 耗时 10~18ms 且拖脏 UI/准星）。
- 提出高画质极低开销方案：①自适应动态余量预绘（2~12ms）+ 非破坏性弹痕缓冲 + 地块位图池化复用；②天角兽 `findBox` 空间网格二分裁剪（1200+→<20 个）+ 念力发光改用 `colorTransform` 染色 + 闪电微损增量保护；③背景位图全面开启双线性采样（`smoothing=true`, `pixelSnapping=never`）+ Camera 解除 `int` 截断支持浮点亚像素平移 + 微阻尼跟随。

## 2026-11-04 — GC 组合治理终局：部署侧由维护者完成；env 泵候选干净负载四轮配对零收益正式关闭

- 用户指令"先做 GC 周期回收的组合治理"。核实组合部署侧：FA 已自行修复部署（bb6b3ac 0.4.1，~393/帧→0），叠加 ConditionSystem 与 RConnect gcfit1，三大外部泵全消。
- 029DAF34 四轮配对（干净负载、当前栈全量再基线、base,cand,cand,base）：GC 掉落 16 vs 15、体积 −1.9%，帧指标无一致方向——第四次确证"减分配≠减帧时"，不部署，候选保留。
- 当前栈归因：env 泵仍第一分配源但消除不动周期；UnitTurret/FocusManager 显示链为最大留存增长；29 个长帧仅 9 个邻近 GC。**长帧主体不是 GC，分配削减路线关闭**；后续需新证据/新路线。
- 过程：Stellaris/WizTree 会话两次触发内存守卫自停（未动用户进程）；v14 探针完整性检查放宽到 AS 源+SWF 哈希（分析脚本不进 SWF）；编排器 bug 当场修复。报告 `gc-combo-current-20261104.md`。

## 2026-11-04 — 因果分析推翻 Phase 2/3a 立项依据；低负载复测被用户 Stellaris 占内存阻挡，重试进行中

- 对 cold-r3 的 196 个诊断事件逐条配对（cx/cy/时间戳）：**29 次同步补画 0 次与取消同块**——Phase 2（弹痕不废预绘）无因果支撑，降级缓办；28 次是入口冷启动填充爆发（1.9s 扫完初始视口，真实游玩被载入遮蔽）；行进中仅 1 次同步补画，预绘跟得上；行进长帧来自不可中断单步（max 125ms）。
- 读源码复核 Phase 3a：`budget=max(2,min(48,ceil(mean×demand×1.35)))` 已按需缩放、warm 实测仅 71ms/s（2.4ms/帧），无堆叠；余量强钳制会在高 demand 平移时饿死预绘、反造 68ms/次同步补画。**判定不实施**，除非低负载复测给出相反证据。
- 低负载尾部复测由"等内存"带界重试完成（fwd-r3 02:24、rev-r3 02:29；r2 被运行中守卫正确中止，用户 Stellaris 占 7.6GiB 提交，不动用户进程）。**五轮配对合并终局**：CS 局部 5/5 轮 −57~−66%；整帧均值 4/5 轮更优（−5.9%~−11.4%，污染最重的 rev-r3 +2.2%）；开火合并 3680+3680 帧均值 −4.7%、中位 53→50、P95 80→77（单轮 P95 从不变差）；**>100ms 合并频率 18.34→18.33 不变**——长帧不由剔除驱动（GC/环境），§5 尾部目标按证据重新定标，**Phase 1 专项门禁通过**。合并分析 `pooled_timing.py`。
- 未完成：cleanup-v1 定量、Phase 4 长局增长证据、玩家重启实测主观流畅度。
- 分析脚本 `build/generated/stutter-opt-20261103/analyze_cold_causality.py`（只读证据）；计划 §7.3 与实施报告已更新因果结论。

## 2026-11-04 — 部署 CS 0.9.7 事件驱动增量剔除（方案 Phase 1）：双进程配对整帧 −7.8%、功能与像素零差异

- 接续并行会话的实施成果：以 23:18 修正版命中夹具重建 qualification-v6，原宿主与 cleanup-v1 宿主各跑一次（14/14）：**屏外命中在 A9B3 原生正常**（无目标弹 627/509 伤害 vs 显式对照 596/624，miss=false）。MainFE 密封（#1069）使 sceneCU 从未存在、Bullet 恒回退 loc.units——旧调查的“镜头列表漏屏外目标”不是现行缺陷；cleanup-v1 因此降级为纯清理候选（去掉 sceneTick 无效列表构造与每弹异常路径），未部署。
- timing-cull-v2 正/反序双进程配对（各 2350 完整间隔、23/23 断言、2,202,688 像素零差异、全部玩家屏内）：整帧均值 **−7.9%/−7.8%**（52.99→48.80、58.60→54.05ms）、CS 局部 **−60.5%/−62.1%**（4.58→1.81、5.01→1.90ms）、max −10.5%/−11.9%、P95 −12.5%/−6.1%、>100ms 频率 −41%/−5%。方向一致；尾部受 RV 并行负载污染，§5 终局目标未达，低负载需复测。
- **已部署** release → **447AE02B**（0.9.7），备份 `ContinuousSceneMod-0.9.6-F16890C9-before-eventculling-20261104-005240.swf`，回执 `state/event-culling-deployment-20261104.json`，宿主 A9B3/scene.xml 不动，重启生效。部署时 1 个 RV 测试 AIR 在跑（原子 rename 对并发读取安全，已记入回执）。
- 不开火对照（timing-nofire-r10，920+920 帧、0 开火帧、全部屏内）**通过且无退化**：均值 58.34→51.71ms（−11.4%）、P95 105→72（−31%）、P99 204→123、>100ms/分 57.0→16.4（−71%）、CS 局部 4.07→1.37ms（−66%）；候选臂一个 4,504ms 离群帧为内存压力下系统级卡顿（剔除工作量与开火无关），不作机制证据。此前 8 次尝试均被 RV 并行测试 AIR/内存门槛 2.5–2.9GiB<3GiB 干净中止，工具自保护正确，未降门槛。
- 冷态探索诊断（cold-r3，qualified 路线 x6203→9535、1300 帧全屏内、650 开火帧、13/13+23/23 断言、像素零差异）**完成**：81.7s 内 cancel 11 次/废弃 431ms、sync 补画 29 次/1985ms（≈68ms/次）、单步 max 125ms、warm 占 7.1%、applyScanned 98,628、markScanned 30,947。Phase 3（帧余量调度）获较强支撑；Phase 2（弹痕不废预绘）量级中等，实施前须证明与同步补画的因果占比；两者待低负载复测后另行实施。
- 未完成：cleanup-v1 定量（已通过双宿主命中对照，纯清理候选，未部署）。
- 过程修正：受限沙箱下启动器命名互斥体（Local\RemainsModManifest-*）被拒 → 按协议对完全相同命令一次性提权重试；自写重试脚本两处自伤（parents 路径、GBK 控制台）已修。src（含事件化剔除与新增 SceneCullEntry/as 测试）、tools 构建器与方案正文本轮一并提交；SceneRenderChecks.as（他人 WIP）未动。

## 2026-11-03 — 按方案实现增量剔除候选；功能通过，资源不足阻止剩余验收

- 用户授权“请按方案进行优化”。实现 CS 0.9.7 候选 event-v3（447AE02B），事件队列维护根、typed entry、避免重复显隐/边界工作；保留坐标轮询，未冒进静态分桶。23 项生命周期、13 项夹具与同帧 2,202,688 像素零差异通过。
- 一轮带高开销遥测的配对见局部 15.44→4.70ms、整帧均值 121.72→91.82ms，但不能作发布承诺；精简反序轮发生约 668s 的执行间断，作废。timing-cull-v2 / timing-nofire-v1 等待独立重复。
- sceneCU 的先前结论更正：MainFE 实测封闭、属性读取报 #1069，镜头筛选有效的前提不存在。独立宿主 cleanup-v1（5B409966）只去掉无效构造/读取异常，两方法/类布局差异核对通过，原生命中尚未通过有效夹具，不部署。
- 从实际物理地图找出 2840px 走廊；旧完全预载准备不适合冷态探索，cold-v2 已改。两次游戏启动被内存门槛阻止，随后只剩约 0.8–1GiB 承诺余量、物理负载 91–92%、无 AIR；未降门槛、未关闭其它进程。
- 已保存 [实施报告与接续](../knowledge/experiments/stutter-optimization-implementation-20261103.md)，更正原调查前提。正式 A9B39CC7 / F16890C9 / 1CEA74E2 不变，未部署。下一步资源恢复后修正命中夹具对照→精简计时双进程/不开火→合格探索→仅部署门禁通过的同一产物。既有六份修改、其它报告及并发方案改写保留，自有测试均已结束。

## 2026-11-03 — 轻机枪移动与探索卡顿调查：优先验证增量剔除，深层探索保留归因缺口

- 用户补充复现场景：马哈顿废墟、轻机枪、大窗口、RV/WB/光暗效果均关闭。委托是详细调查及执行方案；本轮未实现或部署性能修复，正式 A9B39CC7 / F16890C9 / 1CEA74E2 保持。
- 做了什么：回读当前产物链、既有负结果和真实帧记录；三轮登记隔离诊断 7980 个完整间隔（7770 玩家屏内），各 11 项夹具检查通过；新探针确认实际 lmg 出膛、修正 invulner/离屏静止等旧夹具问题。同路开火约增加 8ms；剔除开关提供明确局部脚本成本证据，整帧配对仍有反向结果。
- 判断修正：本轮不支持把主要慢帧归到 presenter 拆建或大批休眠/唤醒；远距 leash、其它震屏、深层探索均未被这些结果排除。深走被墙挡住，不算有效探索复现。当前宿主仍有取消预绘/整步越预算风险，已有弹痕相交剪枝并未消除全表扫描。sceneCU 的镜头目标筛选及跨图陈旧列表另列正确性风险，未冒充已复现卡顿原因。
- 交付：[调查报告](../knowledge/experiments/stutter-investigation-20261103.md)、[优化方案](../design/stutter-optimization-plan-20261103.md)、`knowledge/experiments/stutter-analysis-20261103.py`；原始证据及三个诊断工具目录按报告索引留存。第一次存储权限失败及登记核对释放也保留，三次成功运行均已结束。
- 下一步：先固定当前完整源码谱系及有效新区域路线，做局部增量剔除独立候选；自然探索取消链计量成立后再改预绘保留/预算。旧低清缓存、炮塔 guard、单独环境键缓存负结果不重复包装；只有稳定整帧和相应正确性证据才部署。六份既有未提交源码及其它报告未动。

## 2026-11-02（十一）— 镜头移动退化调查：三臂切分在探针配置下未见退化，战斗拴绳振荡成头号未验嫌疑

- 用户报告镜头移动退化，要求对照 git 历史。部署链回溯：0.9.4/0.9.5（本会话）→ 阵容变更（ConditionSystem/gcfit1）→ **0.9.6（另一会话，未提交源码直接构建部署，仅功能断言零计时）**。宿主/入口配置核对未变。
- v13b 探针 10 轮交错（v93/v94/v95/v96；同布局种子 4077752896；host A9B3+当前阵容恒定）。负载高（RV 全天测试），用相位比值+干净子集双重降噪：**v96 pan比 1.425 最快、v93 1.555、v94≈v93、v95 1.600（单轮干净样本，边缘噪声）——探针配置（scale1 非战斗）无可测退化**。平滑唤醒无罪。
- **头号未验嫌疑：0.9.6 拴绳的战斗休眠/唤醒振荡**（风筝时敌人跨 2200px 反复 freeze+重唤醒）——非战斗探针覆盖不到。战斗对照首跑因负载在路线预热 2.5 分钟超时（cscombat-v93-r1 残迹保留），`orchestrate_cscombat.py` 就绪待低负载重跑。
- 未排除用户侧变量：窗口模式（探针 scale1 vs 默认小窗 scale⅔ 呈现/震屏全惰性）、场景类型、游玩时段负载。用户选项 A/B/C/D 已列（维持待测/回退 0.9.3/回退 0.9.4/建 0.9.7 剔除默认关）。报告 `camera-regression-bisect-20261102.md`。

## 2026-11-02（十）— CS 0.9.6 部署：脱战拴绳 + 弹道威胁双盒 + 震屏容忍（优化方案 Phase 1）；Phase 2 撤销（宿主已有弹痕剪枝）

- **方案执行**（`design/combat-motion-optimization-plan.md`）：Phase 1 三项全部模组层实施并部署 → CS release **F16890C9**（0.9.6）。宿主 A9B39CC7 未动。备份 `build/backups/ContinuousSceneMod-0.9.5-1A66B1F4-before-leash-20261102-152416.swf`，回执 `state/leash-v096-deployment-20261102.json`。
  - **1.1 脱战拴绳**：`NativeSceneActivity` 新增 `deadline/leashed`——150 帧无战斗信号且在 2200×1600 追击半径外，`engaged` 重置、受伤条件同受拴绳门控、until 清零即时休眠；`wake()` 刷新期限；boss/npc/剧情豁免与既有 urgent 语义不变。
  - **1.2 威胁双盒**（实现偏离方案原文，理由记入 MEMORY）：弹道命中走廊（path±explRadius+40）= urgent 立即唤醒；400px 警戒晕圈 = active+预算唤醒。保留 on-path 语义，"projectile-path-wakes-distant-enemy" 断言原样通过。
  - **1.3 震屏容忍**：协调器与 Fill 均容忍 |quake|≤25（World.quake 上限 20）；分数平移仅震屏激活时接受；无额外变换注入（世界容器同移）。
- **验证**：mechanics r2 29/29（旧阵容）+ issues r1 16/16 + 正式阵容变更后补 mechanics r3 29/29（ConditionSystem 组合）；均 game-coexist。无计时声明。
- **Phase 2 撤销**：部署宿主 `sceneRestoreMarks` 已有 decal 空间剪枝（sceneDecalBounds+sceneApplyRegionAction 区域绘制；冻结源 camera-spatial-20261101/source 可证）。原诊断读了过时 `src/patches/GrafonChunks.as.inc`——本轮对 .inc 的编辑已 git 回退；**.inc 与部署谱系分叉记为源码卫生债**（全量构建若直接用它会回退宿主剪枝）。Phase 3 炮塔守卫维持待 GC 配对测量。
- **测试设施**：首轮超时根因=并行会话改写 `build/runtime` 模组选择（探针出局）；恢复走启动器 `--only` + `ContinuousSceneMotionMod` shim 并刷新 shim SWF 为本轮构建。入口注册行/清单入口名必须 `*Mod`（ModScanner EntryPattern）。
- git：本轮改动 5 个 src 文件 + state/design 文档；`SceneRenderChecks.as`（他人 WIP）未触碰；未提交（留待用户/后续会话按惯例处理）。

## 2026-11-02（九）— 外部 GC 修复验证通过；组合复测帧判定受日间负载污染

- 阵容变更核实：AddictionSystem+PermanentInjury → **ConditionSystem**（v0.2.1），RConnect → gcfit1（8AB94C8B）。v14b 独立归因（24/24 窗）：**persist 408/帧→0、setParameters ~867/帧→0、NetHud 139/帧→0——移交三项全部确认消除**，与对方自测（addiction:: −94.6%；fit 3,324→0）互证。
- 勘误：移交报告 §2.3 两条（Catalog/clone + Runtime/after，~366/帧）经 ConditionSystem 包名核实为 **FirearmAttachments（fa::）**——下一个应通知的维护者。
- v13b 组合配对（4 轮交错，当前阵容）：GC 指标一致（cand 6/6 轮 −1 掉落、体积 −10~20%）；**帧指标不可判**——日间机器负载污染（轮时长 198–297s vs 清晨干净 137s，两轮均值差方向相反）。029DAF34 维持不部署；夜间低负载可重跑裁定（工具链就绪）。
- v14b 运行另见 76 长帧异常为同因（机器负载，均匀分布各阶段、仅 8 邻 GC）。报告 `gc-fixes-verification-20261102.md`；证据 `v14b-attrib-r1`、`combo-gctail-*`。

## 2026-11-02 build 相同副本清理（ModLoader 会话统一执行，跨模组治理）

- 按"只删完全相同副本"处置 build 堆积（D 盘曾剩 6.2 GB）：本模组 5,152 个文件被删（runs 等冷目录中的重复副本；generated/runtime 因 48h 内仍在写入被整体保留）；git 跟踪文件、测试登记表目录、backups 一律保留。三模组本轮合计实际释放 54.67 GiB，D 盘回到 61 GB。
- 恢复：被删文件按 `../ModLoader/build/out/cleanup-plans/20261102-095751/receipt.json` 记录的 origin 重新复制即可；工具 `../ModLoader/tools/cleanup_test_copies.py`（plan/check 可复跑；热目录冷下来后可再回收）。
- 根因（每试验复制一份完整游戏本体，camera-* 每个约 1 GB）与防复发（调试器 1.2.0 硬链接冻结＋自动 sweep、`/build/` 整体 gitignore、配额巡检）见 ModLoader journal 同日条目；本模组自带 runner 的输出根迁硬链接路径待后续迭代。knowledge/experiments 4.3 GB 证据未动，归档另议。

## 2026-11-02（六）— GC 组合路线终局：每窗分布量化 B/C 上限后关闭

- 用户批准继续组合包后，先用已有 v14 证据做每窗分布：**A 的 env 泵窗级清零确认**；warm/块键稳态仅 ~400/帧（此前"9k/窗"为 23 窗累计误读）；剩余稳态垃圾主体为 pre-render（1.0–3.6k 波动）与 AddictionSystem（~1.2k 恒定）。
- **判定：B/C 不构建**——上限合计 ≈ A 的 1/3，A 已证不足以移动帧指标。AS3 垃圾削减路线整体关闭；"减分配≠减帧时"三次独立验证定案。
- 外部移交卡（AddictionSystem/RConnect，含栈与每帧量级）写入 `gc-combo-closure-20261102.md`；修复 A 候选 `029DAF34` 保留，供未来组合复测。零新增运行。


## 2026-11-02（五）— 修复 A 单元格缓存：泵消除成功、配对无帧收益，不部署


- 候选 `029DAF34`：sceneNativeEnvironment 逐单元格结果缓存（state.cellCache int 稀疏数组，width<=0 回退字符串路径，无新增 Grafon 字段，审计仅该方法变化）。构建时把宿主导出源两处 §§findproperty/§§push 残渣改为等价可编译写法（不移植，字节码保持原宿主）。
- 验证：mechanics 27/27 + issues 16/16（r1 超时=清单被 motion 流程改写的环境失误）；v14 归因复测**区域键泵完全消失**（分配 382,817→344,613）；v13 四轮配对：GC 掉落 9→8（−11% 一致）、长帧 13→23/9→9 不一致、均值混合 → **不部署**。
- 判定依据：门禁要求真实整帧收益；区域键只占总分配速率 ~10–15%，单点修复移动不了 ~65MB 周期回收节奏。GC 停顿的可行路径是组合削减（B 键缓存+外部模组 JSON/NetHud+原生侧）并先配对验证预期。
- 生产 A9B3/CS0.9.5 未动；8 次争用重试全部登记，无残留进程。报告 `envkey-cache-20261102.md`。


## 2026-11-02（四）— GC 周期回收来源定位：首要泵是自研 sceneNativeEnvironment 每帧字符串


- v14 探针（FrameCostProbe v2：DeleteObjectSample id 关联回出生栈 + 类型直方图 + 存活字节）在生产栈（A9B3+CS0.9.5 全栈）跑 24 个单帧采样窗全有效：382,817 新对象、157,022 当窗死亡。
- **`Grafon.sceneNativeEnvironment < Location.step` 以 ~2,812 新对象/帧居首，99.7% 当窗死亡、零留存**——宿主补丁每对象每帧调用拼区域键（2×int→String+concat×~570对象）。估计 ~110–180KB/帧，主导 ~65MB 周期回收填充。修复方向 A（单元格 int 缓存，宿主单方法替换）已明确未实施。
- 次要：sceneEnsureUpcoming 块键 ~396/帧（82.6%死）、NativeSceneActivity ~530/帧（与 0.9.4 前同量级）。外部：AddictionSystem 每单位每步 JSON（88.7%死）与 RConnect NetHud（100%死）移交负责人；TDFC snapshot 是留存型非泵；原生 pre-render 死亡率 13.3% 排除主驱动。
- 运行 `gc-source-attrib-r5`（r1 被 RV 并行测试正确中止、r2 输入哈希断言中止、r3/r4 再遇争用，编排器自动重试至成功；全部登记 game）。报告 `gc-source-attribution-20261102.md`。


## 2026-11-02（三）— 炮塔守卫 GC/长帧尾部配对测量：负结果，Phase 3 关闭


- v13 探针（v12+每帧 System.totalMemory 字节）四轮配对（base A9B3 / cand 6AC6C692 交错、同布局种子 4077752896、CS0.9.5 全栈、独占 game、1115 采样/轮）：**GC 掉落 7–9 次/轮两臂无差、~65MB 周期大回收照旧、长帧无一致方向（r1 18vs5 更差、r2 11vs14 略好）、r1 均值 +11%**。叠加 10-31 旧两轮共 6 轮配对零收益 → **维持否定不部署**。
- 机理修正：休眠炮塔不调 animate，醒着炮塔不足以驱动 GC 周期；"采样最大存活来源 ≠ 回收可削减来源"。GC 方向转往周期性大回收真实来源（原生渲染/display 基础设施），炮塔守卫不再投入。
- 单位勘误记录：System.totalMemory 为字节；初版分析误按 KB，GC 阈值/换算已按字节重算（帧间隔统计不受影响）。
- 玩家游戏期间后台编排器自动等待（未打扰），退出后自动完成四轮；登记/进程全部正常结束。报告 `turret-guard-gctail-20261102.md`；证据 `turret-gctail-{base,cand}-r{1,2}`。


## 2026-11-02（二）— 部署 CS 0.9.5 状态保真物体剔除（Phase 4）；Phase 3 候选备妥未部署

- **Phase 4**：`SceneObjectCulling` 接入生产（透明包装 Sprite 只切包装层 visible，游戏独占对象自身 visible——UnitSpectre 正解）；SATS 截取挂起/恢复（SatsVisibleGuard.capture）；空边界安全；故障自禁用。`ContinuousSceneMod` 0.9.5：onFrame 调 update、nativeAPI 挂 objectCullingEnabled/Stats。
- 兼容性依据：`Pt.remVisual` 为父相对删除（源码核实），包装层孤儿检测同帧清理；teleObj/潜伏(lurk)箱保持直挂。验证：mechanics 27/27 + issues 16/16（门/边界×3/Bonus·Trap·CheckPoint·**UnitTurret** 固定视觉，剔除激活态），截图存档+程序化健全性通过；像素级人工复核开放。
- 已部署：release → **1A66B1F4**（0.9.5），备份 `ContinuousSceneMod-0.9.4-DF3B6812-before-culling-20261102-004010.swf`，回执 `state/object-culling-deployment-20261102.json`。需重启生效；运行时开关 `objectCullingEnabledSet(false)`。
- **Phase 3**：UnitTurret.animate 同帧守卫在 A9B3 重建 `6AC6C692`（`camera-turret-animate-20261102/`，单方法、类布局不变）；候选宿主冒烟 27/27（10 炮塔 0 错位）。**不部署**：旧否定（两轮配对无均值收益）仍有效，翻案需 iteration-review 要求的 GC 频率/长帧尾部配对证据。
- 三次隔离运行均登记 game-coexist 并结束；本会话模型不能读图，issues-entry.png 待有视觉能力时人工/模型复核。


## 2026-11-02 — 部署 CS 0.9.4：分帧平滑唤醒（Phase 1 削峰）

- 用户按优化方案授权实施。`NativeSceneActivity.update` 拆分唤醒语义：**紧急信号（掉血/交战/弹道威胁/状态效果/非敌对/功能关闭）保持原即时唤醒**；仅预期性唤醒（邻近 1900×1300 / 视口 +600px 边界）进入每帧预算队列，**最近者优先，默认 1 个/帧**，余者保持冻结+跳过 step，后续帧再授予。镜头扫过敌群时的同帧 resume+step+gotoAndStop 风暴被摊到多帧。
- 纯模组层改动（src 两文件：NativeSceneActivity.as、ContinuousSceneMod.as 版本 0.9.3→0.9.4），stats 增加 budget/version（"smooth-wake-1"），nativeAPI 增加 activityBudget 可调。冻结配方与 src 已核对逐字一致，`build.ps1 -DriverOnly` 重编。
- 隔离验证（登记 game-coexist，宿主 A9B3 + 14 模组 + 探针，`smooth-wake-v094-mechanics-r1`）：**27/27 断言通过**，含 8 项调度语义（远敌休眠 124/186、邻近唤醒、追击保持、伤害/弹道即时唤醒、禁用全恢复）与门/边界/奖励池/跨房机制。无计时声明。
- 已部署：release/ContinuousSceneMod.swf → **DF3B6812**（0.9.4），备份 `ContinuousSceneMod-0.9.3-D8A68A4C-before-smooth-wake-20261102-000448.swf`，回执 `state/smooth-wake-deployment-20261102.json`。**需重启游戏生效**；回退=备份覆盖。
- Phase 2–4（AI 分频、动画防抖、安全屏外剔除）未实施：均需宿主方法替换，待本轮实测反馈后另行推进。旧 UnitSpectre 回归教训对 Phase 4 仍有效。


## 2026-11-01 — 视口预过滤负结果：Location.step 修改导致全面回归

- Location.step() 链表迭代中加入视口过滤（>800px Unit 跳过 step）导致**全面恶化**：战斗静止 44.5→49.2、走路左 33.8→42.3、静止后 44.5→51.9。原因可能是方法体积超出 JIT 阈值或链表检查开销。不部署；当前 A9B39CC7（空间碰撞-only）仍为最优。报告 `viewport-prefilter-negative-20261101.md`。

## 2026-11-01 — 部署空间分区碰撞（战斗静止 −21.7%）

- Grafon.sceneTick 每帧构建视口内（±500px）单位子列表存于 `visual.root["sceneCU"]`；Bullet.run 碰撞优先读子列表（~15 单位 vs 全量 ~130），回退安全。
- **12 敌人战斗静止 56.8→44.5ms（−12.3ms，−21.7%）**；战斗走动 54.6→51.4ms（−5.9%）；非战斗无回归。无可见性管理（避免 UnitSpectre 问题），无视觉影响。
- 已部署：根 pfe.swf → **A9B39CC7**，备份 `pfe_before_spatial_collision_20261101-225837.swf`，回执 `host-patch-receipt-spatial-collision-20261101.json`；冒烟 10 断言通过。报告 `spatial-collision-deploy-20261101.md`。需重启生效。

## 2026-11-01 — 多敌人卡顿调查：O(n²) 子弹碰撞归因（非镜头问题）

- v12 变敌数探针（0/3/12）测量：战斗走动 0敌 36.6ms → 3敌 41.6ms → 12敌 54.6ms（**每敌人 ~1.5ms，超线性至 1.96**）。战斗静止 12敌 56.8ms（超 33ms 目标 24ms）。非战斗相位不受敌数影响。
- **根因**：`Bullet.as:503` 每颗子弹对**所有 ~130 单位**做 AABB 碰撞（无空间分区）。12敌时 ~40 发 × 130 = **~5200 检查/帧** + 命中音效/特效/伤害。这与镜头移动无关——四层镜头优化已到位，剩余卡顿来自游戏碰撞架构。
- 修复方向：①空间分区（网格索引，最大收益）；②视口内单位预过滤（中等）；③降射速（改玩法）。报告 `multi-enemy-stutter-20261101.md`。

## 2026-11-01 — 质量管理最终判定：AIR direct 渲染下不可行（负结果关闭）

- 四轮尝试（宿主 visFront / mm.stage / mm+sleep / CS 模组 ENTER_FRAME）均导致回归或无效。CS 模组版本（从冻结源重建、加入 onFrame 质量管理）战斗走动 56.5ms vs 基线 42.5ms（+14ms）。
- **v11 探针的 15~17% "改善"是伪象**：探针每帧设置 quality 属性触发显示列表失效（invalidate），LOW/HIGH 差异来自失效+重栅格化代价差，不是 LOW 质量的稳态渲染加速。在 AIR `renderMode="direct"` 下，任何触碰 stage.quality 都破坏 GPU 渲染缓存。
- 此方向**永久关闭**。根 pfe.swf 保持 CA94AF17（四层），CS 模组保持 D8A68A4C（0.9.3 原版）。报告 `quality-final-negative-20261101.md`。
- 注：另一会话同日迭代审查发现第四层（屏外单位显隐）在 UnitSpectre 上有 false→true 视觉影响，建议安全撤掉——见其 `camera-iteration-review-20261101.md`。

<!-- quality-and-dense-20261101 -->
## 2026-11-01 — 画质取舍与画面内多敌人诊断；候选均未达部署门槛

- 接续用户接受两类画质试验与多敌人补充，完成11次实际AIR运行。四次检查失败/争用中止原件保留；另一次编译排队超时无Java/AIR。成功非采样时序19860区间，玩家在屏内16638；额外540帧为带采样器交火诊断，不作为性能验收。
- 修正测试资格：invulner玩家不会被原生敌人选作目标；有开火仍需逐帧证明交战对象在屏内；Pers重算会重设knocked=1。v29/30在地形预绘后生成六敌，使用fixed测试靶，六敌存活、玩家/至少三敌持续可见、逐窗开火。玩家物理运动未验，不夸为自然游玩验收。
- 全景低分辨率、地形低分辨率、原生LOW/MEDIUM、逐帧质量切换、请求GPU及隔帧缓存均未得到稳定可用收益。隔帧3档横移平均仅约2.3%变化，>100ms长帧14/178→26/178；存在图像滞后，明确淘汰。
- 原生allowLowQuality显式启用后实际有效，更新共享事实纠正旧缺省配置结论；正式application.xml未修改。多敌人CPU画像中原生呈现和GC值得继续分开核验，但GC调用上下文不是分配归因；旧快照/区域键/炮塔候选的负证据仍有效。
- 本轮未部署、未达到近原版。正式9D8662F6与14模组指纹不变，全部自有登记/测试退出，未停止玩家或他人进程。报告knowledge/experiments/quality-and-dense-enemies-20261101.md；本轮输入/源码/失败/图片/采样冻结于quality-evaluation-20261101清单。只提交本轮标记段，保留他人WIP。
<!-- /quality-and-dense-20261101 -->


<!-- lossless-cut-survey-20261101 -->
## 2026-11-01 — 无视觉降级切口普查与候选淘汰

- 逐项复核既有绘制、镜头、调度、分配证据，新增TDFC双快照、物体同序分组/大小/原生组缓存、GC收尾、两版AIR运行库对照。10次实际运行、29892有效间隔；1次预热超时及一次未启动排队超时原件保留。
- 快照组件节省约0.08ms但整帧更差；中性分组方向/窗口不一致；两档GC收尾均值变化不足1%、尾部更差；新版运行库经原版恢复对照未证明稳定收益。分组/缓存终局见普查报告；不降低质量或改敌人行为换帧率。
- 未部署新性能候选，根9D8662F6与14正式模组指纹保持。全部自有测试登记结束，无玩家或他人进程操作。
- 报告knowledge/experiments/lossless-cut-survey-20261101.md；冻结源、原始结果、环境和汇总位于build/generated/lossless-cut-survey-20261101及manifest列出的本轮目录。剩余限制明确保留：尚未达到近原版，未证明所有可能的无损重构均无收益。
<!-- /lossless-cut-survey-20261101 -->

<!-- camera-optimization-20261101 -->
## 2026-11-01 — 撤回单位显隐回归；九轮镜头候选复验

- 14:58根宿主CA94→9D8662F6，只撤无条件visible赋值，A2/预绘环/48ms预算保留；UnitSpectre真实原生隐藏验证、备份、相同字节部署及回读完成。CS D8A/WB FE3/RV AEA/RC6906等14模组未改。
- 9次私有静音游戏运行、7轮时序15740有效间隔，已全部退出并结束登记。v9像素失败保留；v11相位搜索完成但无相位达标。
- 裁剪、物体层缓存、炮塔guard、地形节点cache无稳定整帧收益；不把GC相位错位或局部观察带下降当产品提速。
- 屏幕分辨率缓存v13十视角：小窗最大RGB1/alpha0，大窗RGBA精确；但小窗仅约2.9%且尾部更差，大窗约11.3%退步，不部署。初版v12与全部负结果保留。
- 旧全类别缩活动范围方案未补内部AI保护，仅静态审查，不重新运行。追击/屏外命中/现有休眠规则保持。仍未达到近原版。
- 业务报告knowledge/experiments/camera-optimization-followup-20261101.md，汇总配方build/generated/camera-optimization-review-20261101；同任务技能反馈追加原报告，不重复登记。仅归档本轮，自有marker以外状态和他人SceneRenderChecks/报告字节保持。
<!-- /camera-optimization-20261101 -->

## 2026-11-01 — 当前四层迭代审核与镜头归因（本会话）

- 审核实际部署 CA94 及 A80→四层配方；没有回退/部署正式文件。确认UnitSpectre原生隐藏被sceneTick覆盖，A80对照不变。
- 4轮12684有效间隔，玩家站定，关闭RV/WB/LAD，预绘稳定后仍有横纵呈现成本；小窗现有合并不启用，大窗合并启用仍有物体显示树成本。大窗光照层未见稳定贡献。
- 35次>100ms中32次伴随明显内存回落；12/12调用栈窗口有效，炮塔重建/FocusManager链与TDFC快照列为候选，不能按分配计数直接宣称收益。276/304/537ms剩余长停顿未归因。
- 纠正旧探针菜单显示层残留、阶段45计时像素哈希、30fps上限及缺少正式纵移测量等证据边界；失败准备原件保留。
- 报告：knowledge/experiments/camera-iteration-review-20261101.md；配方camera-review-v4/v5/v6-20261101。技能反馈已登记全局台账。所有自有测试/登记结束；他人工作树不纳入本提交。

## 2026-11-01 — 质量/休眠负结果与回退到第四层

- 第五层 visFront.stage 质量：无效（visFront.stage 可能 null，3 轮 vs 基线无差异）。第六层 mm.stage 质量：**严重回归 +10ms**（可能 AIR 值规范化致每帧重设+缓存清除）。敌人 sleep：**严重回归 +15ms**（AS3 internal 跨包异常 × 139单位 × 30fps）。全部已回退。
- 已回退到 **CA94AF17**（四层：预算48+A2 gutter+屏外隐藏）。v11 探针证实质量降级从模组 ENTER_FRAME 设置可改善 15~17%，但宿主 Grafon 路径不可靠。推荐下一步在 CS 模组层面实现质量管理（需重建 CS 模组）。报告 `quality-sleep-negative-20261101.md`。

## 2026-11-01 — 部署 LOW 渲染质量（五层完成）

- v11 探针同轮 A/B 显示 LOW vs HIGH 在战斗走动中改善 **15~17%**（4 项测量一致：−7.4~−8.3ms）。跨轮 A/B（3 对 pooled）无差异（噪声掩盖）。探针验证无效（beforeNative 覆盖宿主设置）。
- 候选 `8321E4E7…`（仅 `sceneTick`：`visFront.stage.quality="low"` 当 `sceneLarge=true`，退出时恢复 `"high"`；同时保留屏外隐藏）。地形为预渲染位图不受影响；单位/特效边缘略粗糙。
- 已部署：根 pfe.swf → 8321E4E7，备份 `pfe_before_lowquality_20261101-013945.swf`，回执 `host-patch-receipt-lowquality-20261101.json`；冒烟 10 断言通过。若视觉不可接受可回退。五层累计见 `lowquality-deploy-20261101.md`。

## 2026-11-01 — 部署屏外单位可见性管理（四层完成）

- v10 探针 A/B（同轮 ON/OFF）显示 13~21%；宿主干净 A/B（3 对）pooled +1.4%（0.6ms，P95 56→54），2/3 对改善。探针级数字高估（OFF 基线强制全 visible）。候选 `CA94AF17…`（仅 `sceneTick`）已部署，备份 `pfe_before_unitvis_20261101-004531.swf`，回执 `host-patch-receipt-unitvis-20261101.json`；冒烟 10 断言通过。四层累计见 `unitvis-deploy-20261101.md`；剩余瓶颈为战斗/AI（~5-8ms）与原生渲染（~20-25ms）。

## 2026-10-31 — 部署预算上限 48ms（三层累计评估完成）

- misses 分析：快速平移中预算始终钳制在 36（55/55 帧），misses 每 4 帧出现（跨块周期）；吞吐量需求 ~48ms/帧 > 预算 36 → 缺口由同步补绘填补。
- 候选 `9D8662F6…`（仅 `Math.min(36→48)`，视觉零变化）：快速平移两轮 misses 17→9~10、forced→0、P95 156→122~140、max 181→161~179、空洞 0。正常速度 ±0.91ms 内无回归。
- 已于 17:12 部署：根 pfe.swf 8EAAE4EE→9D8662F6，备份 `pfe_before_budget48_20261031-171254.swf`，回执 `host-patch-receipt-budget48-20261031.json`；安装后隔离字节探针 10 断言通过。
- **三层累计**（vs A80 同 RV）：mean −5~9%、P95 −18~29%、max −40~46%、misses −57~61%、forced −100%、空洞始终 0。报告 `budget48-deploy-20261031.md`。

## 2026-10-31 — 部署 A2 gutter 快速暖块（当前宿主 → 8EAAE4EE）

- 用户允许有限视觉取舍后重评 A2：预热时跳过仅覆盖 gutter 的风格整绘。当前宿主 626DFBC8 上单方法替换 `sceneBeginWarm`，候选 `8EAAE4EE…`；仅该方法变化、1016 类布局不变。
- v8 快速平移两轮：基线 r4 82.73/171/298、forced 4、misses 23；A2 r1 75.84/153/186、forced 0、misses 15；A2 r4 78.78/156/181、forced 1、misses 17；空洞 0。v7 正常速度各相位 ±0.7ms；front/voda 中心像素 0 差异（52+11 共同块）。
- 已于 16:39 部署：根 pfe.swf 626DFBC8→8EAAE4EE，备份 `pfe_before_a2_gutter_20261031-163909.swf`，回执 `host-patch-receipt-a2-gutter-20261031.json`；安装后隔离字节探针 10 断言通过。代价：gutter 近似（伤害/WB 边界采样），当前 WB 关闭；若启用需重评。需重启生效。

## 2026-10-31 — 性能优化切口全面搜查：转塔守卫否定，分配≠帧时间

- 当前宿主 626DFBC8 重跑帧成本采样（2160 帧/48 窗，47 窗有效，1 窗 Sample count mismatch 原件保留）。画像：原生 `[render]`+`[pre-render]` 45–132 CPU 样本/8 窗（最大）；`sceneNativeEnvironment` ~14,900 分配/8 窗；`UnitTurret.animate→gotoAndStop` 链 12–17 CPU、1,050–1,920 分配，并带动 FocusManager/Sprite 子对象；`sceneEnsureUpcoming` 1,390–2,430 分配；JSON persist / NetHud 属其它模组。
- 候选：`UnitTurret.animate` 同帧守卫（仅当 `puha.currentFrame != tr` 才 gotoAndStop），单方法替换 `1666FCB1…`；两轮配对无帧收益（static/pan/walk ±0.3~2.6ms、方向多为略差），否定。
- 结论：分配 churn 不等于帧时间（与旧 `sceneNativeEnvironment` clamp 一致）；剩余最大 CPU 是原生渲染，需视觉门禁；已部署的预热预算仍是唯一有同日成对证据的视觉中性收益。报告 `performance-cut-survey-20261031.md`。

## 2026-10-31 — 部署视觉中性预热预算补丁（A80 → 626DFBC8）

- 用户批准部署。安装前目标 A80ED32B… 未变、候选 626DFBC8… 与审计产物一致；备份 `pfe_before_visualneutral_budget_20261031-121918.swf`（A80 原字节），覆盖根 `pfe.swf` 并回读 626DFBC8…。回执 `build/host-patch-receipt-visualneutral-budget-20261031.json`。
- 安装后冒烟：部署字节复制进隔离运行时，v7 探针完整通过（ok、10 项断言、1115 帧）；该轮与 RConnect 长测试并发，相位偏慢（38–44ms）不作性能证据，性能证据用安装前同日成对轮（P95 237/238→137/180，max 332/406→221/333，forced 3→2，空洞 0）。
- 回退：用备份覆盖根 `pfe.swf` 即可恢复 A80ED32B…；CS 模块/WB/RV/RC/配置未动（CS 模块仍 D8A68A4C…）。需重启游戏生效。

## 2026-10-31 — A3 慢帧定位与视觉中性预算候选

- A3 慢帧不是每帧开销：v9 计时探针手动调用 `g.sceneTick()` 三宿主均为 0.07–0.65ms；A3 正常相位落后来自偶发大帧（pan 均值 45.7ms，剔除前 8 帧后 34.1ms；出现 1817ms 单帧）。A3 因此不再推进。
- 视觉中性候选（A80 单方法替换 `sceneEnsureUpcoming`）：预热环 ±2→±3、预算上限 24→36ms，候选 `626DFBC8…`；审计仅该方法改变、1016 类布局不变。绘制路径未动；front/voda 中心像素 0 差异（29+5 个共同块），back/back2 为动画噪声。
- 快速平移两轮（同日基线）：P95 237/238→137/180，max 332/406→221/333，mean −4.3/−5.5ms，forced 3→2，空洞 0；>100ms r1 11→7、r2 11→11。正常速度各相位 ±0.15ms；默认窗口 1280×720 冒烟 9 项断言通过、33.27–35.52ms。代价：极端场景驻留 +14~19 块（≈36–49MB）。
- 未部署；候选与证据保留。报告 `knowledge/experiments/visual-neutral-budget-20261031.md`；证据 `camera-baseline-1031-v8-r{1,2}`、`camera-budget-fast-1031-r{1,2}`、`camera-baseline-1031-v7-r1`、`camera-budget-normal-1031-r1`、`camera-budget-default-1031-r1`；构建 `camera-a80-budget-20261031/`；计时探针 v9 `56E82449`。

## 2026-10-30 — A80 移植 A2/A3：实测未达流畅度门槛，不部署

- 从 A80 自身方法布局构建 A2-A80 `7180CD1A`（仅 sceneBeginWarm）、A3-A80 `5E318EC6`（再改 sceneEnsureUpcoming）；均载入运行、探针通过。A80 反编译源 importScript 因 `findproperty` 预处理指令失败，作失败原件；改用已验证的干净 81C1 源向 A80 单方法替换。
- v8 快速平移：基线 78.93ms/P95 204/max 343/forced 3/空洞 0；A2 71.73/179/309/3/0；A3 117.07/206/255/0/24。A3 尖峰降低但平均更差、>100ms 11→30、24/55 帧空洞。
- v7 同会话重跑基线：A2 正常相位 ±1.6ms、跨新块 39.28→37.03；A3 无 misses/预绘/空洞仍 +3~9ms，两次复跑一致。控制实验：A80↔81C1 的 sceneEnsureUpcoming 字节相同；FFDec 重编译原方法 `changed=[]`，排除重编译副作用；A3 慢帧原因未完全定位。
- 用户条件“空洞若实证大幅提升则接受”不满足：A3 平均更慢且正常相位回归；A2 收益小未达明显门槛。**不部署**，A80/D8A/WB/RV/RC/配置/存档未改。报告 `knowledge/experiments/a80-fastwarm-port-20261030.md`；证据 `camera-a80-*-20261030-r*`、`camera-baseline-now-20261030-r1`。

## 2026-10-30 — 三项镜头实验完成：战斗走动归因、默认窗口对照、快速暖块/有界补绘候选

- 第1项：固定走廊(841.8/4960) v3探针，无战斗走动 +0.5~1.2ms；6敌+玩家开火战斗静止 +5.0ms、战斗走动 +11.6/+8.4ms，与用户真实记录走动差 +11.2ms 同量级。结论：战斗/AI 是运动差主体，地形预绘次之（报告 `camera-combat-window-lead-20261029.md`，证据 `camera-combat-walk-lead-20261029-r2`）。
- 第2项：默认窗口 1280×720（内容区1264×681、scale0.6583、呈现回退原生）静止33.36、横移33.31、回驻留走动34.18、跨新块37.34ms(22块)，与scale1几乎同速；窗口/缩放本身不解释卡顿（同报告，证据 `camera-default-window-lead-20261029-r1`）。
- 第3项：58块归因双风格组76.2ms≈单组38.3ms的2倍，常由40px gutter触发整块重画（`chunk-cost-attribution-20261030.md`）。候选A2单改sceneBeginWarm（81C1诊断宿主 C33A2FBC，仅1方法变化）：边界块78.8→56.7ms(−28%)，front/voda中心像素0差异（基线-基线噪声对照）。候选A3再单改sceneEnsureUpcoming有界补绘（A2CB22A7）：80px/帧快速平移最大帧343→161ms、P95 204→139、forced 3→0；代价21/55帧短暂空洞，正常速度无回归（`chunk-fastwarm-candidate-20261030.md`、`chunk-forced-spike-candidate-20261030.md`）。
- 均未部署：A2/A3为81C1血缘诊断宿主，不含A80后续补丁；部署前需A80移植、WB/空洞视觉门禁，并需用户接受"极端速度短暂空洞换300ms卡顿"取舍。A3 r1的#1010（81C1缺单位边界修复）与r2的#1069（新字段未进trait）作失败原件保留；探针v3/v7/v8、候选A/A2/A3构建与全部运行原件保留。

## 2026-10-29 — 优先修复原启动器与多会话测试路径

- 按用户要求转入基础设施修复。已定位入口EXE继承Low完整性标签，普通运行器启动后子进程降为Low；同字节Medium副本恢复后，修复原启动器/ADL及两个模组工具入口标签，字节和DACL不变，原窗口正常打开。
- 共享测试工具已部署：复制ADL与根宿主完全同字节才复用普通标签宿主；保持隔离描述符/运行库/存储。默认功能计划两组并行，性能仍独占，FIFO与有证据的中断回收。68项定向检查、双AIR各39项、两个独立CLI真实菜单并行通过，全部自有占用结束。
- [实现、证据与回退](../../ModLoader/knowledge/experiments/startup-test-path-2026-10-29/README.md)。本轮未改CS源码/release/根SWF，保留外来SceneRenderChecks；不宣称镜头改善。平台3686890F候选仍待计时，后续可沿已恢复私有桌面运行。

## 2026-10-29 — 镜头相位候选图像通过，启动故障中止性能验收

- 当前产品4320完整间隔的30/120对照确认30纵移改善不稳定；保留长帧及前后反转，不把120容量当实际30fps体验。全层局部相位及取整候选alpha超限停止；独立mask7首次15图RGBA精确，但自然位置不同，不越界归因。
- A283两次路线资格失败均计时前停止，未放宽玩家屏内/纵移幅度。3686890F已编译，新增有记录的测前一次现有平台布置和45正常站稳帧；暂无运行及性能数据，不生产化。
- 随后AIR启动前0xC0000142；创建资源策略成功，旧回读断言是进程退出后的次生问题。此前成功的独立小AIR也失败，私有TEMP不能恢复；轻量Python/user32成功。用户报Remains Launcher临时路径访问被拒，但普通用户Temp写读成功、没有修改权限；用户确认Remains.vbs直接入口可正常进游戏，原启动器未修复。
- 用户授权一次可见小样例，AIR101344在15秒上限前无存储，清理自有进程并结束登记；不把清理退出码1当自然错误，不扩大一次授权。所有自有测试已结束，正式A80/D8A/FE3/BD64/6906未变，外来代码和.dshclaim未动。报告camera-pacing-phase-20261029.md；下一步恢复测试环境再测候选，本轮无正式部署。

## 2026-10-29 — 屏外及RV隐藏受击实测；单格取样解释未成为修复

- 用户新增要求攻击命中屏幕外、RV遮住的区域，继续强调横纵镜头卡顿。当前A80/D8A四个Bullet方法核对未见视口筛除；更后方法解码失败如实保留，不放宽解析器。RV按当前D56正式源映射，隐藏显示/提示不等于禁伤。
- 新增SceneOffscreenHitChecks，两轮真实游戏分别20/21断言通过：自然休眠天角兽889→887.147、RV实际隐藏蝙蝠97.2→94.695；移除测试弹再调度唤醒，其他119/111休眠者保持；实墙、到期负例通过。短路径组件，不宣称完整武器射程/光束/爆炸/AI追击。初版编译失败及v2修正均保留。
- v3补屏内隐藏和真实buffer取样已编译，启动前内存保护中止，无AIR。低占用独立合成图实验18组合完成：scale1/.5精确，2/3两种fill均超限，否定本次局部Sprite锚定修复，停止生产化；72输出释放、参照重复/源像素不变通过。该组件不载入游戏，不是帧率证据，不降低完整地图门槛。
- 报告offscreen-hits-20261029.md。三次自有AIR与登记均结束。正式A80/D8A/FE3未动；本轮观察到RV BD64、RC6906的他人更新并保留，外来SceneRenderChecks不动。镜头性能未完成，无新部署。

## 2026-10-29 — 深入镜头：确认默认缩放覆盖缺口，两条新路线停止

- 用户确认默认小窗口和全屏／大窗口都卡顿。实际1280×720初始scale2/3，而现0.9.3呈现限scale1；缺口不解释大窗口，不称唯一根因。原帧率30，旧120fps容量不冒作真实节奏。
- 四次AIR都退出：缩放v1-r2玩家投影暖图失败；v2原生矩阵数值资格失败；v3完成10图，2/3五例RGB/alpha超限、.5五例精确，.8未进入图像比较。另v1-r1在独立存储权限前失败未启AIR。所有失败原件保留；v3独立局部复核/恢复通过，停止泛化缩放资格，不部署。
- upcoming阳性完整环memo单方法诊断通过构建审计，2160/28与168模拟检查通过。2161逐点验证1080真实回调/1076命中，横汇总9.62%但最后原横窗异常高，纵反慢6.02%，完整长帧保留；停止候选，不拿局部扫描减少换成提速承诺。
- 正式A80/D8A/FE3回读未改，外来SceneRenderChecks不动。报告camera-scale-coverage-20261029.md，旧快照MEMORY-history-20261029-before-scale-coverage.md。无本轮自有进程/等待、无后台承诺，近原版目标仍未达。

## 2026-10-29 — 继续镜头定位，三个候选实测无稳定收益，正式版保持

- 当前A80/D8A/FE3七次隔离游戏完成并退出。frame-cost采48窗，1窗count mismatch失败保留；47有效窗支持移动pre-render/render增量，内存下降及分配次数不直接证明耗时归因。total getter低成本已测，private getter每次11–17ms不用逐帧。
- 环境键同实例2160/28与3000字段×两臂、五图通过，横2.90%/纵0.57%；炮塔13×120帧未见子树替换，后继同帧守护2160/28主循环带少约2ms但完整横/纵无明显收益。两候选停止，无部署；Math.max旧失败未重做。
- 对象层v2采满2700区间后旧360分组断言失败；16已执行检查/恢复通过，独立校验15×180区间、29边界、可见掩码和零绘制增长，原失败不改、末尾像素未做。[0]含阴影层影响较大但不是阴影独占因果。初版仅编译未运行。
- 阴影只读普查596个Box中124个alpha0滤镜根；随后透明阴影候选2160/28、五图像素0、124目标阳性及134540对恢复通过，却横29.133→29.692/纵29.147→28.167ms、横长帧增多，停止不部署。固定Box静止位置写入假说也无源码依据，没有生成候选。
- 只保存研究与记忆，不改生产代码/安装、不碰外来SceneRenderChecks。近原版目标仍未达到；局部变快不冒作完整帧收益。完整报告camera-motion-20261029.md，旧快照已归档MEMORY-history-20261029-before-camera-motion.md；无本轮自有进程/等待，无新后台承诺。

## 2026-10-29 — 安装真实产品镜头优化0.9.3，SATS与兼容复验通过

- 02:58:52部署CS D8A68A4C / WB0.5.10-scene FE3E7A84；根A80及DLC/其它模组/配置不变，保留原边界、天角兽、染色与SATS修复。CS同步四源，WB沿准确13源配方仅加同步恢复，不覆盖WB旧HEAD。回执camera-presentation-deployment-20261029.json已安装/回读通过；备份build/backups/camera-presentation-20261029-025849-fe3f35922315。外来SceneRenderChecks未改。
- 真实产品live-r1（AIR90840/225D32EC）1200/26：平均54.2817→51.05ms（5.95%）、P9569→65，max164→170/>100帧2→4；保留敌射、冲刺、awake差异。真实camera-r1（AIR71820/54E5DA8）2160/28：静23.3→21.7278、横34.7222→30.675、纵33.6528→30.3778；五图像素0，静/纵长帧计数仍增，不宣称全面消除卡顿。120fps诊断、42.422秒预热不是正常载入或自然跳跃验收。
- checks-v3-r1（AIR21012/B60366A7）1213项、7V、14SATS像素通过；缩放、三效果开关、场景重建和普通地图回退通过，48节点/2348alpha平衡。此前r1因原生resize打开菜单超时，v2误读内部vis/page并在finish再抛1069；旧失败保留，v2只按精确登记/创建时间等核对结束自有88440。v3用public World.vpip与原生onoff(-1)，三次下一自然帧恢复allStat1，未改产品或写暂停标志。
- 新呈现仅scale1/native320且RV（含wallbright）、WB、LAD全关；开效果/缩放/震屏/SATS原生回退。借用像素与事件复用，无自有BitmapData副本；当前有限优化不等于近原版。三项证据与实际依赖匹配后直接本机部署，没有额外重复跑完整矩阵。
- memory-r1（AIR88968/1325E7BF）1200/26只读观察有效，但3getter每帧平均19.2875ms，显著扰动，不当性能验收。六旧live尖峰中四次nativeBand、两次Stage外；后续先隔离getter成本，再考虑精确短采样，不能按周期/内存下降就称GC。全部自有AIR/JVM已退出，当前无新测试承诺。

## 2026-10-29 — 节点缓存纯镜头完整对照后停止，另保留v2产品验证

- node-cache-camera-r1，AIR67216、44CAE0F1、正式A80/380与RC239252DF；2160完整间隔/28断言独立复核，62157ms、23段边界全部保留，最低可提交9,702,670,336B。原生世界正常、无额外calc/删敌/强移玩家；本轮玩家1441.8/4320，逻辑点全帧在内，中央PNG身体可见，未逐帧身体框。暖图50.834秒非载入验收，77驻留等预绘计数不变，lastDirtyCount两次2→0→2如实保留。
- 横34.761→32.722ms（5.87%）、纵32.686→30.861（5.58%），静20.081→21.547退7.30%；横纵P95 42→43/39→41，>50ms 3→11/3→9。五软件图RGB最大1/alpha0、节点/缓存32对与alpha2464对恢复，无错误；内部缓存实际分配未知。停止node-cache/combo，无部署；其883帧平台超出5px的live失败不排名，不缩路线重试择优。报告camera-event-fill-node-cache-camera-20261029/RESULTS.md，raw A0051F7F/review68858C53。
- 另一路v2纯像素复用不受此停止决定混淆：后继BAAB独立报告为54.050→50.265ms，结合ABBA支持有限收益，仍有自然负载差异、不宣称精确因果7%或近原版。主任务正在准备必要产品接入验证；本次仅静态审查发现同步clear失败吞没后继续WB/SATS的问题并反馈，主任务修复中，正式A80/380不变。

## 2026-10-29 — v2像素复用动态检查完成，8.62%差值仍有负载混杂

- camera-event-fill-pixel-live-20261029-r1，AIR39012退出0，A80/380、实际RC239252DF、探针3B9444CB；1200完整间隔/26断言与独立raw核验通过，600候选全启用，玩家/六敌人身体框全程在内。无其他AIR，最低提交9,208,688,640B；177驻留和原生绘制计数不变，三边界/长帧完整保留。
- A53.767→B49.130ms表面8.62%，P95 68→66/max192→150，但>100ms帧2→4。玩家各200发观察，敌方1038/775、敌弹6.672/4.633、冲刺129/86；两对7.04%/10.22%均伴随候选负载较轻，不认作纯优化收益，不线性补偿。双方600帧均>33.334ms，未达到近原版。
- helper均0.205ms/最大10，revision=pixelOnly530、纯像素帧201、commands36；实际新路径和清理通过。报告build/generated/camera-event-fill-pixel-live-20261029/RESULTS.md，raw A43ED2C4/review FA257376。正向像素组件证明仍限同步draw，未新增自然Stage像素验收，无新部署。下一独立v1节点缓存候选待测，不写成有效。

## 2026-10-29 — 连续纯像素更新组件通过，性能仍待独立复核

- 旧pixel-checks-r1（219AE308、AIR28708）在原生选点changed=0时失败，315项组件断言含1失败、0计时间隔；恢复及15张临时图释放通过，失败原件保留。v3不改helper9D8F，只改为最多24次、完全基于原生输出的正向选点，没有放宽RGB≤2/alpha0或恢复门槛。
- v3-r1探针2CFF112C、AIR6496退出0，419组件/15外层断言通过。首次在cx3/cy13、屏912/516的16×16两次各256像素变化，候选prime后同一Graphics命令集连续更新，RGB0/alpha0；树事件+2/刷新+1、7fallback精确，55图释放、72节点/2592alpha恢复平衡。独立raw/源码闭包复核通过，报告build/generated/camera-event-fill-pixel-checks-v3-20261029/RESULTS.md。
- 只证明同步BitmapData.draw语义，0性能样本；记录时主代理已启动v2 live AIR39012，尚未独立核验，不提前填写收益。v1战斗仅1.10%且长帧未改善的结论保持，无新部署，用户近原版镜头/动态游玩目标未完成。

## 2026-10-29 — 事件填充真实战斗只有1.10%收益，不部署

- camera-event-fill-live-20261029-r1于00:54–00:56完成，AIR41048，正式A80/380、实际RC239252DF、隔离C8025771；1200完整间隔/26断言与独立原始数据复核通过。四窗均原生跟随、六LMG/ASSR/200px冲刺，玩家/六敌人身体框全程可见，600候选帧实际启用；无其他AIR，最低采样提交9,307,856,896B。
- 原均50.503→49.948ms仅0.555ms/1.10%，P95 63→64、最大149→157，>50ms帧222→229；两个配对仅1.88%/0.30%。玩家开火各200、敌人794/875、敌弹4.715/5.802、冲刺111/92，负载不完全相同，不线性补偿。全部间隔/三边界/长帧保留，177驻留与原生绘制计数稳定；helper均0.422ms/最大9，revision592/commands254，清理平衡无错误。不满足明显提速，无新部署，用户原目标未完成。
- 纠正纯镜头宽视口覆盖：event-bitmap-fill-r1横15.34%/纵7.92%、五视角像素零差异仍是有效同图邻近地形证据，但静/横玩家逻辑点在视口底边外80px，纵128/720点内且无bodybounds，不能称玩家始终可见或替代真实战斗验收。旧“宽视口拆分玩家仍在视野”强表述撤回，旧数字/指纹保留。
- 下一步仅准备v2：验证同一BitmapData纯像素revision是否无需重发Graphics，正向像素变更及恢复必须先通过；几何/身份/树变化仍须重建或回退。未宣称方案已实现有效。详细报告见build/generated/camera-event-fill-live-20261029/RESULTS.md及knowledge/experiments/camera-sats-current-20261028.md；旧驱动、helper、产物、回执均未改。

## 2026-10-29 — 宽视口显示层拆分完成，SATS批量旧失败复核

- camera-nearplayer-layer-split-20261028-r1于00:06–00:08完成，正式A80/380不变，AIR76296，2160完整区间/22断言、独立camera-layer-review有效。实际2032×1084，A完整/B暂隐4地形/C暂隐6对象按ABCCBA；静/横/纵均值A20.096/32.896/36.908ms，B22.958/28.117/27.042，C16.208/25.133/26.013。地形与对象显示都涉及移动成本，但暂隐只作诊断，条件差不可相加，不称已优化或近原版。
- 原生世界持续、无删敌/强移玩家/额外calc；四轮准备34.058秒后计时图块预绘/重绘计数零增长，17边界与4条件切换完整保留，最大110ms。10层2161次状态观察/应用与最终恢复通过，不扩称逐像素恢复。无其他AIR，最低提交9,749,286,912B，持登记等待3次空闲共2.079秒后启动、runnerCompleted=true；没有新宿主/产品部署。后继先检查由内容变化事件失效的缓存与旧扫描失败路线是否不同。
- SATS批量调查只读结束：旧33C1已采用整数格外接矩形单draw/copyPixels拆回原格、1920上限，旧r4七组像素失败，墙影边缘RGB最大3/alpha2；只改回原尺寸逐格后通过。当前全驻留源可见性不同不足以证明可修旧误差，未生成SatsBatchCaptureTrial、未编译/AIR；A80/380及SATS提交180d46f保留。详情knowledge/experiments/camera-sats-current-20261028.md，外来SceneRenderChecks未动。

## 2026-10-28 — SATS视野截图完成验证并部署，镜头性能仍待解决

- 后续有效定位：camera-nearplayer-tail-20261028-r3，正式A80/380、RC EB6，AIR83080退出0，2160完整区间/18断言/12CPU尾段窗独立核验通过、attributionReady=true；无其他AIR，最低提交10,663,690,240B。setZoom后等自然帧，中心840/4320经范围夹取、玩家481.8/4320仍可见；六轮预热44.371秒后图块warm/draw零增长，dirtyCount变化2，不扩称所有栅格工作为零。静/横/纵21.972/29.593/29.126ms，Stage7.047/7.129/7.388ms，均仅诊断；CPU尾段26/50/53样本，移动增量主要原生pre-render/render，非GPU毫秒。r1/r2占用冲突0PID保留，r3持登记的有界等待3次空闲核查2.078秒成功。少量RC单人UI/refresh栈已按既有授权协调负责人；后继准备A完整/B暂隐4地形层/C暂隐6个visObjs层拆分，尚无镜头修复部署。SATS提交180d46f保留。

- 原生V同图ABBAAB开启观察原842/891/713ms、候选144/235/184ms，截图位图84/94/95→16/16/16；目标/AP及真实V关闭恢复通过。此为开启成本依据，不是整游戏FPS。产品保持源图大小/原点，按可见块截取，平移/缩放新曝光补截，返回复用冻结像素，关闭/重建释放。
- 实际A80ED32B/CS0.9.2 380DEC30产品AIR67780退出0，336断言、7次原生V、全关/全开14像素用例零差异、真实同Grafon/Location重建28旧副本全部清理，普通模式原生回退通过。宿主四方法窄改，其他3281主ABC方法体、350类和5038原始tag保留，边界修复/天角兽/loader保持。初版F64产品检查器跨域取类1065（1断言、0V）仍记失败；后继增加API统计入口后独立验，不伪造旧检查通过。
- 22:55部署并最终回读通过：根pfe A80ED32BEE50C612CB46EA1E581C8CA9C81072E0B9E6EE1A51E5BACEFBDCBA19，CS380DEC3068938B3E3BA1F2C8DB25A6B3D5FC229E8526E8FC03CA23795961E111；同步两份产品源码。唯一备份build/backups/sats-visible-20261028-225528-7ef578cb234b保留此前B84F/9A5E及旧主源码；回执state/sats-visible-deployment-20261028.json，门禁build/generated/sats-visible-release-20261028/verification.json。用户配置、玩家存储/进程、其他模组不动；RC负责人既有EB6D11E6按原指纹保留，foreign SceneRenderChecks未改。
- 镜头未解决：旧纯镜头静26.256/横31.183/纵31.822ms仍保留，但后查同回调setZoom留下旧Camera坐标，路线中心961/2880而玩家1441.8/4320，不能当正确玩家中心路线验收，原scale缺失不能倒填。keycache v2/v3分别约62.53/65.41秒后六轮预热不收敛，均0计时间隔；v3已等自然帧修正坐标，原因仍待分析。宽窗口自有鼠标消息入队但原生Stage/命中阳性失败，0样本，不排除热点、不换路径重试。详情knowledge/experiments/camera-sats-current-20261028.md；后继须保留当前A80/380重新冻结测量输入，未部署镜头候选。

## 2026-10-28 — 马哈顿载入鼹鼠 Unit.run #1010 修复并部署

- 用户确认地图为马哈顿废墟。受控原生鼹鼠在普通48×25房间两侧边缘墙体分别触发同一Unit.run #1010：横向墙体修正使X1=-15或X2=1935，后续垂直读取列不存在。不是先假定合并坐标错误，也没有吞错/删除单位。
- 仅守护Unit.run四处列读取，有效路径每查格增加dup/iftrue两指令；主ABC其他3284体及全部5038其他原始标签保持、完整ABC可逆、原1719指令仅重定位分支。未重新编译Unit类，现有天角兽/染色/镜头和loader保留。
- base-r2实际左右两侧复现；候选fixed-r1恢复并完成马哈顿第五阶段普通/大场景各3次进入。正常轨迹v2两轮各153断言，12动作×12帧144状态完全相等。玩家并行但私有存储/桌面静音，明确无帧率资格；全部自有进程退出。v1 protected shX1读取是探针错误，原失败和后继分开保留。
- 部署根pfe.swf：4E5FAB45→B84F24280B3C676F4068E1CDC5A6EBEE89988F62BCF7A44D4DD71A4771360184；CS9A5E及其他SWF/名单/描述符不变。备份build/backups/unit-boundary-20261028-183436-e481f4a8，回执state/unit-boundary-deployment-20261028.json，详细报告knowledge/experiments/unit-prestep-boundary-20261028.md。正常重启生效，未动玩家存档/进程。
- 性能仍未达到近原版，本轮无性能候选部署；后续须保留B84F并重核旧夹具基线。foreign SceneRenderChecks仍不提交。公共机制另存physics-collision/discoveries/unit-run-boundary-column-1010.md。

## 2026-10-28 — 活动范围候选编译完成，后续诊断资源受阻

- 已审查并实际编译当前0.9.1范围载体D90F01DF、六LMG探针5019EC84，两个exit0，精确回执在camera-activity-range-current-20261028/builds/r1。离线编译独立2GiB/1GiB门与512MiB堆上限；AIR门槛不变。后验只证明Stage -1000时点，不扩称全帧安全。
- tail-r2在创建前因3,974,184,960B可用提交被保护拒绝，无PID。新有界等待入口实际运行180.016秒/36次，tail-r3回执notReady，最高2.59GB、末次2.08GB，没有调用目标、没有AIR；全部自有进程退出，未无限等待或打断其他程序。
- 记录提交a066730保留当前普通/连续实测、两候选源码及有界入口。仍未接近原版、没有新性能部署；后续需有资源时跑tail-r4或range-r1并验证真实阳性。foreign SceneRenderChecks未提交。

## 2026-10-28 — 当前RC2普通/连续真实参照完成，尾段与活动范围仍待实测

- RC负责人部署0.2.24-animfix2，正式SHA256 F14A44E74AC98EC480875203D4D714ACFBC496141980E5A1D7B0DE0C7AD222FB；其余正式输入保持。本性能回合无新部署，不覆盖他人更新。
- camera-dense-reference-rc2-20261028-normal-r1/scene-r1各1200原生六LMG/ASSR冲刺间隔通过独立核验，AIR56856/67024退出。普通均35.510833ms/中位34/P95 46/最大123，大场景59.570ms/中位58/P95 75/最大167；Stage监听段10.53211/20.20517ms（各1199条），native带9.05833/18.85917ms。计时无新warm，scene常驻130块、普通0。体验参照保留自然群体差异，不称纯渲染/GPU因果；旧RC固定镜头55.492ms仍为有效历史。
- 尾段addon已编译07CFFC4F48993CA50201EF84DBAA9299E5C1FBA9C78B255F4D2E9A6A47C921EC；r1在AIR前资源保护失败，无PID、无样本。camera-activity-range-current-20261028最小build/run准备完成，未编译、未AIR；永久参战锁不变。后续资源适配只针对离线编译，不降低AIR4GiB/2GiB预检与512MiB运行保护。
- 纠正停止路线范围：farparking实际含Box1202/Bonus125个显示根，不能当对象数或仅睡眠敌人；range每候选帧至少711个Box根移出父层，收益仅2.15%且四对反向。frameChanges=0是未更新默认值；严格静态资格普查剩0，未测到屏外阶段。不重启同一路候选。
- 证据见knowledge/experiments/camera-live-reassessment-20261028.md、对应两份summary与tail构建/失败回执；接续tail或activity-range实测。权限、拒绝路径及foreign SceneRenderChecks全部保留。本次仅更新MEMORY/journal，未git提交。

## 2026-10-28 — 新正式组合下真实战斗复现，固定镜头仍持续偏慢

- 用户继续报告镜头、角色动作与活动敌人/子弹卡顿。保留另一任务已部署的4E5F/CS9A5E；本性能回合没有部署。低内存纯Python诊断宿主51C90D99构建成功，5770其他方法体/1016类/5038标签与当前报警修复保持，未获运行时/性能资格。
- 修复测试自己的私有存储重定向识别；旧失败配方与回执冻结，无AIR的8fa登记按证据恢复。新silent种子实写/回读/拒绝覆盖通过，只涵盖原生Snd。已知构造器前失败清launching，未知创建失败仍保守。
- camera-live-current-silent-20261028-r1真实AIR39128完成退出，1200连续实弹/冲刺间隔与26原断言通过，独立验证再次通过。follow均59.398ms，held55.492ms，双方开火和在场子弹相近。固定600帧全>33.334ms；Stage混合约20ms，余量不能直接称GPU。最低提交3.80GB，无他人AIR争用。
- 当前普通/大场景同六LMG旧7F1F0B探针后继已准备，优先测当前普通参照。静态物体已广泛原生缓存、全图对象父层无巨大全图缓存的旧证据已复核，不盲目重做合图或逐物件缓存。详情knowledge/experiments/camera-live-reassessment-20261028.md；仍未达到近原版目标。

## 2026-10-28 — 天角兽局部报警与接力概率已合并部署（会话01a151d4）

- 用户明确要求合并部署并新增0–100%接力概率；替代10月21日仅候选限制。CS0.9.1默认0%，同一警戒每接收者只抽一次，budilo与telepat共享资格，原版恢复平静/明确重置后可重新判定。每一跳为发送者居中1920×1000，跨旧房边界。
- 当前A796宿主上仅移植UnitAlicorn五方法；其他5766方法体、所有类布局/旧常量/其他SWF资源保持。31项实际原生方法与设置验证通过：0/100/中间概率、原生control接力、两个传播路径、矩形边界、普通模式、重置、配置重启。进程73456/83744退出，真实存档未写。
- 正式宿主4E5FAB45、CS9A5E24E1；部署前备份和并发指纹核对，安装同一已验产物后回读一致。编辑器及其他模组SWF/名单保持。回执state/alicorn-alert-deployment-20261028.json，报告knowledge/experiments/alicorn-alert-release-20261028.md。运行中的游戏须重启。
- 这不是镜头性能修复；其他会话性能配方仍绑定旧A796/7F1F，继续时须显式复核基线，不能覆盖回旧整包。保留其camera-environment-paired与SceneRenderChecks未提交内容，未发送跨会话消息。

## 2026-10-28 01:44 — 恢复后三回合同一资源条件，目标已标blocked

- 上一回合确有同图配方与静态审计进展，不是完成性能修复。本回合01:43:49确认提交余量2413924352B，物理10440192000B，仍不足以构建/实测；新build.json、retained.xml与r1运行目录都不存在，未启动新等待或Java/AIR。
- 已完成必要独立准备；同一资源条件在恢复后连续三个回合重现，update_goal返回blocked，停止自动空转。目标保持完整且未解决，正式A796/CS7F1F与F15候选未改。用户恢复并使资源稳定后从paired构建/同图对照接续，重新开始阻塞审计。
- HEAD e43509a，仅保留foreign SceneRenderChecks未提交；无新部署、无外部进程干预或额外协调消息。

## 2026-10-28 — 新增同图交替原始/缓存对照，减少跨次地图准备差异

- 回读native-once首对：计时起点resident133/117、redraws136/124不同，各轮内部虽然稳定，不能视为完全相同的渲染输入。7.7%仍只是线索；不覆盖旧回执。
- 新camera-environment-paired-20261028在同一诊断宿主内选择原始51字节与F15缓存274字节，公共选择分支计入两臂；静态核原字节、分支/栈通过，493字节方法，原常量无诊断属性。完整宿主审计、编译与AIR仍待，不部署。
- 16×120区间正反顺序，继承原生单次镜头更新；helper5D8E2084、85源/114配方/77夹具，9个Python可解析、生成器一致。双150环境情形、1921/1920计划捕获、模式恢复、20位图精确及完整区间均为待运行断言，独立核验脚本已准备。
- 当前资源仍约3.4–3.9GB可分配，已开始一次有界等待后构建；原门槛不变，不停止外部实验。本回合有静态配方和对照设计进展，根目标保持未完成。
- 等待已到期：486466b0/BC253BDA，末次3579019264B，无Java/AIR/构建产物或运行句柄。恢复后第二回合仍遇同一资源条件；若下次第三回合重现且无必要独立工作，按blocked审计停止空转，不把反复等待写成测试进展。

## 2026-10-28 — 新驱动首对实测通过，约7.7%线索仍受内存波动影响

- native-once冻结2F7B/9b56efbf，base-r1 AIR24656、cache-r1 AIR70412均完成并退出。两边150环境情形×20字段、960坐标、961原生目标计划、零计时额外calc、监听器移除全部通过。候选F15功能验证通过，正式A796/526文件未变。
- 移动均值26.5667→24.5278ms、P95 36→32，观察约7.7%；两轮最低提交余量569774080/787353600B均接近保护线，静止也变快，不能作因果/稳定收益。Stage主循环移动差约0.23ms，余差混合多种开销，不称纯GPU。独立pair-review A5471DA2，未部署、未达近原版。
- 增加启动前有界5GiB稳定等待，不改原4GiB启动和512MiB运行中止。cache-r2初次180秒超时、没有AIR/运行目录，receipt096eab73/6CDA3A58保留。同名可新等待复测；已执行源码和配方冻结。
- 已按一次授权协调实验窗口，对方确认自动续批且不能安全暂停，窗口从未开始；无额外消息、无终止。01:12系统与进程可分配余量同为2165501952B，未发现内存工具误报；没有改系统设置。下一步同探针cache-r2/base-r2及normal参考。
- 补记：cache-r2第二次300秒等待到期，末次1633095680B，无AIR/无运行目录，receipt499f715c/3FBE8FA5；等待不计作完成测试。当前无自有句柄，保持active且目标未完成，本逻辑回合实际已有两轮AIR新进展，不沿历史三回合直接标blocked。

## 2026-10-28 — 恢复目标，修正额外镜头调用，获实验时段协调授权

- native-once新配方准备：Stage优先级500只设置目标，原生World.step更新，-1000逐帧核实际相机；计时额外helper calc拒绝，保留960完整区间/窗口边界。旧quiet额外调用已由原生源码和采样区分，此修改是测量修正，不是产品提速。生成helper EC96356E，85源/526正式/105配方/71夹具静态通过，未编译/AIR。
- 可见运行器进程组无明确内存cap；系统承诺余量仍2–3GiB，不降低4GiB线。用户允许向云宝实验对话01a17835-6129-7440-9bcc-0382b03fef3b协调一次10分钟自然批次间窗口；已发送，等待实际就绪，不干预进程或实验规则。新probe未构建，原F15/正式版不变。

## 2026-10-28 — 连续三回合内存阻塞，目标已标blocked

- 第二自动接续确认57628结束；可分配余量短时5.49GB，cache-r3初始预检3.97GB，再次未启动AIR。失败保留，既有4GiB线未降低。没有游戏/Java运行句柄，没有正式部署或跨任务消息。
- 同一资源条件已连续阻塞3回合，update_goal返回blocked；镜头问题未完成，不缩小目标。用户恢复并使余量稳定后从cache-r4、同一ef6149a0探针接续，交替当前/候选排除背景变化。候选40%分配下降不能替代帧率证据。

## 2026-10-27 — 环境键缓存消除65312次分配，无采样候选等待内存

- 第一自动接续：余量3.04→2.47GB，无AIR。83808已退出，同一外部实验下一批57628实际在跑约5.56GiB；未干预、未发协调消息。核四成功轮系统余量下降1.78–2.11GB，不能冒充AIR私有峰值，也不足以降低预检线。当前连续内存阻塞2回合，下回合重新核查，满足第三回合阈值时正确标blocked，避免空转。
- 补记：cache-r2完成528文件准备后提交余量4.31→4.06GB，在AIR前二次保护停止；随后2.93GB。无遗留测试实例，下一次cache-r3；未降低4GiB线。50个源码/记忆文件提交6567c4d，不含生成SWF、原始大证据或foreign WIP。
- 短窗CPU/分配采样定位sceneNativeEnvironment：65312次/40区间。clamp不足1%无效；keycache候选F15B从A796只改一方法，audit F0A8核其余5770方法/1016类/素材不变。实际AIR70744复用同探针，环境分配降0、总分配约降40%，allocation-review DC3B6B17；未称帧率改善、未部署。
- 无采样86源098F/ef6149a0的base-r1通过：150情形×20环境字段/完整960时钟，移动均值21.8458ms，base-review7E595DC7。cache-r1在AIR前2.70GB提交余量失败；只读确认另一个实验Python83808约6.76GiB，未中断。用户选择处理其占用，随后需交替当前/候选避免背景负载误归因。
- 共享启动器ECE3/资源86D/登记器E3由ModLoader负责人修改；精确回读新链。policy-normal原末检因唯一UTF-8变动失败，后验5539957F核实际证据，不改原失败记录。正式526/13运行保持。
- 源配方分五新目录sampling-policy/allocation-stacks/environment-clamp/environment-keycache/environment-quiet，均20261027；结果见各RESULTS。foreign SceneRenderChecks未动。镜头根目标仍未达到。

## 2026-10-27 — 探索历史配对完成，接续共享启动策略后的镜头采样

- fog-history-normal-r3完成960区间，AIR37804退出。1200格局部遮罩及全部960镜头坐标配对通过，pair-review B5DC4EA1；先前黑区差异来自夹具进入前探索历史，不据此修产品。随机装饰仍异，大场景scene-r2尖峰保留，不作稳定均值比较。
- preparation-memory-r2八阶段完成，主Python私有内存峰值约44MiB，未见GB积累；无Java/AIR，回执ABC25564。旧玩家记录无相机/产品指纹，不能作当前镜头证据。
- sampling-scene-r1在编译前因共享启动器漂移失败，无Java/AIR。后继policy配方只读接入ECE3ED08/86D5F280策略并记录实际回读，87源、采样行为保持。已静态准备，scene-r1登记等待；保护门槛不变，无部署。
- 记忆归档MEMORY-history-20261027-before-resource-policy.md；旧配方/失败证据冻结，foreign SceneRenderChecks不动。

## 2026-10-27 — 补记：第二次普通房间启动前中止

- 用户再次释放内存后，normal-r2仍在副本准备后的二次预检4500684800→3895889920B中止，没有AIR；原失败保持。追加复核scene-review-v2 C2F73741，目标房间对照仍未完成，下次normal-r3。
- 新camera-preparation-memory审计只准备隔离副本、记录本进程内存；r1初始3333734400B即中止、无阶段数据、无游戏或编译器。继续保护线，无正式改动；报告见该目录RESULTS.md。

## 2026-10-27 — 探索历史大场景侧完成，短时调用栈诊断待内存恢复

- fog-history-scene-r2完成960镜头区间与可见原图检查，独立核526正式/13运行/86源，scene-review D4CFA81B。AIR77000退出；probe D4B5DBE6/result F6ADC369。目标房间探索状态计时两端全等，但不能证明中间零写入。
- 本轮29个>100ms长帧、最大1068ms，不拿均值作稳定性能基准。normal-r1在AIR前内存4859768832→3303354368B中止；scene-r1早先编译前4266745856B中止。两失败保持，下次normal-r2复用已冻探针。两模式探索历史假设尚待对照。
- 用户再次选择释放内存继续；两Windows读数核实物理空闲约19.2GB时可分配仅2.87GB，后降1.58GB。未降低4GiB线、未结束用户程序。测试程序导入约19.1MB私有内存，不能因此排除整个准备阶段的峰值。
- 前轮atlas维护仅额外0.08–0.31ms，缓存内容/绑定/分配计数零增长，停止这项微调。新sampling配方八窗各五区间CPU栈、100000上限，按CPU自身时间验出现次数、保留混合流诊断；已静态准备，未构建或启动。
- 报告build/generated/camera-visible-room-fog-history-20261027/RESULTS.md；前快照MEMORY-history-20261027-before-fog-sampling.md。正式安装不变、没有部署，foreign SceneRenderChecks未动。继续镜头主线，先普通房间对照，再新调用栈诊断；目标active未完成。

## 2026-10-27 — 有效原版内景参考，合图内景收益仅4.37%

- reference平台检查失败0样本；scout扫描真实地形选3,3局部(940,640)，同字节普通/大场景各960全镜头坐标和地形哈希一致，角色屏内且镜头未钳制。原图实看：原版16–18ms移动、场景25–29ms；装饰和探索遮罩不同，不称像素等价或纯因果。
- 同内景1920段原绘制/1280合图正反22.4569→21.4750ms约4.37%，横移更慢，六移动配对四好二坏。五视角RGB1/alpha0/恢复精确，20比较图和32缓存图释放。200MiB预分配238ms，测量无新增分配，原生预绘零增长。未部署。
- 四AIR59228/72668/47188/53408退出；atlas-r1余量4206452736B<4GiB编译前停止，恢复后r2通过，旧失败保留。独立review0A312FDD/E2C14761，526正式/13runtime和86或87冻结源保持。
- 继续镜头主线：暂停微调页缓存，核对内景探索遮罩差异与Stage间实际绘制/回调来源，旧鼠标3%路线不重试。报告build/generated/camera-visible-room-atlas-20261027/RESULTS.md；前快照MEMORY-history-20261027-before-visible-reference.md。无正式修改、权限请求或跨模组写入，foreign SceneRenderChecks保持。

# 开发日志

## 2026-10-27 多次横向战斗改善约13%，RV组合仍不稳定，未部署

- 七次AIR：repeated完整20×60，61.950→54.045ms/9对改善；两jump各9/0窗口越原平台失败；pagesize仅约4%且反向变慢/内存翻倍，不采用。失败保留，不放宽边界、不改原物理。
- 确认RV读取上一帧合图的风险：四态真实Flash旧第二态错1600像素，新只读原图接口全部精确；12图释放。正式D44六源派生到CS隔离候选，未修改正式RV或其他模组源码。
- 完整current两轮95.710→92.180、107.898→106.187ms仅3.7%/1.6%。首轮终局恢复自身807像素差失败；后继固定7图两次RGB≤2/alpha0与精确恢复通过，但未重现旧异常，原因未确认。功能通过不等于性能达标。
- 总报告rv-pixels/RESULTS.md；前五轮独立闭包9EF4773E，两RV轮BF377949，526正式/13运行/冻结源/显式RV覆盖均核对。前快照MEMORY-history-20261027-before-persistent-rv.md。正式安装和foreign SceneRenderChecks保持。
- 内存已足够，无待答问题或新护栏拒绝。原登记显示过滤把null当空字符串不成立，已纠正后续查询；实际驱动锁/AIR门槛一直有效。目标继续，优先实际移动分段、真实纵移路线及剩余兼容，不再增大合图页。


## 2026-10-27 持续绑定镜头改善，实际战斗尚不稳定，无部署

- 用户释放内存，完成checks/fullpage/combat-imports三次AIR；另保留初始内存失败和combat缺导入编译失败。总体报告fullpage/RESULTS.md；前快照MEMORY-history-20261027-before-persistent-runtime.md。
- 两次无敌人活跃模拟/1920×1080/2880区间：持续绑定移动27.853→23.833约14.4%；整页内容28.585→22.028约22.9%，但强制缓存静止变慢。16状态真实Flash、五视角RGB≤1/alpha0及资源通过。
- 实际30fps设置、六SMG/原生冲刺开火/480区间：49.721→45.888约7.7%，P95 62→63、一对反向。终局画面与恢复通过，X移动/Y固定，仍不足部署。已实际查看两类PNG。
- imports原汇总内部VERSION遗漏而失败；独立review仅修验证常量后其余完整检查通过，原失败/登记不改绿。quiet-review76FD97F9，combat-review839341D8；526正式/13运行与89/86源全部核对。
- 三AIR均退出、最后占用空，正式及foreign WIP不动。目标继续：短周期多次交替核实际战斗波动，随后纵移/原版参考/RV和生命周期。无新护栏拒绝，无待答内存问题。


## 2026-10-27 持续合图候选准备完成，内存预检停止，未构建或部署

- 新建camera-persistent-atlas与camera-persistent-atlas-checks两配方，均-20261027。减少逐帧原图显示切换/索引重建，保留源revision/身份检查；事件通知只管理集合。实际收益未知。
- 首次runner在编译前提交内存2877861888B未过4GiB，保留-r1失败。后续仅检查内存/代码，未编译、未AIR；已向用户请求释放内存，未重复请求。首次目标轮内存停点，未标blocked。
- 后继预备16状态真实Flash夹具，132源位图/34截图及精确恢复；尚未执行。三臂2880间隔预案、非请求页隐藏、两呈现器独立清理。89预期源码。
- offline_review.py成功：526正式/13运行输入一致、Python/生成来源核对，报告DB4E5C6A，提交3316633600B/AIR空。不能称编译或性能通过。报告checks/RESULTS.md；前快照MEMORY-history-20261027-before-persistent-atlas.md。
- 正式安装、foreign SceneRenderChecks、其他模组不改；无新保护拒绝。内存达标后先编译/夹具/三臂，收益确切才进入真实镜头战斗与兼容验收，目标继续。


## 2026-10-27 可见大视口归因与透明图块对照，无可部署收益

- 五次AIR，526正式/13运行库/86或87冻结源全部复核。报告camera-visible-components-20261027/RESULTS.md，统一review9EC414B0；前快照MEMORY-history-20261027-before-visible-components.md。正式与foreign WIP不改。
- 完整显示树第一遍15680，第二遍45空子槽拒绝计时。四9700/5000外边框关闭缓存无综合收益；全不透明仅1张且屏外，正确拒绝用帧率评价。
- 1920×1080图层控制保留6720间隔，地形隐藏六移动配对同向改善，原生光照无稳定收益。原汇总假设EXIT_FRAME一次错误，实际15738；后验只核时钟/坐标，保留门槛失败及逐区间覆盖未知，不称物理FPS/纯GPU。
- 完全透明162张显示解绑，每帧35–53张按原cull可见，1920间隔移动24.9375→24.9264ms仅0.045%，横向更慢，不部署。五视角RGB≤1/alpha0、20图释放、1944解绑归还；无新地形位图。
- 五AIR均退出、最后登记空。允许Unit.as读取纠正blit近远切换推测；未重试旧受拒源。下一步查有内容地形的合成/更新契约及更密集内景，避免继续缓存微调。目标保持活动。

## 2026-10-27 纠正黑区镜头基准，近景缓存仍无明显收益，未部署

- 四冻结程序/六次AIR完成，526正式/13运行库/86或87源与全部时间戳独立复核。报告camera-native-visible-groups-20261027/RESULTS.md，bands/verify_batch.py，review121667E8；前快照MEMORY-history-20261027-before-active-quiet.md。
- 重要纠正：active-quiet-axis/bands同房同坐标四轮主菜单/活跃模拟正确，但中心Y600在角色平台Y120下方；near-groups保存PNG实际查看几乎全黑。原始计时保留而撤回代表性，不能称正常原版/大场景差距或纯GPU定位。
- visible-groups改为玩家居中，保留原分组类字节，五图覆盖60.5%–73.4%，1920样本角色在视野内，原生/候选完整PNG已查看。15根/5组：移动19.9806→19.8639ms仅0.58%，纵向稍慢、多配对反向，不采用；静止16.2875→15.9125也配对混合。
- 五视角软件RGBA精确、20图释放、210移入恢复、五容器清空脱离、地形预绘计数零增长。仍未验真实战斗/自然跳跃/门等生命周期/RV和Windows呈现。正式不动、他人SceneRenderChecks不动，无新保护拒绝。目标继续，以可见镜头与有效原版参考为前提，不重跑已失败缓存微调。


## 2026-10-27 屏外暂存进入真实镜头战斗，收益仍不足，未部署

- 新增七目录，一次编译失败/八次AIR。window完成20×60区间，47.258→49.658ms，逐根管理5.875ms使平均更慢；math管理降4.182ms仍慢至51.292且坐标审计失败。range按82组管理降0.913ms，总帧49.292→48.232仅约2.15%，四对反向、最大帧更差，不部署。
- window/range末尾单视角软件像素精确、Location.remObj不复活、根/窗口清理通过。range玩家400/敌人885开火帧；相机每窗X跨度206–276，Y固定。不能称无敌人、跳跃或完整交互/RV验收。
- 首编译返回错误、return监控长空档超时/晚显窗口后allStat2、math预热内存中止、groups/safe-groups读取不存在lurkBox/lurk均原样保留。后者改为玩家/镜头近区保留，不能再猜公开字段。保护拒绝一次联合原版UnitPlayer与旧辅助类读取，未换路重试。
- 526正式/13运行库/86源与时间守恒独立核验；原始证据同名-rN，完整报告range/RESULTS.md，旧快照MEMORY-history-20261027-before-live-parking.md。他人SceneRenderChecks不动。目标继续，下一步转屏内绘制并补有效原版/纵移/无敌人基准。

## 2026-10-27 屏外高覆盖摘树得到约7%镜头线索，尚未部署

- 五次AIR/一次编译失败，新增六目录配方及独立核验。visibility原生预热图失败、warm资格变化/清理审计失败、cohort编译失败均保留。counts对1170根完成960区间：隐藏移动33.896→38.008ms，停止；native-static-cache合格目标0，未计时。
- detach对1203根完成960区间：移动34.325→31.921ms、两对−3.017/−1.792，P95 43→39；静止20.613→20.971，最大移动104→161。10组像素精确、13233摘/放平衡、六层顺序恢复、150截图与边界探针释放。只作正向线索，不能称纯矩阵成本/实际战斗/近原版。
- 两有效轮随机对象不同，不跨轮直接归因；排除不稳定根分支未触发，仍未验。五轮独立核526正式/13运行库/86源和时间守恒，AIR全退出、最终登记空，正式/foreign WIP不变。
- 报告camera-far-live-detach-20261027/RESULTS.md，旧快照MEMORY-history-20261027-before-far-live.md。下一步先查动态世界的父节点/移除依赖，再决定实际候选，目标继续活动。

## 2026-10-27 原生auto更慢，保留上层特效仅小幅移动收益且静止倒退

- 同世界窗口路线先两轮像素失败，固定转移后draw一次再三次精确往返，第三轮e2707a70完成1440区间；原direct移动33.7375、新direct34.0375、auto42.6583ms，auto两对慢8.5/9.3417ms。95图释放，两个新窗口异步关闭，原Stage/根顺序恢复。原两次失败保留。
- native-quality 5c7d344d实际1440区间全HIGH；桌面AIR忽略MEDIUM/LOW，汇总器拒绝错误分组，未降正式画质。文档与实测核对后记shared-knowledge/rendering/facts/desktop-stage-quality-limit.md。
- 新native-effects-overlay d5aaa840保留七个上层为原生、缓存九个下层；960区间移动31.858→30.463仅4.4%，静止22.254→29.742回退。480角色draw3584ms/2397块刷新4979ms，无上层重画或计时分配。13角色oracle精确但全图RGB71–125拒绝，40CPU/30纹理/260图释放，157临时写入恢复。未部署。
- 五轮全部独立输入/资源/时间戳核对，测试实例退出、登记空，正式526文件与13运行库保持。完整报告camera-native-effects-overlay-20261027/RESULTS.md；旧快照MEMORY-history-20261027-before-native-windows.md，foreign SceneRenderChecks未碰。
- 根目标仍活动，停止auto/无效画质/上层边界微调。下一步核屏外滤镜/动画根是否属于旧静态筛选漏测，先做窄归因；不能把原生移动或世界暂停测试当实战验收。

## 2026-10-27 角色图像缓存七轮验证，仍未获得可部署的镜头提速

- sprites移动34.246→57.463ms、direct31.867→57.992ms，均倒退；后者消除计时分配仍无收益。frames/checked两轮0计时失败，异常栈定位只读nestedBlends中的空子节点；scan修正清点后33.950→38.679ms，姿态池3065命中/1441未中/1438淘汰，仍慢。
- atlas按变化根合批，把GPU区间draw降至480次/3629ms，移动32.800→32.442ms仅约1%，画面RGB97–252拒绝。atlas-checks在同一世界1440区间比较：原生32.925、检查GPU35.804、默认异步36.583ms；关闭图形调试无收益，不能据官方同步说明推翻实测。
- 所有完成轮前后像素都拒绝。5轮计时完成、2轮原失败保留；7轮独立核526正式/13运行库/86源及连续时间戳。全部资源/临时矩阵恢复，7个AIR退出、最后测试登记空，正式版本不变。总记录camera-actor-atlas-checks-20261027/RESULTS.md。
- 目标仍活动。停止继续微调小图缓存参数；下一步回原生路径找结构性开销，真实AI/弹体、无敌人移动、OS窗口、RV等尚未验。旧快照MEMORY-history-20261027-before-actor-cache.md；foreign SceneRenderChecks未碰。

## 2026-10-27 活动动画分层缓存与局部更新完成三轮，仍无净提速

- layer-dirty 448ed0d2保持Flash时间轴，960区间移动35.721→42.679ms倒退；角色层480次重画更新20.973ms/区间。layer-tiles bd8ebe9d首7块64ms，角色层oracle1364像素RGB128/alpha24失败，0计时，原失败保留。
- layer-region fccbb003固定坐标一次draw中性角色层，13完整角色图oracle RGBA精确，960区间33.979→34.971ms仍无净收益；每区间更新11.844ms（含原生draw8.790ms），无计时分配。全图RGB121–184/alpha0拒绝，不部署。
- 三轮verify_run核526正式/13运行库/86源和工具输入；全部图像/纹理释放、层隐藏恢复平衡。AIR66260/64548/9832退出，最后登记空。原生/候选全图及角色层失败PNG对均实际看过；详见各camera-layer-*目录RESULTS和review。
- 正式A796/CS0.9.0保持，目标继续。下一步小范围验证已有Bitmap/帧图像的直接复用，避开每帧栅格化；旧census的78 Bitmap主体仅线索。合成大色差、实战/窗口与生命周期仍未解决。旧记忆存MEMORY-history-20261027-before-live-layers.md；foreign SceneRenderChecks不碰。

## 2026-10-27 阴影根批量剔除像素精确但未提速，原生GPU模式没有显示优势

- region-prune原生效果外延保守筛出475个远处阴影根，仅一次整树draw期间隐藏并立即恢复；13次512区域与未剔除原生RGBA完全一致。960区间移动31.467→26.654ms，区域CPU仍13.146ms/次，未突破此前约26ms。489CPU图/8纹理/260像素图释放、234175隐藏/恢复平衡，清理通过；停止继续扩大每帧区域draw的剔除优化。
- native-direct/gpu复用39a87632/EE82同一探针，各960，逐帧镜头路线与房间/视口相同，实际mainMenuOff。组合移动22.113/23.292ms，未见大幅优势；两世界149/155单位、玩家初始x不同、时间轴活动，明确不是纯模式因果效果。软件截图稳定不证明GPU窗口/滤镜，未部署。测试模式描述符全文/指纹留档，runtime/application.xml原字节B0375AD1恢复，根描述符未改。
- verify_run/verify_pair独立核对526正式/13运行库/86源、工具输入与2880连续区间。AIR31884/33656/31736退出、登记空。详见camera-stage3d-region-prune-20261027与camera-native-gpu-20261027的RESULTS/review；foreign SceneRenderChecks不碰。
- 根目标仍活动。下一步追清已有Bitmap图像与实际变化/失效时机，减少动态栅格化；不再围绕已慢的每帧全/局部draw做参数微调，也不为未见收益的GPU配置贸然改变正式运行方式。仍需正常动画/弹体、RGB2且alpha0、真实窗口与实玩验证。

## 2026-10-27 局部重绘仅改善15%，逐对象重画严重倒退并完成归因

- region-refresh固定512平方区完整960区间：移动30.738→26.067ms，两对约−4.6/−4.7，CPU局部重绘11.888ms/次，上传0.423ms。区域包含密集战斗内容，但模拟/动画仍冻结，不能称真实战斗收益；13整图画质仍不合格，不部署。
- region-items按原顺序拆为逐对象draw，180秒超时，原失败保留：351区间，GPU静止111区间均770ms，没有GPU移动或反序配对。每次查询2368、跳过1671、仍draw697，单次区域绘制756ms。区域像素maxRGB29/alpha32也失败；停止当前结构，不延长测试。
- item-profile取消帧率循环，首个区域707次draw共974ms。578个根几何界在区域外；474个DropShadowFilter物件占689ms，105个带scrollRect Bitmap占157ms。仅解释失败候选的保守剔除/大量调用，未证明正式舞台瓶颈，也未证明滤镜实际输出都在区外。下一步验证可靠效果边界与批量原生绘制/位图复用，避免重复700次draw。
- 三份独立verify_run核对526正式/13运行库/86冻结源及全部输入；原生自然/恢复精确，CPU图/纹理/260像素图分别释放，清理通过。AIR31808/52276/23204退出，登记空；A796/7F1F正式版本和foreign SceneRenderChecks保持。证据在camera-stage3d-{region-refresh,region-items,item-profile}-20261027各RESULTS与review JSON。
- 根目标仍活动未完成；仍需正常动画/弹体/图块生命周期、RGB2/alpha0画质、实际窗口和有/无敌人镜头实玩验证。没有新产品部署。

## 2026-10-27 完整世界固定画面显卡呈现出现上限收益，整视口动态重画倒退

- 七轮隔离测试，前五失败全部保留：时间轴在isPlaying=false时仍变帧、空显示槽、首视角RGB112、bloat_bulk_896末帧脚本重播。采用8间隔实际观测＋固定一次已知帧脚本消化后，完整固定图960/9通过归因协议；43播放者固定、7纹理22.6MB，移动29.658→12.092ms，两对−16.892/−18.242ms，约59.2%。真实动画未运行，13视角RGB92–253仍全部不合格，106/130ms长帧仍在，不是可部署修复。
- 追加完整视口逐帧重绘/上传成本对照，同样960/9，移动30.988→41.333ms，两对都更慢；计时CPU重绘24.5ms、上传2.942ms。停止每帧整视口重绘，下一步检验局部变化更新的代价和正确性，不原样重跑挑结果。
- 原生自然基线与恢复均精确；两完成轮各260像素图全部释放，纹理/Context/CPU图释放通过。隐式活动者通过play恢复，isPlaying可能变化，只作终结式隔离诊断；成功轮frameScriptDrain分支0，不夸称验证了重停分支。
- wholeworld-settle/verify_runs.py独立核前6轮，viewport-refresh/verify_run.py独立核追加轮：526正式、13运行库、86源及脚本/编译器输入保持；所有自有AIR退出，无部署、foreign SceneRenderChecks不触碰。详见这些目录RESULTS与review JSON。旧MEMORY原样保存为MEMORY-history-20261027-wholeworld.md后缩写入口。
- 根目标未完成。优先动态局部更新，以及发光混合/伤害数字像素差异、实际Windows呈现；最后回到无敌人/实战镜头对照。A796/7F1F正式版本保持。

## 2026-10-27 镜头滚动、宿主坐标抑制与远处图块摘除均未提速

- 七次运行，全部隔离。固定完整偏移预备后缓存world首视角RGB92失败；无缓存代价轮121区间下一入口坐标守卫停止。帧相位轮480完整，但EXIT_FRAME为1281而非480使原摘要失败；只读review核保留的480最新状态，原失败保持，不把事件数称物理帧数。原生33.108→滚动33.396ms无收益，画面RGB3未合格。
- 精确A796→06FC隔离宿主仅包住Camera.calc两处world x/y setter，其余5770方法、1016类、常量池和原素材保持；两轮240次calc后位置0/下一入口无重定位。无缓存33.288→33.550、缓存34.304→39.300ms，四对都慢，停止整world滚动/缓存，未部署。源码/复核见camera-world-scroll-native及native-cached目录。
- 远处地形摘除首轮204 Bitmap、第一视角像素精确，但暂停后台仍新增surface，0计时、清理审计失败原样保留。接续仅接纳已验证四层所有权和原父层尾部追加，固定集合200 Bitmap、4新surface/16节点，480/9完整、75图精确/释放；32.075→33.038ms两对都慢，停止。不再为无收益路径补生产Drop支持。
- 三份独立复核检查526正式、13运行库、各86冻结源/脚本与06FC实际宿主输入，原失败不改写；自有AIR均退出，无新产品部署，foreign SceneRenderChecks.as不触碰。详见上述目录RESULTS、phases/verify_batch.py、native/verify_runs.py、far-terrain-append/verify_runs.py。
- 根目标仍未完成。新方向只待准备：完整world呈现转GPU的代价上限，区分前轮局部地形GPU保留原生对象/前景的混合路径；尚未实现。静态/暂停原型收益不能当实际游玩或战斗结果，需真实窗口证据与后续动画/状态生命周期。原生camera旧cache源码仍不可作补丁基线。

## 2026-10-27 世界窗口滚动：像素门槛与自然基线各中止一轮

- a140d73之后检查旧对象父层裁剪失败范围，再尝试整个world的窗口滚动。a54fdd7f不缓存模式5174像素变化，RGB3/alpha0、恢复精确，唯一3差位于(1021,605)。实际图片无明显缺块/位移，但不放宽2/255门槛；0计时、11截图释放、清理通过。
- 原计划缓存模式单独派生c5a95e8c，候选启用前，原生120px双轴往返即103像素/RGB76不稳定；前两次1px返回精确。0候选检查/0计时、9截图释放、清理通过，不能声称缓存成功/失败。
- 526正式/13运行库/86冻结源/脚本独立复核保持，两个原失败保留，证据与verify_batch位于camera-world-scroll-20261027。AIR45916、45720退出，无部署。缓存尝试还未具备有效原生基线，先补证不能原样重复挑通过。
- 参考官方DisplayObject.scrollRect处理时机和缓存说明（本轮README含直接链接）；运行时缓存采用情况未知。旧Camera.as缓存仅作机制参考，不能拿它覆盖A796当前方法。根目标仍未完成。

## 2026-10-27 区分透明与不可见，停止远处单帧根裁剪

- 六次独立游戏运行；3完成/3提前失败。526正式/13运行库/86冻结源及脚本复核通过，75/9/20/9/55/75截图全部释放；失败原样保留，所有自有AIR退出、登记0。正式A796/CS7F1F未改，未部署新候选。
- c16c3bab世界地图原生32.579、alpha0为21.858、visible=false为13.788ms（960帧）。这只证明条件差异，不等于保留画面的性能，也不能把差额叫纯GPU/渲染。
- 远处根先后在首次预备和visualBloat0多帧模型边界变化处停止；排除所有多帧后又遇遮罩盘点#1009。加空节点保护/单次mask读取和路径诊断后d3162bd8完成480帧，实际只选274根；33.646→35.063ms，正反都慢，停止。成功轮未遇空节点，未证明前轮空引用根因。
- a5e0f915六物件层原生33.892、alpha0为29.733、visible=false为26.813ms（960帧）；精确恢复、75截图释放，保留287ms长帧。物件层只解释部分，下一步看剩余显示层组合/世界容器，不复活无收益的GPU/条带/静态根路线。
- 源码/报告入口build/generated/camera-world-alpha-visible-20261027及本批camera-far-*、camera-object-alpha-visible目录。root目标尚未完成；foreign SceneRenderChecks.as未触碰。Pt参考读取保护拒绝后未转路重试，仅继续本模组自身证据检查。

## 2026-10-27 修正首次绘制诊断基线，分离角色/明暗/地图开销

- 新增9次隔离游戏运行与1次16例合成运行，详见build/generated/camera-object-groups-20261027/RESULTS.md及batch-review.json。526正式/13运行库/冻结源码/脚本复核保持，所有自有AIR退出、登记0，无产品修改或部署。
- 角色/上层单独alpha恢复仍失败；二维合成未复现。原生镜头往返v1/v2先被盘点错误中止，v3确认首次自然往返也改1219像素，后续返回图一致。先前3D猜测未证实；部分节点记录失败保留，不将部分相同称全状态相同。
- 基于新证据，每视口固定一次自然预备，再强制三种自然往返与alpha恢复精确；8a9491bd完成960/9，角色约减少3.6ms，上层无独立收益，两者约4.8ms；75截图释放，旧失败不改判。
- 全地形GPU因水层原生透明度被守卫拒绝；保留水的d7432500完成960帧，但31.50→35.058ms更慢。摘要器与硬编码父层计数不符，原失败保留；只读review核其他断言且明确无实测父层计数。143截图/121纹理/Context释放，停止该路线。
- 8200f709原生明暗/地图归因960/9通过，32.363→明暗透明30.125、地图透明22.388ms，75截图释放。明暗只解释一部分；根目标仍未达到，不能用隐藏画面当提速。
- 接续：区分alpha0仍保留的显示树处理、真正可见像素绘制与时间轴/回调。若作visible对照，仍须同样精确恢复和新预备条件；先核旧远处包装/睡眠时间轴范围与检测成本，不重复无收益路线。foreign SceneRenderChecks.as不提交。

## 2026-10-27 镜头移动后续四轮：节点取证、透明裁剪与底层归因

- 6849b5e0只读节点取证：未改状态连续截图精确；alpha恢复失败4028像素/maxRGB218。928节点首次draw后的公开状态与最终恢复相同，内部渲染状态未知。981b46e1先呈现3帧仍1898像素/maxRGB255失败，两轮0计时/各6截图释放；不比较不同暂停状态的像素数量来宣称改善。
- 4d75556b透明边缘裁剪保留全部源数据、0地形分配/复制，13视口RGB≤2/alpha0/原生精确恢复、960/9通过；移动33.129→36.629ms倒退10.56%，停止不部署。39截图释放，原生预绘/重绘计数保持。
- 3c1b07c4仅分离底部物件0/1层，沿相同alpha方式与精确门槛，五视口15次恢复、960/9通过、35截图释放。原生31.592、两底层透明31.125ms，未显示主要收益；169ms长帧保留。不能把不完整画面当优化，也未关闭角色/上层的恢复失败。
- 四轮526正式、13运行库、冻结源/探针/脚本逐项复核通过，batch-review.json位于build/generated/camera-lower-objects-20261027；无自有AIR存活、共享占用0，正式A796/CS7F1F未变。源码与报告归档，foreign SceneRenderChecks.as排除。
- 根目标仍未完成。停止重复低收益底层/透明边缘/背景路线，接续优先分离角色2层和上层3–5层的绘制与缓存行为；旧trace仍有记录开销和菜单入口限制。详见四个新增目录RESULTS.md。

## 2026-10-27 对象层恢复异常实际留图，未形成性能候选

- 4ee1990a按原版mainMenuOff进入后仍复现对象层alpha恢复差异：2180像素/maxRGB88/alpha0，0计时帧；5临时截图释放，数值状态恢复，AIR35080退出。实际PNG与只读连通区域分析保留，差异主要在角色/碎片附近，具体显示节点未明。
- 明暗裁剪、背景硬件绘制均不提速，正式安装未变；没有新的合格部署包。当前自有AIR全部退出，后续需要新的高占比证据，不重复同路线取最优结果。


## 2026-10-27 硬件背景未提速，补齐原生主菜单关闭流程

- 独立能力DirectX9Ex通过；游戏背景原型实际DirectX11，首视角失败。分层留图确认旧夹具只设mm.active=false，残留菜单遮住GPU背景；改为原版mainMenuOff后13视角RGB≤2/alpha0/精确恢复全部通过。
- 修正入口的7de6eed8完整960/9：移动原生33.1875→GPU33.5208ms，无收益，不部署；81纹理、39截图、Context释放，526正式/13运行输入保持。AIR31020退出。历史绝对性能加入口限制，不扣臆测固定耗时，不覆写旧证据。
- menu-worldstep-gating与programmatic-gameplay-driving已补共享知识：逻辑放行不等于显示清理。对象层旧恢复失败报告称PNG保持，但实查无保存代码/图像；新4ee1990a只补图像取证并修正入口，exec73358运行中，原恢复门槛不改。


## 2026-10-27 镜头同区域基线补齐，远景与条带候选停止

- 远景屏幕缓存960/9像素/透明度通过但移动仅约1%，停止。条带原r1像素max6失败；留图轮960/9、13视角通过但无收益；取消无变化写入后仍移动慢16%，停止，不部署。
- 原版旧2032×1084基线的镜头四段恒(56,42)。小窗口仍默认适配整间，v1资格失败保留；v2明确原生zoom0，普通/连续各960帧，同源同几何同局部轨迹复核通过。组合13.8125/24.6167ms，静止已差8.25ms；世界单位9/153及时间轴差异保留，不称纯渲染因果或实际游玩FPS。
- 新事件分段960/9脚本约1.5ms且稳定，增量主要在事件间隙；间隙不是GPU证明。lightBmp裁剪v1internal访问失败0修改；v2冻结35cb78c9完整960/9、13视角精确但移动慢3.67%，停止不部署。AIR51820退出，源/结果各自新目录，历史不改写。
- 独立Stage3D能力ae7d3b88已通过：DirectX9Ex/baseline，65536像素RGB1alpha0，Context与位图释放/正常退出/526正式+13运行输入保持。新背景硬件原型e3bf12ec已构建，r1 exec58073运行中；只限远景与两背景层，读回合成不代替窗口输出验收。正式A796/7F1F等及foreign WIP保持。

## 2026-10-26 静止同步/透明省略/背景合并已测，实战收益不足部署

- idle-v1看不到弹痕的夹具失败保留；v2改实际屏幕内外墙并通过960/9、原生击墙/毁墙、动静切换及资源释放。empty/merged依次只增加空页省略和受守卫的背景合并，各960/9通过。
- merged暂停移动31.6875→26.8417ms约15%，但真实480/27两轮47.0125→44.1958和46.2125→44.9833ms，第二轮配对反向且P95更差，仍156/196ms长帧。保持候选，不部署，不重复取最佳。
- display对象alpha恢复不精确，0计时，停止。仅远景抑制960/9精确恢复，但四对都更慢；下一候选是屏幕尺寸的不透明远景副本，先严格像素与资格检查。当前r1 exec38643运行中。
- 本轮已完成八个AIR均退出、526正式/13运行输入守恒；各RESULTS已记录。MEMORY全文精确归档至MEMORY-history-20261026-2340.md后重写，取消旧“正在运行”前缀堆叠；foreign WIP保持。

## 2026-10-26 固定池画面/跨页通过，仍有静止额外开销与外部长帧

- pool实战两轮480/26：均53.1417→47.7083、49.225→47.4542ms；准备344/275ms，计时物理分配0、像素容量200MiB。配对和火力不同，收益不稳定，最大160/221ms仍有；AIR65176/44888清理，不部署。
- pool-paused-v1旧战斗init排斥presentationCheck，留菜单0样本，600秒自动清理自有AIR54020，stderr确认。失败不改写。v2仅收窄该战斗门控，b00e63b9完整960/9，五视口RGB1/alpha0/恢复0、几何回退/跨页淘汰复用/释放通过；移动30.5667→27.425ms，两对同向，静止反多约1.84ms；跨页有220ms长帧，其中准备185ms。AIR33024退出。
- stage-cost b46de033保持池35956ECD，只拆四段墙钟；960/9全部验证通过，移动28.475→24.9458ms。镜头段均.35/最大2ms，呈现器均1.258/最大7ms；本轮148/140ms长帧的准备仅3/0ms，未复现185ms。不能把残差归GPU/GC。AIR67816退出，所有正式526/运行13及冻结输入保持，无新产品部署。后续先去掉静止无用缓存扫描，并验证重新移动时同步动态变化及真实兼容。

## 2026-10-26 分帧缓存仍有长帧，准备固定池复用

- budget-r1冻结a8bacc46/helperB6A2ED06完整480/26，通过每update至多一张图、所有原生冲刺/实弹/边界、清理与输入守恒。第一B23准备/24分配帧，94/119候选呈现；两对49.3833→50.0583与53.4167→41.7833不同向。最大291ms仍在分配期，探针自身55/43/58ms；不能称分帧已解决停顿，停止不部署。AIR14924退出，RESULTS.md保留。
- pool候选35956ECD在计时前预留固定200MiB、运行复用，不在update分配。A诊断仅恢复原生并保留不可见池，普通关闭释放；因此需要额外原生/加载/视觉与生命周期验收，不能仅凭ABBA部署。源与运行器预检完成，exec50815登记等待后构建实测。

## 2026-10-26 镜头地形/远景对照结束，短窗真实合图两轮正向

- terrain-layers-r1完整960帧：原生35.2875、后层隐藏34.3917、前层隐藏36.5375、四层隐藏29.5583ms；15恢复精确，八绘制计数不变，只归因。AIR65040退出。
- backdrop-cache-r1实际960帧/9检查通过；旧汇总误用两处parents==4，独立校正仅改为1和cache=true，原失败保留。原生移动35.6208→缓存38.5875ms，两对均更慢，停止；像素最大RGB1、alpha0、恢复0，AIR66932退出。见RESULTS.md与summary-corrected.json。
- short-combat-r1/r2复用同一10c85dfb冻结85源，四段120帧，原生行为、六SMG10、地图/碰撞未改。480帧/26检查/真实冲刺与双方实弹均通过。均值55.9208→51.5458和57.4375→51.7542ms，四对同向，首建150MiB仍有281/212ms尖峰。正式526/运行13不变，AIR52400/38440退出；近原版未达，不部署。准备只改缓存建立调度，减少分配峰值。

## 2026-10-26 共享登记已恢复，镜头地形层实测重新启动

- 用户明确授权ModLoader登记器修复。系统复用进程已自行退出，原recover恢复11d714；新增保守CIM创建时间回退，原生token精度保持，15项回归通过。首轮临时目录清理错误保留，ModLoader提交08957b4，未动supported-mods.txt他人工作。
- 原不可变seed检测到工具8B35→E9F5更新而拒绝继续；新lineage.py只允许此精确工具更新，其余全部输入、旧收据、85源/探针/编译日志保持。新fdd190c0冻结构建完成，camera-terrain-layers-20261026-r1在共享占用后进入AIR65040；前后层可逆抑制仅归因，不是产品减画质方案。

## 2026-10-25 地形层对照被旧PID复用登记拦住，候选保留待授权

- terrain-layers-r1仅编译成功，CreateDesktop拒绝访问、无AIR；r2提权复用包，但自己的r1登记11d714仍needs-check，等满300秒后暂缓73f23c。原编译PID63256被MoUsoCoreWorker于23:38:25复用；原token与CIM创建时间明确不同，OpenProcess两种权限均拒绝，现工具recover两次保留。未结束系统进程，未改共享SQLite或跳过占用。
- 只在CS目录准备ModLoader进程身份回退候选：CIM仅补拒绝查询、失败仍unknown，按微秒比较避免时间精度差误放行。原共享源8B35A6D6，候选C18D8084；实际只读复用身份核验通过，Registry/Registration/main AST不变。已请求必要跨模组修复授权，答复前不接入。详见camera-terrain-layers/REGISTRY-ISSUE.md；若系统进程自行退出可原工具恢复。
- 已通知RConnect (2)共享占用缺口，正式包、玩家进程、其他会话WIP保持。近原版目标仍active，尚未进行前后地形层960帧测试。

## 2026-10-25 镜头原生记录完成，继续前后地形层归因

- camera-axis-trace-r1使用原字节A796宿主，经961条trace标记对齐960帧/3361341记录；时钟差-1.087ms、完整流两遍解析、像素/计数/清理/输入通过。移动时绘制区间增长明显；记录开销和跨度嵌套不可忽略，不称GPU原因或正常游玩FPS。AIR46520退出，临时配置删除，已通知RC释放。详见其RESULTS.md。
- 前轮axis-telemetry-r2仅769帧/0自定义标记并触及时限，失败保留。测试宿主tag93写入及精确授权登记均被hook拒绝，未执行，不转工具重试。后继trace只变自有测试helper，宿主不变。vendor版权说明纠正为三份Apache与一份BSD，原头完整保留。
- camera-terrain-layers准备同路线前/后/全部地形抑制，全部恢复精确才测，保持实体与模拟对象；不是隐藏画面的产品方案。r1编译成功但后台桌面创建拒绝，未启动AIR；r2按既有授权提权复用同构建等待共享时段。无新产品部署，近原版目标仍未达。

## 2026-10-25 四节点绘制无明显收益，接入原生镜头耗时记录

- camera-bitmap-fill-r1完整960帧，原生移动32.446→四节点32.296ms，方向不稳定；静止变慢。RGB1/alpha0/精确恢复、八原生计数不变、输入与资源清理全通过，AIR51228退出。不部署，报告保留helper维护开销，不能扣掉它宣布提速。
- 独立原生telemetry v1校准失败保留；v2验证120帧标记、20工作span、1432绘制span，AIR39184正常退出，临时配置删除。仅通过本机能力，不是游戏/性能验收。原生跨度按并集归类，避免父子重复相加。
- camera-axis-telemetry新夹具保留原960帧/像素/八计数/输入门禁，只加帧锚点；r1在0构建/AIR前发现RC变为2C49，已核负责人安装回执，r2用新指纹独立运行。旧78C证据不重标。已按用户授权与RConnect (2)协调约3分钟测试时段，等待其当前组结束。

## 2026-10-25 地形原生滚动缓存实测倒退，正式安装保持

- r1等满共享登记300秒，未构建/启动。按已有RConnect协调授权给两对话发送测试时段请求；r2实际完整960帧32967ms、五view RGB1/alpha0/恢复0、15图释放，原生八值逐帧不变。正式526及13运行库、冻结源保持。登记036044、自有AIR50680退出后已通知释放时段。
- 原生移动36.750ms，缓存43.438ms，两个移动对都慢，合并约18.2%倒退；静止28.013→29.163ms。请求6次均恢复、终态0父层，内部缓存分配未知。停止该候选，不部署、不推进战斗复验；完整结果在camera-scroll-cache-20261025/RESULTS.md。
- 主目标仍active，镜头分轴复现证据有效，但近原版未达。后续以镜头显示表示为主线；批量纹理填充仅未实现假设，不能复活已失败显隐/缓存或用减少敌人演算当镜头优化。

## 2026-10-25 恢复实测，以镜头移动为核心

- 用户重新允许测试，明确不论敌人出现与否均以移动镜头为核心。activity-camera-range候选保留、暂不优先。正式文件和其他任务WIP保持。
- mouse-world-v4-r2已完成1200帧/30检查，真实单次鼠标消息、直接Stage固定、原生冲刺和双方实弹资格通过。A59.613/B57.807ms约3%，敌人射击482/337、预绘等不同，无主要瓶颈/部署结论；AIR46000已退出。原失败不覆盖，完整报告RESULTS-R2.md。
- 新camera-world-motion只做固定暂停世界的静止/移动×可见/隐藏正反序，保持实际私有窗口可见；沿路八绘制计数稳定才计时，逐帧核零增量与精确恢复。编译/运行状态见新evidence，不称真实无敌人玩法或GPU归因。

## 2026-10-25 镜头分轴复现通过，停用有副作用的世界显隐控制

- 显隐v1/v2均计时前停止、0性能帧；v2连续三原生图全等，恢复两图稳定但武器区域2612像素不同/maxRGB206/alpha0，六PNG保留，未猜根因或放宽恢复标准。源检索+截图局部对照命令及其grant被reference保护器拒绝，未再换路执行；完整图与只读差异足够停止该控制。
- 原生分轴r1（110D9DB4）完整960帧36532ms、八计数逐帧零变化。静止/横/纵/组合29.821/41.304/37.125/43.967ms，正反序移动均更慢；helper含原Camera仅约0.2–0.4ms。原30fps、试验120，暂停归因不称真实FPS或GPU原因。正式526/运行库13保持，AIR51420退出，清理通过；结果见camera-axis-motion/RESULTS.md。
- 新camera-scroll-cache只在四原生地形父层请求视口范围cacheAsBitmap+scrollRect，平移补偿保留屏幕位置；世界根和对象层不隐藏，原nativeBuffers不变。RGB≤2/alpha0/恢复0、960帧及实际战斗门槛保持。已准备并登记实测，尚无收益/部署结论。

## 2026-10-25 用户保留正式游戏，转为准备镜头活动范围候选

- mouse-world-v4五源完成根与独立复审；r1预检发现另一个AIR后停止，未编译、未启动本轮实例、未发消息，0性能样本。用户随后明确保留正式游戏、先准备候选；未操作或关闭其窗口。原失败登记f4df5795及RESULTS.md保留。
- 新activity-camera-range只针对未参战远处单位的near范围，精确7F1F来源与原战斗/弹体/宽限段保持；当前画面与预计下一镜头包围合并，普通小震动纳入界限，未知情况回原near。后验一旦越界即失败并退回原范围，不把预测当成已证全部行为。
- 本轮后续只做源码、离线数学和准备脚本检查。没有新部署、没有实战改善结论，用户接受2/255但仍要求真实战斗明显提速的门槛保持。
- 收尾：activity-camera-range源6→7/2改、5组原段和精确反转通过，helper898D；独立数学适配313800结果0违例且late-write反例保留。根探针最终9d862774为29AF85→86，仅Main/helper，加入checkComplete/tick/模式逐帧守卫。未编译、无AIR，运行器接入及真实性能资格留后续；报告RESULTS.md明确全部边界。

## 2026-10-25 地形摘树无明显收益，鼠标资格继续核验

- terrain-v2-r1实测1200/26和完整新增/恢复通过，但A56.185/B56.055ms无稳定提速，停止不部署。计时内716摘还、终态332摘还，实际16次追加/0Drop，终态世界三图逐像素相同；不得补称SATS、完整路线像素或Drop已验。helper平均约4ms全在计时内，不事后扣除。result BEB61182、报告v2/RESULTS.md，AIR16324退出，全部正式守恒。
- mouse-world前三版均失败且0性能样本；v2早于AS超时终止丢失result的问题在v3修正，原executionError仍在旧记录。v3证实单次消息命中真实world，直接Stage坐标等于中心，而事件派生stageY偏3；守卫拒绝并恢复窗口，未做ABBA。官方MouseEvent页不足以解释偏差原因。后续v4保留直接坐标±1和单次事件身份闭环，另记录localXY/矩阵/变换与各差值，派生event坐标不拿来充当固定光标位置。这里只改变诊断证明目标，不修改游戏行为或回填失败。

## 2026-10-25 自有鼠标能力通过，地形静态驻留诊断失败保留

- 鼠标v4 cbbb25c5完成3条各一次native消息、正确target0/1/2与真实Stage/后Timer读回，exit0、原句柄关闭；22运行输入及构建前后记录保持。前三轮v1/v2/v3未通过各保留，不把正确第一条事件补成全通过。v4无全局光标/焦点/桌面操作。报告及复审SWF重读被护栏阻止的限制均见v4/RESULTS.md；构建和实际runner已做二进制前后守恒，独立报告未绕过阻止。该结果仅输入能力，不含任何FPS收益。
- native-terrain-detach-r1已编译并实跑：初始109surface/436Bitmap，第一A第74次update出现正常新增图块，严格static-resident拒绝。0完整段、0detaches/held/pending、未跑终态像素；284ms仅helper诊断开销。原始result A5B691B4、summary544EEF6F，正式526/运行库13保持，AIR49264退出。报告native-terrain-detach-20261025/RESULTS.md。下一版必须处理原生append/Drop，不能停预绘或修剪失败帧。
- 当前两条后续均仅准备：准确29AF真实鼠标位置下的mousetree ABBA；支持原生增删的terrain v2。没有新部署或已解决声明；目标继续，外部WIP和既有正式版本保留。

## 2026-10-25 固定Box清点为零，停止摘树并更正容器概括

- 准确29AF夹具上只新增Main视口记录和终态helper，21751A27探针完整1200/26；603Box经wall/门/交互/lurk筛选归零，0未知字段。1204逆变换视口与+320并集独立重算全等；41ms清点在最后帧之后，25ms视口观察留在计时内。均50.6933ms无候选收益；result9ADD22B3，报告build/generated/static-box-census-20261025/RESULTS.md。
- 603Box全部同时在数组及1066节点链，反证shared object-containers旧过强概括；已按知识归档技能在原文补新证据与更正，保留旧Sandevistan实验事实。最早链独占指示/中途只看objs.push推断均由最终双容器实测纠正，没有执行移树。8个末级排除全lurk非零，仅保存3个niche1例子，不称8个ID全同；treeNodes0不能解释为全图单帧。
- 44脚本/10夹具/13runtime/526正式/86冻结源独立复核保持，AIR18080退出、登记释放并已通知RC/RV；无新部署。停止该白名单，不扩到门/交互/藏身/移动箱。主目标继续；只准备自有私有AIR鼠标命中能力检查，旧mousetree的Stage(0,0)尚未覆盖真实世界位置，未把新假设当原因。

## 2026-10-25 活跃线程IP实测完成，继续静态物件清点

- 真实SMG夹具完成1200/26，平均52.8617ms，仅诊断无成对收益；134IP/124入窗，68批3264CPU行，排名/轮转/区间与134次恢复均经独立重算。最忙线程62IP仍有39未命名AIR、8未知，未定位具体渲染函数，不把等待频数当CPU时间。
- 43脚本/7夹具/13运行库/526正式/85冻结源保持；AIR10512已退出并通知RC/RV释放时段。报告build/generated/owned-native-stack-20261025/IP-RESULTS.md，result8E5341EE；原栈r2展开不完整的降级结论不变，无部署。
- 参考Box死亡链与Location登记缺口已按既有精确调用授权补读关闭；普通Box.dead并不自动移除图像。STATIC-DETACH-PLAN追加更正。下一步只读清点严格白名单固定Box，尚不移树；其他会话源与天角兽候选不动，主性能目标继续。

## 2026-10-25 自有AIR原生IP诊断完成，调用链与收益未验

最新2026-10-25：owned-native-stack-air-r2完成1200/26和120份真实IP（108在战斗窗），均45.4675ms没有成对基线，不是提速。48线程轮转使忙8条各仅2–3份；缓存78模块缺表，调用链降级，只采用真实RIP+CPU。进程约2.314核。AIR36936已退出，526正式/42脚本/7夹具/13runtime/85源保持，无新部署。详见build/generated/owned-native-stack-20261025/RESULTS.md；正在准备air-ip-only聚焦忙线程，尚未运行。STATIC-DETACH-PLAN仅方案，补充源码读取被钩子拒绝未绕过。目标仍active。

r1在附加GetThreadDesktop WinError5后0采样停止；v2放弃该属性观测，不改权限/换通道，所有原句柄/PID/FILETIME身份与一次恢复保留。独立审查重算1200连续54561ms/26项及60CPU区间、检查输入闭包/退出清理通过。105/108瞬时系统等待位置不能当等待占比。文档写入一度被SWF路径启发式误拦，按既有授权登记精确调用后接续，未关闭护栏。

## 2026-10-25 画质敏感性与活动状态候选，仍未取得镜头优化验收

- 画质r2实际HLLH共1200/26，67秒连续守恒，六Class无关。HIGH/LOW均57.8383/53.4133ms，两对同向但火力/预绘/弹体负载变化；LOW历史栅格可留到HIGH且线程观察共3185ms，不能降画质部署或报7.65%净收益。r1在AIR前描述符格式锚点失败保留；实际r2namespace30接受allowLowQuality且恢复/清理通过。详见stage-quality-native-20261025/RESULTS.md，resultA13F894E。
- 首次确认CS engaged永久锁与TDFC lastSeen>=0历史记忆唤醒，准备精确7F1F/7ACD隔离候选，未改live其他任务。独立审查拦下再报警冻结、额外威胁遍历及rapid<=0误判，当前source-v3/access-v2/tdfc-candidate-v2已修；同包原生字段外部存根绑定经实际字节码核对，局部activation槽单列，未嵌入原生类。
- 实测activity-release-native-r1的1200/26通过，原生6Class身份严格相等、30个闲置阳性。末态released0，12个engaged只有近处6Raider及6未知家族，没有实际解除锁收益证据。均52.0567/中50/P95 69仅单候选，不能当优化；生命周期验证不完整。result670214F8、AIR31196已退出/登记释放，安装526保持，无部署。入口activity-release-20261025/STATUS.md，原生产BA20、只读观察B0E1分别留证。
- 继续原镜头目标，不把活动兼容当更小的替代目标。停止重复同一固定战斗找阳性；下一条是owned-native-stack-20261025的自有Python原生线程位置能力准备，禁止既有/用户进程、符号联网、注入或把等待样本当CPU百分比。尚无AIR调用栈证据。MEMORY已接续。

## 2026-10-25 原生战斗逐线程CPU诊断完成，继续定位镜头成本

准确29AF只在Main加首末/四case时钟锚，85源、三处可逆追加，CFD85A18；新thread_cpu只查询拥有的AIR线程和私有桌面窗口映射，未暂停线程/改优先级。API冒烟的空桌面FALSE0不回填；实际AIR有窗口映射阳性。Toolhelp实测约150ms，故每3次原processCPU采样才查询线程；完整采样耗时保留，非生产遥测。r1的1200间隔/26项、74638ms和逐线程累计获独立复核，玩家/敌400/329实射，后段火力下降，不能当提速。

时钟漂移1ms，67个进程区间74.36s/153.828CPU秒，21个线程区间69.969s/144.141CPU秒；window创建TID58336约.729核，七个无窗口线程共1.300核，仅证多线程计算。22查询3728ms（枚举3667ms）不可忽略，不从整帧扣除；计时外2个invalid及区间内3个退出身份保留，覆盖有缺口，不称全CPU或GPU归因。result6C4D7368/process-policy01738547；详细表与指纹在build/generated/thread-cpu-native-20261025/RESULTS.md。正式526/隔离528/runtime13保持，最低commit6.47GB，AIR118596已退出并通知RC/RV释放，不追加本批。无部署。

本轮还准备native-cpu-profile离线ETL消费器，真实TraceEvent3.1.13程序集/API冒烟通过，actualEtlRead=false；不录制/下载/安装。普通及sandbox外均非管理员，未启动WPR。下一步质量HIGH/LOW诊断正在新目录准备，需allowLowQuality独立描述符，仅测试质量敏感性，像素变化不能部署；并行只读发现NativeSceneActivity.engaged无退出分支，待核原版战斗记忆/追击安全释放条件，尚未修改生产。目标仍active。

## 2026-10-25 私有桌面显隐实测完整，未解释主要卡顿

window-visibility-native-20261025从准确29AF仅Main+新helper共86源派生EAD18FDE；7处唯一锚点可逆，nativeWindow.visible是唯一运行改写，切换在caseBegin/连续钟开始之后，末态closeProbeTiming后恢复。helper6BC5/patch2871/runnerB39B与13runtime闭包独立审查，r1注册f983ab89等待RV/RC当前轮完成后运行，自有AIR112256已退出并通知双方释放，不追加批次。1200帧/26项、连续54927→129036=74109ms，result7026DB47；无缺块/强制补绘/内存中止/其他AIR。

隐藏600帧均61.553/中59/P9580、可见600帧61.962/59/82，正反两对差+.693/+.123ms，敌395/456、夹具弹密度可见稍高，预绘6/6块47/43片。均值差很小且自然战斗混杂，停止显隐路线，不将其当主要成本或部署方案。首显示36ms、其余切换2/0/1ms与所有长帧保留；窗口读取总34ms也未扣除。全1200实际visible准确，其余active/applicationActiveWindowMatches/onPause均false，Stage2032×1084/HIGH/30、normal/direct和bounds全程稳定，末恢复false/pending0/errors空。每窗600 RENDER事件不代表用户桌面呈现；私有桌面可见仍不等于真实用户桌面，不能外推全部历史测试或GPU后端。526正式/528隔离/13runtime输入保持，无部署，原README/代码冻结，详见RESULTS.md。

下一条只读可行性调查已结束：有wpr/tracerpt/typeperf/logman/dotnet，wpr -status为未录制；已查PATH、常见Windows Performance Toolkit目录与安装登记未见WPA/WPAExporter/xperf/PerfView。存在NuGet TraceEvent3.1.13库/依赖，没有现成分析程序；CS与相关共享记录未见旧ETW/WPR实测。尚未启动录制、安装/下载工具或写新解析器，先不盲采。若补齐工具，OS采样可补线程/模块CPU及调度等待信息，但缺AIR符号未必还原具体渲染函数；不能把[render]标签或剩余墙钟直接称GPU/GC成本。目标仍active。

## 2026-10-25 叶部件资格未满足，补得实际窗口隐藏证据

player-leaf-cache-20261025 只从准确29AF/85源派生Main+helper共86源，9F8419E6探针；helper C6BE/patch F3B5/runner3B1D均独立复核，初次纯静态锚点不唯一与not-qualified缺final census摘要问题在首次运行前修正，不改原失败口径。注册r1/AIR111968实际暖场后护甲均pip，扫描121节点，指定sleg20_53缺失，按协议即停：0观察/0像素/0缓存写入/0临时位图，8个准备检查不当完整验收。原始result AE71EE22、inventory C6838631，summary保留inconclusive/rawOK=false，不能声称缓存有效或提速。该对象路线结束，不换符号、不调阈值、不追加重跑。

初末窗口getter无错误：visible=false、active=false、applicationActiveWindowMatches=false、normal/direct，窗口2048×1123，Stage2032×1084/HIGH/30。它明确本轮为隐藏状态；不是叶失败原因，也不是无内部渲染/全部旧相对比较失效的证据。正式526与隔离528输入保持，自有进程已退出、登记结束；已向RV协调释放与新发现。新window-visibility-native仅准备，打算同一private desktop内false/true/true/false，原生输入/AI/物理和连续时钟保留，终态恢复visible。不调用activate/focus/SwitchDesktop；需要记录其他窗口状态的混杂，仅作环境敏感性诊断，不当正式游玩优化。无本轮部署。

## 2026-10-25 direct/cpu 全原生战斗完成，停止模式改动

native-render-mode-20261025/run.py 01C4E836仅在本地run_owned函数副本的描述写入和清理核对处加两锚点，原代码逐字可反向；复用准确29AF/85源/9837原回执，从真实probePath.parent验证相邻compile.log。rcnative不访问RC API，不隐藏画面或合图，无新增逐帧观察。原保护、登记、私有桌面、唯一存储和清理保留。最终实际描述只有ID/mode不同，2048×1123一致；归一SHA同C0938…71017，526正式/528隔离/13runtime/25runner输入跨轮相同。

direct-r1 A2BC381B完整81355ms、均67.796/中63/P9596/max360/>100帧50；cpu-r1 70DA9604完整83018ms、均69.182/中66/P9588/max356/>100帧23。各1200/26通过，实际玩家各400射、敌1176/523、fixture在飞弹均3.988/1.764、活动抽样均42.775/37.425；CPU普通预绘19块129片多于direct11块72片，均无缺块/强制增量。尾部计数改善照实保留，但平均/中位无改善且负载混杂，不作净收益结论，不追加第三臂、不部署。独立raw时序/描述/JSON来源复核通过，边界及全部长帧保留，不将残差称GPU时间。

两自有AIR92392/125828和登记f148b1…/cb1024…均已退出释放；CPU等RV当前轮后获资源，结束按已有协调授权通知不追加本批。正式游戏、运行时、模组、画质均未改。run与README维持测试开始的冻结指纹，结果单列RESULTS.md；不改旧失败front-r1。只读去重另找到单帧叶sleg20_53（sleg3_52装备容器内，旧pinok16树快照）未被整根playercache覆盖，但对象是否稳定、是否位图填充、父旋转重采样和RGB2资格均未知，未创建候选/运行，禁止把旧animate约3ms当潜在收益。目标仍active。

## 2026-10-25 原生输入纯地形分层完成，未显出主要成本

从精确29AF的85源只改Main挂点并加复用Bitmap记录的helper，共86源，CA08A5FF；不是隐藏前景父层（那会误藏角色）。Stage最高优先级先恢复、World/RV/WB更新后仅隐藏原生地形[0]或[1,2]；A/B同扫，1200原始间隔含切换和扫描，按previousApplied另归组，不删长帧。源码与runner独立复核后，back-r1结果37EF47FA、79079ms、26/26；front-r2结果E38F7960、75523ms、26/26。

背景A/B均67.018/64.780、P9594/86、敌465/458；前景62.352/63.520、P9583/87、敌493/603。四窗与活动/子弹/预绘详见terrain-layer-native-20261025/README.md。背景两对差3.677/.800ms、前景−.163/−2.173ms，不支持主要瓶颈或可发布优化；也不能将前景反向差视为真实成本为负。计时缺块/强制补绘增量0，但普通预绘仍存在。全部44450/22265隐藏恢复、444/452绑定释放，非目标层保持，原生输入/击退/火力不改。

front-r1误传evidence复制probe-build.json，原验证器要求相邻compile.log，启动前失败完整保留；front-r2用原4d02b28b…构建路径复用同一CA08，不修改runner绕门禁。等待期间RC请求空档，已答复不追加批次；其44e7加载诊断先正常完成，再完成本侧front-r2。所有自有测试退出/登记释放，无部署。下一项只准备native-render-mode-20261025，官方资料说明桌面direct仍软件绘制+GPU送屏，gpu回退direct；不将改标签当自动GPU加速，不启动Stage3D重写。既有源字段失效候选仍未构建。

## 2026-10-25 两轮真实SMG战斗完成，停止分页候选生产推进

冻结29AF3457探针、各1200连续间隔/26项通过，r1结果C59DD1EA（73965ms）、r2结果3930AFFF（71522ms）。r1 A/B均64.970/58.305、P95 93/82、敌射424/301；r2均60.667/58.537、P95 81/92、>100ms10/22、敌射477/557。每段玩家100射，真实移动与击退、首建/切换/全部长帧保留。r1两对19.32%/.68%、r2两对5.97%/.96%，不能把平均差归因算法；第二轮长帧更差，未达到减少卡顿目标，不部署，不第三次重复筛结果。详细表在camera-atlas-paged-combat-20261025/README.md。

594/600与593/600实际图集呈现，无几何回退、无缺块；各6页150MiB、24位图全释放，无页淘汰。r1首B299ms含237ms维护/分配；404/381/357ms无建页，局部计时不能解释，不推断GC/GPU。两轮526正式输入/528隔离输入核对不变，原生game/CS未改；等待期间按已授权范围协调RC/RV时段，结束已通知释放，无自有运行/等待测试。

仅源码候选scene-raster-invalidation-20261025补scenePreloadRegions四层写前++surface.revision：根与子代理静态验证来源保留链、唯一锚点、逐字反向及6个错误输入拒绝。未构建/运行；75157只可供目标方法，禁止整类覆盖A796。SATS恢复接口、显示属性/WB顺序仍未实现。只读去重确认旧worldlayers/shortlayers强制定位，unitblit/playercache/implicitpause/sleep-cache无可部署收益；真正未做窄项是当前native-input持续跟随下分开前景和背景两层的呈现成本，不重新包装旧失败路线。

## 2026-10-25 固定位图池完成，转真实SMG战斗

pool-r1探针9B5A6706、结果5E25D5C1，960连续帧26996ms/八原生计数零；8遍1000次预备40730ms单列。五视口RGB≤1/alpha0/恢复0、两回退及19截图释放通过。计时只建8物理页，满池后无再分配/释放，10次重定向/40次全层清零；全阶段16页64图最终全释放、峰200MiB。移动两对37.8167→32.5583与37.975→37.15，第二对P95变差；合并37.8958→34.8542但P95 48→53，静止18.158→21.575。首B86ms/work54、移动新页199ms/work146和原生354ms/work1均保留，不推断后者GC，不跨轮归因池收益。独立复核通过诊断门禁，尚不能部署。

新camera-atlas-paged-combat-20261025只改冻结85源中Main/Atlas/Encounter三处，采用已通过r2的非池分页类；六原生SMG10仍单发knock3，rapid3/clip24/reload35，新负载不和旧LMG跨算收益。连续1200帧、原生冲刺/击退和原越界检查不变，实际矩阵/呈现/资源逐帧记录。按共享登记排队，未给性能结论。正式生产接入只读核到：帧首恢复native须早于RV读实际树，帧尾呈现须晚于WB覆盖层；SATS任意帧间截图与scenePreloadRegions原地改图无revision尚待明确处理。

## 2026-10-25 分页r2完成

六遍750次预绘/34336ms后，F73FC719真实960帧31903ms、逐帧八原生计数全零；五view RGB1/alpha0/恢复0与两回退、27页全释放通过。移动A43.4792→B35.8875ms、两对同向；静止25.52→28.04，仍有235/264/315ms长帧且对应work仅4/2/0，不能据此归因GC。暂停线索约17.46%，未部署。独立准备有界位图池及使用原生smg10的新全1200帧战斗夹具；旧LMG失败不改写、不降低物理/边界门槛。

## 2026-10-25 固定世界分页缓存r1与预绘修正

用户接受RGB2/alpha0继续验证，不放宽战斗收益/功能部署条件。新增固定1280世界页/最多8页的隔离helper与960帧跨页诊断，5192969冻结r1配方。r1五view RGB1/alpha0/恢复0、两种几何force回退全等，19截图及27页/108位图全释放、峰200MiB；实际跨11页且有淘汰和回访复用。完整960帧却计时新增16驻留/19重绘/52预绘分片，全部移动窗发生，故runner失败，不归因收益。r2仅加强全路线预绘至完整pass八计数不变（上限12），其余门槛不改，正在隔离运行。新组合采用负责人已部署RV0.33.10/638E，保留旧BF4A结果原标签；本任务未部署生产改动。

旧六LMG夹具失败审计：godMode不消除击退，HP100000敌人会长期集火并汇集同侧；不是普通护甲缺失。只读未找到可直接推荐的原版封闭无障碍长平台，未改原地形或放宽旧边界。分段重布置只能作新的短时战斗基准，不能叫连续1200帧或替代长期验收，尚未实现。

## 2026-10-25 — 真实合图交火因击退越场地中止，保留600帧与重建代价

E0C2F3探针第三段X4302.160<safe4305失败。完整两窗600连续帧37362ms，A63.923/中61/P9590，B60.617/57/84；B敌557>511、活动与弹体更高，但单对约5%不是完整收益。B294/300实际呈现且全部整数/无震动；2188复制/2重建，301/145ms长帧全保留，缓存109.375MiB。第三窗仅171条probeTiming不拼性能样本；终态4层/140隐藏原图全部恢复，独立AIR清理与登记释放。

原生AI使六敌逐渐聚到玩家右侧，持续单侧击退；当前最长平台只比原场地多80px。禁止简单放宽边界、瞬移或重跑直到偶然通过，转静态筛新的真实原版场地再核碰撞。独立guarded几何纯变换642B4A仅离线准备：未验变换回native并保留缓存，force不绕过，未构建/测试/部署。按既有授权协调后让出约10分钟给RC验证；本侧正式文件未写。见motion-combat及guarded的README。

## 2026-10-25 — 原尺寸停走合图通过暂停诊断，进入真实战斗验证

6BBCE1探针完成960帧31134ms，五视口实际合图RGB1/alpha0且恢复全等，15/15释放、八计数及玩家不变。移动均41.05→31.5ms，两对37.1167→31.0417、44.9833→31.9583同向；静止28.32→28.85，首次建图213ms及138/228ms长帧全部保留。仍不作战斗收益或部署结论。独立审查核原始JSON，带指纹计算命令被保护钩子拒绝，未重试，实际SHA由获准runner验证。

新camera-atlas-motion-combat-20261025-r1已登记等待：85冻结源仅Main/Atlas变化，保留真实冲刺/六LMG/玩家步枪与全部1200连续间隔，补实际/上一帧呈现、震动/显示变换、copy/rebuild及终态释放。用户RGB2授权已保存；Camera vx/vy为int，实际world小数另有quake/scale，旧0.8+震动RGB96/71反证仍限制生产资格。当前正式文件未变。

## 2026-10-25 — 同帧比较否定补尺寸修复，用户接受RGB2后验证原尺寸停走候选

size-compare-r1第四视口旧/新均RGB2、alpha0、两次恢复精确，20/20截图释放，原RGB1 failed保留；停止pow2，避免128–256MiB与348ms代价。用户明确接受RGB2/alpha0继续验证，但仍要求真实战斗明显提速及功能正常才部署。原尺寸motion-only用强制呈现像素检查和逐帧presented计时校验，r1登记等待；无新生产安装。见camera-atlas-size-compare-20261025及camera-atlas-motion-native-size-20261025。

## 2026-10-25 — 合图补尺寸首轮通过像素检查，仍有静止和建图代价

严格pow2-r1五视口RGB1/alpha0通过、恢复精确，960帧31744ms连续。移动均40.604→35.0875ms，两对均值同向但第一对尾帧变差；静止24.979→31.596，首建图348ms，128–256MiB像素载荷。未部署，不把不同随机世界的像素结果当因果证明。正准备同场同帧旧/新比较，见camera-atlas-pow2-20261025/README.md；保护钩子拦截了独立审查者的二进制读取，未重试，审查者仅核JSON，实际SHA由已准许runner前后核对。

## 2026-10-25 — 合图成本对照取得同向信号，视觉仍不合格

独立成本版E68CE只允许RGB超差后继续收集，保持原视觉失败、顶层ok=false与登记failed；alpha、恢复、身份、输入和内存门禁未放宽。960帧30788ms完整，预绘等八计数不变；移动均37.0417→31.075ms、两对同向，中位/P95也降；静止29.179→30.988。首建图146ms与原生181ms尖峰保留。五视口四个RGB2、一个RGB1，恢复与15/15释放通过，未部署。

只证明暂停整数短路线值得继续研究显示结构，尚非战斗/长距离缓存重建收益。准备只扩物理位图尺寸的窄像素实验，原生块实际400×400，内部512并无证据；旧gutter/横条等失败不重复。准确入口与成本/失败双记录见build/generated/camera-atlas-cost-20261025/README.md。

## 2026-10-25 — 恢复镜头实测，裁块无稳定收益、合图像素门禁未过

核实保留的B190试玩窗口已退出，沿共享登记独立运行；曾等待RConnect/RV占用并按既有授权协调，未结束其他进程。严格裁块r2在600像素RGB差1时失败，保留原记录；新容差版701E完成960帧，连续总32397ms、五视口RGB1/alpha0且恢复精确。原生/裁块移动均37.4958/37.8125ms，P9547/53，保留191ms尖峰，停止guarded crop生产化。见camera-raster-tolerance-20261025/README.md。

随后复用现有atlas做同条件诊断，前三视口RGB1，第四视口RGB2超门限；恢复零差、12/12截图释放，但没有计时样本。旧原始复制与边缘尝试已否定简单补gutter方案，不放宽门限、不部署。见camera-atlas-20261025/README.md。正式A796/RV BF4A保持，镜头目标未完成；本轮结果不能代替真实战斗验收。

## 2026-10-25 — 离线准备整数镜头裁块候选，保持正式游戏不变

按用户保留试玩窗口的要求，未启动AIR。裁块候选新增整数/单位变换与效果保护、可见副本休眠复用、即时层同步及批量强制同步、SATS原图回退、候选错误计数与原生异常保留。只提取六个已确认与A796一致的原方法，不重编落后的完整Grafon源。来源核对和动态AS3语法检查通过；首轮框架World桩同文件编译失败如实保留，修正后通过。源码helper163959，准确回执见camera-crop-20261025/offline-status.json。

尚未构建实际宿主、实测像素或收益、部署；正式A796保持。额外遮罩/滤镜组合及640会继续原绘制，不能称这些组合已经加速。下一步仍须恢复实测，先核对已冻结679A的实际差额；未达到近原版目标，不把候选准备当修复完成。

## 2026-10-25 — 转入镜头平移专项，保留试玩窗口并完成离线诊断构建

用户明确卡顿主要发生在镜头移动。重新核对旧tilecrop两次正向与nativecrop小数/缩放像素反证，决定先以暂停World、整数平移、120fps消除上限的8×120归因检查核实当前收益；不冒充真实战斗。85冻结源仅改Main并新增helper，共86；静态复核后冻结。

游戏尝试r1在预检发现玩家B190双窗口，未编译或启动AIR；与联机任务核实后用户选择保留试玩、先准备。新增真正独立的compile-only分支，offline登记、512MiB JVM、保留4GiB/2GiB预检，build-r1成功产出679A，正式526输入保持；无游戏/像素/性能结论。后续入口与准确回执见camera-raster-20261024/README.md。目标active、未完成，不把用户保留窗口理解为允许自动关闭或排队采样。

## 2026-10-24 — 黑雾遮挡观测完成，停止缺乏收益的隐藏方向

正式A796的只读诊断保留900完整帧/33有效快照，第四段原生击退越平台，原failed不改写、不拼成1200帧。屏内完全被原生黑雾覆盖的显示根仅1–4个（平均2.21），面积和最大16614.545；独立复核纠正视口为实际Stage2032×1084而非窗口外框，最大约0.7543%。根不是独立敌人，面积不是并集；滤镜等未知根仍未知。扫描花208ms，不用于性能结论。正式526输入保持，探针及528实际输入复核一致。

这不足以支持增加有visible/alpha副作用的复杂隐藏机制，停止本方向生产化；没有新的可部署明显提速版本。当前可靠基线仍为大场景57.33ms/原版房34.35ms，近原版目标未完成。原颜色修复和RV负责人更新保留。证据在scene-compat-20261024.md及occlusion-census目录。

## 2026-10-24 — 弹壳候选未验收，补齐当前原版房间基线

用户释放内存后继续实际测试。单帧弹壳三对即时/真实帧后像素和引用检查通过，精确单方法50D6构建与原始素材审计通过；真实候选r1/r2却分别在第四段/第一段被击退推出已验证平台。900/0完整采样帧不能用于验收收益，失败保留，停止此候选且不部署；不把失败原因未经证明归为候选回归。

原39A冻结探针不重编，当前A796/CS7F1F/RC78C/RVBF4A/Loader2050组合下，大场景1200帧/26项均57.33、中52、P9577ms；原版房间1200帧/21项均34.35、中33、P9543ms。原版运行器误硬要求26而退出1，两名独立审查及根review核准21为正确模式数量，仅接受原始负载数据，原failed不改写。正式526项文件与开测前一致。

另排除了把弹痕约两次paint直接认作冗余，以及把前景副本旧小收益归因于大量复制抵消。下一步仅统计屏内被原生全黑雾完全遮住的角色根，暂不改变visible/alpha或动画；原生、RC和RV都读取/管理这些字段。证据与限制见scene-compat-20261024.md、shell-stop-candidate/README.md及combat-review.json。近原版目标仍未完成。

## 2026-10-24 — 实际调用栈采样与焦点上界完成，排除两条窄方向

内存恢复后，独立AIR采样能力确认可用。战斗v1因记录超限且后续角色越平台失败；v2/v3各1200帧26项负载通过，但混合采样时间门禁失败。v3独立审查只接受956条时间/索引有序的CPU出现次数，不篡改失败或推算毫秒。准确环境为A796/CS7F1F/RC78C/RVBF4A/ModLoader2050；RV由负责人独立部署，历史0DBE结果不重标。

炮塔38组本地同步选帧像素/引用全等，但每侧仍141构造事件，不能把全局排队工作归为炮塔自身重建，停止简单guard。FocusManager前两版因错误要求空舞台/最近焦点而0样本失败；v3按原生Stage状态完成1200帧、44快照、连续67,492ms及公开恢复。A/B均57.0/55.4867ms，中54/53，敌740/699，预绘43/1slices；差小且负载混杂，停止全管理器关闭方向，不部署。切换35ms保留，正式文件未变。

下一线索是40条Part.initVis包含栈来自开枪弹壳。visualGilza素材确为单帧单Shape无自身脚本，正在准备新鲜副本的goto1/stop跨帧组件与精确单方法静态方案；不能预认全局队列工作消失，不池化对象、不减少特效/弹体/AI。近原版战斗目标仍未达。详细证据、失败与结论见scene-compat-20261024.md及各generated诊断README。

## 2026-10-24 — TDFC视线候选真实1200帧完成，收益不足不部署

`tdfc-los-20261024-combat-r2`以准确9F2E候选、A170探针在当前A796/CS7F1F/RC78C052/RV0DBE/ModLoader2050组合完成ABBA，26项通过；独立重算1200个连续间隔与时间戳匹配，总73,067ms，结束恢复原始缓存开关。四段均58.9567/60.1867/60.7567/63.6567ms，A/B合并61.3067/60.4717，中位59/58，均9帧超过100ms。仅0.835ms差异，B未快过首A；敌A1010/B904、A预绘4块23slices而B无，不能归为净收益。

玩家全轮400次，A/B各200（不是各400）；B真实8129次调用、101166次同格命中、44804次取格，fallback0，A计数增量0。实际命中充分不代表整帧改善明显，故不部署。前序组件r6的38对等价与完整恢复仍有效，r1–r5及combat-r1的AIR前中止全部保留。更正上条“86AC探针”简写：它是冻结目录UUID，实际性能探针SHA为A170B7EB6CC8F5DB14F033D22C568F733A763C49FDA1EA369E4479B2B6175C58。

正式宿主仍A796颜色修复、TDFC仍7ACD；RC和ModLoader由其负责人独立更新，不把跨组合变快计入本任务收益。下一条仅保留checkShelf将同一Y条件前置的静态建议：仍要遍历loc.objs，需先证明所有活动单位实际调用/枚举占比，未构建、测试或承诺收益。近原版战斗目标未达，详见scene-compat-20261024.md末节。

## 2026-10-24 — TDFC视线空格复用组件38对通过，真实战斗仍待结果

准确7ACD历史源码的单调用空格复用候选已完成r6组件：38对/76调用布尔全等、缓存hits280、阻挡11、旧路径回退10，25个原生Tile/125字段及公开状态恢复。独立回读raw/summary和输入指纹一致，候选9F2E…735E74、探针6BCA…CA1F71；未推进World.step，0性能样本，不宣称整帧提速。私有Class引用仅保留至该隔离进程退出。来源曾漏两个locale依赖，现递归22文件核准历史fb73655及7ACD产物；20文件旧proof、编译失败日志保留。

前序r1可提交3,934,093,312、r3为3,861,843,968 bytes预检中止；r2编译缺locale；r4虽编译D507/958C成功，准备后可提交3,815,768,064不足4GiB；r5登记900秒超时。均无AIR，不把它们当运行样本或删除失败。随后combat-r1编译独立86AC探针后仍因可提交3,918,725,120 bytes中止，根复用同产物启动combat-r2，真实ABBA尚在进行。

新依赖由负责人分别部署：RC78C052/roomfix5单实例ed2fa23d99启动已过，但deployment.json的smoke_status仍pending且性能资格false；本侧不代改回执。ModLoader2050/2.5.0安装verified，FrameRecorder1.0.0与telemetry enabled:true生效。旧DF0F/BD71结果保留历史标签，不能跨组合归因。根任务本轮仅部署A796颜色修复；正式TDFC7ACD保持，checkShelf仅单行Y前置静态方案未构建测收益，近原版战斗目标仍未达。详见scene-compat-20261024.md末节。

## 2026-10-24 — 跨区域角色染色A796已部署；战斗环境配对完成但近原版未达

用户将颜色残留限定为同一大场景换区域后未更新，RV异常限定为开启更卡。真实颜色组件发现两个独立缺陷：AIR存储ColorTransform会量化乘数，旧严格比较拒绝原本属于场景的绿色；玩家自主悬浮levit1又被通用念力物件门控排除。精确ABE2上仅改Grafon.sceneUpdateEntityColor/sceneEntitySameColor，保留外部根色、内部滤镜及箱体原生dropTeleObj；原快速比较失败后用未入显示树的Sprite规范化颜色，并拒绝非有限值。当前src/patches/SceneEntityColors.as.inc已同步等价逻辑，历史冻结源不改。

基线r2、候选、实际安装路径组件各20项通过。宿主A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7于11时部署；严格保留5769其他方法体、1016类/初始化器及素材。state/scene-tint-deployment-20261024.json为verified，备份build/backups/scene-tint-20261024-110720-c26a0e46/pfe_before_ContinuousScene_tint_20261024.swf是ABE2，仅可在正式仍为自己候选时还原。独立审查确认模板与已验证字节码等价、安装冒烟读取实际正式文件。r1探针期望错误、构建内存预检中止及共享登记短时错误完整保留；未降保护、未改其他模组、未动用户存档。详见scene-tint-20261024.md；这是方法级组件闭环，不是完整自然跨区行走或性能验收。

完整可见/隐藏世界各1200帧镜头ABBA：可见跟随/固定均122.18/92.735ms；隐藏110.712/103.332ms，但中位反向且末跟随段最快，火力1254/1769有混杂。今日脚本墙钟也明显放大，不能直接归因GPU、镜头或游戏计算量。已排除新增telemetry.json启用这几轮的正式帧记录器：实际ModLoader均BD71/2.4且无记录器代码；后续仍核实际指纹，不假设负责人版本不变。

随后environment-control基于B7ED/39A冻结源，仅增加首尾UTC/getTimer内存锚点和既有每秒CPU记录的时间对齐，未引入cameraHold或177块新预备。按共享登记等待ModLoader轻量记录器任务释放后，两轮同D972探针/完整输入在当前A796完成：scene26项/normal21项、各1200帧，地形/路线/视口匹配。大场景均71.479/中66/P95 109ms，普通房44.585/41/65ms，仍约1.60倍；玩家均400射、敌1883/1316，平均夹具弹6.644/3.999，人口及实际负载不同。脚本墙钟27.260/11.823ms，区间外44.232/32.759ms，不能只归镜头。对齐CPU覆盖99.626%/98.303%，全进程均2.001/1.716核，不当主线程/GPU。大图原方式计时预绘8块，普通无预绘；所有尖峰和准备成本保留，详见scene-compat-20261024.md。

原测试方式回到71ms，说明先前约107ms不是固定表现，但仍未接近普通房，未部署新的性能修复。TDFC只读审计否定普通AI逐个扫描全159目标的假设；根任务也已核RV关闭后字典清空、原生findCel不全图目标搜索，不继续猜测这两项。下一步仅推进TDFC单条视线内同格重复查询的组件候选，尚无该候选性能收益。当前正式A796颜色修复已verified，历史失败、外部WIP和全部冻结驱动不改；近原版战斗目标继续。

## 2026-10-24 — 纵向镜头缓冲ABE2已部署，真实跳跃改善与安装65项通过

承接用户明确接受的纵向缓冲测试，精确80CF上仅Camera.calc变化，原生541条指令逐条保留，5770其他方法体/1016类与素材不变。唯一状态在nativeAPI；普通跳跃持镜头，持续升降带外跟随，保留观察、缩放、SATS、地图边界、震屏。新字段/计数/计时为零。组件r1/r2的探针命名空间与显示坐标量化期望失败保留，修复探针后r3为65/0、56次实际calc与完整恢复。

RV负责人中途独立更新0DBE，旧6DBB基线不混入。新组合真实跳跃A/B/A每轮720帧、12次150px起落，均49.3958/37.8708/46.0417ms，候选四跳窗全快于前后对应基线；活动28/25/28略不同，约18%–23%不称精确因果净提升或最终FPS。四轮密集战斗各1200帧，A61.3308/67.7975、B66.8700/60.9883，中位合并均60；活动/火力/预绘变化明显，未见持续回退信号，但不算战斗提速。B2离开核验平台而终止，900帧与失败段状态保留，未知位移原因不假定为击退。

根代理与独立复核限定放行跳跃改善。release-qualification绑定8组完整证据及B2失败，check通过；按release gate 2026-10-19.1和持续本机授权于00:00安装ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A。安装后从真实pfe复制启动，共65/0，回执state/vertical-camera-band-deployment-20261023.json为verified，结果F8CC27E8…32E38。备份build/backups/vertical-camera-band-20261024-000000-9ee00a9c/pfe_before_vertical_camera_band.swf为80CF，仅在当前仍ABE2时回滚，不覆盖其他人后续宿主。524依赖及用户配置保持；RC负责人已通知。

整体近原版战斗和实际探索累积问题仍未完成。缓存124→155只否定本轮同位置增长的简单解释，不代表深度探索无问题。foreign SceneRenderChecks WIP及天角兽候选未动；所有失败、尖峰与不利数据保留。详见knowledge/experiments/vertical-motion-20261023.md。

## 2026-10-23 — 真实跳跃归因完成，用户接受纵向镜头缓冲

真实输入跳跃补足旧平地测试缺口。水平惯性污染在r1中完整保留，r2增加收敛条件后纯Y跳跃仍约44–46ms，静止约33–34ms；各窗3次150px完整起落，驻留124、无新预绘。固定视口ABBA共720帧A44.1958/B35.2208ms，说明镜头相关成本值得优化，但固定镜头仅诊断。原版房平台过高导致正常向上换房，失败不删除，不虚构原版跳跃基准。

同位置缓存增长r2因自设1.5GiB进程预算跳过；核实系统余量后r3用2GiB诊断预算、额外启动余量检查，运行512MiB保护不变。r3共1440帧，驻留124→155，private +72.08MB，跳跃43.271→41.521ms；未复现此增长导致进一步跳跃卡顿，不等于排除真实探索累积。原始结果及全部限制见vertical-motion-20261023.md。

用户已接受普通跳跃少移动、持续升降连续跟随的纵向缓冲。仅Camera.calc候选已完成可逆静态检查，严格单方法编译/运行验证进行中；正式80CF及CS7F1F保持，不将诊断约20%作为候选实测收益。RC/RV测试已协调并按共享登记排队；外部WIP和天角兽候选不触碰。

## 2026-10-23晚 — 缓存容差与2400帧复测完成，本轮不部署

用户已答复接受测试近乎看不出的色差，要求先确认明显提速。图章draw与copyPixels各完成172项；均153严格相等、158在RGB每通道≤1/alpha0内、14超界，alpha全部相等。比较器原alpha-only哨兵失败已另存，修正为完整ARGB扫描后没有删反例。两路停止，可复用方法归档KB-000111修订1，细节见dense-combat-near-native-20261023.md及新实验RESULTS.md。

前景同尺寸显示副本先解决测试准备：r1/r2未启用就超时/击退越平台；r3在创建测试敌人前原生预绘测试区域，准备7833ms单列，不算加载改善。30帧真实交战、50次尾同步、四组整屏像素一致，177副本清理完整。同冻结探针两轮各1200帧/90项通过：A/B平均65.0567/63.2633ms与64.010/61.505ms；中位61/61和61/59，敌方882/863与815/887，各五块四好一坏。仅小幅改善倾向，仍有负载差异，常驻约108MiB，未达明显接近原版的目标，不部署、不继续扩建此缓存。

正式80CF/CS7F1F/RCDF0F保持；他人SceneRenderChecks WIP及天角兽候选未触碰。下一次从新的高占比证据入手，不能直接跳过活动屏外单位动画（影响枪口与射击时序），也不复活已撤回配方。当前继续优化目标未完成。

## 2026-10-23 — 遮挡格复用80CF已部署，安装后51项通过

release.py deploy按release gate 2026-10-19.1与本机持续授权完成，state/fog-last-blocker-deployment-20261023.json为verified；正式pfe.swf实读SHA80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D，与回执一致。原BEFC备份在build/backups/fog-last-blocker-20261023-184722/pfe_before_ContinuousScene_fog_last_blocker_20261023.swf。installed-native-r1安装后51/0、ok=true、error=null，结果SHA73C7B1804B411E7C1260DAD0A1D6E1EC91AC6FD37A773DC6901EF673D0FD7B99；没有新增生产计数或诊断开关。

反向大场景baseline-r4有效完成1200帧，A均58.2075/中56/P95 75/敌1806，先前candidate-r2为B56.1975/中54/P95 75/敌1622；火力与预绘仍不同，不报精确净百分比。普通房A/B各1200帧：均35.520833/34.1925、中34/33、P95 49/43、max188/132、敌1651/1767；玩家各400，资格通过，旁路未见回退，不把未启用算法时的随机差值称为其收益。早期失败、820ms未明尖峰和全部混杂记录保留。结论仍是小幅算法改善，整体近原版目标未完成。

当前宿主快照已改80CF；所有绑定旧BEFC的驱动不可直接覆盖新宿主，后续须重新冻结并保留已部署改动。更激进绘制缓存的像素容差已询问用户，未回复未启用。RC DF0F与RV6DBB为各负责人独立更新，不归本任务收益；foreign SceneRenderChecks WIP未触碰、不提交。

## 2026-10-23 — 生产遮挡候选像素通过，继续核对性能

80CF无计数生产候选与BEFC基线使用同探针092CE47A，各91对原生legacy/typed全图状态与像素一致并完整恢复；候选明确引用基线组件证据，不把旧诊断开关或命中数当成生产实测。两对sceneLarge=false仅验证大尺寸图标志旁路。独立opacity-call-cache的101对通过，但真实1200帧A/B均64.24/64.1083ms、中位均61，未见净收益，停止，不叠加。

生产baseline-r2均65.795/中63/P95 91，candidate-r1均60.415/中56/P95 80；敌方出膛1875→1063、活动均46.75→41.55，不能归因于候选。candidate-r2均56.1975/中54/P95 75、敌方1622；完整轮各1200帧、玩家400次，仍待有效反向对照。首候选820ms长帧未落在现有计时脚本段，原因未定。baseline-r1超过1200帧预热未稳定、0计时样本；baseline-r3第二段前原生击退X4298.525越平台左4305、dx−18.343，仅1段完成，整轮失败保留。当前同探针baseline-r4复测中，候选未部署，不称已近原版。

新生产对照使用RC负责人独立部署的0.2.24-aura1/DF0FA0E2与RV负责人独立更新的6DBBAE60（更正先前6DBA短写）。当前安装快照已改为准确完整指纹；旧EB365诊断及约15%离线采集交付结论保留历史组合，不跨版本算收益。完整证据见knowledge/experiments/dense-combat-near-native-20261023.md。

## 2026-10-23 — 真实遮挡复用获得小幅改善，待生产验证

38C7单方法fog-last-blocker严格保留5770其他方法、1016类布局与素材；89对全图状态/像素检查通过，覆盖原86对、负visi两对和弱水，外部起点强制fallback。两轮同冻结探针20×60/90项均通过，A/B帧均分别61.463/60.572ms、63.228/61.418ms，10块7块改善；原生lighting每调用约2.694→2.038、2.743→1.975ms。实际缓存命中1444135/1470722次，原采样步数下降约44%，B火力和预绘仍有差异，不称整帧纯因果值或近原版。仅准备无诊断计数的生产候选，尚未部署。

stamp r2/r3/r4均出现像素差异，最后alpha保持的普通paint在第7对差7个RGB像素（最大1），停止。新的单次调用opacity缓存独立准备、不叠加，不预认收益。RV负责人已部署6DBA；本侧每轮冻结实际依赖，不把RV成果归本任务。当前stage首尾计时已覆盖已知监听；V2大场景22.46ms/普通10.38ms，其余帧间区间仍含时间轴、呈现与等待，不能称GPU或纯绘制。

## 2026-10-23 — 合批通过像素但战斗无收益

4A84单方法inline诊断84对像素/状态一致，1200帧/90项通过，但A58.163/B59.793ms、P95 70/75，无净收益，停止。实际每帧不足3次像素写入，瓶颈仍在遮挡检查。正式组合未改。已释放并通知RC/RV恢复测试；后续stamp仅临时画布组件已排队，新last-blocker仅数学/源码候选。创建stamp驱动时钩子误认源码中的SWF文本为二进制改写，按此前明确授权登记一次10分钟精确补丁，未关闭护栏。

## 2026-10-23 — 原生警戒实测与像素合批准备

activity-internal完整1200帧、26项、44快照通过，原生同包Unit身份匹配；搜索/战斗记忆的Merc可满血且无目标，缩范围不能按公开目标判静止。保守Raider安静空间上界均4.41，仍不改调度。fog-bitmap-lock异常清理写法导致67槽activation，未保留；独立inline候选保持原寄存器和作用域，仅隔离正常路径诊断，尚待组件与战斗对照。正式安装保持，目标仍未达到。

## 2026-10-23 — 末采样剪枝真实对照无收益

fog-terminal 852BCD单方法候选84组30000格状态/像素全等，真实20×60/90项通过，A/B均63.343/64.007ms、中位60/61，B火力和预绘更少仍无净收益。真实提前拒绝约20.2%射线，但视野计算每次2.743→3.027ms，停止且不部署。双方测试时段按用户已授权协调完成，已告知RC任务可恢复排队。下一步独立批量像素更新、内部AI状态只读验证；后者外部stub探针首编成功且QName/no-native-def/no-numeric-slot静态审计通过，尚待AIR。正式组合保持。

## 2026-10-23 — 活动范围实测与视野候选

activity-spatial诊断1200帧/26项、44快照通过，统计仅替换stats、其余56方法保留。活动均47.16，其中屏外26；收紧空间范围理论可少13.86，但未观察internal搜索状态且当前宽限内立即可少0，不直接改调度。保留前两次FFDec词法导入失败，第三次与严格审计成功。新fog-terminal-bound针对持续执行的lighting，以末采样遮挡证明不必遍历整条射线；已独立源码审查和隔离导入，正在修正审计对可选参数flags的错误假设，未运行、未部署。正式组合保持，近原版目标仍未达到。

## 2026-10-23 — 密集战斗继续：停止无净收益和低覆盖候选

3401单方法decal诊断完成1200帧，定位每次outer7.4–7.85ms、scenePaint2.89–3.19ms、素材准备.055–.088ms；原版对照在第四段真实击退越平台终止，保留前三段归因，不作完整性能。原汇总错误要求cut>0已独立修复报告、核原数据不变，未改原FAIL登记。休眠身体缓存实际467次变更全部恢复，短ABBA均63.708→64.468ms，无净收益，停止。

BCCF lighting2整数循环六组全图组件状态/像素一致；真实移动900帧只有16次收尾调用，第16窗原生击退越平台，按守卫失败。不能把此前lighting合计2.5ms全算给lighting2，停止该方向。原V2已采视野半径2000、retDark=false；下一步只读活动快照核未参战远敌上界，不更改追击/伤害/弹体。正式BEFC/CS7F1F/RC EB365保持，新近原版目标尚未达到；clipRect旧无收益记录再次核验，不重跑旧配方。

## 2026-10-23 — 继续近原版目标：密集负载与热点归因

本轮仍在进行，正式BEFC/CS7F1F/RC EB365未变。denseV2修去观察器段边重复设置，真实Shift/六LMG/玩家ASSR同探针1200帧：原版均35.573/中34，大场景均63.253/中59，实射400/2009与400/1109，仍有明显差距。原V1的2659ms尖峰大部分来自探针自身2591ms startCase，不能当作游戏长帧或扣除后宣称提速。

背景短ABBA表面6.24%改善但火力/预绘不等，长ABBA无收益；完整400px含边缘扫描opaque0/571，停止不透明缓存。区域合成缓存诊断1200帧calls0，容量候选排除。Location准确单方法计时显示大场景逻辑15.7–19ms，原版6.5–7.7；大场景单位4–5ms、子弹3–5ms、原生视野2.5ms，箱子不是主因。Bullet细分命中墙体1.35–3.25ms/帧，遍历单位.28–.64；RC owner准确19FF采集诊断仅.37–.46，0重建/0compare，不继续改历史语义。归因宿主不部署、不作生产墙钟验收。

两轮内存保护中止后保留失败证据；用户关闭暂不用程序、余量恢复7.16GB再继续成功。新证据/限制在knowledge/experiments/dense-combat-near-native-20261023.md。当前继续BEFC decal分段和可逆休眠显示根缓存审查；旧回退宿主、Alicorn仅源码与他方SceneRenderChecks WIP不触碰。

## 2026-10-23 — 单人战斗优化已部署，实际安装复验通过

RC负责人已将准确0.2.24-offline1/EB365安装到正式release；原574D备份在RConnect/build/m52/recovery-offline-deploy-01。部署回执7DB4BDC4…65EE86为deployed-smoke-passed，原运行器ae58b8049b确从实际release取样，两端版本/tick、join welcome/unitsync、日志与登记通过，自有实例清理完成。根及子代理独立核对当前22项只RC变化，root BEFC、CS7F1F、配置和其他模组保持。未混入墙面候选或撤下的下午配方。

性能结论限关闭LAD/RV/WB、未尝试联网的真实单人战斗路线：准确生产包平均69.615→58.866ms，约15.4%，两轮诊断ABBA也重复同方向；473ms偶发长帧未解，不称全部配置近原版。首次联机78/0及安装冒烟补足资格，当前限定目标完成，下次启动生效。MEMORY/README和combat-stable-driver-20261022.md已同步；后续是否继续追尖峰由新任务接续，不重复原验收。外来SceneRenderChecks WIP与天角兽仅源码未动。

## 2026-10-23 — 资源恢复，首连78项完整通过，进入部署

用户退出暂不用应用并要求优先推进。保留原6GiB启动门槛，不改系统设置或关闭他人进程。修复的是隔离测试的AIR虚拟路径、原生走廊站位、附件调整后的弹药取样时机与收尾竞态；EB365产品保持。最终driver07/native08/d0048aff49两端39/0、首次连接各1、旧效果无重播、新双向弹道/枪口/冻结与解除/最终确认和清理全过，根独立读回结果C103B588及候选散列。

约15.4%真实战斗平均耗时改善证据保持；473ms偶发长帧未解，不称近原版。RC负责人进入精确备份部署及实际安装冒烟，普通墙面候选不并入。尚未记为已安装。MEMORY收束成76行左右的当前入口，先前完整快照无损保留MEMORY-history-20261023-0818.md。证据及失败原因见knowledge/experiments/combat-stable-driver-20261022.md末节；其他会话SceneRenderChecks WIP及天角兽仅源码边界保持。

## 2026-10-23 07:45 — 用户继续：冻结首连驱动通过，定位系统额度限制

RC first-connect-driver-02已成功编译，子代理只读验证11冻结文件/22安装项一致及早期观察修正进入7FB9源，驱动0A3B、产品EB365。未启动双游戏。进一步只读WMI确定自动C盘分页文件约31GiB，接近250GiB卷的1/8默认增长界限（Microsoft文档支持，非唯一因果断言）；物理空余13GiB但commit仅1.412GiB。未动系统设置，向用户给出正常关闭暂不用QQ/Chrome的具体余量信息。正式BEFC/7F1F/574D保持；goal工具仍blocked，余下真实门禁/部署/复验不减。

## 2026-10-23 07:33 — 测试编译触发内存保护，重新标记受阻

07:29状态重新active后3轮同一资源限制，最后一轮仅核对、无进展。RC first-connect-driver-01被原512MiB运行保护中止，原始compile-memory记录降至308609024字节、exit125，prepared仍未编译；没有双实例运行或产品失败结论。现在余量约1.136GiB仍低于6GiB启动线，正式BEFC/7F1F/574D哈希全同。update_goal返回blocked，保留候选与有效测试证据，不重试低内存构建、不扩任务。

## 2026-10-23 07:26 — 恢复后的第三次资源阻塞，目标标记受阻

上一回合完成具体夹具审查及修正核对，分类progress；本回合仅重核资源/安装，分类no progress。原生memory snapshot可提交约2.034GiB，首次双实例所需6GiB不变；同一条件已连续3个恢复后目标回合，无自身可清理进程、无新首连实测证据。update_goal已返回blocked；不把候选性能改善冒充已部署或目标完成。正式BEFC/7F1F/574D保持，余项及已完成证据见MEMORY。没有改动游戏、存档、配置或他方WIP。

## 2026-10-23 07:23 — 首次联机门禁的早期漏检反馈

恢复后第2回合。独立只读确认首次连接夹具仅在round检查生产包/远端显示，可能遗漏connecting/prepare短暂重播；另需处理peerClass晚赋值、begin清证据、before早退不触发RENDER。具体意见已交RC负责人，其源码仍在修订，本侧不改RC文件、不重复测试。提交余量2.73GiB低于6GiB，正式BEFC/7F1F/574D哈希保持。此轮进展是修补验收设计缺口，尚无双人通过或部署结论；目标active。

续核：D65B4345已补早期来包与begin前判定。准确产品ExplorationSync每ENTER会invalidate，故before早退本身不证明无RENDER；已纠正这项意见，不将其当新增门禁。最终仍需双人实际结果。

## 2026-10-23 07:14 — 恢复目标，排查提交内存与测试残留

get_goal已active，新阻塞审计从1计。只读确认物理空余约13GiB而提交额度仍约3GiB；完整权限进程检查无AIR/JVM和匹配本任务的Python。独立审计测试正常清理与88条已结束登记，当前没有已证可安全释放数GiB的自有残留；没有杀进程、修改系统设置或降低双实例6GiB门槛。资源调查已一次交付RC负责人；其继续准备首次真实接入夹具。正式BEFC/7F1F/574D、候选EB365保持，性能/单实例旧证据不冒充最终门禁或部署。

## 2026-10-23 02:28 — 部署目标标记受阻，保留已证收益

同一双实例内存限制连续三目标回合重现，RC原snapshot当前3.696GiB低于既有6GiB。正式BEFC/CS7F1F/RC574D保持，当前可用的性能/单实例功能证据已全部整理，未发现新的可推进实测入口。update_goal返回blocked；不是完成或主动暂停，也不改用户目标。候选EB365、两轮ABBA及574D直接对照约15%收益、56生命周期及86实际采集验证均保留，473ms偶发长帧未解。剩余首次真实双人接入/双向事件、正式部署与部署后冒烟由RC负责人集中接续；资源恢复或新验收证据出现后再重入，不再次重复索要内存释放。

## 2026-10-23 02:22 — 单实例采集回退通过，正式部署仍待双人入口门禁

RC生命周期56/0、实际原生喷火弹采集六分支86/0全部通过，产品EB365未改。真实采集不是只检查资格值；范围不含全部身体效果或对侧渲染。发布范围已收敛为首次真实双人接入和双向可见事件，约4.95GiB余量未达既有6GiB启动门槛。RC负责人接续门禁和正式部署，此处不重复催用户释放内存，不降低护栏、不动用户进程。原574D正式保持，明确性能收益约15%但未部署；目标active。性能代码/证据已提交b00ddb1和79d378a，他方SceneRenderChecks WIP保持。

## 2026-10-23 01:54 — 无诊断接口的生产候选复现明显收益

RC负责人构建EB365353/0.2.24-offline1，原574D与候选分别跑同一冻结rcnative探针3fa568…：各1200帧90项PASS，连续均69.615→58.866、中位64→54、P95 96→80、>100ms51→32，五块均值/中位全改善。玩家400同、敌810→884，最大306→473保留，不称尖峰消失或近原版。源与runner独立复审通过；正式仍未动，联机/效果门禁由RC负责人继续，之后其统一部署/复验。本侧不接管他方源码候选或SceneRenderChecks WIP。目标active。

## 2026-10-23 01:33 — 两轮离线采集收益确认，转正式形态验证

88CC诊断两轮真实输入交战各1200帧90项，五ABBA×2全部同向。r2连续时间戳跨段不重置，主中位67→56ms、均71.645→60.852、P9597→83；保留B286ms峰值、动态火力/人口和探针成本，不称近原版或长帧解决。r1原段内结果63→54，计时边界纠正单独存档。纯离线采集是首个有重复明确收益的方向，正式安装仍未改。

提供574D最小三类生产源码提案（无探针接口/计数器）给RC负责人，等待其正式形态构建与联网验收；本侧接无API独立进程同夹具性能对照，直接比较原574D。BG3仍因WB状态不可访问拒绝且0变动，继续只读找已存在入口；r5 null拒绝仅静态完成，暂不抢占主路线。目标active，部署门禁尚未通过。

## 2026-10-23 01:13 — 最小离线采集候选，背景残留层原因明确

用户要求持续到明显下降，目标active；无新正式部署。RC574D冻结源最小三类候选88CC639E编译完成，来源0BE07E23；仅跳过纯离线presentation/body采集，保留实际呈现、墙痕和念力，首次host/join永久撤资格。真实输入ABBA探针接入中。只读确认标准assr/autor先以player=false记录，不能泛称玩家记录无限积留；A/B恢复历史非无状态，主统计保留切换成本。

背景diagnostic-2完整早检查因lower额外隐藏WallBlendBackgroundLayer拒绝，0应用、0复制；400原生scratch正常，正审该层生命周期。睡眠r3/r4失败指向UnitVortex safeTree null；原数据不删，准备仅拒绝未知null的r5后看可摘节点规模，不把r2已证负收益重写成有效。所有自有测试已释放；正式BEFC/CS7F1F/RC574D保持，RV由他方维护。

## 2026-10-23 00:38 — 原生输入对照否定r2，拆分画面检查与性能测量

真实输入r4完整1200帧90项，20/20窗双方实射。睡眠Slaver显示根移除A/B均65.86/70.13ms，五块B均更慢，停止、不发布。此前r1–r3失败与边界修正原样保留，原生落地/受击/AI不重写。r3扩大类的首个长像素检查在gate启用前被抛飞打断，准备首次真实落地后10帧的独立画面/恢复检查。新增探针自身/census/save/后置监听器分段，避免段末诊断停顿污染解释。另一条背景双层预合成仅准备诊断。正式BEFC/7F1F保持，目标active；旧2f10ffe提交保留此前诊断，当前新夹具尚待里程碑提交。

## 2026-10-22 23:35 — 识别夹具悬空偏差，睡眠显示根完成像素与唤醒验证

- 玩家animate严格E498诊断完成，主要成本在bodyState；同pinok16重复goto像素/树一致但广播67次构建事件。正式站立已有guard，不重复实现；仅准备静梯和腾空窄候选。
- 发现stableMotion仍每帧把脚放在地面上一像素并清dy，恰触地被collisionTile排除，stay未建立；旧数据保留但限制为同驱动归因，不再称正常行走验收。新nativeInputMotion用真实方向键与原生物理，正在实现。
- sleeping-root r1无合格精确Raider而失败，110是累计跳过事件非唯一单位。r2增加仅构造器不同的Slaver后像素/零clips唤醒/清理通过；1200帧ABBA存在活动人口和预绘时间趋势，合并13%只是线索，不部署。准备短交错真实输入复验。
- 正式BEFC/CS7F1F保持，其他会话RV独立83D8；Alicorn源码候选不接管。用户明显改善目标仍active。

## 2026-10-22 22:50 — 原房间对照确认差距，透明地形路线无效

原版/连续场景同seed同房间同路线各1200帧完成；完整地形与路线hash一致、六敌双方实射。原版中位恒33ms，大场景51–61ms；正常房固定镜头与总人口不同，不能据此独归调度。证据native-combat-20261022-room24-normal-r1和scene-r1。empty-terrain-route200-r1完整1200帧，A/B均值69.129/69.132ms，55.35次/帧空层隐藏没有收益，不发布。玩家Unit.step分组诊断00A1严格审计完成，测量中；远处睡眠敌人显示根候选准备中。正式BEFC/7F1F不变，用户明显改善目标仍未达成。精确源码写入保护误拦以已授权root会话同摘要授权解决，未绕过护栏。

## 2026-10-22 22:18 — 排除开火文字刷新，完成地形与物体显示归因

- GUI.setWeapon精确诊断1200帧/37项：每帧约0.07–0.113ms，不能解释玩家4ms；不实施文字缓存。离屏10组CSS/外部写入对照全等，仅为语义证据。
- worldlayers完整1500帧/50窗双方实射，完整/无fog/无地形/无物体/无world中位64/62/52/48/40ms，均68.0/65.4/59.9/52.3/44.4。恢复完整、无身份变化、无原生可见性重写；所有隐藏均仅诊断，非可部署优化。
- 横条绘制约5%改善、脚本额外约2.5ms，像素仍不全同，停止继续打磨gutter。下一步补原版同房间体验基线、全透明层显示诊断和玩家step分组。
- 两个测试辅助类漏import导致首轮编译失败，已补齐，失败证据保留。正式BEFC/7F1F保持；RV独立更新6593，不归功或回退。

## 2026-10-22 20:59 — 场景分段和停止弹实射对照完成，绘制定位到横向分块取样

- Location严格诊断1200帧/24项，玩家约4ms、敌人约1.3ms、子弹1.6–3ms、原生lighting约2.2ms；没有捕获错误。暂停敌人的环境切换仍多做，箱子总成本小，暂不大改远处对象机制。
- 停止弹738F真实双方开火ABBA，每段剔除60帧后中位56/55/59/59ms，没有明显提速；虽然遥测证明误唤醒，不以此宣称战斗优化完成或部署。
- Atlas r5的横条使0.8下的大取样差缩到max2，但未全等；竖条仍max127。原生引用/清理恢复通过。继续原生gutter对照，以及玩家开火里每帧GUI.setWeapon的归因。
- 正式BEFC/7F1F保持，RV独立发布按实际每轮输入冻结；本任务不认领、不回退其更新。

## 2026-10-22 20:01 — 主循环热点缩小到场景更新，继续查异常唤醒与绘制取样

- World单方法计时1200帧/24项通过；主循环14–16.5ms，Land13–15.1ms，GUI约0.1ms。原全图唤醒在末段从39增到154，需要新的弹体与激活来源观测，尚未认定原因。
- Atlas实射ABBA中位73/62/70/79ms，有潜在显示差额但像素仍失败、负载随时间变化，不部署。该轮活动39–52，未复现全图唤醒。CPU记录是全线程合计，不误称渲染用时。
- 正式BEFC/7F1F不动，继续最小像素与调度诊断。

## 2026-10-22 19:45 — 同层交战与绘制候选复核，主循环计时进入实测

- 同高真实地形200px往返、双方原生实际出膛夹具成立。短显示1500帧每短窗均实射，完整中位60ms、仅单位57、无对象48，只作归因。普通Bullet单位段0.34–0.42ms/帧、hitTile1.08–2.23ms/帧，未支持先重写全单位扫描。
- 子弹混合315次临时切换全部恢复，但无稳定收益；玩家cache出现63像素差并且800帧无稳定收益，均不发布。atlas153检查中10像素失败，原生弹痕/破墙/SATS均通过，后续聚焦取样路径而非缓存更新。正式BEFC/CS7F1F保持。
- World诊断经历activation与导入类漂移两次严格拒绝，专项精确证明后只复制step到原BEFC类，C431单方法宿主最终完整审计通过。其他4758具名方法、1016类及原始素材保持。world-step-route200-r1正在运行；所有测试是隔离存储/私有桌面/共享登记，不写真实存档。
- 按已有授权协调RC/RV时段；RC19:11–19:17窗口主动归还，继续登记等待。天角兽仅源码、SceneRenderChecks.as他人WIP不接管。目标继续active，尚未测得可发布的明显改善。

## 2026-10-22 — 战斗驱动纠错、compact实际对照与角色层归因（进行中）

- 用户目标为继续至明显下降；仍无新部署。识别旧setLocPos逐帧重置武器/滤镜的夹具污染，新增setPos与玩家实际开火、换枪后100帧暖场和双方逐窗实际出膛计数。不能把驱动提速计为游戏优化。
- r1正式游戏占用拒绝启动；r2编译成功但沙箱拒绝CreateDesktopW、未创建AIR，核对后释放自己中断登记；r3隔离1500帧完整且无缺块，玩家500次实射，因敌方停火窗而未过持续交战门禁。角色层all/units均显著慢于none/boxes，是新显示归因线索。
- 五版实物追查确认76dd47d误将被拒compact实验带入0.8.2；旧配方注释纠正。800帧同实例开关、267玩家实射与逐窗真实敌火通过，关闭compact并未改善，前四可比窗中位54/58/58/56ms。保留当前正式路径，不以历史误带入代替性能证据。
- 旧出生点各寻地板造成玩家/敌人80–340px高差；正在增加真实同层连续平地路线和枪械/睡眠状态观测，再测角色层屏外显示。详见knowledge/experiments/combat-stable-driver-20261022.md。天角兽仅源码、SceneRenderChecks.as他人WIP保持。

## 2026-10-22 01:30 — 回退版上的战斗热点对照，拒绝无收益候选

- 按用户“继续尝试解决战斗卡顿”推进，完成11组独占运行对照13,200帧及像素/功能检查；正式BEFC/CS7F1F/TDFC7ACD保持，本轮无部署。RC574D保持；RV7852是其负责人独立发布，LAD8ADB。保留天角兽source-only边界和SceneRenderChecks.as他人WIP。
- 裁块像素失败；停止弹取消陈旧速度投影功能成立但无稳定整帧收益；Unit.blit去重2753次完整ARGB比较相同，计时仍无稳定收益；都不发布。分段宿主仅改Bullet.run，严格保留其他方法/布局/原始素材，首次计时器绑定错误的0样本轮明确作废。
- 普通Bullet单位段约0.10–0.14ms/帧，直接地形hitTile约4.05–4.21ms/帧，后者主要真实draw。隐藏所有对象层提供显示开销线索，逐组及全根裁剪未给出稳定收益；不把不完整画面当优化。
- 新只读8帧观测确认睡眠敌人11段子动画在isPlaying=false时仍推进；实际停住11段再恢复的ABBA没有整帧收益。世界显示树鼠标交互关闭也无收益，但测试鼠标(0,0)没有充分真实输入覆盖，保留这个限制。原生区域完整包含快路仅静态候选，不为未测微小收益再构建。
- 记录knowledge/experiments/combat-recovery-followup-20261021.md及evidence汇总；13个本轮Python脚本语法通过，构建/审计负例与失败原始结果保留。所有自有测试释放，无真实存档写入。后续先改善固定工作量/短窗交错归因，再作实际交战复验；不能沿旧下午配方重装。

## 2026-10-21 22:38 — 按用户要求回退下午两轮改动，再做整帧对照

- 用户反馈指定“跳跃和高速移动…先不做测试”消息后的性能修改变慢。对照实际对话、提交和回执，确认回退点BEFC；备份5432及旧回执到build/backups/afternoon-recovery-20261021-222045，只恢复root pfe。用户保存退出后安装，51项正式文件隔离复验通过，state/afternoon-recovery-20261021.json verified；两份下午回执标rolled-back-by-user。
- RC574D/RV76314B81是各自负责人独立回退，LAD8ADB保留。本任务不写其发布文件；CS0.9.0、编辑器、地图、TDFC、配置及存档保持。保留另一会话的天角兽源候选与SceneRenderChecks.as WIP。
- 六敌旧/新/新/旧4800帧、完整人口1200帧均通过，未证明5432稳定改善，撤下版最大帧更高但射击进程不同不能唯一归因。回退版完整人口仍58–63ms，约129单位暂停，0缺块；已核对Grafon内无关热函数和匿名体，无已证实重编译漂移。
- 尝试裁块显示原型同场1200帧：原/新/新/原中位51.5/48/46.5/52ms，初步有收益，仍未到近原版；SATS/WB/多缩放与像素即时刷新尚未完整验收，因此原型只留探针，正式保持BEFC。不继续收益上界仅约0.9ms/帧的透明erase路线。
- 回退与6组实验原始输入/帧数据/loader/登记均保存；所有自有AIR结束。新记录knowledge/experiments/afternoon-recovery-20261021.md，脚本recover-afternoon.py、recovery-compare.py、recovery-presentation.py。后续只从BEFC做单一路径候选，不能按旧配方恢复下午组合。

## 2026-10-21 — 一房大小报警候选与原版追击失联续查，未构建

- 用户选择先给原版报警加范围，确认中心为发送者、整个区域1920×1000（X±960/Y±500），允许跨旧房边界；另一会话正在改动，本任务仅调查/候选编写。
- 新增 src/patches/SceneAlicornAlerts.as.inc，budilo和telepat同时限距，保留原接收者条件及普通房间分支；未改control、actPort、活动调度、生成或存档。未构建、测试、集成或部署，没有发送跨会话消息。
- 查清500为飞行悬停距离、失联按感知检查衰减并搜索旧位置、听觉/重见刷新、接报可再广播、瞬移可重新靠近；setNull(true)含回血/回位，engaged保活不等于永久仇恨。完整源码位置续入原诊断报告。
- 范围及后续定向合并要求见 design/alicorn-alert-range-candidate.md。此候选保留逐跳传播和原版瞬移，不承诺已消除所有围攻。对话所见BEFC回退属于其他会话，不接管其未提交回执/代码；只提交本任务文件与记忆片段。

## 2026-10-21 17:56 — 原生弹痕素材复用5432已安装并复验

- 六组发布前403项通过；严格方法/类布局/常量池与18种素材审计通过。RC负责人最后协调为“紧邻旧版复测结束后可更新”，于17:54:26交接登记，没有在其轮次中换宿主。
- 备份7D42至build/backups/impact-20261021-175427/pfe.swf，只替换root pfe为5432A3B9…677B71D；正式文件独立工厂全效果136项再过，state/impact-deployment-20261021.json verified，其他发布依赖/配置回读完全保持。AIR与登记已释放，已通知RC新宿主来源及回退点。
- 组件约11%收益不等于战斗FPS提升；真实交战仍卡、整体未达近原版。多帧原生素材尚未逐帧真实分支配对，记录验收边界；未发布透明erase、clip、紧画布或atlas实验。用户已有游戏需正常保存退出并重启。
- 当前只读/源码复核无阻断；门禁另显式拒绝runFailure/diagnosticOnly。更新README、报告与MEMORY，提交仅本性能任务文件，保留他人SceneRenderChecks.as标记。
- 收尾构建元数据调用因同时含SWF指纹读取与JSON写入，被保护钩子启发式拦截；沿用用户授权登记本会话5分钟精确摘要，原调用随后通过。没有改保护定义、换工具绕过或再次修改正式SWF。

## 2026-10-21 17:46 — 战斗弹痕候选完成主要验证，等待部署窗口

- 两轮只用于诊断的profile发现高速段Bullet的大部分时间嵌套在hitTile→sceneApply.decal，实际paint/cut draw主导；计时互含不相加。纠正诊断process-policy的自动performanceEligible推定，保留原数据和更正说明。
- clipRect555D与缓冲复用2F6C未见稳定收益，tight04D6因旋转像素差异拒绝；通用素材复用8506只留实验。最终5432限定18种原版空构造/无脚本静态Shape素材，作用域限一次命中；未知类原路径保留。
- 5432在马哈顿128项、工厂完整效果136项、真实交战16项、存读档/重置51项和SATS60项通过。组件八轮交错100次decal平均476→423.5ms；交战中位52/60/57.5/69ms、696次敌方开火，整体仍未达到近原版，不报FPS固定提升。
- 正式7D42和RC574D等未动，等待普通房回归；已按RC负责人的协调请求保留宿主至约17:59再评估部署窗口。所有测试共享登记、唯一AIR存储/私有桌面，只结束本任务实例。透明erase仅新增未启用实验片段。
- 详见knowledge/experiments/combat-impacts-20261021.md；当前候选构建impact-native-build.py、测试impact-run.py、门禁impact-release.py。天角兽讨论与其他会话WIP未接管。

## 2026-10-21 15:40 — SATS视野截图与弹痕对象复用已部署并复验

- 用户明确恢复测试和部署。拒绝分批截图33C1的边缘像素差异，改为原光栅起点/尺寸、视野内逐块捕捉；旧区域冻结，新区域补齐，关闭/清图释放。sceneApply复用Rectangle，未改AI、碰撞或联机。
- 最新发布组合马哈顿关效果60项、工厂全效果60项、进出/刷新/存读档/地图51项、大图高速交战16项、普通房12项，共199项通过。冻结参考、缩放坐标、诊断文件名和私有调用等探针问题均保留失败记录后修正；逐像素无放宽。4672其他方法、1015类布局、旧常量池不变。
- 只安装pfe 7D423BD7…85BCD4，备份build/backups/sats-20261021-154054/pfe.swf为BEFC；正式文件独立实例再验60项，回执state/sats-deployment-20261021.json verified。CS7F1F/TDFC7ACD/RC574D及其他发布依赖和配置保持；RV8D4A等其他任务的新发布已纳入最新组合，未回退覆盖。
- SATS同场景截图旧917/902ms→新319/320ms；完整高速交战候选53/52ms、旧65/58ms、普通34/33ms，随机人口/战斗不同，不能报因果比例。最大帧仍278ms，整体近原版未达标。首屏诊断耗时也不作为2–5秒普遍保证。
- 所有游戏登记独立存储/私有桌面；没有用户存档或其他进程操作。保护钩子所需备份精确调用按已有授权登记5分钟，未关闭护栏。AIR已释放，已向获准协调的RC负责人回报宿主与回退点。详见knowledge/experiments/sats-viewport-20261021.md；另一会话天角兽草案与SceneRenderChecks.as无实质diff标记保留。

## 2026-10-21 — SATS性能候选恢复实测，首轮画面对比未通过（处理中）

- 用户本会话明确“请进行测试和部署”，取代性能任务的暂停测试要求；天角兽机制讨论的独立约束不变。正式BEFC/CS7F1F/TDFC7ACD/RC574D未改。
- 仅从BEFC导入Grafon，候选33C11A47：4672个其他方法、1015个其他类布局与旧常量池保留。首轮探针AS3保留字错误修正后，sats-20261021-pixels-r2实际运行34项，原生V开关/行动点/释放/冻结复用通过，7组像素对比未通过；未部署。
- 部分缩放用例坐标误设到地图外，已修测试世界坐标并加入差异图片。其余截图差异继续诊断，失败不豁免。游戏测试均登记、独立AIR存储和私有桌面；遇其他任务占用等待，不关闭其进程。

## 2026-10-21 — 天角兽大场景机制头脑风暴，保留讨论草案

- 用户要求构思机制调整，沿用先不做测试。读取 game-brainstorming、静态机制证据与单图编辑设计，比较局部范围兼容、情报/搜索协同、据点/心灵中继三个方向。
- AI 推荐局部协同轻量版：区分转述与直接接敌，消息不可无限续传，三类瞬移分别限制，脱战靠失联而非房边界。支援名额只限制主动召援，不能限制现场自然接敌；援兵生成另受有限配额管理。数值、表现与方向均未获用户拍板。
- 讨论稿 design/alicorn-large-scene-brainstorm.md，含取舍、实现接点和风险；无代码/构建/测试/部署。原版能力已确认事实仍以静态诊断为准，不把新提案回写为原版机制。仅提交本轮设计与记忆，保留其他会话 WIP。

## 2026-10-21 — 暂停实测期间排查跳跃、交战和SATS，保留源码候选

- 用户反馈跳跃/高速移动轻微卡顿、交战明显卡顿、V开启SATS延迟，明确“先不做测试”。无AIR/JVM、无编译、无测试、无部署；正式BEFC/7F1F/7ACD/574D指纹未变，没有查询/关闭用户进程或要求退出游戏。
- 准确Grafon来源确认sceneSats对全体驻留块各次截图。独立候选SceneSatsViewport.as.inc实现视野分批捕捉、镜头补齐、摘下离屏快照、关闭释放，临时恢复原生隐藏角色层并finally还原。sceneApply另复用Rectangle。prepare-sats-viewport.py只生成文本，combined源码FF9A7015…00E4067；未接旧整包或安装点。
- 静态发现永久engaged、正式TDFC按lastSeen>=0唤醒、原版子弹子步全单位扫描、弹痕取消相交的未完成预绘。未验证各自占比，未改变追击/碰撞或移动预算。
- 归档knowledge/discoveries/static-performance-20261021.md（verified:false）。候选编译/像素/新曝光动画相位/效果兼容/整体性能待验，继续暂停测试。保留并合并期间另一会话已提交的天角兽记录；SceneRenderChecks.as无实质diff的标记未纳入本轮提交。

## 2026-10-21 — 天角兽整图警报与远距瞬移静态诊断

- 用户报告一只发现玩家后多只瞬移围攻，明确先不做测试。本轮只读原版 1.02 源码、CS 源、TDFC 已部署冻结源及既有审计，未测试/构建/部署/修改玩法。
- UnitAlicorn 的 budilo/telepat 不限距离，原房 Location 合并后广播到整图；警报独立提高战斗计时，tr=2 actPort 直接找玩家附近落点且无施法距离上限。NativeSceneActivity 将共享目标锁存为 engaged，可能放大活动范围。已区分原版延迟援兵、Land.aliAlarm 及 TDFC 不接管 alicorn 的边界。
- 正式宿主 BEFC、CS7F1F、TDFC7ACD 指纹匹配原回执；未重新反编译/执行历史审计。详细代码位置、判断限度和建议见 knowledge/experiments/alicorn-alert-static-20261021.md；结论为高可信静态原因，未声称现场复现或修复。
- 下一步可按局部警报/来源、防无限接力和瞬移有效范围处理，保留无边界追击及原版能力。测试继续暂停；只提交本轮记录，不接管 SceneRenderChecks.as 既有 WIP。

## 2026-10-20 15:30 — 用户暂缓后续实测，保留已安装修复

- 用户选择“先保留修复，稍后再测”；正式游戏PID39908使用application.xml运行，未关闭。后续不启动AIR，当前本任务无占用/自有进程。RConnect必要兼容及直接协调授权仍在，但负责人尚未交付最小离线候选；正式RC仍574D，本任务未写RC源码或发布文件。
- 已完成部署与保存：宿主BEFC+TDFC7ACD，442项先行检查+51项安装后复验，回执verified；CS0.9.0/7F1F、编辑器/地图保持原字节。提交CS4a41636、TDFC9217549。整体卡顿仍未达到近原版，不能将组件加速或单轮较好数据作为达标。
- 最后有效自然人口样本activity-census为高速中位67/68.5ms、入场5162ms、16项通过；不同轮次大图可达98/105ms，普通对照47.5/53ms，随机战斗与机况导致波动，须恢复后严格对照。活动单位从26增至70左右，远处部分有目标或历史参战保活；未改变追击/脱战规则。
- 六敌人受控人口试验local-population因环境长停顿超时，只有第一段完整，整轮作废；r2/r3均在启动前发现其他AIR而退出，无新游戏。sandbox内进程列表漏见宿主实例，受权只读核对才确认正式游戏；不能把受限环境AIR=[]当全机空闲。run_owned异常现在明确写performanceEligible=false。未能读取电源事件，未断言电脑睡眠。
- 接续：用户恢复实测后，先核对已安装文件与是否仍有用户游戏，再用enemy-baseline-test.py --local-enemies和全新证据前缀完成普通/大图人口控制对照；该模式仅私有测试移走原生敌人，不代表正式体验。随后取RC负责人基于574D的最小离线修复做组合测试，不发布room-entry加载WIP。显示裁块/遮罩/合图原型仍仅探针引用，WB层次/完整截图兼容未验，继续禁用。

## 2026-10-20 12:47 — 等价计算优化已安装，整体性能未达标

- 用户已允许必要RConnect单人/大图兼容并直接协调。RC负责人01a086bb已接下离线UnitPresentation采集、结束记录淘汰和无人接收快照检查；本任务不并行写RC。RC活动源为experimental/room-entry-fast叠加build/m52/coop-bundle-04，不能从根src覆盖。
- 排除RC的私有副本16项通过，移动中位98/89ms、RENDER计时0；不同原生人口/战斗进度，不能宣称确定改善百分比。仍有卡顿，RC不是唯一原因。
- BEFC+7ACD当前组合normal/scene/native分别12/16/51项通过，宽窗同入口布局，移动中位普通47.5/53ms、大图98/105ms。大图末段第289帧墙钟66137ms，附近1306/2182/1022ms；ENTER_FRAME不呈同量级，最低可用提交内存8.6GB且无其他AIR。尚未归因，不删异常、不用该均值宣称性能进步。
- 12:45登记备份并只安装root pfe BEFC与TDFC 7ACD(scene2)，442项先行验证；安装后native51项通过，15入口当前会话通过、所有生产依赖与输入复核无漂移。回执state/performance-deployment-20261020.json为verified，备份build/backups/enemy-perf-20261020-124545。CS0.9.0/7F1F、编辑器与地图、其他模组保持原字节。
- 这次安装依据等价像素/状态、组件同状态ABBA和玩法回归，不声称达到近原版；atlas/tilecrop/fogpixels显示原型均未部署。原版视野变更有严格方法/布局审计，TDFC从fb73655+scene1冻结线构建，未发布HEAD authority接口。
- 下一步已编译只读SceneActivityCensus，按实际调度区域记录远处仍运行的原因和播放动画种类。测试enemy-speed-20261020-activity-census在独立AIR运行；等待RC离线候选作新组合验证。

## 2026-10-20 — 宽屏交战卡顿实测，性能候选验证中

- 同2048窗口/6名原生持枪敌人：普通房移动55–57ms，大场景108–110ms，灯光/RV/WB关闭仍有差距。事件分段及世界显示对照确认计算与绘制均有成本，未归咎单一模组。
- BEFC原生视野类型优化通过两地图像素/状态及严格字节审计；7ACD TDFC威胁缓存通过197项同算法检查，已前移对应GameBridge源码。二者组合的普通房、大图、原版生命周期回归排队，正式文件未改。
- 遮罩裁切整帧无稳定收益；裁块/四层合图仅约9–10ms后段差值，未接产品。atlas第一轮图层顺序错误在画面对照中拦住，修正后17项画面与16项运行通过。完整证据及失败保留于enemy-speed-20261020.md。
- 另一会话部署的CS0.9.0编辑入口保留；未回退或提交其工作。RC离线采集路径只读发现潜在开销，正在隔离排除对照，不改RC或正式清单。近原版目标未完成。

## 2026-10-20 — 0.9.0单一大地图与现有编辑器扩展，部署及复验通过

- 用户恢复编辑器开发。增加完整单网格文档、原生编辑器大地图面板、平移缩放、轻量概览、远端笔刷和物体操作、保存/扩展/应用备份；现有预渲染明确显示局部48×25。附192×50工厂研发部素材试验图，启用文件只在原先不存在时创建。
- 编辑器25项、游戏22项通过后，11:24备份并仅更新Editor、EditorTools、CS0.9.0；宿主81C1与其他模组不改。安装后独立editor-2a95849e1eb1和game-fb62e285b785再次47项通过，15个当前会话loader入口全通过。回执deployment-v090.json=verified，备份authoring-v090-20261020-112459。
- 样例168个固定Box逐件对应；真实E取物、原生伤害破墙、远端绘图、探索地图、存读档及重新进入读到编辑结果通过。早期失败来自概览的密集标签开销、探针跨域接口及原生箱体坐标预期，均保留原证据；登记表WinError 5属于启动前环境暂缓，未记成游戏通过。
- 格式与构建见design/single-map-authoring.md，范围和失败详见knowledge/experiments/single-map-authoring-20261020.md。最大尺寸、完整任务、联机与全效果性能未验，2–5秒加载目标不在本轮通过结论。另一对话的移动/敌人/视野WIP保留，不混入本轮提交。

## 2026-10-20 — 单一大地图编辑验收中，暂未部署

- 用户明确恢复编辑器开发。192×50 工厂/研发部样例、编辑器扩展和游戏入口候选已完成；独立编辑器22项通过。缩放全图改为轻量概览，旧版密集标签造成的长停顿已复测消除。
- 发布前游戏测试 game-f5fae18c4ea7 的22项中2项未通过，门禁停在自动验证步骤。定位为探针忽略 Box 默认 size=1、并将重力后的当前坐标与生成坐标比较；现依原版 createObj/Box 改为逐件匹配 begX/begY，保留缺失列表待重跑。正式文件尚未修改。
- 正在补测远端原生地形笔刷与缩放标签刷新。仅处理本任务单一地图/编辑器文件，另一会话的敌人/移动/视野候选不纳入本次提交。
## 2026-10-20 — 回读LAD0.5.1独立部署，不新增运行

- 收到获授权灯光任务完成通知，只读核对LAD正式BAFE52B9…C04C47A、02:58安装回执、579项门禁证据与安装后43项PASS；宿主81C1、CS CD65、WB1411保持。本任务未写发布文件、未启动AIR/JVM。
- 最终全14且RV/WB开启、2544×955证据remains-lad-perf-20261020023131019287：大图开灯102/95ms、关84/86；普通开43/46.5、关33。两大图开灯段89步/89绘制，0缺块、无其他AIR。屏幕外弹丸重复绘制已减，但整体仍未近原版。不同路线/效果/尺寸，不能直接横比此前36–37ms。
- 历史deployment-v082回执继续保留LAD4291验收基线，当前快照更新到BAFE；不重跑旧依赖验证或覆盖新灯光。剩余重点为全效果大图逻辑和显示成本归因，时段已由对方交还整合方。

## 2026-10-20 02:23 — 补记不同效果配置的性能边界

- 获授权的LAD任务反馈并经只读证据核对：新宿主配其1F5B候选、RV/WB开启、1424×861、另一入口的暖大图开灯90.5–92ms/关76–80ms。非本轮已部署4291组合，不能横比因果收益或宣称全部配置近原版。条件、路径及限制补入motion-v082报告；未新增AIR/JVM或改发布文件。

## 2026-10-20 02:11 — 0.8.2镜头移动优化与内部箭头修复，部署及复验通过

- 用户恢复实测并允许协调灯光测试时段。按唯一AIR身份、私有桌面、无争用和内存门禁完成实测；仅结束自有实例，真实存档与设置未写入。
- 宿主81C1按方向分帧预绘、跳过原生视野无效扫描及无法增亮的射线；CS CD65移除实际相邻房间内部箭头，保留真正出口、外沿和0.8.1破墙修复；WB1411远处墙面分片完整发布并修正刷新失效。条带C285因像素不同拒绝，不部署。
- 最终598项门禁通过，备份后只替换宿主/CS/WB；由实际安装文件重建隔离输入，51项原版玩法复验通过。回执deployment-v082.json=verified；备份motion-v082-20261020-021117。LAD4291及RV/TDFC/RC、配置清单不动。
- 灯光关闭固定路线：普通33ms，大图暖36–37ms、冷41ms；快速跨区冷46ms。开启灯光后大图暖47–48.5ms，仍未达到普通33ms。全部路线0可见缺块/0同步兜底；实体随机不同，不作严格整体百分比结论。见knowledge/experiments/motion-v082-20261019.md。
- 安装复验后已向两相关灯光任务明确交还AIR/JVM时段，对方将基于81C1继续0.5.1验证。后续先核对新组合，不能把本轮剩余卡顿写成全部解决。

## 2026-10-19 23:22 — 移动卡顿与内部标记候选，用户要求稍后再测

> 2026-10-19 23:22：移动卡顿/内部箭头候选0.8.2已保留，用户最后要求“稍后再测，先保留候选”。**本轮未部署，停止新增游戏测试。** 正式仍0.8.1/241E、宿主02BF；WB0DA与LAD6F最终字节尚未运行回归。4D9原绘图逐像素通过，但关闭灯光后的完整帧仍慢，不能称性能已解决。接续state/in-progress-v082.md、candidate-v082.json及knowledge/experiments/motion-v082-20261019.md。

- CS/CD65内部箭头104→0且出口保留；宿主4D9分帧预绘10块四层逐像素一致，其他4672方法/1015类布局/原常量池不变。最后完整帧仍有WB峰值，WB0DA分帧候选仅编译、LAD6F最终版本未回归；未发布。
- 正式双实例出现，测试在启动前退出；用户明确选择稍后再测。无关闭其他实例或跨任务发消息。报告motion-v082-20261019.md保留失败、拒绝方案、环境漂移与后续步骤。

## 2026-10-19 21:37 — 0.8.1恢复内部边界墙可破坏身份
- 用户要求恢复大场景中原本可破坏的房间边界墙。旧版马哈顿实测1535格仍不可破坏、hp10000，定位buildLoc边缘标记与随机mainFrame材质/耐久覆盖。
- 新NativeSceneWalls在合并前只恢复内部邻接边的可破坏材质伤害参数，保留钢墙、外沿/角、缺房、原模板固有保护和门/陷阱；图像、碰撞与对象引用不动。固定图保留已有损伤，重复调用不回血。
- 候选马哈顿20/工厂15/关闭模式15项通过；21:37只部署CS为0.8.1/241E48EA，宿主02BF、LAD0.4.1/94A及其他模块配置保持。实际安装文件独立回读21项通过、1587格恢复，原生地形命中正确扣血/破墙/更新画面。备份boundary-v081-20261019-213736，回执deployment-v081.json verified。
- 本轮沿“大场景 (2)”已有明确协调授权发送进度，另一个对话的18行箭头和移动性能WIP未纳入候选/提交。完整证据、早期探针命名失败、截图时序修正与未验边界见knowledge/experiments/boundary-walls-v081-20261019.md；不宣称所有武器/地图或总体性能已通过。

## 2026-10-19 — 记录RConnect后续独立部署基线
- 收到对方主动完成通知后，只读核对其coop-bundle-04/deployment.json=deployed-smoke-passed与安装指纹：宿主A61→02BFABE6…D9240、RC→574D2B51…441AFE；CS B5、TDFC032、WB0BD均保持。
- 对方报告保留大场景偏移接口，安保432项及普通双侧启动通过；本任务未额外测试、未回消息。17:14本轮性能证据不移用为新组合数据。
- 后续修复必须基于02BF或更新基线保留安保接口，不用A61整体覆盖；本轮旧回退脚本应因宿主不匹配而拒绝，不能绕过。历史部署回执不改写。

## 2026-10-19 17:14 — 0.8部署完成，最终当前组合采样与正式启动通过
- 用户明确要求部署；收到RConnect主动交窗后完成无争用采样，未发跨任务消息。当前RV763/LAD514下真实工厂3499/4373/4359ms，全场183/156/166单位；大图待机50/59ms、步枪65ms、加特林74ms，普通房间参照41/44、46、54ms，均真实开火40/119发。持续性能差距如实保留。
- 367项预检通过；首次Install因短时新AIR在写入前拒绝，确认其自行结束后重试，381项含备份/回读全部通过。仅部署宿主A61、CS B5、TDFC032、WB0BD，备份upgrade-v08-20261019-171447944；deployment-v08.json verified。
- 正式文件隔离启动pfe-modsettings-continuous-installed-20261019171448通过20项，14模组全部加载，新版本/注册/心跳正常，本任务实例已清理。保留RV、LAD、清单、配置与真实存档。
- 更正16:20的未完成状态：旧正式0.7关闭合并已复现同一生成#1010，见报告；候选功能及部署现已完成，整体流畅度仍未达到普通房间。回退仅四文件且核对当前版本，不覆盖后续发布。完整结果scene-v08-20261019.md。

## 2026-10-19 16:20 — 0.8统一回归与新RV依赖核对，待最终采样/部署
- 四个候选固定A61/B5/032/0BD。旧RV组合已完成27机制、51原版、34工厂+10内容像素、113体验、600帧预绘及24双墙样式检查；门和固定物体无偏移，边框/缩放检查通过。
- 旧组合三次无争用进图3854/3997/4864ms；大图待机50/51、步枪58、加特林70ms，仍未证明达到原版流畅度。LAD两种缓存及弹痕小画布没有稳定收益，未部署；细分计时也未支持继续修改LAD。
- 核对发现RV已由负责人更新至0.32.3/76314B81，保留并同步隔离副本；新组合113体验、600帧预绘通过。加载/原版战斗参照正在等待无争用窗口，不发跨任务消息。
- 保留两个失败：第五阶段原生预步进Radscorpion #1010尚未在旧宿主复现；探针设置模块启动竞态#1009已修ready门控并以native-release-r2通过。正式仍0.7，尚未执行安装，当前指纹/流程见in-progress-v08及scene-v08-20261019报告。

## 2026-10-19 v0.8 候选：门/边框修复、远处敌人暂停，尚未部署
- 用户补充静止持续卡顿，已退出正式游戏；明确允许远处未参战敌人暂缓，并允许必要 TDFC 兼容。此前 CS/RV/WB/LAD 授权继续有效。没有跨任务发消息或启动子代理。
- 原生门/物品显示坐标、边框被重绘重置、移动机关端点和每原房奖励池已修候选。独立物品审计由另一任务提交4b805eb，报告 native-object-audit-20261019.md，仅按其实际覆盖引用。
- NativeSceneActivity 不改完整对象/碰撞数组，靠近、目标/受伤、效果和弹体预判保持运行；TDFC 同字典跳过远处未参战敌人。冻结正式 TDFC fb73655 源码增桥，不混入 HEAD 未发布联网接口。
- 活动机制/奖励/移动机关检查通过，最初炮塔一像素差已定位首次落地同步，修后stage5全部显示断言通过。无争用同世界暂停/全运行两对中位43/57、55/72ms，有收益但仍未达到原版流畅度；继续查绘制，不宣称性能已完成。
- 目前正式仍0.7，候选/测试/停点和指纹详见 in-progress-v08.md。新发布门禁尚未完成，不把诊断SWF或未同步冻结目录部署。

## 2026-10-16 v0.7加载优化已安装，三轮真实工厂4.49/4.39/4.38秒
- 用户明确接受按视野提前绘制，先生成全场敌人/物品/碰撞；第一相机位置批量首绘，按移动方向预绘两圈、已绘块不因移动淘汰。保留原生遮罩/滤镜，裁剪透明材质填充边界，WB缓存确定性接缝计算；缩短原版渐隐空等但保留生成/点击/控制/HUD步骤。
- 非诊断、无其他AIR随机任务三轮4486/4392/4382ms，184/197/176单位、24首屏块。功能诊断另有5724ms，不能保证所有地图每次≤5秒。诊断移动仍有长帧，未宣称开火或整体帧率恢复原版。
- 最终Native51、Factory34+内容像素10、Experience113、WB470/4120组合通过；首屏四层9830400像素精确一致；600帧移动缩放无缺块/同步补绘/移动淘汰。保留失败实验和旧组合边界，见loading-v07-20261016.md。
- 15:12:32门禁283项核对后仅安装宿主2A466248、CS70C06879、WB0.5.6-scene DF9AA072；保留PI宿主合并、RV BAA、LAD514、14模组清单和配置。正式启动pfe-modsettings-continuous-installed-20261016151253通过19/19，实例已结束；回执deployment-v07.json verified，独立备份upgrade-v07-20261016-151232751。
- WB A40独立候选3D41DE62未混入，本轮不写其开发源码。用户要求不发跨任务消息，已遵守；无新增子代理/真实存档访问。后续回退只接受本次三个精确目标，拒绝覆盖后来发布。

## 2026-10-16 v0.7部署前核对：尚未写入正式文件
- 首轮只读门禁在清单比较处停止。已核对实际内容：生产/隔离均启用同14个1.02模块；隔离生成器按既定流程把CS和探针放在末尾，并将CS的DLC列设为0，直接逐行相等是错误判据。修正为1.02启用项的目录/入口精确集合与数量，保留逐模块产物指纹检查；实际正式路径启动仍另行验收。
- Factory运行本身34项通过，外围临时命令误读PowerShell脚本后的空LASTEXITCODE，导致内容核对尚未执行；随后单独运行verify_factory，10项通过，没有重跑或改游戏断言。

## 2026-10-16 后续灯光0.3.0发布已核对，保留更新
- 02:23只读确认LAD在02:20:29独立备份488并安装3BA；宿主11B/CS F6ED未变。其正式回读remains-lad-projectile-20261016022047545通过131项，指纹与当前安装一致。
- 更新本模组回执附记、README与MEMORY：本次0.6四文件原始快照不改，旧回退必须拒绝覆盖后来的3BA；灯光自己的回退仅恢复488。没有再次替换任何产物，也未发送跨任务消息。
- 已公布22.404秒、72/96ms仅属于488验收组合，不代替后续3BA全组合性能。原验收与后续发布证据明确分开。

## 2026-10-16 v0.6原版地图模式与光影兼容已安装
- 原版任务生成后的标准主层合并，设置默认关闭、即时保存，下一次载入生效；普通返回保留、重新开始按原版规则刷新地形及灯具。随机地图读档回基地规则保留。
- 区域预绘12pass、240小块常驻；修复遮罩临时父引用/WB旧覆盖释放，灯具首次绘图前转换免二次全图重绘，恢复原版及LAD照明平滑。保留0.5地图/交互/缩放/区域绘图及弹痕修复。
- 最终13模组含RV BAA：Native51、Factory34+内容像素10、Experience113、Lab64通过；WB470/4120组合、LAD81+7及改键39+6+21通过。947项检查和1065项安装事务核对，正式原生启动18/18通过。所有来源与失败见knowledge/experiments/native-v06-20261015.md。
- 最终无其他AIR性能：首载22.404秒，开火中位/P95/最大72/96/198ms，同配置普通房60/76/104ms；命中最多更新2块，无全图重绘，Private峰3583MB。仍有长帧，不能宣称已达原版流畅度；视野合成是残余成本线索，不关闭效果交付。
- 02:14:08仅安装宿主11B、CS F6ED、WB3B、LAD488，保留新RV/公共快捷键/Addiction及其他发布。回执state/deployment-v06.json，独立备份3087208c；正常保存重启生效。回退拒绝覆盖后续修改，不能使用旧整体备份。
- 用户选择等待空闲且不发协调消息，已遵守；多次受争用性能弃用。RV独立发布导致门禁正确拒绝旧组合，更新隔离RV并重跑final6后安装；final5中断无完整结果保留。编辑器、全剧情/联机与长期性能仍未全面验收。

## 2026-10-15 v0.6 加载与阴影调查继续（尚未部署）
- 用户确认硬黑块、原版刷新规则，并授权本轮 CS/RV/WB 范围逐条短时精确调用登记。当前正式安装仍为0.5。
- 实测光照位图更换后 smoothing=false；候选恢复原版平滑。批量预绘把区域pass从288降到52，同时保留320px伤害小块；最新诊断初入22.714秒，对照0.5为26.666秒。WB候选改为邻域透明像素前缀和与背景保护查询缓存，效果仍需回归。
- 失败和边界：全240块同帧额外像素对照导致5.86GB峰值及退出，无结果；改12处采样。一次旧版重绘#2015尚未稳定复现。FFDec语法/验证错误修正后batch3及prefix运行通过。当前下一步为像素对照、开火诊断与原版地图设置接入，不宣称已完成。

## 2026-10-15 v0.5 显示、交互与性能修复已安装
- 完成地图尺寸与居中、三档镜头/背景铺屏、区域底墙/色调/水/实体颜色和开关电同步；持续 E 与 Y 动作补实体墙遮挡复核，原版念力例外保持。弹痕按实际范围更新，背景建立空间索引，RV 保留每帧完整逻辑减去重复查找。大爆炸跨块 alpha 污染已修复，4 组独立原生像素判据通过；原生栅格少量差异按证据限定，不宣称全图逐位相同。
- 最终相同宿主/入口/兼容模块/驱动：Experience 111、Factory 34 + 内容/像素 10、Lab 68 全绿；632 项门禁通过。RV 42 与 WB 470/4120 的具体宿主边界及全部早期失败保留在 experience-v05-20261015.md。
- 两轮无采样 PNG 的性能测试：首次进入 25.052/27.851 秒（旧 62.992），开枪帧 P95 63/52ms（旧 193），最大 202/154ms，最多弹痕刷新块 20→2。仍有偶发长帧，未达到完全原版体验；Private 峰 2.7–3.0GB 高于基线，不声称内存优化或严格固定种子因果实验。
- 16:18:17 安装 0.5.0/RV v0.30.5-scene/WB0.5.3-scene，保留原版Map1宿主布局和其他模组已发布字节。独立原生启动 15/15 通过，证据 pfe-modsettings-continuous-installed-20261015161849；测试驱动未安装，未碰实际存档/玩家进程。回执 state/deployment-v05.json；回滚 build/upgrade-v05.ps1 -Action Rollback，四目标独立备份 8a1b6645。
- 首次安装因 PowerShell 将 null 备份路径转换为空字符串而在替换前失败，目标原值与备份核验无损。保留失败9290c631回执；改为 NullString.Value 并验证原子替换后重新安装成功。没有关闭钩子或放宽门禁。
- 后续：剩余长帧需要逐次开火/命中与绘制阶段计时；继续实际隔墙拾取路径及长时内存验证。编辑器暂缓，联机/完整工厂剧情未认证。

## 2026-10-15 v0.5 候选检查中，尚未部署
- 处理用户报告的光影、射击卡顿、实体墙隔墙取物、缩放、首载和两处地图显示问题。源码已补地图尺寸/居中、镜头三档、原区域色调、弹痕局部刷新、背景索引、RV完整逻辑快速路径、持续E/Y遮挡验证和实体颜色缓存回链。
- 构建曾因私有命名空间映射停止；限定核对原生 changeWeaponNow/actionReady 后修复。保护钩子拦截手动构建续跑后，用户明确授权一次会话绑定短时调用；没有关闭钩子。最终宿主2032451D…基于已发布Map1 BEBEE…，4659无关方法与Land布局审计通过。
- 并行期间WB更新0.5.3、RC更新Map1后又fix15、MSW更新配套版；兼容源迁移到WB正式f32e4a9，RC种子字段/构造保留，隔离运行副本已刷新RC07B76E…与MSW DDADA3…，不回退别人发布。
- RV三项42断言通过；WB独占43/43（3.6ms）、破坏54/54、覆盖373/373与4120组合通过。WB首轮并行8.3833ms超8ms的红项保留，未放宽阈值。
- Experience多轮已通过地图、缩放、基础/持续/Y交互、区域水和12区域显示；release2在终端弹痕逐像素检查停止。先前远块列纹证实为测试逐块alpha回写自造，已改独立画布一次绘制。当前旋转样本各1世界像素及放大爆炸边缘少量差异，正补ARGB/native-local对照，未放宽像素断言；完整结果保存scene-decal-checks.json。
- 门禁upgrade-v05已准备，尚缺最终Experience/Perf/Factory/Lab四套同字节验证和安装冒烟。本条为实际中间停点，不代表发布完成。

## 2026-10-15 v0.4 工厂接入与墙边黑块修复已安装
- 用户确认实际游玩墙边黑块，且入口不是原版工厂。旧入口确为自制走廊；改为12个原版工厂模板的7680×3000连续验证地图，保留原内部格子、444个物件和603个装饰，240画面块进入时一次预绘。
- 复现黑块在关闭RV/WB后仍存在，定位第二背景层backBmp2漏做世界到画面块的坐标换算；修复并对替换数量加断言。证据见knowledge/experiments/factory-v04-20261015.md，保留原失败截图和原生像素对照。
- 最终FA0.3.1/WB0.5.1/RV0.30.4-scene组合34项工厂、63项旧走廊、10项内容/绘图通过；12:03:27仅替换宿主、入口SWF和场景XML。安装原生启动15项通过，回执state/deployment-v04.json，回退build/upgrade-v04.ps1 -Action Rollback。未改其他模组、清单、配置、正式存档或玩家进程。
- 最终首次进入54.7秒，短通道31帧中位89ms；诊断峰值Private6501MB，不代表稳态。性能仍需优化，未达稳定30帧。工厂是原版素材连续测试关卡，完整剧情/原色调分区/地图缩略图和编辑器仍不在本轮交付内。

## 2026-10-15 v0.4 发布前组合核对
- 工厂候选首轮34项、旧走廊63项、原版内容/绘制10项通过，尚未安装。检查发现 FirearmAttachments 已更新为0.3.0，旧测试副本仍为此前字节；停止部署，复制当前安装组合重测。
- 清单差异实际来自 test-mods 把 CS 的 DLC 标志写为0；正式清单未变。门禁仅比较本次认证的1.02活动模块，并逐一核对模块字节；共享多版本清单整体保持原样，不据此声称DLC支持。
- 失败探针、初次通过与最终重测各保留独立证据目录；不覆写历史记录，不回退其他模组的新版本。

## 2026-10-15 v0.3.1 信息页按钮热修
- 用户反馈“大场景”按钮无法按动。已复现信息页打开12帧后allStat=2，0.3.0的travel只允许1，点击直接返回。
- 修正信息页暂停门槛，保留其他暂停、剧情、重伤、负重及转场保护，补原版pip.noAct。旧测试同帧点击漏测；新测试还发现开场对话未完成，改为原版按键推进对话、连续30帧可操作后再开菜单。
- 最终63项短程回归通过（107.3秒）：稳定菜单进入/返回/再进入、五类限制、重复点击、整图预绘、战斗、破坏及多存档。只重编和替换ContinuousSceneMod为0.3.1；宿主、RV/WB、清单、配置、正式存档及玩家进程保持。
- 01:26:47已安装，原生启动15/15通过；回退build/hotfix-v031.ps1 -Action Rollback恢复0.3.0入口。记录knowledge/experiments/entry-v031-20261015.md；回执state/deployment-v031.json。当前性能边界不变，玩家需正常重启以加载修复。

## 2026-10-14 v0.3 整图预绘与性能验证已安装
- 用户提出进图一次生成全部地图；192块预绘常驻，像素共用，局部破坏不刷新远处，RV按需复制单位子格快照。编辑器继续暂缓。
- A/B/A及逐步对照后撤销无稳定收益的遮罩实验；最终1699步行帧零生成，中位55ms/p95 73ms，仍未稳定30帧；进图13.5秒，完整进程峰值3.1GB。
- 48场景+42视野+43墙面+15安装原生启动通过。23:10:26安装0.3/RV0.30.4-scene/WB0.4.2；清单、配置、正式存档及玩家进程保持。新FirearmAttachments纳入最终加载验收。
- 回退build/rollback-v03.ps1；回执state/deployment-v03.json。详见knowledge/experiments/preload-v03-20261014.md。下一步实际试玩与剩余显示/内存瓶颈，不扩展编辑器。

## 2026-10-14 v0.2 入口、兼容与持久化已安装
- 信息页顶部原生旅行按钮；生产模块与外部驱动分离；多存档地形/弹痕保存；320px 缓存、遮罩复用、RV局部绘图与WB世界坐标共享材质覆盖层。
- 用户明确允许RV/WB必要修改；不发布RV另一个任务的authority接口，安装包基于0735491。完整44项、原版墙43项、视野37项、真实安装原生启动14项通过，依据见 integration-v02-20261014.md。
- 首次嵌套Loader验证错误后回退；第二次原生运行成功但空stdout被误判集合，再次回退并修正检查；最终18:17重新安装，18:18:57独立原生启动通过。当前备份pfe_before_ContinuousScene_20261014-181702.swf，回执state/deployment-v02.json。
- 全模组步行中位56ms/p95 85ms，仍需性能优化；当前尺寸/少量敌人通过不代表联机、密集长时运行和全部交互已验收。玩家游戏未关闭，重启后使用；编辑器继续暂缓。

## 2026-10-14 v0.2 首次安装后验证回退
- 候选完整 44 项、墙面 43 项、视野 37 项已通过。首次安装备份为 `pfe_before_ContinuousScene_20261014-180224.swf`。
- 安装后外部 Loader 包裹游戏的验证器在 MainFE 构造时触发 #1009，检查列表为空；MainFE 构造函数直接访问 stage，不能作为普通 Loader 子资源启动。按发布门禁先执行 rollback，根宿主、清单、RV/WB 已恢复原指纹。
- 后续改用原生 pfe.swf 作为 AIR 初始内容验证正式目录启动；按钮行为由相同候选字节的完整独立游戏验证，不再用包裹启动器推断产品行为。

## 2026-10-14 v0.1 连续大场景运行样片
- 做了什么：扩展单一 Location，400×400 像素分块预绘，保存/重放破坏画面；隔离宿主、可复现构建、试玩启动器和自动检查齐备。短程生命周期和最终完整测试通过，后者 23 项断言。
- 关键决定/发现：编辑暂缓；不拼接旧房身份；实体共享空间，只有绘图分块。整类 FFDec 回编风险以四方法移植限制，4665 个无关具名方法/初始化字节码保持一致。实际范围和数据见 `knowledge/experiments/runtime-validation-20261014.md`。
- 遗留/下一步：性能峰值、压力和原版交互覆盖、破坏地形跨读档保存、其他模组兼容；当前未部署。AGENT_SCOPE 仍因保护规则未创建。自定义二进制写入被拒后已放弃，最终使用标准 FFDec CLI；没有关闭保护。

## 2026-10-14 项目创建
- 做了什么：根据已经完成的当前 SWF 调查建立隔离运行项目。
- 关键决定：单一逻辑 Location；绘图按镜头处理；编辑功能暂缓；不修改正式游戏。
- 遗留：运行版构建与游戏内验证。范围说明文件的创建被保护规则拦截，未写入。

2026-10-15 20:43 验证失败记录：native-v06-candidate 在 phase9 等待随机工厂原地读档超时。原版 Game.as:297-299 明确随机地图读档回基地；属于驱动错误期待，候选按原版运行。修正探针为回基地后重新进入并确认设置仍生效，保存失败证据，重编驱动后重跑。
