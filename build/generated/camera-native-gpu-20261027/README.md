# 原生direct与GPU绘制模式的隔离对照

正式application.xml目前是direct。[NativeWindowRenderMode](https://airsdk.dev/reference/actionscript/3.0/flash/display/NativeWindowRenderMode.html)说明direct由软件画矢量再GPU传送；gpu请求硬件画矢量。这条路径不同于此前手动Stage3D整图缓存，可保留原显示树，但[运行库维护者讨论](https://github.com/airsdk/Adobe-Runtime-Support/issues/2869)记录了滤镜与Stage3D叠放限制，因此不能直接改正式模式或把更快当正确。

沿room-axis-v2同种子/同房间/1280×720/原生1倍的静止、横、纵、组合8×120窗口，世界模拟暂停，Flash时间轴保留活动。修正旧基线没有实际mainMenuOff的问题：此轮两种模式都真正移除主菜单，旧数字不拿来直接配对。先direct再gpu，共用同一冻结探针；如有意义再做完整复验。

仅临时调整独占测试runtime/application.xml的renderMode；在创建唯一AIR描述符后保存并核其全文/哈希，运行时读NativeWindow.renderMode，结束原字节恢复。正式根application.xml与所有SWF不改。没有请求Stage3D，不开depthAndStencil。526正式/13运行库/86源及工具输入沿冻结协议，私有桌面与共享登记。

重要边界：BitmapData.draw的像素检查证明软件截图稳定和清理，**不证明GPU窗口显示相同**。即便实际报告gpu且帧间隔下降，也必须再核实际窗口、阴影/滤镜/混合、正常动画与子弹、RV/LAD/WB兼容。当前运行仅能力/成本归因，绝不部署。
