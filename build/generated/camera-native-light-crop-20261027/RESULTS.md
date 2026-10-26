# 首轮因internal字段不可访问停止，0修改/0计时

2026-10-27，冻结b3627b7ba62c4071956fdc6457baa179，AIR32684退出。
外部动态读取Grafon.lightBitmap报#1069；原生声明为internal，visLight与lightBmp为public。测试在应用裁剪前停止，0新位图/复制/呈现，1张原生截图释放，镜头与状态恢复，正式526/运行13保持。

v2使用公开显示树中唯一BitmapData身份匹配，不读取内部字段。原失败保留，不放宽画面门槛。

