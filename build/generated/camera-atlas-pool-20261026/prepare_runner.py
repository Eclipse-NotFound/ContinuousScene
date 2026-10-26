"""Prepare a frozen-pool runner; retain the owned orchestration and combat checks."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
source=(HERE.parent/'camera-atlas-budget-20261026/run.py').read_text('utf-8-sig')

def one(before,after):
    global source
    assert source.count(before)==1,(before,source.count(before))
    source=source.replace(before,after,1)

one('480 native combat frames; at most one new atlas bitmap per update.',
    '480 native combat frames; fixed preallocated pool, no timed bitmap allocation.')
source=source.replace('camera-atlas-budget-combat-1','camera-atlas-pool-combat-1')
source=source.replace('budget_short_framework','pool_short_framework').replace("'budget_patch'","'pool_patch'")
source=source.replace('budgetAtlasVersion','poolAtlasVersion')
source=source.replace('bitmapAllocationsPerUpdate=1','preallocatedPages=8')
source=source.replace("origin['bitmapAllocationsPerUpdate']==1","origin['preallocatedPages']==8")
one("HERE/'README.md',HERE/'SceneRasterPresentation.as')}",
    "HERE/'README.md',HERE/'SceneRasterPresentation.as',HERE/'prepare_runner.py')}")
begin=source.index('def page_state(state):')
end=source.index('summary_source=inspect.getsource(old.summarize)',begin)
source=source[:begin]+'''def page_state(state):
    assert state['version']=='atlas-pool-1'
    assert state['pageSide']==1280 and state['cellSide']==320 and state['pageLimit']==8
    assert 0<=state['livePages']<=state['peakPages']<=8
    assert state['pagesCreated']-state['pagesDisposed']==state['livePages']
    assert state['poolPages']==state['livePages']+state['freePages']
    assert state['poolPages']==(8 if state['poolReady'] else 0)
    assert state['layers']==state['attached']==state['liveBitmaps']==state['livePages']*4
    assert state['layers']==sum(p['layers'] for p in state['pages'])
    assert state['ownedBitmaps']==state['allocations']-state['disposals']==state['poolPages']*4
    layer_bytes=1280*1280*4
    assert state['pixelStorageBytes']==state['ownedBitmaps']*layer_bytes
    assert 0<=state['pixelStorageBytes']<=state['peakPixelStorageBytes']<=8*4*layer_bytes
    assert state['totalAllocatedPixelBytes']==state['allocations']*layer_bytes
    assert len(state['residentPageKeys'])==len(set(state['residentPageKeys']))==state['livePages']
    assert len(state['currentPageKeys'])==len(set(state['currentPageKeys']))==state['requestedPages']
    assert set(state['visiblePageKeys'])<=set(state['currentPageKeys'])<=set(state['residentPageKeys'])
    if state['presented']:
        assert state['visiblePageKeys'] and state['pendingHidden']>0 and not state['fallbackReason']
        assert set(state['visiblePageKeys'])==set(state['currentPageKeys'])
    else:assert not state['visiblePageKeys'] and state['pendingHidden']==0

'''+source[end:]
begin=source.index("before='expected = bool(")
end=source.index('tree=ast.parse(summary_source)',begin)
source=source[:begin]+source[end:]
source=source.replace("'<budget-atlas-summary>'","'<pool-atlas-summary>'").replace('budget_summary','pool_summary')
begin=source.index('def summarize(raw):')
end=source.index('original_main=inspect.getsource(',begin)
source=source[:begin]+'''def summarize(raw):
    value=pool_summary(raw,VERSION)
    assert value['continuous']['count']==480 and value['qualification']['passed']
    assert [row['continuous']['count'] for row in value['rows']]==[120]*4
    preparation=raw['atlasPoolPreparation']
    before,after=preparation['before'],preparation['after']
    page_state(before);page_state(after)
    assert before['ownedBitmaps']==0 and after['ownedBitmaps']==32 and after['freePages']==8 and after['livePages']==0
    assert after['allocations']==32 and after['disposals']==0 and after['copies']==after['rebuilds']==0
    assert preparation['startedAtMs']<=preparation['endedAtMs']<=raw['continuousSampling']['startedAtMs']
    assert after['pixelStorageBytes']==209715200
    for result,row in zip(value['rows'],raw['samples']):
        poses=list(zip(row['atlasMotion']['worldX'],row['atlasMotion']['worldY']))
        result['cameraPoseChangesWithinWindow']=sum(poses[i]!=poses[i-1] for i in range(1,len(poses)))
        assert result['cameraPoseChangesWithinWindow']>0
        for state in row['atlasMotion']['states']:
            assert state['poolReady'] and state['poolPages']==8
            assert state['allocations']==32 and state['disposals']==0 and state['ownedBitmaps']==32
        result['timedBitmapAllocations']=0
    final=raw['atlasMotionCleanup']['after']
    assert final['allocations']==final['disposals']==32 and final['poolPages']==final['ownedBitmaps']==0
    value['preparation']=dict(elapsedMs=preparation['endedAtMs']-preparation['startedAtMs'],
        pixelBytes=after['pixelStorageBytes'],runtimeMemoryIncrease=preparation['memoryAfter']-preparation['memoryBefore'],
        timing='after fixture warmup, before first measured frame; not yet integrated into production loading')
    value['protocol']=dict(segments=4,framesPerSegment=120,nativeGameplayUnchanged=True,
        preallocatedPages=8,timedBitmapAllocations=0,originalLongRunFailuresPreserved=True)
    value['limitations'].append('The native arm retains the same-process invisible pool but performs no atlas synchronization; separate loading/visual/lifecycle acceptance remains required.')
    return value

'''+source[end:]
source=source.replace('camera budget atlas combat / 01a13816','camera pool atlas combat / 01a13816')
source=source.replace('480 native combat frames, budget atlas ABBA','480 native combat frames, preallocated atlas ABBA')
compile(source,'pool-run-source','exec')
target=HERE/'run.py';assert not target.exists()
target.write_text(source,'utf-8',newline='\n')
print('Prepared source only; no compiler, AIR, or deployment')
