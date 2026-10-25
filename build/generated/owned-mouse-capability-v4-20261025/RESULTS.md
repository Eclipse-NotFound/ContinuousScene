# 自有私有桌面鼠标命中能力：v4 实测结果

2026-10-25。**能力通过，非性能结果、非真实游戏验收，未部署。** 运行 `cbbb25c5f75940dba64c40358efc287c` 的 runner 判定 `capabilityPassed=true`、`threeTargetsConfirmed=true`，自有 AIR 以0退出。它证明本机该指纹运行库下，给新建自有内容窗口定向投递三条 `WM_MOUSEMOVE`，能产生真实 AIR 鼠标事件、正确命中三个 Sprite，并更新后续 Timer 所读的真实 Stage 鼠标坐标。

本报告只新增结果说明，没有改任何冻结源码、旧结果、正式文件或全局设置，也没有重新启动游戏/编译。README中继承的“尚未执行”文字属于准备阶段历史，本次实际状态以此报告和原始结果为准。

## 本轮证据及输入边界

- 主证据：[runner-result.json](runs/cbbb25c5f75940dba64c40358efc287c/runner-result.json)、[air-result.json](runs/cbbb25c5f75940dba64c40358efc287c/air-result.json)、[air-events.json](runs/cbbb25c5f75940dba64c40358efc287c/air-events.json)、[air-ready.json](runs/cbbb25c5f75940dba64c40358efc287c/air-ready.json)。
- 构建证据：[compile-receipt.json](build/compile-receipt.json)：编译exit0，输出3344字节，36项编译输入检查未变，源码与配置未变；构建器没有启动AIR。
- 独立应用ID `com.remains.ownedmouse.cbbb25c5f75940dba64c40358efc287c`；登记ID `1a8323994717412dbca1ea98fdc66d4c`。仅此应用的独立存储与唯一描述符。
- 原自有AIR PID34600，创建FILETIME `134373954898622004`，私有桌面 `RemainsTest-da6db81de7e54bdab8477277f078f4f6`。选中的唯一合格内容窗口为 `ApolloRuntimeContentWindow`，HWND20256258、窗口线程48372、客户区640×480、标题为完整唯一应用ID。枚举也看到了该PID的输入法辅助窗口，但没有向它们投递。
- 三次投递前均重验相同原进程/创建时间/桌面/描述符身份；每步 `attemptCount=1`，同一HWND、消息512、`wParam=0`，只包含客户区坐标，没有按钮按下。没有重试、广播、子窗口盲试、全局光标移动、激活、切换桌面或Ghost。
- 描述符 `direct`、仅私有桌面窗口可见；Stage为NO_SCALE/TOP_LEFT。继承v3的一次自身窗口尺寸调整保留：首个Timer仍可见624×441，ready及全部三次输入/事件/后续读回已是640×480。未修改系统DPI。

## 逐事件交叉核验

| 目标 | 投递客户区坐标 | 事件序号／应用时间ms | 后续Timer序号／时间ms | 事件后间隔ms |
|---|---|---|---|---:|
| target0 | 90,230 | 1／3378 | 4／3445 | 67 |
| target1 | 290,230 | 2／3630 | 6／3690 | 60 |
| target2 | 490,230 | 3／3790 | 7／3847 | 57 |

三条事件均为运行时 `mouseMove`，`buttonDown=false`。每条 `event.stageX/Y`、事件处理器内的 `stage.mouseX/Y`、事件之后Timer的 `stage.mouseX/Y` 均与对应投递坐标**完全相同**，并非仅在±1容差内。路径均是准确目标Sprite → `OwnedMouseCapability`文档根身份 → Stage，`pathReachedStage=true`。事件原件与runner逐步确认对象相等，后续Timer序号及应用时刻均晚于相应事件，没有拿旧Timer充当后验读回。

`PostMessageW` 的3次成功返回只是入队证据；能力通过另依赖上述3个真实事件与3个独立后续Timer，不能只凭消息API返回成功。AS原始结果保留 `capabilityPassed=null`；最终能力判定由runner核全链后写为true，未回填原始AS结论。

## 清理、指纹与复审范围

原始记录为 `runner-finish:runner-complete`，AIR错误数组为空、`eventSeq=3`、`timerSeq=7`；runner清理记录 `exitCode=0`、`ownedHandlesClosed=true`、`descriptorRemoved=true`。stdout/stderr均0字节。独立存储和结果文件保留，没有递归删除；未复用旧PID或读取真实pfe存储。

启动提交余量26,058,301,440字节，超过4GiB预检；三次消息前仍约25.94GB，运行保护线512MiB。运行冻结22项（夹具、源/配置/构建回执、运行产物副本、既有工具、adl64及所用runtime文件），最终 `inputChanges=[]`。这不是正式游戏526项部署门禁；此独立夹具没有加载游戏或模组。

本次复审重新核了源文件、配置、JSON回执/原始结果指纹及事件断言。原计划包含自有SWF二进制的独立SHA重读，被保护钩子以 `binary-swf-use-release-pipeline` 拦下，整条调用未执行；按主任务要求未重试、未换通道。下列产物二进制指纹来自成功构建回执和实际runner前后检查的一致记录，**本次报告复审没有独立重读SWF或全部运行库字节**。后续真实游戏接入前由主任务按精确授权复验需要的二进制。

| 文件／证据 | SHA256 |
|---|---|
| runner-result.json | `21CD0CC0B61D39FE499C7E545CB415460F6DA6CC5D1C528642E582340EE94B84` |
| air-result.json | `6117CB2EC5A0B977C690D1A564C47BBAA039F8237402212C34EFD7EC2FDF1B26` |
| air-events.json | `CA6BF1D70A82EF14ABD24A4C6D8534CAC8B71E593DB439CD892160E446BAF1FA` |
| air-ready.json | `8561D3870C1D75C8DDFC7165567BC7BAD771F94D6E244926A60A374873B3E25B` |
| compile-receipt.json | `39DC2F7F138B3AF2E66C147FA00CB384BE7C280CD0F0570D548F353684296941` |
| src/OwnedMouseCapability.as | `AD18C31F72E28F2F7CE317FD539929EA908B280F347461541F9FEFA99D45694A` |
| compile.xml | `B5567A9EAFEF822DDE0B98C3F1F06821F837CC0827105990D528E91AB4A46A90` |
| run.py | `2C16D90AC24834BE291FDBF60D867933A64CCDA072383B2CBF93D8DDBE8E67F4` |
| build.py | `CDDF6FCE2706E2B627EE95A35135853A31DD5BA7537D5768FA04B09CE40A9229` |
| 构建／运行副本产物（回执记录） | `4C4996DB53267E1364A4B12CE095F4710312773CC414A41CA6B01790ADCF507C` |
| 实际独立描述符（原文保留于runner结果） | `B2B09583CA93CB170F3F3B6435B28C7947829C797DEBC668730C4DE229EF955D` |
| adl64（runner记录） | `D851EB9E68D38ABD335916DD91E08DE3F1660945B49F382691A188ADC7C8C295` |
| Adobe AIR.dll（runner记录） | `FC1586A74045DF4A31548A3CF0820E01558DB033C2237F81ABC4731BADC8AF01` |

## 前三轮失败保持原结论

| 轮次／run | 实际情况 | 原runner结果SHA256 |
|---|---|---|
| v1 `e470354f115e418c8b1aedb8f1e26300` | 修改时间轴文档根name报#2078；0消息，0事件，exit2；句柄关闭和描述符删除成功。 | `396B4EE46DE7EFA83B5BB0508F424879E76D3D5A594BF99AD06B2F90520DCF50` |
| v2 `b845b2ef08624e3a8e3edeb63ecaa316` | Stage／客户区为624×441，未满足640×480；ready超时，0消息，0事件；受控finish后exit0仍判失败。 | `49226A235AFF1BBF67721D612D329F22BE1FAAFC58BA93854B32F56F42712B5D` |
| v3 `b019bcb56784428a8269041109035da4` | 只投递1条，target0及90,230坐标正确；写观察文件报#3012、exit2。最后Timer3428ms早于事件3497ms，没有完整后Timer证明，失败保留。 | `9E79C58B744D3ABD28A75A957FC941EAF28E828D0F34023AD6C5758731E94449` |

三轮原 `capabilityPassed=false`、`inputChanges=[]`，都已关闭自有句柄并删除独立描述符。v4相对v3的源码差异只包含版本号、AS单调编号不可变 `events-编号.json` 观察文件，以及Python读取最高已完成编号/720文件上限；不是扩大输入范围、增加消息重试或换另一种控制通道。v1/v2修正与v3失败原件未覆盖。

## 可用结论与未覆盖范围

可以继续准备准确新建游戏实例中的少量定向鼠标输入验证；不能直接把此结果当真实游戏已命中世界、真实鼠标设备行为等价，或用户桌面显示等价。尚未测游戏的GUI覆盖、鼠标捕获/菜单、视口和DPI映射、连续移动消息负担以及对真实瞄准/射击的影响。

旧mousetree阴性试验中Stage鼠标始终(0,0)，因此没有充分排除指针位于世界中心时的底层命中开销；本轮只补上建立该条件所需的输入能力，不是新的ABBA性能对照，没有FPS、耗时收益或部署资格。是否值得做游戏内单独ABBA，还须先取得游戏场景中实际坐标和真实目标路径阳性，并保持两臂完全相同的消息量与原生战斗负载。
