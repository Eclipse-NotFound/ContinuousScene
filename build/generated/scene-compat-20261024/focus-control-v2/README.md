# FocusManager 成本上界诊断 v2

沿用原 4×300 帧负载与公共 activate/deactivate；只修正舞台焦点检查，并记录具体失败字段的类型。没有主动赋焦点或私有字段写入。

`evidence/focus-control-v2-20261024-scene-r1/`入图 4920ms、0 战斗样本时拒收：stage.focus 和 lastFocus 实际均为 same-stage，defButton 与 _defaultButton 均为 null。仍未调用 deactivate，没有性能结果；v1/v2 原始失败保留。

原版 World.step 会设置舞台焦点，FocusManager.focusInHandler 会记录其为 lastFocus。后续 v3 以这组实际状态为资格条件，关闭后允许 deactivate 原生清空 lastFocus，恢复时只用公开 activate/setFocus 与舞台焦点切换重建原生状态。该方案仅为隔离诊断，不能部署整个焦点管理关闭行为。
