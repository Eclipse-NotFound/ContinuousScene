# 最新停点：2026-10-20，0.8.2已部署并独立复验

02:11安装81C1宿主、CD65入口和1411墙面兼容。598项发布前检查、51项实际安装后原版玩法复验通过；deployment-v082.json=verified。详见当前MEMORY、candidate-v082.json和motion-v082-20261019报告。用户“恢复实测”已取代旧“保留候选”。

关灯暖路线36–37ms接近普通33ms，但首次41ms、快速跨区46ms；开灯暖47–48.5ms仍未达标。安装时LAD4291，后续灯光任务独立验收0.5.1；已明确交还AIR/JVM，不再启动本任务实例。接续先核对正式依赖与灯光任务结果。备份motion-v082-20261020-021117，仅用motion-release.py的精确三目标回退，拒绝覆盖后续发布。

以下为历史停点，不作为当前执行指令。

## 2026-10-19 23:22，候选保留

用户要求“稍后再测，先保留候选”。停止新增游戏测试，不部署。正式02BF/CS241/WB0BD/LAD94；候选4D9/CD65/0DA/6F见candidate-v082.json。完整证据、失败与限制见knowledge/experiments/motion-v082-20261019.md，下文只是历史过程。

4D9已完成4672其他方法/1015布局/常量池审计，pixels-6十块四层逐位一致。adaptive冷104/P95 260、暖84/136、静51/83ms，冷3次同步兜底无缺块，后续0；图形片段最大42ms，但WB仍有峰值，不称流畅。WB0DA仅编译，测试在启动前因正式与第二玩家存在退出；LAD6F最终字节未标准回归。

runtime目前4D9/CD65/0DA/LAD94，最终6F尚未复制。motion-test --prepare会覆盖候选，慎用。恢复：核对正式依赖和空闲，WB --wall-check/关灯 --short、LAD像素+标准回归、全组合native/experience/factory/upcoming/mechanics及--visual截图，再完整性能紧邻对照与门禁。不要沿用旧整包升级覆盖RC安保。

motion-host.py incremental现可从原始配方再生，显式保留已发布compact-impact后处理；--source-only重建源码与4D9构建源同SHA E4425097，prepare.py本身无修改。WB用wallblend_motion.py从正式0.5.8配方生成，不能用未发布WB HEAD。保护调用按已授权会话<=10分钟逐条登记，无Ghost/子代理/跨任务发消息，不停止他人实例、不写真实pfe存储。

收到RC任务消息：对方正在调查联机布局模式不一致并请求保留实测基线；本对话未回复（没有新增跨任务发消息授权），本轮本来就不部署/不启动游戏。

---

# 0.8.2 移动卡顿与内部箭头（进行中，未部署）

22:42接续：分帧候选当前宿主FDAD5084（build/generated/motion-host-incremental/pfe.swf），其它4672方法/1015类布局/常量池审核通过。pixels-1遇FFDec把局部step()误译为fe::step，已改数组函数.call；pixels-2/3/4后层像素缺失，最终确认是生成器拆stage17时漏掉backBmp2.draw(back2)，已补回。曾怀疑MovieClip自行变化并尝试快照，未解决，已撤回；**不能把动画假说写成发现**。pixels-5实际10块×4层逐位相等（15断言含箭头），宿主FDAD；performance no-light-incremental-5却冷93/P95218、暖86/140、静止51/91，22可见同步补绘，未达到可交付要求。同期进图10.7s，其他命令也显著变慢；不能将该轮与一小时前旧基线直接比作因果。正在跑相同宿主sceneAsyncWarm=false/true、固定自建进程HighQoS两轮紧邻参考，证据motion-v082-no-light-sync-qos / motion-v082-no-light-incremental-qos。HighQoS仅用自己HiddenProcess句柄，保留其他状态，明确readback，不改用户进程/机器电源计划。

LAD版本现已在源码升0.4.2（Mod与Runtime三处）；构建候选build/generated/lad-motion-v042/LightAndDarknessMod.swf=6F138FB891A412905CA72EA94C47D4B48A72865A18C78603E844E0E2223816E0（33338B）。此最终版本尚未跑新版精确字节回归，正式仍94A2/0.4.1。

motion-test已增加--suite native/experience/factory/upcoming/mechanics（旧专用Probe通过同一私有桌面驱动），暂未使用。--suite会设置必要临时flag，结束清理；fixtures仅runtime/scene.xml，正式不动。--visual现在仅诊断截图揭开原生探索黑幕（设置visi/t_visi），此前signs-before图片大半黑，不能作正式视觉验收。--raster-check若宿主sceneWarmVerify存在，会运行10个跨帧/同步同块对照；否则走已拒绝的bitmap mask诊断。最新Probe复制前要重新Build -ProbeOnly。下一步仍需解决调度跟不上、再跑功能/完整帧/LAD回归，最后才能部署；正式三文件均未改。

2026-10-19 22:21。本对话 01a13816-367b-7261-8e11-ca9152565dd9；用户最新补充：关闭灯光渲染仍明显卡顿。不能以LAD修复代表全部解决。

正式仍宿主02BFABE6、CS0.8.1/241E48EA、LAD0.4.1/94A2F086；CS的8673cd7边界墙热修必须保留。RV76314B81/WB0BD209A1/TDFC03243196/RC574D2B51保持。无新增部署、无任务消息、无Ghost、无子代理。

独占私有桌面证据：motion-v082-before-2（LAD开暖区中位75–80ms）；motion-v082-no-light-before（灯光从进图前关闭，冷区49/P95 165ms，暖区51/73，静止33/50；单次补绘最高145ms）。布局seed20261019，但实体随机数未完全冻结，不把不同世界的微小差别称为因果。

箭头改动已构建CS0.8.2/CD65CEC6到build/runtime，仅移除两个原房均存在的内部切房箭头，保留缺房/外侧箭头与真正出口。测试104→0、出口对象保留通过。未正式部署。

LAD src/lad/LadLightField.as 是本任务WIP（未版本升级），空间地形快照+带边距环境光缓存。候选build/generated/lad-motion-candidate/LightAndDarknessMod.swf=EB850A52；motion-v082-light-cache-pixels-1的145项通过，72视口/遮挡与背墙改变/电源/缩放/移动灯图像逐位一致；80次移动渲染原路径1528/1563ms，缓存254/277ms，仅函数级对照，不当成FPS。仍须正式版本构建、标准LAD回归和完整帧测试。

已拒绝的隔离宿主试验（正式未动）：
- motion-host旧目录90AF72C9：160px小块与每帧预绘，冷区86/143、暖区61/76，整体变慢。
- motion-host-masks/0D574913：按形状复用MC与避免同帧gotoAndStop，无明确稳定收益。移动对象wrapper裁剪同轮62/102与53/83，未采纳。
- motion-host-bitmap-masks/02342E71：MC cacheAsBitmap破坏22/100层像素一致性，停止后续性能测试，未采纳。
- motion-host-profile/81CF5997：116 pass绘制4186ms，其中drawKusok2422ms，背景装饰642ms。仅归因，不发布。

正在构建替代方案：build/motion_incremental.py + src/patches/SceneWarmJob.as.inc，把原drawLoc步骤/各材质/各背景层拆成闭包，每帧约8ms推进一个未发布的320px块；独立7 scratch+4 output缓冲，当前绘图字段/材料used标记/区域风格每次保存恢复；完成后才发布，受影响地形变化取消任务。首屏同步批绘保持；突然移动仍可同步兜底。sceneWarmVerify诊断对每块同步重画逐像素对照。尚未运行，不能宣称正确或优化成功。

构建器build/motion-host.py固定02BF宿主，仅替换Grafon并核对4672其他方法、1015类布局及旧常量池。旧renderer-build/candidate-v08-build不可直接用，会覆盖RC新变更。FFDec不支持多变量声明、Vector.<uint>=需空格，已修。

测试入口build/motion-test.py，HiddenProcess私有桌面、独立appId、launcher精确15模块（14正式+探针），检测其他AIR即作废并只结束自建进程。--prepare覆盖runtime候选回正式，候选须之后复制。每次证据唯一，备份旧失败。保护钩子要求的精确授权事件在build/generated/grant-motion-*.json；用户已允许每次<=10分钟会话绑定，不能关闭钩子。正式部署后需备份/回读/隔离复验/记录和定向提交。
