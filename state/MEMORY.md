# ContinuousScene

## 1. 这个模组是什么
大的无内部房间边界场景。镜头、敌人和子弹连续运行，单一Location持有全场逻辑；进图预绘全部320px画面块并常驻。入口ContinuousSceneMod；信息页顶部进入/返回基地。

## 2. 用户偏好与授权
中文交流；编辑器暂缓，原版房间只作测试。2026-10-14 用户要求接入游戏入口，并明确允许 RealisticVision、WallBlend 必要兼容修改。已授权部署，不重复询问。测试独立身份，不碰正式存档，不关闭玩家游戏；未授权 Ghost 或并行委托。

## 3. 当前状态
0.4.0于2026-10-15 12:03:27安装。入口“大场景 · 工厂”读取12个原版工厂房间组成的连续测试关卡，192×75格（7680×3000），240块预绘常驻，444个物件标记和603个背景装饰。修复第二背景层坐标遗漏造成的墙边重复黑块。最终34项工厂、63项旧走廊、10项内容/像素、15项安装原生启动均通过。当前混装RV v0.30.4-scene、WB0.5.1、FA0.3.1；本轮只替换宿主、CS入口和场景XML。用户需保存并正常重启游戏。

## 4. 本轮交付与停点
旧入口实际是自制稀疏走廊，没有加载原版工厂；现从Rooms/rooms_plant.xml只读导入固定4×3区域，在互相兼容的原版门槽打开通路。内部地形保留。黑块根因是prepare.py的Bmp结尾匹配漏掉backBmp2，世界坐标装饰反复画到各块同一位置；显式匹配并断言8处调用数量后修复。像素对照、实际通道步行、敌人/子弹跨区、基地往返与存读档通过。保留0.3.1按钮暂停修复。没有进行地图编辑或新的性能优化。

## 5. 已知问题
密集工厂各轮首次进图55–81秒；最终组合54.7秒，短通道31帧中位89ms/max118ms，未稳定30帧。含PNG导出、原生对照重绘、往返和读档的诊断进程Private峰值6501MB，结束AS3内存559MB，不能当成稳态内存。再进图/读档仍重新预绘。测试HighQoS只作用自身进程，正式启动器不变。工厂统一基础色调，区域原色调仅存元数据；不是完整55模板/跨层剧情/后房移植。信息页地图缩略图、编辑器、长时/联机及所有门/平台/水体未验收。

## 6. 后续与回退
优先继续定位工厂首次预绘成本、游戏帧耗时和长时内存；WB每块遍历全部装饰只是疑点，未证明是瓶颈，不能据此贸然改动。后续再扩大原版交互覆盖。当前回退只用build/upgrade-v04.ps1 -Action Rollback，依据state/deployment-v04.json和build/upgrade-v04-receipt.json，恢复三个文件到原0.3.1组合；根备份pfe_before_ContinuousScene_v04_20261015-120327.swf。其他模组/清单/配置不回写。不要运行旧整体回退覆盖WB的新版本。

## 7. 接续入口
- README.md：使用、复建、回退；design/runtime.md：实现和边界；knowledge/experiments/factory-v04-20261015.md：本轮根因、失败与验证。
- 最终证据knowledge/experiments/evidence/factory-v04-release、factory-v04-lab-release、pfe-modsettings-continuous-installed-20261015120344；factory-v04-before保存黑块复现。按钮是原生监听器事件派发，不是系统鼠标注入。
- 完整构建build/build.ps1 -BaseHost ./pfe_before_ContinuousScene_20261014-181702.swf；不要用已打补丁的根宿主重复构建。-ProbeOnly仅驱动；-DriverOnly入口+驱动。
- test-mods.ps1 -AllMods复制当前安装组合；test.ps1 -Factory -HighQoS -TimeoutSeconds 650 -EvidenceName <新名>后运行build/verify_factory.py；-Quick -TimeoutSeconds 420验证旧走廊。AIR ID pfe-modsettings-continuous-scene，生产驱动不安装。
- Start-Scene.cmd仍为旧稀疏走廊夹具；正式入口使用工厂。测试后runtime/scene.xml可能变回走廊，升级脚本固定从scene-factory.xml取生产数据。
- RV HEAD有其他任务未发布接口；WB与FA均由其他任务独立更新。本轮测试已安装SWF，不重编它们。旧compat-build.ps1不应覆盖现行WB。
- state/deployment-v04.json记录SHA256和备份；更早的entry-v031、preload-v03及v02证据保留作历史。AGENT_SCOPE仍因早期保护拦截而未创建，不绕过保护。
