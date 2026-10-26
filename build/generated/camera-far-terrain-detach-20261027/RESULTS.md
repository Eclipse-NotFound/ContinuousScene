# 暂停不能保证原生图块集合固定

2026-10-27，冻结b93c4e8d47884030b9c9494901c71b0c，AIR61468，入图4546毫秒。
原始证据knowledge/experiments/evidence/camera-far-terrain-detach-20261027-r1。

三次完整预备循环，最后八项计数零变化；第一验图视角筛选121个surface中的204个
远处不可见原生Bitmap（四层各51）。候选和恢复均逐像素精确，408次摘除/恢复后
全部原位。第二视角原生surface又新增，原固定集合守卫失败，0计时。

28截图全部释放，terrainRestored=true、pendingOwnedBitmaps=0；清理完整审计因为
同一surface集合假设而restored=false，保留该失败，不能改称全部通过。没有性能结论，
没有新产品部署。世界暂停仍保留后台回调，先前完整路线一次计数安静也不证明以后
不再新增。下一版只能识别有证据的新增生命周期，不能停止预绘或追加等待挑通过。

已准备相邻camera-far-terrain-append-20261027：旧父层完整前缀保留、新尾节点均
对应四层新surface才接纳，原固定摘除集合保持。Drop仍明确不支持，不作为玩法验收。
