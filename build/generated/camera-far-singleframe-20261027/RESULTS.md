# 遮罩盘点早退，无计时

证据camera-far-singleframe-20261027-r1；冻结5e968e0e8c164f33a6f54519bdc4f31d，AIR59812退出。
0帧计时；scanned=selected=transitionWrites=0。全舞台遮罩递归发生#1009，错误点位于
首次根筛选之前，尚未写可见性。截图已全部释放，cleanup.restored=true。

无法仅凭#1009证明具体哪一节点为空。后续版本加入空节点保护、mask单次读取及逐路径错误
信息，其他读取异常仍中止；未把本轮错误当成已确认根因或有效性能结果。
