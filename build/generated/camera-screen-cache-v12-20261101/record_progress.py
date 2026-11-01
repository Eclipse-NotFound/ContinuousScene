from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[5]
REPO=ROOT/'mods/ContinuousScene'
marker='<!-- camera-optimization-20261101 -->'
memory='''
<!-- camera-optimization-20261101 -->
> 2026-11-01 14:58 后续优化进行中：正式宿主已从 CA94 安全撤回到 **9D8662F6**，只撤掉 sceneTick 无条件单位显隐，前三层 A2/预绘预算保留。独立当前组合20断言通过，原版UnitSpectre保持隐藏；备份与回执见 build/generated/camera-object-clip-v7-20261101/visibility-fix-deployment.json。CS D8A/WB FE3/RV AEA未改。整层裁剪/物体缓存/炮塔guard复验均无稳定镜头收益，不部署；既有地形节点cache画面相等但不提速；旧缩放fill在实际0.6583窗口失败（含alpha差），已拦下。正在私有测试目录验证屏幕分辨率增量地形缓存（v12），尚未验收或部署。测试通过共享登记串行安排，不停其它任务或玩家。详情稍后汇入本轮报告。
<!-- /camera-optimization-20261101 -->

'''
journal='''<!-- camera-optimization-20261101 -->
## 2026-11-01 — 继续镜头优化：先撤回单位显隐回归（进行中）

- 14:58正式宿主 CA94→9D8662F6，只撤掉无条件visible赋值；当前依赖组合/原生UnitSpectre/连续场景及镜头运行通过；相同已验字节部署并回读，旧文件独立备份。
- 整层scrollRect/形状mask、物体0/1层缓存、炮塔同帧guard、既有地形节点cache暂无稳定镜头收益，均不部署。内存回收停顿在短对照段之间错位，不能用选段的P99宣称guard改善。
- 旧局部phase fill在真实小窗0.658333比例像素检查失败；phase搜索将差异缩小但仍有alpha差，不进入产品。新屏幕分辨率增量地形缓存v12正待实测。
- 本轮报告与收尾待补；他人的SceneRenderChecks及既有状态/报告改动保留。
<!-- /camera-optimization-20261101 -->

'''
preserved={}
for rel,note in [('state/MEMORY.md',memory),('state/journal.md',journal)]:
    path=REPO/rel;raw=path.read_bytes()
    if marker.encode() in raw:raise RuntimeError('Own progress note already exists')
    preserved[rel]=hashlib.sha256(raw).hexdigest()
    nl='\r\n' if b'\r\n' in raw else '\n';add=note.replace('\n',nl).encode()
    if rel.endswith('MEMORY.md'):
        pos=raw.index(b'\n')+1;new=raw[:pos]+add+raw[pos:]
    else:new=add+raw
    assert new.replace(add,b'',1)==raw
    path.write_bytes(new)
(Path(__file__).parent/'preserved-state.json').write_text(json.dumps(preserved,indent=2),'utf-8')
print('Updated current install and ongoing work without altering pre-existing notes.')
