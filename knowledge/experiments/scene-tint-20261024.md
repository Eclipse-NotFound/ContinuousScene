---
domain: rendering
type: experiments
game-version:
  - "1.02"
confidence: high
verified: true
discovered-by: ContinuousScene
evidence:
  - kind: runtime-experiment
    summary: "同一冻结组件分别在 ABE2 基线、A796 隔离候选及实际安装路径运行；每组 20 项检查、14 次真实宿主方法调用。验证范围仅为染色方法组件。"
  - kind: retained-bytecode-audit
    summary: "仅 Grafon.sceneUpdateEntityColor 与 sceneEntitySameColor 改变；5769 个其他方法体、1016 个类布局及非 ABC 内容保持。"
  - kind: deployment-receipt
    summary: "正式部署回执 verified；526 项输入仅根 pfe.swf 改变，安装后组件再次通过。"
date-updated: 2026-10-24
---

# 大场景内换区后玩家颜色残留：双缺陷修复记录

用户确认的问题是**同一个大场景内离开工厂区域后，玩家仍保留工厂颜色**。本轮确认了两处独立原因，并将修复部署到根目录 1.02 宿主。三组组件证据支持染色方法的修复；没有进行完整跨区行走验收，也没有测得或声称战斗性能改善。

## 两处原因与准确改动

基线为 `ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A`，保留此前镜头及其他已部署改动。研究使用该谱系的 Grafon 源码：`build/generated/motion-direction-rays/source/fe/graph/Grafon.as`，SHA256 `75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB`，重点为 1170–1220 行。

1. **颜色存储量化被误判为外部效果。** 原 `sceneEntitySameColor` 将显示对象读回值与原始 `ColorTransform` 八分量直接比较。真实 green 输入 RGB 乘数 `(0.8, 1.16, 0.8)` 经 AIR setter/getter 后为 `(0.796875, 1.15625, 0.796875)`。方法把正常区域底色误认为其他效果所有，换区时只更新逻辑 `cTransform`，未更新玩家或普通武器的实际显示色。
2. **玩家自主悬浮被套用持物保护。** 原 `sceneUpdateEntityColor` 只在 `target.levit == 0` 时允许更新根显示色。玩家自主悬浮也用 `levit=1`，但其悬浮特效位于内部显示对象；逻辑底色先被推进到新区后，后续 `original === desired` 提前返回，使落地后仍无法自行补回显示色。组件另用可精确表示的 `(0.75, 1.25, 0.75)`，排除了第一处量化问题才复现此缺陷。

生产只改以下两个准确方法：

- `fe.graph.Grafon::0:1:sceneUpdateEntityColor`：原 `levit == 0` 条件增加“或对象就是 `World.w.gg`”。位置、区域选择、颜色所有权、交互高亮、武器魔法色等其余条件不变。普通箱体和其他单位没有获得玩家豁免。
- `fe.graph.Grafon::0:1:sceneEntitySameColor`：保留原八分量快速比较。只有比较失败且预期颜色八分量均有限时，才将预期色写入一个未加入显示树的 Sprite，再读回实际存储值，按原八分量严格比较。不使用 epsilon，不猜舍入规则，不修改被比较的目标显示对象。

精确保留审计确认：实际改变方法恰为上述两项；5769 个其他方法体、1016 个类布局、构造器、原常量池、原私有身份、方法/类索引和非 ABC 外壳保持；未增加方法或字段，未复制导入整类。

### 当前维护入口同步

主任务另将同一修复同步到当前维护模板 [SceneEntityColors.as.inc](../../src/patches/SceneEntityColors.as.inc)，本记录作者只读复核：

- `sceneUpdateEntityColor`（第 10 行起）的去注释/空白方法体，与准确旧 Grafon 方法仅替换 `target.levit == 0` 为 `(target.levit == 0 || target === World.w.gg)` 后逐字一致，其他原分支没有变化。
- `sceneEntitySameColor`（第 56 行起）与已验证 [source-equivalent.as.inc](../../build/generated/scene-compat-20261024/tint/product/source-equivalent.as.inc) 去注释/空白后逐字一致，包括有限值检查及未入树 Sprite 规范化。
- 模板 SHA256 为 `EDEDC3C5577AD286289D467196F426581C044A155013EFA73D98D331CDC4B975`；冻结等价源码 SHA256 为 `57398E9E9A75B287688A02DFB20D3DF476291DCA92C6F004B58D0C3F34DCDAF5`。

正常生成入口 `build/prepare.py:168` 调用 `entity_color_patch.apply_grafon`，后者在 `build/entity_color_patch.py:51–57` 直接读取该维护模板；`build/build.ps1:24` 先调用 prepare。无需改调用器即可带入同步的源级修复。本次没有重新编译全量宿主，因此这个入口的检查属于源码一致性核对，不等同于一次全量构建验收。

历史实验脚本仍可能直接读取冻结的 `generated/motion-direction-rays/.../Grafon.as` 等旧来源，例如 `build/enemy-speed.py:86`。这些历史产物与证据保持原样；若未来复用为新正式候选，应明确基于当前宿主或移植已审两方法，不能把历史重建自动视为当前发布路线。

## 三组有效证据

三轮使用同一冻结组件 `scene-entity-tint-components-2`，源码 SHA256 `B9F13F3E97C47A0D98E34FEBAC1B049854E826636BCE5725685E7143FEB6931F`。通过宿主自己的应用域确认真实 World、UnitPlayer、Box；在已初始化的大场景中选取两个真实区域身份，临时输入 green/neutral 色并调用真实 `Grafon.sceneUpdateEntityColor`。这些是受控组件输入，不是实际行走路径。

| 证据目录 | 宿主与用途 | 结果 |
|---|---|---|
| [baseline-r2](evidence/tint-components-20261024-baseline-r2/summary.json) | ABE2 基线，`expectFixed=false` | 20/20；普通量化残留与自主悬浮残留均为 true，确认两种缺陷确实复现 |
| [candidate-r1](evidence/tint-components-20261024-candidate-r1/summary.json) | A796 隔离候选，正式路径当时仍为 ABE2 | 20/20；两种残留均为 false，恢复检查通过 |
| [installed-r1](evidence/tint-components-20261024-installed-r1/summary.json) | 从实际正式路径复制 A796，重新编译独立探针 | 20/20；两种残留均为 false，恢复检查通过；`installedPathSmoke` 与 `copiedActualInstalledHost` 均为 true |

每组均为 14 次真实染色方法调用，无性能采样。组件自身耗时分别为 5、4、4 毫秒；这些是短组件总耗时，**不能作为帧率或性能收益**。三轮进程策略均为私有桌面，`performanceEligible=false`，未记录运行失败、内存中止或其他 AIR 进程争用。

组件还验证了以下保护：

- 独立 Sprite 的存储读回值与真实玩家 MovieClip 一致，输入包含工厂色、负乘数、大乘数、小数/越界偏移及外部根色；所有有限颜色按严格相等判断。
- 普通持有武器随新区底色更新；单独外部玩家根染色保留，玩家内部色变和滤镜不变。
- 真实 Box 在模拟原生持物状态时保留念力色；调用真实公开 `player.dropTeleObj()` 后，恢复为新区底色，随后重复染色仍稳定。
- 非大场景的更新入口保持不写入。公共状态、显示对象/武器引用和区域颜色引用均恢复。

NaN、正无穷、负无穷仅在独立 Sprite 上记录观察结果，未写入玩家或箱体，也不作为必须显示同色的通过条件。不能据此宣称损坏颜色输入已有完整运行覆盖；生产新增规范化路径会先拒绝非有限预期值。

早期 `baseline-r1` 保留为失败证据：它把原始颜色当作显示读回值的预期，因量化而误判。r2 使用独立真实 setter/getter 修正预期，没有放宽容差，也没有覆盖 r1 证据。

## 部署与门禁

正式新宿主 SHA256：`A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7`。ContinuousScene 仍为 `7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F`，本轮没有替换模组发布文件。

已交叉核对的小 JSON 回执：

| 文件 | SHA256 |
|---|---|
| [product/build.json](../../build/generated/scene-compat-20261024/tint/product/build.json) | `7B62C88F5C918E07DDA31178DF788CD2195ACE4B092CFBBA8F9BE087105EA74D` |
| [semantic-audit.json](../../build/generated/scene-compat-20261024/tint/product/semantic-audit.json) | `0A24C942735D105956DAC367B8097A34E1DA57F747403080493C917B61F5CF83` |
| baseline-r2 summary | `B8E425F6A29DB1A1ADCBA780BC1799A320DE69DE644FE0A22805EDF406292E79` |
| candidate-r1 summary | `AD6B929A1B77ED075B89A62BA1FBDDFA3E316DBEBE8502B371DC5AE1D817DBEB` |
| installed-r1 summary | `A0DB3947C439D9F1A74DF28D8A3CA45C88E2962A2EF29934B97806566CB2D825` |

[正式部署回执](../../state/scene-tint-deployment-20261024.json) 为 `verified`：2026-10-24 11:07:24 安装，11:09:41 通过正式路径组件复验。回执安装前后各记录 526 项输入，只有根 `pfe.swf` 从 ABE2 变为 A796，其余 525 项一致。构建回执和组件摘要中的 `deployed=false` 分别表示冻结产物元数据、组件 runner 不执行部署；实际安装状态以此部署回执为准。

部署只接受准确 ABE2 基线、两方法保留审计及匹配候选哈希；正式依赖需与候选测试快照一致。安装后 runner 从正式文件复制到隔离运行目录，不用候选产物覆盖该副本，强验安装宿主、原始基线及来源标志后重新完成组件检查。登记、私有桌面/存储、内存保护和运行输入核对沿用测试入口。执行依赖 Python 断言，不能用 `-O` 或禁用断言的环境运行。

## 回滚路径与未覆盖范围

本次没有触发回滚。准确 ABE2 备份位于：

`build/backups/scene-tint-20261024-110720-c26a0e46/pfe_before_ContinuousScene_tint_20261024.swf`

部署脚本 [release.py](../../build/generated/scene-compat-20261024/tint/release.py) SHA256 `2BFE8BD52BC263D9181DF670851C4E95F33D07E685FD3710E8CA4CAB565C8EA6`。安装替换后立即标记本轮已写入，替换至正式复验都在同一异常保护中；失败日志写入失败不会跳过回滚尝试。回滚只允许当前正式宿主仍为本次 A796、备份仍为 ABE2，通过已核验哈希的临时文件原子替换。若宿主已被其他工作改变则阻止覆盖；发现未知 AIR 进程则明确记为暂缓，不关闭进程。回滚路径本轮仅静态审查，未做故障注入实测。

此组件在恢复公共状态后立即终止独立进程。Grafon 私有弱缓存无法经公开接口完整恢复，报告明确 `privateColorCacheRestored=false`、`terminalProcessRequired=true`，因此不得在该测试进程继续游玩、存档或采集性能。

尚未由这三组证据覆盖：完整工厂区到普通区的自然行走/悬浮输入、长时间反复换区、所有模组效果组合及地图退出流程。方法组件通过足以确认这里的两个受控缺陷与保护条件；不能替代这些玩法验收，更不能用来宣称战斗卡顿已改善。
