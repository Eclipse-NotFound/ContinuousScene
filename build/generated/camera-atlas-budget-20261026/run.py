"""480 native combat frames; at most one new atlas bitmap per update."""
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
VERSION='camera-atlas-budget-combat-1'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

framework=load('budget_short_framework',HERE.parent/'camera-atlas-short-combat-20261026/run.py')
reference=framework.reference
old,shared,control,dense,base,r,m,support=(framework.old,framework.shared,framework.control,
    framework.dense,framework.base,framework.r,framework.m,framework.support)
lineage=framework.lineage
patch=load('budget_patch',HERE/'probe_patch.py')
PINS=dict(framework.PINS)

def own_inputs():
    return {str(p):r.sha(p) for p in (Path(framework.__file__),HERE/'run.py',HERE/'probe_patch.py',
        HERE/'README.md',HERE/'SceneRasterPresentation.as')}

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
    assert changed==patch.CHANGED and len(after)==85
    assert after['SceneRasterPresentation.as']==r.sha(HERE/'SceneRasterPresentation.as')
    origin=staging/'source-origin.json'
    r.save(origin,dict(version=VERSION,seedReceiptSHA256=reference.SEED_SHA,seedProbeSHA256=reference.PROBE_SHA,
        seedSourceSHA256=seed['frozenSourceSHA256'],stagedSHA256=after,changed=changed,fixtureInputs=fixture,
        segments=4,framesPerSegment=120,allNativeBehaviorRetained=True,bitmapAllocationsPerUpdate=1))
    path=shared.compile_frozen(lease,staging/'src',baseline,scripts,compiler,fixture)
    value=r.read(path);value.update(budgetAtlasVersion=VERSION,sourceOrigin=str(origin),sourceOriginSHA256=r.sha(origin))
    r.save(path,value);return path

def verify_probe(path,baseline,scripts,compiler,fixture):
    value=base.verify_probe(path,baseline,scripts,compiler,fixture)
    assert value['budgetAtlasVersion']==VERSION
    seed=lineage.read_seed(reference);op=Path(value['sourceOrigin']);assert r.sha(op)==value['sourceOriginSHA256']
    origin=r.read(op)
    assert origin['seedReceiptSHA256']==reference.SEED_SHA and origin['seedProbeSHA256']==reference.PROBE_SHA
    assert origin['seedSourceSHA256']==seed['frozenSourceSHA256'] and origin['fixtureInputs']==fixture
    assert origin['changed']==patch.CHANGED and origin['stagedSHA256']==value['frozenSourceSHA256']
    assert origin['bitmapAllocationsPerUpdate']==1 and len(value['frozenSourceSHA256'])==85
    assert value['frozenSourceSHA256']['SceneRasterPresentation.as']==r.sha(HERE/'SceneRasterPresentation.as')
    changed=sorted(k for k in set(value['frozenSourceSHA256'])|set(seed['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED
    frozen,source=Path(value['frozenSourcePath']),Path(seed['frozenSourcePath'])
    assert (frozen/patch.CHANGED[0]).read_text('utf-8-sig')==patch.transform_main((source/patch.CHANGED[0]).read_text('utf-8-sig'))
    assert (frozen/patch.CHANGED[1]).read_text('utf-8-sig')==patch.transform_presenter((source/patch.CHANGED[1]).read_text('utf-8-sig'))
    return value

def options(name):return old.options(name)

def page_state(state):
    assert state['version']=='atlas-budget-1'
    assert state['pageSide']==1280 and state['cellSide']==320 and state['pageLimit']==8
    assert 0<=state['livePages']<=state['peakPages']<=8
    assert state['pagesCreated']-state['pagesDisposed']==state['livePages']
    assert state['layers']==state['attached']==state['liveBitmaps']==state['allocations']-state['disposals']
    assert state['layers']==sum(p['layers'] for p in state['pages'])
    assert all(0<=p['layers']<=4 and p['ready']==(p['layers']==4) for p in state['pages'])
    assert state['readyPages']==sum(p['ready'] for p in state['pages'])
    assert state['partialPages']==state['livePages']-state['readyPages']
    assert state['pendingPages']==sum(not p['ready'] and p['key'] in state['currentPageKeys'] for p in state['pages'])
    assert state['allocationsLastUpdate'] in (0,1)
    layer_bytes=1280*1280*4
    assert state['pixelStorageBytes']==state['liveBitmaps']*layer_bytes
    assert 0<=state['pixelStorageBytes']<=state['peakPixelStorageBytes']<=8*4*layer_bytes
    assert state['totalAllocatedPixelBytes']==state['allocations']*layer_bytes
    assert len(state['residentPageKeys'])==len(set(state['residentPageKeys']))==state['livePages']
    assert len(state['currentPageKeys'])==len(set(state['currentPageKeys']))==state['requestedPages']
    assert set(state['visiblePageKeys'])<=set(state['currentPageKeys'])<=set(state['residentPageKeys'])
    if state['presented']:
        assert state['visiblePageKeys'] and state['pendingHidden']>0 and not state['fallbackReason']
        assert state['pendingPages']==0 and set(state['visiblePageKeys'])==set(state['currentPageKeys'])
    else:assert not state['visiblePageKeys'] and state['pendingHidden']==0

summary_source=inspect.getsource(old.summarize)
before='expected = bool(not reason and pose is not None and current != pose)'
after="expected = bool(not reason and pose is not None and current != pose and state['pendingPages'] == 0)"
assert summary_source.count(before)==1
summary_source=summary_source.replace(before,after,1)
assert summary_source.replace(after,before,1)==inspect.getsource(old.summarize)
tree=ast.parse(summary_source)
counter=framework.ShorterMeasuredWindows();tree=counter.visit(tree);ast.fix_missing_locations(tree)
assert counter.counts=={300:6,1200:0}
scope=dict(old.__dict__)
scope.update(VERSION=VERSION,page_state=page_state,dense=types.SimpleNamespace(VERSION=dense.VERSION,
    continuous=framework.short_continuous,workload=framework.short_workload))
exec(compile(tree,'<budget-atlas-summary>','exec'),scope)
budget_summary=scope['summarize']

def summarize(raw):
    value=budget_summary(raw,VERSION)
    assert value['continuous']['count']==480 and value['qualification']['passed']
    assert [row['continuous']['count'] for row in value['rows']]==[120]*4
    previous_allocations=0
    for result,row in zip(value['rows'],raw['samples']):
        poses=list(zip(row['atlasMotion']['worldX'],row['atlasMotion']['worldY']))
        result['cameraPoseChangesWithinWindow']=sum(poses[i]!=poses[i-1] for i in range(1,len(poses)))
        assert result['cameraPoseChangesWithinWindow']>0
        states=row['atlasMotion']['states']
        for state in states:
            delta=state['allocations']-previous_allocations
            assert delta==state['allocationsLastUpdate'] and delta in (0,1)
            previous_allocations=state['allocations']
        result['allocationFrames']=sum(s['allocationsLastUpdate']>0 for s in states)
        result['buildingFrames']=sum(s['pendingPages']>0 for s in states)
    value['protocol']=dict(segments=4,framesPerSegment=120,nativeGameplayUnchanged=True,
        bitmapAllocationsPerUpdate=1,allBuildingFramesRetained=True,originalLongRunFailuresPreserved=True)
    return value

original_main=inspect.getsource(framework.framework.main)
main_source=original_main
main_edits=[('camera terrain layers / 01a13816','camera budget atlas combat / 01a13816'),
    ('960 moving camera terrain-layer controls; diagnostic only, no deployment','480 native combat frames, budget atlas ABBA; diagnostic only, no deployment'),
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
