# 单帧弹壳的局部时间线验证

2026-10-24，正式游戏保持 A796，未部署此实验。

`components-r1` 在编译阶段因旧 Flex 的 Object→Array 类型检查失败，没有启动 AIR。根代理只将 `afterA/afterB` 显式声明为 Array，原失败冻结源和日志保留。

`knowledge/experiments/evidence/shell-timeline-20261024-components-r2` 完成局部验证。三对实际 `visualGilza` 新素材分别用原生 `gotoAndStop(1)` 和候选 `stop()`；每次均保留一次随机数消耗，后续位图缓存、坐标、旋转、缩放及染色相同。即时及真实帧后每对 65,536 个 ARGB 像素全等，子树和引用稳定，捕获边界完整且边缘透明。Stage 收到两次 ENTER_FRAME，每个克隆实际收到一次，不能表述为每个克隆验证两帧。6 个克隆停止并移除、12 张位图释放，暂停状态与原世界引用恢复。

- 原始结果 SHA256：`593D65EA0495D23A5F3309E52B1FD6A6E0099B3D92194D5C33D69E2CB6B562D5`
- helper SHA256：`552C195847AEAF8B16B0EC118D190BB04257F810A7478C8637919C39A6B27015`
- 构建回执：`probe-builds/probe-source/799a6e30de8c485bbb171dd2764e599d/probe-build.json`
- 独立只读复核：通过上述局部边界。

游戏处于暂停，素材离屏挂 Stage，没有运行真实 Part/武器。A/B 顺序执行且共享全局动画队列，因此不能证明取消 goto 的全局时序等价，也不能证明减少整帧成本。原始 `candidateEligible=false`、`globalQueueTimingVerified=false` 和 `performanceEligible=false` 保留。r2 summary 的旧模板第一条误写 “synchronous only/no cross-frame”，本说明纠正其措辞，不改写冻结的运行脚本、回执或原始结果。后续若测试实际宿主候选，必须另行记录。
