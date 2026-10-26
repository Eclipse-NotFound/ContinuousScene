# 完整画面上限：按实际帧变化固定动画

前轮已定位24个 isPlaying=false 却跨间隔变帧的子时间轴，主要位于 visualBloat*/visualVortex 的 osn 与 visualBloodwing 子层。整个地图2392×1444固定图已上传7纹理（22,626,944字节），但下一步时间轴保护失败，0计时；资源全部释放，原始恢复失败保留。空槽变体本轮未遇到空槽，不能宣称前轮空值原因已证实。

本轮采用已有 tests/SceneImplicitFreezeProbe.as 的“先观察实际变化再停止”原则：固定8个帧间隔，只读观察所有多帧对象；冻结时停止显式播放对象及观察到实际变帧的对象。没有观察到移动的 isPlaying=false 对象不擅自播放/停止。记录隐式活动对象路径、前后帧与变化次数，计时条件均保持相同冻结状态；任何后续变帧仍失败。

清理仅在姿态未变时恢复被本轮停止的对象；隐式活动者通过 play 恢复，因此 isPlaying 可由原false变为true，**不宣称原始内部播放状态逐位恢复**。仅用于即将退出的隔离诊断，不用于真实世界暂停/恢复，不部署。显卡/位图/世界可见性等资源恢复仍严格核验。像素门槛和960区间协议不变，真实Windows呈现及动画可用性仍未验。

官方 MovieClip 文档仅描述 isPlaying 为当前播放状态，未解释本案例；这里依赖实际帧观察，不将推测写成运行时规范：https://airsdk.dev/reference/actionscript/3.0/flash/display/MovieClip.html#isPlaying 。
