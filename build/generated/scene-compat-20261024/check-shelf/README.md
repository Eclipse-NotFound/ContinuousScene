# checkShelf：只前置 Y 判断的候选设计

日期：2026-10-24。状态：仅静态方案与方法文本，未编译、未运行、未部署。没有修改模板、当前 src、宿主或既有实验。此目录不证明存在性能收益。

## 原件和当前宿主关系

`original.as.inc` 来自本模组冻结导出的 `build/generated/player-step-profile-20261022/original-31fd028e520f4a7eaac0d98d7dde0b4f/scripts/fe/unit/Unit.as:2713–2743`。整份源文件 SHA256：`3E5DC9AF3133ED16F28843CB3F1B9826FF14F1C18459AB75CAB0B325FD59B54F`。这里只规范化换行，不重新反编译。

当前正式宿主的已审谱系为 BEFC → 80CF → ABE2 → A796：分别只变更 Location.lighting、Camera.calc、两个 Grafon 色彩方法；严格审计均保留其余方法，未变更 Unit.checkShelf。依据为本模组下：

- `build/generated/combat-near-native-20261023/logic-profile-audit/fog-last-blocker-production-minimal/semantic-audit.json`。
- `build/generated/vertical-camera-band-20261023/semantic-audit.json`。
- `build/generated/scene-compat-20261024/tint/product/semantic-audit.json`。

本轮没有读取或改写当前宿主大 XML。后续若决定构建，仍须在精确当前宿主中定位方法并审核实际字节码；这里不给未经核对的 ABC namespace/method 编号。

静态校验已通过：原件文本与冻结源提取结果相同（仅统一换行）；候选恰好一次字符串替换，只有第 8 行变化。两个快照各 31 行，SHA256：

- `original.as.inc`：`0F53E569CD95C50D6D0637A4C9CC4C0237CC64E8CCDDF054042187D1054869A4`。
- `candidate.as.inc`：`4CFA477613E295576E88AD2417C71E6844791F57BD9AE333C1E51E790363B1AE`。

## 唯一差异

两个方法文本均为 31 行，只改第 8 行：

```diff
-            if(!_loc4_.invis && _loc4_.shelf && !_loc4_.levit && !(X2 < _loc4_.X1 || X1 > _loc4_.X2) && Y2 + param2 <= _loc4_.Y1 && Y2 + param1 + param2 > _loc4_.Y1)
+            if(Y2 + param2 <= _loc4_.Y1 && Y2 + param1 + param2 > _loc4_.Y1 && !_loc4_.invis && _loc4_.shelf && !_loc4_.levit && !(X2 < _loc4_.X1 || X1 > _loc4_.X2))
```

没有新增局部变量、对象、缓存、索引、计时或空值处理。仍逐项枚举 loc.objs，仍为 O(B)；它不是对约千个 firstObj 链节点建立索引。可能减少的工作仅是：不在本次脚底垂直运动区间内的 Box 不再读取 invis/shelf/levit 与 X 边界。反例是多数 Box 不可见或不能承重时，原条件更早拒绝，候选反而多做加法和 Y 读取；必须由独立实测判断。

## 等价边界

原版 `fe/Obj.as:20,28,30,50–56` 的 scX、massa、坐标为 Number，levit 为 int；`fe/loc/Box.as:22,28,48,68` 的 shelf/fixPlav/invis 为 Boolean、mat 为 int；`fe/Pt.as:17,27` 的 stay 为 Boolean、dy 为 Number。均为普通字段，不是会触发外部逻辑的 getter。对原生有效 Box 数组，这些只读条件交换位置不会改变该次命中判断。

必须保留：

1. `for(_loc3_ in loc.objs)`、按键读取和 `as Box` 均原样。结果是原枚举顺序中的首个命中，不是最近/最高平台。不能改成排序、空间候选、不完整数组或按 in_chain/dead 过滤。
2. `Y2 + param2 <= top`、`Y2 + param1 + param2 > top` 原式原方向。NaN 会使相应比较为 false；不能改为补集排除式。第二式保持 `(Y2 + param1) + param2` 的结合顺序，不能复用第一式的和再加 param1。
3. `!(X2 < box.X1 || X1 > box.X2)` 原样，不能替换成两个非严格比较的与；X 为 NaN 时两者不同。边界接触原本算横向重叠。
4. 命中体逐字保留：shX1/shX2、stayMat/stayPhis/stayOsn、动量和 fixPlav、return 位置全部不变；无命中仅返回 0，不清空旧支撑状态。
5. 不承重静止的 Box（`stay == false`）每次命中都累加 `Unit.dy * Unit.massa / (Unit.massa + Box.massa)`，不使用 param1 代替 dy，不缓存上次结果，不改变除法或加法次序。原有零质量和非有限结果仍保留。
6. 移动、念力、销毁/复活后，每次调用仍重新读当前位置和 flags。Box.setNull 会复活/移动；只按静态类别缓存资格不在本方案内。

不承诺损坏数据的异常文本完全一致：原 loc.objs 项若不能转成 Box，两版本都会解引用 null，但首个报错字段可能由 invis 改为 Y1。本候选不增加跳过 null 的修复，支持域为原生有效 Box 列表；若需要异常属性名也逐字保留，此方案不满足。

## 原调用条件及性能边界

冻结 Unit.step:1817–1823 对较大速度分段调用 run，可能在同帧多次扫 loc.objs。Unit.run:2340 在正常下落、未被前面的地形/斜坡命中且非穿透时调用 checkShelf；levit/plav/isFly 的下落分支不同。run:2422 还覆盖自身 dy 为正而支撑物带动造成净向上的特殊分支。普通自身向上跳跃不直接走这条平台扫描。

checkShelf 命中后的头部空间检查可能拒绝该平台；本方法此前已产生的原有副作用不能因此删除。既有计时没有单独量出 checkShelf，不能将用户纵向卡顿或整条 Unit.run 的全部成本归给本函数。

## 独立 AS 组件验收方案（尚未实现）

采用终止型独立组件进程，明确 baseline/candidate 宿主身份；同一冻结探针分别调用两宿主的真实 `w.gg.checkShelf`，不把方法文本复制进探针充当原生对照。不推进原生帧、不调用整体 animate/physics、不做性能采样、不保存游戏。

选择真实宿主域的玩家和已有 2–3 个 Box，核实例身份；不要调用 Box 构造器来临时造物（会改 land 数量和显示状态）。暂存 loc.objs 的原数组引用，将其替换为受控的真实 Box 列表，只改本表列出的公开字段。每项恢复公共哨兵状态，动量重复项除外；finally 恢复所有 touched 公共玩家/Box 字段和原数组引用、暂停状态。引用按 fixture 标签记录，不能跨两个进程比较对象地址。

冻结 Unit.as:272/274 的 shX1/shX2 是 protected。最薄组件不能动态读写它们，也不能声称完整恢复：静态与后续单方法字节审核证明其计算未动；运行组件只验证公开输出/动量。报告必须注明 `terminalOnly=true`、`protectedStateRestored=false`，组件后直接退出隔离进程，禁止继续游玩/计时/存档。若必须动态验证这两个 protected 字段，需另行设计合法访问桥，不能默默扩大本轮。

共同默认输入：Unit X1=90、X2=110、Y2=100、scX=20、dy=5、massa=2；Box X1=80、X2=120、Y1=105、invis=false、shelf=true、levit=0、stay=true。调用 param1=10、param2=0。记录返回值、stayOsn 标签、stayMat、stayPhis、各 Box.dy/fixPlav 及异常；未命中时核原哨兵不变。NaN 用显式标志比较，不用 NaN===NaN。

| 输入组 | 调用数 | 必须观察 |
|---|---:|---|
| 空数组 | 1 | 返回 0，支撑哨兵不变 |
| 单个正常静止箱体 | 1 | 返回 105，选中它并写原支撑字段，Box 动量不变 |
| 顶面 99、111 | 2 | 分别在运动区间上/下方，均不命中 |
| 顶面 100、110 | 2 | 起点相等命中；终点相等不命中 |
| Box 完全在左、右 | 2 | Y 合格但 X 不重叠，不命中 |
| Box.X2=90、Box.X1=110 | 2 | 两侧恰好接触均命中 |
| invis=true、shelf=false、levit=1 | 3 | 各自拒绝且无命中副作用 |
| 移动 Box：stay=false、massa=3、dy=1、fixPlav=true；连续同样调用两次 | 2 | Box.dy 依次 3、5，fixPlav=false；不能把第二次当重复而跳过 |
| 两箱顶面 104/108；数组交换顺序 | 2 | 分别返回首项顶面及身份，非最近平台规则 |
| 第一箱 invis=true，第二箱合格 | 1 | 选择第二箱，无第一箱动量副作用 |
| 同一箱依次移出 Y、移回、levit=1、levit=0 且 invis=true | 4 | 每次直接读新状态，无帧推进和缓存 |
| Box.Y1、Unit.Y2、param1、param2 分别设 NaN | 4 | Y 条件拒绝；未命中状态保持 |
| Unit.X1=NaN、X2 仍在正常范围 | 1 | 保持原 X 条件的实际命中行为 |
| param1=+Infinity；Box.Y1=+Infinity；Unit.Y2=-Infinity 且 param1=+Infinity | 3 | 第一项可命中有限顶面，后两项拒绝；逐分量如原结果 |
| Y2=-1e16、param1=1e16、param2=1、Box.Y1=0.5 | 1 | 原 end 为 1，必须命中；错误复用 start+param1 会得到 0 而漏撞 |
| param2=5、param1=10、顶面 107 | 1 | 支撑物位移参与原垂直区间，命中仍用真实 dy 计算动量 |

合计 32 次直接调用；不会把这些受控方法输入称为真实跳跃、物理或帧率验收。只有组件等价后才考虑独立真实下落/跳跃和密集战斗样本；必须记录实际 checkShelf 调用覆盖，若成本很小就停止此方向，不为凑收益扩大机制改动。
