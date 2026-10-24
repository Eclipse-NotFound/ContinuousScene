# 原生图块批量写入失效通知：仅源码配方

状态：未构建、未运行游戏、未部署。仅补已知缓存通知缺口，不代表分页显示有性能收益；真实战斗无明显收益则不推进部署。

唯一改动是在 `Grafon.scenePreloadRegions()` 的非空 `worldClip` 分支、四层 `copyPixels` 前插入 `++surface.revision;`。同一 surface 每个有效区域写入前递增一次，四层共用该版本号。放在写入前能覆盖部分复制后异常；版本变化可保守多报，不能在像素已变后漏报。原循环、像素调用、环境恢复和异常传播不变。没有新增清理广播、SATS 接口、字段或方法。

来源为 `../motion-direction-rays/source/fe/graph/Grafon.as`，原始 CRLF 字节 SHA256 `75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB`。目标方法切片为第1299–1368行，原SHA `62076B8C4CB76AF3EBCE8AB4994A86D8D91C277EC36DDFA3E627368A2C24F9F0`；变换后 `48A7FE260D46E16C12706BE751EE799001C971CD0E9E5A3DE83F261E74649A2D`。

这是历史81C1源码中的**方法来源**，不是A796全类导出。已保留的81C1→BEFC严格审计，以及BEFC→80CF→ABE2→A796三个方法级审计证明该目标未改；脚本锁定这些回执指纹与链路。准确目标宿主为 `A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7`。未来如获准构建，只能把目标方法留存到准确A796宿主，不得整体导入此历史Grafon，避免撤回正式颜色修复。

`source_transform.py` 的 `extract_target(bytes)`、`transform(method_bytes)`、`reverse(method_bytes)` 只接受准确指纹。直接运行仅在内存核对来源、唯一锚点、非目标字节保持、逐字反向还原和六个错误输入拒绝；输出JSON，不生成AS副本/SWF，不调用工具链，不读取当前安装宿主。

后续最小验证（尚未执行）：

- 已有一部分resident块并缓存其像素后，通过公开 `scenePreload=true; sceneTick()` 进入有效regions分支；原块身份不变，实际覆盖块revision增长，缓存同步后与原生像素一致。最后恢复该开关。
- regions缺失/面积不符走原分支：已有块像素和revision不变，新块按原生生成。
- 多region接缝及gutter、四层非空内容：原像素输出保持，只版本增加；不要要求每个块整批恰好加一。
- 隔离组件故障注入在四层复制中途：异常仍向外传播、原环境按既有逻辑恢复，任何可能已写块的revision已失效。不得在正式实例销毁原图制造故障。

批量重绘与帧间SATS的原生恢复仍属独立问题，本配方不解决、不假称已验证。源码静态通过也不是字节码、类布局、素材保留或性能发布资格。
