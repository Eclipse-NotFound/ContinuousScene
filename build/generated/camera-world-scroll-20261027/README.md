# 世界容器的窗口滚动诊断

新依据：整个world父层停止显示的收益大于六物件层，且单帧远处根裁剪无收益。
旧components-r4-raster的对象父层scrollRect曾像素失败；本轮改的是世界镜头呈现路径，
保留它为历史失败，不重命名旧候选或降低恢复门槛。

三条件走相同路线：原生平移；world位置归零、scrollRect以原生-vx/-vy滚动；同样窗口滚动
加cacheAsBitmap。先设视口大小的裁剪再请求缓存，未确认运行时实际缓存分配/采用情况；
禁止原本已有mask/filters/scrollRect/cache的世界容器。
原生cam.calc仍运行，之后才设置滚动，所以此原型仍有两次位置写入；不能声称消除了所有
祖先变换或负结果排除了更深入的宿主实现。期间不调用立即localToGlobal作资格证明。

官方说明scrollRect在绘制时生效，立即读坐标换算可能仍为旧值：
https://airsdk.dev/reference/actionscript/3.0/flash/display/DisplayObject.html#scrollRect
缓存只适合相对稳定内容；动画可能抵消收益，故本轮只作诊断：
https://airsdk.dev/docs/development/display/display-programming/manipulating-display-objects/caching-display-objects

五视角固定原生预备、候选RGB≤2/alpha相同、恢复逐像素精确。65截图全部释放。
6窗口0/1/2/2/1/0共720帧。原生准备计数不变，保存/恢复scrollRect/cache/matrix，退出独立实例。
Flash内部缓存由运行时管理，恢复cache标志不等于证明即时物理释放；结束AIR回收进程资源。
不部署；实际游玩、RV/灯光、SATS/输入坐标和冷态仍未验收。
