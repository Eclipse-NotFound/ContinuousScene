from pathlib import Path
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2]
memory=MOD/'state/MEMORY.md';journal=MOD/'state/journal.md'
archive=MOD/'state/MEMORY-history-20261027-before-live-parking.md'
assert not archive.exists(),'Preserve previous memory milestone'
prior=memory.read_bytes();archive.write_bytes(prior)
s=prior.decode('utf-8-sig').replace('\r\n','\n')
a=s.index('## 4. ');b=s.index('## 5. ',a)
s=s[:a]+'''## 4. 最新实测（2026-10-27 实际水平镜头与交战）

本批前HEAD73f4fa3，旧快照MEMORY-history-20261027-before-live-parking.md。七目录、一次编译失败/八次AIR，正式未改；总报告build/generated/camera-live-parking-range-20261027/RESULTS.md。

- 暂停摘树7%线索进入真实战斗后未得到明显提速。完整窗口均原生输入跑动、六SMG射手/玩家assr、20×60连续区间，2032×1084/zoom1、LAD/RV/WB关闭；不同轮随机对象不同，只各轮内比较。
- window e509fcf4/74E83D09/AIR59916：1327根，最多1086暂存；原生47.258→候选49.658ms，管理0.183/5.875ms，平均慢约5.1%。单视角软件像素精确、原生Location.remObj不复活、清理通过。
- math e5087010/100CC091/AIR61480：1200区间47.443→51.292ms，管理4.182ms，仍慢；终结式新旧坐标审计失败，未保存最大差，不归因于舍入。像素/移除未执行，根恢复通过。此路线停止。
- range 9d760a10/389A5495/AIR21036：82组、活动48–51组/最多840图像，管理降至0.913ms；49.292→48.232ms仅约2.15%，6对较快/4对较慢，P95 69→64，最大138→151。软件像素0差/原生Box移除不复活/清理通过；收益不足，不部署，不继续盲目细调屏外管理。
- range实际玩家400/敌人885开火帧，每窗口相机X跨度206–276px；独立movement_audit确认三完整轮实际水平相机/角色位移，所有Y相机固定。不是无敌人/跳跃纵移/RV/SATS/完整原版基准验收。report.nativeInputMotion.measurement为空占位，实际记录在每窗口nativeInputMotion。
- 保留失败：首live-parking a8a87358编译try/finally返回错误；return 2668ea6a/2EB7 r1在index13/age40后监控347s/1445s空档超时，无最终结果/清理证明；r2晚显示窗口后allStat2，0暂存，清理通过。早显示窗口后成功轮无焦点事件；失焦因果仅有源码支持，不是失败轮事件实证。
- math r1 AIR46488预热phase3/age259、候选未开始，可用提交11.75GB→5MB触发原保护，只停止自有测试；无最终清理证明。后余量恢复到17.8GB才用同冻结SWF复测。
- groups da3a1467/177070F8/AIR61324与safe-groups 5a31a6a2/38741C23/AIR69812分别读取玩家不存在的公开lurkBox/lurk而失败；各1原生窗口、0暂存、清理通过。前述对旧代码的字段解释错误，不能再猜玩家有这些字段。range仅用已确认X/Y/teleObj，保留玩家1024px周边和镜头提前区。
- window/range检查是计时后单视角Stage软件像素，3图+边界探针释放；未保存PNG/目视窗口，不是全路线GPU呈现。Location.remObj验证不是全部伤害死亡/门/藏身/拾取路径。
- 独立审查：window/review_batch、math/review_batch、groups/review_runs、range/movement_audit；526正式/13运行库/86源闭包和完整区间守恒通过。具体失败保持失败；初次超时与内存中止不补造清理成功。
- 本批新增保护拒绝：联合rg读取UnitPlayer.as与SceneObjectCulling.as的lurk字段被PreToolUse拦截；未换路径/工具重试。后继按已运行的数据范围完成候选。先前拒绝边界继续。

'''+s[b:]
a=s.index('## 6. ');b=s.index('## 7. ',a)
s=s[:a]+'''## 6. 下一步（保持活动）

1. 目标仍未解决。暂停摘树7%不能当实战收益；逐根暂存更慢，区域暂存总收益约2%且混合，停止把屏外管理当主要修复。转向屏内绘制，具体新机制先核证据，再做独立候选；不能复活旧wrapper/actor缓存失败路线。
2. 补真正原版模式、无敌人和纵向镜头基准。当前2032×1084/zoom1接近1920×1000单房尺寸，原版对照须核实际镜头位移而非按键请求；旧未mainMenuOff的原版基准无效。当前完整实测全部水平相机，不能称跳跃问题已验证。
3. 任何可部署方案还须明显实战收益、无回退、像素RGB2/alpha0、原生门/藏身/念力/死亡/拾取、RV/SATS/跨区颜色及长期资源通过。range滤镜外延取整组收集边界，移除外侧节点后内部强滤镜成为边界、动态滤镜扩大尚未保证；1024px提前区不是通用正确性证明。

'''+s[b:]
marker='## 7. 接续入口\n\n'
assert s.count(marker)==1
s=s.replace(marker,marker+'''- 本批七目录camera-live-parking{,-return,-window,-math,-groups,-safe-groups,-range}-20261027。range/RESULTS.md总报告，range/movement_audit.py核实际水平位移；groups/review_runs.py可核失败的完整1200区间，math/review_batch.py可核内存中止。已运行配方全部冻结；后继新目录。
- 本批前快照MEMORY-history-20261027-before-live-parking.md。没有新部署。共同86源来自原29AF种子，仅驱动和测试helper改变；不触碰正式CS编辑器或SceneAlicornAlerts候选。无新共享事实/技能修改。

''',1)
memory.write_text(s,'utf-8')
old=journal.read_bytes();bom=b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b'';body=old[len(bom):]
sep=b'\r\n' if body.startswith('# 开发日志\r\n'.encode()) else b'\n'
head='# 开发日志'.encode()+sep+sep;assert body.startswith(head)
entry='''## 2026-10-27 屏外暂存进入真实镜头战斗，收益仍不足，未部署

- 新增七目录，一次编译失败/八次AIR。window完成20×60区间，47.258→49.658ms，逐根管理5.875ms使平均更慢；math管理降4.182ms仍慢至51.292且坐标审计失败。range按82组管理降0.913ms，总帧49.292→48.232仅约2.15%，四对反向、最大帧更差，不部署。
- window/range末尾单视角软件像素精确、Location.remObj不复活、根/窗口清理通过。range玩家400/敌人885开火帧；相机每窗X跨度206–276，Y固定。不能称无敌人、跳跃或完整交互/RV验收。
- 首编译返回错误、return监控长空档超时/晚显窗口后allStat2、math预热内存中止、groups/safe-groups读取不存在lurkBox/lurk均原样保留。后者改为玩家/镜头近区保留，不能再猜公开字段。保护拒绝一次联合原版UnitPlayer与旧辅助类读取，未换路重试。
- 526正式/13运行库/86源与时间守恒独立核验；原始证据同名-rN，完整报告range/RESULTS.md，旧快照MEMORY-history-20261027-before-live-parking.md。他人SceneRenderChecks不动。目标继续，下一步转屏内绘制并补有效原版/纵移/无敌人基准。

'''.replace('\n',sep.decode()).encode()
new=bom+head+entry+body[len(head):];assert new.endswith(body[len(head):]);journal.write_bytes(new)
print('Saved live-parking milestone; goal remains active, no release changed')
