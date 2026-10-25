# 远处原生地形位图摘树：隔离诊断草案

仅源码准备，未编译、未运行、未部署。它回答一个尚未被旧 visible=false/合图实验覆盖的问题：已经由原生判断为不可见、但仍在四个地形父层中的 Bitmap，实际移出舞台树是否会降低镜头移动成本。没有预设收益；不能用作生产实现。

`tests.SceneNativeTerrainDetach` 只借用 `sceneSurfaces().bitmaps[0..3]` 的父节点关系。原 Bitmap、nativeBuffers、scrollRect、颜色、可见性、世界坐标、marks 与逻辑均不写；不复制、释放或替换像素，不移走 scratch、WB覆盖层、对象父层或实体。`removeChild` 后 parent=null，由自身记录保持引用。

## 接口和时序

- `begin(w:Object):Boolean`：场景预备完成后调用一次。保存所有 surface/四层位图/数据身份，以及四个父层的**完整直接子序列**和位图属性。任何不明结构失败，不放宽资格。
- `beginFrame(w:Object):void`：最高优先级、原生更新前调用。仅检查本场景与禁止SATS条件；正常情况下不把所有节点每帧恢复再摘除。
- `update(w:Object, enabled:Boolean):Object`：原生 camera/sceneTick、其他已获准原生更新之后，实际呈现之前调用。原生仍可对离舞台的同一 Bitmap 写 visible。先按原顺序归还已经 visible 的节点；B再从原子序列末端摘下不可见节点。A归还全部。未移动的远处节点跨帧保持离舞台，避免主动制造每帧全部移树。
- `snapshot():Object`：只读计数；不返回原生对象引用。
- `checkPixels(w:Object):Object`：仅在连续计时关闭后、终态A且held为0时调用。用实际 `w.visual.transform.concatenatedMatrix` 绘制到真实Stage尺寸透明画布，依次原生/摘树/归还三张同帧world层图片；不是包含HUD的整屏截图。返回 `valid/equal/restored/heldPositive/nonemptyNative/cases/samples/bitmapsCreated/bitmapsDisposed/elapsedMs/errors` 及前后快照，逐像素必须精确相等。三张图片与可能产生的比较差异图全部finally释放；空原生图或没有真实held均拒绝。此终态检查不能代替真实跨视口与其他功能组件。
- `clear():Object`：终态/失败 finally 调用，幂等归还。`restored` 只有无错误、无跳过且held为0才真；不能只看pendingRestore为0宣称通过。

`update` 返回 `enabled/applied/previousApplied/valid`、四层 `nativeVisible/nativeInvisible/heldByLayer`、`enteredRestored/restoredThisUpdate/newlyDetached/ownMs` 与快照。`previousApplied` 是上一update结束的实际状态，用于对齐连续帧；切窗归还成本不得丢弃。快照保留 `held/pendingRestore/detaches/restores/droppedSkipped/enteringRestores/peakHeld/updates/headChecks/scannedNodes/structureChecks/elapsedMs/errors`。正常运行应满足 `detaches-restores==held`，清理后均归还；失败跳过另列，不能算正常归还。

## 第一版的强限制

运行器必须精确冻结正式A796/CS7F1F及实际依赖，明确关闭RV、WB、LAD显示效果并证明配置生效。helper不跨loader反射猜这些开关。运行器也必须禁止SATS输入/菜单进入；helper额外检查keySats、sats.active及visSats.visible，但这不是生产截图前恢复hook。原生sceneSats会在方法内部临时显示所有块再draw世界，离树节点不会自动回归，**任意未被提前检测的同帧截图都未覆盖**。

第一版只接受固定resident集合和固定四父层直接子序列：新增、替换、销毁surface或其他直接节点、父层变化、数据绑定/显示属性变化都使本window/整轮失败。它不阻止原生预绘，不为了通过而关闭守卫。测试应先完成原生预备；如果真实战斗中持续新增块，本版本不具备有效计时资格。新增无害节点也不默许。

每帧A/B都做同样的surface身份、属性及完整父层子序列核对；B还执行真实摘树/进入归还。扫描、属性读取、数组和事件成本在完整连续时间里保留，`ownMs/elapsedMs`只是观察，不能从帧间隔扣除。新旧节点进入/离开不创建图像缓存。

正常恢复按原序插入，完整子序列须完全一致。失败清理只对仍由当前场景surface持有、原data还活着的held节点，依原相邻节点尝试归还；未知归属不挂回、原生已Drop的节点不复活。发现结构变化即失败，即使可保守归还部分节点也不把新结构判成原结构。无法安全归还保留pending和错误，由隔离进程结束释放；不允许在正式实例使用。

## 待根任务接入的最低验证

1. 真实旧样本首计时帧102块×4=408节点，只有每层35可见，268隐藏节点仍在树上；这只是候选覆盖数量，不是性能证据。新轮必须记录自己的数量，不能沿用旧计数。
2. 同帧原生/摘树/恢复像素对照（应精确相等）；非目标父层、所有对象层、原数据与属性保持。不能把只有静止、没有实际held的空对照算通过。
3. 镜头移动使已held块重新visible后，必须本次update归还；真正近→远→近过程需有 `newlyDetached` 和 `enteredRestored` 阳性，不得只改变测试标记。画面、远处弹痕/破墙/水写入再进入仍需验证。
4. A/B/B/A保留全部4×300原生SMG战斗、真实物理/开火和连续切换成本。终态无错误、全部顺序精确归还，宿主/模组/保存输入守恒。若resident变化使守卫失败，保留失败，不把残缺窗口拼成收益。
5. SATS/换图/重绘/Drop的失败归还必须另查；本版只允许观察诊断失败，不声称功能兼容。纯Bitmap无MovieClip时间轴，但移树仍会触发ADDED/REMOVED等事件，是否有外部监听影响必须以实际验证为准。

参考依据：A796已核对应Grafon `sceneCullSurfaces` 仅写visible；`sceneApply`直接写nativeBuffers；`sceneDrop`解除当前父节点并dispose数据。`scenePreloadRegions`漏revision是旧像素副本缓存问题，本方案沿原数据绑定，不需要靠revision更新副本。当前没有修改任何这些原生方法。
