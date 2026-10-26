# 节点取证完成，原像素恢复失败仍保留

2026-10-27，camera-display-state-20261027-r1，冻结6849b5e0，AIR58252已退出，运行器退出1。没有计时样本、产品修改或部署。

正常mainMenuOff入口；连续两次未改状态的原生截图逐像素完全相同。远景alpha恢复精确；六对象层alpha恢复后4028像素不同，最大RGB218、alpha0。6张截图均释放、数值清理通过；526正式/13运行库和冻结输入保持。原始失败没有改成通过。

11份只读快照各列2022个直接根，范围内递归928节点，无截断/读取错误；每份摘要100016位图像素。对象层0/1/2/3/4直接根分别895/400/265/449/13。首次draw前后167节点仅concatenatedMatrix不同；第一次draw后与最终恢复后的全部已记录公开状态完全相同，包括局部矩阵、颜色、帧号、位图身份/摘要。不能据此宣称内部渲染缓存也完全相同。

变化像素与角色、碎片、浮字等边界相交；几何重叠不等于来源归因。部分5×5 Bitmap处于非整数坐标。源位图摘要未变化，不支持“图像数据被alpha切换改写”。具体像素机制仍未查明。

证据在knowledge/experiments/evidence/camera-display-state-20261027-r1：storage/result.json、display-state-analysis.json与storage/display-pixels下真实PNG。analyze.py只读取图像和节点记录，不修改图像。
