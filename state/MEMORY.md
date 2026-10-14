# ContinuousScene

## 1. 这个模组是什么
大的无内部房间边界场景。镜头、敌人和子弹连续运行，单一 Location 持有全场逻辑，320px 缓存块管理绘图。正式入口 ContinuousSceneMod；信息页顶部进入/返回基地。

## 2. 用户偏好与授权
中文交流；编辑器暂缓，原版房间只作测试。2026-10-14 用户要求接入游戏入口，并明确允许 RealisticVision、WallBlend 必要兼容修改。已授权部署，不重复询问。测试独立身份，不碰正式存档，不关闭玩家游戏；未授权 Ghost 或并行委托。

## 3. 当前状态
0.2.0 已安装到实际 1.02 根 pfe；RV v0.30.3-scene、WB 0.4.1。清单只追加 ContinuousScene 1|0|0，不安装测试驱动。192×60（7680×2400）场景；原版存档已补齐破坏地形和弹痕。44 项完整运行、43 项墙面、37 项视野、14 项安装后原生启动通过。玩家正常重启后可用。

## 4. 本轮交付与停点
入口、往返、跨界战斗、破坏持久化、RV/WB 兼容已交付。安装后曾因测试器嵌套 Loader/空日志类型出现两次误失败，均先回退再修验证器；最终正式文件启动通过。AGENT_SCOPE 仍因保护规则未创建，沿用根 GOVERNANCE，不绕过。

## 5. 已知问题
全模组步行中位56ms/p95 85ms/p99 123ms/max326ms，未稳定30帧。首次进入/瞬移同步补块；全场格子和实体常驻。只测当前尺寸、少量单位、1280×800、current视野；联机、密集/长时战斗、全部水/门/剧情未验收。SATS仅画面覆盖通过。大场景固定原倍率，编辑器暂缓。

## 6. 后续与回退
优先按实际试玩问题继续定位性能和交互，不自行恢复编辑器范围。回退脚本 build/rollback.ps1 依 state/deployment-v02.json 对应回执核验；当前根备份 pfe_before_ContinuousScene_20261014-181702.swf，清单/RV/WB备份 build/backups/install-20261014-181702/。回退前需离开大场景并保存，保留正式玩家存档。

## 7. 接续入口
- README.md：使用、复建、回退；design/runtime.md：实现和边界。
- knowledge/experiments/integration-v02-20261014.md：本轮问题、失败过程、性能、指纹。
- evidence/release-v02-final、vision-v02-regression、pfe-modsettings-continuous-installed-20261014181857。
- build/build.ps1 -BaseHost <上述原版备份>；-ProbeOnly仅测试驱动；-DriverOnly生产模组+驱动。test-mods -AllMods后再compat-build，不能反序覆盖新候选。
- RV兼容包从已安装源码0735491构建；RV HEAD另有authority接口及既有WIP，未发布。build/compat_prepare.py保存可复现变换。
- 自动test.ps1 -TimeoutSeconds 380；-Quick短程；-Benchmark 360帧。AIR ID pfe-modsettings-continuous-scene；旧remains.continuousscene.dev会触发MSW测试接管，不再用。
- 生产安装器固定旧指纹，已安装后不能直接再次覆盖；先核对当前版本。state/journal.md、state/deployment-v02.json。
