# 无计数生产照明组件核验

仅隔离测试准备；本目录未编译、未启动游戏、未部署。`static-review.json` 记录锚点、原 89 个 spec 逐字保留、9 个拒绝负例及实际生产候选指纹核对。

同一宿主、同一帧、完全恢复输入之后比较两条独立分支：A 强制 `fogTypedEnabled=false`，执行准确 BEFC 中保留的动态类型旧分支并 return；B 显式开启 typed，运行该宿主的自然实现。原两例 legacy 的 B 仍为 false。新增两例仅临时令 `grafon.sceneLarge=false`，分别检查不透明物和不透明水，随后恢复；它们不代表普通房间玩法验收。没有新增 last-blocker 开关、计数或游戏类副本。

执行顺序（使用现有登记、私有桌面及内存门禁）：

1. `component-run.py --name <新的baseline证据名> --host baseline --compile-probe`
2. `component-run.py --name <新的candidate证据名> --host candidate --probe-build <第一步原始probe-build.json绝对路径> --reference-evidence <第一步证据名>`

第二步只接受第一步通过的 91 例、原始构建回执、完全相同的探针二进制/源码/编译配置/实际依赖。当前 RC 明确固定为 DF0FA0E2…DC01E7；旧 EB365 的性能证据不混入新组合。候选指纹在独立 `candidate-pins.json`，运行前后逐项核对该文件和生产构建/审计来源；此数据不进入探针编译输入，避免填指纹改变同探针要求。

每对比较全部原生 Tile 的 visi/t_visi 与 lightBmp 精确像素，同时检查原引用、公共状态、旁路 Tile、选择器及清理恢复。已有诊断 `fog-last-blocker-20261023-check-r1` 的四个人工场景确实命中缓存，但这里只引用其固定指纹作为既往覆盖证据；生产结果明确 `cacheHitsMeasured=false`，不伪称观察到生产命中。89 个旧输入和新增 2 个标志旁路都必须通过。

baseline 首先核准“BEFC 旧分支与 typed 分支”的比较方法，再由候选自身同帧旧分支对照生产 typed。两次启动可能有不同的自然交战状态；没有把跨进程原始像素直接当相同输入比较。场景几何、种子、视口、完整依赖仍须一致。本组件不计性能、不验证全屏显示或普通房间玩法。

`rejected-arguments.json` 保留首次被保护器拦下的纯源码写入参数；root 以已授权的精确调用登记后原样重放，未关闭保护或换工具执行该写入。
