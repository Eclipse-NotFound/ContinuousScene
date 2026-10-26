# 原生明暗层裁剪 v2

首轮lightBitmap是internal字段，动态外部访问报#1069，0计时、0修改；失败保留。v2通过public visLight的公开显示子节点，匹配public lightBmp的BitmapData身份，要求唯一对象；不读取internal字段。原裁剪、源像素只读、十三视角39截图、960帧、资格与恢复检查保持。候选尚未证明收益，不部署。
