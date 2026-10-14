# ContinuousScene

## 1. 这个模组是什么
大的无内部房间边界场景。镜头、敌人和子弹连续运行，单一Location持有全场逻辑；进图预绘全部320px画面块并常驻。入口ContinuousSceneMod；信息页顶部进入/返回基地。

## 2. 用户偏好与授权
中文交流；编辑器暂缓，原版房间只作测试。2026-10-14 用户要求接入游戏入口，并明确允许 RealisticVision、WallBlend 必要兼容修改。已授权部署，不重复询问。测试独立身份，不碰正式存档，不关闭玩家游戏；未授权 Ghost 或并行委托。

## 3. 当前状态
0.3.0于2026-10-14 23:10安装到实际1.02根pfe；RV v0.30.4-scene、WB0.4.2。192×60（7680×2400），进图192块全部生成，行走零补块。像素共享、局部脏区、RV按需复制子格快照。48完整运行、43墙面、42视野、15安装后原生启动，共148项通过。清单保留，包括本轮新增FirearmAttachments，测试驱动未安装。

## 4. 本轮交付与停点
用户要求的进图预生成方案已实现并安装。后台顺序A/B/A证实无沿途生成，但整体帧率增益有限；遮罩范围实验无稳定收益已撤掉。原生安装启动通过，正在等待实际试玩反馈；AGENT_SCOPE仍未创建，不绕过保护。

## 5. 已知问题
最终1699行走帧中位55ms/p95 73ms/p99 87ms/max213ms，未稳定30帧。首次进入约13.5秒；短程进程峰值约1.8GB，完整读档/SATS峰值约3.1GB。测试显式HighQoS仅作用于自身测试进程；正式启动器不变，不能保证用户同帧率。再进图/读档仍重新预绘。更大尺寸、密集长时/联机/全部水门剧情未验收，SATS仅画面。编辑器继续暂缓。

## 6. 后续与回退
下一步按实际试玩继续定位显示合成和长时内存。当前回退build/rollback-v03.ps1恢复0.2四文件，依据state/deployment-v03.json / build/upgrade-receipt.json；根备份pfe_before_ContinuousScene_v03_20261014-231026.swf，模组备份build/backups/upgrade-v03-20261014-231026。清单和配置不回写。不要直接用旧rollback.ps1回退当前版。

## 7. 接续入口
- README.md：使用、复建、回退；design/runtime.md：实现和边界。
- knowledge/experiments/preload-v03-20261014.md：本轮对照、取舍、失败过程、性能与边界。
- evidence/release-v03-final、vision-v03-regression、wall-v03-regression、pfe-modsettings-continuous-installed-20261014231050；安装回执state/deployment-v03.json。
- evidence/release-v02-final、vision-v02-regression、pfe-modsettings-continuous-installed-20261014181857。
- build/build.ps1 -BaseHost <上述原版备份>；-ProbeOnly仅测试驱动；-DriverOnly生产模组+驱动。test-mods -AllMods后再compat-build，不能反序覆盖新候选。
- RV兼容包从已安装源码0735491构建；RV HEAD另有authority接口及既有WIP，未发布。build/compat_prepare.py保存可复现变换。
- 自动test.ps1 -HighQoS -TimeoutSeconds 420，默认整图预绘；-Quick短程，-Benchmark 360帧，-Streaming旧策略对照。AIR ID pfe-modsettings-continuous-scene。compat-build -Profile只用于隔离诊断，正式构建不能带Profile。
- build/upgrade-v03.ps1固定0.2旧指纹和验收门禁；安装后不能重复覆盖。RV另一个任务4项既有WIP保留，不打包、不提交。旧0.2历史记录保留。
