# ContinuousScene

## 1. 目标
大且无内部玩法边界的可编辑场景；当前先完成运行，编辑器暂缓。镜头/敌人/弹体连续，全图进入时生成、逻辑和画面常驻，原版房间作验证素材。

## 2. 授权
中文。用户明确授权CS修复/构建/部署，RV、WallBlend及LightAndDarkness必要兼容改动，保留效果和原版能力例外。允许本轮逐条登记会话绑定、每次不超过10分钟的精确调用授权，不能关闭钩子；无需重复询问。无Ghost授权，不关闭其他实例，不碰真实pfe存档。没有新委托。

## 3. 正式状态
正式仍CS0.5 / RV0.30.5-scene / WB0.5.3-scene；LAD已由原任务升级0.2.0，必须保留氛围新功能。0.6尚未安装。原0.5回执state/deployment-v05.json，回退build/upgrade-v05.ps1，旧整体回退禁止覆盖后续更新。

## 4. 0.6候选
候选宿主11BCECA88365AB00A29A99511380CBAFA35F18CE9BF4465BE66FDAD16AD1BD4F；CS F6ED93AFF2BFB76B4AE8CA2A2E01B84BBE4D24A8DD59EB4DE720847C8457D8D2；WB 3B1B40A65D7C57E4711C3861463B3470B0DFC086A8C8C01870C91A2F413DA96F；LAD8125FD509F824E326B31CE3A6AC7D96023C9E468E84A393CA9080FC28477735B。
NativeSceneAdapter/设置已实现：nativeEnabled默认false，原版生成后的主层合并；基地、后室、挑战保留，普通返回保留、beginMission刷新。随机任务读档回基地是原版Game规则，再次进入仍按设置大场景生成。
区域一次预绘12pass，保留240个小伤害块；遮罩父缓存清理；WB预先释放旧覆盖；原版/LAD恢复光照smoothing；SATS捕获补齐隐藏块。LAD首次栅格前转换灯具，免二次全图绘图，HUD缓存、离屏灯壳仅隐藏显示；新任务清对应灯具存档。WB精确前缀计数/保护查询缓存。
RV最终运行代码未改，但重编产物A3E2F4634F62CD1C2E10C4733E1CE9EEB3BF85F11FE2B385DBC47AFA8C1F336E与正式B7695DF82AA45FDB783C4EB88AFFCB0C34A7674E3A052D2FD128867172A83A49仅ProductInfo最后8字节日期不同。verify_rv_rebuild.py固定双完整哈希并比较除日期外所有解压字节；保留正式RV，不复制候选。不能扩成任意等价例外。

## 5. 当前验证与停点（21:38）
用户明确选择不向其他任务发协调消息，继续等待空闲。不得跨任务发送消息或停止其进程。shell89909等待空闲后已开始perf-v06-final（自有AIR40568），随后顺序native/factory/experience/lab-v06-final2；Perf若重叠失败仍继续四套功能，不将失败结果当性能通过。
当前隔离依赖已精确匹配正式ModLoader BD71B6F3…4908B1、FA B3304596…D2A4B9、RR14 26989527…CE2AB及其他模块。先前current组合Native51、Factory34+像素10、Experience113、Lab63全部通过，但用旧ModLoader/FA，留作历史。Factory原始11/95/0/0像素差，无透明差异、无通道差超过8；不可称零像素差。
WB三套11B宿主/3B模块全过：Harness43 wallblend-test-cs053-harness-20261015210548-a2cf31；Coverage373/4120组合 wallblend-test-cs053-coverage-20261015210643-744b3d；Destruction54 wallblend-test-cs053-destruction-20261015211025-eae3f6。
LAD8125最终专项81项：remains-lad-test-20261015213154464；同身份冷读档7项：remains-lad-test-20261015213154464-cold-213433。包含最终ModLoader BD71、11B/CS/RV/WB/配置七项指纹。测试已结束。
LAD快捷键另任务已提交8d302fb/a53aad9；本任务随后4619ac2仅提交兼容增量，主源为scene-keybind-dev合并开发版。发布仍用已测8125（不含快捷键）。build/scene-v021-release.patch已入库，针对84f1d79复原独立发布源码，原快照完整哈希已核对；不要直接重编混合主源冒充8125。正式LAD仍0176。
待：最终四套/Perf、Factory核对、门禁Check/Install/installed-smoke，最终文档和部署提交。Gate须显式传final2四证据及上述WB3/LAD2；默认旧证据已过期。不要再次编译候选。

## 6. 性能边界
同中间宿主/RV/WB，LAD0.2基线进图29.235s，开火中位/P95 63/84ms；兼容候选20.373s、50/69ms，同期原版43/70ms。随机单位145/147，不是严格种子A/B，未承诺稳定30fps；最终性能尚待。区域诊断native全重绘7.569s、WB8.528s，旧LAD重复生成那轮33.669s不是最终值。多任务同时测游戏会污染耗时；不得杀他人进程。

## 7. 发布入口
README、design/runtime.md及knowledge/experiments/native-v06-20261015.md已更新候选状态。门禁upgrade-v06.ps1只写宿主/CS/WB/LAD四项，核对正式0.5及LAD0.2回执、其他模组、五主套件和WB3/LAD2证据。尚未通过/运行Install。RV时间戳例外已绑定完整字节证据，所有其他模块必须精确匹配。installed-smoke.ps1可传LightVersion0.2.1-scene，菜单只检查LAD版本/错误，灯具心跳属于游戏内测试。
完整构建固定C631原备份+RConnect Map1 BEBEEA8B，17个指定方法/4652无关保持；不要拿安装宿主重复补丁。RV/WB冻结源仍0735491/f32e4a9，不混其他WIP。无收益RV子bitmap裁剪脚本已删除，生产未启用；其他诊断脚本只保留作复现。失败证据和旧0.5调查完整保留。
