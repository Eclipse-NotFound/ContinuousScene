# FocusManager 成本上界诊断 v1

只在独立测试进程临时关闭整个已有 FocusManager，以原 4×300 帧真实战斗观察该子系统的成本上界。不是生产候选；TAB、Enter、鼠标与菜单焦点功能不在关闭窗口验收范围。

`evidence/focus-control-20261024-scene-r1/`在入图后、0 战斗样本时被资格条件拦下：本版错误要求 `stage.focus` 为空。原版 `World.step` 会把焦点设置为 Stage。未调用 deactivate，cleanup.attempted=false/restored=true；失败与冻结源不修改，不称为性能样本。

后续独立 v2 允许真实 Stage 焦点，但仍错误要求 lastFocus 为空，详见 sibling `focus-control-v2/`。正式文件保持不变。
