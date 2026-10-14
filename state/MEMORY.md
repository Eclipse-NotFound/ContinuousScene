# ContinuousScene

## 1. 这个模组是什么
支持无内部房间边界的大场景。镜头、敌人、子弹在同一坐标空间连续运行。原版房间只作测试素材。入口为 ContinuousSceneMod，需要对隔离的游戏宿主做尺寸和绘图适配。

## 2. 用户偏好与协作约定
中文交流。2026-10-14 用户明确暂缓地图编辑，先打通大场景加载与正常运行。当前为开发验证，不部署到正式游戏。

## 3. 当前状态
2026-10-14 v0.1 运行样片完成。192×60 格（7680×2400），400 像素块预绘。完整隔离 AIR 检查 23 项通过，另一次短程生命周期通过。独立 git master；入口 Start-Scene.cmd。正式游戏未部署。

## 4. 正在进行与卡点
功能首轮打通，等待试玩反馈。AGENT_SCOPE.md 新建被工作区保护规则拦截，未写入；沿用根 GOVERNANCE，不绕过。编辑器仍暂缓。

## 5. 已知问题
步行帧间隔中位 33ms、p99 76ms、最慢 117ms，预绘仍有卡顿；瞬移同步补块更慢。格子/实体全场常驻。只测少量敌人和当前尺寸，其他模组、水体/门/SATS/剧情未全面测试。存档可读回大场景，完整破坏地形不跨读档保存。大场景固定原倍率。手动入口已提供，未做人工操作验收。

## 6. 下一步
先依据试玩反馈继续运行性能和原版交互压力检查，再决定更大尺寸、远处实体调度与场景保存扩展；编辑器等待用户恢复该范围。正式部署须另有明确授权。

## 7. 深入了解
- `design/runtime.md`
- `README.md`：试玩、构建、测试命令；工具链只读复用 Sandevistan/build/tools
- `knowledge/experiments/runtime-validation-20261014.md`：范围、失败条件、性能和证据
- `knowledge/experiments/evidence/full-suite/`：最终同一构建指纹的 23 项通过结果
- `build/build.ps1` 完整构建；`-DriverOnly` 仅编驱动；`build/test.ps1` 自动验证（`-Quick` 跳过长走廊）
- AIR ID `remains.continuousscene.dev`；所有测试存储独立，不碰 `%APPDATA%/pfe`
- `state/journal.md`
- 游戏根 `讨论档案/seamless-world-20261014/report.md`
