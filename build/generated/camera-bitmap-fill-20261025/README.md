# 四节点原生像素填充对照

用户要求镜头移动在有无敌人时都接近原版流畅度。上轮分轴诊断证实固定场景的移动额外开销；原生scrollRect缓存移动倒退18.2%，停止。此处改变显示表示，不复用该缓存：front/back/back2/water每层一个Sprite.graphics，通过beginBitmapFill借用原nativeBuffers，在320px中央矩形填充，保留40px gutter取样原点。不创建新地形BitmapData、不copyPixels、不设cacheAsBitmap、不移动世界或对象层。

原Bitmap只暂设alpha0以免重复绘制；visible留给原生cull管理，每帧按实际visible生成参与列表，列表/身份/修订变化才重建绘图命令。清理恢复每张原Bitmap的alpha并清空全部命令、移除四节点，绝不dispose原nativeBuffers。原像素、碰撞、AI、弹体没有改动。逐帧扫描/排序/资格检查包含在计时，不能宣称零维护成本或没有底层临时内存。

仅暂停诊断、320px块、比例1、整数平移、零震动、SATS关闭、默认位图颜色/混合/裁剪契约。未验证普通战斗动态修改原位图时图形填充失效传播、SATS、缩放、RV/WB兼容及完整离图清理；不是产品候选的完整回退逻辑。

冻结29AF 85源→86源，只改Main、替换SceneTilePresentation并增加Trial。helper从已验证滚动缓存试验仅改名称与说明，原960帧静止/移动正反序、五视口RGB≤2/alpha0/恢复全等、15图释放与预绘八值稳定门槛保持。每帧另外要求B有4个实际节点和非零填充命令、A全部为0；终态创建/移除相等、0原图记录、自有位图分配/像素复制均0。

独立AIR/存储、共享登记、私有桌面、正式输入/运行库/源指纹与内存保护沿用。原30fps暂设120，World模拟暂停但时间轴/其他回调仍在，结果不是真实游玩FPS。通过后仍需实际战斗显著收益与功能门禁才考虑部署。

API语义只采用[官方Graphics文档](https://airsdk.dev/reference/actionscript/3.0/flash/display/Graphics.html#beginBitmapFill())；它支持位图填充和矩阵，并不保证此方案在本游戏加速。
