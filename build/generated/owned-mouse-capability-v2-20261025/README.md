# v2: 文档根身份修正

v1独立运行e470354f115e418c8b1aedb8f1e26300初始化报#2078，不曾投递输入，AIR21156退出。v2不改文档根name，通过node===this与精确类名核对事件路径；其余测试和输入边界保持。下面为继承说明，本版尚待构建和运行。

# 独立 AIR 鼠标命中能力夹具

状态：仅源码，尚未编译或执行。仅 `src/OwnedMouseCapability.as`、`compile.xml`、`run.py`；不导入游戏、模组或 IP/线程采样器，不触碰正式文件。主任务审查通过后，由主任务另行安排编译和一次能力运行。

## 要回答的问题

在新建自有 AIR 私有桌面中，只给唯一内容窗口投递 `WM_MOUSEMOVE`，AIR 是否更新真实 Stage 鼠标坐标并把真实 `MouseEvent.MOUSE_MOVE` 命中到对应 Sprite？

窗口为 640×480、NO_SCALE、TOP_LEFT；三个无子对象的 100×100 Sprite 位于 (40,180)、(240,180)、(440,180)，名称 target0..2。Stage 只监听运行时送来的事件，不自行创建或派发 MouseEvent。定时器另读真实 `stage.mouseX/Y`。原始事件保留目标、类型、坐标和一直到 Stage 的父路径。

Python 持有刚创建的原 `HiddenProcess` 对象/句柄，核对 PID、创建 FILETIME、adl64 映像、精确启动描述符/命令和私有桌面名。仅在该桌面枚举窗口，先按自有 PID 筛选才读取标题/类名；收到应用 ready 后，必须恰好一个 client 矩形为 640×480 且标题为唯一 AIR id 的顶层窗口。每次输入前重验所有权与完整窗口身份，才依次向 (90,230)、(290,230)、(490,230) 各投递一条消息。没有 PID 参数、附加既有进程或子窗口盲试。

每个目标必须有新的真实事件，target0→target1→target2、准确父路径、event.stageX/Y 与 handler 内 stage.mouseX/Y 均在目标坐标 ±1 内，并有事件之后的 Timer 对实际 Stage 坐标作相同读回。超时、入队失败、身份或读回异常都停止后续消息，不重试或切换输入通道。`PostMessageW` 成功只证明入队，不能代替上述断言。

无 NativeWindow 激活、系统光标移动、SendInput、桌面切换、任意窗口广播或 Ghost。descriptor 的 visible=true 仅显示于自有私有桌面。不调整全局 DPI/鼠标参数；尺寸不符直接失败，因此失败也不等于所有后台输入方案均不可行。

## 运行边界与产物

未来构建位置固定为 `build/OwnedMouseCapability.swf`。编译者须生成 `build/compile-receipt.json`，包含 `sourceSHA256`、`configSHA256`、`swfSHA256`，均对应本目录源码、配置和实际构建产物。配置使用本机现有 airglobal；从本目录编译且显式指定本目录 source path。runner 不含编译、下载或安装逻辑，缺构建回执即拒绝启动。

未来 runner 只接受登记等待时长 `--wait`；使用正式只读 HiddenProcess/test_registry 源并核对预定 SHA。登记资源为 game；启动前可用提交内存须 ≥4 GiB，运行中须 ≥512 MiB。唯一 AIR id、`runs/<UUID>/`、独立 `%APPDATA%/<id>/Local Store/`；不会访问真实 pfe 存储。初始输入和后验指纹覆盖夹具、正式工具、adl64 及该固定 runtime 目录文件。

AS3 写 ready.json、events.json（原始事件与逐次 Timer 记录）、result.json；runner 保存每一步基线、投递返回、最后读回、确认事件和定时读回，不把失败结果改写为成功。结束向本次独立存储写 finish 命令，失败或无响应仍在 finally 只停止并等待原 HiddenProcess、关闭其句柄与私有桌面，确认退出才解除登记。描述符退出后移除，原文保存在 runner-result.json；独立存储留作证据，不递归删除。

通过只证明本机、本运行库、这个独立三个 Sprite 夹具下的消息输入能力；不等价物理鼠标、不证明真实游戏命中路径、玩法或性能改善。

## 文档依据

- [Microsoft WM_MOUSEMOVE](https://learn.microsoft.com/en-us/windows/win32/inputdev/wm-mousemove)：lParam 为相对客户区左上角的有符号 x/y。
- [Microsoft PostMessageW](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-postmessagew)：异步入队即返回，不等待窗口处理。
- [Microsoft EnumDesktopWindows](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-enumdesktopwindows)：仅枚举指定桌面顶层窗口；此夹具必须传原非空自有 HDESK。

2026-10-25 源码准备；未执行 Python、AS3、编译器或 AIR。后续能力结论必须来自新的实际运行证据。
