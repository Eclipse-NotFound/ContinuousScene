"""Archive the previous long snapshot, then save this measured stopping point."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;MOD=HERE.parents[2]
BODY='''## 4. 当前实测停点（2026-10-27）

本轮7次隔离运行，正式文件未变；完整world绘制终于出现**固定画面上限收益**，尚未成为合格产品。

- wholeworld初轮25f57170：立即停止22个显式时间轴，预备后24个轴仍变帧；65图释放/0计时/恢复失败。late 99c35ff8：延后停止，遍历空节点，65图释放/0计时/清理通过。nullslots f22d6e66：7444节点/1670多帧，本轮空槽0；24个isPlaying=false的osn/Bloodwing子轴仍变化；7纹理/8临时图/65像素图释放，恢复失败。旧失败均保留，未证明空槽根因。
- observed 3c3ad63c：8间隔实看帧变化，停止47（24隐式），无变化；首视角92738像素差异，604像素RGB≥3、最大112/alpha0/精确恢复，0计时。80像素图/8临时图/7纹理释放。已看完整PNG，发光边缘颜色差异，具体混合原因未证实。
- cost 666d6fb8：明确允许画面不合格的归因计时（visualAccepted=false，**不放宽RGB2部署门槛**），但两个pfe_fla::bloat_bulk_896在下一间隔从55→3并重新播放。源已核frame55 gotoAndPlay(2)、frame1随机gotoAndPlay。0计时，47中45恢复，外部改动的2个未覆盖，恢复失败保留。
- **settle 08eb4372完整960/9**：固定一次已知帧脚本消化＋下一间隔核验；实际drain0，分支重停没有得到动态验证。固定43播放者（25隐式）；7纹理22,626,944字节，整个2392×1444区域预先捕获。原生静止11.229/移动29.658ms，GPU静止11.125/移动12.092ms；两移动配对−16.892/−18.242ms，约59.2%。原生移动多18.429ms，GPU只多0.967ms。中位数29→11，P95 36→16，但106/130ms长帧仍在，不能说卡顿已解决。
- settle的13视角全visualAccepted=false，RGB92–253/alpha0，原生恢复精确；18组自然基线通过。第5视角实看无明显地形缺失，RGB≥3为2509像素，发光线/伤害数字附近不同，28像素≥200。不仅是1/255舍入；数字像素位置差异原因未明。260像素检查图、8临时图、7纹理释放，43播放者恢复，八项计时预绘计数零变化。
- **viewport-refresh 712c32f2完整960/9**：每GPU区间重新draw整个当前视口并上传，原生裁剪保留，计时不分配。原生移动30.988→GPU移动41.333ms，配对+10.808/+9.883ms，约33.4%倒退，停止此实现。480计时重绘24.5ms/次、上传2.9417ms/次。原生/GPU静止13.183/40.604ms；13像素刷新＋480计时=493、上传495、copies494。2纹理/2CPU图/260像素图释放，47播放者恢复。画面仍不合格，非实战，不部署。
- 两份独立复核：wholeworld-settle/verify_runs.py→runs-review.json（前6轮）、viewport-refresh/verify_run.py→run-review.json。每轮526正式/13运行库/86源/脚本保持。AIR58696/68948/64972/65440/30136/41748/21864均退出；实际占用再即时查询。cost/verify_runs.py是未运行的冗余草稿，不作为证据、不提交（删除失败未转路处理）。

## 5. 已知边界与停止路线

- 上述是暂停模拟、固定动画、预备路线的ENTER_FRAME间隔，**不是无敌人实玩/真实战斗/物理呈现数**。visibility可能被回调观察，不直接叫纯GPU成本。实际敌人AI、子弹/动态画面、RV、Windows真实混合呈现、SATS及长时生命周期未验。
- 8间隔观测后只停止显式播放/实际变帧者；隐式活动者清理用play，isPlaying可从false变true，不宣称内部播放状态原样恢复。只用于终结式隔离实例，不能复制进产品。帧脚本固定drain仅允许已核bloat_bulk_896的1/55帧；成功轮未触发，不能声称该分支已验证。
- 完整截图/像素图有冷首次差异；固定全偏移原生预备后，仍检查三次独立精确自然往返，不循环拍到通过。mainMenuOff必须真实调用。GPU读回再叠Stage.draw不能当OS窗口截图。
- 已停止：远景缓存约1%混合；视口条带clean慢16%；原生明暗裁剪慢3.7%；透明边缘裁剪慢10.6%；GPU仅背景无收益；静态地形GPU慢11.3%；远处单帧根隐藏慢4.2%；远处不可见地形摘树慢3%；整world scrollRect真正抑制Camera写入后仍无收益，cacheAsBitmap慢14.6%。不换名重跑。
- merged合图暂停移动约15%，实际战斗只约6%/3%且第二轮配对反向/P95变差，保留候选不部署。整world alpha/visible与六对象层隐藏只作归因，不是产品。旧CPU text trace语义未明，不命名为文字或纹理耗时。
- 世界暂停不能保证后台不再新增surface；只读见新节点应按身份/顺序处理，不强摘/复活旧图块。多帧isPlaying=false不是静态证明。完整旧试验链见新归档，避免重走失败。
- 原Monstrik读取、合并Weapon/UnitVisual读取+截图、host tag93补丁/grant、CIM CPU查询、合并PNG枚举/Pt读取被拒绝，禁止转路重试。当前Camera旧缓存缺正式补丁，不可拿build/cache/current-swf/scripts/fe/inter/Camera.as覆盖A796。
- 全地图2–5秒、近原版动态游玩及所有兼容目标仍未完整达到。此前用户撤回的afternoon配方不得复活，旧本体回退不能无条件套用。

## 6. 下一步（目标保持活动）

1. 完整固定世界呈现已有可用代价上限证据；整视口逐帧重绘明确太慢。下一步先测**有界局部更新**，确认CPU重绘是否随变化区域明显下降，再考虑完整动态绘制结构。不要把只刷某个假定区域当真实动态正确性；旧位置/新位置、子弹尾迹、图块新生/销毁、弹痕和门变化都要保留。
2. 画质问题未解决：混合/发光与伤害数字有大于RGB2差异。需具体定位层和对象，不能改口成可忽略误差；GPU readback尚未证明Windows窗口呈现。完整固定图不是产品，不直接部署。
3. 能够保持动画后，再做有敌人/无敌人的真实输入镜头移动对照；全部区间保留。当前原生近原版基线需同尺寸/同路线，旧2032固定cam(56,42)不是运动基线，不能复用作收益分母。
4. 通过实际门禁才备份、本机部署、安装复验；A796/CS0.9.0已安装版本保持。继续测试前查共享占用，不清理他人游戏。

## 7. 接续入口

- 本轮：build/generated/camera-stage3d-wholeworld{,-late,-nullslots,-observed,-cost,-settle}-20261027/ 与camera-stage3d-viewport-refresh-20261027/的prepare.py、probe_patch.py、run.py、README/RESULTS；对应knowledge/experiments/evidence/*-r1为原始证据。
- 新旧完整停点归档：state/MEMORY-history-20261027-wholeworld.md；更早MEMORY-history-20261026-2340.md、MEMORY-history-20261023-0818.md。journal顶部本轮和前轮链。
- 85源种子receipt：knowledge/experiments/evidence/camera-atlas-paged-combat-20261025-r1/probe-build.json（983727AE）；frozen f298932b38e24919991997c68e0a8b8a，probe29AF。新变体86源。lineage入口camera-terrain-layers-20261025/lineage.py只允许登记器8B35→E9F5这一变更。
- 隔离调用沿各run.py，先prepare.py生成并校验源码；共享登记game、独立桌面、唯一ID/存储、≥4GiB提交和≥2GiB物理内存。Python在用户.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe，Java在D:/Program Files/Adobe Animate 2024/jre/bin/java.exe，Flex/SWC/ffdec在Sandevistan/build/tools。
- 本轮按已获授权逐条使用会话01a13816精确调用短时grant；未关闭任何保护。工具说明见.agents/skills/remains-{auto-testing,runtime-debug,mod-build,mod-memory,release-gate}/SKILL.md与ModLoader/docs/TEST-REGISTRY.md。
- design/single-map-authoring.md、state/deployment-v090.json为独立编辑器发布；state/scene-tint-deployment-20261024.json为正式A796染色修复。
'''
def main():
    memory=MOD/'state/MEMORY.md';archive=MOD/'state/MEMORY-history-20261027-wholeworld.md'
    assert not archive.exists();old=memory.read_bytes();archive.write_bytes(old)
    prefix=old.decode('utf-8-sig').replace('\r\n','\n').split('## 4. 当前实验停点')[0]
    assert prefix and len(prefix)<6000
    memory.write_text(prefix+BODY,'utf-8')
    journal=MOD/'state/journal.md';text=journal.read_text('utf-8-sig')
    item='''## 2026-10-27 完整世界固定画面显卡呈现出现上限收益，整视口动态重画倒退

- 七轮隔离测试，前五失败全部保留：时间轴在isPlaying=false时仍变帧、空显示槽、首视角RGB112、bloat_bulk_896末帧脚本重播。采用8间隔实际观测＋固定一次已知帧脚本消化后，完整固定图960/9通过归因协议；43播放者固定、7纹理22.6MB，移动29.658→12.092ms，两对−16.892/−18.242ms，约59.2%。真实动画未运行，13视角RGB92–253仍全部不合格，106/130ms长帧仍在，不是可部署修复。
- 追加完整视口逐帧重绘/上传成本对照，同样960/9，移动30.988→41.333ms，两对都更慢；计时CPU重绘24.5ms、上传2.942ms。停止每帧整视口重绘，下一步检验局部变化更新的代价和正确性，不原样重跑挑结果。
- 原生自然基线与恢复均精确；两完成轮各260像素图全部释放，纹理/Context/CPU图释放通过。隐式活动者通过play恢复，isPlaying可能变化，只作终结式隔离诊断；成功轮frameScriptDrain分支0，不夸称验证了重停分支。
- wholeworld-settle/verify_runs.py独立核前6轮，viewport-refresh/verify_run.py独立核追加轮：526正式、13运行库、86源及脚本/编译器输入保持；所有自有AIR退出，无部署、foreign SceneRenderChecks不触碰。详见这些目录RESULTS与review JSON。旧MEMORY原样保存为MEMORY-history-20261027-wholeworld.md后缩写入口。
- 根目标未完成。优先动态局部更新，以及发光混合/伤害数字像素差异、实际Windows呈现；最后回到无敌人/实战镜头对照。A796/7F1F正式版本保持。

'''
    assert text.startswith('# 开发日志\n\n');journal.write_text('# 开发日志\n\n'+item+text[len('# 开发日志\n\n'):],'utf-8')
    attrs=MOD/'.gitattributes';a=attrs.read_text('utf-8-sig')
    names=['camera-stage3d-wholeworld-20261027']+[f'camera-stage3d-wholeworld-{s}-20261027' for s in ('late','nullslots','observed','cost','settle')]+['camera-stage3d-viewport-refresh-20261027']
    for name in names:
        entry=f'build/generated/{name}/** -text whitespace=cr-at-eol,-blank-at-eof'
        assert entry not in a;a+='\n'+entry
    attrs.write_text(a.rstrip()+'\n','utf-8')
    print('Archived prior memory; wrote current snapshot, journal milestone and exact-byte attributes')
if __name__=='__main__':main()
