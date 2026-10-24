# 原尺寸合图：静止回原图、移动呈现

仅供隔离实验，r1已编译并完成暂停世界的960帧诊断；不是生产或真实战斗资格。

`presentation_transform.transform(source)` 直接接受原始 `SceneRasterPresentation.as` UTF-8 文本，SHA256 必须为 `C0E40368FD8BF6FE1413EC4C8D533C7034B18297AEB35119FBFEC4ADD5D93175`。与前一 motion-only 版本使用逐字相同的七处呈现控制变换，但完全移除 pow2 导入和调用：位图仍按原 `next.width/next.height` 分配，逻辑范围、图层、像素复制、修订记录、copies/rebuilds 和释放路径不变。反向替换必须逐字恢复 C0E4 输入。模块及转换函数均不读写文件，不生成游戏文件或完整源副本。

接口仍为 `update(w, enabled, forcePresentation=false)` 和 public `presented:Boolean`。成功 update 记录 `cam.vx/vy/scaleV`；只有此前已有有效姿态且本次至少一项实际变化，或显式 force 时才显示 atlas。首次非 force 调用仍创建/同步缓存但显示原图；静止时恢复原图而保留缓存。beginFrame 清 presented 但保留姿态，clear、禁用及换图沿原路径释放并清姿态。SATS 原有恢复/早退保持，force 不绕过该路径。

像素检查必须 `update(world, true, true)` 并确认 `presented === true`，防止静止原生显示造成假阳性；计时仍两参数并核对实际呈现标记。仅相邻成功 update 的相机字段变化参与切换，完整变换、缩放与震动资格仍由实验夹具限制。

用户于2026-10-25明确接受继续验证每通道 RGB 最大差不超过 2/255，alpha 必须完全一致，恢复原生仍要求逐像素全等。这是新的视觉容差授权，不改写旧 RGB1 失败结果。同帧 size-compare r1 第四视口旧尺寸和 pow2 都出现 RGB2、alpha0，原生恢复全同；没有证明 pow2 修复误差，因此不继续其额外内存路线。

原尺寸仍有缓存分配、重建和每帧维护成本；此前 pow2 首建348ms、128–256MiB仅属旧变体实测，不能直接当本变体数值或宣称已消除卡顿。开火、长距离跨缓存边界、SATS/效果兼容和真实战斗明显提速仍待验证；功能正常与真实战斗收益是部署前提。

## r1实际结果（2026-10-25）

证据：`knowledge/experiments/evidence/camera-atlas-motion-native-size-20261025-r1`。探针`6BBCE1F973C7D3E15C2294D2235C58FA2C1796AE2DFA210C40A78C171FEDD9EC`，原始结果`0B0027406B222761B4A7DBAF640134B2A4DA8DB20BF19292A944DC0D2BC8D3FD`；冻结源回执位于本目录`probe-builds/probe-source/9a8921b611af4628b78eb11a0ca29a0e/probe-build.json`。正式A796、CS7F1F和其余526输入前后保持；隔离528输入和加载检查通过。

完整960帧连续31134ms。五视口均实际强制呈现，RGB最大差1、alpha0，原生恢复全等；15/15截图释放。八窗预绘等八计数、玩家状态不变。按每模式240原帧合并：

| 模式 | 平均ms | 中位ms | P95ms | 最大ms |
|---|---:|---:|---:|---:|
| native-static | 28.3208 | 26 | 43 | 52 |
| atlas-static | 28.8542 | 27 | 36 | 213 |
| native-moving | 41.05 | 38 | 55 | 228 |
| atlas-moving | 31.5 | 31 | 37 | 45 |

两对移动分别37.1167→31.0417、44.9833→31.9583ms，中位/P95亦同向。八窗实际呈现帧0/0/0/119/120/1/0/0，逐帧姿态模拟全匹配。首次B的252次cell-layer复制/1次重建、213ms长帧全部保留；另一B静止138ms和A移动228ms也保留，不据helper计时0归因GPU/GC。移动B窗口没有复制/重建；首末原生静止也有时间漂移，不能把合并静止差值认作纯维护成本。

独立复核原始JSON的全960帧、显示路径、像素、恢复、加载与记录内指纹；保护钩子拒绝了审查者带指纹计算的读命令，未重试，独立审查不宣称重新散列SWF。实际二进制前后SHA由获准runner核对。

已进入`../camera-atlas-motion-combat-20261025`准备真实冲刺/开火ABBA；暂停120fps结果不等于游戏战斗帧率。Camera的vx/vy为int，但震动和缩放可使世界显示坐标含小数；当前像素仅单位缩放/整数显示条件，旧0.8+分数震动存在大色差，尚不能生产启用所有变换。
