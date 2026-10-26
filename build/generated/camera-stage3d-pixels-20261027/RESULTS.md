# Stage3D 分层留图结果

仍在首视角画面对比中失败，0计时帧；未部署。

- camera-stage3d-pixels-20261027-r1，冻结cbff2106f1bc45f7872a937e3e9ff108；AIR59652退出。
- 原生/候选差931853像素，maxRGB211，alpha0；恢复原生精确。3截图全部释放、81纹理与Context全部释放，峰值60010752字节；526正式/13运行及冻结输入保持。
- PNG见证据storage/stage3d-pixels：gpu-raw-1是地图远景与原生两背景层；candidate-0却露出标题菜单，native-0没有。原始绘制命令与此前完全一致，只增留图。
- 对应夹具入口源直接写mm.active=false后newGame；原版MainMenu.mainMenuOff同时移除菜单显示节点，未被执行。因此Stage3D位于显示树下方时被残留菜单遮挡，先修正测试入口再比较。
- 本轮不能归因为显卡采样精度，也不能据此得出性能好坏。此前同源夹具的绝对耗时亦带此测试入口限制；不覆盖历史证据。

