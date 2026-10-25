# 真实后台鼠标位置下的世界命中树对照

v3 仅修诊断收尾：Python 读回等待由 5 秒改为 20 秒，使原 AS3 的 15 秒失败终态先保存真实 events/context。AS3 和 Main 补丁逐字沿用 v2（其中数据版本仍为 mouse-world-native-2），不增加第二坐标、消息或重试。若最终 result.json 缺失，单列 result-unavailable.json，并重新抛出原执行错误，避免文件缺失盖掉最初原因。原 v2 证据保持不变。尚未编译或运行。

v2：保留 r1 的失败证据和冻结源码。r1 在 begin 首次窗口守卫失败，尚未发送消息；只记录了 2032×1084，无法分辨 scaleMode/align/title/visible/尺寸哪项失配。未找到当前 CS motion 路径另行隐藏窗口的源码证据，不能说已确定隐藏为根因。

本版仅新增 begin 设置前后完整实际窗口状态和失败 expected/actual，明确给本次自有 NativeWindow 设置 visible=true 一次（全 ABBA 恒定、无 activate/resize），clear 恢复原 title 与 visible。尺寸、noScale/TL 和唯一 HWND 守卫不放宽，单次消息边界不变。三个状态快照只在初始化或失败创建，成功计时帧不新增这些分配。尚未编译或运行。

状态：源码初版，未编译、未运行。准确冻结来源仍是 29AF SMG 夹具，85 个源码仅改 `ContinuousSceneMotionProbe.as` 并增加 `tests/SceneWorldMouseProbe.as`（总 86）；不写正式 SWF、共享 runner 或其他模组。

独立能力 v4 已在 `owned-mouse-capability-v4-20261025/runs/cbbb25c5f75940dba64c40358efc287c/` 通过三目标原生事件和 Timer 读回。这里只复用其审查后的 `OwnedWindow` 源码（SHA 2C16D90A…），不加载、读取或重新核验其 SWF。能力通过不代表真实世界路径已通过，本候选必须重新证明一次真实场景输入。

## 输入与时序

`owned_mouse.py` 从当前正式 `motion-test.py` 的 `run_owned` 文本生成独立内存函数副本。仅四处精确、可逆改动：当前独立 descriptor 的 visible=false 改 true；替换诊断说明；原 HiddenProcess 创建并登记后绑定；每秒原采样前推进一次输入握手。共享文件与模块函数不改。窗口只在从未切换的私有桌面可见，四段保持一致，不激活窗口，不移动系统光标。

AS3 在 phase3 第一次探针预热之前建立等待门。此时 phase2 已完成场地和敌人准备；等待只挡探针的预热、按键和开火驱动，原生 World.step 的 AI、物理、预绘仍继续。留存 ready、放行时间、等待 tick 数、位置、速度和预绘计数，不能称冻结或完全同初态。四段共用这一次放行，不在每段重新定位鼠标。

应用把窗口标题设为本轮唯一 AIR id，ready 报告实际 Stage 宽高、NO_SCALE/TOP_LEFT 和独立存储位置。Python 只绑定刚创建的原 HiddenProcess 对象/句柄，沿 v4 核对 PID、创建 FILETIME、adl64 映像、精确 descriptor、原私有 HDESK。仅在该桌面筛自有 PID；必须唯一一个实际 client 宽高匹配 ready、标题匹配 AIR id 的内容窗口。没有固定 640×480 假设，不盲试窗口或子窗口。

只允许一条 WM_MOUSEMOVE，坐标是实际 Stage 中心，wParam=0。投递前再次核对完整窗口身份、唯一性和进程所有权。AS3 必须收到真实 MOUSE_MOVE，目标祖先包含原 `w.visual` 且最终到 Stage、无按键，事件坐标及实际 Stage 坐标均与中心相差不超过 1；独立后续 Timer 再读同一真实坐标。Python 校验完整 proof 后只写一次接受文件，AS3 才放行。没有 proof 就停止，不激活、重试或换输入通道。

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
