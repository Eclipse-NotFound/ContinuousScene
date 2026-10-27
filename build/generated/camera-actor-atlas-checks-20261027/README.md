# 同一世界的显卡调试检查开关对照

此前候选设置Context3D.enableErrorChecking=true。[AIR官方文档](https://airsdk.dev/reference/actionscript/3.0/flash/display3D/Context3D.html#enableErrorChecking)说明该开关使clear/drawTriangles同步执行并降低性能，默认false为异步。本轮只切换这个图形调试属性，资源上限、输入验证、隔离与所有恢复断言不变。

同一世界12段：原生静/动、GPU检查静/动、GPU默认异步静/动，然后逆序返回；每段120区间，总1440。各段记录实际enableErrorChecking值。开场13次和结束5次像素参照都开启检查；计时默认异步路径的OS呈现和画质仍需后续独立验收。相机、敌人、显示树、缓存逻辑不在条件间替换。

只判定调试设置的影响，不能从预期推断收益。场景模拟仍暂停，动画继续；父候选画面错误未预设解决。运行后冻结，不部署。
