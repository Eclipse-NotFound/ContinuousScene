# 静止回原图、移动呈现合图：隔离实验转换

仅供暂停世界的整数镜头归因。未编译、未运行，不是生产设计。

`presentation_transform.transform(source)` 接受原始 `SceneRasterPresentation.as` 的 UTF-8 文本，SHA256 必须为 `C0E40368FD8BF6FE1413EC4C8D533C7034B18297AEB35119FBFEC4ADD5D93175`。模块装载时核对并加载相邻已冻结的 pow2 转换（`C9C071AB87588DD4CB0CECA161A4CBD89F4C2E04F1C7DC832DB6AEE892B984CD`）；函数先调用它，再应用七处可逐字反转的呈现控制修改。函数不读写文件，不生成游戏文件或完整源副本。运行器冻结输入时须同时纳入这两个转换文件。

接口变为 `update(w, enabled, forcePresentation=false)`，并提供只读观察用途的 public `presented:Boolean`。启用时仍按原逻辑创建、扩展和同步缓存，`copies`、`rebuilds`、尺寸、图层、像素复制、修订记录全部不变。仅当已有一次有效相机姿态，且本次 `cam.vx/vy/scaleV` 中至少一项实际变化，或显式 force 时，才隐藏原图并显示 atlas。首次非 force 调用创建缓存但显示原图；静止时现有 `beginFrame` 恢复原图，atlas 隐藏但保留。非有限姿态或非正 scale 不作为有效运动参考。

`beginFrame()` 将 `presented` 置 false，但保留上次姿态；成功 update 末尾记录本次姿态和实际呈现选择。`clear()`、`update(false)`、换图或原有父层失配路径仍执行原释放逻辑，并清除姿态和 `presented`。SATS 原有早退恢复保持，force 不绕过禁用、SATS 或几何检查。

像素检查必须调用 `update(world, true, true)` 并确认 `presented === true`；否则静止时直接显示原生会产生假阳性。计时仍调用两参数版本，并逐帧观察 `presented` 是否与有效姿态变化相符。它比较的是相邻成功 update 的相机字段，不是玩家位移，也不是完整世界到 Stage 的矩阵资格检查；单位整数、零震动等限制由既有诊断夹具维持。

本变体仍每帧执行原 `beginFrame` 与缓存维护，仍可能触发首次分配、跨缓存边界重建和复制。首建实测348ms、实际缓存128–256MiB没有解决；首帧和切换成本不能从计时删除。只验证暂停物理时的显示控制，不证明开火、长距离移动、缩放/震动、模组回调时序或生产兼容，也不承诺收益。
