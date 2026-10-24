# 独立 flash.sampler 能力探针

仅验证本机实际 `adl64.exe` / `runtimes/air/win64` 能否在 `debug=false`、`optimize=true` 的独立SWF中返回真实CPU Sample和带 `knownHotLoop` 名称的调用栈。没有游戏类、模组loader、替代宿主或性能优化；不修改mm.cfg、PreloadSwf及任何全局配置。

官方说明区分“存在API”与“可用于采样”：

- [Adobe flash.sampler](https://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/flash/sampler/package.html)标注采样接口为debugger版本能力。
- [Sample示例](https://help.adobe.com/en_US/FlashPlatform/reference/actionscript/3/flash/sampler/Sample.html)将NewObjectSample、DeleteObjectSample与普通CPU Sample分别统计。
- [HARMAN ADL](https://airsdk.dev/docs/building/air-debug-launcher)说明AIR自身支持调试，无需独立debug runtime；`-nodebug`会关闭调试支持。本次命令不加该选项，但这仍不证明采样能力成立，必须看实际样本。

先无采样预热命名方法20ms，随后clear→start→约200ms真实算术循环→pause→遍历样本→stop→保存退出。保留已执行批次/迭代数/校验值、真实耗时、Sample/New/Delete计数、原始首末微秒时间及有限数量的调用栈。不触发强制GC，不要求分配/释放样本非零。只有真实普通CPU样本、命名栈和knownHotLoop阳性全部出现才支持；零样本/API空操作/仅分配样本/仅匿名栈均为unsupported，不能当通过。循环遇系统调度可超过请求时长，原值保留，不把它当性能结果。

运行器新建唯一 `runs/<name>-<uuid>/`，冻结源码、工具链/运行时散列、编译配置和日志、应用描述与运行输入。复用motion-test的登记、资源查询和HiddenProcess；不调用prepare/run_owned，不触碰其共享runtime目录。唯一AIR ID对应独立Local Store，结果复制回本轮目录。game登记同时覆盖编译与运行，JVM `-Xmx512m`；启动前4GiB可提交/2GiB物理、运行512MiB可提交保护。仅停止自身登记的编译或AIR进程，私有桌面退出后关闭；无前台回退。失败原件和独立存储均保留，不自动删除。

根审核后执行（当前仅准备，未编译/运行）：

```powershell
& 'C:/Users/hello/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -B 'mods/ContinuousScene/build/generated/scene-compat-20261024/sampler-capability/run.py' --name sampler-capability-r1 --duration-ms 200 --registry-wait 600
```

`--compile-only`只验证编译，永远不授予采样能力资格。无等待时预计数秒至半分钟构建/启动；热点约200ms，AIR上限45秒，编译上限120秒。支持结果只适用于此SWF与该ADL配置，不证明正式debug=false游戏的全部方法可命名、采样无开销、能观察渲染线程或可直接解释CPU占比。下一阶段需另行设计，不在本探针内扩展。
