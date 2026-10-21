---
domain: rendering
type: discoveries
game-version:
  - "1.02"
confidence: medium
verified: false
discovered-by: ContinuousScene
evidence:
  - kind: source-audit
    symbol: "Grafon.sceneSats/sceneApply/sceneEnsureUpcoming/sceneCancelWarm; NativeSceneActivity.update"
    summary: "回读BEFC宿主的已核对Grafon编译来源；仅静态分析与候选文本生成，未编译或运行。"
  - kind: decompiled-game-code
    symbol: "fe.inter.Sats.onoff/getUnits; fe.inter.Camera.calc; fe.World.step; fe.weapon.Bullet.step/run"
    summary: "原版输入时序、暂停后镜头更新与子弹分段命中的参考机制。"
date-updated: 2026-10-21
---

# 跳跃、交战及SATS卡顿：静态接续

后续状态：用户恢复测试和部署后，候选已修正并于2026-10-21安装7D42，发布前199项/安装后60项通过。以下保留暂停实测时的历史静态记录，当前结果以[实测与部署报告](../experiments/sats-viewport-20261021.md)为准；分批截图已因像素差异放弃，战斗近原版目标尚未达成。

## 已确认

用户要求“先不做测试”。本轮没有启动AIR/JVM、编译SWF、执行测试或部署；仅读取、生成候选源码、复查文本差异。正式宿主BEFC、CS0.9.0/7F1F、TDFC7ACD、RC574D与前轮指纹相同。

**SATS截图。** 当前Grafon.sceneSats临时显示所有原生分块及隐藏的WB块，对每个sceneChunks成员各分配sceneSide²位图、分别执行data.draw(this.visual)。开启时显示树遍历次数等于驻留块数，而非屏幕块数；关闭只隐藏visSats，像素留到重开/清图。准确源为build/generated/motion-direction-rays/source/fe/graph/Grafon.as，SHA256 `75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB`。fog-typed/strict-audit记录81C1→BEFC只改Location.lighting，Grafon方法字节保留。

World.step在世界推进及Camera.calc之后才处理keySats，当前战斗帧耗时也会叠加到V响应。Sats.onoff依次drawSats→onSats(true)→getUnits；原生目标搜索仍有独立成本。SATS期间Camera.calc继续处理看远处、缩放、震动，不能只留开启时的一屏。onSats(true)还会隐藏visObjs[2]角色层。

**战斗。** NativeSceneActivity.update将受伤、有目标、流血/中毒记录设为engaged=true，没有恢复false分支；wake同样永久标记。TDFC已部署冻结源build/generated/tdfc-threat/TdfcRuntime.as按lastSeen>=0唤醒，不判断记忆年龄。原版参考Bullet.step/run将高速弹按World.maxdelta=9分段，每段循环loc.units；合图扩大该数组。尚未逐条审计当前宿主Bullet字节，不能将参考阅读称为独立宿主审计。

Grafon.sceneApply每次弹痕遍历驻留块，并为每块创建Rectangle做相交判定。候选仅复用这张临时矩形，不改变顺序、判定、随机数或永久弹痕。

**移动预绘。** sceneApply会对相交的未完成预绘调用sceneCancelWarm，取消作业并销毁输出（判断含额外80像素）。镜头进入缺块时sceneEnsureUpcoming强制完成或同步补绘。预算按移动需求为2–24ms，单个绘制步骤不可中断，不是严格整帧上限。

## 观察到

用户本轮报告跳跃/高速移动轻微卡顿、交战明显卡顿、V延迟。本轮没有新运行观测或性能数字。前轮样本见knowledge/experiments/enemy-speed-20261020.md，不可沿用为本候选验证。

## 推测与候选

走过更多区域可能增大旧SATS截图成本；频繁弹痕取消预绘可能放大交战移动峰值。实际占比未知。没有取消追击、缩减碰撞对象或修改战斗结果。

新增src/patches/SceneSatsViewport.as.inc：视野加8像素模糊边缘、每批不超过1920×1920、一次绘制显示树后分出各块。旧截图像素冻结复用，镜头新露出区域按需补齐；离屏快照摘下，回看复挂，关闭/清图释放。补截图临时恢复原生隐藏的角色层，隐藏SATS自身避免重影；原生/WB/角色可见性都在finally恢复。

build/prepare-sats-viewport.py只能输出源码与来源记录，不能编译/启动/测试/安装。支持sats、impacts、combined分别准备；当前combined位于build/generated/sats-viewport-20261021-combined，源码SHA256 `FF9A70150EEF8259BB8FB857064A46FDA66B24610CF7D528A7ACA688E00E4067`，状态source-only-uncompiled-untested，未接旧整包链。

## 尚未验证

- 未编译，AS3结果、FFDec新增成员/方法影响与运行错误未验。恢复后只能从当前宿主窄范围导入Grafon，核对其余类/方法保留，禁止旧整包回退BEFC或RC接口。
- 分批像素、块缝、WB/RV/LAD、重开/移动/缩放/窗口变化/切图/存读档及SATS目标/费用/队列均未验。新区域在曝光时截图，仍播放的MovieClip可能与按V瞬间的动画相位不同，需检查接缝或角色缺失。
- 驻留数量不变时仍逐个核对视野内entry.sats，避免块替换后被视图键误跳过；清场也重置键。这些只是源码处理，缓存替换/释放的运行覆盖仍待验，不能宣称支持其他模组任意替换块。
- 复用Rectangle没有消除全块扫描；无证据表明战斗已明显改善。还需预绘取消/同步补绘、子弹子步×单位数、历史保活规模及RC离线兼容的实际采样。近原版目标未完成；测试保持暂停。
