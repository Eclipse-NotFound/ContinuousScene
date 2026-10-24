# 同一大场景内区域底色残留：独立组件

2026-10-24。用户已确认是**同一大场景内换区域后，角色颜色没有更新**；并非已经证实离开整张地图仍残留。这里只新增诊断组件，未修改宿主/模组、未构建、未运行或部署。

## 已核静态路径

当前宿主 ABE2 是 80CF 上仅替换 `Camera.calc`，本问题相关的 Grafon / Unit / UnitPlayer 仍沿用冻结源码：

- `build/generated/motion-direction-rays/source/fe/graph/Grafon.as`（75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB），`sceneUpdateEntityColor` 1170–1211。
- `build/generated/player-step-profile-20261022/original-31fd028e520f4a7eaac0d98d7dde0b4f/scripts/fe/unit/Unit.as`：1828 每帧调用 `setVisPos`，2973 调用上述实际方法；玩家没有重写 `setVisPos`。
- `build/generated/player-animate-profile-20261022/original-8fbf3776cd7b4b29ba1bd8549b2a6714/scripts/fe/unit/UnitPlayer.as`。

具体反例：玩家处于 A 色区域，自主悬浮时 `levit=1`（UnitPlayer 2792–2803），跨入 B 色区域。Grafon 1195 因 `levit!=0` 拒绝更新根 `vis`，但 1197–1198 已将逻辑 `cTransform` 和缓存 `base` 推进为 B。后续同一区域 1193 因 `original===desired` 直接返回，停止悬浮也不补刷，因此仍显示 A。现有普通武器分支 1208–1210 不受 levit 门控，可以同时出现“武器颜色已更新、身体未更新”。这是确定的代码反例，尚待本组件实际重现；用户没有确认当时是否悬浮，不能把该触发条件写成已观测事实。

两种 `levit=1` 不能混为一谈：

- 玩家自主悬浮：UnitPlayer 4133–4139、4178 只设置 `vis.osn.filters`；死亡色也是内层 `vis.osn.transform`（4207、4227）。不会取得玩家根 `vis.transform.colorTransform` 所有权。
- 念力拿起箱体/敌人：UnitPlayer `actTele` 1834–1842 确实写被拿起对象的**根**滤镜和颜色；`dropTeleObj` 1927–1933 恢复其最新 `cTransform`、清掉 levit。此保护仍要保留。
- 正常整图/后室切换走 Land.ativateLoc 1318 → UnitPlayer.inLoc 654–659，重新给玩家与普通武器赋新 Location 底色。当前反馈无需扩展这条生命周期。
- 准确 RV 0DBE 的独立只读审查未发现玩家根 CT 或 gg.cTransform 写入，仅 fogShadow 写 CT；这不能证明所有其他模组都不写，故仍保留原值所有权检查。

## 最窄修复建议（尚未实现）

只把 Grafon 1195 的 `target.levit == 0` 改为 `(target.levit == 0 || target === World.w.gg)`；保留 `!highlighted`、根当前 CT 与旧基色逐项相等的检查，以及所有外部 `cTransform` 引用所有权保护。

这样玩家自主悬浮时，只有仍由原生底色控制的根图像会更新。被念力拿起的箱体/敌人继续保留魔法颜色；其他模组/效果已经写了不同根颜色时也不覆盖。不要清空玩家所有滤镜、重设毛发颜色、改动地图色彩或每帧重刷所有显示颜色。安装后按正常重启/入图重新初始化；此一行不声称能修复已存在于同一运行进程中的旧私有缓存残留。

## 组件接入

类 `tests.SceneEntityTintChecks`，文件 `SceneEntityTintChecks.as`。

`run(w, check = null, expectFixed = false):Object`

- 基线 ABE2 用 `expectFixed=false`：要求实际观测到残留；`passed=true` 表示反例成功重现，**不表示产品修好**。
- 修复候选用 `expectFixed=true`：要求悬浮跨区及停止悬浮后身体已经更新。
- 输出 `cases[].passed`、完整 `observations` 的八个 CT 分量、`residualReproduced`、`nativeCalls`、`elapsedMs`、`restore.passed`。
- 真实宿主域 World/UnitPlayer/Box 身份，真实既有两个 region；只临时把两个 style 的 CT 设为原生 `colorFilter('green')` 与 `colorFilter('')`。没有复制算法或伪造 target。场景需已有两个区域和带 vis 的 Box。
- 覆盖普通跨区、悬浮跨区与连续补刷、普通武器、念力箱体跨区与真实 `dropTeleObj` 释放、外部根 CT 不被覆盖、内层效果不变、非大场景 updater 早退。最后一项不是实际离图验证。
- `terminalOnly=true`：必须隔离 appID `pfe-modsettings-continuous-motion-*`，同步运行后终止自有测试进程，不保存，不继续游戏或计时。组件自身不启动/关闭进程。
- `restore.passed` 严查所有触及的**公开**引用与值（区域 CT 引用、玩家/箱体 X/Y/levit/逻辑 CT、根/内层/武器 CT、滤镜、teleObj、pause/shine/counter）。Grafon 私有弱缓存无公开恢复入口，明确 `privateColorCacheRestored=false`。真实释放会刷新 GUI 魔法值文本。这两个终端诊断限制不能冒充全内部状态逐字节还原。

后续自然复验只需原生实际操作：同一大图从有色区进入无色区，分别步行和自主悬浮；落地后原地停留，再返回原区域；手持普通武器；另拿起真实箱体/敌人跨区后释放，确认魔法色期间保留、放下恢复新区域底色。不要用每帧 setLocPos 构造“自然运动”。

## 隔离入口与源码候选

`run.py` 只接受当前 ABE2/CS7F1F 正式输入；其他正式依赖取本轮完整指纹，运行前后及冻结编译回执逐项核对。它复用现有登记、唯一 appID/私有桌面/独立存储、启动内存门槛及运行中 512 MiB 可提交余量保护。启动到真实大场景后，在通用探针的路线、测试敌人、开火和性能采样之前直接执行本组件并终止。`probe_patch.py` 只改冻结副本里的入口并加入本 helper，不修改共享源码。

基线复现（由主任务登记执行；本次未执行）：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'mods/ContinuousScene/build/generated/scene-compat-20261024/tint/run.py' --name tint-components-20261024-baseline-r1 --baseline --compile-probe
```

候选复验：使用上轮输出的原始 `probe-build.json` 路径和主任务实际完成的保留式候选 `build.json`，不能传 evidence 中缺编译日志的副本。

```text
run.py --name tint-components-20261024-candidate-r1 --host-build <实际候选build.json> --probe-build <基线原始probe-build.json>
```

候选回执需绑定 ABE2、`fe.graph.Grafon::0:1:sceneUpdateEntityColor`、产物/XML/审计哈希和源码输入；审计必须证明仅该方法变化、5770 其他方法和 1016 类布局保持、无新增字段/方法/类初始化变化。没有预先批准或锁定未生成的候选产物。基线 `expectFixed=false` 与候选 `true` 来自运行器冻结的明确控制文件，不能根据运行结果猜测。

源码层最小替换仅为：

```actionscript
// before
var displayOwned:Boolean = target.vis != null && target.levit == 0 && !highlighted
   && this.sceneEntitySameColor(target.vis.transform.colorTransform,original);
// after
var displayOwned:Boolean = target.vis != null && (target.levit == 0 || target === World.w.gg) && !highlighted
   && this.sceneEntitySameColor(target.vis.transform.colorTransform,original);
```

敌方抓取的补充只读证据（均为 `game-reference/decompiled/1.02/src102/scripts/fe/unit/` 原生资料，不使用另一会话天角兽候选）：

- `UnitAlicorn.as:1177` 与 `UnitBossAlicorn.as:628` 的 `upTeleObj` 明确只给 **非 UnitPlayer** 根图像加 teleFilter；玩家改的是 `fracLevit/levit`，并由 `UnitAlicorn.as:1148` 设置 `levitFilter2`。玩家 `setFilters` 将它放到 `vis.osn.filters`。允许玩家根底色随区域变化，不会删除这层被抓取效果。
- `UnitZombie.as:1178` 抓取设置 `levit=2`，随后给玩家设置 `levitFilter2`；这里不写根 ColorTransform。
- `Effect.as:271–278` 的冰冻效果会将冻结色与原底色合成写到根 CT。它与原底色不等，原有 `sceneEntitySameColor(...,original)` 将继续拒绝覆盖；`Effect.as:383–392` 结束效果时恢复最新逻辑 `owner.cTransform`。因此不要移除同色所有权条件。

这些是源码兼容性依据，不冒充敌方抓取和冰冻的实际操作验收。组件的外部根色保护覆盖相同的颜色所有权分支，但不重放完整敌方 AI 或状态效果生命周期。
