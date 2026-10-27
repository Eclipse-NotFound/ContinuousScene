# 原生窗口与上层特效对照：仍无可部署修复

2026-10-27。本批五次游戏运行，正式 A796 / CS0.9.0 及模组组合未改。根目标仍未完成；实验都是暂停模拟、保留 Flash 时间轴的 ENTER_FRAME 区间，不能当作正常战斗或实际呈现帧率。

## 原生绘制窗口

在同一个实例中，保持同一世界与路线，对比原 direct、新 direct、新 auto；新 direct 用来观察换窗口本身的影响。2032×1084、HIGH、1 倍，每类静动各两段，共 1440 区间。所有切换成本保留在连续计时中。

| 条件 | 静止均值 ms | 移动均值 ms | 移动 P95 ms |
|---|---:|---:|---:|
| 原窗口 direct | 23.8333 | 33.7375 | 40 |
| 新窗口 direct | 24.0417 | 34.0375 | 41 |
| 新窗口 auto | 23.5000 | 42.6583 | 51 |

auto 比原 direct 两对慢 8.5000 / 9.3417ms，比新 direct 慢 8.0500 / 9.1917ms，没有采用理由。不能仅凭模式名说明底层硬件如何执行。三个窗口共用完全相同的显示树，五视角各三次软件图往返精确，95 图释放；两个自建窗口等待异步关闭后确认 closed，原 Stage、World.swfStage、根节点顺序、矩阵和可见性恢复。OS 窗口图像尚未验，未作真实玩法验收。

这个有效轮次之前保留两个失败：

- window-switch：首图与新 direct/auto/返回图差 2217 像素、RGB78，零计时。close 的同帧 closed 检查失败，最终自有 AIR 已退出；不能倒改成完整清理通过。
- window-audit：仅做转移的固定预热仍差 2232 像素、RGB255，零计时；差异区域 [731,234,1109,360]，新 direct、auto、返回图互相一致。完整原生/新 direct PNG 已查看；新窗口异步关闭校验通过。
- window-draw-warm：每个目标窗口转移后固定执行一次实际 draw，再强制三次独立精确往返，全部通过后才计时。没有增加条件性重试或放宽门槛。它支持“先实现绘制再核对热态”的验证方法，不证明冷态像素问题已作为产品修复。

## 画质开关无效，拒绝错误分组

native-quality 完成 1440 区间，但所有实际 getter 都为 HIGH；请求 MEDIUM/LOW 没生效，汇总器正确拒绝预期与实际不符。不能称这些分组是不同画质，也不能按其相等图像宣称无损优化。[官方文档](https://airsdk.dev/reference/actionscript/3.0/flash/display/Stage.html#quality)说明桌面 AIR 仅支持 HIGH/BEST。五组图像原样恢复、25 图释放；正式画质未改。本机限制已归档到 shared-knowledge/rendering/facts/desktop-stage-quality-limit.md。

## 保留原生上层效果，仍不足以采用

native-effects-overlay 把原始顺序的下方九层缓存到 GPU；visObjs[4] 起的上方七层继续原生绘制，不换父节点/顺序/坐标，不停止动画。world 始终可见，下方九层和背景按需隐藏，完整恢复检查通过。

| 条件 | 原生 ms | 候选 ms | 变化 |
|---|---:|---:|---:|
| 静止均值 | 22.2542 | 29.7417 | 慢 7.4875ms |
| 移动均值 | 31.8583 | 30.4625 | 快 1.3958ms，约4.4% |
| 移动 P95 | 37 | 37 | 无改善 |

两对移动分别快 0.7000 / 2.0917ms，收益不足，静止明显回退。480 个候选区间没有上层整层重画、没有分配/释放；角色层仍 draw 480 次 / 3584ms，2397 块刷新合计 4979ms（含上传887ms），每区间10.373ms。实际减少了重复工作，仍没有足够的总耗时收益。

13 次独立完整角色层 oracle RGBA 精确，但最终合成图 RGB 最大71–125、alpha0，全部超限；13 次原生恢复精确。完整 native-0/candidate-0 PNG 已实际查看，主体没有大块丢失，不能据此判通过。40 CPU 图、30纹理、260像素图全部释放，157次临时图层可见性写入/恢复平衡，CPU/GPU峰87,650,336 / 68,828,704字节。正式不部署。

## 可核对入口与下一步

五轮独立复核526正式文件、13运行库、86源与全部工具/构建输入。原始失败保留，不能将命令退出或驱动 ok 等同画质/性能通过。

| 目录 camera-…-20261027 | 冻结源 | 探针前8 | AIR |
|---|---|---|---:|
| native-window-switch | 5a929aa9617847c3bf15ef2a95053886 | 694BFE6F | 66232 |
| native-window-audit | 06ccce09e321406886435c7964882eed | 52322E24 | 51180 |
| native-quality | 5c7d344d52d248b1afca487aa9c39195 | 514EE3D4 | 69852 |
| native-window-draw-warm | e2707a708adb43d8954cd7675ed80abe | 796719A7 | 59464 |
| native-effects-overlay | d5aaa840aa86463996214a9f89edd1a3 | 06A9BAB1 | 15376 |

各原始目录在 knowledge/experiments/evidence/ 同名-r1。window-audit/verify_runs.py 核前两轮，其余各目录 verify_run.py 与 run-review.json。全部测试实例已结束，登记最终为空。生成源按编译字节保存，不原地改配方重跑。

另只读核对 A796 对应 pfe.xml（SHA256前8位1D2642C7）：sceneTick 实际只有 sceneEnsure 与 sceneCullSurfaces，没有每帧 setZoom。src/patches/GrafonChunks.as.inc 的旧写法不能作为正式行为。Camera 原生 X/Y/vx/vy 为 int，不能凭小数相机假说直接做“取整优化”。

后续不再重跑原生 auto、无效 MEDIUM/LOW 或仅调整上层缓存边界。继续寻找能减少实际原生场景绘制工作的结构性改动；先核旧场景层与屏外剔除覆盖，任何候选必须在移动、静止、真实AI/弹体及无敌人路线均不回退，RGB2/alpha0、原生功能、RV、SATS、跨区颜色和长期资源检查通过后才部署。当前没有接近原版的证据。
