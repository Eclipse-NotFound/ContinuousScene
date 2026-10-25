# 活动范围候选：离线几何核对

2026-10-25。仅此目录的 `offline_geometry_check.py` 与本说明由当前审查者维护。没有编译、运行游戏或改正式文件。

已读 `source-candidate/SceneActivityCameraRange.as`，当前核对版本 SHA256 `898D0C6C260A49FC3DD5FF8B374933845A168948F3FACAA90A669FB903A99227`。最初 `C05A56EC4A8D75609ED694F47CD8A0DF59EDA10FE71EDEEE97DCE92ACDD6C63A` 的几何已通过；中间版 `7B37947202A01F690485163613E6BA4CBAD7907161CD70984113D748154E7DC1` 只增加编译器所需末尾return和post-check普通跟随/比例/尺寸复核；当前版再增加Verify中旧near独有休眠数量及至多8个数值例。脚本在内存中逐项逆变换，依次严格还原7B与C05完整指纹；几何未变。脚本把 `offset` 与 `plan` 的纯几何部分显式映射为受测对象，读取时锁住完整源指纹；不能自动跟随以后源码变化。不是执行AS，也不验证实际Stage、跨域对象、菜单状态或首帧等运行时资格守卫。

原生依据为 `../vertical-camera-band-20261023/source/fe/inter/Camera.as`，SHA256 `392218D33CAD0A9ACB1C5237281B407A513E6360DD8E8454A8260C24598A4C70`。X/Y/vx/vy/ovy/maxvx/maxvy 为 int；普通跟随的 reset、缓冲和旧缓动三种 Y 路径见287–305行，限界与隐式int赋值见311–340行，quake随机保持/反向衰减/小值归零见344–363行。

独立模型执行上述具体分支，而不通过同一份区间包围函数推导“原生结果”。按每次int赋值执行截断及32位回绕；不能用Python的floor或round替代。显示坐标运行时取整仍需保守余量，离线程序不冒充真实DisplayObject setter验证。

边界集包括0.5/0.8/1/1.25比例、偶数和奇数屏幕、maxvx/vy为正/零/负、旧缓动5/50严格边界、普通移动与大位移、当前实际visual位置与当前quake字段不同、quake保持/衰减/归零。随机输入使用固定种子，输出只写stdout，不生成缓存或证据文件。

硬边界：activity之后、Camera.calc之前仍有对象更新。后来新增的quake、玩家位置、缩放、尺寸或其他镜头写入不在这个模型保证内。即使候选区间包含所有已测原生结果，也必须另核真实逐帧包围、醒来与交互生命周期；没有帧率、玩法或部署资格。

## 已执行的纯Python检查

命令（`-B`禁止生成字节码缓存；JSON仅stdout）：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene/build/generated/activity-camera-range-20261025/offline_geometry_check.py'
```

首次原生模型检查4188姿态，8个ToInt32基础例、55个quake基本例；首轮候选比对exit0、约0.93秒。最终898D版本已重新执行同组检查，exit0、约0.79秒；观察计数逆变换及编译器/后验守卫逆变换均逐字节通过。最终脚本SHA256为 `5C638773220AD82BD47B94B7E576E1582E0A8BF8EB25DA1F187CFE957E4EBB21`。结果：

- 4184个普通姿态，另4个moved=false明确列入回退，不伪装成候选启用。
- 每个姿态25种独立X/Y quake保持或衰减选择，并以0/正负0.05 Stage像素作额外坐标扰动，共313800个结果；`predicted`和最终`planned`均包含原生结果，严格零比较容差，0违例。
- 4184次当前actual视口包含检查通过。actual位置与当前quake字段独立提供，未假定两者同步。
- 实际原生分支覆盖：reset34475、band34300、legacy-direct31075、legacy-quarter4750（这些是每次quake组合计数，尚未乘3个坐标扰动）。
- 14个不安全几何输入被适配层拒绝，包括非有限数、非正比例/屏幕、非整数字段及可能int溢出；这是数字资格映射，不是AIR守卫实测。
- 删去下一视口、删去当前实际视口、删去quake界限的三个负例均不能覆盖对应实际结果，防止空的或只比较同一公式的假通过。
- 三个明确未覆盖的后写入反例（新增大quake、玩家在计划后瞬移、计划后改scale）确实越过既定范围，原样作为限制输出，未靠扩大包围到全图让它们通过。

`conditionalGeometryPassed=true`仅表示这批有限案例的条件几何成立。原生分支模型直接执行每次赋值与选择；候选则使用端点区间包围，两者不是同一份包围算法互比。某些合成分支/尺寸组合并不一定对应可达游戏历史，保留它们作为更宽的数学压力输入。±0.05扰动也不是对AIR DisplayObject setter取整方式的实测。`runtimeGuardsExecuted=false`、`lateObjectWritesProvenSafe=false`及`productionAcceptance=false`保持明确。
