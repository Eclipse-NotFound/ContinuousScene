"""Fixed-pool same-frame pixels and paused camera route; no deployment."""
from pathlib import Path
import argparse
import importlib.util
import inspect
import json
import shutil
import sys
import traceback
import uuid

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
VERSION='camera-atlas-pool-paused-1'

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

framework=load('paused_pool_framework',HERE.parent/'camera-atlas-pool-20261026/run.py')
reference=framework.reference
old,shared,control,dense,base,r,m,support=(framework.old,framework.shared,framework.control,
    framework.dense,framework.base,framework.r,framework.m,framework.support)
lineage=framework.lineage
patch=load('paused_pool_patch',HERE/'probe_patch.py')
paused=load('paused_pool_old_runner',patch.PAGED/'run.py')
PINS=dict(framework.PINS)

def own_inputs():
    return {str(p):r.sha(p) for p in (Path(framework.__file__),HERE/'run.py',HERE/'probe_patch.py',
        HERE/'README.md',patch.HELPER,patch.PAGED/'tests/SceneCameraRasterTrial.as',
        patch.PAGED/'run.py',patch.PAGED/'probe_patch.py',patch.PAGED/'presentation_transform.py')}

def runner_inputs():
    assert patch.HELPER.read_text('utf-8-sig')==patch.helper_source()
    return dict(framework.runner_inputs(),**own_inputs())

def fixture_inputs():return dict(framework.fixture_inputs(),**own_inputs())

def compile_probe(lease,baseline,scripts,compiler,fixture):
    seed=lineage.read_seed(reference);staging=HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(seed['frozenSourcePath']),staging/'src')
    after=base.tree_hashes(staging/'src')
    changed=sorted(k for k in set(after)|set(seed['frozenSourceSHA256']) if after.get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED and len(after)==86
    assert after['SceneRasterPresentation.as']==patch.PRESENTER_SHA
    origin=staging/'source-origin.json'
    r.save(origin,dict(version=VERSION,seedReceiptSHA256=reference.SEED_SHA,seedProbeSHA256=reference.PROBE_SHA,
        seedSourceSHA256=seed['frozenSourceSHA256'],stagedSHA256=after,changed=changed,fixtureInputs=fixture))
    path=shared.compile_frozen(lease,staging/'src',baseline,scripts,compiler,fixture)
    value=r.read(path);value.update(poolPausedVersion=VERSION,sourceOrigin=str(origin),sourceOriginSHA256=r.sha(origin))
    r.save(path,value);return path

def verify_probe(path,baseline,scripts,compiler,fixture):
    value=base.verify_probe(path,baseline,scripts,compiler,fixture)
    assert value['poolPausedVersion']==VERSION
    seed=lineage.read_seed(reference);op=Path(value['sourceOrigin']);assert r.sha(op)==value['sourceOriginSHA256']
    origin=r.read(op)
    assert origin['seedReceiptSHA256']==reference.SEED_SHA and origin['seedProbeSHA256']==reference.PROBE_SHA
    assert origin['seedSourceSHA256']==seed['frozenSourceSHA256'] and origin['fixtureInputs']==fixture
    assert origin['changed']==patch.CHANGED and origin['stagedSHA256']==value['frozenSourceSHA256']
    assert len(value['frozenSourceSHA256'])==86 and value['frozenSourceSHA256']['SceneRasterPresentation.as']==patch.PRESENTER_SHA
    changed=sorted(k for k in set(value['frozenSourceSHA256'])|set(seed['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED
    frozen,source=Path(value['frozenSourcePath']),Path(seed['frozenSourcePath'])
    assert (frozen/patch.CHANGED[0]).read_text('utf-8-sig')==patch.transform_main((source/patch.CHANGED[0]).read_text('utf-8-sig'))
    assert r.sha(frozen/patch.CHANGED[2])==r.sha(patch.HELPER)
    return value

def options(name):return paused.options(name)

original_verify=inspect.getsource(paused.verify_trial)
assert original_verify.count('camera-atlas-paged-trial-2')==1
verify_source=original_verify.replace('camera-atlas-paged-trial-2',VERSION,1)
verify_scope=dict(paused.__dict__);exec(compile(verify_source,'<pool-paused-verified-checks>','exec'),verify_scope)
verify_trial=verify_scope['verify_trial']

def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config']
    assert cfg['drawControl']=='atlas' and cfg['presentationCheck'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    trial,cleanup=raw['cameraRaster'],raw['cameraRasterCleanup']
    rows=verify_trial(trial,cleanup)
    assert trial['zeroRasterWork'] and all(v==0 for v in trial['timingRasterDelta'].values())
    prep=trial['poolPreparation'];assert len(prep)==2
    for index,item in enumerate(prep):
        before,after=item['before'],item['after']
        framework.page_state(before);framework.page_state(after)
        assert before['ownedBitmaps']==0 and after['ownedBitmaps']==32 and after['freePages']==8
        assert after['allocations']-before['allocations']==32
        assert item['label']==['before-pixels','before-timing'][index]
        assert item['endedAtMs']>=item['startedAtMs']
    assert prep[-1]['endedAtMs']<=trial['timingStartAtMs']
    initial=trial['timingStart']['atlas']
    assert initial['allocations']==64 and initial['disposals']==32
    for row in trial['windows']:
        for state in row['atlasStates']:
            framework.page_state(state)
            assert state['allocations']==64 and state['disposals']==32 and state['ownedBitmaps']==32
    final=cleanup['atlasAfter'];framework.page_state(final)
    assert final['allocations']==final['disposals']==64 and final['poolPages']==0
    arms={mode:base.metrics([x for row in trial['windows'] if row['mode']==mode for x in row['framesMs']])
        for mode in ('native-static','native-moving','atlas-static','atlas-moving')}
    pairs=[dict(nativeIndex=a,atlasIndex=b,mode=rows[b]['mode'],atlasMinusNativeMs=rows[b]['meanMs']-rows[a]['meanMs'])
        for a,b in ((1,3),(6,4),(0,2),(7,5))]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        rows=rows,arms=arms,pairs=pairs,elapsedMs=trial['timingElapsedMs'],zeroNativeRasterWork=True,
        pixels=trial['pixels'],fallbackPixels=trial['fallbackPixels'],cleanup=cleanup,
        preparation=[dict(label=x['label'],elapsedMs=x['endedAtMs']-x['startedAtMs'],pixelBytes=x['after']['pixelStorageBytes'],
            runtimeMemoryIncrease=x['memoryAfter']-x['memoryBefore']) for x in prep],
        timedBitmapAllocations=0,timedBitmapDisposals=0,
        limits=['Simulation paused, timelines and other callbacks live; not enemy-free gameplay FPS.',
            'Same-process native arm retains an invisible pool; no production loading integration yet.',
            'All 960 timing frames and spikes retained; preparation cost recorded separately.'])

original_main=inspect.getsource(framework.framework.framework.main)
main_source=original_main
edits=[('camera terrain layers / 01a13816','camera pool paused / 01a13816'),
    ('960 moving camera terrain-layer controls; diagnostic only, no deployment','960 pool camera frames plus pixels/lifecycle; diagnostic only, no deployment')]
for before,after in edits:assert main_source.count(before)==1;main_source=main_source.replace(before,after,1)
reverse=main_source
for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
assert reverse==original_main
exec(compile(main_source,'<unchanged-owned-game-orchestration>','exec'),globals())

shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
