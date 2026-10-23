# 图章绘制容差组件

独立复制旧 `decal-stamp-proof/tests/SceneDecalStampProof.as` 后修改；旧文件和旧证据不变。本侧只准备源，未构建、未启动 AIR。

接口仍为 `SceneDecalStampProof.run(w):Object`。`REQUIRED_HOST` 固定正式 `80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D`；调用方必须验证实际 SWF 哈希，运行时另核实际 World/Grafon 域、素材类名与帧数、隔离应用 ID。

- `valid`：全部计划执行完、每目标确有原生绘制变化、素材/域/清理/宿主引用检查通过。
- `equal`：严格逐像素一致，不因用户接受容差而改义。
- `tolerancePassed`：所有比较的 alpha 完全相同，R/G/B 各自整数通道差不超过 1。
- `completedAllCases`、`exactCases`、`toleranceCases`、`failedCases`、`invalidCases` 和 `executionErrors` 单独记录；像素不等不会中断后续计划。
- 每例保留 `details.maxARGB`、差异/越界像素数与包围框、一般示例和专门的 `failureExamples`。总 `elapsedMs` 与每例累计耗时只表示本组件成本，不是提速证据。

计划为 172 次最终比较：原四种正常 paint 几何及六个多帧素材的全部 25 帧，共 29 计划；每计划比较同原点、右、下、右下四目标，计 116 次。另每素材各做 8 次完全同位同图章叠加、12 次交错位置/帧/颜色重叠，计 48 次；再对旧 r4 已知误差例 bullet_tre 第 5 帧、几何 `[1.7,.71,.5,.25]`、颜色 2，分别重复 8/32 次，每序列四目标，补 8 次，共 56 次序列最终比较。两个目标从同样底图各自连续累积，序列中不复位、不互抄、不修正 RGB，最后才比较；每步的 alpha 保存/恢复仍执行原生算法，且只读该路径自己的当前 alpha。

首轮隔离实测中，AIR 的 compare 差图在 alpha-only 哨兵上得到空范围；该轮 0 实际绘制例，不能解释成图章失败。原冻结产物和证据保留。活动 helper 已改为直接通过两个源位图的 `getVector(rect)` 全扫每个 ARGB 像素，不再依赖 compare 返回值或差图包围框跳过像素。向量为单次比较的局部临时数据，末尾清空引用，不放进游戏缓存。正式比较前仍有四例 8×8 哨兵，用同一方法检查完整的变化数、alpha/RGB 变化数、最大差与容差违规数，同时逐点核对 getVector 与 getPixel32 相同，含低 alpha 和相反角/跨行边界；哨兵失败会使组件无效。每 16 例有一条隔离进度 trace。172 例共扫描 27.52M 对像素，耗时须由新实测的 elapsedMs 确认；组件临时分配不作为提速证据。

范围限制明确写进报告：world edge、部分源图章、超过公共边缘的图案、erase/hardlight、改变 alpha 的 ColorTransform **没有覆盖**。相邻块使用完整包含在 80 px 公共边缘内的素材，不能将其解释成上述边界通过。接受像素容差也不代表已经达到性能或部署要求。
