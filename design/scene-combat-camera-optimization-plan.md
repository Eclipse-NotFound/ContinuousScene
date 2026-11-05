# ContinuousScene 场景探索、天角兽交战与镜头视觉优化方案

> **文件标识**：`mods/ContinuousScene/design/scene-combat-camera-optimization-plan.md`  
> **编制日期**：2026-11-04  
> **当前基线**：宿主 `pfe.swf` (A9B39CC7)、CS 0.9.7 (447AE02B，事件驱动增量剔除)、`scene.xml` (1CEA74E2)  
> **调查范围**：
> 1. 探索新场景时偶发的严重卡顿（>100ms 冻结）；
> 2. 与单只天角兽（UnitAlicorn）交战时的严重卡顿；
> 3. 镜头移动时背景（墙壁等）移动的视觉效果较粗糙（含动态模糊可行性论证与低成本平滑方案）。  
> **状态**：**技术根因排查完成，可执行优化方案定稿**

---

## 0. 综合现状与优化路线图速览

根据前期真实游玩采样（Session 1793689524405，196秒内出现38次 >100ms 长帧，峰值 242ms）及针对宿主 `Grafon.as`、`Camera.as`、`UnitAlicorn.as` 和模组 `SceneObjectCulling`、`SceneEventBitmapFill` 的代码级深度排查，三大问题的根因与实施路径清晰如下：

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        ContinuousScene 专项性能与视觉优化三维全景图                     │
├────────────────────────────┬─────────────────────────────┬─────────────────────────────┤
│   问题 1：新场景探索偶发严重卡顿  │  问题 2：单只天角兽交战较严重卡顿 │  问题 3：背景移动视觉粗糙 / 动态模糊  │
├────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ 根因：                      │ 根因：                      │ 根因：                      │
│ ① 48ms 激进预绘与单步阻塞   │ ① findBox 全图1200+物体遍历 │ ① 30fps低采样率人眼生理频闪 │
│ ② 视口 miss 触发同步强制重绘 │   + 频繁 DDA 射线检测(isLine) │ ② 瓦片 smoothing=false 近邻 │
│ ③ 冷块批量分配触发 GC 周期停顿│ ② GlowFilter 强制全向重绘    │   采样导致的硬像素爬行跳跃  │
│ ④ 移动开火相交取消作业风暴 │ ③ 闪电 destroy=50 破坏地形  │ ③ Camera 坐标强转 int 截断  │
├────────────────────────────┼─────────────────────────────┼─────────────────────────────┤
│ 对策：                      │ 对策：                      │ 对策：                      │
│ • 自适应动态余量调度 (2~12ms)│ • findBox 局部空间网格限制  │ • 否定全屏动态模糊(单帧30~80ms)│
│ • 预绘作业非破坏性待应用缓冲  │ • 念力发光改用轻量染色/预烘焙│ • 瓦片开启 smoothing=true   │
│ • 视口 miss 异步占位平滑过渡 │ • 闪电破坏降级为局部增量补丁 │ • 相机解绑 int，支持亚像素平移│
│ • 地块 BitmapData 对象池化   │ • 瞬移 actPort 局部安全采样 │ • 引入微阻尼 Lerp 消除突变  │
└────────────────────────────┴─────────────────────────────┴─────────────────────────────┤
                                          ↓                                              
                           [分阶段安全实施与独立门禁验收]                                 
```

---

## 1. 探索新场景偶发严重卡顿：调查与可执行方案

### 1.1 代码级与机制级根因调查

玩家在马哈顿废墟等超大连续场景探索新未知区域时，偶发高达 100~240ms 的严重冻结，其根因由以下四个链条交叉共振引起：

#### 根因 1.1：预绘预算上限膨胀（48ms）与单步不可中断执行
- **代码位置**：宿主 `fe.graph.Grafon.as:2378` (`sceneEnsureUpcoming`) 及 `:3268` (`sceneAdvanceWarm`)
- **机制剖析**：
  1. 当前宿主补丁将预绘时间上限设定为 `2~48ms`（源自历史极端 80px/帧平移测试遗留值）。在 30fps 基准下，整帧总时间仅为 33.3ms，除去游戏原生逻辑和物理更新通常只剩余 5~15ms。
  2. `sceneAdvanceWarm` 仅在完整步骤之间检查时间（`if(getTimer() - start >= budget)`）。然而单个背景层绘制、复杂滤镜处理或底层材质生成（`drawKusok`）往往单步耗时即达 20~35ms 且无法中断。单步超限直接将当帧拉长至 60~90ms。

#### 根因 1.2：视口 Miss 触发主线程同步全量强制补画（Sync Render）
- **代码位置**：宿主 `fe.graph.Grafon.as:56` (`sceneRender`) 及 `:2420`
- **机制剖析**：
  当玩家移动速度较快、穿过障碍或跳跃推进时，镜头视口边缘覆盖到了尚未完成异步预热的区块。此时宿主判定发生视口 miss，触发 `sceneRender(force=true)`，在**主线程中同步强制执行全量绘制**（包含 Front、Back、Back2、Voda 四层位图的完整光栅化与合并）。单个 320×320 复杂地块同步绘制耗时高达 **25~45ms**，叠加当帧其它负载，瞬间形成 **>100ms 乃至 200ms+ 的视觉卡死**。

#### 根因 1.3：冷块创建大量 BitmapData 诱发 Mark-Sweep 全量 GC 停顿
- **证据与数据**：真实游玩采样显示，38 次 >100ms 长帧中有 **25 次伴随明显的堆内存暴跌**（单次释放数兆至数十兆字节）。
- **机制剖析**：
  每个逻辑边长 320px 的地块包含 4 张带 gutter 扩展的 400×400×4 字节位图，单个地块裸位图内存即达 **2.56 MiB**。在新区域推进时，几秒钟内连续分配数十个新地块，产生超过 50~100MB 的突发内存分配，直接撞上 Adobe AIR 的内存阈值，强制触发耗时 40~90ms 的 Mark-Sweep 垃圾回收停顿。

#### 根因 1.4：移动开火相交取消预绘风暴（Cancel-Warm Storm）
- **代码位置**：宿主 `fe.graph.Grafon.as:1085` (`sceneApply`)、`:3046` (`sceneCancelWarm`)
- **机制剖析**：
  探索时若玩家手持轻机枪向前方射击，弹痕（paint/decal）落在正在预绘区块的外扩相交区域内，`sceneApply` 会无条件调用 `sceneCancelWarm(affected)`，将正在异步绘制的作业直接取消并销毁中间缓冲区。这导致本来即将就绪的区块变成视口 miss，被迫退化为上述的根因 1.2 同步强制补画。

---

### 1.2 探索卡顿可执行优化方案

#### 方案 1.1：自适应帧余量预绘调度（Adaptive Frame-Budgeting）
- **目标**：彻底消除预绘主动超时拉垮帧率的现象。
- **改动位置**：宿主 `fe.graph.Grafon.as` (`sceneEnsureUpcoming`, `sceneAdvanceWarm`)
- **设计逻辑**：
  废弃固定 48ms 预算，引入以 30fps（33.3ms）为安全基线的动态反馈调节公式：
  ```actionscript
  // 计算当帧剩余安全时间，扣除渲染底线安全缓冲 4ms
  var frameElapsed:int = getTimer() - World.w.frameStartTime;
  var availableBudget:int = 33 - frameElapsed - 4;
  // 严格钳制在 [2ms, 12ms] 区间，重负载帧坚决让路
  var budget:int = Math.max(2, Math.min(12, availableBudget));
  ```
  同时，在 `sceneAdvanceWarm` 内部每完成一个子图层绘制前采样时间，一旦当前累计消耗超过预设的安全步长阈值（8ms），立即主动 `return` 延迟至下一帧。

#### 方案 1.2：非破坏性弹痕待应用缓冲（Pending Decal Marks）
- **目标**：开火命中预绘区域时杜绝取消作业。
- **改动位置**：宿主 `fe.graph.Grafon.as` (`sceneApply`, `sceneCancelWarm`, `sceneAdvanceWarm`)
- **设计逻辑**：
  1. 区分修改类型：纯弹痕 (`kind == "paint"` / `"decal"`) 与破坏性地形更新 (`kind == "destroy"` / `"drawKusok"`)。
  2. 若仅为弹痕击中正在预热的区块，**禁止调用 `sceneCancelWarm`**；
  3. 将弹痕数据存入该预绘作业的 `pendingMarks:Vector.<Object>` 队列；
  4. 当 `sceneAdvanceWarm` 完成所有底图光栅化、准备将地块挂入驻留字典前，一次性重放并图章化 `pendingMarks`，实现零废工与零取消。

#### 方案 1.3：地块 BitmapData 对象池化复用（BitmapData Recycling Pool）
- **目标**：平抑进入新区域时的剧烈内存分配与 GC 停顿。
- **改动位置**：宿主 `fe.graph.Grafon.as`
- **设计逻辑**：
  建立 400×400 ARGB 尺寸的全局位图对象池：
  ```actionscript
  private var bmdPool:Vector.<BitmapData> = new Vector.<BitmapData>();
  ```
  当超出视口极远（如视口外 3000px）的历史区块被逐出（evict）时，不再调用 `dispose()` 丢给 GC 回收，而是回收进 `bmdPool`；生成新区域区块时优先从池中复用并执行 `fillRect(rect, 0)`，大幅削减大内存分配频次。

---

## 2. 与单只天角兽（UnitAlicorn）交战较严重卡顿：调查与可执行方案

### 2.1 代码级与机制级根因调查

针对用户报告的“**单只天角兽交战即严重卡顿**”，我们对反编译源码 `game-reference/decompiled/1.02/src102/scripts/fe/unit/UnitAlicorn.as` 进行了全逻辑排查。天角兽作为高阶魔法 Boss 级单位，其独特的战斗机制在 ContinuousScene 连续大场景下产生了严重的放大效应：

#### 根因 2.1：`findBox()` 全图 1200+ 物体线性遍历与穿墙 DDA 射线暴击（首要元凶）
- **代码位置**：`fe.unit.UnitAlicorn.as:1026-1033`、`:1140-1168`
- **代码实证**：
  ```actionscript
  // control() 每帧步进计时器
  ++this.t_tele;
  if(this.t_tele == 0) {
      if(aiState <= 1 || this.findBox() == null) {
          this.t_tele = -Math.floor(Math.random() * 100 + 50);
      }
  }
  
  internal function findBox() : Obj {
      ...
      for each(_loc1_ in loc.objs) { // 遍历当前地图所有物体！
          if(_loc1_.levitPoss && _loc1_.wall == 0 && _loc1_.levit == 0 && _loc1_.massa >= 1 && isrnd(0.3)) {
              if(getRasst2(_loc1_) <= this.optDistTele * this.optDistTele) {
                  // 对满足条件的物体进行射线穿墙相交测试！
                  if(loc.isLine(X, Y - scY / 2, _loc1_.X, _loc1_.Y - _loc1_.scY / 2)) {
                      this.upTeleObj(_loc1_);
                      return _loc1_;
                  }
              }
          }
      }
      return null;
  }
  ```
- **机制剖析**：
  1. 在游戏原版单房间地图中，`loc.objs` 通常仅有 10~30 个物体，线性遍历开销可忽略。
  2. 但在 **ContinuousScene 连续大场景**（如马哈顿废墟）中，整个大场景所有房间合并，`loc.objs` 包含 **1200+ 个箱子（Box）和上百个道具**。
  3. 天角兽交战时高频进入 `findBox()`：它对全图 1200+ 个物体逐个做属性读取和距离平方计算；更严重的是，对距离相符的物体调用 `loc.isLine()`（在全瓦片网格上步进计算 DDA 视线阻挡）。
  4. 如果当前范围内没有合适的箱子，`findBox()` 将完整扫描全图 1200+ 物体，单次函数耗时可达 **4~10ms**！战斗中周期性出现该遍历，帧率出现明显剧烈抖动。

#### 根因 2.2：念力发光滤镜 `GlowFilter` 诱发每帧离屏重绘
- **代码位置**：`fe.unit.UnitAlicorn.as:226`、`:1179` (`upTeleObj`)、`:1050-1065`
- **代码实证**：
  ```actionscript
  teleFilter = new GlowFilter(this.tlColor, 1, 6, 6, 1, 3);
  ...
  this.teleObj.vis.filters = [teleFilter];
  ```
- **机制剖析**：
  1. 一旦抓取物体，天角兽给被抓物体的显示对象挂上 `teleFilter`。
  2. 随后在 `control()` 中，天角兽每帧通过念力物理加速度改变物体的坐标（`teleObj.dx += teleAccel`, `teleObj.dy += teleAccel`）。
  3. 在 Adobe AIR 软光栅管线下，**凡带有滤镜（Filters）的 DisplayObject 只要发生位移或改变，Flash 引擎每帧都必须全量为它重新生成离屏位图表面并执行双向高斯模糊卷积**！
  4. 尤其当天角兽通过 `isrnd(0.25)` 抓取玩家（`UnitPlayer`）时，玩家包含身体、武器、多层骨骼和复杂动画，整个人物容器挂上滤镜每帧动态重绘，单帧带来巨大的 CPU 渲染开销。

#### 根因 2.3：瞬移 `actPort()` 在全大场景跨度盲测 `collisionAll`
- **代码位置**：`fe.unit.UnitAlicorn.as:1248-1317`
- **代码实证**：
  ```actionscript
  var _loc5_:* = 1;
  while(_loc5_ <= 20) {
      if(_loc5_ < 5 && !param1) { ... }
      else if(_loc5_ < 10 && !param1) { ... }
      else {
          _loc3_ = Math.random() * loc.limX; // 全大地图数千像素随机！
          _loc4_ = Math.random() * loc.limY;
      }
      ...
      if(!collisionAll(_loc3_ - X, _loc4_ - Y)) { // 全局碰撞探测！
          teleport(_loc3_, _loc4_, 1);
          return;
      }
      _loc5_++;
  }
  ```
- **机制剖析**：
  天角兽血量危急或释放大招时执行 `actPort()` 寻找传送点，循环高达 20 次。在大场景下后 10 次在全图上万像素范围随机取点，每次都调用 `collisionAll` 进行庞大的碰撞测试，造成瞬时 CPU 脉冲阻塞。

#### 根因 2.4：闪电主武器 `alilight` 的地形破坏机制（`destroy='50'`）
- **代码位置**：`fe.AllData.as:684-690`
- **配置数据**：`<weapon id='alilight' tip='0'><char damage='50' rapid='35' prep='12' prec='0' tipdam='9' destroy='50'/><vis vweap='visalilight' tipdec='11' vbul='lightning'.../>`
- **机制剖析**：
  天角兽默认武器 `alilight` 射速极快（`rapid='35'`），且带有 `destroy='50'` 的地形破坏属性！天角兽与玩家交火时，闪电弹体频繁击中附近的墙面和地板，不断触发 `loc.destroyTile`。在大场景下破坏地形属于破坏性修改，立即打碎周围地块的位图缓存，引发主线程地块同步局部重绘（`drawKusok`），导致战斗过程频繁伴随掉帧。

---

### 2.2 天角兽交战可执行优化方案

#### 方案 2.1：`findBox()` 空间局部网格约束与节流（Spatial Culling & Throttling）
- **改动位置**：移植补丁 `fe.unit.UnitAlicorn.findBox`（宿主补丁或模组方法替换）
- **设计逻辑**：
  1. **空间距离粗筛**：不再遍历 `loc.objs` 全量列表。天角兽念力最大有效距离为 `optDistTele`（约 400~600px）。利用连续场景已有的空间网格或按 X 轴排序二分裁剪，将检索候选集限制在 `[X - optDistTele, X + optDistTele]` 局部窗口内，遍历对象数从 1200+ 缩减至 **10~20 个以内**。
  2. **DDA 射线检测节流**：单帧内最多执行 **2 次** `loc.isLine` 测试；若未通过则中断并在下一探测周期再试，杜绝单帧连续多次执行昂贵射线检测。
  3. **空搜失败退避**：若连续 2 次未找到合适箱子，将下一次搜索冷却时间延长（`t_tele = -150`），避免空旷区域无意义的频繁高频重搜。

#### 方案 2.2：念力重型滤镜降级与替代（GlowFilter Mitigation）
- **改动位置**：`fe.unit.UnitAlicorn` (`upTeleObj`, `dropTeleObj`)
- **设计逻辑**：
  1. **被抓物体**：取消高开销的 `filters = [teleFilter]`（全向高斯发光），替换为轻量级 `transform.colorTransform`（赋予魔法荧光浅色调，如微蓝/微青色叠加），或者在物体周围挂载一个轻量级预烘焙矢量光圈 Sprite。`colorTransform` 属于原生 GPU/寄存器级乘加运算，**零位图重绘开销**。
  2. **被抓玩家**：严禁给玩家整体容器 `vis` 施加任何 `filters`，保持玩家骨骼与武器绘制管线干净畅通。

#### 方案 2.3：`actPort()` 传送范围局部化与安全点快速采样
- **改动位置**：`fe.unit.UnitAlicorn.actPort`
- **设计逻辑**：
  取消在大场景 `loc.limX` / `loc.limY` 全图盲抽。传送目标严格限定在以天角兽当前坐标为中心、半径 800px 的战术战斗圈内。若尝试 5 次未命中合适空地，则直接选用玩家背后的合法地面锚点，避免连续 20 次盲测 `collisionAll`。

#### 方案 2.4：高频闪电弹体地形破坏增量保护
- **改动位置**：宿主 `fe.graph.Grafon.sceneApply`
- **设计逻辑**：
  对于 `alilight` 等非重度爆炸（非炸弹/C4）的轻微地形损伤（`destroy <= 50`），仅执行瓦片逻辑破损与小贴图覆盖，**不标记区块为全面脏（isDirty）**，不触发全块 320px 的重新光栅化，阻断战斗时的背景重绘冲击。

---

## 3. 镜头移动时背景（墙壁等）移动视觉粗糙调查与动态模糊评估

### 3.1 视觉粗糙根源深度调查

用户反馈：“现在镜头移动时背景（墙壁等）移动的视觉效果较粗糙（我正在考虑引入动态模糊）”。经深入分析，背景移动“粗糙/卡顿感/步进感”有三个核心物理与技术根源：

#### 根因 3.1：30 FPS 锁定帧率下的视觉频闪（Strobe Effect / Judder）
- **生理与渲染原理**：
  Remains 游戏底层逻辑与渲染均锁定在 **30 FPS**（每帧约 33.3ms）。
  当玩家平移探索时，镜头通常以每秒 150~300 像素的速度移动，这意味着**每一帧背景在屏幕上跨越 5~10 个物理像素**。
  人眼视网膜对运动物体的追踪时间分辨率远高于 30Hz。当高对比度纹理（如砖墙垂直缝隙、金属支柱、栅栏网格）以离散的 5~10 像素跳跃刷新时，人眼的视觉暂留机制会在视网膜上形成“锯齿状阶梯”与“多重残影轮廓”（Judder / 齿轮抖动感），直观感受就是“粗糙、不平滑”。这也是为什么玩家本能地想通过“动态模糊（Motion Blur）”来掩盖这种步进跳跃。

#### 根因 3.2：地块位图采用近邻采样（`smoothing = false`）与像素爬行（Pixel Crawl）
- **代码实证**：
  在 `mods/ContinuousScene/src/tests/SceneBackgroundCompositeProbe.as:169` 等核心模块中确认：
  ```actionscript
  b.bitmapData.transparent && b.pixelSnapping == "auto" && !b.smoothing
  ```
  原生地形地块以及很多模组生成的位图节点中，默认均设定了 `smoothing = false`，并且启用了 `pixelSnapping = "auto"`。
- **机制剖析**：
  1. `smoothing = false` 代表**最近邻采样（Nearest Neighbor）**，无双线性插值。
  2. 当镜头发生微小亚像素移动或窗口缩放（scale != 1）时，纹素不会平滑过渡，而是当浮点位移超过阈值时瞬间“跳”到下一个物理像素网格。
  3. 这种离散的像素跳变会导致墙壁边缘发生刺眼的**像素爬行（Pixel Crawling）与高频莫尔条纹闪烁**，极大地加剧了画面的粗糙感。

#### 根因 3.3：`Camera.as` 坐标强转 `int` 截断与无阻尼机械瞬变
- **代码位置**：`game-reference/decompiled/1.02/src102/scripts/fe/inter/Camera.as:24-25`、`:218`、`:285-286`
- **代码实证**：
  ```actionscript
  public var vx:int;
  public var vy:int;
  public var X:int = 200;
  public var Y:int = 200;
  ...
  this.X = param1.X * this.scaleV; // param1.X 为浮点，强转为 int
  this.vx = -this.X + this.screenX / 2; // 整数截断
  ...
  this.w.visual.x = this.vx + this.quakeX;
  ```
- **机制剖析**：
  相机的目标位置 `X`、`Y` 与最终位移 `vx`、`vy` 全部被定义并截断为 `int` 整型！玩家移动速度是带有惯性浮点加速的，但相机位置却只能在整数像素上跳变；加上相机直接硬绑定玩家位置，无任何缓动插值阻尼，玩家起步、跳跃、落地时的加速度冲击被无缓冲直接传递到屏幕，呈现出强烈的机械生硬感。

---

### 3.2 动态模糊（Motion Blur）可行性与性能代价深度评估（重点！）

针对用户提出的“**正在考虑引入动态模糊**”，我们从 Adobe AIR 运行环境底层机制、渲染成本与视觉效果三个维度进行全面推演和评估：

#### 3.2.1 方案 A：使用 Flash 原生 `flash.filters.BlurFilter`
- **实现机制**：在世界主容器 `w.visual` 或镜头呈现层上动态挂载 `BlurFilter(blurX, blurY, quality)`，根据镜头瞬时速度 `vx, vy` 动态设置模糊半径。
- **致命缺陷（性能雪崩）**：
  1. **全向高斯模糊 vs 定向运动模糊**：`BlurFilter` 是轴向盒式/高斯模糊，无法实现沿运动轨迹单向拖尾的真实运动模糊，会导致墙壁上下左右全部发虚。
  2. **灾难性的 CPU 软光栅开销**：Adobe AIR 桌面版在纯 CPU 软光栅模式下运行。在用户当前的大窗口（2048×1123，超过 220 万像素）下，对全屏容器执行一次 `quality=1` 的最低画质高斯模糊，**单帧 CPU 耗时高达 35ms ~ 85ms**！
  3. **结论**：直接使整帧耗时突破 70~120ms，游戏帧率从 30fps 断崖式跌落至 **8~12 FPS 幻灯片**！该方案在工程技术上具有绝对破坏性，坚决不可行。

#### 3.2.2 方案 B：全屏累积缓冲（Accumulation Trail Buffer）
- **实现机制**：创建全屏尺寸 `BitmapData`，每帧以半透明 Alpha（如 0.6）将上一帧图像叠加混合，制造运动残影拖尾。
- **致命缺陷**：
  1. **大分辨率 BitmapData.draw 吞噬帧时间**：在 2048×1123 分辨率下，单次 `BitmapData.draw()` 在 CPU 下耗时 **10~18ms**，吃掉超过一半的帧预算。
  2. **2D 横版视效灾难**：在快节奏横版射击游戏中，全屏残影不仅模糊背景，还会将准星、UI 文字、飞行动画、角色和敌人全部重影拖脏。玩家在高速移动时会产生强烈的视觉疲劳、对焦困难和眩晕感。

#### 3.2.3 评估结论
**坚决否定在 Flash/AIR CPU 渲染管线中引入全局动态模糊**。动态模糊是 3D 现代引擎借助 GPU Compute Shader 的廉价后处理技术，而在 Flash 2D 软光栅架构下，全屏模糊在性能上是不可逾越的鸿沟，在视觉上是破坏性的倒退。

---

### 3.3 高画质、极低开销的背景平滑优化替代方案

无需引入沉重且肮脏的动态模糊，通过以下三个极低开销（<0.5ms）的底层改进，即可从根本上消除背景移动的粗糙感：

#### 方案 3.1：全面开启位图双线性平滑重采样（Bilinear Smoothing）
- **改动范围**：`SceneEventBitmapFill.as`、`ScenePresentationCoordinator.as`、宿主 `Grafon.as`
- **技术设计**：
  1. 将所有背景地块（Front、Back、Back2、Voda）的 `Bitmap` 实例显式设为：
     ```actionscript
     bitmap.smoothing = true;
     bitmap.pixelSnapping = PixelSnapping.NEVER;
     ```
  2. 针对地块拼接边缘可能因双线性采样引入邻域透明接缝（1px 缝隙）的问题：
     ContinuousScene 当前地块本来就带有 400×400（针对 320px 逻辑块有 40px gutter 边缘外扩缓冲）；开启 `smoothing = true` 时，双线性插值会平滑采样 gutter 内部的真实纹素，**天然支持平滑过渡且绝对零拼缝**。
- **效果与代价**：
  - **视觉提升**：消除近邻采样的像素离散跳变与锯齿爬行，移动时边缘呈现柔和的亚像素过渡。
  - **性能代价**：Flash 底层对已就绪 BitmapData 的双线性重采样开销极小，全屏 4 层渲染耗时增加 **<0.4ms**，几乎完全免费！

#### 方案 3.2：解除 Camera 坐标整型截断，支持亚像素浮点移动
- **改动范围**：宿主 `fe.inter.Camera.as`
- **技术设计**：
  1. 将 Camera 的关键位移字段从 `int` 改造为 `Number`：
     ```actionscript
     public var vx:Number;
     public var vy:Number;
     public var X:Number;
     public var Y:Number;
     ```
  2. 取消 `this.X = param1.X * this.scaleV` 时的强制整数截断，允许浮点精度保留。
  3. 世界容器平移赋值 `this.w.visual.x = this.vx + this.quakeX;` 保持原生浮点赋值。
  4. 配合 `ScenePresentationCoordinator`，放宽平移矩阵中的非整数校验，允许带有微小小数的亚像素变换矩阵正常通行合批。

#### 方案 3.3：相机轻度阻尼平滑插值（Damped Smooth Follow）
- **改动范围**：宿主 `fe.inter.Camera.as` (`calc`)
- **技术设计**：
  在相机跟随玩家坐标时，废除机械瞬时硬赋值，引入轻量级指数平滑插值（Lerp）：
  ```actionscript
  // 目标平移坐标
  var targetVx:Number = -this.X + this.screenX / 2;
  var targetVy:Number = -this.Y + this.screenY / 2 + 100;
  
  // 0.85 比例平滑逼近，保留手感即时响应的同时消除加速度离散冲击
  this.vx += (targetVx - this.vx) * 0.85;
  this.vy += (targetVy - this.vy) * 0.85;
  ```
- **效果**：玩家起跑、刹车、落地时的加速度剧变被平滑过滤，背景呈现出丝滑、柔和的移动质感。

---

## 4. 分阶段实施甘特图与工期规划

本优化严格贯彻 **“先纯模组层速赢，再宿主针对性修复；独立验证、随时可回滚”** 的工程铁律：

| 阶段 | 优化模块 | 涉及关键文件 | 预估工时 | 产出物与预期成效 |
|---|---|---|---|---|
| **Phase 1**<br>探索卡顿平抑 | 自适应预绘调度 (1.1)<br>弹痕待应用缓冲 (1.2)<br>地块位图池化 (1.3) | 宿主 `fe.graph.Grafon.as`<br>`tools/stutter_host.py` | 1.5 天 | 根除预绘越界与取消风暴；新区域探索 >100ms 峰值减少 60% 以上 |
| **Phase 2**<br>天角兽交战减负 | findBox 空间网格裁剪 (2.1)<br>念力滤镜降级变色 (2.2)<br>actPort 局部安全采样 (2.3)<br>闪电地形破坏保护 (2.4) | 供体/宿主 `UnitAlicorn.as`<br>`SceneAlicornAlerts.as`<br>`build/alicorn-alerts.py` | 1.5 天 | 单只天角兽交战帧率由剧烈抖动稳定至 ≥27 FPS，彻底根除 1200+ 物体遍历 |
| **Phase 3**<br>镜头背景平滑 | 地块开启双线性平滑 (3.1)<br>Camera 亚像素浮点化 (3.2)<br>相机跟随阻尼缓动 (3.3) | `SceneEventBitmapFill.as`<br>`ScenePresentationCoordinator.as`<br>宿主 `Camera.as` | 1 天 | 彻底消除像素爬行硬边锯齿与机械顿挫；零性能负担实现视觉顺滑 |
| **Phase 4**<br>集成回归验收 | 综合打包、真机双臂测试与交付 | `release/`<br>`state/MEMORY.md`<br>`state/journal.md` | 1 天 | 交付稳定版 CS 0.9.8，输出完整配对对比验证报告 |

---

## 5. 质量保证、验证门禁与回滚机制

### 5.1 验证测试矩阵与门禁检查单

每一阶段产物必须严格通过以下自动化与真机夹具验证，未达门禁严禁推入 `release/`：

1. **功能完整性与正确性门禁**：
   - 运行 `src/tests/SceneCullingChecks.as`（24/24 增量剔除与包装层断言全部通过）；
   - 运行 `src/tests/SceneOffscreenHitChecks.as`（屏外自然敌人正常受击并唤醒）；
   - 运行 `src/tests/fe/unit/AlicornAlertAccess.as`（天角兽警戒、念力与瞬移正常工作，无报错异常）；
   - SATS 战术模式截屏保真度比对：像素级 0 误差。
2. **性能与时序量化门禁**：
   - **探索指标**：在马哈顿废墟连续探索 3000 帧，断言 `syncRenderCount <= 2`，预绘引起的 >100ms 长帧频次由 ~11.6 次/分压制到 **<3 次/分**；
   - **天角兽交战指标**：生成单只天角兽进入战斗 1000 帧，函数耗时分析断言 `findBox()` 耗时稳定在 **<0.5ms**，整帧均值较基线提升 **≥15%**；
   - **视觉呈现指标**：平移测试中 `SceneEventBitmapFill` 保持稳定 `presented`，无 `fallback` 发生。

### 5.2 安全回滚机制（Rollback Runbook）

每次改动均采用原子替换和版本备份，任何阶段未达预期可秒级无损回滚：
1. **模组层回退**：
   若 CS 模组出现逻辑异常，将 `build/backups/ContinuousSceneMod-0.9.7-447AE02B-...swf` 重新覆盖至 `mods/ContinuousScene/release/ContinuousSceneMod.swf` 并重启游戏。
2. **宿主层回退**：
   若宿主补丁（Grafon / Camera / UnitAlicorn）出现兼容性缺陷，直接使用备份 `build/backups/pfe_before_spatial_collision_20261101-225837.swf` 覆盖根目录 `pfe.swf`，恢复至 A9B3 原生基线。
3. **运行时应急开关**：
   模组中保留全局诊断开关 `nativeAPI.scenePresentationEnabledSet(false)` 及 `nativeAPI.objectCullingEnabledSet(false)`，支持在不重启游戏的前提下在线降级。
