# ContinuousScene

## 1. 这个模组是什么
大的无内部房间边界场景。镜头、敌人和子弹连续运行，单一Location持有全场逻辑；进图预绘全部320px画面块并常驻。入口ContinuousSceneMod；信息页顶部进入/返回基地。

## 2. 用户偏好与授权
中文交流；编辑器暂缓，原版房间只作测试。2026-10-14 用户要求接入游戏入口，并明确允许 RealisticVision、WallBlend 必要兼容修改。已授权部署，不重复询问。测试独立身份，不碰正式存档，不关闭玩家游戏；未授权 Ghost 或并行委托。

## 3. 当前状态
0.3.1入口于2026-10-15 01:26安装，修复信息页菜单暂停导致按钮点击被拒绝。宿主仍为0.3整图预绘，RV v0.30.4-scene、WB0.4.2；192×60（7680×2400），192块常驻。新增63项短程回归和15项安装原生启动通过，覆盖菜单等待12帧后的进入/返回/再进入、旅行限制、战斗破坏与多存档。共享清单及其他模组字节保持，测试驱动未安装。用户需正常重启现有游戏。

## 4. 本轮交付与停点
用户反馈按钮无法按动：allStat==1门槛误拦菜单暂停allStat==2。旧测试同帧开菜单点击，且跳过开场对话；已补稳定时序和原版noAct限制。测试先按键完成对话、等待连续30帧可操作，再打开菜单等12帧点击。0.3的148项历史通过不代表普通点击已覆盖。进图预生成仍有效，性能问题和编辑器不在此次按钮热修范围；AGENT_SCOPE仍未创建，不绕过保护。

## 5. 已知问题
最终1699行走帧中位55ms/p95 73ms/p99 87ms/max213ms，未稳定30帧。首次进入约13.5秒；短程进程峰值约1.8GB，完整读档/SATS峰值约3.1GB。测试显式HighQoS仅作用于自身测试进程；正式启动器不变，不能保证用户同帧率。再进图/读档仍重新预绘。更大尺寸、密集长时/联机/全部水门剧情未验收，SATS仅画面。编辑器继续暂缓。

## 6. 后续与回退
下一步按实际试玩继续定位显示合成和长时内存。0.3.1回退用build/hotfix-v031.ps1 -Action Rollback，仅恢复0.3.0入口，依据state/deployment-v031.json / build/hotfix-v031-receipt.json；备份build/backups/ContinuousSceneMod-before-v031-20261015-012647.swf。如需恢复0.2，先回退入口再运行build/rollback-v03.ps1。0.3根备份pfe_before_ContinuousScene_v03_20261014-231026.swf。清单和配置不回写；不要直接用旧rollback.ps1。

## 7. 接续入口
- README.md：使用、复建、回退；design/runtime.md：实现和边界。
- knowledge/experiments/entry-v031-20261015.md；evidence/entry-v031-before为原版入口复现，entry-v031-final为63项通过。按钮测试使用真实监听器事件派发及命中区域检查，未用系统鼠标注入。
- knowledge/experiments/preload-v03-20261014.md：本轮对照、取舍、失败过程、性能与边界。
- evidence/release-v03-final、vision-v03-regression、wall-v03-regression、pfe-modsettings-continuous-installed-20261014231050；安装回执state/deployment-v03.json。
- evidence/release-v02-final、vision-v02-regression、pfe-modsettings-continuous-installed-20261014181857。
- build/build.ps1 -BaseHost <上述原版备份>；-ProbeOnly仅测试驱动；-DriverOnly生产模组+驱动。test-mods -AllMods后再compat-build，不能反序覆盖新候选。
- RV兼容包从已安装源码0735491构建；RV HEAD另有authority接口及既有WIP，未发布。build/compat_prepare.py保存可复现变换。
- 自动test.ps1 -HighQoS -TimeoutSeconds 420，默认整图预绘；-Quick短程，-Benchmark 360帧，-Streaming旧策略对照。AIR ID pfe-modsettings-continuous-scene。compat-build -Profile只用于隔离诊断，正式构建不能带Profile。
- build/upgrade-v03.ps1固定0.2旧指纹和验收门禁；安装后不能重复覆盖。RV另一个任务4项既有WIP保留，不打包、不提交。旧0.2历史记录保留。
