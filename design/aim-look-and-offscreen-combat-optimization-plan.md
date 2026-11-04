# ContinuousScene 瞄准视口、镜头动力学、移动射击解耦与屏外命中优化方案

> 责任模组：ContinuousScene  
> 日期：2026-11-04（方案）/ 2026-11-04（实施记录见 §六）  
> 状态：**已实施 CS 0.9.9 + 宿主候选**（确定性 61/61、隔离实机 13/13）  
> 涉及模块：`SceneAimController.as`、`ContinuousSceneMod.as`、`NativeSceneActivity.as`、宿主 `Grafon.as`、宿主 `Camera.as`、`Bullet.as`

---

## 一、 现状调查与根本原因剖析

针对用户提出的四个核心痛点，我们对游戏反编译源码、模组运行机制、当前已部署的 0.9.8 瞄准补丁及测试夹具进行了完整的代码级与时序级链路调查：

### 1. 按 Alt 瞄准时远端墙体不会加载（视口时序错位与剔除）

- **现象**：按住 Alt 将镜头推向远处时，远端延伸出的视野区域呈现黑色/空白，原有的墙体、地形瓦片（Tile）未被渲染；或者松开回中后再推，部分墙体丢失或闪现。
- **机制与调用链根因**：
  1. **执行时序错位**：
     - 在游戏原生主循环中，每帧先由 `fe.inter.Camera.calc(param1:Unit)` 计算镜头位置。原生逻辑依据玩家角色的世界坐标计算 `cam.vx = -param1.X + screenX/2`（以及 `cam.vy`）。
     - 宿主补丁（`prepare.py:177`）在 `Camera.calc` 内部调用了 `this.w.grafon.sceneTick()`。
     - 在 `Grafon.sceneTick()` 中：
       ```actionscript
       var camera:* = World.w.cam;
       var scale:Number = camera.scaleV > 0 ? camera.scaleV : 1;
       this.sceneEnsure(-camera.vx / scale, -camera.vy / scale, camera.screenX / scale, camera.screenY / scale);
       this.sceneCullSurfaces();
       ```
     - 此时 `cam.vx, cam.vy` **仍然是未偏移的玩家中心坐标**！`sceneEnsure` 只为玩家脚下 1920×1000 区域加载与渲染区块（Chunk）。
     - 紧接着，模组的 `ContinuousSceneMod.onFrame` 监听器在 `ENTER_FRAME` 优先级 `-200`（即原生主循环之后）才执行：
       `aim.update(w, mouseX, mouseY)` 在此处将 `cam.vx` 和 `cam.vy` 强行偏移了最多 700 像素，并直接赋值给 `w.visual.x, w.visual.y`。
  2. **缺少瞄准后视口确保**：
     - 在 `aim.update` 修改了 `cam.vx, cam.vy` 之后，**完全没有再次触发 `Grafon.sceneTick()` 或 `sceneEnsure()`**。
     - 到了下一帧，`Camera.calc` 开始时又立刻将 `cam.vx` 覆写回玩家中心，然后再以玩家中心调用 `sceneTick()`。
  3. **表面剔除导致远端墙体被隐藏**：
     - `Grafon.sceneCullSurfaces()` 会遍历所有已加载的 Chunk，将不在 `sceneViewport()` 内的 Chunk Bitmap 设置为 `visible = false`。
     - 哪怕远端区块曾经被加载过，因为 `sceneTick` 每次运行时读取的都是玩家中心坐标，远端 Chunk 会被判定为“出屏”并直接设为不可见，导致镜头推向远处时远端墙体空洞。

---

### 2. 按 Alt 瞄准时的镜头移动较为急促，不够平缓（动力学缺陷）

- **现象**：按下 Alt 键的一瞬间，镜头猛烈冲出；鼠标在边缘微调时画面剧烈抖动；松开按键时回弹速度突兀，缺乏现代射击游戏的顺滑质感。
- **动力学根因剖析**：
  1. **一阶线性 Lerp 导致的初速度阶跃（无限大加速度）**：
     - 当前 `SceneAimController.as` 采用简单的一阶插值：
       `nx = offX + (tx - offX) * k;`（其中 `SPEED_IN = [0.12, 0.22, 0.32]`，默认 `k = 0.22`）。
     - 一阶 lerp 的物理特性是初始误差 `(tx - offX)` 最大时瞬时速度达到峰值。在第 1 帧，如果鼠标在屏幕边缘（`tx ≈ 700`），初始速度计算为 `700 * 0.22 = 154 px/frame`！
  2. **速度硬截断（Hard Clamp）带来冲击感**：
     - 控制器设置了 `MAX_STEP = 50`，导致第 1 帧、第 2 帧、第 3 帧以恒定 50px/frame 的极高速度“硬撞”出去（相当于 1500px/s 的匀速冲击），在没有加速度缓冲（Ease-In）的情况下给玩家眼睛造成极强的闪烁与顿挫感。
  3. **缺乏速度连续性与惯性阻尼**：
     - 当前算法没有记录相机的当前瞬时速度 `currentVelocity`，位移直接由目标差值决定，无法形成平滑的加减速 S 曲线（Ease-In-Out）。

---

### 3. “注视远处”与“移动/射击”互相冲突的交互死锁

- **痛点**：玩家想看清右侧远处的敌人并射击，但鼠标一移向敌人，镜头立刻缩回；或者按住 Alt 时左手被按键锁死，无法灵活走位。
- **机制与交互死锁分析**：
  1. **单一鼠标输入双重绑定的冲突**：
     - 目前镜头偏移计算公式为：`tx = (dx / d) * t * MAX_OFFSET_X`，其中 `dx = mouseX - halfW`。
     - 偏移量大小完全取决于**鼠标指针与屏幕中心的距离**。
     - 当玩家将视角推向远处看到敌人后，为了**射击敌人**，鼠标必须从屏幕边缘移向敌人所在的位置（通常在屏幕视野内）。
     - 鼠标一旦往屏幕中央移动，`dx, dy` 立即变小甚至归零，**导致镜头立刻飞速回缩**！敌人瞬间从画面中消失，玩家根本无法精准射击敌人。
  2. **移动时的视口拉扯**：
     - 当玩家使用 WASD 移动角色时，角色的世界坐标在变化，如果玩家想要注视远处的一个固定目标，鼠标在屏幕上必须反向补偿移动，否则镜头就会疯狂摇晃，无法实现“移动走位 + 注视警戒”。
  3. **按键人机工效冲突**：
     - 默认的“长按左 Alt”要求玩家左手拇指持续按住 Alt，严重限制了左手对 Space（跳跃）、A/D（移动）、Shift（冲刺）、R（换弹）的操作自由度，并且在 Windows 环境下极易触发系统级按键组合干扰。

---

### 4. 子弹对屏幕视野外的敌人命中机制与隐患

- **背景与现状澄清**：
  1. **原生命中链路正常但存在脆弱性**：
     - 原生 `fe.weapon.Bullet.run()` 通过遍历 `loc.units` 对世界空间内的所有单位进行 AABB 碰撞检测：
       `if (X >= u.X1 && X <= u.X2 && Y >= u.Y1 && Y <= u.Y2)`
     - 只要子弹的逻辑坐标未越界且未超过自身存活周期（`liv`，默认 100 帧），在原生未魔改状态下，子弹天然可以在屏幕外命中敌人。
  2. **历史补丁引入的严重设计隐患（`sceneCU` 视口过滤）**：
     - 在 11-01 的优化尝试中，曾试图通过 `Grafon.sceneTick` 构建相机视口（±500px）内的单位列表 `sceneCU`，并让 `Bullet.run` 仅遍历该视口列表。
     - 这一设计**从根本上破坏了屏幕外命中**：子弹飞出屏幕视口后，由于视口外敌人不在列表中，导致子弹彻底无法击中屏幕外的敌人！
     - 虽然 11-03 查明因为 `MainFE` 密封属性导致读取 `sceneCU` 恒抛 `#1069` 运行时异常而回退到全量 `loc.units`（屏外命中勉强保住），但每发子弹每帧抛异常带来了极大的额外开销，且一旦有人修补该属性，屏幕外命中就会立刻瘫痪。
  3. **实体调度休眠（`NativeSceneActivity`）对子弹响应的影响**：
     - 距离玩家超过 2200px 且在视口外的敌人会被置为 `sleeping`。
     - 必须确保子弹在超视距飞行时，弹道威胁区域（Threat Corridor）能够可靠穿透并有效唤醒和击伤目标，不能因休眠机制导致弹体穿透或伤害吞并。

---

## 二、 优化与重构方案设计

围绕上述四个核心维度，提出一整套体系化、互锁安全、零视觉退化且符合直觉的优化方案：

```
+-----------------------------------------------------------------------------------+
|                            ContinuousScene 瞄准与远程战斗架构                     |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [输入与控制层]                                                                   |
|   +--------------------+     +-------------------------------------------------+  |
|   | 触发模式:          |     | 瞄准解耦核心 (Decoupled Aim):                   |  |
|   |  - 切换模式 (推荐) | --> |  - 视线朝向向量锁定 (Directional Look Anchor)   |  |
|   |  - 长按模式        |     |  - 自由移动跟随 (WASD + Camera Follow)          |  |
|   +--------------------+     |  - 自由准星射击 (Free Crosshair Target Aim)     |  |
|                              +-------------------------------------------------+  |
|                                                      |                            |
|                                                      v                            |
|  [镜头动力学层]                                                                   |
|   +----------------------------------------------------------------------------+  |
|   | 临界阻尼平滑模型 (Critically Damped SmoothDamp):                           |  |
|   |  - 二阶速度连续性 (无初速度阶跃)                                           |  |
|   |  - 动态加减速 S 曲线约束 (Smooth Ease-In-Out)                              |  |
|   |  - 独立注视死区与微小抖动滤波                                              |  |
|   +----------------------------------------------------------------------------+  |
|                                                      |                            |
|                                                      v                            |
|  [视口渲染与表面层]                                                               |
|   +----------------------------------------------------------------------------+  |
|   | 瞄准视口同步机制 (Aim Viewport Sync):                                      |  |
|   |  - aim.apply 后触发偏移视口确保 (sceneEnsure + sceneCullSurfaces)          |  |
|   |  - 预加载外扩缓冲带 (Lookahead Margin 320px) 杜绝远端黑边与加载空洞        |  |
|   +----------------------------------------------------------------------------+  |
|                                                                                   |
|  [远距战斗与弹道层]                                                               |
|   +----------------------------------------------------------------------------+  |
|   | 屏幕外命中与弹道保障 (Offscreen Combat System):                            |  |
|   |  - 彻底解耦子弹碰撞与摄像机视口 (坚决不用任何视口过滤)                     |  |
|   |  - 弹道走廊威胁穿透唤醒 (Bullet Corridor Active Wakeup)                    |  |
|   |  - 清除 Bullet.run #1069 异常路径，维护完整的世界坐标碰撞判定              |  |
|   +----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

### 方案 1：远端墙体加载与渲染同步（修复黑边与空洞）

#### 1. 视口协同双重确保（Dual Ensure Mechanism）
- **时序重构**：
  在 `SceneAimController.apply()` 完成 `cam.vx` 和 `cam.vy` 的最终位移写入后，**立即调用宿主视口刷新**：
  ```actionscript
  // 在 SceneAimController.apply 结尾执行
  if (w.grafon && w.grafon.sceneLarge) {
      var scale:Number = cam.scaleV > 0 ? cam.scaleV : 1;
      // 以平移后的实际视口进行区块加载与表面裁剪
      w.grafon.sceneEnsure(-cam.vx / scale, -cam.vy / scale, cam.screenX / scale, cam.screenY / scale);
      w.grafon.sceneCullSurfaces();
  }
  ```
- **好处**：
  - 当镜头向前平移时，新的可视区域内的 Chunk 被立刻识别并提交给 `sceneEnsure` 渲染，瓦片和墙体绝不缺失。
  - `sceneCullSurfaces` 使用真实的偏移后视口判定表面可见性，远端已加载的墙体不会被误判为“出屏”而隐藏。

#### 2. 预测性外扩缓冲（Pre-fetch & Lookahead Buffer）
- 瞄准推镜的距离最大可达 700px（纵向 380px）。如果只在屏幕精确矩形内加载，当镜头高速推进时可能遇到单帧同步绘制开销。
- 方案：
  在 `sceneEnsure` 计算 `minX, minY, maxX, maxY` 时，加入**外扩 1 个 Chunk（320px）的预备缓冲范围**；
  同时在 `SceneAimController` 推进过程中，提前向移动方向追加 160px 的前瞻探测量，使区块在真正露在屏幕前已经完成预热，保证 0 黑边、0 闪烁。

---

### 方案 2：基于临界阻尼（SmoothDamp）的平滑镜头动力学

彻底废弃原有的“一阶简单 Lerp + MAX_STEP 硬截断”，升级为现代物理级平滑模型。

#### 1. 临界阻尼动力学算法（Spring-Damper Dynamics）
采用二阶连续性算法（类似 Unity 的 `Mathf.SmoothDamp`），保证位置平滑且速度连续（加速度有限，杜绝冲撞）：
```actionscript
// smoothTime: 达到目标所需的大致时间 (推荐 0.25s ~ 0.35s)
// maxSpeed: 限制最大移动速度 (例如 800px/s)
// dt: 帧间隔时间 (30fps 下约 0.0333s)
private function smoothDamp(current:Number, target:Number, currentVelocity:Number, smoothTime:Number, maxSpeed:Number, dt:Number):Object {
    smoothTime = Math.max(0.0001, smoothTime);
    var omega:Number = 2.0 / smoothTime;
    var x:Number = omega * dt;
    var exp:Number = 1.0 / (1.0 + x + 0.48 * x * x + 0.235 * x * x * x);
    var change:Number = current - target;
    var originalTo:Number = target;

    // 限制最大位移跨度
    var maxChange:Number = maxSpeed * smoothTime;
    change = Math.min(Math.max(change, -maxChange), maxChange);
    target = current - change;

    var temp:Number = (currentVelocity + omega * change) * dt;
    currentVelocity = (currentVelocity - omega * temp) * exp;
    var output:Number = target + (change + temp) * exp;

    // 防止越过目标点振荡
    if ((originalTo - current > 0.0) == (output > originalTo)) {
        output = originalTo;
        currentVelocity = (output - originalTo) / dt;
    }
    return { pos: output, vel: currentVelocity };
}
```

#### 2. 参数设计与手感调优
- **平滑时间（Smooth Time）**：
  - **推进（Aim In）**：设为 `0.28s`（约 8–9 帧），形成柔和自然的推镜推进，起步平缓（Ease-In），中段加速，收尾柔顺（Ease-Out）。
  - **回中（Aim Out / Release）**：设为 `0.20s`（约 6 帧），保证松开或退出时快速恢复正常视野，不拖泥带水。
- **加速度与极速软约束**：
  - 最大速度软限制设为 `1200 px/s`（单帧位移约 40px），完全由阻尼物理曲线收敛，不再有 50px 的突兀切角。
- **输入滤波**：
  - 对鼠标相对于屏幕中心的距离引入二次幂平滑，死区设置为 `160px`，并在死区边缘应用平滑过渡（Smoothstep），消除鼠标微动引起的镜头神经质晃动。

---

### 方案 3：注视方向锁定与自由移动射击解耦（Decoupled Aim & Movement）

这是用户体验优化的核心灵魂：**将“镜头朝哪个方向推远”与“鼠标准星当前瞄准哪里”彻底解耦！**

#### 1. 注视朝向锁定与稳定视野（Directional Look Anchor）
- **核心逻辑**：
  - 玩家激活瞄准时，算法根据鼠标相对角色（或屏幕中心）的朝向，提取出一个**注视方向单位向量**（`dirX, dirY`）。
  - 镜头推移的目标偏移量 `tx, ty` 依据该朝向延展至最大距离：
    `tx = dirX * MAX_LOOK_DISTANCE;`
    `ty = dirY * (MAX_LOOK_DISTANCE * 0.6);`
  - **关键差异**：鼠标不需要死死贴在屏幕最边缘！
    只要鼠标保持在该朝向的半球区域（例如玩家看向右方，鼠标在右半屏活动），**镜头就稳定保持在右方最大视野处，绝不缩回**！
  - 只有当鼠标明显反向（例如移到了玩家身体左侧超过死区阈值）或者松开瞄准时，镜头才平滑平移至新方向或归中。

#### 2. 视野内自由射击（Free Aim Crosshair）
- 当镜头延展到远处后，鼠标指针作为纯粹的**武器射击十字准星**：
  - 无论鼠标移动到屏幕上方的敌人、下方的敌人、还是中央的掩体，鼠标都在直接控制 `w.celX, w.celY`（世界坐标精准逆算已支持：`(cam.celX - cam.vx) / scaleV`）。
  - 玩家可以在宽广的延伸视野内，从容地用鼠标微调准星、点击左键射击敌人，而**镜头不会因为鼠标回到视野中央而回缩**！

#### 3. 全向移动跟随（Full Movement & Stride Support）
- 玩家使用 WASD 移动角色时：
  - 原生 `Camera.calc` 正常计算玩家世界坐标 `cam.X = player.X * scaleV`。
  - 模组的平滑注视偏移 `offX, offY` 叠加在该基准之上。
  - 表现结果：**摄像机视野始终锚定在“玩家前方 + 固定延展距离”**。
  - 玩家可以一边向后撤步（S 键），一边端着步枪注视前方远处（Aim Look），一边射击逼近的敌人——实现完美的战术风筝与边走边打！

#### 4. 双操作模式：切换（Toggle，强烈推荐）与长按（Hold）
- **切换模式（Toggle Mode，推荐默认开启）**：
  - 按一下 Alt：镜头平滑延展至鼠标指向的远端，进入“远处警戒/注视”状态；
  - 此时左手完全从 Alt 键解放，自由控制 WASD 走位、空格跳跃、R 键换弹；右手专心用鼠标瞄准射击；
  - 再次按 Alt、或者打开 PipBuck / 菜单 / SATS 时，镜头平滑回中。
- **长按模式（Hold Mode）**：
  - 为适应习惯长按的玩家，保留按住 Alt 延展、松开回中的逻辑，但同样享有上述“方向锁定与自由射击解耦”，按住期间在视野内瞄准开火镜头不缩回。

---

### 方案 4：子弹对屏幕视野外敌人命中保障体系

#### 1. 彻底清除非法视口过滤与 `#1069` 异常
- **原则**：坚决禁止任何“按相机视口筛选子弹碰撞目标”的逻辑。子弹碰撞检测必须在整图/真实世界空间进行。
- **实施改动**：
  1. 彻底移除宿主 `Grafon.sceneTick` 中尝试向 `visual.root["sceneCU"]` 写入视口单位的废弃逻辑。
  2. 彻底移除宿主 `Bullet.run` 中尝试读取 `visual.root["sceneCU"]` 并抛出 `#1069` 异常的降级路径。
  3. 保留并优化 `Bullet.run` 对 `loc.units` 的原生遍历，消除每帧数千次 try-catch 异常开销，确保屏外敌人时刻处于合法的受击候选集中。

#### 2. 弹道走廊威胁穿透与即时唤醒（Threat Corridor Penetration）
- 在 `NativeSceneActivity.as` 中，原版调度对飞行子弹设置了威胁走廊：
  ```actionscript
  // impact 走廊计算
  var impact:Number = 40 + Number(p.explRadius);
  threats.push({
      l: Math.min(p.X, p.X + p.dx * 4) - impact,
      r: Math.max(p.X, p.X + p.dx * 4) + impact,
      t: Math.min(p.Y, p.Y + p.dy * 4) - impact,
      b: Math.max(p.Y, p.Y + p.dy * 4) + impact,
      pad: 360
  });
  ```
- **保障机制**：
  - 当子弹飞向屏幕外的休眠敌人时，子弹只要命中敌人的 AABB 物理框，原生 `Bullet.udar(u)` 和 `u.udarBullet(this)` 就会被触发并扣除 HP。
  - `NativeSceneActivity` 在下一轮判定时，由于 `u.hp < r.hp`（受到了伤害），立即将其判定为 `combatSignal = true` 并触发 `urgent = true`，立刻从 `sleeping` 中唤醒，进入交战或警戒状态，避免“敌人被打死了还在休眠”或“无敌假死”现象。

#### 3. 远程弹道参数与射程保护
- 经反编译代码审查，原版普通枪械子弹的默认存活时间为 `liv = 100` 帧，飞行速度 `vel = 15 ~ 35 px/frame`，理论飞行距离为 `1500 ~ 3500px`。
- 瞄准模式延展视野后，交战距离从原先的 600px 扩展至 1200–1800px，绝大多数枪械的弹道完全能够覆盖该射程。
- 对于特种狙击武器或高斯步枪，验证其 `liv` 确保不会在中途意外消散，支持屏外超远距离狙杀。

---

## 三、 详细技术实现路径与代码改动清单

| 模块 / 文件 | 改动性质 | 具体改动内容与技术要点 |
|---|---|---|
| `mods/ContinuousScene/src/SceneAimController.as` | **核心重构** | 1. 算法升级：引入 `SmoothDamp` 临界阻尼平滑，替换原一阶 lerp 与 50px 截断；<br>2. 交互解耦：实现视线朝向向量锁定（Directional Lock），使鼠标在视野内瞄准开火时不缩回视野；<br>3. 视口协同：在 `apply()` 结束时主动调用 `w.grafon.sceneEnsure` 与 `sceneCullSurfaces`，确保远端瓦片与表面即时呈现；<br>4. 优化移动跟随：在 `cam.vx/vy` 上平滑叠加偏移，保持角色 WASD 移动连贯。 |
| `mods/ContinuousScene/src/ContinuousSceneMod.as` | **配置与接入** | 1. 暴露并持久化切换模式配置（`aimToggleMode: true`）；<br>2. 增加平滑时间与延伸幅度微调项；<br>3. 确保 `ENTER_FRAME` 调度链在 `aim.update` 后同步刷新渲染层状态。 |
| `fe.graph.Grafon.as` (宿主补丁) | **清理与确保** | 1. 彻底清除 `sceneCU` 写入废弃代码；<br>2. 为 `sceneEnsure` 增加 1 个 Chunk（320px）的预备缓冲边距，防止极速推镜产生黑边。 |
| `fe.weapon.Bullet.as` (宿主补丁) | **异常清除** | 彻底删除对 `root["sceneCU"]` 的反射读取与 `#1069` 异常回退路径，保证整图与屏幕外单位碰撞 100% 干净执行。 |
| `mods/ContinuousScene/src/NativeSceneActivity.as` | **协同保障** | 确认弹道威胁走廊（Threat Corridor）对瞄准延伸区域的敌人覆盖无遗漏，受击敌人即时唤醒。 |

---

## 四、 验收标准与验证方案

### 1. 确定性夹具与单元验证（Automated & Deterministic Checks）
- **视口加载验证（`SceneAimViewportChecks.as`）**：
  - 构造假世界环境，模拟镜头由 (0,0) 平移至 (700, 380)；
  - 断言 `w.grafon.sceneChunks` 中位于远端 (700, 380) 视口内的所有 Chunk 均已生成，且其 `bitmaps[0..3].visible == true`；
  - 断言无未加载的空白地块（0 黑边漏洞）。
- **动力学平滑验证（`SceneAimDynamicsChecks.as`）**：
  - 采集前 30 帧的瞬时位移与速度，验证初速度从 0 连续平滑加速，加速度平缓，无单帧突变超标（`maxAcceleration < 阈值`）；
  - 验证到达目标位置时平滑收敛，零越界振荡（No Overshoot Oscillation）。
- **解耦操作与射击验证（`SceneAimDecoupleChecks.as`）**：
  - 模拟按 Alt 激活瞄准后，将鼠标移回屏幕中心（模拟瞄准中央敌人）；
  - 断言镜头偏移量保持在目标延伸范围内，未发生回缩；
  - 模拟射击事件，断言开火朝向世界坐标准确指向鼠标当前位置。
- **屏幕外命中验证（`SceneOffscreenHitChecks.as`）**：
  - 运行 `qualification-v6` 夹具，发射子弹穿过屏幕外；
  - 断言屏幕外处于休眠（sleeping）状态的敌对单位正确被子弹命中并扣除 HP，且受击后下一帧状态变更为已唤醒（awake）。

### 2. 游戏内实机主观手感验收
- **场景**：马哈顿废墟（Manehatten Ruins）等大场景。
- **操作项**：
  1. 使用轻机枪/狙击步枪，按 Alt（或切换）开启瞄准，观察远处墙体、门、地面无缝即时加载，无黑边和白块。
  2. 观察镜头延展过程平滑流畅，完全消除急促顿挫感。
  3. 在瞄准延伸视角下，操控角色使用 WASD 移动走位，同时使用鼠标自由瞄准视野内的各个敌人射击，视角稳定不晃荡。
  4. 向视野边界及屏幕外的目标射击，确认子弹精准命中屏外敌人并引发警报与反击。

---

## 五、 实施计划与步骤

1. **第一阶段（视口同步与屏外命中清理）**：
   - 修复 `SceneAimController.apply` 触发宿主 `sceneEnsure` 与 `sceneCullSurfaces`，彻底解决远端墙体不加载问题；
   - 清除宿主 `Bullet.run` 与 `Grafon.sceneTick` 中的 `sceneCU` 异常代码，稳固屏幕外命中底层。
2. **第二阶段（动力学重构与解耦瞄准）**：
   - 实现 `SmoothDamp` 临界阻尼算法，替换一阶 lerp；
   - 实现视线朝向向量锚定与自由准星解耦逻辑，完成移动与射击自由化；
   - 适配切换（Toggle）模式。
3. **第三阶段（自动化回归与实机部署）**：
   - 运行针对视口、平滑度、解耦射击和屏外命中的自动化回归测试；
   - 编译模组 SWF，按治理流程进行本机部署验证并交付用户体验。

---

## 六、 实施记录（2026-11-04，CS 0.9.9）

### 1. 实际落地与方案差异

| 方案条目 | 落地形态 | 与方案的差异及原因 |
|---|---|---|
| 视口同步（方案 1） | `SceneAimController.syncViewport()` 在每次 `apply()` 后调用宿主 `w.grafon.sceneTick()` | 宿主 `sceneEnsure`/`sceneCullSurfaces` 是 private，模组无法直接调用；`sceneTick` 是 public 且内部正好先 ensure 再用同一 `cam.vx` 做 cull，同时让异步预热按平移方向优先排序。**未改宿主 `sceneEnsure` 缓冲**：读部署版 `sceneEnsureUpcoming` 确认它根本没有逐出逻辑（常驻块只增不减），因此不存在"模组补画后被原生 ensure 逐出"的抖动，唯一缺陷是"ensure 用的是未平移视口"——加一次平移后的 tick 即可 |
| 镜头动力学（方案 2） | `spring()`：按帧固定 `dt=1/30` 的临界阻尼积分，速度上限 700/1000/1400 px/s，平滑时间 0.40/0.26/0.17（推进）与 0.30/0.20/0.13（回中） | 未采用 Unity `maxSpeed*smoothTime` 位移钳制（会把 700px 跨距一次截成 286px，反而更冲）；改为只钳速度。`MAX_STEP=90` 仅作安全网 |
| 注视锁定与射击解耦（方案 3） | **边缘定向锚定**：准星在屏幕边缘带（90px）停留 3 帧即锁定方向与距离；之后准星在视野内任意位置瞄准/射击都不缩回；到另一条边缘重新锚定 | 方案原文"半球锥"在实现时被证明与"在延展视野内自由瞄准"冲突：向右延展后，要打角色左侧的目标准星必然指向左半屏，锥形判定会把镜头拽回去。改为"只有主动压边才改向"，并把停留计时改为**跨视野内移动累计**（只有回中或换边才复位），因此探针用自备光标与入口自身调用不会互相清零 |
| 屏外命中（方案 4） | 宿主候选 `9FAB2AEF`：删除 `Grafon.sceneTick` 的视口单位表与 `Bullet.run` 的 `sceneCU` 读取；`Bullet.run` 回到 `loc.units` 全量遍历 | 与方案一致。**尚未部署**（见 §6.4 与并行会话重叠说明） |
| 弹道走廊唤醒 | 未改动 `NativeSceneActivity` | 复核后确认现有威胁走廊+受击 `hp` 下降判据已能唤醒屏外被击中的单位；`qualification-v6`（2026-11-04）已实测休眠目标被屏外弹命中后下一轮 `activity` 唤醒，本轮不重复改动 |

### 2. 顺带修正的两个既有缺陷

1. **`cam.celX` 预移与 `w.celX` 计算重复计数**：0.9.8 先把 `celX` 预移一个 pan 宽度（供下一帧原生 `w.celX=(celX-vx)/scale` 使用，这一步是对的），随后又用**已平移的** `vx` 去算本帧 `w.celX`，等于把 pan 算了两遍。0.9.9 统一为原生同一恒等式：`w.celX=(cam.celX-nativeVx)/scale`，于是"本帧消费方"与"下帧原生算出的值"逐像素一致，且都等于渲染恒等式 `(cursor-vx)/scale`。
2. **同帧二次 `update()` 叠加平移**：探针等调用方会在入口自身调用之后再驱一次；0.9.9 记住自己上一笔写入，识别到"`cam.vx` 仍是上一笔写入值"时回退到平移前的基准，避免平移被叠加成两倍（`double-update-does-not-stack` 夹具覆盖）。

### 3. 验证证据

- **确定性夹具**：`src/tests/SceneAimChecks.as` 重写后 **61/61** 通过（独立 AIR 应用 `remains.cs.aimchecks`，1280×800/1920×1000 假世界，无游戏、无存档）。覆盖：视野内光标不转向、边缘停留 3 帧锚定、锚定后准星在视野内任意位置不缩回、方向重锚、首帧步长（≈20px，远低于旧 154px 硬冲）、逐帧位移上限、零过冲、回中单调、世界边界钳制、七类互锁、切换/长按、自定义组合键、震屏透传、缩放映射、幅度缩放、速度档单调、原生 int 字段写回、视口同步开关、双调用不叠加、渲染/原生双恒等式。
- **隔离实机**（私有桌面、独立 AIR id 与存储、正式 13 模组 + 探针、候选 CS + 候选宿主）：`panned-view-resident` 通过且 `sceneResident 70 → 110`——平移后视口新增的 40 个地块被真实加载并保持可见（旧宿主只 ensure 玩家视口，这正是"远端墙体不加载"的直接证据）；`viewportSyncs 208`、`pan-engaged 616.8px`、`apply-consistent`、`world-map-exact`、回中与光标恢复、`applied 419` 全部通过；真实光标被私有桌面固定在左边缘时按被动模式运行并记录，方向重锚的主动腿只在自备光标模式跑。
- **宿主谱系对照**：`control` 构建（仅部署中的 decal 免取消）**逐字节复现**当前安装的 `1D2004AB`，据此证明候选 `9FAB2AEF` 只改了 `sceneApply`/`sceneTick`/`Bullet.run` 三个方法且类布局不变。

### 4. 交付状态

- **模组已部署**：`release/ContinuousSceneMod.swf` = 0.9.9 `D04CD26A`，备份 `build/backups/ContinuousSceneMod-0.9.8-285625F4-before-aimv2-*.swf`，回执 `state/aim-look-v2-deployment-20261104.json`；`scene.xml` `1CEA74E2` 未动；**需重启游戏生效**。
- **宿主候选未部署**：`build/generated/aimv2-20261104/noscenecu/candidate.swf`（`9FAB2AEF`）。原因：同一时间另一会话（`combat-collision-20261104`）在建 `scu-remove-clean` 与子弹空间网格候选，覆盖同一处宿主改动；避免两边同时替换 `pfe.swf` 互相回退，宿主侧留给该会话按自己的网格方案一并落地。部署命令：`python mods/ContinuousScene/build/generated/aimv2-20261104/deploy_host_noscenecu.py`（脚本自带安装版/候选双哈希校验、备份、原子替换与回读）。
- **仍未做**：玩家主观手感验收（边缘锚定的停留帧数、边缘带宽度、三档速度的实际体感）；武器倍镜联动与受击强制回中。

