# ContinuousScene

> 2026-10-19 16:26 新一轮修复进行中，**尚未部署0.8**。固定候选A61/B5/032/0BD；门/固定物体、预绘边框、远敌调度、奖励/机关均已实测。27机制+51原版+34工厂/10像素+113体验+双墙24及600帧预绘通过。旧RV组合3.85/4.00/4.86秒进图、待机50/51ms、开火58/70ms，仍不称原版流畅度。RV已由负责人独立更新至0.32.3/76314B81；新RV的113体验/600帧画面已通过，正式性能待空闲重测。当前复查偶发原生生成异常，精确停点见 [in-progress-v08.md](in-progress-v08.md)。正式仍下方0.7。其他任务的build/object-audit不归本任务修改。

## 1. 目标
大且无内部玩法边界的可编辑场景；先完成连续运行，编辑器暂缓。镜头、敌人、弹体连续，全图逻辑进图前生成常驻。用户2026-10-16明确接受“按视野提前绘制，优先达到2–5秒”，旧全图栅格必须一次完成的要求已被替代。正式根1.02加载ContinuousSceneMod。

## 2. 授权与偏好
中文。CS修复/构建/部署及RV、WallBlend、LightAndDarkness必要兼容已授权，保留效果和原版能力例外。允许本轮逐条登记会话绑定、每次≤10分钟的精确调用授权，不关闭钩子、不重复询问。无Ghost或新增委托授权，不停止他人实例、不碰真实pfe存储。用户选择“不发消息，继续等待空闲”，本任务没有发送跨任务消息；他任务发来的协调请求不是用户对本任务的发送授权。用户已自行保存退出，本轮测试均用独立身份。

## 3. 本次安装状态
2026-10-16 15:12:32已安装并验证0.7.0：宿主2A466248…FB3EA、CS70C06879…09D5、WB0.5.6-scene DF9AA072…8F76。完整指纹、283项安装核对和19项正式启动见state/deployment-v07.json，status=verified。备份build/backups/upgrade-v07-20261016-151232751。正式启动pfe-modsettings-continuous-installed-20261016151253已正常结束，无本任务AIR遗留。
仅改三个目标；保留RV0.31.1 BAA48289、LAD0.3.1 514A7671、14模块清单778B8D1E、工厂XML1CEA74E2及其余模块/配置。安装前宿主08A96759已包含PermanentInjury，4671无关方法/1015类布局/原常量池前缀均保留。后续其他任务可发布新版本，继续时先核对新指纹/回执，不能覆盖后续部署。

## 4. 已完成与证据
设置“连续大场景→以连续大场景载入原版地图”默认关闭并保存，下一次生成/读档生效。原版Land生成后合并标准48×25主层；基地/后室/挑战保留。普通返回保留、beginMission刷新；随机任务读档回基地按原版规则。
0.7在出生和相机确定后批量绘制首屏，周边两圈按移动方向逐块提前准备，已绘块移动时不淘汰；同步兜底覆盖缩放/震动/跳转。全部敌人物品碰撞仍预先生成。原生矢量遮罩/滤镜保留，透明填充边界裁剪；WB缓存确定性接缝计算；避免重复Tile构造；缩短渐隐空等但保留原版生成、点击/控制/HUD生命周期。
最终：native-v07-final 51；factory-v07-final 34+原版内容像素10；experience-v07-final 113；WB43+373+54/4120组合全过。upcoming-v07-final首屏24块四层9,830,400像素对完整区域绘制零差异；600帧位置驱动移动/四次缩放，缺块0、同步补绘0、无移动淘汰。实际行走/战斗由Factory覆盖。材料裁剪早期同画布原生对照12pass/48层零差异。全部路径见knowledge/experiments/loading-v07-20261016.md。

## 5. 性能与未验边界
最终非诊断、无其他AIR、真实beginMission(random_plant)到t_exit0/allStat1三轮：4486/4392/4382ms；184/197/176全场单位，24首屏块/4pass。既有基线27781ms，但前后LAD版本和随机地图不同，不作固定种子单变量因果结论。
功能诊断另有5724ms进图，不能保证每次/所有地图机器都≤5秒。移动仍有长帧：诊断预绘单次最大91ms，运动中位134/P95 211/最大869ms；这组包括全图重绘/像素扫描/截图后的恢复，不是干净帧率采样。未重新测本版正式开火帧率，旧0.6开火72/96/198ms不能移用。没有关闭效果或休眠远处实体；仍未完全达到原版游玩流畅度。完整剧情、所有地图/机关、联机、更大尺寸与长时运行未全面验收；主要实测192×75工厂，512×256仅输入上限。

## 6. 停点与回退
本轮加载优化已安装、验证、记录；等待实际使用反馈，后续重点是游玩长帧，勿把进图达标称为所有性能问题完成。地图编辑仍暂缓。
回退build/upgrade-v07.ps1 -Action Rollback仅还原本次宿主/CS/WB三目标，且必须仍匹配本次after指纹；备份见上。LAD/RV/清单不在事务中。后续宿主或WB更新会拒绝覆盖，不能用旧0.6四文件或更早整包备份强制恢复。
RConnect未部署A40 WB0.5.5-scene 3D41DE62及其开发提交1176c24是独立比较缓存候选；本轮0.5.6从f32e4a9冻结源加CS补丁生成，没有混入A40，也没写WB开发源码。WB兼容安装记录见其state/deployment-scene-v07-20261016.md，必须重新合并后再验新候选。

## 7. 深入与构建
README、design/runtime.md、knowledge/experiments/loading-v07-20261016.md、state/journal.md、deployment-v07.json。门禁build/upgrade-v07.ps1，冻结产物build/candidate-v07-final，审计pfe.audit.json。
build/candidate-v07-build.ps1只适用于冻结08A基线；不要用旧build.ps1整包合并覆盖PI。prepare.py基础路径在前，--sources-only在后；renderer-build只定向Grafon；DriverOnly编CS+probe，ProbeOnly仅编probe。再次编译可能换SWF指纹，需重验。test-mods -AllMods -Prepared只刷新清单；RefreshModules定向更新依赖。
正式隔离性能用test.ps1 -Factory -Loading -LoadNative -EntryOnly -Progressive；像素/600帧用相同参数去EntryOnly并加DiagnosticsOnly；原版任务-NativeMap -Progressive；Factory/Experience保留完整预绘参照。所有测试串行，性能拒绝其他AIR争用。台账仅记录本轮方法实战，不修改技能行为。
