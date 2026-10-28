# 构建与运行入口（脚本准备，尚未执行）

离线编译单独预检 2GiB 可用提交/1GiB 物理内存，串行、每次最多 180 秒，运行中低于 512MiB 可用提交则中止。`-Xmx512m` 只限制 Java 堆，不是进程总内存；不启动可见窗口。游戏实测仍保留原 4GiB/2GiB 创建线，未降低。

原 `source-manifest.json`、prepare.py、README 和源码副本保持冻结；本层另由构建回执锁住四个脚本/说明文件。只有 root 安排真实调用，本轮没有编译或启动 AIR。

`build.py --name r1 --registry-wait 300`：共享登记后顺序编译 8 源载体与 86 源探针到 `builds/r1/`。复用 39A 回执中的 Java/mxmlc/airglobal 指纹、原 XML 参数、`-Xmx512m`、SWF32、静态运行库参数；只改源目录、入口及输出路径。输出是新编译，不声称复用 39A 或 rc2 的旧二进制。保留原回执引用、源清单摘要、实际命令、日志和产物摘要，不复制完整历史 JSON。

随后 `run.py --build <本目录绝对路径>/builds/r1/build.json --name camera-activity-range-current-20261028-r1 --registry-wait 300`。只运行 scene，原生跟随四窗 A/B/B/A 各 300 帧。直接复用 rc2 的 options、runtime、静音与登记，只在隔离 runtime 覆盖 CS 和 Motion 两个二进制；宿主仍 4E5F、当前正式依赖含 RCF14A。所有正式文件不变。创建前 4GiB 提交/2GiB 物理和运行中 512MiB 提交中止线保持，静音/预检构造器前失败清 lease，构造器开始后失败保留保守不确定状态。

独立复核：`verify_run.py camera-activity-range-current-20261028-r1`。调用未修改的 rc2 汇总器保留 1200 连续区间、真实运动/火力、40 个完整 30 帧火力窗、缺块/补绘和缓存变化守卫；再检查 1200 个 range 后验、模式/tick/epoch、无可见休眠、每个 B 窗实际 applied 及 oldNearOnlySleeping 阳性、最终恢复。输出核验摘要，运行回执与完整 summary 只保存在既有 evidence/name 下。

继承限制不变：后写入玩家位置/震动/缩放仍可能使本轮失败，不能因下一帧回退而宽免。所有只读扫描、计划、观察器与边界开销计入；A/B 游戏状态会延续，非严格反事实重放。若存在异步预热，只能作完整体验对照。当前 ordinary/scene 参照与本新编译探针不混算因果百分比，成功运行也不自动获得部署资格。
