# 原生自定义指标路线未完成，不作性能验收

r1在启动前发现RConnect已由其负责人更新2C49/animfix1，0构建/AIR，原run-before-rc-update.py与失败登记5d1aaf保留。已核对应安装回执5446D95A，r2仅更新这一依赖预期，不重标历史78C数据。

r2登记1df453c852a64b0e8a442a3b996166f2，自有AIR52744退出、临时配置删除、原世界/镜头/帧率清理通过。探针冻结a8f7192ba1544576b398678d0050db31；原生流38506319字节，180秒接收时限触发，游戏到769帧时因Telemetry断开停止。顶层camera-raster-complete失败，无完整960帧对照。

三遍预绘28141ms最后八值全零；五视口重复图精确一致、10图释放。测量开始getTimer=121595ms，已有大量启动/准备时间，不能把180秒全算作测量。六个完整窗口和49帧残段全部保留，不挑选成完整正反序。

只读流式清点3257097条后尾部还剩3字节半条记录；完整解析器正确拒绝。普通.trace有53条，但remains.camera自定义标记0，connected=true不足以证明自定义指标送达。已有记录中added/removed事件总数约190.8万/94.6万，包含启动，不等于游玩时每帧有同等负担。partial-inventory.json及partial-spans.json均显式validFullRun=false。尝试以.starttimer暂映射getTimer仅用于下一步假设，未校准、未作为正式归因。

后续只读查到正式A796无tag93，AIR二进制有“EnableTelemetry tag on child SWF was ignored”诊断文本，独立能力根SWF有tag93。仅为隔离宿主加tag93的源码方案在v2目录保留，但离线写入调用和精确grant均被hook拒绝、未执行。已转为camera-axis-trace-20261025的普通日志标记路线，不改宿主二进制，不降低画面或资源门禁。

正式526及13运行库保持；本轮没有部署、没有近原版已达结论。
