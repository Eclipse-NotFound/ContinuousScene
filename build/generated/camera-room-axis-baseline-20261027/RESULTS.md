# v1原版房间默认缩放使资格检查停止

2026-10-27，冻结8594abd2d53b422b9965f8501e2d3fed，AIR51160退出。
实际画布1280×720，但原版默认zoom2仍把1920×1000房间缩到2/3；maxvx0、maxvy−53，镜头固定。初始要求scale1的检查停止，0计时/0截图，保存和恢复状态成功；原失败保持。

旧environment-control-20261024-normal-r1的2032×1084/scale1数据也已直接核对：四段镜头始终(56,42)，完全没有位移，不能直接作连续移动性能基线。共享rendering/discoveries/camera-screen-pixel-scale.md已有原生zoom100=false→mode2机制。

v2仅在保存状态后调用原生cam.setZoom(0)，两种地图均单位比例、相同1280×720及房间内部路线；结束精确恢复，不修改用户配置或正式游戏。下一结果见v2目录。

