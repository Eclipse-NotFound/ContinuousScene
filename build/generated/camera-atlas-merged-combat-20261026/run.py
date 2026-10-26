"""480 native combat frames; fixed preallocated pool, no timed bitmap allocation."""
from pathlib import Path
import argparse
import ast
import importlib.util
import inspect
import json
import shutil
import sys
import traceback
import types
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
VERSION='camera-atlas-merged-combat-1'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

framework=load('pool_short_framework',HERE.parent/'camera-atlas-short-combat-20261026/run.py')
reference=framework.reference
old,shared,control,dense,base,r,m,support=(framework.old,framework.shared,framework.control,
    framework.dense,framework.base,framework.r,framework.m,framework.support)
lineage=framework.lineage
patch=load('pool_patch',HERE/'probe_patch.py')
PINS=dict(framework.PINS)

def own_inputs():
    return {str(p):r.sha(p) for p in (Path(framework.__file__),HERE/'run.py',HERE/'probe_patch.py',
        HERE/'README.md',HERE/'SceneRasterPresentation.as',HERE/'prepare_runner.py',HERE/'tests/SceneCombatAtlasPixels.as',
        patch.CANDIDATE/'probe_patch.py',patch.CANDIDATE/'SceneRasterPresentation.as',HERE.parent/'camera-atlas-pool-20261026/probe_patch.py')}

def runner_inputs():
    assert (HERE/'SceneRasterPresentation.as').read_text('utf-8-sig')==patch.transform_presenter(
        patch.PRESENTER_SOURCE.read_text('utf-8-sig'))
    return dict(framework.runner_inputs(),**own_inputs())

def fixture_inputs():return dict(framework.fixture_inputs(),**own_inputs())

def compile_probe(lease,baseline,scripts,compiler,fixture):
    seed=lineage.read_seed(reference)
    staging=HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(seed['frozenSourcePath']),staging/'src')
    after=base.tree_hashes(staging/'src')
    changed=sorted(k for k in set(after)|set(seed['frozenSourceSHA256']) if after.get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED and len(after)==86
    assert after['SceneRasterPresentation.as']==r.sha(HERE/'SceneRasterPresentation.as')
    origin=staging/'source-origin.json'
    r.save(origin,dict(version=VERSION,seedReceiptSHA256=reference.SEED_SHA,seedProbeSHA256=reference.PROBE_SHA,
        seedSourceSHA256=seed['frozenSourceSHA256'],stagedSHA256=after,changed=changed,fixtureInputs=fixture,
        segments=4,framesPerSegment=120,allNativeBehaviorRetained=True,preallocatedPages=8))
    path=shared.compile_frozen(lease,staging/'src',baseline,scripts,compiler,fixture)
    value=r.read(path);value.update(poolAtlasVersion=VERSION,sourceOrigin=str(origin),sourceOriginSHA256=r.sha(origin))
    r.save(path,value);return path

def verify_probe(path,baseline,scripts,compiler,fixture):
    value=base.verify_probe(path,baseline,scripts,compiler,fixture)
    assert value['poolAtlasVersion']==VERSION
    seed=lineage.read_seed(reference);op=Path(value['sourceOrigin']);assert r.sha(op)==value['sourceOriginSHA256']
    origin=r.read(op)
    assert origin['seedReceiptSHA256']==reference.SEED_SHA and origin['seedProbeSHA256']==reference.PROBE_SHA
    assert origin['seedSourceSHA256']==seed['frozenSourceSHA256'] and origin['fixtureInputs']==fixture
    assert origin['changed']==patch.CHANGED and origin['stagedSHA256']==value['frozenSourceSHA256']
    assert origin['preallocatedPages']==8 and len(value['frozenSourceSHA256'])==86
    assert value['frozenSourceSHA256']['SceneRasterPresentation.as']==r.sha(HERE/'SceneRasterPresentation.as')
    changed=sorted(k for k in set(value['frozenSourceSHA256'])|set(seed['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED
    frozen,source=Path(value['frozenSourcePath']),Path(seed['frozenSourcePath'])
    assert (frozen/patch.CHANGED[0]).read_text('utf-8-sig')==patch.transform_main((source/patch.CHANGED[0]).read_text('utf-8-sig'))
    assert (frozen/patch.CHANGED[1]).read_text('utf-8-sig')==patch.transform_presenter((source/patch.CHANGED[1]).read_text('utf-8-sig'))
    assert r.sha(frozen/patch.CHANGED[2])==r.sha(HERE/patch.CHANGED[2])
    return value

def options(name):return old.options(name)

def page_state(state):
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
        assert set(state['visiblePageKeys'])=={p['key'] for p in state['pages'] if p['key'] in state['currentPageKeys'] and any(p['layerHasPixels'])}
    else:assert not state['visiblePageKeys'] and state['pendingHidden']==0

summary_source=inspect.getsource(old.summarize)
tree=ast.parse(summary_source)
counter=framework.ShorterMeasuredWindows();tree=counter.visit(tree);ast.fix_missing_locations(tree)
assert counter.counts=={300:6,1200:0}
scope=dict(old.__dict__)
scope.update(VERSION=VERSION,page_state=page_state,dense=types.SimpleNamespace(VERSION=dense.VERSION,
    continuous=framework.short_continuous,workload=framework.short_workload))
exec(compile(tree,'<pool-atlas-summary>','exec'),scope)
pool_summary=scope['summarize']

def summarize(raw):
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


pool_verified_summary=summarize
def summarize(raw):
    value=pool_verified_summary(raw);pixels=raw['combatAtlasPixels']
    assert pixels['passed'] and pixels['error'] is None and pixels['presented']
    assert pixels['created']==pixels['disposed']==3 and pixels['stateRestored']
    assert pixels['atlas']['maxRGB']<=2 and pixels['atlas']['maxAlpha']==0 and pixels['restore']['equal']
    assert pixels['startedAtMs']>=raw['samples'][-1]['sampleAtMs'][-1]
    displayed=[];omitted=[]
    for row in raw['samples']:
        for state in row['atlasMotion']['states']:
            for page in state['pages']:
                content,shown=page['layerHasPixels'],page['layerVisible']
                assert len(content)==len(shown)==4 and all(type(x) is bool for x in content+shown)
                assert not content[1] and not shown[1]
                assert shown==[bool(state['presented'] and page['key'] in state['currentPageKeys'] and b) for b in content]
            if state['presented']:
                pages=[p for p in state['pages'] if p['key'] in state['currentPageKeys']]
                displayed.append(sum(sum(p['layerVisible']) for p in pages))
                omitted.append(sum(sum(not b for b in p['layerHasPixels']) for p in pages))
    assert displayed and max(omitted)>0
    value['combatTerminalPixels']=pixels
    value['layerCounts']=dict(displayed=base.metrics(displayed),omitted=base.metrics(omitted))
    value['limitations'].append('Three synchronous terminal combat screenshots are excluded from timing; one view does not cover all effects or every combat frame.')
    return value

original_main=inspect.getsource(framework.framework.main)
main_source=original_main
main_edits=[('camera terrain layers / 01a13816','camera pool atlas combat / 01a13816'),
    ('960 moving camera terrain-layer controls; diagnostic only, no deployment','480 native combat frames, preallocated atlas ABBA; diagnostic only, no deployment'),
    ("arms=summary['arms'],pairs=summary['pairs']","grouped=summary['grouped'],qualification=summary['qualification']")]
for before,after in main_edits:assert main_source.count(before)==1;main_source=main_source.replace(before,after,1)
reverse=main_source
for before,after in reversed(main_edits):reverse=reverse.replace(after,before,1)
assert reverse==original_main
exec(compile(main_source,'<unchanged-owned-game-orchestration>','exec'),globals())

shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
