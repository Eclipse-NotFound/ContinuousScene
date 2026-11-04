# 2026-11-04 交战卡顿：子弹碰撞通道修复与空间分桶（宿主单方法替换）

被测技能：remains-runtime-debug / remains-mod-build / remains-swf-patching / remains-release-gate / remains-mod-memory
测试工作区：D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene

用户指令：「请按方案进行优化」（方案 = `design/exploration-and-combat-stutter-optimization-plan-20261104.md`）。

本文只覆盖**方案支柱 C 的 C1（子弹碰撞）**：其余条目按本仓已有实测证据**不实施**，理由见 §8，避免把已证伪的路线重跑一遍。

基线：根宿主 `pfe.swf` = **1D2004AB**（2026-11-04 13:36「弹痕不取消预热」），`scene.xml` `1CEA74E2`。
CS release 在 18:35 由并行会话部署到 **0.9.9 `D04CD26A`**；本轮三次游戏内运行都用这个 0.9.9，
所以 A/B 两臂之间只差宿主。

---

## 1. 问题链（源码级）

1. 已部署宿主里 `Grafon.sceneTick` 每帧试图把「视口 ±500px 内的单位」写进
   `World.w.visual.root["sceneCU"]`，包在 `try/catch` 里；
   `Bullet.run` 每颗子弹每帧读同一个属性，也包在 `try/catch` 里。
2. `World.w.visual.root` 是 `fe.MainFE` —— 一个**密封类**（非 `dynamic`）。
   AVM2 对密封类读写未声明属性会抛错（读 `#1069`，写 `#1056`），
   因此这两处 `try/catch` 每天都在「抛了再吞」。
3. 后果一：`Bullet.run` 的 `_collisionUnits` 永远拿不到列表，恒为 `loc.units`
   （大场景实测 ~122 个单位），于是**每颗子弹每帧都要全量扫描单位**：
   O(子弹数 × 单位数)。
4. 后果二：交火时数十发子弹在场，就是**每帧数十次异常构造与展开**。
   这条开销与敌人类型无关，只与「同时有多少弹」有关——与用户描述的
   「各种敌人交火都卡」一致。
5. 全仓确认该通道**没有其它读者**：`sceneCU` 只出现在测试探针
   (`src/tests/SceneBulletBoundaryChecks.as`) 与设计/记录文档里。

## 2. 改了什么（两处，均为宿主方法级替换）

候选产物目录：`build/generated/combat-collision-20261104/`，构建器 `patch_bullet.py`。
只替换两个方法，类布局不变（`classesUnchanged`，`changedMethods` 校验为
`fe.graph.Grafon::0:1:sceneTick` + `fe.weapon.Bullet::0:1:run`）。

### 2.1 `Grafon.sceneTick`：每帧建「整张房间」的分桶表

- 表存在 `World.w.vgui["__csBulletGridV1"]`。
- **为什么是 `vgui`**：这是本轮抓到的一个真 bug。最初版本把表挂在
  `World.w.visual`（`World.as:414` `this.visual = new Sprite()`），想当然地以为
  `Sprite` 是 dynamic。离线探针
  （`src/SpriteDynamicProbe.as`，无头 adl）实测：
  - `new Sprite()["x"]=…` → **`Error #1056: Cannot create property … on flash.display.Sprite`**；
  - `new MovieClip()["x"]=…` → 正常；
  - 自定义密封类 → `#1069`（阴性对照）。
  也就是说 `Sprite` 是**密封类**，`MovieClip` 才是 dynamic 类，而 `World.w.vgui`
  声明为 `MovieClip`（`World.as:88`）且开机创建一次、不随房间变化。
  若按原写法部署，`sceneTick` 会**每帧在 ensure/cull 之后抛 #1056**，
  整条预热/剔除链路直接死掉——这个探针把该事故挡在部署之前。
- 单元格 **512px**，按地图尺寸 `loc.spaceX * Tile.tileX` 推格子数（9600×5000 → 19×10）。
- 每个单位按其 AABB **外扩 96px** 覆盖到的所有格子登记，登记顺序 = `loc.units` 顺序。
  外扩解决「建表与子弹 step 之间单位移动一帧」的覆盖问题。
- 分桶数组**跨帧复用**（只把 `length` 清 0），稳态不产生每帧垃圾。
- 非大场景 / `loc` 变化 / 没有 `vgui` 时把表置 `null`，子弹自动回落原生全量扫描。

### 2.2 `Bullet.run`：按子弹自己的坐标查桶

- 彻底删除 `World.w.visual.root["sceneCU"]` 的读与 `try/catch`。
- 命中条件与原版**完全一致**：仍然用原 AABB 判定、原过滤字段、原
  `break`/`continue` 语义；改变的只是「候选单位从哪来」。
- 三道安全闸（任一不满足就回落 `loc.units` 全量，即当前线上行为）：
  1. `targetObj != null`（指定目标弹走原生分支）；
  2. `_gridData.loc === loc` 且 **`_gridData.units == loc.units.length`**
     （同帧内单位被生成/移除 → 表不可信）；
  3. 玩家自建表后位移 < 256px（传送/换窗口等大幅跳变 → 表不可信）。
- 查询格子为空时用共享空数组，`for each` 零次迭代。

## 3. 等价性（离线，可以复算）

`build/generated/combat-collision-20261104/src/BulletGridBench.as`
（mxmlc 编译，`adl64 -runtime` 无头运行，纯合成 AABB，不碰游戏）。

| 组 | 内容 | 点/用例 | 不一致 |
|---|---|---:|---:|
| [1] 静态 | 100 只聚在玩家周围 + 30 只散布全图，随机点 | 6,000 | **0** |
| [2] 建表后单位移动 ±96px（一帧陈旧） | 同上 | 6,000 | **0** |
| [3] 对抗几何 | 跨格边界、超大盒、退化盒(`X1>X2`)、越界盒、精确落在格线/盒边界 | 4,000 + 9 | **0** |
| [5] 建表后新增单位 | 原生=130 号单位，带闸=130，**不带闸=-1** | 1 | 闸必要性已断言 |

「不一致」的口径是**首个命中单位的下标**（原生循环命中即 `break`，顺序会影响
结果），不是集合。带闸与不带闸的对比同时证明：`units` 计数闸**不是装饰**——
去掉它，建表后新生成的单位当帧不可被命中。

## 4. 成本（离线，900 帧，40 弹 × 130 单位）

`bench-run.txt`（机器空闲时的最后一轮；括号内为另两轮范围）：

| 路径 | ms / 900 帧 | 折算 ms/帧 |
|---|---:|---:|
| 原生全量扫描 | 601（591–636） | 0.67（0.66–0.71） |
| 原生全量扫描 + 每弹 #1069 抛/捕 | **1,204**（1,011–1,176） | **1.34**（1.12–1.31） |
| 分桶（建表 + 查询） | **420**（428–439） | **0.47**（0.48） |
| 仅建表 | 256 | 0.28 |
| 仅异常抛/捕（每帧 40 次） | 521（390–830） | 0.58（0.43–0.92） |

读法：
- **异常本身**在 AVM2 上每次 10–23µs，40 弹/帧就是 0.43–0.92ms/帧——这是当前线上
  纯粹白烧的钱，且**与敌人类型无关**。
- 去掉异常后（= `scu-remove` 候选）剩下全量扫描 0.67ms/帧。
- 再换成按位查桶，总成本 0.47ms/帧（含建表 0.28）。相对当前线上
  **1.34 → 0.47，−65%**；相对「只删异常」**0.67 → 0.47，−30%**。
- 离线是纯合成数组访问；真实 `Unit` 每轮要读 9 个属性
  (`sost/disabled/trigDis/loc/fraction/X1..Y2`)，全量扫描一侧更贵，所以真实差距
  只会比这张表大、不会更小【推断，未在游戏内单独计量】。

## 5. 候选产物

| tag | 改动方法 | SHA256 | 说明 |
|---|---|---|---|
| `grid-diag` | 7 个相位诊断 + `sceneTick` + `Bullet.run` | `C2012FA3…` | 诊断面（本轮实测**不可用于配对**，见 §6.4） |
| `grid-clean` | `sceneTick` + `Bullet.run` | `91F8E10D…` | **已部署产物** |
| `scu-remove-clean` | `sceneTick` + `Bullet.run`（仅删通道） | `BAA22A81…` | 回退档：只删异常不带分桶 |

三者 `compiled=true`、`classesUnchanged=true`。
探针：`build/generated/phase-20261104/probe-v6`（`81E7738F…`）= probe-v5 + 逐帧
`row.grid{active,stamp,gx,gy,units,bucket,dense,max,error}`；对无诊断宿主也做了
`chunkDiagnostics` 空值保护。

## 6. 游戏内

### 6.1 已完成的运行（`game` 独占登记、独立 AIR ID / 私有存储、静音、2048×1123、6 敌交战）

| 证据目录 | 宿主 | 探针 | 结果 |
|---|---|---|---|
| `bulletgrid-cleansmoke-combat-n1` | `grid-clean` `91F8E10D` | probe-v5 | ok，1300 样本，13 项检查通过，无错误 |
| `bulletgrid-baseclean-combat-n1` | `decal-nocancel-clean` = 线上 `1D2004AB` | probe-v5 | ok，1300 样本，13 项检查通过，无错误 |
| `bulletgrid-gridlive-combat-n1` | `grid-clean` `91F8E10D` | probe-v6 | ok，1300 样本，13 项检查通过，无错误 |

### 6.2 分桶在真实游戏里确实生效（probe-v6 逐帧读数）

| 指标 | 值 |
|---|---|
| `grid.active` | **1300 / 1300 帧** |
| `grid.error` | `null`（没有 #1056 / #1069） |
| `loc.units` 平均 | **122.0** 只 |
| 视口处一格候选数 | 均值 **2.71**、P95 5、最大 5 |
| 全表分量（单位×覆盖格数） | 均值 287.7（≈122 × 2.4，外扩 96px 的预期） |

即：**一发子弹要检查的单位从 ~122 只降到 ~3 只（约 45×）**，而且没有异常。

### 6.3 整帧对照（同为 clean 宿主 + 同一探针 v5，各 1299 个完整间隔）

| 指标 | 线上 1D2004AB | grid-clean | 差 |
|---|---:|---:|---:|
| 均值 | 49.89 ms | 49.29 ms | **−0.60 ms (−1.2%)** |
| P50 | 47 | 47 | 0 |
| P95 | 73 | 69 | −4 |
| 最大 | 225 | 305 | 系统级尖峰 |
| >100ms 帧 | 16 | 18 | 噪声 |
| 在飞弹数均值 | 3.44 | 4.45 | 候选臂**更多弹** |

第三轮（候选 + probe-v6，18:48）均值 **46.93**，相对同一控制臂 **−2.96 ms (−5.9%)**、
P95 73→65、max 225→152、>100ms 16→12——但那一臂探针自身更重，且有约 12 分钟负载漂移。

**判定口径**：两臂同向为负（−0.6 与 −3.0 ms），与离线机制量级（−0.5~−0.8 ms）同号；
但机器负载波动大于该差值的可分辨范围，**只主张「没有退化」与机制量，不主张整帧收益**。
三次运行 `projectileMax` 9–17，说明碰撞路径确实被真实弹道走到。

### 6.4 与 CS 0.9.9 瞄准平移路径的互操作（部署后验证）

0.9.9 的 `apply()` 在平移后会**再调一次** `w.grafon.sceneTick()`，也就是说平移期间分桶表每帧会被重建两次。
用 0.9.9 自己的实机夹具 `build/generated/aimv2-20261104/driver`（`AimProbe`，会真的按 Alt 平移并断言）
对**已部署的字节**（`91F8E10D`）跑一遍（`build/generated/combat-collision-20261104/run_live_grid.py`，
输入换成部署字节、CS 仍是 0.9.9 `D04CD26A`）：

```
CHECK viewport-resynced ok=1 syncs 208
CHECK panned-view-resident ok=1 resident 110 before 70
CHECK world-map-exact ok=1 bad 0
CHECK apply-consistent ok=1 bad 0
CHECK pan-engaged ok=1 maxPan 616.8 reason aiming
CHECK release-zero ok=1 off 0,0
CHECK stats-applied ok=1 applied 239
RESULT PASS checks=14 reason=complete
```

即：**平移路径 14/14 通过**，444 帧里 239 次额外 `sceneTick` 都正常重算（`resident 70→110`、
世界映射与渲染恒等式零违例），分桶表在第二次调用里重建不影响任何已断言行为。

### 6.5 同毫秒去重（已建候选，**不部署**）

一度想加"同一毫秒内不重复建表"的闸（`getTimer()` 相等就跳过），以减少平移期间的第二次建表。
两个候选已构建：`grid-probe` `1D415967`（带 skip/build 计数）、`grid-clean-guard` `6E3BC782`（纯净版）。
**判定不部署**：0.9.9 的第二次 `sceneTick` 发生在模组 ENTER_FRAME 里，而模组帧代码**永远晚于游戏 step**
（`shared-knowledge/.../modding-interop.md`），两次调用的间隔是毫秒级到几十毫秒，`getTimer()` 同毫秒几乎不成立；
改动换来的是"绝大多数情况下不生效"，不满足本仓"可测收益才动宿主"的门槛。两个候选保留、`deployed=false`。

### 6.6 过程中的两个坑（都已排除，记录备查）

- `decal-nocancel-v2`（`BD8F90FA`，7 方法相位诊断构建，连 `sceneEnsureUpcoming` 都插桩）
  **两次跑挂**（10 分钟超时、无 result.json），而同一探针在 clean 宿主上 3 次全过。
  该诊断宿主**不可再用于配对**；本轮控制臂改用真正线上字节 `decal-nocancel-clean`
  （`1D2004AB`），反而更严谨。
- 第一次构建 probe-v6 时把入口文件写成 `ContinuousSceneMotionMod.as`，SWF 文档类不是
  Sprite，游戏报 `TypeError #2023: … must inherit from Sprite to link to the root`；
  入口必须是 `ProbeDoc.as`。

> **证据目录损失（2026-11-04 21:05 发现）**：`knowledge/experiments/evidence/` 整个目录在
> 19:12 之后被外部清理删除（789 个已跟踪文件 + 本轮未跟踪的 `bulletgrid-*` /
> `installed-smoke-*` 原始 `result.json`）。已跟踪部分用 `git checkout -- knowledge/experiments/evidence`
> 全量恢复（恢复后 73 个目录、0 个删除）；**本轮那几份未跟踪的原始运行目录无法从 git 找回**，
> 但汇总数字已写进 §6，且全部可用 §9 的命令原样重跑（夹具、探针、运行器、分析器都在仓库里）。
> 见 `state/bullet-grid-20261104.md` 的记录。

## 7. 部署（GOVERNANCE §6）

| 项 | 值 |
|---|---|
| 产物 | `grid-clean` `91F8E10D…3CB45` |
| 前值 | 根 `pfe.swf` `1D2004AB…AB02F3` |
| 备份 | `build/backups/pfe_before_bulletgrid_20261104-185052.swf`（= 1D2004AB） |
| 回执 | `build/generated/combat-collision-20261104/deploy-receipt-grid-clean.json` |
| 读回 | `pfe.swf` SHA = `91F8E10D…` ✔ |
| 回滚 | 用备份覆盖根 `pfe.swf` 并重启游戏 |
| 生效 | **需重启游戏** |
| 未动 | CS 0.9.9 `D04CD26A`、`scene.xml` `1CEA74E2`、其它模组 |

**装后冒烟（装的字节本身）**：`knowledge/experiments/evidence/installed-smoke-pfe-bulletgrid-smoke-20261104191330/InstalledSmoke.json`
——独立 app id、隐藏窗口、真 `pfe.swf` + 真 13 模组清单：`startup-heartbeat-and-loader-ok`、
`no-loader-errors`、`scene-loaded-and-heartbeat`（日志 `v0.9.9 loaded`）、`process-alive`、
`no-uncaught-error` **5/5 通过**，`errorLines` 为空。

## 8. 按既有证据不实施的方案条目

| 方案条目 | 处置 | 依据 |
|---|---|---|
| C2 唤醒信号强弱分级 | **不做** | `alicorn4-alicorn-n1`（900 帧、14/14）：一次交战把「带目标单位」1→9，但唤醒仍按每帧 1 只预算走、`awake` 28–43、整场帧时无抬升（前/后 100 帧 34.5/34.9ms），仅高活跃帧 +4.9ms。现状 `wakeBudget=1` + 2200×1600 leash 已把这条链压住；改成「弱信号」有把真交战单位判错的风险。 |
| C3 拴绳双阈值迟滞 | **不做** | 同上：没有测到跨边界振荡的帧时证据，改判据属于无证据调整。 |
| E1 视口前馈缓冲（多预热） | **不做（反向）** | `long-frame-memory-20261104`：≥100ms 帧的 85–100% 与一次 >1MB 内存回落同帧，回落由**大地块分配**推动（约 18MB/s）。加大前馈 = 加大分配 = 更快触发回收，方向相反。 |
| E2 `drawKusok` 增量切分 | **不做** | 2026-11-04 相位实测 `maxStepMs` 仅 20–25ms（125ms 是冷态单次 outlier），当前形态不构成 >100ms 主因。 |
| E3 远处逐出 + 复用 | **不做** | 2026-11-04 已实测负结果：cap=96 时均值略好但**最大帧 171→568ms**、同步补画 22→30 次（相机跳变那帧要补所有被逐缺口）。 |

## 9. 复跑

```powershell
$py = "C:\Users\hello\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
# 候选（每个约 4–8 分钟，FFDec 7 次调用）
& $py mods\ContinuousScene\build\generated\combat-collision-20261104\patch_bullet.py grid-clean grid-clean
& $py mods\ContinuousScene\build\generated\combat-collision-20261104\patch_bullet.py scu-remove-clean scu-remove-clean
# 离线等价 + 成本（无头，约 30 秒）
& $py mods\ContinuousScene\build\generated\combat-collision-20261104\build_probe_v6.py probe-v6   # 若需重建探针
.\adl64.exe -runtime runtimes\air\win64 mods\ContinuousScene\build\generated\combat-collision-20261104\app-debug.xml
# 单臂游戏内运行（host 目录 + 探针 + 标签）
$env:PHASE_HOST_DIR="...\combat-collision-20261104\grid-clean"; $env:PHASE_PROBE="probe-v6"; $env:PHASE_LABEL="bulletgrid-gridlive"
& $py mods\ContinuousScene\build\generated\phase-20261104\run_phase2.py combat 2
& $py mods\ContinuousScene\build\generated\combat-collision-20261104\analyze_grid.py `
   bulletgrid-baseclean-combat-n1 bulletgrid-gridlive-combat-n1
# 部署 / 回滚
& $py mods\ContinuousScene\build\generated\combat-collision-20261104\deploy_bulletgrid.py grid-clean
```

## 10. 边界

- 分桶按**子弹当前点**查格，与原版一致（原版也只看当前帧位置，不是扫掠段）；
  因此高速弹穿透单位这一原生缺陷**既没被修好、也没被改坏**。
- 单位在同一帧内瞬移（天角兽 `actPort` 类）后到下一帧建表前，理论上有 1 帧窗口
  仍按旧格命中——概率极低（33ms 内），且方向是「可能漏一发」，与「错伤多目标」
  相反。玩家大幅位移（>256px）已有闸回落到全量扫描。
- 离线成本是合成夹具，不是游戏内读数；游戏内不做「绝对帧时收益」主张。
- **已知交互（未改，留作后续）**：CS 0.9.9 的瞄准平移会在 `apply()` 后**再调一次** `w.grafon.sceneTick()`，
  因此平移期间每帧可能建两次分桶表（多约 0.3ms/帧）。因为查询侧省的是 0.5–1.3ms/帧，
  净收益仍为正；若要抹平，可在建表前用 `getTimer()` 判断同帧（同一毫秒）已建过就跳过。
- 本轮**没有**处理探索侧的同步补画/地块分配链：那里的证据指向原生渲染与
  大地块内存回收，加缓冲只会加大分配（见 §8 E1）。
