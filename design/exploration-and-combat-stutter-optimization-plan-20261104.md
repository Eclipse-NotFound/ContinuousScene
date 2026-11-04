# ContinuousScene 深入探索与全敌人交战卡顿调查及可执行优化方案（2026-11-04）

> **文档标识**：`mods/ContinuousScene/design/exploration-and-combat-stutter-optimization-plan-20261104.md`  
> **编制依据**：基于 2026-11-01 至 2026-11-04 全量真机时序采样、相位归因探针（`phase-v3/probe-v5`）、反编译源码审查及多次 A/B 隔离测试实测数据。  
> **当前工程基线**：
> - 根目录宿主 `pfe.swf`：**`1D2004AB`**（2026-11-04 13:36 部署“弹痕不取消预热”）；
> - 模组版本：**CS 0.9.8 `285625F4`**（含 Aim-Look 瞄准平移、事件驱动增量剔除 `0.9.7`、脱战拴绳 `0.9.6`、分帧平滑唤醒 `0.9.4`）；
> - 场景配置：`scene.xml` **`1CEA74E2`**。

> **实施状态（2026-11-04 晚补记）**：本轮按本方案实施 **C1（子弹碰撞）** 一项，其余条目按本仓既有实测证据判为不实施，逐条理由与证据指针见
> [knowledge/experiments/bullet-collision-20261104.md](../knowledge/experiments/bullet-collision-20261104.md) §7。
> - **C1 已实现并部署**：宿主 `Grafon.sceneTick` 改为每帧建整房间 512px 分桶表（存 `World.w.vgui["__csBulletGridV1"]`；`Sprite` 是密封类、`MovieClip` 才是 dynamic，这一条由无头探针实测挡下一次 `#1056` 事故），`Bullet.run` 去掉 `sceneCU` 反射通道并按子弹坐标查桶；带三道回落闸（targetObj / 单位数变动 / 玩家位移 >256px）。产物 `grid-clean` **`91F8E10D…`**（类布局不变，仅 `fe.graph.Grafon::sceneTick` + `fe.weapon.Bullet::run`），已装根 `pfe.swf`（前值 `1D2004AB`，需重启）。
> - **C1 证据**：离线等价 16,009 个探针点 0 不一致（含跨格、超大/退化盒、一帧陈旧 ±96px、建表后新生成单位）；离线成本（40 弹 × 130 单位、900 帧）从「全量扫描 + 每弹异常」1.34ms/帧 降到「建表 + 查桶」0.47ms/帧（−65%），其中异常本身占 0.43–0.92ms/帧；游戏内 3 次 1300 样本/13 检查全过，分桶 1300/1300 帧生效、单位 122 → 候选 2.7，clean↔clean 对照均值 −0.60ms（不主张整帧收益）。
> - **不实施**：C2/C3 由 `alicorn4-alicorn-n1` 计数证据关闭（唤醒已按每帧 1 只预算、整场帧时无抬升）；E1 与「长帧 85–100% 与 >1MB 内存回落同帧、回收由大地块分配推动」的方向相反；E2 由 `maxStepMs` 仅 20–25ms 的实测关闭；E3 已实测负结果（最大帧 171→568ms）。

---

## 0. 执行摘要与核心诊断结论

针对用户反馈的 **“深入探索过程中仍容易偶发卡顿”** 与 **“与敌人交战（各敌人类型都有）时容易出现卡顿”** 两个核心痛点，经过对游戏宿主执行链路、模组调度、渲染管线及多轮真机相位归因的深入排查，得出以下核心诊断：

1. **深入探索卡顿的真正元凶**：
   - **长帧主体不在日常 CS 调度（仅占 ~13.6%），而在偶发性大阻塞**。2026-11-04 最新 1149 帧相位归因证明：常态 CS 管线耗时约 5.67ms/帧。但在 ≥100ms 的严重长帧中，原生渲染与调度窗口（R 桶）占 **61%**，CS 仅占 21%。
   - 造成探索中突发 100ms+ 卡顿的根因是两处硬阻塞：
     - **视口 Miss 触发的强制同步补画（Sync Render）**：探索移动或开启 Aim-Look 瞄准快速拉动视角时，一旦视口越出预热缓冲区，`Grafon.sceneEnsureUpcoming` 被迫在单帧内**同步阻塞渲染整块**，单次耗时达 **31–178ms（均值 68ms，峰值 296ms）**，直接打崩当前帧；
     - **掩码地块单步不可中断（`drawKusok`）**：单步内部创建 6 个 Sprite + 588 个掩码子节点，冷态单步耗时峰值高达 **125ms**（占 ≥8ms 单步的 94%）；
     - **地块常驻无逐出导致的堆膨胀与 GC 停顿**：探索 38 秒驻留地块由 47 飙升至 181 块（+343MB 位图内存），全图上限达 1.2GB，持续将 AIR 堆压向临界区，引发系统级底层换页与垃圾回收停顿。

2. **全敌人类型交战卡顿的真正元凶**：
   - **子弹空间碰撞优化彻底失效并伴随“异常轰炸”**：
     此前宿主补丁试图通过 `World.w.visual.root["sceneCU"]` 传递视口内单位以减少子弹碰撞遍历。然而运行时 `root` 是密封类 `fe.MainFE`（非 dynamic class），**每颗子弹每帧读取该属性均抛出 `#1069` ReferenceError 异常**！
     当交火时 30~60 颗子弹在场，**每帧引发 30~60 次 AVM2 异常抛出与捕获**，随后被迫回退到全图 `loc.units`（130+ 单位）进行 **O(n²) 纯暴力 AABB 碰撞遍历**（每帧 3900~7800 次相交测试），仅碰撞计算就消耗 **+1.5~2.0ms/敌人**；
   - **`NativeSceneActivity` 索敌唤醒风暴**：
     任何敌人在获得目标玩家（`celUnit != null`）或受到警报广播时，`combatSignal` 与 `urgent` 标志被无条件置为 true，**直接击穿 `wakeBudget` 分帧分批唤醒防线**！方圆 2200×1600 范围内的所有同阵营敌人（即便隔着多层坚壁、处于屏幕远端）在同 1 帧内被成批强行唤醒（`resume`）。每个被拉活的敌人每帧带来原生物理（`step`）、骨骼动画（`gotoAndStop`）及 DDA 穿墙射线检测（`isLine`）的刚性消耗，瞬间将整帧耗时从 33ms 推高至 50~60ms 以上；
   - **脱战拴绳在边界处的剧烈休眠/唤醒振荡**：
     玩家与敌群在 2200×1600 边界拉扯时，缺乏缓冲迟滞，敌人频繁跨线触发冻结（递归遍历整棵显示树）与解冻，形成周期性卡顿脉冲。

---

## 1. 详细调查过程与事实核验

### 1.1 深入探索过程中的偶发卡顿分析

#### （1）探索阶段的帧时三分归因（2026-11-04 真实大场景 1149 帧实测）
通过在宿主 `Camera.calc → Grafon.sceneTick` 内部打入微秒级相位探针（`phase-v3` + `probe-v5`），实测探索过程中的耗时构成：

| 相位分类 | 总耗时 | 平均每帧 | 占比 | 长帧贡献（≥100ms 帧） |
|---|---|---|---|---|
| **CS 模组管线**（预热/同步/剔除/弹痕） | 6,515 ms | 5.67 ms | 13.6% | **20.6%**（340 ms / 1648 ms） |
| **原生渲染与调度窗口（R 桶）** | 25,025 ms | 21.78 ms | 52.1% | **60.5%** |
| **原生游戏逻辑与物理步进** | 16,521 ms | 14.37 ms | 34.4% | **18.9%** |
| **整帧合计（dtMs）** | 48,061 ms | 41.82 ms | 100% | 100%（共 13 个长帧） |

**关键结论**：
1. 模组的日常预热稳态耗时仅 **2~5ms/帧**（由自适应预算 `sceneWarmBudget` 动态控制在 2~25ms 内），平时并不卡；
2. 长帧发生时，CS 管线只有少量尖峰（峰值 80~90ms），其余 **80% 的时间被阻塞在原生软光栅渲染、主线程同步和系统调度中**。

#### （2）探索卡顿的三大机制源

1. **机制 A：视口 Miss 触发的强制同步阻塞补画（Sync Render）**
   - **代码路径**：`fe.graph.Grafon.as:2414-2425, 725-797`
   - **运行机制**：当玩家行进速度较快或使用 Aim-Look 快速横移视野（最大可偏移 700px）时，镜头边缘掠过尚未预热的新区块。`sceneEnsureUpcoming` 检测到当前视口内缺少地块位图，判定为 miss：
     - 若该块正在后台分步预热，则调用 `sceneAdvanceWarm(true)` 强行在单帧内执行完所有剩余步骤；
     - 若该块尚未开始预热，则调用 `sceneRender(x, y)` 强制进行全量不可中断同步渲染。
   - **量级实测**：单次同步整块补画耗时 **31–178ms，均值 68ms**。在 `cold-r3` 记录中，自然探索中的 29 次同步补画，直接产生了对应的剧烈卡顿。

2. **机制 B：地块单步掩码构建（`drawKusok`）**
   - **代码路径**：`fe.graph.Grafon.as:4136-4294`
   - **运行机制**：预热设计了分步调度器 `sceneAdvanceWarm`，按步执行 `sceneDrawSteps`（共 25 个 step）。但在 step 内部是原子不可中断的。
   - `drawKusok` 负责处理边缘地块与转角，内部实例化 6 个 Sprite，遍历生成约 588 个掩码子节点，挂载 `cacheAsBitmap` 和材质滤镜后执行 `draw`。
   - **量级实测**：冷态下单步峰值耗时高达 **125ms**，在所有耗时 ≥8ms 的慢步中，**94% 为 `drawKusok`**。

3. **机制 C：常驻地块无淘汰（No Eviction）引发的内存激增**
   - **代码路径**：`fe.graph.Grafon.as:510-534`
   - **运行机制**：`sceneDrop` 仅在切换地图和暖图验证时被调用，大场景探索中对走过的区块**完全不释放**。每个 320px 逻辑块包含 4 层 400×400×4 字节位图（约 2.56MB）。
   - **量级实测**：探索 38 秒内，驻留块由 47 块猛增至 181 块（内存净增 **+343MB**）；在 9600×5000 的大地图中，全图 480 个地块常驻将占用 **~1.2GB 显存/内存**。高内存水位直接迫使 Windows 系统和 AIR 虚拟机进行频繁内存整理，诱发随机性的系统级大顿挫。

#### （3）已被实测证伪/停止的探索优化方向
- **压低 `sceneWarmBudget`（如压到 2~12ms）**：实测自适应预算本就只有 2~25ms，强行压低预算会导致预热严重滞后于镜头移动，**诱发更多 31~178ms 的同步补画，适得其反**；
- **简单粗暴的地块 Cap 强制逐出（实测负结果不部署）**：2026-11-04 针对 `cap=96` 的实测表明，简单的距离逐出虽然使均值从 41.8 降到 39.9ms，但在镜头跳变/折返时**引发同步补块风暴**，最大长帧恶化至 **568ms**（单帧同步补画 25 个缺口），直接否定单纯的丢块逐出；若要控制内存，必须依赖带占位降级的平滑调度；
- **地块 BitmapData 对象池**：减小短寿命分配无法改变地块需要长期驻留的事实，四次严格配对实测证明“减分配≠减帧时”；
- **弹痕待应用缓冲（Pending Marks）**：因果分析证明 29 次同步补画中与弹痕取消同块的次数为 0，且 2026-11-04 已部署 P2 补丁（`decal` 不再取消预热），该问题已在源头解决。

---

### 1.2 与敌人交战过程中的卡顿分析（全敌人类型通用）

#### （1）子弹碰撞检测的致命缺陷：异常抛出轰炸 + O(n²) 暴力计算

1. **宿主补丁中的动态属性异常陷阱**：
   - 宿主 `fe.graph.Grafon.as:486-497` 试图在每帧将视口内的单位写入 `World.w.visual.root["sceneCU"]`：
     ```actionscript
     try { World.w.visual.root["sceneCU"] = cu; } catch(cuErr:Error) {}
     ```
   - 子弹碰撞逻辑 `fe.weapon.Bullet.as:503-509` 试图从该属性读取：
     ```actionscript
     var _collisionUnits:Array = loc.units;
     try {
        if(World.w != null && World.w.visual != null && World.w.visual.root != null) {
           var _cuList:* = World.w.visual.root["sceneCU"];
           if(_cuList is Array && _cuList.length > 0) _collisionUnits = _cuList;
        }
     } catch(_cuError:Error) {}
     ```
2. **严重缺陷实锤**：
   - 运行时 `World.w.visual.root` 的实际类型是 `fe.MainFE`；
   - `fe.MainFE` 是**密封类（Sealed Class，非 dynamic）**；
   - 在 ActionScript 3 (AVM2) 虚拟机规范中，对密封类实例访问未声明的动态属性，**虚拟机必定抛出 `ReferenceError: Error #1069` 运行时异常**！
   - **后果一：全量异常轰炸**。交战中若有 40 发子弹同时在场，每帧虚拟机都要连续构造并捕获 40 次带有调用栈上下文的异常对象，产生严重的 CPU 停顿；
   - **后果二：空间优化完全失效**。`_collisionUnits` 永远在 catch 块中保持为全图所有单位（`loc.units`，连续场景中常达 130+ 个）。
3. **碰撞计算的超线性爆炸**：
   - 40 发子弹 × 130 个单位 = **每帧 5,200 次 AABB 矩形碰撞检测**；
   - 叠加子弹穿透检查、`isLine` 墙壁检测及命中特效触发，实测 12 敌交火时帧时从 33.4ms 暴增至 **56.8ms（+23.4ms）**，每敌人稳定贡献 **+1.5~2.0ms/帧** 的巨额负担！

#### （2）`NativeSceneActivity` 索敌唤醒风暴（目标广播穿透）

1. **唤醒判断逻辑缺陷**（`src/NativeSceneActivity.as:49-57, 91-96`）：
   ```actionscript
   // 只要单位拥有目标（即使是同阵营广播获得），或有扣血/流血
   var combatSignal:Boolean = u.hp < r.hp || u.celUnit != null || u.cut > 0 || u.poison > 0;
   if(combatSignal) { r.engaged = true; r.deadline = s.tick + disengageTicks; r.leashed = false; }
   ...
   // urgent 判断直接包含 combatSignal 与 r.engaged
   var urgent:Boolean = ... || combatSignal || r.engaged ...;
   if(urgent) { resume(r); delete s.sleeping[u]; ++s.awake; }
   ```
2. **连锁拉活反应**：
   - 当玩家与任何一只敌人（如天角兽、突袭者、飞马）交火并产生警报时，首发敌人会向同一大房间（1920×1000 范围）内的同阵营单位广播玩家坐标，将周围敌人的 `celUnit` 强行设为玩家；
   - 一旦 `celUnit != null`，`NativeSceneActivity` 立即判定 `combatSignal = true` 且 `urgent = true`；
   - **`urgent` 绕过了所有 `wakeBudget`（每帧仅唤醒 1 个的分帧平滑预算）**，导致方圆 2200×1600 内的所有敌人**在同 1 帧内被成批同时唤醒**！
3. **活跃敌人的每帧沉重负担**：
   - 每个处于 `awake` 状态的敌人：
     - 原生物理步进 `step()` 计算移动与碰撞；
     - 动画驱动 `vis.gotoAndStop` 更新肢体动画骨骼，导致 AIR 显示列表节点不断脏化；
     - AI 寻路高频发起 DDA 穿墙射线检测 `isLine`；
   - 瞬间唤醒 6~12 个敌人，直接向当前帧砸入 **10~24ms** 的净开销，造成交战瞬间的断崖式掉帧。

#### （3）脱战拴绳（Leash）边界处的休眠/唤醒振荡
- 当前脱战判定使用 `Math.abs(u.X - loc.gg.X) < 2200 && Math.abs(u.Y - loc.gg.Y) < 1600`；
- 当玩家在风筝敌人拉扯时，敌人在 2200px 临界线边缘来回穿梭；
- 每次跨入边界外倒计时归零即休眠（调用 `freeze` 递归遍历整棵 DisplayObject 树），跨入边界内又因 `celUnit` 再次被强行唤醒（调用 `resume`）；
- 缺乏**迟滞区间（Hysteresis）**，导致频繁的树遍历开销与状态抖动。

---

## 2. 整体优化方案架构与核心改动

本方案分为两大支柱：**支柱 E（深入探索平滑化）** 与 **支柱 C（全敌人交战高效化）**。

```
┌────────────────────────────────────────────────────────────────────────┐
│                   ContinuousScene 全场景流畅度优化体系                    │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
     【支柱 E: 深入探索平滑化】               【支柱 C: 全敌人交战高效化】
                    │                                │
  ┌─────────────────┴───────────────┐  ┌─────────────┴─────────────────┐
  │ E1. 动态自适应视口缓冲 (Aim-Look) │  │ C1. 真正空间分区的子弹碰撞系统  │
  │     消除高速移动/瞄准的同步补画 │  │     根除 #1069 异常, O(N)→O(1)│
  ├─────────────────────────────────┤  ├───────────────────────────────┤
  │ E2. drawKusok 掩码分步增量切分  │  │ C2. 敌人唤醒信号分级与预算控制 │
  │     125ms 峰值单步削平至 ≤25ms  │  │     弱信号走预算, 阻断拉活风暴│
  ├─────────────────────────────────┤  ├───────────────────────────────┤
  │ E3. 远处驻留地块 LRU 智能逐出   │  │ C3. 脱战拴绳双阈值迟滞防抖    │
  │     驻留限制 ≤64 块, 降 GC 水位 │  │     消除风筝时的休眠/唤醒振荡 │
  └─────────────────────────────────┘  └───────────────────────────────┘
```

---

## 3. 具体实施方案（分模块详细设计）

### 3.1 支柱 C：全敌人交战高效化方案

#### C1. 修复子弹空间碰撞体系（True Spatial Partition for Bullets）
- **核心目标**：彻底消除 `#1069` 运行时异常；建立真正按子弹空间位置检索的高性能网格，将碰撞检查从 O(n) 降至 O(1)。
- **改动位置**：
  1. **宿主层 `fe.graph.Grafon.as`**：
     - 在 `Grafon` 类中正式声明类型化公共字段：`public var sceneSpatialGrid:Object;`（或声明在全局适配器中，**坚决不写非 dynamic 对象的动态属性**）；
     - `sceneTick` 中构建 640×640 像素的轻量空间分桶（Spatial Hash Grid）：
       ```actionscript
       // 以 640px 为单元格，遍历 loc.units 归入桶中（仅存单位引用，零对象包装）
       var grid:Object = {};
       for each(var u:* in this.loc.units) {
           if(u == null || u.sost == 4 || u.disabled) continue;
           var minGx:int = int(u.X1) >> 9; // 512px 或 640px 快速位移分桶
           var maxGx:int = int(u.X2) >> 9;
           var minGy:int = int(u.Y1) >> 9;
           var maxGy:int = int(u.Y2) >> 9;
           for(var gx:int = minGx; gx <= maxGx; ++gx) {
               for(var gy:int = minGy; gy <= maxGy; ++gy) {
                   var key:int = (gx << 16) | (gy & 0xFFFF);
                   if(grid[key] == null) grid[key] = [];
                   grid[key].push(u);
               }
           }
       }
       this.sceneSpatialGrid = grid;
       ```
  2. **宿主层 `fe.weapon.Bullet.as:503-509`**：
     - 彻底删除对 `World.w.visual.root["sceneCU"]` 的反射调用与 try-catch 结构；
     - 改为直接通过类型化字段读取空间网格：
       ```actionscript
       var _collisionUnits:Array = null;
       var grafon:* = World.w ? World.w.grafon : null;
       if(grafon && grafon.sceneSpatialGrid) {
           var bKey:int = (int(this.X) >> 9 << 16) | (int(this.Y) >> 9 & 0xFFFF);
           _collisionUnits = grafon.sceneSpatialGrid[bKey];
       }
       // 兜底回退：若不在网格内或非大场景，安全使用 loc.units
       if(_collisionUnits == null) _collisionUnits = loc.units;
       ```
- **预期收益**：
  - 消除每帧 30~60 次 `#1069` 异常抛出与调用栈回溯开销；
  - 碰撞判定对象从 130+ 缩减至当前分桶内的 **2~6 个**，碰撞测试量下降 **90% 以上**；
  - 完美支持屏幕外自然弹道碰撞（按子弹实际坐标查桶，彻底解除对视口的错误依赖）。

#### C2. 敌人唤醒信号分级与预算平滑（Activity Signal Tiering）
- **核心目标**：阻断由目标广播触发的同阵营敌人“同帧集体拉活”风暴。
- **改动位置**：模组层 `src/NativeSceneActivity.as:49-105`（纯模组层，零宿主风险）。
- **具体设计**：
  1. 将战斗信号严格分级为 **强战斗信号（Strong Signal）** 与 **弱战斗信号（Weak Signal）**：
     - **强信号（必须即时唤醒，零延迟）**：
       - 受到实际伤害（`u.hp < r.hp`）；
       - 处于负面状态（`u.cut > 0 || u.poison > 0 || u.stun > 0 || u.bind != null`）；
       - 处于正在攻击/受击硬直中（`u.sost != 1`）；
       - 正处于直飞弹道的直接危险走廊中（`threatened == true`）。
     - **弱信号（允许平滑排队，受预算调度控制）**：
       - 仅拥有目标但未进入交火（`u.celUnit != null`，来自同伴警报共享）；
       - 处于弹道警报扩散光环外圈（`alerted == true`）；
       - 玩家视野靠近边缘（`proximity == true`）。
  2. 调度执行调整：
     - 弱信号仅刷新活跃期限 `r.until = s.tick + 45`，但**不置 `urgent = true`**，且**不赋予无限期的 `r.engaged`**；
     - 弱信号休眠单位进入 `deferred` 队列，按离玩家距离排序，由 `wakeBudget`（默认每帧 1~2 个）按帧顺序平滑唤醒。
- **预期收益**：
  - 彻底瓦解开战首帧 6~12 个敌人同时唤醒的 15~25ms 瞬时阻塞峰值，将其平摊到 4~8 帧中平滑过渡；
  - 玩家战斗交火感知完全不受影响（正在向玩家射击或挨打的敌人依旧 0 延迟即时反应）。

#### C3. 脱战拴绳双阈值迟滞防抖（Leash Hysteresis）
- **核心目标**：消除在追击边界来回走动时的冻结/解冻振荡。
- **改动位置**：模组层 `src/NativeSceneActivity.as:55-57`。
- **具体设计**：
  - 引入双阈值区间：
    - **脱战外边界**：超出 `2400 × 1800` 且持续 150 帧无强战斗信号，方可判定脱战休眠；
    - **重新接战内边界**：休眠中的敌人必须靠近至 `1900 × 1300` 或受到强攻击信号，才会重新激活追击；
  - 500px 的迟滞死区（Deadband）彻底消除玩家风筝拉扯时的边界状态反复震荡。

---

### 3.2 支柱 E：深入探索平滑化方案

#### E1. 动态自适应视口缓冲（Aim-Look & Motion Dynamic Buffer）
- **核心目标**：杜绝因探索移动或 Aim-Look 瞄准视野平移导致的视口越界，将视口 miss 触发的同步大补画彻底降为 0。
- **改动位置**：模组层与宿主预热层联动（`Grafon.as:484` 与 `SceneAimController.as`）。
- **具体设计**：
  - 在 `Grafon.sceneEnsureUpcoming` 中，既有的预热矩形只考虑当前摄像机坐标与固定边距；
  - 将 `SceneAimController` 暴露的当前瞄准偏移速度（`aimOffsetX, aimOffsetY`）以及摄像机运动速度矢量注入预热边界计算：
    ```actionscript
    // 动态前馈预测：沿运动与瞄准方向增加 1~2 个区块的额外前馈预热宽度
    var forwardX:Number = (c.vx - c.lastVx) * 10 + aimController.targetShiftX;
    var forwardY:Number = (c.vy - c.lastVy) * 10 + aimController.targetShiftY;
    var preWarmLeft:Number = viewLeft + (forwardX < 0 ? forwardX - 320 : -160);
    var preWarmRight:Number = viewRight + (forwardX > 0 ? forwardX + 320 : 160);
    ```
- **预期收益**：
  - 预热管线始终先于玩家视野一步完成位图准备；
  - 探索移动与按住 Alt 快速索敌横扫时的 **视口 Miss 次数归零**，消除 31–178ms 的突发同步卡顿。

#### E2. `drawKusok` 掩码分步增量切分（Slicing Kusok Construction）
- **核心目标**：将 125ms 的地块单步最大峰值削平至 ≤25ms。
- **改动位置**：宿主 `fe.graph.Grafon.as:4136-4294`（`drawKusok`）。
- **具体设计**：
  - 目前 `drawKusok` 内部在单个 step 内一次性执行 588 个掩码子节点的循环构建；
  - 将该循环拆分为可重入的分批状态机（如每次处理 48 个格点），在 `sceneAdvanceWarm` 的 step 循环中允许中途返回 `false`（让出时间片给下一帧继续），仅在所有掩码节点就绪后再执行终末的 `cacheAsBitmap` 与位图绘制；
  - 中间状态由当前正在预热的 `job` 持有，一旦遭遇 `sceneCancelWarm` 可安全随 job 一并释放。
- **预期收益**：
  - 地块预热的总时间保持不变，但**最大单步耗时从 125ms 压制在 20~25ms 以内**，不再击穿 33.3ms 帧预算。

#### E3. 远处驻留地块 LRU 智能逐出（Distance-based Block Eviction）
- **核心目标**：控制大地图驻留地块上限，将地块内存占用锁定在安全水位，消除堆膨胀引起的系统顿挫。
- **改动位置**：宿主 `fe.graph.Grafon.as:510-534`（`sceneDrop`）。
- **具体设计**：
  - 引入轻量 LRU 访问时间戳与曼哈顿距离双重判定；
  - 设定驻留块上限（例如 **64 块**，对应 8×8 的超大视口覆盖区，内存稳定在 ~160MB，远低于全图 1.2GB）；
  - 每当新块完成预热且总数超过上限时，从距离玩家最远（距离 > 2500px）且最近最少使用的地块开始调用 `sceneDrop` 释放 BitmapData；
  - 配合 E1 动态预热，保证被逐出的地块在玩家掉头往回走时有足够时间重新后台预热，绝不引发回头路补画风暴。

---

## 4. 实施阶段与可执行工序（Implementation Roadmap）

实施遵循工作区**“分步实施、独立验证、门禁卡点、快速回滚”**的原则：

| 阶段 | 实施内容 | 涉及文件 | 风险等级 | 核心验收指标 |
|---|---|---|---|---|
| **Phase 1** | **子弹碰撞修复与空间分桶（C1）** | 宿主 `Grafon.as`、`Bullet.as` | 中 | 消除 #1069 异常；屏外命中正常；12 敌人交火帧时下降 ≥8ms |
| **Phase 2** | **敌人唤醒信号分级与脱战迟滞（C2+C3）** | 模组 `NativeSceneActivity.as` | 低（纯模组层） | 29 项机制断言通过；开战首帧 awake 增量 ≤2；无站桩呆滞 |
| **Phase 3** | **动态自适应视口缓冲（E1）** | 模组 `SceneAimController.as`、宿主 `Grafon.as` | 低 | 快速横移与 Aim-Look 扫荡中视口 miss 次数 = 0 |
| **Phase 4** | **`drawKusok` 增量切分（E2）** | 宿主 `Grafon.as` | 中 | 像素 100% 严格一致；单步耗时 maxStepMs ≤ 25ms |
| **Phase 5** | **远处地块 LRU 智能逐出（E3）** | 宿主 `Grafon.as` | 中 | 驻留块稳定在 ≤64 块；长探索内存平稳，无掉头补画风暴 |

---

## 5. 正确性门禁与性能验收标准（Verification & Gates）

### 5.1 正确性保证（发布红线）
1. **屏外命中机制（Offscreen Hits）**：
   - 必须通过 `qualification-v6` 命中测试套件：屏幕外休眠/活动目标在无视口依赖下能正确受到盲射子弹伤害与触发受击判定；
2. **AI 警觉与战术行为完整性**：
   - 处于玩家正面视线或直接攻击走廊中的敌人必须 0 延迟响应，严禁出现“当面开火敌人无反应”的弱智站桩；
3. **视觉渲染零破坏**：
   - 地块预热切分与视口缓冲必须与原生渲染保持严格像素级等价（沿用 `SceneBackgroundCompositeChecks` 220 万像素零差异门禁）；
   - 绝不允许出现黑块、拼缝拉伸或可见闪烁。

### 5.2 性能验收目标（真机实测标尺）
- **交战场景（Combat Benchmark）**：
  - 12 敌人同屏开火平均帧耗时从 **56.8ms 下降至 ≤40ms**（帧率提升 30% 以上）；
  - 开火交战过程中的 ≥100ms 严重长帧发生率下降 **≥50%**；
- **探索场景（Exploration Benchmark）**：
  - 自然行走探索中的视口 miss 强制补画发生次数降低至 **0 次/分钟**；
  - 预热最大单步耗时从 **125ms 严格压减至 ≤30ms**；
  - 30 分钟连续深入探索内存增长上限锁死在 **≤250MB**，无单调泄漏趋势。

---

## 6. 回滚预案与安全承诺

- **宿主补丁回滚**：
  - 实施前备份当前宿主（`build/backups/pfe_before_opt_*.swf`）；
  - 出现任何异常，直接用备份文件覆盖根目录 `pfe.swf` 并重启游戏，1 秒内无损还原；
- **模组层回滚**：
  - 模组层修改保留上一版本 release SWF 备份（如 `ContinuousSceneMod-0.9.8-*.swf`）；
  - 运行时可通过配置或控制台直接热关停相关模块（如 `nativeAPI.activityBudget`、`objectCullingEnabledSet`）；
- 每次性能验证严格遵循工作区治理章程：**独立 AIR ID、独立临时存储目录、私有桌面隔离运行、绝对不修改玩家真实存档与配置**。
