# 2026-11-04 单只天角兽计数探针（B-P1）：工具就绪，首轮结果不支持“警报拉活”假设

被测技能：remains-runtime-debug / remains-auto-testing / remains-mod-build
测试工作区：D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene

目的：执行 v2 方案 §3.3 的 B-P1——用**只读计数探针**回答“与单只天角兽交战时，警报/目标共享到底把多少单位拉进活跃集合”，为 B-P2（弱信号走唤醒预算）提供取舍依据。

## 1. 工具

| 组件 | 位置 | 说明 |
|---|---|---|
| 探针源码/构建器 | `build/generated/phase-20261104/build_alicorn_probe.py` → `alicorn-v3/`（`1722C1A1…`） | 以 cold-v2 探针为底，新增：`spawnAlicorn()`（原生 `fe.unit.UnitAlicorn("1",100,null,{tr:1})` + `putLoc/addObj/units.push/setPos/setCel`，`hp=1200`）、`scheduleFor` 的 `controls.alicorn` 分支（单阶段 900 帧）、以及逐帧 `row.alert`（units/cel/f1/awake/asleep/leashed/filters/projectiles/redraws/resident）与 `row.unicorn`（tr/mater/aiState/aiSpok/t_tele/t_attack/teleObj/filt/x/y） |
| 运行器 | `build/generated/phase-20261104/run_phase2.py`（`alicorn` 模式） | 手写隔离 manifest + 标准 `run_owned` |

要点：探针读取宿主诊断计数器；`fe.unit` 密封类的属性访问一律包 try/catch（`visBmp` 在 `UnitPlayer` 上会抛 #1069，首版因此丢掉整段计数）。

## 2. 首轮实测（`alicorn2-alicorn-n1`，900 帧，单只 alicorn 已生成）

- 生成确认：`{"id":"alicorn1","tr":1,"fraction":1,"x":6620,"y":2940,"hp":1200}`；14 项检查通过（含 `alicorn-spawned`）。
- 帧时：均值 **34.4ms**、中位 33、P95 46、最大 119ms，仅 3 帧 >100ms。
- 活动集合（`NativeSceneActivity.stats()`，version `leash-wake-2`）：`awake` **33→27（区间 27–35）**、`asleep` 105→112；**900 帧内唤醒事件仅 11 次、休眠 18 次，交战开始后前 30 帧唤醒 0 次**。
- 帧时对比：前 60 帧 33.6ms、60–400 帧 35.4ms、400–900 帧 33.8ms；`awake` 高于中位的帧 35.5ms vs 低于中位 33.7ms（差值 ≈1.8ms，与“每多一个活跃单位 +1.5–2ms”同向，但本轮的 awake 波动只有 ±4）。

**判读**：这一夹具里**没有出现“警报把同房同伴成批拉活”**——没看到 awake 跳变，也没看到交战后持续帧时抬升。因此 B1 假设在本夹具**未被证实**；`cel/f1/filters` 等判别字段因首版密封类访问异常丢失（v3 已修），尚未取到。

## 3. 为什么还没结论

1. **判别字段缺失**：首版 `row.alert` 整段因 `UnitPlayer.visBmp` #1069 抛错而丢弃；v3 已改为逐个 try/catch，但 v3 的运行被并发会话持续占用 AIR 挡住（见 §4）。
2. **夹具的代表性**：本轮只造了 `tr=1` 的 alicorn 在玩家旁 420px；真实战斗里天角兽会 `actPort` 传送、`superSila`、`castShit`，且同阵营单位分布不同。要判定 B1 必须同时看 `celUnit != null` 的单位数与 `awake` 跳变，而非只看帧时。
3. **同房同阵营单位的数量**未知——如果这一带本来就只有这一只敌对单位，B1 天然不成立（与 alicorn 调查 §6.1-A 的“若实际只有 1 只同阵营单位则此条不成立”一致）。

## 4. 环境阻塞（如实记录）

14:04–14:20 期间另一会话持续以 `game-coexist` 跑 wallprobe/fogtest/coverage-move，并有一个 13:57 起、CPU 已累计 1600s+ 的 `adl64` 常驻；本会话 `alicorn3` 的 n1–n10 全部因 `Existing AIR` / `Other AIR appeared` 失败（探针要求运行期独占 AIR）。已停止重试，未动他人进程。

## 5. 下一步（拿到干净窗口即可完成）

1. 跑 `PHASE_PROBE=alicorn-v3 PHASE_LABEL=alicorn3 python run_phase2.py alicorn 14`（约 90 秒）；
2. 判读：`row.alert.cel/f1/awake` 相对生成前的变化 + `row.unicorn` 的 `mater/teleObj/t_tele` 相位；
   - `awake` 在交战开始后跳升 3 只以上且帧时同步抬升 → B1 成立 → 做 B-P2（弱信号走 `wakeBudget`）；
   - `awake` 不跳、`cel` 只 +0~1 → B1 不成立，关闭该方向，天角兽问题按“非 CS”处理。
3. 若要与真实游玩对齐，需要第二个变体：`tr=2`（会 `actPort` 的型号）+ 同阵营单位密度更高的位置。
