# 子弹空间分桶部署快照（2026-11-04 19:15，20:57 复核）

> **为什么单独成文**：`state/MEMORY.md` 与 `state/journal.md` 被另一会话
> `session-9f1f58e1-5574-4c28-b98d-de859054a71c`（部署 CS 0.9.9 的那条）通过 `dsh-file-claim` 认领。
> 该会话 18:42 之后再无写操作、心跳也已 37+ 分钟未更新，但**它的 DSH 进程仍存活**，
> 因此 `claim_files` 与 `claim_files(force:true)` 都被判为"活跃会话占用"而拒绝（20:57/21:01 两次实测），
> 写 MEMORY/journal 被护栏拦下。按治理要求不绕过护栏。
> **下一位接手者**（或让那条会话 `release_files` 后）请把本文 §1 的条目合并进 `MEMORY.md` 顶部，
> 把 §2 追加进 `journal.md` 顶部，然后删除本文件。
>
> **⚠ 记忆里的过时事实**：`MEMORY.md` 顶部那条 0.9.9 记录写的是"宿主 `1D2004AB` 不动"，
> 现在的根 `pfe.swf` 是 **`91F8E10D`**（本轮子弹分桶部署）。以 `Get-FileHash pfe.swf` 为准。
>
> **过程记录（认领互斥锁卡死）**：本轮 `.dsh-file-claim.lock` 三次卡住（pid 24028，
> 时间戳每次都被后续等待方刷新），删除后才恢复；备份
> `.dsh-file-claim.lock.stale-20261104-1936.bak`、`.stale-20261104-2058.bak`。

## 1. 应插入 `MEMORY.md` 顶部的条目

```markdown
<!-- bullet-grid-20261104 -->
> **2026-11-04 已部署子弹空间分桶（宿主 `1D2004AB` → `91F8E10D`）**。CS release 未动（当时已被并行会话部署到 0.9.9 `D04CD26A`）、`scene.xml` `1CEA74E2` 未动；**需重启游戏生效**。备份 `build/backups/pfe_before_bulletgrid_20261104-185052.swf`（= 1D2004AB），回执 `build/generated/combat-collision-20261104/deploy-receipt-grid-clean.json`，报告 `knowledge/experiments/bullet-collision-20261104.md`。
> - **改了什么**：①删掉 `Grafon.sceneTick` 往 `World.w.visual.root["sceneCU"]` 写列表、以及 `Bullet.run` 读它——`root` 是密封的 `fe.MainFE`，那两处每天都在抛了再吞（读 #1069 / 写 #1056），`_collisionUnits` 恒回退 `loc.units`；②`sceneTick` 改为每帧建**整房间 512px 分桶表**（单位 AABB 外扩 96px 登记全部覆盖格、桶数组跨帧复用），存 `World.w.vgui["__csBulletGridV1"]`；`Bullet.run` 按子弹自身坐标查桶。只改 `fe.graph.Grafon::sceneTick` + `fe.weapon.Bullet::run`，类布局不变。
> - **为什么存 vgui**：离线无头探针实测 **`Sprite` 是密封类**（写动态属性抛 `Error #1056`），`MovieClip` 才是 dynamic。最初版本挂 `World.w.visual`（`new Sprite()`）会**每帧在 ensure/cull 之后抛 #1056**，整条预热/剔除链死掉——部署前被 `src/SpriteDynamicProbe.as` 挡下。该结论已回写 shared-knowledge `knowledge-validation/facts/modding-interop.md`。
> - **等价性（离线、可复算）**：16,009 个探针点（静态 6000 / 一帧陈旧 ±96px 6000 / 对抗几何 4000+9）**0 不一致**，口径是“首个命中单位下标”；另断言“建表后新生成单位”必须靠 `units` 计数闸回落（不带闸会漏）。
> - **成本（离线 40 弹 × 130 单位 × 900 帧）**：全量扫描 + 每弹异常 **1.34ms/帧 → 分桶建表+查 0.47ms/帧（−65%）**；异常本身占 0.43–0.92ms/帧。真实单位每轮读 9 个属性，全量一侧更贵，真实差距只会更大【推断】。
> - **游戏内**（3 次隔离运行，均 1300 样本 / 13 项检查通过 / 无错误）：`bulletgrid-gridlive-combat-n1`（probe-v6）**`grid.active` 1300/1300 帧、`grid.error=null`**、`loc.units` 均值 **122**、视口处一格候选 **2.71（P95 5、最大 5）** → 每发子弹要查的单位从 ~122 降到 ~3（约 45×）。clean↔clean 同探针对照（各 1299 间隔）：均值 49.89→49.29（−0.60ms/−1.2%，且候选臂在飞弹更多）；第三轮候选臂 46.93（−2.96ms）。**只主张“没有退化”+机制量，不主张整帧收益**。装后冒烟（装的字节本身）5/5 通过，CS `v0.9.9 loaded`、无未捕获 `Error #`。
> - **未做（有证据）**：C2 唤醒强弱分级 / C3 拴绳迟滞（`alicorn4` 计数显示唤醒已按每帧 1 只预算、整场帧时不抬升）；E1 视口前馈（长帧 85–100% 与 >1MB 内存回落同帧，回收由大地块分配推动，加前馈反向）；E2 `drawKusok` 切分（`maxStepMs` 仅 20–25ms）；E3 远处逐出（已实测最大帧 171→568ms）。
> - **回退档/陷阱**：`scu-remove-clean` `BAA22A81`（只删异常通道、不带分桶）。`decal-nocancel-v2`（`BD8F90FA`，7 方法相位诊断含 `sceneEnsureUpcoming` 插桩）**两次跑挂**（10 分钟超时无 result），不可再用于配对；控制臂请用真正线上字节 `decal-nocancel-clean`。
> - **已知交互（已实测互操作）**：CS 0.9.9 瞄准平移会在 `apply()` 后再调一次 `w.grafon.sceneTick()`，平移期间分桶表会被重复重建。已用 0.9.9 自己的 `AimProbe` 实机夹具跑**已部署字节**：**14/14 通过**（`viewportSyncs` 239/444 帧、`resident 70→110`、`world-map-exact bad 0`、`apply-consistent bad 0`），说明这次额外的重建不影响任何已断言行为。
> - **同毫秒去重候选已建但不部署**：`grid-probe` `1D415967`（带 skip/build 计数）、`grid-clean-guard` `6E3BC782`（纯净版）。理由：第二次 `sceneTick` 在模组 ENTER_FRAME 里、晚于游戏 step，两次调用相隔毫秒级以上，`getTimer()` 同毫秒几乎不成立 → 无可测收益，按门槛不动宿主。
<!-- /bullet-grid-20261104 -->
```

同时 `MEMORY.md` §3 安装表的 `根pfe.swf` 行需改成：

```
| 根pfe.swf | **91F8E10DFB36A2024EAB140FC4BD67719330BF67310BA5CAB5CDAE8DEDF3CB45（2026-11-04 18:50 子弹空间分桶；需重启；回退备份 build/backups/pfe_before_bulletgrid_20261104-185052.swf）；前值 1D2004AB…（弹痕不废预热） |
```

## 2. 应追加到 `journal.md` 顶部的条目

```markdown
## 2026-11-04 — 交战卡顿：子弹空间分桶落地（宿主 1D2004AB → 91F8E10D）

- 按方案 C1 实施：删除 `Grafon.sceneTick` 写 / `Bullet.run` 读 `World.w.visual.root["sceneCU"]`
  的密封类异常通道，改为每帧整房间 512px 分桶表（存 `World.w.vgui`，`Sprite` 密封不能用），
  子弹按自身坐标查桶；三道回落闸（targetObj / 单位数变动 / 玩家位移 >256px）。
- 离线：16,009 探针点 0 不一致（含一帧陈旧与建表后新增单位）；成本 1.34 → 0.47 ms/帧（40 弹×130 单位）。
- 游戏内 3 次 1300 样本 / 13 检查全通过：分桶 1300/1300 帧生效，单位 122 → 候选 2.7；
  clean↔clean 对照均值 −0.60ms（候选臂在飞弹更多），第三轮 −2.96ms；**不主张整帧收益**。
- 部署 `pfe.swf` → `91F8E10D`，备份 `build/backups/pfe_before_bulletgrid_20261104-185052.swf`，
  回执 `build/generated/combat-collision-20261104/deploy-receipt-grid-clean.json`，装后冒烟 5/5。
- 按既有证据不做 C2/C3/E1/E2/E3（理由见报告 §8）。陷阱：`decal-nocancel-v2` 诊断宿主两次跑挂。
- 报告 `knowledge/experiments/bullet-collision-20261104.md`。
```

## 3. 状态核对（写本文时的实测值）

- 根 `pfe.swf` SHA256 = `91F8E10DFB36A2024EAB140FC4BD67719330BF67310BA5CAB5CDAE8DEDF3CB45`
- 备份 = `mods/ContinuousScene/build/backups/pfe_before_bulletgrid_20261104-185052.swf`（`1D2004AB…`）
- CS release = `D04CD26AA674238BBB2F43A2CA49C57811301E9B9B614352A099F8190D9E0193`（0.9.9，非本轮改动）
- `scene.xml` = `1CEA74E2…`（未动）
