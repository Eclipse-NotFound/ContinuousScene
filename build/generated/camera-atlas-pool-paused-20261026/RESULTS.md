# r1入口失败，无性能样本

冻结1599e384e33d4225b3c8a9d02a115185已编译，但旧战斗探针init禁止presentationCheck；新增phase97尚未执行就抛出`Motion atlas requires four-window real native-input scene combat`。原stderr.log第23行确认，progress停initialized、无世界/玩家。600秒所有者超时后按既有finally只停止自有AIR54020、保存私有存储并释放登记；无其他AIR或内存中止。

没有进入场景，没有像素或性能结果。正式输入、旧源和失败记录保留。下一版仅把战斗专用init门控限定为非presentationCheck调用，独立phase97诊断仍走其原有世界/视口/像素/清理检查。不得据这轮推断缓存池性能。
