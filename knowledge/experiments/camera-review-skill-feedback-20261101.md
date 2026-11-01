# 2026-11-01 技能实战：迭代审查与镜头卡顿归因

被测技能：code-review（2026-10-08.1，C:/Users/hello/.agents/skills/code-review/SKILL.md，20eb443874b0acf377206900a1e1b6a1705b8d23005b0c10246082f4a4e78258）；remains-auto-testing（2026-10-27.1，工作区 .agents/skills/remains-auto-testing/SKILL.md，d4b08a7f0d2643bf6afe3864d07a996e334ff61d570e133c4ab8567e9f6874fe）；remains-runtime-debug（当前工作区正式版，6c5d30bf90748a0532356b3ac469419ab7775e13add3b35e73e362f6a4236b79）
技能归属：code-review 为用户级；后两项维护驻地为 Remains/mods/ModLoader
测试工作区：D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene

- 自然选用。以实际部署字节和忽略的构建配方补足 git diff；Standards/Spec 分开报告，未启用子代理。按调试技能固定模组组合、独立副本/存储、实际可见的私有桌面、静音和共享测试登记；编译采用已有工具链。
- [业务报告与证据](camera-iteration-review-20261101.md)：原生隐藏状态被新 sceneTick 覆盖，A80 阴性对照成立；四个有效时序测试12684个间隔，横纵移动、分层与内存关联分开；未部署产品改动。
- 新问题：auto-testing 的程序化驱动示例仍把 `mm.active=false` 当成第0步；它只放行循环，未移除菜单显示层。本次按旧写法复现菜单挂在世界后方。应由维护侧核对是否把正常开档入口改为 `mainMenuOff()`，并验证主显示树；不能据此声称所有旧测试被菜单完全遮挡。
- 执行偏差：本轮前两次准备失败来自复用静音助手的固定目录限制、未等待全部设置页注册；后续独立目录绑定和设置就绪检测修正。第三次等待周边补绘不足8轮，保留失败原件，延长有界准备后通过。不是产品修复，也不证明技能全部分支通过。
- 测量纪律的新证据：旧计时回调内像素哈希污染阶段45；30fps上限掩盖容量成本；分配条数不等于字节和收益。新probe仅在块边界外作检查，无像素哈希；完整保留块内长帧。后台桌面结果不是显示器呈现延迟。
- 追加：当前字节12/12分配采样有效；炮塔重建子显示对象/FocusManager链、TDFC快照等已定位为候选。分配数、尚存活对象size、整帧成本保持分开；仍不把此诊断当成部署收益。
- 处置：待维护核对。没有修改正式技能。用户对本轮结果尚未反馈，不推断满意程度。已查重追加全局测试报告台账并回读确认唯一一行，既有记录保留。
