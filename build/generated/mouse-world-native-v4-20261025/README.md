# 真实后台鼠标位置下的世界命中树对照

v4 的资格目标是“直接 Stage 鼠标固定在实际视口中心，且真实事件命中原 world 显示树”，用来比较鼠标命中树的成本；不验证精确点击、瞄准或 event.stage 坐标转换兼容。v3 实测真实事件内 direct Stage 为 (1016,542)，与投递一致；event.stage 为 (1016,539)，相差 3 像素。旧资格失败、0 个计时样本的证据原样保留，不回填通过。

[官方 MouseEvent 文档](https://airsdk.dev/reference/actionscript/3.0/flash/events/MouseEvent.html) 说明 stageX/Y 在 localX/Y 设置时计算。这不足以解释本次 3 像素差异；本版不猜测镜头、震屏或其他原因，不改写事件坐标，不把容差放大到 3。新资格把直接 getter 与事件派生坐标分开：事件回调前后、后续 Timer 及 1200 帧中的直接 Stage 读回仍严格为中心 ±1；event.stage 仅要求有限且位于实际视口内，并完整留存其派生证据。

保留 v2 的窗口状态记录、一次 visible=true 和 clear 恢复，以及 v3 的 Python 20 秒等待（AS3 15 秒失败终态先落盘）和缺失 result 时保留最初执行错误。尺寸、noScale/TL、唯一 HWND 和单消息边界不变。旧目录不修改。尚未编译或运行。

状态：源码初版，未编译、未运行。准确冻结来源仍是 29AF SMG 夹具，85 个源码仅改 `ContinuousSceneMotionProbe.as` 并增加 `tests/SceneWorldMouseProbe.as`（总 86）；不写正式 SWF、共享 runner 或其他模组。

独立能力 v4 已在 `owned-mouse-capability-v4-20261025/runs/cbbb25c5f75940dba64c40358efc287c/` 通过三目标原生事件和 Timer 读回。这里只复用其审查后的 `OwnedWindow` 源码（SHA 2C16D90A…），不加载、读取或重新核验其 SWF。能力通过不代表真实世界路径已通过，本候选必须重新证明一次真实场景输入。

## 输入与时序

`owned_mouse.py` 从当前正式 `motion-test.py` 的 `run_owned` 文本生成独立内存函数副本。仅四处精确、可逆改动：当前独立 descriptor 的 visible=false 改 true；替换诊断说明；原 HiddenProcess 创建并登记后绑定；每秒原采样前推进一次输入握手。共享文件与模块函数不改。窗口只在从未切换的私有桌面可见，四段保持一致，不激活窗口，不移动系统光标。

AS3 在 phase3 第一次探针预热之前建立等待门。此时 phase2 已完成场地和敌人准备；等待只挡探针的预热、按键和开火驱动，原生 World.step 的 AI、物理、预绘仍继续。留存 ready、放行时间、等待 tick 数、位置、速度和预绘计数，不能称冻结或完全同初态。四段共用这一次放行，不在每段重新定位鼠标。

应用把窗口标题设为本轮唯一 AIR id，ready 报告实际 Stage 宽高、NO_SCALE/TOP_LEFT 和独立存储位置。Python 只绑定刚创建的原 HiddenProcess 对象/句柄，沿 v4 核对 PID、创建 FILETIME、adl64 映像、精确 descriptor、原私有 HDESK。仅在该桌面筛自有 PID；必须唯一一个实际 client 宽高匹配 ready、标题匹配 AIR id 的内容窗口。没有固定 640×480 假设，不盲试窗口或子窗口。

只允许一条 WM_MOUSEMOVE，坐标是实际 Stage 中心，wParam=0。投递前再次核对完整窗口身份、唯一性和进程所有权。AS3 必须收到 ready 序号之后的真实 MOUSE_MOVE，目标祖先恰好包含一次原 `w.visual` 且最终到 Stage、无按键、currentTarget 确为 Stage；事件中直接 Stage getter、回调前后 getter 与中心相差不超过 1，独立后续 Timer 再读同一真实坐标。event.stage 必须有限且在实际视口内，不要求等于投递中心。AS3 和 Python 使用相同的新资格；没有 proof 就停止，不激活、重试或换输入通道。

真实事件记录保留 localX/Y、原 event.stageX/Y、事件目标名称/类与实际父路径（含目标、world、Stage 身份和子索引）、target 的 concatenatedMatrix、target.localToGlobal(localPoint)、同矩阵计算的点、eventPhase/currentTarget，以及派生值、直接读回与投递值之间的差值。上述内容只读、只在预热前观察，不改写任何坐标。Python 核对 proof 后只写一次接受文件，AS3 才放行；投递返回成功只表示入队。

握手完成移除诊断 MouseEvent listener、停止 Timer；此后只有每帧真实 Stage 坐标和两项鼠标树状态读取。预热和 1200 帧任一坐标、尺寸、标题、世界身份失配均失败。读回在原有连续时间采样之前，成本保留。JSON 文件各发布一次，不在计时窗反复覆盖日志。

## A/B/B/A 与保真边界

沿用旧 `mousetree` 模式的四段 300 帧：A 保留原 `visual.mouseChildren/mouseEnabled`，B 将两者置 false，最后 A 恢复。初始必须两者为 true。原始开火、原生移动、路线、六名 SMG 敌人、SATS未使用、RV/WB/LAD关闭等夹具保持；旧 `drivePlayerFire` 原有的 cam.celX/Y 瞄准写法逐字保留，新增代码不会把这些字段当成真实指针证明。

切换成本、检查成本和全部连续帧保留，不减去诊断耗时、不裁掉尖峰。终态恢复鼠标树与原窗口标题并移除自己的观察器。未来完整 runner 冻结 526 正式输入、13 runtime、85 来源、86 试验源和完整 runner 输入；沿既有登记、独立 storage、4 GiB 启动预检与 512 MiB 运行保护，只由原 runner finally 关闭本次自有进程。

这只是定位鼠标命中树成本的实验。B 会改变交互，不能直接部署；指针真实位于场景中心也不证明物理鼠标或完整玩法兼容。等待阶段的自然演化、四段敌人/弹体/预绘负载仍须逐项审查，平均差值不能自动当成产品收益。

## 文件职责

- `SceneWorldMouseProbe.as`：真实事件、后续 Timer 和持续 Stage 坐标守卫。
- `probe_patch.py`：准确 29AF Main 的可逆插入与 86 源准备。
- `owned_mouse.py`：仅原自有 HWND 的一次消息；共享 run_owned 的可逆内存接入。
- `run.py`：复用已审查的登记、构建、保留证据和输入守恒流程，默认 helper 未冻结即拒绝编译。

当前没有执行编译器或 AIR，也没有运行新 runner。先审查源码和接入资格，再由根任务决定是否冻结和运行。
