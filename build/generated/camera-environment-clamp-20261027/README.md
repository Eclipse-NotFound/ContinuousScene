# 区域环境坐标：去掉两次可变参数Math.max

镜头分配栈实测在40个区间中把65312次AS分配归到Grafon.sceneNativeEnvironment，全部调用者是Location.step。先做最小单项验证：两处int(Math.max(0,x)/cellSize)等价改成int((x<0?0:x)/cellSize)，y同理。保留负数、NaN、无穷与int转换行为；-0在除法后转int，输出仍为0。

仅在当前A796宿主的sceneNativeEnvironment方法体替换已核实的两个指令片段；全部其他指令和分支目标按偏移保留。没有新字段、常量、方法或类。独立副本构建；正式文件不改。先核区域判定、实际分配，再用不采样的完整镜头路线比较；源码等价不能代替性能或玩法验收。

本目录是候选，不是已部署优化。Math.max是否解释大部分分配以及实际收益均待验证。
