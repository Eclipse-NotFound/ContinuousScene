# 同实例 A/B 诊断宿主：Python 直接编辑 ABC

**当前已完成双基线只读解析与完整 `--check-only`，尚未生成 SWF 或进行游戏运行验证。** 本目录的 `pfe.swf` 即使构建成功，也只能用于隔离诊断，不能部署。正式 F15 仍没有稳定性能收益的验收结论。

该入口锁定游戏根目录当前宿主 `4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75`，同时只读 A796 备份以独立验证基线演变。它不读取 92 MB XML，不启动 Java/FFDec/AIR，不写原 paired 配方或正式游戏文件。回执标明 `method: python-direct-abc`、`xmlAudit: false`、`ffdecUsed: false`，不能当作既有 XML/FFDec 审计通过。

最初锁 A796 的 `--check-only` 实际在 `Installed A796 host changed` 检查停止，尚未解析、没有产物。原因是另一授权任务已部署 CS0.9.1 与 4E5F；本次在未产物的新目录适配该精确版本，不放宽为任意宿主。部署回执为 `state/alicorn-alert-deployment-20261028.json`，A796 备份为 `build/backups/alicorn-20261028-121734-7ee3b24f/pfe.swf`；两者及部署审计都硬锁指纹。

## 范围与保留检查

`raw_abc.py` 解析 ABC 46.16 的常量池、方法签名、metadata、instance/class/script traits、方法体与异常表，保存原始字节范围。它是定位与保留校验器，不是完整 AVM2 验证器。未知版本、未知种类、越界索引和不完整数据均停止。

主 ABC 仅做五处诊断编辑：字符串池计数增加 2，追加 8173/8174；名称池计数增加 2，追加公开 QName 9717/9718；替换 method 3253 的方法体。新索引取当前池尾，同时硬锁本次全部实际池计数（字符串 8173、名称 9717、namespace-set 185），不接受任意版本。代码长 205→493，寄存器 9→17、栈上限 6→8；作用域深度及无异常/无 activation traits 的尾部保持。原 51 字节表达式保持；274 字节 F15 缓存表达式只迁移缓存属性 QName 9705→9717，其余指令保持。回执明确 F15 历史基线为 A796，并复原其 428 字节方法核对原 F15 stage-proof，不能称 F15 原本基于 4E5F。

A796→4E5F 的独立核对先验证仅 UnitAlicorn 的 budilo/telepat/alarma/setNull/control 五体变化，旧常量条目、其他 5766 体和 1016 类字节保持；新增 12 字符串、2 namespace-set、12 名称的实际字节与指纹严格匹配。对应五个 method_info 添加调试名，control 的 NEED_ACTIVATION 位还从 0 变为 2，参数、返回及默认值保持；每对 method_info 原始 hex 单独硬锁，不泛化忽略 flags。再反向还原五体、这五条 method_info 及追加常量，要求整个主 ABC 逐字恢复 A796，第二 ABC 及其他原始 tag 也逐字相同。Grafon 3253 的 205 字节 SHA256 保持 BF4AF7FF4B66C3C999EF16A7293A090CB12A6B66C4B7F680620E5F4F241DC934。诊断产物基于 4E5F，逐体确认保留当前五个天角兽方法和全部 method_info；`baselineEvolution` 与 `currentAlicornMethodsPreserved` 明确记录此事。

适配中的第一次完整 `--check-only` 因原先断言全部 method_info 字节不变而停止；随后只读定位出上述五条精确差异，改为严格匹配并反向恢复这些字节。该失败无产物，不能计为检查通过。

构建从已冻结 paired `audit.py` 精确抽取四个算法函数，通过 RawABC 适配其 `prior.original()`；不导入原审计模块及 XML 依赖链。原 `native-crop-audit.py` 只抽取已有操作码表与 `decode()`，提供算法所需指令解码。两个来源文件及 F15 stage-proof 都有硬指纹，变化即停止。

检查实际类/方法身份、Array/String/Math/max/分隔符、公开命名空间和数组动态查找绑定，并记录原/新方法用到的全部名称绑定。所有旧常量池原始条目保持；反向应用五处编辑必须逐字恢复完整原 ABC。随后逐一比对其余 5770 个完整方法体和 1016 个类的 instance/static 字节与方法签名。其他 ABC、所有非目标 tag 的原始 header/payload、帧头和素材均原样保留；压缩 SWF 的整体 zlib 字节流允许重新压缩。

输出再次读回，目标 ABC 必须等于已审计字节，其他原始 tag 必须逐字相等。`build.json` 最后写入；已有输出或部分失败产物不覆盖。没有完整 build 回执时，留下的 SWF 不算成功产物。

## 资源边界

只在 Windows 执行。开始前用 GetPerformanceInfo 核对系统可用提交内存至少 768 MiB；为当前 Python 单进程建立独立 Job Object，将其提交内存限制为 512 MiB，读取实际限制与峰值，并记录阶段私有内存。不能加入自己的限制组时直接失败，不绕过原有进程保护。不创建子进程，不调整任何其他进程或系统资源策略。

此门槛仅用于本次约 15 MB SWF 的离线字节构建，不改变既有 4 GiB 游戏启动保护或运行中止线。SWF 使用内存视图保存 tag 范围，压缩输出分块写入；未建立大 XML 对象树。实际峰值仍需首次执行回执证明。

## 执行

使用本机已有 Python；下面 `python` 可替换为已探测的解释器绝对路径。请保留 `-B`，不要使用 `-O`。

```powershell
python -B "D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene/build/generated/camera-environment-paired-binary-20261028/build.py" --check-only
python -B "D:/Program Files/Steam/steamapps/common/Remains/mods/ContinuousScene/build/generated/camera-environment-paired-binary-20261028/build.py" --build
```

`--check-only` 只在内存中解析、生成与反向审计，输出简短结果，不写文件。`--build` 执行同样检查后，在本目录独占创建 `pfe.swf`、`audit-proof.json`、`build.json`。两种模式均没有注册或启动游戏，后续实测仍走共享测试登记与原有游戏保护。旧 paired 的 `run.py` 尚未接入本目录，不能复制回执到旧配方冒充其构建；后续运行接入需显式核验该构建方法与来源。

## 格式依据与尚未验证

2026-10-28 已浏览 Adobe 主源：[ABC 46.16 格式](https://github.com/adobe/avmplus/blob/master/doc/abcFormat-46-16.txt)；[AbcParser.cpp](https://github.com/adobe/avmplus/blob/master/core/AbcParser.cpp)。格式文档说明自身并不完整，因此 TypeName 的前向引用、单参数及循环限制，MultinameLA，以及方法体异常表与 traits 的读取顺序同时参照解析器。

已实际只读解析 A796 备份和当前 4E5F，自有 Job 限制生效，双宿主解析峰值 64,626,688 字节；确认上述五体与池计数、镜头目标代码保持。随后完整 `--check-only` 通过，检查峰值 74,002,432 字节（约 70.6 MiB），结束时私有内存 57,569,280 字节。诊断 ABC 的 SHA256 为 CA3AD259C9AC5AE0E8CB5BA64D71855F877D06CA304FECFA7E69E40127423EAE；仅内存中候选，不是 SWF 文件指纹。完整 A796 逆向恢复、当前 4E5F 逆向恢复、其余 5770 体/1016 类、五个天角兽方法保持及 F15 历史方法复原均通过，`wroteArtifacts=false`。SWF 写入和压缩后读回仍未执行。

待核对：实际构建峰值；实际 SWF 载入及选择器两臂的运行语义；旧诊断探针与 CS0.9.1 天角兽接口的兼容性（由后继运行接入核实）。原 paired 的边界分段统计归因问题也仍需在后继运行配方处理。本目录只解决宿主离线构建的 XML 内存成本，不证明镜头提速。
