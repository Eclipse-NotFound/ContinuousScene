# Stage3D 背景层原型

针对镜头移动绘制开销，仅限隔离、暂停世界的诊断。526正式文件保持，不接生产代码。

- 使用原生静态远景与 back/back2 两层位图；保留原显示顺序、原生中心裁剪，最近点采样，仅单位缩放与整数位移。
- 前景、对象、敌人、弹体、明暗、界面仍由原生显示树绘制。后续真实战斗/缩放/SATS/RV/WB/LAD和设备丢失流程未验，不可发布。
- 私有桌面先前独立 Context3D clear/readback 已返回 DirectX9Ex，本轮仍验证身份和驱动。
- 背景 CPU 截图仅初始化一次并立刻释放；原生纹理按身份/版本上传，预算192MiB，计时前沿全路线准备，计时不分配或上传新纹理。
- 原生基线保留相同 Context/纹理，仅将 Stage3D 隐藏；候选启用同一资源。结束恢复父层可见性、Stage3D原状态并释放全部资源。
- 13视口比较：原生 Stage.draw 与 GPU backbuffer readback 叠加剩余原生 Stage.draw；RGB≤2、alpha0、恢复精确。读回不是窗口真实混合输出验收；量性能阶段不读回。
- 固定960帧静止/移动ABBA，全段保留；原生绘制准备计数保持。所有长帧保留，不以暂停数字冒充战斗FPS。
- 使用正式共享登记、唯一ID/存储、无其他AIR、4GiB提交/2GiB物理门槛、私有桌面，仅清理自有进程。

官方参考：[Context3D](https://airsdk.dev/reference/actionscript/3.0/flash/display3D/Context3D.html)；
[AGAL byte format](https://github.com/adobe/glsl2agal/blob/master/agalassembler/agal.h)。

