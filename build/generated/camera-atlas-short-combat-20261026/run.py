"""480-frame native combat ABBA; timing-only candidate, no deployment."""
from pathlib import Path
import argparse
import ast
import hashlib
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
VERSION='camera-atlas-short-combat-1'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

framework=load('short_combat_framework',HERE.parent/'camera-terrain-layers-20261025/run.py')
reference=framework.reference
old,shared,control,dense,base,r,m,support=(framework.old,framework.shared,framework.control,
    framework.dense,framework.base,framework.r,framework.m,framework.support)
lineage=framework.lineage
patch=load('short_combat_patch',HERE/'probe_patch.py')
PINS=dict(framework.PINS)

def runner_inputs():
    old.tested_paging()
    return dict(framework.runner_inputs(),**{str(p):r.sha(p) for p in
        (Path(framework.__file__),HERE/'run.py',HERE/'probe_patch.py',HERE/'README.md',Path(old.__file__),Path(dense.__file__))})

def fixture_inputs():
    return dict(framework.fixture_inputs(),**{str(p):r.sha(p) for p in
        (HERE/'run.py',HERE/'probe_patch.py',HERE/'README.md',Path(old.__file__),Path(dense.__file__))})

def compile_probe(lease,baseline,scripts,compiler,fixture):
    seed=lineage.read_seed(reference)
    staging=HERE/'source-staging'/uuid.uuid4().hex
    patch.prepare(Path(seed['frozenSourcePath']),staging/'src')
    after=base.tree_hashes(staging/'src')
    changed=sorted(k for k in set(after)|set(seed['frozenSourceSHA256']) if after.get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED and len(after)==85
    assert after['SceneRasterPresentation.as']==patch.PRESENTER_SHA
    origin=staging/'source-origin.json'
    r.save(origin,dict(version=VERSION,seedReceiptSHA256=reference.SEED_SHA,seedProbeSHA256=reference.PROBE_SHA,
        seedSourceSHA256=seed['frozenSourceSHA256'],stagedSHA256=after,changed=changed,fixtureInputs=fixture,
        segments=4,framesPerSegment=120,allNativeBehaviorRetained=True))
    path=shared.compile_frozen(lease,staging/'src',baseline,scripts,compiler,fixture)
    value=r.read(path);value.update(shortAtlasVersion=VERSION,sourceOrigin=str(origin),sourceOriginSHA256=r.sha(origin))
    r.save(path,value);return path

def verify_probe(path,baseline,scripts,compiler,fixture):
    value=base.verify_probe(path,baseline,scripts,compiler,fixture)
    assert value['shortAtlasVersion']==VERSION
    seed=lineage.read_seed(reference);op=Path(value['sourceOrigin']);assert r.sha(op)==value['sourceOriginSHA256']
    origin=r.read(op)
    assert origin['seedReceiptSHA256']==reference.SEED_SHA and origin['seedProbeSHA256']==reference.PROBE_SHA
    assert origin['seedSourceSHA256']==seed['frozenSourceSHA256'] and origin['fixtureInputs']==fixture
    assert origin['changed']==patch.CHANGED and origin['stagedSHA256']==value['frozenSourceSHA256']
    assert len(value['frozenSourceSHA256'])==85 and value['frozenSourceSHA256']['SceneRasterPresentation.as']==patch.PRESENTER_SHA
    changed=sorted(k for k in set(value['frozenSourceSHA256'])|set(seed['frozenSourceSHA256'])
        if value['frozenSourceSHA256'].get(k)!=seed['frozenSourceSHA256'].get(k))
    assert changed==patch.CHANGED
    assert (Path(value['frozenSourcePath'])/patch.CHANGED[0]).read_text('utf-8-sig')==patch.transform(
        (Path(seed['frozenSourcePath'])/patch.CHANGED[0]).read_text('utf-8-sig'))
    return value

def options(name):return old.options(name)

class ShorterMeasuredWindows(ast.NodeTransformer):
    """Only measured length constants; no movement, combat or resource checks removed."""
    def __init__(self):self.counts={300:0,1200:0}
    def visit_Constant(self,node):
        if type(node.value) is int and node.value in self.counts:
            self.counts[node.value]+=1
            return ast.copy_location(ast.Constant({300:120,1200:480}[node.value]),node)
        if isinstance(node.value,str) and 'All 1200 continuous intervals' in node.value:
            return ast.copy_location(ast.Constant(node.value.replace('All 1200 continuous intervals','All 480 continuous intervals')),node)
        return node

def shorter(function,scope):
    tree=ast.parse(inspect.getsource(function));transformer=ShorterMeasuredWindows();changed=transformer.visit(tree)
    assert transformer.counts[300]>0
    ast.fix_missing_locations(changed);local=dict(scope)
    exec(compile(changed,'<short-window-'+function.__name__+'>','exec'),local)
    return local[function.__name__],transformer.counts

short_continuous,continuous_counts=shorter(dense.continuous,dense.__dict__)
short_workload,workload_counts=shorter(dense.workload,dense.__dict__)
summary_scope=dict(old.__dict__)
summary_scope.update(VERSION=VERSION,dense=types.SimpleNamespace(VERSION=dense.VERSION,
    continuous=short_continuous,workload=short_workload))
short_summary,summary_counts=shorter(old.summarize,summary_scope)
assert continuous_counts=={300:1,1200:1} and workload_counts=={300:3,1200:0}

def summarize(raw):
    value=short_summary(raw,VERSION)
    assert value['continuous']['count']==480 and value['qualification']['passed']
    assert [row['continuous']['count'] for row in value['rows']]==[120]*4
    value['protocol']=dict(segments=4,framesPerSegment=120,nativeGameplayUnchanged=True,
        summaryConstantChanges=summary_counts,continuousConstantChanges=continuous_counts,
        workloadConstantChanges=workload_counts,originalLongRunFailuresPreserved=True)
    for result,row in zip(value['rows'],raw['samples']):
        poses=list(zip(row['atlasMotion']['worldX'],row['atlasMotion']['worldY']))
        result['cameraPoseChangesWithinWindow']=sum(poses[i]!=poses[i-1] for i in range(1,len(poses)))
        assert result['cameraPoseChangesWithinWindow']>0
    return value

# Keep the already verified registration/process/input/cleanup orchestration.
# These are label/output changes only, with byte-exact reverse verification.
original_main=inspect.getsource(framework.main)
main_source=original_main
main_edits=[('camera terrain layers / 01a13816','camera short atlas combat / 01a13816'),
    ('960 moving camera terrain-layer controls; diagnostic only, no deployment','480 native combat frames, short atlas ABBA; diagnostic only, no deployment'),
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
