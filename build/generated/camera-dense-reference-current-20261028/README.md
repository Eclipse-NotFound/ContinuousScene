# 当前普通场景与连续场景真实战斗参照

只复用旧 dense-v2 探针7F1F0B4361D78E2736EE8EC969C9495FB0CB3CD93A1446F38E0FDDDE4805E0F9，不编译、不修改或部署产品。这个7F1F0B是测试探针，不是旧产品CS 7F1F2961。正式宿主4E5F、CS 9A5E、RC2C49、RV638E、Loader2050保持；完整526正式输入与13运行库固定到本目录prepared.json。

目的：在同一当前依赖下判断普通房间真实战斗是否也接近55ms，区分共同运行成本与连续场景增加的成本。普通房间不是原版无模组宿主；两轮都加载当前全部选中模块，原生场景合并设置不同。两轮都有六LMG敌人、玩家ASSR、方向键/Shift原生移动、真实开火与弹体；自然敌人保留，不暂停世界，不逐帧改位置。每轮四段各300连续间隔、两轮都保持原生镜头跟随。耐久敌人、玩家godMode和补弹等继承夹具限制不变。

来源：原回执dense-v2-20261023-normal-r1/probe-build.json摘要1AB690B790CC06F8C5092931C1D10DE1813D78B385DBD2CD722F852B191F67DC，原二进制位于fixture-audit-v2/probe-builds/probe-source/7eecdd4747dc4494b140487385c1e036。先调用未修改的dense/base.verify_probe及原编译参数，再分别核当前依赖；不改历史回执。85个冻结源与39A种子全部相同；对FA2B镜头探针为84共同源相同、Motion不同、FA2B独有镜头helper。复用成功silent配方的固定摘要验证器与silence.py；任何已审核上游文件变动都会拒绝。

FA2B不能直接改normal：其helper硬要求sceneLarge。这里使用原本已实测normal/scene的旧dense探针，普通场景固定房间(2,4)、路线搜索原点(480,119)；期望归一化玩家840→1040、地面120、平台104格。配对必须同时匹配normalizedRoute、nativeRouteHash、selectedCombatCorridorTiles、viewport、fixture和探针摘要。

缓存边界：保留原dense的miss=empty=0并补forced=0；异步预热、切片和常驻变化完整记录，全部间隔保留。没有FA2B强制177块预热。旧scene曾有1块/3切片异步预热，本后继不会伪称两轮都稳定缓存；出现异步预热时仅作完整体验参照，不能作稳态缓存归因。

静音、共享登记、私有桌面、唯一APPID、自有句柄收尾沿成功silent配方。创建前均要求4GiB可用提交/2GiB物理，运行中512MiB提交中止线不变；静音/内存/参数检查在进程构造器前失败时清launching，一旦进入构造器则保留不确定状态。核CPU32、内存优先级5、highQoS和设置/回读无错。静音仅原生Snd配置回读，不宣称全模组声音或SoundMixer已确认。

顺序执行（由主线程负责，均使用现有Python加-B；本子任务不运行AIR）：

1. `verify_reuse.py --prepare`
2. `run.py --name camera-dense-reference-current-20261028-normal-r1 --mode normal --registry-wait 300`
3. `verify_run.py camera-dense-reference-current-20261028-normal-r1`
4. `run.py --name camera-dense-reference-current-20261028-scene-r1 --mode scene --paired-evidence camera-dense-reference-current-20261028-normal-r1 --registry-wait 300`
5. `verify_run.py camera-dense-reference-current-20261028-scene-r1`

原生输入、火力/并发子弹、1200间隔守恒、加载/资源/原始结果/失败回执守卫保留；另精确重算40个30帧火力窗。totalScript是前一帧Stage监听带且只有1199项，RENDER/EXIT_FRAME也仅计事件监听，不等于全渲染/GPU耗时，不按数组索引相减。自然群体、瞄准及普通房间镜头边界不同，配对是体验参照，不能把全部差值归给单一调度器或GPU。
