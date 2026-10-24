# 玩家叶部件缓存资格诊断 r1：未具备测试条件

日期：2026-10-25。证据：`knowledge/experiments/evidence/player-leaf-cache-20261025-r1/`（相对 ContinuousScene 模组目录）。

本轮实际启动并完成初始化、暖场和玩家树盘点，但指定的原生符号 `pfe_fla::sleg20_53` 没有出现。结果为 `inconclusive-initial-target`，`complete=false`、`passed=false`、`rawOK=false`；不能记作缓存验证通过或性能测试通过。该方向在当前夹具下结束，不更换目标、不改变阈值，也不追加重跑。

## 实际观察

- 玩家实际护甲和背包护甲均为 `pip`，玩家视觉类为 `visualPlayer`；装备与预设一致。
- 盘点扫描玩家树共 121 个节点，精确目标匹配列表为空。121 是总节点数，不是合格叶部件数。树中另有 `sleg10_6` 等符号，未拿它们替换指定目标。
- 连续观察样本为 **0**，没有进入计划中的 4×300 帧观察；`rows=[]`、`continuous=null`。不能从零样本的稳定性计数推断目标稳定或频繁替换。
- 像素比较 `attempted=false`，没有请求缓存，也没有写入 `cacheAsBitmap`。未产生 A/cache/A 截图或缓存性能臂。
- 自有位图 `created=0`、`disposed=0`，`pendingRestore=0`，清理 `restored=true`、`errors=[]`。摘要中的 8 项是此前准备检查，不代表原计划完整验收。

旧姿态样本中曾见到该符号，不能据此证明当前真实冲刺夹具会出现相同叶部件。本轮只否定该精确目标在这次夹具中的测试资格，不证明所有叶部件缓存都有效或无效。

## 窗口事实及边界

暖场盘点与终态读取一致，全部属性读取无错误；辅助代码没有显示、激活或聚焦窗口。

| 项目 | 两次实际读取 |
|---|---|
| NativeWindow visible / active / closed | `false / false / false` |
| NativeApplication.activeWindow 与该窗口相同 | `false` |
| 窗口 displayState / renderMode | `normal / direct` |
| 窗口 bounds | x=52，y=52，2048×1123 |
| Stage 大小 | 2032×1084 |
| Stage displayState / quality / frameRate | `normal / HIGH / 30` |

这证明本次隔离实例在两个观测点处于隐藏、非活动状态。隐藏窗口不是本轮叶部件资格失败的判据；实际失败原因是目标不存在。`direct` 是窗口报告的渲染模式，不能据此确认 GPU 后端；正常 Stage 尺寸和配置帧率也不证明操作系统实际呈现或实际 FPS。`screenPresentationVerified=false`。不能将这两个观测点外推为所有历史实测的窗口状态。

## 输入与证据保持

原始运行器记录 528 项输入，并在结束时报告 `inputsUnchanged=true`。本说明只核对已有记录，没有再次读取二进制重算指纹，也没有运行新测试。没有部署或修改正式输入。

| 输入 | 本轮记录的 SHA-256 |
|---|---|
| 正式宿主 | `A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7` |
| ContinuousScene | `7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F` |
| RConnect | `78C052AEA963F1689B705AE1E14D274916AE1A1F7E81933390CAF8D1A88F4699` |
| RealisticVision | `638E2D408E2CF46683C41114F75773829A1B4417D74BFFE9D08855A4FE343710` |
| ModLoader | `2050E023205E87FDFDF7FBA4B54B9BAD7769868E51767D0BFBE1742CDC7542E2` |
| TDFC | `7ACD45193109267DBBF875240528048AD6F1D09FA3B8B36BAA6F98EBB5FDDCE5` |
| 实际探针 | `9F8419E6B8EC3541134A2DC3C15BE3DC763522FD6C6934C4A459E6DD1480357E` |
| `storage/result.json` | `AE71EE22EEBCF36C00DF96B0D8DBCA36B862D30CC34CD5ADF2695BFBCA48FB10` |
| `storage/leaf-inventory.json` | `C683863154DF89ADD57FEE4E9EEC01AD49A29E603323FA9E834D52C7F95360DC` |

核对依据为上述证据目录的 `summary.json`、`component-status.json`、`inputs.json` 和原始盘点/结果。`runner-failure.json` 保留失败；未覆盖旧 README、运行器、辅助源码、变换脚本或任何原始证据。本轮没有缓存画面等价结论，没有战斗帧率结论，也没有玩法验收或部署。
