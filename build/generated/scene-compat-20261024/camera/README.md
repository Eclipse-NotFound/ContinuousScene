# 密集战斗镜头归因：仅隔离诊断

本目录从已实际通过的 `dense-sprint-2` 探针39A1497B冻结源复制，只新增镜头helper及6处接入，不修改其SceneEncounter、SceneDenseCombatMetrics、真实Shift移动、六名LMG敌人、ASSR射击或单次出生定位。当前正式ABE2宿主直接复制至隔离实例，不替换任何游戏方法，不部署。

四段各300帧依次为跟随、固定、固定、跟随。B段只设置`cam.moved=false`，不跳过原Camera.calc、sceneTick、瞄准转换或开火逻辑，不关闭AI、子弹和自然敌人。两个连续B段保持同一视口。结束只恢复注入的moved控制，不回写已经过时的镜头、玩家坐标或原生verticalCameraState。该状态由真实Camera.calc自行处理，helper对API没有写操作。

每帧记录真实位置/速度、镜头坐标、视口、原生活动统计、缓存计数及helper开销ownMs。完整平台和玩家/六敌的**碰撞身体**必须在视口内；这不是武器、特效或其他显示根完整在屏幕内的证明。原夹具的每30帧存活/持枪/双方实际射击门禁及逐帧子弹并发检查保持。相机抖动不会被强制消除，B段发生抖动即拒绝。提前结束保留不完整标志和已采样世界坐标。

准备阶段在生成夹具敌人与唯一玩家定位之前，用公开sceneTick同步准备原视口及已验证平台附近的缓存。仅临时改变镜头逻辑视口与asyncWarm，finally恢复，检查玩家位置/速度与单位数未变；不推进World.step。新增缓存有意留存，耗时单列，不冒充天然探索或初次加载时间。驻留上界256不放宽；计时期间任何resident/warm/slices/forced/misses/evictions变化拒绝整轮，但命中修改已有地形的redraw仍保留并记录。

主序列保留全部1200个连续时间间隔，不删切换帧、不扣观察开销。段边界间隔跨越前一帧和新控制，不能称纯粹某模式绘制成本；四段300帧选择是为了保留现有严格连续时间及火力审计。固定视口也可能影响可见范围参与的原生活动、声音中心等，只能归因“镜头跟随相关路径”，不能直接称GPU或某单一函数耗时。动态自然敌人和随机战斗仍是混杂，应同时读活动/火力/并发。结果不是无探针的最终游戏FPS。

灯光、RealisticVision、WallBlend均关闭；不覆盖用户另报的RV开启后卡顿。原耐久敌人/伤害2、玩家godMode及弹药/耐久补充按原夹具保留，仅用于持续交战诊断。

## 冻结与运行

固定宿主：`ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A`。
固定CS：`7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F`。
固定RC：`DF0FA0E2CA952E77E5132E75D71E73558DC919C7B8CDEBA5DA05FC9E94DC01E7`。
RV及所有其他正式依赖、配置、编译工具、运行器、85文件原探针树与新helper逐项冻结。构建/运行前后及复用均拒绝变更，不混合owner独立更新前后的结果。原探针回执固定`B7ED1EAB…B35FF13`，完整常量见run.py。

尚未构建或运行。由根任务按既有精确授权执行下列命令；run.py自行登记、等待空闲、注册编译子进程，并使用私有AIR桌面/唯一APPID/独立存储。先检查至少4GiB提交余量、2GiB物理余量，保留旧运行中512MiB提交保护。不结束外部进程。

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene/build/generated/scene-compat-20261024/camera/run.py' --name camera-combat-20261024-r1 --compile-probe --registry-wait 600
```

以上先构建再运行，输出冻结probe-build路径；重复轮用新的证据名及该路径传`--probe-build`，不重复编译。预计首轮约3–5分钟加共享测试位等待，真正计时1200帧约70–90秒；准备耗时、失败和超时完整保留。证据写到本模组`knowledge/experiments/evidence/<name>`，测试源码和编译产物只在本目录新树，正式安装不变。
