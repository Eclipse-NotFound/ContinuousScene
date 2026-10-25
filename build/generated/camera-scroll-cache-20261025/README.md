# 静态地形的原生滚动缓存候选

依据：camera-axis-motion-r1固定同一已预绘场景、暂停演算、世界始终可见时，静止29.821ms、横移41.304、纵移37.125、组合43.967；正反序均移动更慢。helper含原Camera计算平均0.2–0.4ms，不能把完整差额仅归镜头数学；不是已证GPU根因或产品收益。

新候选仅对front/back/back2/water四个原生地形父层设置屏幕范围scrollRect并请求cacheAsBitmap，局部平移补偿裁剪原点，使画面坐标不变。世界根、对象层、敌人、弹体不隐藏或移树，原地形像素绑定不改，不引入自行copyPixels合图。仅单位整数镜头、零震动、尺寸≤2560每边、无原层filter/mask/cache/额外变换条件；当前只是诊断，其他条件报错，不作为产品回退设计。

AIR官方缓存文档描述scrollRect配合cacheAsBitmap可复用滚动像素并更新露出区域，同时提醒内容频繁变化可能变慢。此处只把它作为待测假设；cacheAsBitmap=true不能证明内部缓存实际创建。峰requestedPixelBytes只计四张视口大小的请求像素，不是实际运行时显存或总内存。

来源：https://airsdk.dev/docs/development/display/display-programming/manipulating-display-objects/caching-display-objects
坐标语义：https://airsdk.dev/reference/actionscript/3.0/flash/display/DisplayObject.html

从冻结29AF的85源派生86源：改Main接入，替换SceneTilePresentation，新增Trial。反转核对Trial，其余源指纹保持。五视口原生/候选/恢复：RGB最大≤2、alpha0、恢复精确，15截图全释放。沿路原生预绘八计数稳定后960帧正反序（原生静止/移动、缓存静止/移动，再逆序），每帧记录实际请求及四父层数量，首建/切换和长帧保留。

World模拟暂停，Flash时间轴和其他回调仍在；120fps不是原30fps游玩验收。窗口只在私有桌面可见，登记、唯一AIR/存储、内存预检/运行保护、正式输入守恒照旧。结束恢复每个父层的矩阵、scrollRect、cacheAsBitmap并核验，世界状态亦恢复。尚未通过像素、性能、真实战斗、SATS、缩放/震动、破墙弹痕或RV兼容，不部署。
