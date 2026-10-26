# 消除原生重复坐标写入后仍无收益

2026-10-27。隔离宿主06FC8175，原宿主A796不变。精确字节码审计确认仅Camera.calc
两个world.visual坐标setter加入scrollRect非空时跳过的分支；5770其他方法、1016
类布局、常量池、私有身份、所有非ABC原始素材保持。SATS、sceneTick和镜头数学保持。
详见host-build.json、audit-proof.json、runs-review.json；没有部署。

冻结4b54c43dfa54427ea31ed32c113da409，AIR44664，入图5030毫秒，480间隔/9原检查。
240次候选calc后world位置保持0，所有下一入口与最新帧末状态一致，原生重定位0。
因此这轮确实补上前一原型没有消除坐标写入的限制。

| 条件 | 均值 ms | 中位 ms | P95 ms | 最大 ms |
|---|---:|---:|---:|---:|
| 原生移动 | 33.288 | 32 | 39 | 174 |
| 场景坐标固定的无缓存滚动 | 33.550 | 33 | 40 | 48 |

两对候选分别慢0.417、0.108毫秒。原生174毫秒长间隔未剔除，仍没有收益，停止。
五视角只有一项RGB3超界，alpha0、原生恢复精确；visualAccepted=false。75截图
释放、监听移除、清理通过。2203个EXIT_FRAME回调只记录每个区间最新状态，不叫
物理呈现次数。暂停测试不能作实战或无敌人游玩FPS。

独立verify_runs.py重新检查526正式/13运行库/86冻结源、候选实际输入与完整宿主
语义审计。原始证据knowledge/experiments/evidence/camera-world-scroll-native-20261027-r1。
缓存条件另行测量见相邻native-cached目录，不把不缓存结论泛化为缓存速度结论。
