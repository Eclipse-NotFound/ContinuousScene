"""Prepare source-only revision; preserve the failed first receipt and all inputs."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-pool-paused-20261026'
for name in ('run.py','probe_patch.py','README.md'):
    target=HERE/name;assert not target.exists()
    source=(OLD/name).read_text('utf-8-sig')
    source=source.replace('camera-atlas-pool-paused-1','camera-atlas-pool-paused-2')
    if name=='run.py':
        before="HERE/'README.md',patch.HELPER"
        assert source.count(before)==1
        source=source.replace(before,"HERE/'README.md',HERE/'prepare.py',patch.HELPER",1)
    if name=='probe_patch.py':
        before='def transform_main(source):return paged_patch.transform(source)'
        after='''def transform_main(source):
    value=paged_patch.transform(source)
    before='if(cfg.drawControl=="atlas") {\\n                if(cfg.benchmark!="scene"'
    after='if(cfg.drawControl=="atlas" && !cfg.presentationCheck) {\\n                if(cfg.benchmark!="scene"'
    assert value.count(before)==1
    changed=value.replace(before,after,1)
    assert changed.replace(after,before,1)==value
    return changed'''
        assert source.count(before)==1;source=source.replace(before,after,1)
    if name=='README.md':
        source+='\n\nv1因战斗专用init拒绝presentationCheck而留在菜单，0性能/像素；旧600秒超时证据完整保留。本版只将那条战斗门控限定为非presentationCheck，phase97自身检查均保留。正式游戏与缓存算法不变。\n'
    if name.endswith('.py'):compile(source,name,'exec')
    target.write_text(source,'utf-8',newline='\n')
print('Prepared source only; no compiler, AIR, or deployment')
