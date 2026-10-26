# 源码准备状态，未构建或运行

准备了仅给A796测试副本增加EnableTelemetry tag93的四字节补丁和逐字节还原验证。离线调用被PreToolUse hook以binary-swf-use-release-pipeline拒绝；随后包含该精确调用的短时授权登记也被同一钩子拒绝。两条都未执行，没有metadata-check产物或新AIR。

不经其他路径重试该二进制写入，不关闭保护器。已转为camera-axis-trace-20261025，仅更改自有测试helper的日志标记，正式/隔离宿主保持原字节。本目录的run.py与host_metadata.py目前不可执行；analyze.py/capture.py的独立流式解析与时限准备可供不改宿主的诊断使用。
