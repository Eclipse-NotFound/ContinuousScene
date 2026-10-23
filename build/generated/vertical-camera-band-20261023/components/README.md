# 纵向镜头缓冲组件检查

入口：`tests.SceneVerticalCameraChecks.run(w, check = null, expectCandidate = true)`。
将此目录的 `SceneVerticalCameraChecks.as` 原样复制到隔离探针的 `tests/` 包后编译。`expectCandidate` 必须由固定运行配置显式指定：正式 `80CF` 为 `false`，经审核的候选为 `true`；不能根据状态是否出现来猜宿主。

组件在已经初始化的真实大场景中同步调用实际宿主 `Camera.calc`。它暂停世界物理，并以实际 `Camera`、玩家和已存在的 `Location` 对象构造几何边界输入。检查首次初始化、缓冲范围内外、远距位移、实际缩放键与外部 `setZoom`、逻辑屏幕尺寸改变、低屏高、过高碰撞身体、普通场景与 sky 回退、API 缺失、观察与剧情镜头及 `camRun`、地图边缘、镜头与地图身份变化、震动余量；还核对瞄准坐标换算、声音中心及世界/SATS 显示层同步。

这不是跳跃、移动物理或帧率验收，也不是图像比较。改变的是 Camera 的逻辑 `screenX/screenY`，真实 Stage 和 `World.swfStage` 不写入；不调用 `setLoc` 覆盖夹具。实际碰撞高度 `scY` 表示从脚底 `Y` 向上的完整高度，不代表武器、头发、翅膀和特效边界。

为避免真实 `calc` 尾部的 `sceneTick` 改动地形缓存，组件暂置公开 `grafon.loc = null`，保留 `sceneLarge`，因此原生 `sceneTick` 的第一条空位置判断直接返回。仅此组件采用这一隔离方式，不能据此宣称分块呈现正确。

`finally` 恢复所写的玩家碰撞几何、控制键、镜头、位置引用、公开地图标志、Grafon 引用、显示对象坐标/缩放/透明度、`World.w`、世界瞄准坐标和日志、`Snd` 中心及 API 原状态对象身份。先移走原 API 状态再开始，避免改变原状态对象的内容。每个恢复字段随后比较。

有两项明确例外：真实缩放键产生的 GUI 私有提示/计时器，以及原生震动消费的随机数不能完整回滚。它们只存在于独立组件进程；运行后必须退出，不保存、不接任何性能采样或继续游玩。缩放提示追加的公开 `World.log` 会恢复。

返回值包含 `passed`、`terminalOnly: true`、`expectCandidate`、逐例 `cases[].passed`、`restore.passed`、`elapsedMs` 和限制。基线使用原生表达式期望，候选使用各例明确的缓冲/重置期望。缺少第二个真实位置对象会记录不确定且使整体不通过，不伪造位置对象以凑齐覆盖。

入口由独立 `--components-only` 轮调用，与真实输入性能轮分离。首轮隔离运行在初始读取宿主 `World.w` 时发生 `#1069 tests::w`，尚未修改世界或执行任何 case，不能算行为验收。活动源码已将宿主 Class 的全部静态成员读取和公共字段快照/恢复统一改成显式 public `QName`；保留首轮冻结证据，修正版尚未重新构建或运行。这里读取的 `World.w/cellsX/cellsY` 与 `Snd.centrX/centrY` 都是 public static，不涉及 internal 字段访问。
