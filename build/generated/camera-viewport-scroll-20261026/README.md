# 视口条带更新候选

四个与屏幕同尺寸的透明缓冲区分别位于原前景、背景两层、水层原位置，保留层序和父层效果。仅整数单位镜头、320格、无SATS/缩放/震动的暂停诊断。原生像素只读；每次移动先scroll旧像素，清空并补画新露出的横纵条带；原生版本、位图引用和可见性变化重新覆盖受影响格。大跳全刷，不在计时分配新位图。

与旧父层cacheAsBitmap/scrollRect、世界固定分页、AIR direct/cpu模式不同。先测是否值得继续，不部署。五大视口加八个1–7像素往返视口，共39截图，RGB≤2/alpha0且原生恢复精确；960帧动静正反序，原生八绘制计数保持，所有资源释放。真实战斗修改、父层额外前后对象顺序、缩放/效果/旅行生命周期需后续验证。

依据AIR BitmapData.scroll官方语义，露出的边缘原像素不会自动清除，因此本候选显式fillRect再copyPixels，不依赖未定义像素：
https://airsdk.dev/reference/actionscript/3.0/flash/display/BitmapData.html#scroll()

