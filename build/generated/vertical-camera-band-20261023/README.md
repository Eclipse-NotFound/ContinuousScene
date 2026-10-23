# 纵向镜头缓冲候选

已于2026-10-24 00:00完成本机部署及实际安装65项复验。基础宿主 **80CF…FD3D** → 当前 **ABE2…2602A**；仅替换 `fe.inter.Camera.calc`，不覆盖 Camera 类、CS 模组或其他宿主方法。全部证据及限制见模组`knowledge/experiments/vertical-motion-20261023.md`。

正常大场景跟随使用屏幕像素半带 `min(160, screenY×0.18)`，并按原脚底锚点 `screenY/2+100`、碰撞身体高度及当前震屏幅度缩小安全带。带内沿用上帧 `ovy`，带外直接跟到最近带边；持续升降不锁镜头。原 X 跟随、地图边界、震屏及随机数调用、SATS、声源中心、鼠标换算和 `sceneTick` 保留。

已有 `ContinuousSceneCarrier.nativeAPI` 的普通动态 Object 保存唯一自有 `verticalCameraState`。首次、camera/loc/缩放/屏幕身份变化、超过半屏的单步位置跳变、退出观察或 camRun 后，在正常跟随分支直接重定位至玩家 Y；不修改玩家或世界坐标。主动观察、观察过渡、camRun、天空、非玩家镜头、无 API、不可容纳安全带等情况不启用缓冲。普通房/不合资格时清除自有状态，释放旧地图引用。无 Camera 字段、方法、计数、定时器或诊断开关。

这里保证碰撞身体不因缓冲额外裁出屏幕；地图原生边界仍优先，不承诺头发、枪口特效等所有美术边缘。无 API 期间采用完整原生跟随；若外部临时移走再原样插回同一个 API，且 camera/loc/scale/screen/位置均未变，不声称识别这种外部事件。当前正式调用链没有这个过程。

源码参照：`../scripts/fe/inter/Camera.as`，SHA256 `4EB7D9B9E96B1CFF61A92A8297DC537CE1D488E051EF1236672F926CEA9A22A2`。构建必须先从 **80CF** 新导出 Camera，并逐字核对 `calc` 与该参照；不把旧整包源码作为宿主来源。`recipe.py` 的反向删除必须恢复全部原语句和方法外文本。

`source/fe/inter/Camera.as`刻意保留原导出空行中的缩进和文件尾空行，作为精确源指纹/反向还原证据，不作格式化。提交前其他手写文件的空白检查通过；此生成文件的空白提示属于已核对的原文保留。

构建已走严格单 body 保留器：`build.py --compile-only` → 核实际导入分支/绑定/寄存器 → 填 `audit.py` 实际 pins → `build.py --resume-compiled`。新导出的原 Camera 源与参照指纹完全一致。导入后的 541 条原生非 debug 指令逐条保持，包括全部原生跳转（链式赋值临时寄存器由 2 搬至 14）；新体 flags 0、scope 4/5、寄存器 15、栈 8，无 activation、异常或 Timer。

原 Camera 全类没有私有 trait；编译器给新增动态 Object 访问生成了两个无实际成员的私有身份。审计仅将新增 namespace set 182 规范化为已存在 set 164 的完整有序内容，移除这两个无用身份；保留原 `compiled.*`，反向校验其余全部 XML 节点和代码字节不变。详见 `namespace-normalization.json` 和 `native-instruction-proof.json`。继承保留器的 nextStep 提示仍提 BEFC，属于旧文案；实际锁定和验证的是 80CF/B922。

最终 `semantic-audit.json` 确认仅 `Camera.calc` 改变，其余 **5770 个方法体、1016 个类和脚本初始化、全部原始素材**保持；无新增字段/方法，Location 光照补丁保留。

| 产物 | SHA256 |
|---|---|
| 候选 `pfe.swf` | `ABE2B65EDF3D0E4E0FA8ECA76A60E577D40E47F20B9ACECEBEC7730849A2602A` |
| 候选 `pfe.xml` | `EE33CE0282C1DFBA7BF7AE03D1E7646383DCCF79EA1252F9792A57344E1208CF` |
| 最终严格审计 | `F8147E6F0E6939E65387F5A15FE9E80322EF925A306096F8816A490F401AE4B1` |

已验证：65项组件（56次实际calc）覆盖带边、上下/小屏/缩放边界、入图与瞬移、观察/camRun退出、无API/普通房回退；实际150px跳跃A/B/A共2160采样帧，跳跃平均49.40/37.87/46.04ms。组件的持续升降是几何覆盖，不冒充真实攀爬玩法。四轮密集战斗共4800完整帧未见持续回退信号，但有自然人口、火力和预绘混杂，不声明战斗提速；另B2未完成失败保留。更深探索与整体近原版目标仍未解决。

`release-qualification.json`绑定全部8组完整证据；`release.py check`已通过524依赖核对，deploy使用同一产物并从实际安装文件完成65/0复验。回执在`state/vertical-camera-band-deployment-20261023.json`，备份为`build/backups/vertical-camera-band-20261024-000000-9ee00a9c/pfe_before_vertical_camera_band.swf`。rollback只允许当前仍是本次ABE2时恢复80CF，不能覆盖他人新宿主。
