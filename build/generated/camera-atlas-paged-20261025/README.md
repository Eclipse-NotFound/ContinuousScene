# 固定世界页合图诊断

只准备源码，尚未编译、运行或部署。它替换隔离探针中的 `SceneRasterPresentation`，不修改宿主、模组生产文件、物理、AI或原生地形生成；不是旧横条缓存或每次移动重建整张视口合图。

`presentation_transform.transform(source)` 仅接受冻结 C0E4 原始 helper 文本（SHA256 `C0E40368FD8BF6FE1413EC4C8D533C7034B18297AEB35119FBFEC4ADD5D93175`），返回模块内钉住的新类。单独 `.as` 是同字节可读副本；构建前须核对 `REPLACEMENT_SHA256`。函数和模块不做文件读写。`reverse(candidate, original)` 校验两个精确输入后返回原文；这是整类实验替换的可恢复性，不是新算法的语义等价证明。主驱动、暂停/战斗夹具及编译由根任务独立管理。

每个页固定在世界坐标 `px*1280, py*1280`，包含4×4个320像素格，每页四张1280×1280透明位图。层顺序仍是 front/back/back2/water；每层插在其原生最浅地形位图之前，并继承该位图的 smoothing/pixelSnapping。源只读取 nativeBuffers 的 `gutter,gutter,320,320` 中央区；不使用相邻页像素，不移动任何原图、不改其数据或 scrollRect，不新增边缘取样规则。

只分配当前视口相交页；额外保留附近最近使用页，不预先分配满8页。先释放超出当前页范围外一页的旧页，再按最近使用顺序逐出非当前页，之后才分配缺页。硬上限8页，四层位图像素存储最多200MiB，**包括创建过程的瞬时峰值**；不包括原生地形、Flash内部纹理、截图或其它程序内存，不能替代进程资源门禁。当前视口本身需要超过8页时回原图并报告原因，不偷偷扩大预算。

每页有独立的16格身份/版本记录。原生 surface 身份、统一 revision、nativeBuffers 身份改变时同步对应格；当前仍消费宿主统一 revision，一次修订对可见的四层都复制，不引入宿主逐层 dirty 接口。页首次创建没有旧记录，必须完整初始化所需格。只有原生 bitmap 当帧实际 visible 的层才进入页图；隐藏时清零对应格，surface 消失也清除旧像素，避免整页暴露隐藏地形。所有页同步完成后才隐藏所替代的原生位图。`cellsCleared`/`cellClears` 记录逐格逐层 fillRect 次数，不能把这项额外写图成本漏算在 copies 之外。

几何守卫要求 world 已在 Stage 中，实际 concatenatedMatrix 为有限的单位2D变换、整数平移，cam.scaleV=1，原始 quakeX/Y 也是有限整数；分数震动、缩放、旋转或不合法视口回原图。`forcePresentation` 只能跳过运动判定，不能越过几何、SATS、320格和8页预算检查。不合资格时停止同步、保留已有页并清 pose 资格；再次合资格先补齐版本，再考虑呈现。

motion 判定保留旧实验的 cam.vx/vy/scaleV：首次合资格且非 force 时显示原生；后续这些字段实际变化才呈现页。静止显示原生但继续维护当前所需页，仍有扫描、同步和可见性变化的代价；并未声称静止零成本。进入帧的原有 beginFrame 挂点必须保留，恢复原图供原生 V/SATS 捕获；SATS 激活时不显示页。禁用、换 Location、父层变化和 clear 均释放所有自有页，绝不 dispose 原生 nativeBuffers。

兼容旧公开接口：`update(w, enabled, forcePresentation=false)`、`beginFrame()`、`clear()`、`copies`、`rebuilds`、`presented`、`snapshot()`。`copies` 是 native→page 的格层 copyPixels 次数；`rebuilds` 现在等于创建页次数，不再表示整张大图重建。snapshot 保留清理验收字段，并增加 livePages/peakPages/pagesCreated/pagesDisposed、allocations/disposals、pixelStorageBytes/peakPixelStorageBytes、pageReuses/evictions/cellsCleared、requestedPages/fallbackReason、currentPageKeys/residentPageKeys/visiblePageKeys；fallbackReason 空字符串表示该次 update 合资格。

后续检查必须强制呈现并断言 `presented`，不能拿原生回退当像素通过。按用户最新授权检查 RGB 每通道最大差≤2、alpha完全一致，恢复原生要求逐像素全等。五个视口之间只 beginFrame 恢复、不 clear，跨1280边界往返并记录实际页集合；全部像素步骤结束再完整清理。计时首个B的分配、清理、跨页新建及可见性清零都要保留，页集合累计跨过8页后才可能证明淘汰路径。旧约240像素路线不保证覆盖这些条件。

尚未验证：页边缘的RGB/alpha、固定页是否减少实际移动成本、首次多页分配是否仍有长帧、跨缓存边界与开火、WB/RV/其它效果、异常回收、真实战斗收益。现有宿主 `scenePreloadRegions` 原地批量覆盖已有块却不增加 revision 的缺口仍存在；这个 helper 不能凭像素身份识别该写入，后续隔离运行必须记录批量生成/重绘，不能将其漏更新说成已兼容。未引入每帧全像素比较来推测 dirty 层。8页预算只是诊断约束，不是产品内存或收益资格。

## 本轮暂停诊断配方

主驱动仍从B7ED收据的85源冻结闭包派生，只改Main、替换Atlas并增加Trial，合计86源。实际宿主继续A796；新测试采用RV负责人已验证部署的0.33.10/638E2D40，核对其deployment/receipt.json并冻结输入，不改旧BF4A试验标签。灯光、RV与WB在隔离试验中关闭，正式选择保持。

原生地图预绘完整路线后，五像素视口按中心、右下960、左下960、左上960、中心顺序保留缓存检查；两次额外变换检查强制呈现也不能绕过小数平移/缩放回退，原生回退像素须完全相同。计时前清空候选缓存；8×120窗仍为native静止/移动、atlas静止/移动/移动/静止、native移动/静止，960个连续时间间隔全部保留。移动路线为4个非零腿×30帧，步长32/64像素，保留首建和跨页分配、逐出、清零及切换成本；此为暂停归因，仍非实战FPS。

新增逐帧真实页集合、可见页、创建/释放与内存峰值；要求累计访问超过8个世界页、实际发生淘汰和离开后复用，不能仅凭每帧缓存命中计数宣称复用。结束须自有页全部释放、创建与释放相等、native精确恢复。原生绘制/预绘/驻留计数在960帧中必须不变，否则不作该归因。

## r1结果与r2准备修正

配方提交5192969，r1探针92AA01340EC9336F38CC88D9D0A8FEAB91B80955B221E36CF57FD881735CFB4E，证据在knowledge/experiments/evidence/camera-atlas-paged-20261025-r1。运行完成960帧/32857ms、9项游戏断言，但计时期间原生resident+16、redraw+19、warmSlices+52，全在移动窗；runner依原标准记failed，不把完整运行改说成归因通过。

五view最大RGB1/alpha0、精确恢复；两次几何force回退像素全等，19/19截图释放。B移动实际11个世界page keys、30次进入、6次已见key返回而创建计数不增；途中有淘汰，终态27页/108位图全部释放、峰8页/200MiB。累计分配675MiB，其中像素阶段225、计时450；两B移动窗各创建6页/150MiB，分页没有消除动态分配。

八窗均值为19.808/55.108/27.300/38.125/42.842/26.275/40.458/23.892ms。两组移动方向不同且预绘负载不匹配，不宣称分页提速。独立审查核对了完整时间戳、像素、真实呈现链及资源守恒。正式包未由本任务改动。

r2仅把准备阶段改为重复完整125点路线，逐遍记录八项计数差；最后一整遍全零才进入像素/计时，最多12遍否则失败。计时前仍清候选缓存，原960帧和归因门槛不变；这不算加载性能，也不保证所有方向的预绘已穷尽，若计时仍有变化继续拒绝该归因。

r2已实际通过，探针F73FC7197A7EA4F922EEE480B20B5A37549FCBFFF86B516685CE5771EF4F0C79，原result SHA2062F0ECFD13DF09B88E63B412E29CD8ABEC9528B2D78F06DBC03D38E55B050F。6遍/750次原生预绘、34336ms后八计数整遍为零；随后960帧/31903ms逐帧八计数不变。五view RGB1/alpha0/恢复0，两回退精确，页覆盖与释放同r1。合并移动A43.4792/中40/P9570→B35.8875/34/47ms；两对38.675→34.9583、48.2833→36.8167同向；静止A25.5208/中22/P9536→B28.0417/25/43ms。原生时间亦有漂移，约17.46%只属本轮暂停归因，不外推稳定产品收益。

首B115ms对应work83、创建6页/128copies；B移动235ms对应work4、0创建/复制、32格层清零；后静止264ms对应work2且无创建/复制；末原生315ms对应work0且无atlas驻留。后三次不能仅据区间余量归因GC。分页仍各移动窗分配150MiB，后续有界池复用在独立目录准备，是否改善长帧尚待验证。独立复核仅读取JSON记录，实际冻结/正式输入指纹由注册runner验证；无本任务生产部署。
