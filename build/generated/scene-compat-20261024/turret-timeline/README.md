# 炮塔同帧定位：同步组件

本目录是隔离同步组件；2026-10-24 已完成下面记录的一轮实测。未修改宿主、正式模组或共享源码，没有部署同帧 guard。

## 2026-10-24 实测结果

证据目录：`mods/ContinuousScene/knowledge/experiments/evidence/turret-timeline-20261024-components-r1/`，原始数据在 `storage/result.json` 的 `turretTimeline`，摘要在 `summary.json`。

真实场景发现 13 个炮塔，其观察到的外层素材均为 `pfe_fla::turel_puha_1262`。组件测试该素材全部 10 个外层数字帧及约定的内层播放/停止状态，共 38 组，全部同步通过：差异像素总数为 0，两侧同侧对象引用变化均为 0，递归树和事件比较一致。两侧各记录 141 条 frameConstructed 事件，不能把“0 对象变化”误写成“没有事件”；本次没有观测到增删事件。

原生单位/视觉树/暂停值检查通过，86 个自有副本全部停止，152 张临时位图全部释放。`passed=true`、`synchronousPassed=true`，但 `timelineAdvanceVerified=false`、`candidateEligible=false`、`performanceEligible=false` 保持不变。

本结果**没有支持“同帧 goto 重建了炮塔 puha 自身”的假设**，也没有证明跳过 goto 会加快游戏。它仅覆盖离树副本同步调用；未推进真实帧，未验证枪口播放时长、舞台上的 FocusManager 或稍后排空的全局队列。采样栈中炮塔 goto 下的 `[execute-queued]` 仍可能代表其他动画的排空点。没有据此构建或部署 guard，也没有性能收益验收。

关键 SHA-256（完整冻结源码与依赖见证据目录的 `probe-build.json`、`inputs.json`）：

| 工件 | SHA-256 |
|---|---|
| 实测 `tests/SceneTurretTimelineChecks.as` | `697B12C9D8DB9882879311198390192E2E325BF6C1FD9B9CEC2EBC94751B6495` |
| 正式宿主 | `A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7` |
| 实测探针 | `B9A1F2D742C0AB14E0E668EF5EBDE00251BFBE1F87AE080D70061ABBD7AA21C3` |
| `storage/result.json` | `BE2034337D0B408393EF5BD8F95D1D4C91160EB8A51D80FC5AADF05AB2B65D4D` |
| `summary.json` | `77F80230B45EAB9D9FC4A3A0E0E4D608FC2452B3AEEB82BFE6E120439F63D952` |

## 实施边界

`probe_patch.prepare(source, destination)` 只接受 B7ED 收据所列的完整 85 源快照（原探针 39A1497B）。它在复制的 MotionProbe 中新增组件导入：phase2 完成真实地图类型检查后提前进入 phase3，跳过路线、玩家定位、六名测试敌人和武器准备；phase3 调用 `tests.SceneTurretTimelineChecks.run(w)`，写入 `report.turretTimeline` 后立即结束。三个插入均可逐字逆转；新增文件只有 MotionProbe 与该 helper。

组件从真实宿主域的 `fe.unit.UnitTurret` 实例取得 `vis.osn.puha` 类，核对其实际 constructor 与宿主域定义，随后只构造该类的离树副本。没有调用 UnitTurret 构造器或 animate，不主动调用或写入真实单位、武器、AI、位置、随机数或存档。暂停值在 finally 恢复；保存的原生对象身份与炮塔视觉树必须完整保持。原生 goto 仍可能同步排空其他待执行帧脚本，本组件不冒称检查并恢复了整张地图的所有隐藏状态，必须终止隔离进程且不保存。

每个实际外层数字帧均检查。存在内层 puha 时测试 stop(1)、play(2)、play(中帧)、play(末帧)，重合帧去重；缺少内层时明确记录并仅作外层检查。每组对照中 A 执行重复 `gotoAndStop(tr)`，B 仅在帧不同或仍在播放时调用；本轮 B 应为真正 no-op。两边初始像素和递归树必须相同且捕获稳定，再比较执行后的完整 ARGB 像素、递归状态、同侧引用变化和增删/构造事件。自动生成的 `instance数字` 名称仅在跨副本结构比较中归一；实际身份以每侧独立递增 ID 记录。原生实物快照没有靠跨轮 ID 对齐。

固定的局部捕获矩形覆盖初态边界并加 64 像素空边，后态边界包含性和透明外圈另有断言，不以裁切后的相同图片放行。像素用 getVector 全扫描，RGB 与 alpha 都要求严格相等。失败保留 before/immediate/after、引用差异、事件序列、差异像素数与通道最大差；不自动放宽容差。所有临时位图释放，两侧全部子 MovieClip 停止并移除本组件监听。

## 输出口径

- `passed` / `synchronousPassed`：只表示本轮同步组件通过，且原生状态恢复与临时资源清理通过。
- `cases[].passed`：该组原始像素、树、引用与事件全部一致；所有组继续执行，保存全部差异。
- `coverage[]`：每个外层帧、内层是否存在、内层实际类和帧数；若真实地图存在多种外层 art 类，本窄组件只测第一类并明确 inconclusive，不伪称全覆盖。
- `restore.passed` / `cleanup.passed`：原生身份/视觉树/暂停值保持，以及自有副本停止和位图释放数量一致。
- `timelineAdvanceVerified=false`、`candidateEligible=false`、`performanceEligible=false`：固定为 false。

本轮不会推进真实 ENTER_FRAME，不能证明枪口动画持续时间、返回 stop(1) 的时刻、舞台 FocusManager 或延后构造队列行为。仅同步全等后才考虑独立跨帧组件。CPU 采样里 `[execute-queued]` 位于炮塔 goto 下，也可能只是全局待执行动画队列在这里被排空；没有副本自身的增删/引用变化，不能据祖先栈宣称炮塔重建或性能收益。
