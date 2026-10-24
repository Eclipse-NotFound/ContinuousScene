# 同场同帧核对合图尺寸与色差

pow2-r1曾通过RGB1，但与旧atlas失败轮次的随机内容不同，不能据此断言尺寸修复。本目录只做像素归因，不收性能帧：同一原生场景、同一同步调用内，依次截图原生A→旧atlas→恢复A→补尺寸atlas→恢复A。每次视口只在此序列之前调用Camera.calc，序列内不推进模拟、不让帧；全局时间轴是否有隐式动作仍由两次精确恢复检查约束。

原85源派生87源，允许变更仅Main、原SceneRasterPresentation（C0E4经物理尺寸转换）、新增SceneRasterLegacyPresentation（C0E4仅改类名）、新增tests/SceneCameraRasterTrial。旧合图实例只用于复现，超RGB1记录反例；新合图仍严格RGB1/alpha0，两次原生恢复必须完全一致。原检查的失败记录不改写。

五视口共25张截图，要求全部释放，两个呈现器分别清理；禁止进入旧计时phase。若旧合图在本轮全部也通过，则sizeRemediationObserved=false，记录未复现，不能声称色差修复。即使出现旧失败/新通过，也只是有限视口的尺寸影响证据，不是通用视觉资格或真实战斗提速。

helper SHA FFDA4B21834810416A700F11D12C3B3D85E7D7ED70773E02665EE18C66584DC1；转换与完整来源/输入在每轮冻结收据中。共享登记、私有桌面、唯一AIR存储及内存保护均保留。正式版本不改动。

## r1实际反证

探针B1FE87FE，构建收据probe-builds/probe-source/0a99b22310324239b93edef3b23bf973/probe-build.json。前三视口旧/新均RGB1；第四视口旧/新均有560个不同像素、最大RGB2、alpha0。两次恢复始终精确，玩家状态和场景计数不变；在第四视口按原RGB1标准失败，20张截图全部释放，cleanup通过，未进入计时。两种图与原生的聚合差异相同，不等于额外证明了旧/新整图逐像素相同。

这足以否定“只补尺寸就解决原RGB1门禁”的候选。停止pow2生产推进，不重复随机重跑来挑通过世界。用户随后明确接受RGB2/alpha0继续验证候选，但旧failed不改写；后续使用新版本入口与新门限。新选择仍要求实际战斗明显提速、功能正常才能部署。原尺寸motion-only准备见camera-atlas-motion-native-size-20261025。
