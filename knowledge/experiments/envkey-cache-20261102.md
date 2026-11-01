# 2026-11-02 修复 A（sceneNativeEnvironment 单元格缓存）：机制成功、帧收益不足，不部署

## 背景

gc-source-attribution-20261102 定位首要垃圾泵为宿主补丁 `Grafon.sceneNativeEnvironment`（每对象每帧拼区域键，~2,812 纯垃圾 String/帧、99.7% 即死）。用户授权按推荐实施修复 A。

## 实现（`build/generated/envkey-cache-20261102/`，候选 `029DAF34…`）

- 单方法替换：逐单元格**结果缓存**挂在模组拥有的 state 对象上（`state.cellCache` 为 int 索引稀疏数组，首次查表后永存；byCell 不可变，缓存随 state 重建自然失效）；`width<=0` 的旧 state 回退原字符串路径——**与任意新旧模组双向兼容**，无新增 Grafon 字段（类布局审计不变，仅该方法 codeBytes 变化）。
- 构建时修复了宿主导出源中两处 FFDec 反编译残渣（`§§findproperty` 循环递增、`§§push/pop` 布尔链）为等价可编译写法；这些方法不参与移植，候选中其字节码保持原宿主。

## 验证

1. **功能（候选宿主，登记 game-coexist）**：mechanics 27/27 + issues 16/16（`envkey-v095-mechanics-r2`、`envkey-v095-issues-r2`；r1 超时是运行时清单被 motion 流程改写的环境失误，非候选问题）。
2. **归因复测（v14，`envkey-gcattrib-r1`）**：`sceneNativeEnvironment` 从分配/垃圾榜首**完全消失**（总采样分配 382,817→344,613）——泵确已消除。但单次运行 GC 掉落 10 次/~65MB/32 长帧与基线（10/33）持平。
3. **配对测量（v13，4 轮交错 `envkey-gctail-{base,cand}-r{1,2}-x*`，同布局种子、CS0.9.5 全栈、独占 game）**：

| 轮 | GC 掉落 | 总掉落MB | >100ms |
|---|---|---|---|
| r1 base→cand | 9→8 | 539→486 | 13→23 |
| r2 cand→base | 9→8 | 549→486 | 9→9 |

GC 掉落 −11% 方向一致但幅度小；长帧不一致（r1 恶化、r2 持平）；各阶段均值混合（pan 两轮 +5.6/+6.6ms，walkL/final 改善）。**无整帧级稳定收益。**

## 结论

1. **不部署候选 `029DAF34`**：机制完全成功（首要泵消除、GC 掉落小幅一致下降），但未达到"真实明显提速"的部署门禁——再次验证"减分配≠减帧时"：~65MB 周期回收由**总分配速率**驱动，区域键字符串只占约 10–15%（掉落次数 9→8、体积 −10% 印证），其余来自原生渲染内部件（46k/窗）、炮塔/部件 gotoAndStops 链、AddictionSystem 每单位 JSON 及单帧窗看不到的中寿命对象。
2. **GC 方向的诚实边界**：单点垃圾源修复在此规模下不足以移动整帧指标。要有意义地降低回收停顿，需要同时削减多个中大型源（方向 B sceneEnsureUpcoming 键现为垃圾榜首 ~9k/窗、AddictionSystem JSON、RConnect NetHud——后两者属外部模组），或从分配量级最大的原生渲染侧入手；这些组合改造的预期收益仍需先以配对测量验证。
3. 候选与全部证据保留；生产宿主 A9B3、CS 0.9.5 未动。

## 证据

- 功能：`evidence/envkey-v095-mechanics-r2`、`evidence/envkey-v095-issues-r2`（r1 超时残迹保留）
- 归因：`evidence/envkey-gcattrib-r1`；配对：`evidence/envkey-gctail-*`（-x 后缀为争用重试）
- 构建：`build/generated/envkey-cache-20261102/candidate-build.json`
