# 瞄准模式（Aim-Look）设计文件 — CS 0.9.8

状态：已实现（源码 `src/SceneAimController.as` + `src/ContinuousSceneMod.as` 接入，2026-11-04）。
本文是设计与执行依据；参数为默认值，均可在模组设置页调节。

## 1. 问题与根因（调查结论）

- 原版单房间 48×25 格（1920×1000px）接近屏幕尺寸，`fe.inter.Camera.setLoc` 走
  `moved=false` 分支：镜头绝对静止，玩家可从房间一头看到另一头。
- ContinuousScene 将整关缝合为远大于屏幕的 Location，`moved=true` 分支每帧把玩家
  锁定在屏幕中心（`vx=-X+screenX/2`，纵向另有 +100px 抬升）。前方视野只剩半个屏幕，
  远程武器有效射程落在屏外盲区，战术与侦察空间被结构性压缩。
- 原版隐藏的 `keyLook`（分号键探头）存在三缺陷：键位反人类（`;`）、推进迟缓
  （`otryv+=0.05`，30fps 下 ~20 帧才推满）、无死区无平滑，鼠标微动即全屏晃荡。
- 可行性核查：射击/拾取全部经 `w.celX=(cam.celX-cam.vx)/scaleV` 逆算世界坐标，平移
  `vx/vy` 天然兼容；`SceneObjectCulling` 视口缓冲 320px、`NativeSceneActivity` 缓冲
  1200px，平滑推移（≤50px/帧）不会触发重绘风暴或剔除闪烁。

## 2. 交互设计

- **触发（默认）**：按住**左 Alt** 视野朝鼠标方向平滑延展，松开平滑回中。
  - Alt/Ctrl 不占用原版任何绑定（`keyXML` 未用）；裸修饰键不能进设置页 keybind
    控件（`SettingsKeybinds.normalize` 明确排除 16/17/18），故内建槽位以滑块选择：
    `0=左Alt（默认）1=左Ctrl 2=停用`。
  - 鼠标侧键：AIR/Flash 运行时不派发 X1/X2 事件，不可行（已从设计移除）。
  - **自定义触发键**：keybind 控件（默认未绑定），支持组合键，单键自动查原版冲突。
- **模式**：长按（默认）/切换（设置项，窗口失焦自动复位；键盘自动重复不会连跳）。
- **手感**：150px 中心死区 → 幂律（^1.4）推进 → 横向上限 700px、纵向 380px（各乘
  幅度系数 50–150%）→ 指数平滑（推进 lerp / 回弹衰减，三档速度）→ 单帧位移硬限
  50px。鼠标靠近角色微调瞄准时画面纹丝不动；推到屏幕边缘时视野延展 ~1400–1600px，
  恢复单房间级远距视野。

## 3. 系统互锁（暂停并复位）

任一条件出现时偏移立即清零、镜头还原创生中心：

| 条件 | 依据 |
|---|---|
| SATS 激活或覆盖层可见 | `w.sats.active \|\| grafon.visSats.visible` |
| PipBuck/暂停/世界过渡 | `w.allStat!=1 \|\| w.t_exit!=0 \|\| w.onPause` |
| 剧情运镜/展示镜头 | `cam.camRun \|\| cam.showOn` |
| 原版探头（分号键） | `w.ctr.keyLook`（避免叠加） |
| 控制台开启 / 窗口失焦 | `w.onConsol` / `Event.DEACTIVATE` |
| 非连续大场景 / 静止镜头 | `!grafon.sceneLarge \|\| !cam.moved` |

世界边界：`vx∈[-maxvx,0]、vy∈[-maxvy,0]` 钳制，地图小于屏幕的轴不平移（无黑边）。
控制器异常只自禁用（`aimFailed` 守卫），绝不拖垮模组入口——与物体剔除同规则。

## 4. 实现要点

- `SceneAimController`（纯模组层，无宿主改动）：ENTER_FRAME 优先级 **-200**，即原生
  `Camera.calc` 重定心之后注入；平移为**每帧瞬态**（原生 calc 下帧重算 vx，天然不累积）。
- 注入顺序：`aim.update` 在 `SceneObjectCulling.update` **之前**——剔除矩形必须跟随
  平移后的实际视口，屏外缓冲 320px > 50px/帧推移，无闪现。
- **瞄准精度**：按"实际生效的平移量"预移 `cam.celX/celY`（`+effX/+effY`），使下帧
  原生 calc 与本帧消费方（射击/拾取）都得到像素精确的屏幕→世界映射；边角钳制时
  eff 取钳后值，映射与画面永不脱节。
- **原生 int 字段**：`Camera.vx/vy/celX/celY` 声明为 int，分数写入被静默截断。控制器
  **写后回读**实际值并以回读值同步 `visual`、`sats.vis` 与 `w.celX/celY`（详见
  shared-knowledge `rendering/facts/camera-int-fields-and-writeback.md`）；回归夹具
  `tests/FakeIntCamera.as` 覆盖该路径。
- 预绘/活动调度：宿主 `sceneEnsure`、`NativeSceneActivity` 均读 `cam.vx`，一帧滞后
  ≤50px，远小于各自余量（预绘按方向分批、活动缓冲 1200px）。
- 偏好持久化：`ContinuousScene.preferences.json` 追加
  `aimEnabled/aimTrigger/aimKeybind/aimToggle/aimDistancePercent/aimSpeed`，
  旧文件缺字段即取默认（向后兼容）。nativeAPI 暴露 `aimStats/aimController`。

## 5. 验证

- 机制断言 `src/tests/SceneAimChecks.as`（假世界确定性测试，30+ 项）：死区/幂律收敛/
  首帧步进钳制/松开归零/方向翻转/世界边界三向钳制/短图轴不平移/七类互锁复位/长按
  与切换/自动重复安全/组合键槽位/裸修饰键槽位/震屏透传/缩放映射/幅度系数/速度档
  收敛对比/统计快照。
- 构建产物与部署回执按 release 门禁流程留档（SHA256 + 备份 + 重启生效）。
- 玩家实机主观验收（视角延展手感、无剔除闪烁、狙击命中）为最终验收项。

## 6. 后续候选（本轮不做）

- 武器倍镜联动（近战×0.5 / 狙击×1.4 幅度系数）——设置结构已留 `distanceScale`。
- 受重击强制回中、屏幕边缘玩家定位引导线。
