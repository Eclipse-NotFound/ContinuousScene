# 独立 Stage3D 能力结果（2026-10-27）

通过，仅证明隔离环境的绘制接口可用。没有游戏性能结论或部署。

- 证据：runs/ae7d3b886f854967ac6f2514a862f58c/runner-result.json 与 air-result.json。
- AIR WIN 51,1,3,3；请求 auto / baseline，实际 baseline，driverInfo 为 DirectX9Ex。
- 256×256 全部 65536 像素读回通过；RGB 最大 1/255，alpha 完全一致。创建 Context 2513ms，总 2558ms。
- 1 张自有位图分配/释放、Context dispose、进程正常退出和句柄关闭均通过；无强制停止。
- 526 正式文件、13 运行库文件、源/工具/编译输入指纹保持。
- 独立唯一 AIR ID/存储、共享登记、私有桌面。不是前台交互测试，也未验证混合显示树、纹理、缩放或游戏帧率。
- 下一步先做有限背景层的真实游戏像素/移动对照；不从接口可用推断收益。

接口参考：[Context3D](https://airsdk.dev/reference/actionscript/3.0/flash/display3D/Context3D.html)。

