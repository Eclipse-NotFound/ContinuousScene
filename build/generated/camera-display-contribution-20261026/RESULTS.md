# 显示层抑制未能精确恢复，停止该诊断

2026-10-26，冻结 e71142f8c75649c88fdde790764cf136。r1在计时前失败，0性能样本。
第一视口(4716,4119)：仅远景alpha置0后，724k量级画面改变且恢复精确（实际此轮717044像素）；对象层alpha置0影响50221像素，恢复后仍1567像素不同、maxRGB227、alpha0。原错误为 Terrain visibility did not restore exact pixels。

不解释为性能证据，不继续通过别种隐藏手段规避恢复失败。七个父层alpha、镜头和玩家状态均按清理恢复，AIR35844正常退出；原失败和PNG保持。后续camera-backdrop-contribution仅测已验证可逆的远景，不再触及对象层。

