# v4：已准备，运行前暂缓

2026-10-25，`mouse-world-native-v4-20261025-r1` 在启动预检发现另一个 AIR 实例，立即退出。未编译、未启动本轮 AIR、未投递消息，也没有计时样本。登记号 `f4df579533dd415893ecbf73020092b6`，原始失败记录保留在同名 evidence 目录。

只读核对表明当时运行的是用户正式 `application.xml -nodebug`，PID 30896、创建时间 18:44:56；这只是当时记录，不作为以后关闭或识别进程的依据。用户随后明确选择“保留游戏，先准备候选”。未关闭或操作该实例。

v4 五源完成根与独立审查，直接 Stage getter 的事件前后、Timer 和逐帧 ±1 条件保留；事件派生坐标另行完整记录，不修正 v3 的三像素差异。窄资格仅用于固定指针下世界命中树成本，不证明点击或瞄准兼容。

| 文件 | SHA256 |
|---|---|
| run.py | 562F181DAFA88F567D19D28F3F5BD63A564DB89A4B473080B72949F7F8418F3A |
| probe_patch.py | 7D8902FDBA56176B265791AF0E4AA2FF86EDE7B33A20DFA27042EE2844A906E8 |
| owned_mouse.py | 0F51374C594D2B9A795ECE43FF241EA21592F3C8BA6AC0F84E8385646DE14AF3 |
| SceneWorldMouseProbe.as | 779219D4EFB71F4B68D35B93F26FA703270C2E729E2F8A23002F8035BA64D01B |
| README.md | BA048B85D65AB7C093220DFB1DF97BF849B3A4C5AE817BB2DDCAA5A4128F1757 |

恢复游戏测试时需使用新 run 名并重新登记；旧失败不覆盖。本轮没有性能结果或部署。
