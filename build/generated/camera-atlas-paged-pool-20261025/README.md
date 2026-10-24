# 固定世界分页：有界位图池候选

仅隔离源码候选，已完成下述暂停诊断，未部署。前版分页的暂停诊断已有移动改善，但跨页仍发生大位图创建；本候选只试着减少这些分配/释放，不宣称已经消除长帧或改善真实战斗。

基于冻结分页 helper `1D06B8B4127081D283860AE1B413ED0B08E4DC3BE0179CAD5263D2227C0ADBFA` 的14处可逆改动。`presentation_transform.transform(source)` 仍仅接受原始 C0E4 helper，返回钉住的替换文本；独立 `.as` 与嵌入文本必须逐字一致。`from_paged`/`reverse_paged` 检查14处唯一锚点并严格恢复旧分页源；`reverse(candidate, original)` 验证输入后恢复 C0E4。模块与转换函数不读写文件；不修改旧目录、宿主或共享源。

固定世界页仍为1280×1280、每页四层、320像素格。当前视口只占用需要的绑定页，附近旧页仍按原有顺序保留/淘汰。变化仅在淘汰后的处理：旧页从绑定列表移到空闲池，隐藏四张 Bitmap、清除格记录和对原生 surface 的引用，保留自有像素。下次缺页先从池中取槽，对四张 BitmapData 各做一次完整透明 fillRect，再重置格版本、key、世界位置；全部完成后才转回绑定列表并执行原同步。物理页 id 保持不变，供验证确实复用了同一槽。

只有没有空闲槽，且绑定页+空闲页少于8时才分配。绑定与池合计最多8页/32张位图/200MiB像素存储；空闲池也计入实际live与峰值。正常持续启用、Location和父层身份不变时，达到8个物理槽后跨页只重绑，不再 new/dispose 大位图。禁用、换Location、父层身份变化、clear仍全部释放；它们之后的新启用当然需要重新分配。像素阶段结束clear后，首B分配不能被历史peakPages掩盖或扣除。

其余逻辑保留：单位世界到Stage实际矩阵、整数平移、scaleV=1、整数有限quake才允许；force不能绕过几何/SATS/预算；静止显示原生但可同步当前页。每格消费统一revision，保留原生bitmap的实际visible，隐藏/缺块清对应格，全部同步完成后才隐藏原图；nativeBuffers始终只读。空闲页留在原父层但始终不可见，复用只改自有Bitmap的位置，不改原生显示深度或数据。复用继承该物理页初建时的smoothing/pixelSnapping及层位置，当前固定父层/原生参数的诊断可用；没有验证外部运行时修改这些属性后的兼容性。

计数含义：

- `pagesCreated/pagesDisposed`：真实物理页创建/释放；`allocations/disposals`及`physicalBitmapAllocations/physicalBitmapFrees`：真实BitmapData分配/释放，单位是单层位图。
- `livePages = boundPages + poolPages = pagesCreated - pagesDisposed`；正常完成状态下 `liveBitmaps = allocations - disposals = 4 * livePages`。`pixelStorageBytes`和峰值包含池，另列`poolPixelStorageBytes`；`poolVisiblePages`必须为0。
- `retargets`：成功重绑空闲槽次数；`fullPageClears`：重绑期间成功完成的整页逐层fillRect，正常状态须等于4×retargets。这些清空成本不能藏到copy计数之外。
- `rebuilds = pagesCreated + retargets`，表示新绑定内容次数；`copies`仍是原生格层→页的copyPixels；`cellsCleared/cellClears`仍是原生可见性/缺块变化导致的逐格逐层清零。
- 所有累计计数及peak跨clear保留，当前live/绑定/池和引用状态必须归零。不能把计数重置伪装成没有再分配。

性能代价仍可能存在：每次重绑要清25MiB，随后复制可见格；首建最多仍需分配200MiB。保留池提高跨页后的常驻内存，隐藏Bitmap仍在显示树中。本次未减少统一revision引起的四层复制，也没有修复宿主批量覆盖已有surface不增加revision的缺口；遇原生预绘/重绘变化仍应按隔离试验原门禁拒绝归因。

后续需同样通过五视口强制呈现RGB≤2/alpha全等、原生恢复精确、几何force回退、实际跨页与淘汰→重绑、完整释放。必须保留首建和清空长帧；在连续启用周期到8页后，实际allocations/disposals应保持不变而retargets继续增加。暂停世界结果不能外推战斗、开火、SATS/WB/RV或长时间探索。200MiB只是位图像素预算，不含原生图、Flash内部存储、截图及全进程内存，不能替代运行资源保护。

## 2026-10-25 r1 实测

证据：`knowledge/experiments/evidence/camera-atlas-paged-pool-20261025-r1`，探针`9B5A6706…D0FAA5`，原始结果`5E25D5C1…4A874A`。完整960连续帧26996ms；计时八原生计数全零变化，8遍1000次准备40730ms单列。五视口RGB≤1/alpha0、恢复精确，两几何回退及19截图释放通过。

计时阶段建8物理页，到满8后没有继续分配/释放；10次重定向与40次整层清空真实发生。像素阶段另有8物理页/1次重定向，全部阶段合计16页64张位图最终释放，峰200MiB。跨11个页键，复用已有物理槽的机制通过。

移动两对平均37.8167→32.5583、37.975→37.15ms；第二对中位35不变、P95 43→57变差。合并移动240帧/侧均37.8958→34.8542、P95 48→53；静止18.1583→21.575。首B86ms/work54，首次移动第46帧199ms/work146并新建1页，原生354ms/work1且缓存已释放；均保留，后者原因未知。不能称稳定明显提速，也不能与非池r2跨轮归因池收益。仅诊断门禁通过，不部署。
