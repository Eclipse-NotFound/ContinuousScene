# 真实世界鼠标输入：v1–v3失败边界

2026-10-25。三轮都没有进入战斗计时，不能评价鼠标树性能，也没有部署。

证据目录分别为 `knowledge/experiments/evidence/mouse-world-native-20261025-r1`、`mouse-world-native-v2-20261025-r1`、`mouse-world-native-v3-20261025-r1`。

- v1：独立 AIR 45712；begin 中的窗口状态条件失败，ready为空、0消息、0样本。只凭该轮概括错误不能区分尺寸、对齐、标题或可见性。
- v2：独立 AIR 38280；ready为2032×1084、noScale/TL，唯一自有窗口；投递一次(1016,542)，系统接受入队。Python在5秒无完整proof时终止，早于AS3的15秒超时，未留下storage/result.json。原始握手超时保存在runner-inputs和process-policy；后验读取文件缺失又产生FileNotFoundError，不能拿后者替代初始原因。
- v3：独立 AIR 53824；Python等待延至20秒，让原AS3先完成失败记录；未增添输入重试。原窗口visible=false，一次设置true后尺寸、noScale/TL、标题均正确。只收到1条实际mouseMove，路径为Sprite→准确w.visual→MainFE→Stage，buttonDown=false、targetInWorld/pathReachedStage均true。

v3事件内直接Stage坐标(1016,542)与投递完全相同，但event.stage=(1016,539)，纵向差3。因此原严格±1事件坐标条件没有产生proof，15秒门控超时；warmed=sampled=0。原始事件保留，不能回填通过。窗口标题及原可见性均恢复，自有实例退出。全部三轮正式版本未改。

官方 [MouseEvent属性说明](https://airsdk.dev/reference/actionscript/3.0/flash/events/MouseEvent.html) 说明stageX/Y与localX/Y的设置相关；这**不能解释本轮3像素差异的具体原因**。不把它猜成已验证的震屏、Camera或DPI问题。

后续v4仅准备重新界定诊断资格：直接Stage坐标（事件前后、独立后Timer和全部计时帧）仍须与唯一投递点±1；真实world命中路径、无按钮、事件序号及进程/窗口身份仍严格核对。派生event.stage只要求有限且在视口内，并另记localXY、实际目标矩阵、localToGlobal及各类差值，不修正它或扩大原容差。这个资格只服务固定指针条件下的鼠标树成本诊断，不证明精确点击、准星或完整输入兼容。
