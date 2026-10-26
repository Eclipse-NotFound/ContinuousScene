# 在帧末核对滚动状态，分开下一帧的原生相机更新

cost-r1全部5视角自然/恢复精确，候选均maxRGB3不合格；计时120原生帧+第1个滚动间隔后
被“Terrain changed during rendered interval”中止，未得到完整对照。错误实际检查世界容器
位置/裁剪，不是地形像素。旧Camera参考显示原生calc每帧写world.x/y；尚未由该失败直接证明
实际变化是哪项，不能直接删守卫。

本变体增加只读EXIT_FRAME观察器，记录每个pending序号的帧末状态；它必须与刚应用的状态
完全相同。下一次ENTER_FRAME检查只允许x/y被写回同一镜头的原生vx/vy，其他属性不得变。
同时保留入口和帧末完整数据，可核对推断。观察器不驱动/重设镜头，不强制invalidate，退出移除。
官方时序：EXIT_FRAME在帧脚本运行后广播；此观察不证明物理显示器呈现或所有其他EXIT监听顺序。
https://airsdk.dev/reference/actionscript/3.0/flash/display/DisplayObject.html#event:exitFrame

仍为无缓存方式的代价诊断，visualAccepted/qualityFailures明确保留RGB2的拒绝结果。
只读帧观察开销纳入两组计时，不以raw.ok当画面或产品通过，不部署。480帧、75截图及原清理保留。
