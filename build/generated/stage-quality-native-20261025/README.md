# 舞台画质与逐线程 CPU 归因

状态：仅准备隔离诊断，尚未构建或运行。它不是画质降低候选，不满足生产部署资格。

静态自审：Python AST／只读导入通过，准确 85 源哈希核对、Main 正逆变换和描述符标签逆变换通过。只在内存中给已保存线程诊断记录补合成画质字段，验证 1200 帧 schema；错位帧号、LOW 未应用、缺帧、恢复失败、切换时间越界和重复标签均拒绝，边界其他状态变化单列为混杂。这不是一次真实画质运行，也未读或重哈希 SWF 实物。

准确 29AF 探针的 85 文件冻结源为输入，仅 Main 增加既有线程时钟锚和画质观察，并新增 `SceneStageQualityTrial.as`，合计 86 文件。保留 `rcnative`、原四个 `dense-native-N` 窗口各 300 帧、真实 Shift 跑动、六 SMG10、玩家 400 发预期负载、AI、物理、击退、镜头和预绘；实际开火量及运行资格仍按原探针检查，不硬补射击。不得从当前共享 `src` 构建。

窗口依次 HIGH／LOW／LOW／HIGH。切换在原 `caseBegin` 和连续起点之后，观察在原 `now` 之前，逐帧读回实际质量并核验 0–299 顺序。全部 1200 连续间隔、切换及查询长帧保留，不删首帧或尖峰。边界间隔可包含上一个质量模式的呈现。末尾关闭计时后恢复原质量，错误路径也调用清理。

只在自有唯一描述符的 `initialWindow` 添加 `allowLowQuality=true`，namespace 30、direct、ID 与窗口尺寸仍按既有运行器处理，正式 `application.xml` 不改。保存 prepared、加标签前、实际使用三个描述符及差异；删除新增标签必须逐字还原，清理前再核实际描述符未变。当前 Adobe AIR.dll 51.1.3.3 是否接受 namespace 30 的新标签，必须由实际启动及 1200 次 HIGH/LOW 读回验证，不能以官方支持说明代替本机成功。官方说明见 <https://airsdk.dev/docs/building/application-descriptor-files/elements/initialWindow>。

复用 `thread-cpu-native-20261025/thread_cpu.py`、`thread_review.py` 与每三次 owned process 采样一次的原包装；所有导入源码、时钟补丁、原回执、运行库和正式输入均冻结。通过 UTC/getTimer 与 monotonic 交叉核对，只使用完整落在测量段内的线程区间；按 TID＋creation time 匹配，退出/新增身份不补零。每段 CPU 明细、覆盖时间、窗口线程映射和观察耗时保留。枚举不是低成本：旧轮 22 次共约 3.7 秒，不能把本轮墙钟和未观察旧轮直接比较；周期数不换算时间，窗口所属线程不自动命名为游戏主线程或渲染线程。

摘要合并每臂 600 个原始间隔重新计算 mean/median/P95，并保留两对方向、每窗火力、弹体、活动人数、预绘和 CPU 覆盖。窗口焦点、可见性、暂停、尺寸、缩放、帧率等只在段边界和终态读回；若变动，`qualitySensitivityEligible=false`，不包装成纯画质效应。

LOW 还可能改变 `BitmapData.draw`、新弹痕或新块的栅格像素，这些内容会留到最后 HIGH 窗，恢复 Stage.quality 并不恢复历史像素。无像素验收，不许据此降画质部署。即使检查通过，`performanceEligible/performanceAcceptance/visualAcceptance/gameplayAcceptance/deployed` 仍为 false。私有桌面的结果不等于用户桌面呈现；线程 CPU 不提供调用栈、等待类别或 GPU 时间。ABBA 的自然敌人、弹道和预绘负载变化仍需独立审查。

登记、私有桌面、独立存储、4 GiB 提交／2 GiB 物理预检、512 MiB 运行保护和只清理自有进程沿用原流程，完整失败证据保留。没有修改其他模组或正式文件。

根会话审查后执行：`run.py --name stage-quality-native-20261025-r1 --compile-probe --registry-wait 600`。复用构建传原构建目录中与 `compile.log` 相邻的 `--probe-build <probe-build.json>`，不传 evidence 复制件。每轮证据目录必须全新。
