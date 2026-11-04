# 2026-11-04 相位归因实测与首个已部署优化（decal 不再取消预热）

被测技能：remains-runtime-debug / remains-auto-testing / remains-mod-build / remains-release-gate / remains-mod-memory
测试工作区：D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene

用户指令：按 `design/scene-combat-camera-optimization-plan-v2-20261104.md` 实施优化。本轮完成**方案 P0（相位归因测量）**、据其结论实施 **P2（弹痕不再废掉进行中的预热）** 并通过门禁部署；同时用同一批数据**否定 P1/P3/P4 的当前形态**。

基线：宿主 `pfe.swf` A9B39CC7（测前）、CS 0.9.8 `285625F4`、`scene.xml` 1CEA74E2。测后宿主 → **1D2004AB**（本文 §5）。

---

## 1. 为什么必须做这一轮（测量盲区）

既往所有 CS 归因都用模组 ENTER_FRAME(-200) 计时，而**预绘/同步/剔除全部发生在宿主补丁 `Camera.calc → grafon.sceneTick()` 里**，不在该计时内。反证见 `explore-warm-sync.md:269-277`。因此本轮先补一只**相位探针**。

## 2. 探针与工具（全部可复跑）

| 组件 | 位置 | 说明 |
|---|---|---|
| 相位诊断宿主 | `build/generated/stutter-opt-20261103/phase-v3/`（输出 `73776892…`），构建器 `tools/stutter_host.py` 的 `phase` 种类 | 宿主 A9B3 上替换 7 个 Grafon 方法：sceneTick/sceneEnsureUpcoming/sceneAdvanceWarm/sceneRender/sceneApply/sceneCancelWarm/sceneRestoreMarks；**类布局不变**；**仅诊断，不部署** |
| 探针 SWF | `build/generated/phase-20261104/probe-v5/`（`61EBC9F6…`），构建器 `build_probe.py` | 在 cold-v2 探针上加 `tickMs/ensureMs/cullMs/warmMs/syncMs/markMs/beginWarmMs/missLoopMs/stepCount/maxStepMs/applyScanned/cancelCount` 逐帧快照 |
| 运行器 | `build/generated/phase-20261104/run_phase2.py` | 手写隔离 manifest（启动器在该沙箱下无法保存，见 §6）+ 标准 `run_owned` 拥有 AIR 进程、独占 AIR 校验、内存红线 |
| 分析器 | `build/generated/phase-20261104/analyze_phase.py` | 用相邻样本差分把每个帧间隔拆成 CS 管线与“其它” |

测量环境：2048×1123、`cam.scaleV=1`、正式 13 模组 + 探针、私有桌面、静音、独立 AIR ID；新档进入 `random_mane` 大图后按脚本走位（40/41/42/43/44/45/49 = 静置/光照/来回平移/行走/再平移/收尾），combat 变体走 47/48（行走 + 玩家持续开火 + 6 名固定敌人）。

## 3. 结果一：CS 管线到底占多少（探索）

`phase2-explore-n1`（1149 个完整间隔，均值 41.8ms / P95 65ms / 最大 171ms）：

| 相位 | 合计 | 每帧 | P95 | 最大 |
|---|---:|---:|---:|---:|
| **CS 管线 `tickMs`** | **6515ms** | **5.67ms** | 21ms | 90ms |
| ├ 预热 `warmMs` | 5715ms | 4.97ms | 17ms | 37ms |
| ├ 同步补画 `syncMs` | 84ms | 0.07ms | — | 44ms |
| ├ 剔除 `cullMs` | 70ms | 0.06ms | 1ms | 4ms |
| ├ 弹痕重放 `markMs` | 30ms | 0.03ms | — | 9ms |
| └ 块启动 `beginWarmMs` | 550ms | 0.48ms | 1ms | **80ms** |
| 其它（原生 step/渲染/OS） | 41546ms | 36.16ms | 50ms | 141ms |

- **≥100ms 帧 13 个 / 1648ms：CS 管线 340ms（20.6%），其它 1308ms**；其中 2/13 帧 CS 完全为 0。
- **≥50ms 帧 220 个 / 13957ms：CS 24.3%，其它 75.7%**。
- 另一轮 `phase-explore-n8`（负载更轻）与 `phase-v1` 首轮结果同向：CS 占 12%~16%，长帧内 CS 占 20%~34%。

**结论 1（本轮最重要）**：CS 管线的**稳态成本**是每帧约 **3~6ms**（预热为主），偶发单帧可到 70~90ms（块启动/同步）；
但**真实长帧的多数时间仍然不在 CS**（≥100ms 帧里 CS 只占 1/5 ~ 1/3，另有两轮共 3~10 个长帧 CS 完全为零）。想把 >100ms 尾部当“CS 问题”处理会走错方向。

## 4. 结果二：战斗场景（含开火）

`phase2-combat-n1`（1299 间隔，均值 41.4ms / P95 58 / 最大 141ms）：

| 相位 | 合计 | 每帧 |
|---|---:|---:|
| CS 管线 | 3897ms | 3.00ms |
| ├ 预热 | 3442ms | 2.65ms |
| ├ 同步 | 62ms | 0.05ms |
| ├ 弹痕重放 | 38ms | 0.03ms |
| └ 块启动 | 244ms | 0.19ms（峰值 73ms） |
| 其它 | 49906ms | 38.42ms |

- **≥100ms 帧 13 个：CS 127ms（7.8%）**，7/13 帧 CS 为 0。
- **取消预热**：`cancelCount=10`、`cancelWork=302ms`（丢弃的预热工作量）。
- 地块扫描：`applyCalls=566`、`applyScanned=58787` → **104 块/次**；总耗时并入 markMs 可忽略。

## 5. 已实施的优化：弹痕不再取消进行中的预热（P2）

**改动**（宿主 `fe.graph.Grafon.sceneApply`，单方法替换，类布局不变）：
`this.sceneCancelWarm(affected);` → `if(kind != "decal") { this.sceneCancelWarm(affected); }`

**正确性依据**（`explore-warm-sync.md:243-249`）：新弹痕在 `sceneApply` 里**先** push 进 `sceneMarks`，而预热 job 的最后一个 step 就是 `sceneRestoreMarks()`，会重放本块相交的全部弹痕；因此对 `decal` 取消预热在功能上冗余。`paint`/`gwall`/`drawWater` 仍保持取消语义（可能是破坏性地形变更）。

**前后对比（同调度、各 1300 帧）**：

| 指标 | 基线 `phase2-combat-n1` | 候选 `cand-a-combat-n1` |
|---|---:|---:|
| `cancelCount` / `cancelWork` | 10 / 302ms | **0 / 0ms** |
| 每块预热工作量 | 3555ms / 78 块 = 45.6ms | 4069ms / 94 块 = **43.3ms** |
| 块启动耗时 | 246ms | 199ms |
| 检查项 | 13/13 | **13/13** |

两轮整帧均值 41.4 vs 45.1ms **不能当收益**（不同轮负载不同，本仓反复强调）。**可主张的只有机制量**：每 1300 帧战斗消除 10 次丢弃与约 302ms 废工（约 8% 预热工时）。

**部署**（GOVERNANCE §6）：宿主 `pfe.swf` **A9B39CC7 → 1D2004AB**（只改 `sceneApply` 一个方法，`classesUnchanged`）；
备份 `build/backups/pfe_before_decal_nocancel_20261104-133604.swf`；回执 `build/generated/opt-20261104/deploy-receipt.json`；
清洁候选（无诊断代码）冒烟 `cand-a-clean-combat-n1`：1300 样本、13/13、无错误。**需重启游戏生效**。

## 6. 被本轮数据否定的候选（写清理由，避免重复）

| 候选 | 原计划理由 | 实测 | 处置 |
|---|---|---|---|
| **P1 拆 `drawKusok` 子步** | 冷态曾见 125ms 单步 | 本轮三轮 `maxStepMs` 仅 **20–25ms**，`stepMs/stepCount ≈ 1.3ms/步` | **不做**：当前形态尾值不构成 >100ms 主因；若将来出现 80ms+ 单步，再用同一诊断器复核 |
| **P3 弹痕空间索引** | 担心 O(N) 增长 | `markMs` 合计 **2–40ms/1150–1300 帧**（≈0.03ms/帧） | **不做**：不在噪声之上 |
| **P3 驻留块上限 / `sceneApply` 空间索引** | 每发扫 118 块 | `applyScanned/apply = 104–126 块`，但 566 次 apply 合计仅 5.9 万次矩形相交 | **暂不做**：当前量级不构成可测成本；**但驻留内存无上限仍成立**（见 §7） |
| **P4 `sceneApplyCompactDecal` 分配按宽高** | 纯浪费 | 量级 = 每发 1–2 次临时位图；工作区四次“减分配≠减帧时” | **不做**：收益低于验证成本 |
| **降 `sceneWarmBudget`** | 认为 48ms 过大 | 实测预算自适应到 **2–25ms**，且预热每帧约 3~5ms 是**配置行为**而非越界 | **不做**：压预算会饿死预绘、转为 31–178ms 同步补画 |

## 7. 尚未解决、已定位证据的两件事

1. **驻留块无逐出**（`Grafon.as:510-534`，`sceneDrop` 只在换图/verify 调用）：本轮实测 `resident 47→181`（探索 38s）与 `51→128`（战斗 43s），即 **+134 块 ≈ +343MB / 38 秒**，全图上限 480 块 ≈ 1.2GB。**长时间游玩的内存单调增长是真实存在的**，但本轮没有证据说它造成当前卡顿；若要做，正确形态是“远处逐出 + 缓冲复用”，并且必须用本文工具验证回头路不会制造同步补画风暴。
2. **长帧主体（≥2/3）在原生侧**：本轮三次测量一致。继续追长帧应转向原生 step/渲染/系统调度，而不是 CS 渲染代码。

## 8. 过程与口径

- 运行器在该沙箱内无法使用 ModLoader 启动器保存选择（命名互斥体写入被拒），故改为**手写隔离 manifest**；`application.xml` 必须由我方改写为 `pfe-modsettings-continuous-scene`（`run_owned` 再替换成唯一 ID）。**首次失误**：手写时直接拷贝了根目录真实描述符（`<id>pfe</id>`），导致一次运行写入**玩家真实存储**（`%APPDATA%\pfe` 的模组日志与 `MSWConfig.sol`/`ModLoader.sol` 被重写，**存档 `PFEgame0.sol` 与 `config.sol` 未被触碰**）；随后已改为改写模板并重新运行。此事如实记录。
- 探针的“必须装备 LMG”前置被放宽为“任意武器”，因为本轮新档初始武器为 `r32`；武器类型与相位归因无关，已在报告中记录实际武器。
- 测试登记：本轮全部运行经共享登记表以 `game` 独占申请；期间清理了本会话一次因低完整性启动被拒留下的 `needs-check` 租约（另有会话的 AIR 进程会占用资源，运行器按拥塞重试）。
- 未做：未改模组 `src/release`（CS 仍 0.9.8）、未改 `scene.xml`、未做天角兽 B-P2（缺只读计数证据）、未做地形双线性开关（只在 `scaleV≠1` 有意义，本轮窗口 `scaleV=1`）。

## 9. 复跑

```powershell
$py = "C:\Users\hello\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
# 诊断宿主（若需重建）
& $py tools\stutter_host.py phase-v3 phase
# 探针
& $py build\generated\phase-20261104\build_probe.py probe-v5
# 基线测量（explore / combat）
$env:PHASE_PROBE="probe-v5"; $env:PHASE_LABEL="phase2"
& $py build\generated\phase-20261104\run_phase2.py explore 14
& $py build\generated\phase-20261104\analyze_phase.py phase2-explore-n8
```
