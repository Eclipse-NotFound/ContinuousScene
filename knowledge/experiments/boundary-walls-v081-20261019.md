---
domain: world-objects
type: experiments
game-version: ["1.02"]
confidence: high
verified: true
discovered-by: ContinuousScene
date-updated: 2026-10-19
---

被测技能：diagnosing-bugs 2026-10-08.1；remains-runtime-debug / remains-auto-testing 2026-10-19.2；remains-release-gate 2026-10-19.1；remains-mod-build / remains-mod-memory / remains-knowledge-contribution 在册版。
技能归属：C:/Users/hello/.agents/skills；D:/Program Files/Steam/steamapps/common/Remains/.agents/skills。
测试工作区：D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene。

# 0.8.1：内部房间接缝恢复可破坏材质

用户要求在连续大场景中恢复原本可破坏墙的身份。本轮只改变原生地图合并时的伤害属性，正式宿主和其他模组未写入；另一个“大场景”对话的箭头、移动性能 WIP 保留但未混入产物。

## 根因与修复范围

1. 原版 1.02 `Location.buildLoc` 在房间边缘给实体格设置 `indestruct=true`。随机 `Land.buildRandomLand` 后续还调用 `Location.mainFrame -> Tile.mainFrame`，把边缘实体统一改为土地的 `border` 材质，耐久改成 10000、不可破坏，原 `thre` 未同步重置。
2. 旧大场景原样复用这些 Tile。`Tile.udar` 在不可破坏时直接拒绝伤害，`Location.hitTile` 无法破坏它们；因此材质 N 的楼房墙在房间内部为 hp1000/thre100，处在旧接缝却永久不能破坏。
3. 新 `NativeSceneWalls.restore` 在合并坐标前检查内部邻接边，只对当前材质可破坏、原模板也是实体且无固有保护的格子恢复；随机图按**当前可见材质**的 Form 恢复 hp/thre，固定图只移除边缘标记并保留已有损伤。保留外沿、接触外沿的角、缺房一侧、原模板固有保护、框架填出的空格、钢墙 A、门和陷阱格、未知耐久修改。
4. 图像、材质、碰撞形状、房门/机关引用均不变。不会把原本钢墙改成混凝土，也不会取消原版抗伤阈值；小破坏力武器依然可能打不动坚固材质。关闭连续大场景时不调用恢复。

接入为 `NativeSceneAdapter.prepare` 内一行 `state.boundaryRestored=NativeSceneWalls.restore(land,regions)`；每 Land 只合并一次，不增加每帧扫描。

## 实测

使用原版 `Game.beginMission` 生成地图，在 prepare 前后逐格比较同一批 Tile。全部 14 个正式模块通过启动器选择，测试探针为新增第 15 个入口；正式清单只读。每轮独立 AIR ID，使用 `air_test_process.HiddenProcess` 的私有后台桌面，未读取或写入真实 pfe 存档。

| 证据目录（本目录 evidence/ 下） | 结果 |
|---|---|
| boundary-baseline-mane-20261019 | 旧版复现：1535 个符合条件的内部边界格仍 indestruct=true、hp10000，0 个恢复；失败结果保留 |
| boundary-candidate-mane-20261019 | 20 项通过；1558 个内部边界格全恢复，其他格伤害属性/图像/碰撞/对象引用无变化 |
| boundary-candidate-plant-20261019 | 15 项通过；1556 个钢墙边界格保持，530 个外沿实体格保持，无可恢复当前材质格，不把此轮算作正例破墙覆盖 |
| boundary-disabled-mane-20261019 | 15 项通过；关闭模式后1598个候选格保持原版保护，未合并世界 |
| boundary-installed-mane-20261019 | 从实际安装文件回读，21 项通过；1587个内部格恢复，430个外沿格保持，版本0.8.1 |

各轮随机世界不同，数量差异不作生成数量变化结论。马哈顿真实生成格 (47,16) 的原生 `Location.hitTile` 流程：99点伤害被100阈值拒绝；500点使1000→500；足够伤害后 hp=-1、phis=0、front为空、opac=0，并使4个绘图块失效更新。受保护墙在100000点命中后仍保持。这里直接调用原生地形命中入口，**未声称遍历所有武器/实际连续开枪测试**。

固定地图保留已损耐久、固有钢墙、自定义耐久、外沿/角、双侧接缝、缺房、重复调用及镜像原模板保护由真实 Tile.dec 构造的局部夹具验证；不把这些夹具称为全固定地图剧情验收。正式马哈顿破墙前后截图已查看：地板接缝格出现实际缺口。候选首轮 before 截图处于瞬移后的旧视野，未当作视觉对照；正式回读改为等待12帧后再采样。

## 产物、部署与回滚

- 源码基线 `3882d90`，冻结发布源四文件加墙体 helper；未从含并行箭头 WIP 的工作树整包构建。
- CS 0.8.1：`241E48EA217D47932B6014B4AB213473E5FCF471E533CCB8F2CD91C4E15B02EA`。
- 宿主保持 `02BFABE6A3B4881DFA1227515E71F2A8EA863D4B1B468FBE1D8008AEBA7D9240`；RV0.32.3/76314B81、LAD0.4.1/94A2F086、TDFC03243196、WB0BD209A1、RC574D2B51均与测试冻结组合吻合。
- 21:37:36 备份并只替换 `release/ContinuousSceneMod.swf`。17个生产指纹、配置、原版房间 XML 在替换前后核对；回执 `state/deployment-v081.json` 为 verified，旧版 B5E8110E 备份在 `build/backups/boundary-v081-20261019-213736/ContinuousSceneMod.swf`。
- 回滚：`python build/boundary-wall/check.py rollback`，只还原该 SWF，当前文件不是本次241E时拒绝覆盖。需要正常重启游戏加载新版；当前已生成的房间在旧实例中不热改。
- 运行：`check.py prepare` 冻结基线及编探针，`candidate` 构建，`run --variant candidate --map random_mane --name <新证据名>`；`--disabled` 验证原版模式。历史构建器只接受 B5 正式基线，不能拿来覆盖后续发布。运行时副本在 `build/generated/boundary-wall-20261019/`。

## 技能与工具边界

实际使用了源码到失败复现、同一批对象对照、先候选后备份部署、安装文件独立复验。新启动器只发现 `*Mod.swf`：首次探针名 BoundaryWallProbe.swf 未被发现，新增 BoundaryWallProbeMod 入口后由启动器成功选入，未手写清单绕过。编译与选择失败未触碰正式产物。所有测试正常退出，无本任务 AIR 遗留。

未重新验收总体帧率、全部地图/脚本、联机和长期存档。图像外观不变意味着工厂原版生成的钢质边框仍不可破坏；把所有边框换成可破坏材质属于另一项设计改变。当前箭头清理与移动性能优化由另一对话继续，本轮不宣称解决。
