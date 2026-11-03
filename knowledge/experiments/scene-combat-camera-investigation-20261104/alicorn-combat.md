# 单只天角兽（UnitAlicorn）交战卡顿 — 只读调查（2026-11-04）

> 任务：`task-2`（只读；未运行游戏/AIR、未构建 SWF、未部署、未改 src/release/game-reference、未 git 提交）。
> 输入源码：`game-reference/decompiled/1.02/src102/scripts/`（下称 `src102/`）；宿主补丁回读源：`mods/ContinuousScene/build/generated/envkey-cache-20261102/host-export/`（其 `candidate-build.json` 记录 `hostSHA256=A9B39CC7…`，即当前部署宿主 A9B39CC7 的回读；本文件所有 `host-export/…` 行号以此为准）。
> 时间口径：`World.fps=30`（`src102/fe/World.as:44`）、`World.maxdelta=9`（`:52`）、瓦片 40×40（`:36-38`）、原版一房 48×25 格 = 1920×1000（`:40-42`）；逻辑每渲染帧执行一次（`fe/MainMenu.as:804-843` 的 `world.step()`）。下文“帧”均指逻辑帧；“每秒”按 30Hz 名义值，掉帧时同秒次数会按比例减少。
> 证据等级：【确证·文件:行号】= 我本轮逐行读到并复算；【已有实测·报告路径】= 工作区已跑过的计时；【推测】= 代码推演的量级，需运行时测量确认。

## 0. 结论摘要（给决策用）

1. **单只天角兽自身的代码没有“每帧几十毫秒”的成本**：其 `control()+animate()` 量级按同图实测约 0.1–0.25ms/帧；飞行中每颗 alilight 弹约 0.2–0.5ms/帧（按既有每弹实测换算）。**不足以单独解释 >100ms 长帧**。
2. 旧方案 §2 的四条“根因”全部需要降级：`findBox` 不是每帧而是**约 0.05–0.6 次/秒**（见 §1 算式），单次约 0.1–0.4ms 量级（`4–10ms` 无实测支撑）；念力滤镜**没有**挂在玩家的 `vis` 上（玩家走 `levitFilter2`→`vis.osn.filters`），且 teleFilter 的 strength=1（与玩家自身 levitFilter1 同 quality=3、更低 strength）；`actPort` 每次只有 ≤8 格碰撞检查（不是“庞大碰撞测试”）；闪电 `tipdec=11` 命中**约 85–90% 免地块重绘**（`decal(null,null)` 在宿主 `sceneApply` 入口就早退），不是“频繁破坏地形”。
3. **剩下唯一有量级能造成“明显/严重”变慢的链条，是警报/目标共享把同阵营、同一房范围内的其它单位拉进 engaged/awake**：每个额外活跃单位既有实测约 +1.5–2.0ms/帧（多敌报告），若有 3–8 个被拉活，就会把 35ms 帧推到 45–60ms，并让“只看见一只天角兽”的玩家感觉“交战即卡”。这是行为放大，不是天角兽函数本身贵。默认接力概率 0 只截断“多跳”，**不阻止**首发者 1920×1000 内的直接唤醒。
4. 次一级是**一次性**事件：真实地块重绘（`fire_soft` 10% 或 tile 被打穿）约 3–8ms/次（既有实测 outer 7.40–7.85ms/次）；念力的滤镜离屏渲染约 0.3–1.5ms/帧（仅 `mater=false` 或被抓的 ~60 帧内）；`actPort` 约 0.1–0.3ms/次（tr=2，约每 11s 一次）。这些都只会造成单帧几十毫秒以内的毛刺，不会造成 100ms 级冻结。
5. **最小验证路线**（§6.3）：先用“只读计数探针”（无需宿主补丁）把单只天角兽战斗的 dt 与 5 类判别计数对齐；只有计数法分不清时，才按既有 `build/combat-profile.py` 模式编一个诊断宿主（wrapper 计时，不部署）。

---

## 1. 必答 1：`control()` 的每帧路径、`aiTCh` 节流、`findBox` 真实周期与遍历规模

### 1.1 每帧无条件执行的部分（在 `sost!=3`、`World.w.enemyAct>0` 前提下）

【确证·src102/fe/unit/Unit.as:1761-1865】`Unit.step()` 每帧固定顺序：`getRasst2()` → `forces()` → **`control()`**(`:1808`) → `run()`（物理/碰撞，可能按 `maxdelta=9` 拆多子步）→ `checkWater()` → `actions()` → `setVisPos()` → `hpbar` 定位 → **`animate()`**(`:1835`) → 遍历 `childObjs` 调 `step()`（武器，含 `Weapon.step`）。
【确证·src102/fe/unit/UnitAlicorn.as:493-1085】`control()` 每帧无条件段（除提前 return）：
- `sost==3`（倒地）只做 `collisionAll()` 并 return（`:497-511`）；
- `levit && stun==0` 时若 `aiState<=1` 触发一次 `budilo()`（`:512-519`）；`stun` 置 `aiTCh=3`（`:520-525`）；
- `t_super`、`t_pole`（每 5 帧发一次 unlock 粒子）、`invis/dexter`、`mana+=resmana`（`:526-566`）；
- `World.w.enemyAct<=0` 直接 return（`:567-570`）；
- `t_shit` 递减与 `castShit()` 判定（`:571-578`）、`t_alarm` 援兵倒计时（`:579-586`）、`allVulnerMult`（`:587-594`，仅整数比较）；
- `aiTCh` 递减（`:595-598`）与 `celDX/celDY/porog/vision/celX/celY/maxSpeed` 重算（`:698-736`）；
- `stay/isFly/levit/fall` 运动分支（`:736-867`）；
- `attKorp(celUnit,…)`：仅当 `celUnit` 且 `celDX∈±optDistAtt(200px)`、`celDY∈±80` 时每帧调用（`:1008-1013`），但玩家侧 `neujaz` 冷却 20 帧（`Unit.as:392,4125-4135`），实际约 1.5 次/秒；
- 开火触发（`:1014-1025`，见 §4）、`++t_tele` 与念力持握/抛出（`:1026-1084`）。

`animate()`（`:269-384`）每帧：动画状态选择 + 动画帧步进/`blit()`（仅动画帧变化时 `copyPixels`，`Unit.as:323-327,2863-2868`）、`visshit` 可见性、隐身 `curA/vis.alpha`、`visBmp.filters` 维护（仅数组长度变化才赋值，见 §2）。

### 1.2 `aiTCh` 节流（周期是从代码直接读出的）

【确证·src102/fe/unit/UnitAlicorn.as:595-647】`aiTCh` 每帧 -1；归零时按状态回填：
- `aiState<=1`（闲逛）：`aiTCh = random(50)+40`，即 **40–89 帧（1.3–3.0s）**；
- `aiState>1`（警戒/交战）：`aiTCh = random(100)+100`，即 **100–199 帧（3.3–6.6s）**。

在该计时器上取模的三处：
| 门控 | 条件 | 语义 | 约合 |
|---|---|---|---|
| 感知块 | `enemyAct>1 && aiTCh%10==1`（`:648`） | 眼位、悬浮浮动、`unsit`、`collisionAll`（仅 `!mater` 时）、**`findCel()`**、`telepat()`、`aiSpok` 增减 | 每 10 帧一次 ≈ **3 次/秒** |
| 目标共享 | 感知块内 `aiTCh%30==1`（`:675`） | `telepat()`（把 `celUnit` 分给同阵营无目标者） | 每 30 帧 ≈ **1 次/秒** |
| 开火触发 | 每帧判定，但 `aiTCh%5==1 && isrnd(0.25)`（`:1014`） | 只在这里设 `aiAttackT=16`，随后 15 帧内调 `currentWeapon.attack()` | 平均 **1/20 帧**≈1.5Hz 的“可触发窗口” |

`isrnd(p)=Math.random()<p`【确证·src102/fe/unit/Unit.as:4855-4858】。

### 1.3 `findBox` 真实调用频率（按 `t_tele` 逻辑算出，不是每帧）

【确证·src102/fe/unit/UnitAlicorn.as:55,57,117,163,1026-1084】

```
t_tele 初值 -100（构造，:117）
每帧 ++t_tele（:1026）
if t_tele == 0:
    if aiState <= 1  → 不调用 findBox（|| 短路），t_tele = -(50..149)     // :1029
    else if findBox() == null → t_tele = -(50..149)                       // :1029-1032
    else                     → 保持 0，teleObj 已抓取                     // :1033
if teleObj != null:
    if t_tele >= tTeleThrow(60) → celUnit? throwTele()           // :1066-1072
                                    否则 dropTeleObj()
                                  t_tele = -tTeleRes             // 默认 600；tr=2 型 400（:57,163）
      若 teleObj.levit==1 被外力解除 → dropTeleObj(); t_tele = -tTeleRes // :1079-1083
    若 celUnit 在抛出前丢失 → dropTeleObj(); t_tele = -tTeleRes/2         // :1073-1077（300；tr=2 为 200）
安全网：t_tele >= tTeleThrow+10 (70) → t_tele = -(50..149)                // :1034-1037
```

由此得周期（30Hz）：

| 情形 | 帧数 | 时间 | findBox 调用率 |
|---|---:|---:|---:|
| 成功抓取且抛出时仍有 `celUnit`（默认型） | 60+600 = **660** | **22.0s** | 0.045 次/秒 |
| 同上，tr=2 型（`tTeleRes=400`） | 60+400 = **460** | **15.3s** | 0.065 次/秒 |
| 抓到了但抛出前 `celUnit` 丢失 | 60+300 = 360（tr2: 260） | 12.0s（8.7s） | 0.083 次/秒 |
| `findBox` 返回 null（失败退避） | 1+(50..149) = **51–150** | **1.70–5.00s** | **0.20–0.59 次/秒（最坏）** |
| `aiState<=1`（不交战） | 50–149 | 1.7–5.0s | **0 次**（不调用） |

另外，`findBox` 只在 `celUnit` 或 `loc.objs` 里随机命中时才结束“等待”，且第一分支只有 `isrnd(0.25)` 会直接抓玩家（`:1143-1152`）——通常要 4 个周期左右才抓到玩家。**结论：60 秒连续交战中 `findBox` 约 4–15 次（最坏连续失败 ≈35 次），即 0.05–0.6 次/秒，不是“高频/每帧”。**

### 1.4 `findBox` 单次遍历规模与 `isLine` 上限

【确证·src102/fe/unit/UnitAlicorn.as:1140-1168】遍历 `loc.objs` 一次，逐物体检查 `levitPoss && wall==0 && levit==0 && massa>=1 && isrnd(0.3)`，再查 `getRasst2<=optDistTele²(=600²=360000)`，最后才 `loc.isLine(...)`（命中即 return）。`Obj.levitPoss` 默认 true（`src102/fe/Obj.as:32`），只有 `wall>1` 的箱子置 false（`src102/fe/loc/Box.as:390-393`）。

【确证·src102/fe/loc/Location.as:2366-2386】`isLine` 是分段采样：步数 = `floor(max(|dx|,|dy|)/maxdelta)+1`（`maxdelta=9`）；600px 上限 → **≤ floor(600/9)+1 = 67 步**，每步一次 `getAbsTile`（两次除法+数组下标，`:2331-2338`）和 4 个边界比较。**不存在“DDA 全网格扫描”。**

遍历规模：任务背景与旧方案口径为 1200+ 物体；工作区可核到的实测下界是 **600 个箱子**（合并大场景，见 `knowledge/experiments/dense-combat-near-native-20261023.md:121,127`）与**603 个 backobjs**（手工大图，`src/ContinuousSceneFactoryProbe.as:150,199,201`）。按既有“600 个箱子整段 step 只花 0.207–0.307ms/帧”的实测（同报告 `:121`），单次 1200 物体的**纯属性遍历 ≈0.1–0.3ms**；`isrnd(0.3)` 先筛掉 70%，实际 `isLine` 只对“距离 ≤600px 且通过属性筛”的少数物体执行，现实约几到几十次 × ≤67 步 ≈ **0.05–0.3ms**；只有“1200 个候选全部落在 600px 内”这种不现实情形才会逼近 1200×0.3×67 步的理论上限（也仅 1–3ms 级）。**旧方案“单次 4–10ms”没有实测支撑，且调用率被高估约 2 个数量级。**

---

## 2. 必答 2：念力滤镜 —— `teleFilter` 施加给谁、`nomaterFilter` 何时长期存在、Flash 侧每帧多做什么

### 2.1 `teleFilter`（`GlowFilter(tlColor,1,6,6,1,3)` → blur 6×6、strength 1、quality 3）

【确证·src102/fe/unit/UnitAlicorn.as:226,1148-1150,1177-1180,1196-1199】
- **被抓的是玩家（`UnitPlayer`）**：`findBox` 的第一分支把 `celUnit` 交给 `upTeleObj`，`upTeleObj` 走 `(teleObj as UnitPlayer).levitFilter2 = teleFilter`（`:1146-1150`）——**不是 `vis.filters`**。真正生效要等玩家自己的 `UnitPlayer.setFilters()` 在 `f_levit` 为真时把 `[levitFilter2]` 赋给 `vis.osn.filters`（`src102/fe/unit/UnitPlayer.as:4093-4101,4143`）；触发条件是 `levit>=1 && fracLevit != fraction`，并且 `UnitPlayer.animate()` 在 `levit>0` 期间**每帧**调用 `setFilters()`（`:4656-4679`）。所以玩家的滤镜绑定对象是**整个骨骼容器 `vis.osn`**，不是 `vis`。
- **被抓的是非玩家单位**：`teleObj.vis.filters = [teleFilter]`（`:1177-1180`）；`dropTeleObj()` 时清空（`:1196-1199`）。
- **被抓的是箱子（`Box`，findBox 主循环的绝大多数结果）**：`upTeleObj` 的 `!(teleObj is UnitPlayer) && teleObj.vis` 分支同样把滤镜挂到**箱子自己的 `vis`**（`:1177-1180`）。
- 持握期间 `control()` 每帧用 `teleAccel` 改 `teleObj.dx/dy`（`:1038-1065`）；抓住到抛出之间是 **60 帧（2.0s）**（§1.3），只有这 60 帧内滤镜存在；抛出击中/落地后 `throwTele→dropTeleObj` 立即清空。
- 旁证（非天角兽路径）：玩家自身悬浮用的是 `levitFilter1`（alpha 从 0 渐升、strength=2、quality=3，`UnitPlayer.as:370,4675`），被抓时换成 alicorn 的 `teleFilter`（alpha=1、strength=1、quality=3，`UnitPlayer.as:371`）——**不存在“被抓时比原生悬浮更贵”的证据：同 quality、更低 strength**。

### 2.2 `nomaterFilter`（`GlowFilter(nmColor,1,15,5,2,3,inner=true,knockout=true)`，**quality=3**，blur 15×5，strength 2）

【确证·src102/fe/unit/UnitAlicorn.as:225,376-383,1095-1100,803-806】
- 仅在 `mater==false`（“非实体/穿墙相位”）时挂到**天角兽自己的 `visBmp`**（`Bitmap`，底图 `BitmapData` 尺寸 **150×150**，来自 `AllData.as:652-667` 的 `sprX/sprY=150` 与 `Unit.as:2833-2861`）。`mater=false` 由 `castNomater()` 设置（`:1095-1100`），进入条件是：飞行中、`aiSpok>10`、`celUnit==null`、`(turnX!=0 || turnY!=0)`（撞到阻挡时由碰撞逻辑置位）且 `t_nomater` 累计 **30 帧**、`mater && t_gotov>=0`（`:800-806`）；`t_gotov` 被设为 `tNomater=-200` 防止连续触发（`:43,1099`）。
- 恢复成实体只在感知块里检查：`!mater && !collisionAll()`（每 10 帧一次，`:667-670`），另在 `sost==3` 分支（`:501-505`）。所以**只要天角兽还在几何体内（`collisionAll()` 为真）且每 10 帧那一次检查没通过，`mater=false` 会长期存在**——这是它唯一“长期存在的滤镜状态”。正常飞越墙体时通常数十帧内恢复（穿过去后 `collisionAll()` 变假）。
- 动画帧变化会改 `visData`：`fly` 动画 `len=14, df=1`（`AllData.as:663`；`BlitAnim.step` 每帧 +1，`src102/fe/serv/BlitAnim.as:3715-3733`），飞行时 `blit()` 每帧 `copyPixels`（`Unit.as:2863-2868`）→ 滤镜源的 **BitmapData 内容逐帧变化**。

### 2.3 Flash 侧每帧到底多做什么（分级）

- 【推测】以 AIR/SWF CPU 软光栅的常见行为：滤镜结果按对象局部空间缓存；**单纯平移不会每帧重做高斯卷积**，只有内容/参数变化才失效。因此：
  - `nomaterFilter`：在 `mater=false` 且**飞行动画逐帧换帧**时，失效频率≈30 次/秒，重绘区域约 **(150+2×15)×(150+2×5)=180×160**，quality=3、strength=2、inner+knockout —— 是本天角兽全部滤镜里最贵的一条，粗估 **0.3–1.5ms/帧**（仅在这种相位内；静止 `stay`（默认 len=1）不换帧时不重做）。
  - 玩家 `levitFilter2`：绑定 `vis.osn`（矢量骨骼容器，约 50–80px 见方），blur 6×6、strength=1、quality=3；且 `UnitPlayer.animate` 在悬浮期间**每帧重新赋值 `filters` 数组**（`UnitPlayer.as:4673-4679`）——若运行库按数组身份判定失效，则每帧重做；这是**被抓的 ~60 帧**内的开销，粗估 **0.1–0.5ms/帧**。注意：玩家自己悬浮时走同一逐帧 `setFilters()` 路径（`levitFilter1`，strength=2、quality=3），所以这不是天角兽独有的机制，只是被抓时换了滤镜实例/参数（更低的 strength）。
  - 被抓箱子 `vis.filters`：箱子 `vis` 尺寸取决于实体美术（常见 40–120px），blur 6×6、strength=1、quality=3；箱子持握期间位置每帧被改但内容多为静态 → 多数情况只付合成、不重做卷积（【推测】；若箱子 `vis` 是时间轴动画则另计）。
- **滤镜会导致“全屏重绘”的说法没有依据**：本轮没有任何代码线索能让滤镜影响相机/全屏容器；受影响对象最大也只有 180×160（天角兽自身）或玩家骨骼容器。

---

## 3. 必答 3：`actPort` 的触发条件、循环次数与 `collisionAll` 量级

### 3.1 触发条件

【确证·src102/fe/unit/UnitAlicorn.as:415-429,1102-1129,153-167】
1. **受击紧急瞬移**：`damage()` 中 `tr==2 && osob && !blasted && param3 && param3.weap && param3.weap.owner.player && aiState<=1` → `actPort(true)`，`blasted=true`，**并 `return 0`（本次伤害无效）**（`:422-427`）。每只天角兽一生（直到 `setNull()` 重置 `blasted=false`，`:481`）只触发一次。`osob` 是构造器里按 `tr` 抽的概率（tr=2 为 50%，`:157-168`；难度 4 强制 true，`:181-184`）。
2. **大招瞬移**：`superSila()` 在 `superSilaTip==2`（即 tr=2）时：`aiState==2 → actPort()`；`aiState==3 && (rasst2<200² || isrnd()) → actPort()`（`:1109-1119`）。`superSila` 的触发是在警戒状态（`aiSpok>0`）下 `++t_gotov > tGotov(90)`（`:727-735`），成功后 `t_gotov = tUsed*(0.8..1.2)`，tr=2 的 `tUsed=-250`（`:164`）→ 下一次约 **(90+250)=340 帧 ≈ 11.3s**；默认型 `tUsed=-500`（`:39`）→ ≈590 帧 ≈ 20s（但默认型 `superSilaTip=1`，其 `superSila` 只是隐身，不瞬移）。
3. 另外 `superSilaTip==1`（默认型，tr=0/1/4…6）：`superInvis=true; isVis=false` 的**隐身循环**（`:1104-1108,1131-1138`）；`superSilaTip==3`（tr=3）：调用 `psyWeapon.attack()` 发一发 psy 弹（`:1120-1126`）。

### 3.2 循环次数与每次尝试的代价

【确证·src102/fe/unit/UnitAlicorn.as:1248-1317】`while(_loc5_ <= 20)`，最多 **20 次尝试**：
- 第 1–4 次（`_loc5_ < 5 && !param1`）：玩家左右 200–500px；第 5–9 次：200–1000px；第 10–20 次：`Math.random()*loc.limX/limY` 全图随机（紧急瞬移 `param1=true` 时直接走全图随机）。
- 每次尝试：坐标对齐到 40px 格 → 4 个边界钳制 → **`collisionAll(_loc3_-X, _loc4_-Y)`**（`:1303`）。`collisionAll`（`src102/fe/unit/Unit.as:2541-2566`）只遍历**平移后身体 AABB 覆盖的瓦片**：天角兽 `sX=70,sY=100`（`AllData.as:653`）→ 70px 地平跨度最多跨 3 列、100px 竖直跨度最多 4 行，即每次尝试 **≤12 次 `collisionTile`**（`Unit.as:2568-2583`：4 个比较+属性读）。**20 次全失败也只有约 240 次瓦片检查**，量级 ≈0.03–0.08ms。
- 成功才 `teleport(x,y,1)`（`Unit.as:2804-2826`）：发两个粒子 `tele`（`kol=30`）和 `teleport`（各是一次 `Emitter.cast`，`Emitter.as:154-188` 每个 `new Part`），重置武器位置/`currentWeapon.setNull()`，然后 `findCel(true)`（`look()` 受视野距离平方的早退约束，`Unit.as:4560-4641`，最长不过百来步）。粗估整次 `actPort` **0.1–0.3ms**（【推测】；粒子创建占大头）。
- 行为提醒：紧急瞬移在**大场景里会瞬移到全图随机空闲格**（`:1280-1284`），可能直接离开玩家视野→“敌人不见了/战斗重置”，这是玩法/观感问题，**不是 CPU 脉冲**。

---

## 4. 必答 4：`alilight` 的字段含义、每秒发弹量、每发的视觉对象、命中后真正重绘的概率

### 4.1 字段逐条（数据在 `src102/fe/AllData.as:684-690`）

| 字段 | 值 | 实际含义（确证） |
|---|---|---|
| `rapid` | 35 | 开火冷却/射击间隔计时，单位=帧（`Weapon.as:126,1325`；“每秒发弹”换算用 `30/rapid`，见 `Weapon.as:2051-2052`）。不是 DPS 显示里的“射速极高”。`auto = rapid<=6` → alilight 为 false（`:856`），即非自动武器，但 AI 每帧仍可调 `attack()`。 |
| `prep` | 12 | 蓄力值：每次 `attack()` 调用 `t_prep += 2`（上限 `prep+10`，`Weapon.as:1317-1320`），达到 12 才把 `t_attack` 置为 `rapid`；同时武器美术 `vis.gotoAndStop(t_prep)` 做蓄力帧（`:1974-1990`）。 |
| `destroy` | 50 | 子弹的 `destroy`（`Weapon.setBullet` → `Bullet.destroy`，`Weapon.as:1666-1673`）；命中瓦片时作为 `Location.hitTile(tile, 50, …)` 的伤害参数（`Bullet.as:489`）。 |
| `tipdec` | 11 | `Bullet.tipDecal`（`Weapon.as:1669`）→ `hitTile(...,param5=11)` → `Grafon.dyrka(...,11,mat,…)` 的贴花/破坏类型码。11 落在“≥11 且 ≤13 的 special”段（见 §4.4）。 |
| `vbul` | lightning | `Weapon.applyXml` 里 `vBullet = getDefinitionByName("visbul"+visbul)`（`Weapon.as:511-524`）→ 类 **`visbullightning`**（`src102/visbullightning.as`，assets.swf 符号 4065 的 MovieClip）。每发一颗子弹 = 1 个该 MovieClip。 |
| `bulanim` | 1 | `bulAnim=true`（`Weapon.as:615-620` 附近 applyXml）→ 发射时 `this.b.vis.play()`（`:1560-1563`），即子弹贴图会播时间轴。 |
| `speed`/`deviation` | 50 / 7 | 弹速 50 px/帧、散布 7°（`:686`）；`maxdelta=9` → 每帧拆 **`ceil(50/9)=6`** 次 `Bullet.run()` 子步（`Bullet.as:199-206`）。 |
| `tipdam` | 9 | 伤害类型 = `D_SPARK`；命中目标时 `udarUnit` 额外发 `moln` 电击粒子+`electro` 音效（`src102/fe/unit/Unit.as:4177-4184`）。 |
| `noise` | 800 | 每次开火 `owner.makeNoise(800,true)`（`Weapon.as:1578-1582`）；`makeNoise` 只更新计数/可能发一个 `noise` 粒子，**不遍历单位**（`Unit.as:3240-3265`）。 |

### 4.2 每秒发弹量（按 AI 实际门控算，不是 `30/rapid`）

【确证·src102/fe/unit/UnitAlicorn.as:1014-1025,1008-1013；src102/fe/weapon/Weapon.as:1180-1196,1279-1337】
- 开火触发：`celUnit && t_shit<900 && aiTCh%5==1 && isrnd(0.25) && aiAttackT<=-15 && currentWeapon.t_attack<=0` → `aiAttackT=16`；随后连续 15 帧调用 `attack()`（`aiAttackT` 从 16 递减到 0，仅 `>0` 时调用）。
- `attack()` 每帧 `t_prep+=2`；第 **6 次调用**（触发后第 5 帧）`t_prep=12` 且 `t_attack<=0` → 置 `t_attack=35`；同一帧末尾 `Weapon.step()` 看到 `t_attack==rapid` → **立刻 shoot()** 并递减到 34（`Weapon.as:1180-1196`）。之后 `t_attack` 每帧 -1，**第 35 帧回到 0** 才允许下一个 `aiAttackT<=-15 && t_attack<=0` 触发。
- 触发等待：冷却结束后还需 `aiTCh%5==1`（1/5 帧）∧ `isrnd(0.25)`（1/4）→ 几何分布，期望等待 **20 帧**，最短 1 帧。
- 所以单发间隔 ≈ `35(冷却) + 5(蓄力6次调用跨5帧) + W(期望20，最短1)` ≈ **41–~100 帧**；典型 **≈60 帧 = 2.0s/发 → 0.4–0.5 发/秒**，理论上限 **≈40 帧 → 0.75 发/秒**。60 秒约 **24–45 发**。
- 补充：tr=3 型另有 `psyWeapon`（`alipsy`：rapid=5 但**只在 `superSila()` 里调用一次 attack()**，见 `UnitAlicorn.as:1120-1126`），按 `t_gotov` 节奏约 **1 发/20s**——`rapid=5` 不产生 6 发/秒。tr=1 型的大招是隐身，不是射击。

### 4.3 每发的视觉/对象增量

【确证·src102/fe/weapon/Weapon.as:1461-1477,1599-1621；src102/fe/weapon/Bullet.as:135-168,208-239；src102/fe/loc/Location.as:2271-2293】
1. **1 个 `visbullightning` MovieClip**（`new` 在 Bullet 构造器内）+ 1 个 `Bullet` 逻辑对象；子弹加入 `loc` 对象链并在 `loc.active` 时 `addVisual()`（即上显示层）。`kol=1`（默认），无 `tracer`/`shell`/`grav`/`flame`。
2. 武器自身 `vis.gotoAndPlay("shoot")`（复用已有对象，不新建）。
3. 命中地形时：`tipDecal=11 > 6` → 走 `else if(flare!="")`，若 `mat>0` 发 **1 个 `spark` 粒子**（`flSpark`，`minliv=3`，`AllData.as:6966`）；音效 1 次。
4. 命中单位时：`udarUnit` 的 spark 分支发 1 次 `moln` 粒子 + `electro` 音效（对玩家还要加 `horror/vote/disorient` 三选一的**状态效果**，`UnitPlayer.as:3251-3267`，效果只是属性修正，不是屏幕滤镜）。
5. 子弹最多存活 `liv=100` 帧（3.3s）后自动 `remObj`（`Bullet.as:240-263`）。

**合计：每发约 1 个显示对象 + 最多 1 个粒子 + 1 个音效。数量级远小于 LMG/霰弹类武器。**

### 4.4 命中后真正触发“地块重绘”的概率（关键：`decal(null,null)` 早退）

【确证·宿主回读 host-export/fe/graph/Grafon.as:4455-4659、4661-4734、1085-1159；src102/fe/loc/Location.as:2501-2570；src102/fe/loc/Tile.as:22,24,340-348；src102/fe/weapon/Bullet.as:476-493】

调用链：`Bullet.run` 进到实体瓦片 → `Location.hitTile(tile, destroy=50, X, Y, tipDecal=11)` →
- `destroyOn` 默认 true（`Location.as:209`），所以不走 `!destroyOn && hp>500` 的“只看贴花”分支（`:2511-2518`）。
- `Tile.udar(50)`（`Tile.as:340-348`）：若 `indestruct` 或 `thre>50` → false；否则 `hp-=50`（默认 hp=1000，`Tile.as:22`，`thre` 默认 0，`:24`）。hp 未破 → `dyrka(...,mat,tipDecal=11,false,ratio)`（`:2555-2561`）；没被伤害 → `dyrka(...,true,ratio)`（`:2563-2569`）；hp 破 → `isRebuild=true` + `tileDie(...)`（`:2519-2553`）。
- `dyrka`（host-export:4455-4659）：`mat==0` 直接 return（`:4463-4466`）；`param3==11` 只命中末尾 `if(param3 == 11)` 分支（`:4583-4589`）——**只有 `Math.random()<0.1` 时 `_loc8_=fire_soft`**，否则前后景类都是 null。
- `decal(front=null, back=null, …)`：在未进入绘制前、`sceneApply` 入口即 `if(kind=="decal" && args[0]==null && args[1]==null) return;`（host-export:1093-1096）——**不计算 bounds、不 cancel warm、不 push sceneMarks、不进 chunk 循环**。只有 10% 的 `fire_soft` 才会走到真实绘制（`sceneApplyCompactDecal`，`:878-924`；里面最多按相交的 chunk 各分配一块临时 BitmapData（≤320×320）做局部重绘；`sceneApply` 的 chunk 循环 `:1125-1146`；绘制本体 `sceneDecalPaint` `:1011-1043`）。
- 打穿瓦片（hp 归零）时 `tileDie` 走 100% 真实贴花（`decal(block_dyr,block_bur,…)`，host-export:4368-4453，`_loc3_=block_dyr,_loc4_=block_bur`）并置 `isRebuild`（下一帧 `Location.step` 里 `rebuild()`，`Location.as:2601-2605,3407-3410`；若 `loc.black` 还会多一次 `lighting()`，`:3394-3404`）。默认 hp=1000、每发 50 → **同一格挨 20 发才破**。

**结论：`tipdec=11` 的地形命中约 90%（+ `mat==0` 时 100%）免重绘；约 10% 触发一次 `fire_soft` 真实贴花；只有同格累计 20 发左右才发生一次“破坏→100% 重绘 + isRebuild”。60 秒按 24–45 发、假设一半打墙 ≈ 12–22 次地形命中 → 真实重绘约 1–3 次/分钟（再加极少数破格）。**

量级参考（【已有实测】）：`knowledge/experiments/dense-combat-near-native-20261023.md:131` 的 `hitTile` 单次 ≈6ms（高射速 LMG 场景，含真实弹痕绘制）；`:139` 的 decal outer 每次 **7.40–7.85ms**、`scenePaint` 每次 **2.89–3.19ms**。把 6ms 直接套到 alilight 会高估约 10 倍（90% 早退），真实约 **0.6–0.8ms/发**平均、单次真实重绘 **3–8ms**。

---

## 5. 必答 5：`budilo/telepat` 补丁后的剩余循环成本（`loc.units` 规模）

【确证·mods/ContinuousScene/src/patches/SceneAlicornAlerts.as.inc:8-67；mods/ContinuousScene/build/alicorn-alerts.py:37-54；mods/ContinuousScene/src/SceneAlicornAlerts.as:15-33；src102/fe/unit/UnitAlicorn.as:386-413】

- 补丁后 `budilo`/`telepat` 仍然 **`for each(_loc2_ in loc.units)` 全表遍历**（没有空间索引），只是对“实际通知谁”加了条件：第一跳发送者居中 **±960 X / ±500 Y**（= World.cellsX*tileX/2 等，`:17-18,31-35,47-57`），另有 `sceneNativeCall("alicornAllow"/"alicornReceive"/"alicornClear")` 跨 SWF 判定/记账（`:19,49,61-62`；`ContinuousSceneMod.as:59-60` 注册）。
- 规模：合并大场景实测 `loc.units` 约 **130–159**（【已有实测】`knowledge/experiments/multi-enemy-stutter-20261101.md:28` “~130 个单位”；`knowledge/experiments/motion-v082-20261019.md:51` “固定同世界 159 单位”）。每次广播的循环体是“自身排除 + fraction/sost/unres 三个比较 + 范围 4 个比较”，无 `isLine`/无 alloc；按 160 次 × 每迭代约 0.1µs 粗估 **≤0.02–0.05ms/次**（【推测】；`sceneNativeCall` 的 `getChildByName`+`Function.apply` 另有每次数 µs–数十 µs）。
- 频率：`budilo` 只在“`aiSpok>=maxSpok` 且 `aiState!=3`”的决策帧（`aiTCh` 归零，每 100–199 帧）或被念力抓住/死亡时调用（`UnitAlicorn.as:631-637,512-518,456`）；`telepat` 在感知块内每 30 帧一次（§1.2）。稳定交战时总和 **≤约 1.3 次/秒**。
- **残余成本量级 ≈0.02–0.1ms/s，可忽略**。真正需要注意的不是循环，而是**广播/目标共享把哪些单位拉进了活动集合**（见 §6 排序第 1）：`NativeSceneActivity.update` 把 `u.celUnit!=null` 直接当 `combatSignal` → `engaged=true` 并 urgent wake（`src/NativeSceneActivity.as:49-50,91-96`），被共享目标的单位在 2200×1600  leash 圈内会**一直保持活跃**（`:55-57,69-75`）。
- 另：`alicorn-alert-static-20261021.md:25` 说 engaged“没有随后自动清除的路径”已过时——0.9.6 起有 150 帧 + 2200×1600 的脱战拴绳（`NativeSceneActivity.as:18,52-57`）；这条旧断言应降级为“部分失效”。

---

## 6. 必答 6：可疑源排序、判别性诊断、最小验证路线

### 6.1 排序（按“单只天角兽交战 1–2 分钟内对帧时间的预期贡献”）

**A. 警报/目标共享导致的“同房同伴被拉活”（唯一有量级的链条）** — 预期 **+1.5–2.0ms/帧/额外活跃单位**（【已有实测】`multi-enemy-stutter-20261101.md:12-22`：12 敌战斗静止 56.8ms、每敌 +1.50–1.96ms；3 敌 +1.67ms/敌）；若同房有 3–8 个同阵营单位被 `telepat` 写入目标并紧急唤醒，帧时间会从 ~35ms 抬到 45–60ms，并且这些单位之后按 leash 规则长期活跃。**天角兽函数本身不贵，贵的是被它“叫醒”的集合**。默认接力 0% 只阻断“接报者再转发”，不阻断首发者房内直接通知（`SceneAlicornAlerts.as.inc:31-35,56-64`）。
**B. 一次性真实地块重绘** — 预期 **3–8ms/次**（§4.4 实测外推），alilight 下约 **1–3 次/分钟**；若部署宿主**没有** `sceneApply` 的 `decal(null,null)` 早退，则升为 **~6ms × 12–22 次/分钟**，且每发都可能毛刺。**这是必须先确认的部署事实。**
**C. 念力滤镜离屏渲染** — 预期 **0.3–1.5ms/帧**（仅 `mater=false` 相位，或玩家被持握的 60 帧内）；不会造成长帧，但会让持续帧时间上浮。
**D. `actPort`/瞬移与 superSila** — 预期 **0.1–0.3ms/次**（tr=2 约每 11s 一次）；主要影响是行为（瞬移脱战/瞬移回来），不是 CPU。
**E. alilight 自身弹体与视觉对象** — 预期 **0.2–0.5ms/帧/在飞弹**（既有实测每弹·帧 ≈0.44ms 已含其分段的单位遍历，见 `dense-…-20261023.md:120`；alilight 每帧 `ceil(50/9)=6` 个子步，量级同阶）；同时最多 1–3 发在飞，合计 ≤1–1.5ms/帧。
**F. `findBox` / `budilo` / `telepat` 循环本身** — 单次 `findBox` ≤~0.5ms、单次广播 ≤~0.1ms，频率分别 ≤0.6 次/秒、≤1.3 次/秒 ⇒ **合计 ≪1ms/s**（§1.3/§5），排序最后；旧方案的“首要元凶”不成立。

> 注意（不重复已否定的路线）：若 B 类最终成立，修的是宿主 `sceneApply`/重绘调度本身；**不要重提“弹痕待应用缓冲”**——工作区已有 196 事件配对 **0/29 同块**的证据把该方向降级（`state/MEMORY.md:26`）；同理，炮塔同帧守卫、环境键缓存、GC 减分配均已实测无帧收益（`state/MEMORY.md:14,80,84,92`），本调查不把它们列为候选。

### 6.2 判别性诊断表

| 可疑源 | 预期量级 | 判别性计数/计时（一次 1–2 分钟战斗内可区分） | 最小验证步骤 |
|---|---|---|---|
| A 警报唤醒链 | +1.5–2ms/帧 × 额外活跃单位 | 逐帧：`loc.units.length`、`NativeSceneActivity.stats().awake/asleep/leashed`、`u.celUnit!=null` 的敌数、fraction=1 的 `id` 列表；把 dt>50ms 帧与 awake 跳变对齐 | 在**正式 CS 大场景**里打一只天角兽，探针只读上列计数 + `dt`；若 dt 与 awake 增量/`celUnit` 数同步升高 ⇒ 归因 A；若 awake 不变而 dt 尖峰 ⇒ 排除 A |
| B 地块真实重绘 | 3–8ms/次（早退缺失时 ~6ms/发） | `Grafon.sceneApply("decal")` 调用次数（按 `args[1]!=null` 分“真实/早退”）、`sceneLastDirtyCount`/`sceneRedraws` 增量、`sceneMarks.length` 增量；dt 尖峰与 decal 是否同帧 | ①先核部署宿主：读 `envkey-cache-20261102/candidate-build.json` 的 `hostSHA256` 对 `pfe.swf`；若无法确认早退存在，直接以“每发是否触发 sceneApply 的 chunk 循环”作为第一优先；②只读探针记录 `sceneRedraws` 与 dt 对齐；③若同帧同步 ⇒ 归因 B |
| C 念力滤镜 | 0.3–1.5ms/帧（短时） | 逐帧：`alicorn.mater`、`teleObj!=null`、`teleObj is UnitPlayer`、`visBmp.filters.length`、`gg.vis.osn.filters.length`、`gg.levit`；把“滤镜存在的帧”与相邻帧 dt 配对 | 只读探针记录上述布尔量 + dt，做“滤镜帧 vs 非滤镜帧”的配对中位数；差异 <1–2ms ⇒ 排除为主因 |
| D actPort/瞬移 | 0.1–0.3ms/次 | 逐帧：天角兽位置跳变（|ΔX|>200）计数、`tr==2`、`aiState`、`aiSpok`、`superSila` 次数；dt 与跳变是否同帧 | 只读探针 + 位置跳变检测；若每次跳变帧 dt 只涨 ≪1ms ⇒ 排除 |
| E alilight 弹体 | 0.2–0.5ms/帧/弹 | 逐帧：alilight `Bullet` 数量（类名 `visbullightning`/`fe.weapon.Bullet` 且 `weap.id=="alilight"`）、`Emitter.kol1`、alight 弹 `liv`；dt 与并发弹数 | 只读探针记录并发弹数；若并发 1–3 且 dt 与弹数无关 ⇒ 排除 |
| F findBox/广播循环 | 单次 `findBox` ≤~0.5ms、单次广播 ≤~0.1ms；合计 ≪1ms/s | 诊断宿主 wrapper 计时（`findBox`/`budilo`/`telepat` 的 calls/ms/max），或只读探针数 `t_tele==0` 帧（需 package fe.unit 的内部访问）；与 dt 对齐 | 首轮只读探针若无法读内部字段，才需要编诊断宿主（照 `build/combat-profile.py` 的 wrapper 模式，只编不部署） |

### 6.3 最小验证路线（不重跑已否定路线）

1. **先决事实（10 分钟，零运行）**：确认部署宿主 `pfe.swf` 的 SHA256 仍是 `A9B39CC7…`，且其回读源 `envkey-cache-20261102/host-export` 的 `sceneApply` 含 `decal(null,null)` 早退（`:1093-1096`）。若宿主已被改写或早退不存在，先按 B 处理。
2. **一次只读计数战斗（1–2 分钟）**：在正式 CS 大场景（马哈顿废墟）找到单只天角兽，用 ModLoader 加载一个**只读**探针（新类可放 `package fe.unit` 以便读内部字段，做法沿用 `src/tests/AlicornAlertProbeMod.as` 的“同包读内部状态”），每帧记录：`dt`、`loc.units.length`、awake/asleep/leashed、`celUnit!=null` 的单位、每只天角兽的 `mater/teleObj/aiState/aiSpok/t_tele/t_attack`、`visBmp.filters.length`、`gg.vis.osn.filters.length`、`Grafon.sceneRedraws/sceneLastDirtyCount`、并发 alilight 弹数、位置跳变。
3. **判读（按 §6.2 的 5 列对齐）**：先看 dt>50ms 帧能否被 A/B/C/D 中的某一类计数解释；工作区已反复证明“减分配≠减帧时”，因此**只接受同帧/同事件的因果对齐**，不接受平均帧时间差当收益。
4. **若计数法分不清**：才编**诊断宿主**（只改宿主方法插桩，不部署、不提交），wrapper 计时 `UnitAlicorn.control/findBox/actPort/telepath/budilo`、`Location.hitTile`、`Grafon.dyrka/decal/sceneApply`，沿用 `build/combat-profile.py` / `build/issues-combat-profile.py` 的既有模式；target 是“单只天角兽、无警报外溢”的隔离状态，与“自然房内可能被唤醒”的对照分开跑。
5. **门禁建议**：单只天角兽夹具 ≥2700 帧（90s@30Hz）真实交战、两轮顺序互换；若 A 归因成立，再专项测“移出 1920×1000 内其它同阵营单位”或“接力 0% 明确不阻止直接通知”的对照——但不要用“减少敌人/缩小范围”冒充修复，这与工作区既有的“不缩减玩法换帧率”原则一致。

---

## 7. 旧方案断言复核（`design/scene-combat-camera-optimization-plan.md` §2 等）

| # | 旧断言（原文位置） | 本轮判定 | 依据/说明 |
|---|---|---|---|
| 1 | `findBox()` 全图 1200+ 遍历 + “交战时高频进入”，单次 **4~10ms**，“首要元凶”（`scene-combat-camera-optimization-plan.md:114-146`） | **证伪（调用率与单次耗时都不成立）** | 调用率 0.05–0.6 次/秒（§1.3 算式）；单次 = 一次 1200 物体属性遍历（按 600 箱 step 实测 0.207–0.307ms/帧折算 ≈0.1–0.3ms）+ 少量 ≤67 步 `isLine`（`Location.as:2366-2386`）；4–10ms 无实测。 |
| 2 | “`GlowFilter` 强制全向重绘 / 给玩家整体容器 `vis` 挂滤镜 / 单帧巨大 CPU”（`:148-160,271-272`） | **机制错 + 量级证据不足** | 玩家走 `levitFilter2`→`vis.osn.filters`，仅 `f_levit && levit>=1 && fracLevit!=fraction` 时生效（`UnitPlayer.as:4098-4101,4143,4656-4679`），且 teleFilter 为 strength=1/quality=3；长期存在的是天角兽自己的 `nomaterFilter`（150×150、blur 15×5、quality=3、`mater=false` 期间，§2.2），其“每帧重绘”取决于动画帧变化，且没有“全屏”路径。原方案的 35–85ms 是全屏模糊的**估算**，与本对象无关，不能借用。 |
| 3 | `actPort` 20 次“全图跨度盲测 `collisionAll`”造成“瞬时 CPU 脉冲阻塞”（`:162-183`） | **成本证伪** | 每次尝试 ≤12 次瓦片检查（§3.2），20 次约 240 次；随机取点 O(1)；成功才发 2 组粒子。粗估 0.1–0.3ms/次。真正的问题是行为（全图随机落点→脱战），不是 CPU。 |
| 4 | 闪电 `destroy=50` “破坏地形、频繁触发 `loc.destroyTile`、`drawKusok` 全块重绘”（`:185-189`） | **API/机制错 + “频繁”证据不足** | 1.02 没有 `destroyTile`；`drawKusok` 存在但只在块光栅化的材质背景路径（`src102/fe/graph/Grafon.as:526,538,659,783`），**不在 `hitTile` 链上**——命中走 `hitTile`→`dyrka`/`tileDie`→`decal`。`tipdec=11` 约 90% `decal(null,null)` 在宿主 `sceneApply` 入口早退（host-export:1093-1096）；默认 hp=1000，50 伤害需 20 发同格才破坏（§4.4）。真实重绘约 1–3 次/分钟。 |
| 5 | “`rapid=35` → 射速极快”（`:185-188`） | **证伪** | rapid 是帧冷却；AI 门控后约 **0.4–0.5 发/秒**，理论上限 0.75（§4.2）。 |
| 6 | 方案 §2.2 提议“取消 `filters=[teleFilter]` 改用 `colorTransform`”，并称“被抓玩家整体容器挂滤镜”（`:202-206`） | **方案对象错位** | 被抓玩家根本没有 `vis.filters`；改 `levitFilter2` 也只在 `f_levit` 条件下生效。若要做，正确对象是 `UnitAlicorn.nomaterFilter`（自身 150×150）与 `levitFilter2`（玩家 `vis.osn`）两条。 |
| 7 | “技术根因排查完成 / 单只天角兽交战帧率可稳定 ≥27FPS”（`:10,341`） | **证据不足（预期不是证据）** | 该文档没有任何天角兽交战的函数级计时或采样；本轮把可用量级都算到了 **≤1–2ms/帧（外加一次性 3–8ms）**，无法支撑“严重卡顿”结论，也未证明修复后能到 ≥27FPS。 |
| 8 | `alicorn-alert-static-20261021.md` 的“engaged 无自动清除路径”（`:25`） | **部分失效** | 0.9.6 起有 150 帧 + 2200×1600 的脱战拴绳（`NativeSceneActivity.as:18,52-57`）；但“近圈内永久活跃”仍成立，是 A 链条的放大器。 |
| 9 | 旧方案 §3 的全屏模糊 35–85ms、§1.2 同步补画 25–45ms 等数字（`:271-272,57`） | **未复核（不在本任务范围）** | 这些是**估算**，不是计时；本任务只提醒不要把它们当作已测事实。本轮天角兽相关的滤镜只有 150×150/玩家骨骼容器两类，与全屏模糊无关。 |

另：`design/alicorn-large-scene-brainstorm.md` 是方案草案，其对“同一范围内仍可能瞬间多人围攻”（`:17`）的预判与本轮 §6.1-A 一致；但它没有性能量级，不能当证据。`alicorn-alert-release-20261028.md:25-36` 的 31 项验证是**行为正确性**（6 只天角兽、空场景、`enemyAct=1` 隔离感知），**不含性能结论**，不能用来支持或否定本卡顿。

---

## 8. 口径与未确认项（留给 Lead）

1. 本轮**未运行**任何游戏/AIR、未编译、未读取运行时；所有“ms”除标注【已有实测】外都是代码推演。
2. 部署宿主与回读源：`build/generated/envkey-cache-20261102/candidate-build.json` 记录 `hostSHA256=A9B39CC7…` 且 `deployed:false`（该目录的 candidate 是未部署诊断候选；`host-export/` 是从**部署宿主**导出的回读）。**建议先核对当前 `pfe.swf` 的 SHA256 仍是 A9B39CC7**，再引用本文件任何 `Grafon` 行号。
3. `src/patches/*.inc` 与部署谱系可能分叉（`state/MEMORY.md:62` 已记“`GrafonChunks.as.inc` 与部署谱系分叉=源码卫生债”）：本文件刻意只引用 `host-export/…/Grafon.as` 的部署回读，不引用 `src/patches/GrafonChunks.as.inc`。
4. 未确认但影响结论的两点：①部署宿主是否含 `sceneApply("decal", null,null)` 早退（若否，B 类优先级上升）；②单只天角兽战斗时 1920×1000 房范围内实际有多少同阵营单位（若确实只有 1 只，A 类不再成立，则剩余可解释量级只有 1–2ms/帧，需把“严重卡顿”归到环境/呈现/GC 等非天角兽侧，与既有“长帧主体不是 GC（仅 31% 邻近）”并列）。
5. 复算入口：`findBox` 周期按 §1.3 算式可手工重算；alilight 节奏按 §4.2；真实重绘概率按 §4.4；量级引用行号见各条【已有实测】。
