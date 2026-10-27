# 同一世界的原生绘制窗口对照

诊断候选，不部署。保持现有 A796、CS 0.9.0 和正式模组，暂停模拟但不停止 Flash 动画。
同一个显示树依次在原 direct 窗口、新 direct 窗口、新 auto 窗口内运行；新 direct 是重新挂接显示树的对照。
每种窗口各有静止和移动两段，正反顺序，共 1440 连续 ENTER_FRAME 区间，2032×1084，1 倍。
换窗口的成本保留在计时中，不扣除尖峰。图像比较为软件 Stage.draw，不冒充 OS 窗口像素。
新窗口只属于本轮独立 AIR 进程和私有桌面，最后恢复原 Stage 的所有直接子节点、World.swfStage、窗口可见性并关闭新窗口。
禁止关闭玩家实例、改真实存储、停用动画或修改正式 descriptor。构建和运行输入冻结，沿共享登记和内存预检。

官方依据：NativeWindowInitOptions.renderMode 只能在新窗口创建时选择，见 https://airsdk.dev/reference/actionscript/3.0/flash/display/NativeWindowInitOptions.html#renderMode 。
本实验验证具体本机行为，不凭模式名称声称已经使用硬件加速。
