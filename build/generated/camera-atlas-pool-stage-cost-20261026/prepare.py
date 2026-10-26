"""Source-only attribution: retain the tested pool, split the camera callback cost."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-pool-paused-v2-20261026'
extra_patch='''
original_helper_source=helper_source
def helper_source():
    source=original_helper_source()
    edits=[('row.atlasStates.push(pending.atlas);',
        'row.atlasStates.push(pending.atlas);row.cameraMs.push(pending.cameraMs);row.presenterMs.push(pending.presenterMs);row.guardMs.push(pending.guardMs);row.snapshotMs.push(pending.snapshotMs);'),
        ('workMs:[],presented:[],atlasStates:[],','workMs:[],presented:[],atlasStates:[],cameraMs:[],presenterMs:[],guardMs:[],snapshotMs:[],'),
        ('            if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();',
         '            var cameraEnd:int=getTimer();\\n            if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();\\n            var presenterEnd:int=getTimer();'),
        ('            checkTransform();guard();\\n            pending=',
         '            checkTransform();guard();var guardEnd:int=getTimer();\\n            pending='),
        ('atlas:presenter.snapshot(),workMs:getTimer()-at};',
         'atlas:presenter.snapshot(),workMs:getTimer()-at};\\n            var end:int=getTimer();pending.workMs=end-at;\\n            pending.cameraMs=cameraEnd-at;pending.presenterMs=presenterEnd-cameraEnd;\\n            pending.guardMs=guardEnd-presenterEnd;pending.snapshotMs=end-guardEnd;')]
    result=source
    for before,after in edits:
        assert result.count(before)==1,(before,result.count(before));result=result.replace(before,after,1)
    reverse=result
    for before,after in reversed(edits):
        assert reverse.count(after)==1;reverse=reverse.replace(after,before,1)
    assert reverse==source
    return result

'''
extra_summary='''
verified_summary=summarize
def summarize(raw):
    value=verified_summary(raw)
    fields=('cameraMs','presenterMs','guardMs','snapshotMs')
    trial=raw['cameraRaster'];spikes=[];groups={}
    for row in trial['windows']:
        assert all(len(row[key])==120 for key in fields)
        for j,dt in enumerate(row['framesMs']):
            costs={key:row[key][j] for key in fields}
            assert all(type(v) is int and v>=0 for v in costs.values())
            assert sum(costs.values())==row['workMs'][j]
            if dt>=100 or row['workMs'][j]>=40:
                state=row['atlasStates'][j]
                previous=row['atlasStates'][j-1] if j else row['start']['atlas']
                spikes.append(dict(window=row['index'],frame=j,mode=row['mode'],intervalMs=dt,
                    workMs=row['workMs'][j],costs=costs,
                    atlasDelta={k:state[k]-previous[k] for k in ('copies','rebuilds','evictions','cellClears','allocations','disposals')}))
    for mode in value['arms']:
        groups[mode]={key:base.metrics([n for row in trial['windows'] if row['mode']==mode for n in row[key]]) for key in fields}
    value['callbackAttribution']=dict(fields=list(fields),groups=groups,spikes=spikes,
        limitation='Inclusive millisecond wall clocks identify the callback stage, not GPU/GC causes; added observation is not production performance acceptance.')
    return value

'''
for name in ('run.py','probe_patch.py','README.md'):
    target=HERE/name;assert not target.exists()
    source=(OLD/name).read_text('utf-8-sig').replace('camera-atlas-pool-paused-2','camera-atlas-pool-stage-cost-1')
    if name=='probe_patch.py':
        before='def prepare(source:Path,destination:Path):'
        assert source.count(before)==1;source=source.replace(before,extra_patch+before,1)
    if name=='run.py':
        before='original_main=inspect.getsource(framework.framework.framework.main)'
        assert source.count(before)==1;source=source.replace(before,extra_summary+before,1)
    if name=='README.md':
        source+='\n\n本轮只增加四段墙钟观察：镜头/原生sceneTick、呈现器、状态守卫、快照。固定池35956ECD完全不改。每帧四段之和必须等于原workMs；所有尖峰保留。用于定位前轮跨页220ms帧中的185ms准备开销，不据跨轮帧率差判断优化。\n'
    if name.endswith('.py'):compile(source,name,'exec')
    target.write_text(source,'utf-8',newline='\n')
print('Prepared source only; no compiler, AIR, or deployment')
