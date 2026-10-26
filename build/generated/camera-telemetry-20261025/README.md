# 镜头移动的原生耗时记录

目标：用户要求以镜头移动（不论敌人是否出现）为核心。分轴暂停诊断已复现移动额外开销，原生滚动缓存倒退，四节点填充净收益不足。本目录先验证AIR原生telemetry能力，再将原生绘制/脚本时间与镜头路线标记对齐；不靠回调外余量直接宣称GPU瓶颈。

独立能力应用TelemetryCapability运行120帧，发送带唯一appid的120个标记、20个约3ms已知工作区间，要求流中均真实出现并具有原生.rend耗时。只启动自建AIR，私有桌面、唯一存储、共享game登记；不加载游戏或改部署文件。

capture.py仅绑定127.0.0.1随机端口，不向外部服务器发送数据，不接受外部地址。AIR要求用户目录.telemetry.cfg：运行前要求两种配置文件均不存在，独占创建，只在确认为本工具的原字节时删除，冲突保留并报错。上下文最长180秒（能力测试45秒），收集上限128MiB；finally停止接收并清理配置。异常中断的准确配置路径/摘要在capture-status.json，须核对自有进程和内容后再清理；不覆盖他人的配置。正式原生耗时只用于诊断，不能把记录开销忽略或作为优化收益。

来源：[AIR官方Scout说明](https://airsdk.dev/docs/tools/development/scout/usage)、[Telemetry API](https://airsdk.dev/reference/actionscript/3.0/flash/profiler/Telemetry.html)、[Adobe源码](https://github.com/gpeacock/telemetry-tools)。vendor为2026-10-25读取的原文件，保留原版权头：amf3reader、telemetry、flmserv为Apache-2.0；add-opt-in为Adobe 2012的BSD式许可。未直接执行其监听器或原地SWF改写工具。仅导入amf3reader，并检查原始流完整消费、类型、上限和标记；遇到不支持的数据停止，不容错丢弃。

|文件|SHA256|
|---|---|
|amf3reader.py|5069D8CE17858E2625D3C309EDC17099A6DA6C147AC7612BD9D7DB021E2F20F3|
|telemetry.py|7EC7699326271A57D6D9893F400D7BFD2A71A61E85FF756E207A49373B11EA84|
|flmserv.py|D7639F4711931640B9DF8B7ACEE0466AC5629C1205C27CF3A06FE100083E9F9F|
|add-opt-in.py|067E00CA4F3D0A33B0C02781D8998CBCB53394D37DA3189681A9728A756BA4FB|
