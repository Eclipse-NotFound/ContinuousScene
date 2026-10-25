"""Isolated candidate runtime/identity smoke on exact native SMG fixture.

No lifecycle or production performance acceptance; no production deployment.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import shutil
import sys
import traceback
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
VERSION = 'activity-release-native-1'


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


build=load('activity_native_build',HERE/'build_candidates.py')
quality=build.support
w,old,shared,control,dense,base,r,m,support=(quality.w,quality.old,quality.shared,quality.control,
    quality.dense,quality.base,quality.r,quality.m,quality.support)
BUILD=HERE/'candidate-builds/0dd3bd018d0c41f89c979a95ff5bbf2a/build.json'
PRODUCTS={'mods/ContinuousScene/release/ContinuousSceneMod.swf':'ContinuousSceneMod.swf',
          'mods/TDFC/release/TDFCMod.swf':'TDFCMod.swf'}
ANCHOR='            closeProbeTiming(true);'
INSERT='''
            if(error==null && report.samples.length==4 && w && w.grafon.sceneLarge) {
                try {report.activityReleaseEnd=SceneActivityReleaseEnd.read(w);}
                catch(activityError:*) {error="Activity candidate identity/read failed: "+String(activityError);}
            }'''


def runner_inputs():
    return dict(build.inputs(),**{str(p):r.sha(p) for p in (Path(__file__),HERE/'SceneActivityReleaseEnd.as',BUILD)})


def candidate():
    value=r.read(BUILD)
    assert value['compiled'] and value['bytecodeAudit']['passed'] and not value['gameStarted'] and not value['deployed']
    assert value['observerOnly'] and value['observerTransforms']
    assert value['sourceInputs']==build.inputs()
    for name,sha in value['artifacts'].items():assert r.sha(BUILD.parent/name)==sha,name
    for name,pins in value['frozenSourceSHA256'].items():assert build.tree(BUILD.parent/name)==pins
    return value


def fixture_inputs():
    seed=w.seed();value=candidate()
    paths=[w.SEED,Path(seed['probePath']),Path(seed['configPath']),Path(seed['sourceOrigin']),
           Path(seed['probePath']).parent/'probe-build.json',HERE/'SceneActivityReleaseEnd.as',BUILD,
           support.OUT/'source-provenance.json']+[BUILD.parent/name for name in PRODUCTS.values()]
    return {str(p):r.sha(p) for p in paths}


def compile_probe(lease,baseline,scripts,compiler,fixture):
    seed=w.seed();src=Path(seed['frozenSourcePath'])
    out=HERE/'probe-staging'/uuid.uuid4().hex/'src';shutil.copytree(src,out)
    main=out/'ContinuousSceneMotionProbe.as';text=main.read_text('utf-8-sig')
    assert text.count(ANCHOR)==1 and INSERT not in text
    changed=text.replace(ANCHOR,ANCHOR+INSERT,1)
    assert changed.replace(ANCHOR+INSERT,ANCHOR,1)==text
    main.write_text(changed,'utf-8');shutil.copy2(HERE/'SceneActivityReleaseEnd.as',out/'SceneActivityReleaseEnd.as')
    pins=base.tree_hashes(out)
    assert len(pins)==86
    assert sorted(k for k in set(pins)|set(seed['frozenSourceSHA256'])
        if pins.get(k)!=seed['frozenSourceSHA256'].get(k))==['ContinuousSceneMotionProbe.as','SceneActivityReleaseEnd.as']
    receipt=shared.compile_frozen(lease,out,baseline,scripts,compiler,fixture)
    return receipt


def summary(raw):
    assert raw['ok'] and raw['error'] is None and len(raw['assertions'])==26 and all(x['ok'] for x in raw['assertions'])
    assert len(raw['samples'])==4
    cfg,motion=raw['config'],raw['nativeInputMotion']
    assert cfg['drawControl']=='rcnative' and cfg['benchmark']=='scene'
    assert all(cfg[k] for k in ('nativeInputMotion','nativeSprint','stableMotion','playerFire','fixedEnemies','combatRoute','noLighting','noWall'))
    assert not cfg['vision'] and not cfg['localEnemies']
    assert raw['denseFixture']['version']==w.FIXTURE and raw['denseFixture']['enemyWeapon']=='smg10'
    assert raw['driver']['forcedPositionCalls']==0 and motion['spawn']['calls']==1
    assert motion['warmup']['ready'] and motion['warmup']['roundTrips']>=1 and motion['warmup']['groundContactRun']>=10
    assert motion['timingStart']['floorContact'] and motion['route']['terrainVerified']
    assert (raw['world']['width'],raw['world']['height'],raw['world']['layoutSeed'])==(240,125,20261019)
    assert raw['viewport']['zoom']==1
    previous=raw['continuousSampling']['startedAtMs']; values=[];rows=[]
    for index,row in enumerate(raw['samples']):
        assert row['name']=='dense-native-'+str(index)
        assert row['empty']==row['misses']==0 and row['playerShotFrames']>0 and row['enemyShotFrames']>0
        old.six_smg10(row['encounter'])
        for sample in row['combatWindows']:old.six_smg10(sample['encounter'])
        assert len(row['continuousFramesMs'])==len(row['sampleAtMs'])==300
        for t,dt in zip(row['sampleAtMs'],row['continuousFramesMs']):
            assert t-previous==dt and dt>=0;previous=t;values.append(dt)
        rows.append({'index':index,'continuous':base.metrics(row['continuousFramesMs']),
                     'workload':dense.workload(row,motion['route']),'encounter':row['encounter'],
                     'playerShots':row['playerShotFrames'],'enemyShots':row['enemyShotFrames'],
                     'activity':row['activity'],'activityEnd':row['activityEnd']})
    end=raw['activityReleaseEnd']
    assert end['nativeIdentityVerified'] and len(end['identities'])==6 and all(x['same'] for x in end['identities'])
    assert end['unknownObjectsRejected'] and end['startedAtMs']>=previous
    assert end['positive']==sum(bool(u['mayRest']) for u in end['units'])
    assert end['released']==sum(bool(u['record'] and u['record']['released']) for u in end['units'])
    qualification=dict(actualSprint=sum(x['workload']['aboveWalkSpeedFrames'] for x in rows)>=30,
        concurrentFixtureBullets=any(v>=3 for row in raw['samples'] for v in row['denseFrames']['fixtureBullets']),
        observedNativePlayerBullets=any(v>0 for row in raw['samples'] for v in row['denseFrames']['playerBullets']))
    assert all(qualification.values())
    return dict(version=VERSION,complete=True,passed=True,checks=26,continuous=base.metrics(values),rows=rows,
                activityReleaseEnd=end,nativeIdentityVerified=True,lifecycleVerified=False,
                qualification=qualification,nativePredicatePositive=end['positive']>0,
                performanceAcceptance=False,gameplayAcceptance=False,deployed=False,
                limits=['One candidate run has no paired baseline; no optimization claim.',
                        'Idle predicate is read only after final timing; this does not prove safe release/re-alarm, pending reports or wake lifecycle.'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',required=True)
    parser.add_argument('--registry-wait',type=int,default=600);args=parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name)
    folder=r.E/args.name;assert not folder.exists()
    options=old.options(args.name);assert options[-2:]==['--draw-control','atlas'];options[-1]='rcnative'
    record=dict(version=VERSION,options=options,deployed=False,performanceEligible=False)
    with m.Registration(owner='ContinuousScene / activity native identity / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=folder,resource='game',wait=args.registry_wait) as lease:
        try:
            assert not m.air_pids();control.memory_gate()
            product=candidate();baseline=r.baseline()
            assert baseline==product['productionSHA256']
            scripts,compiler,fixture,runtime=runner_inputs(),support.compiler_inputs(),fixture_inputs(),w.runtime_inputs()
            record.update(baseline=baseline,runnerInputs=scripts,compilerInputs=compiler,fixtureInputs=fixture,
                          runtimeInputs=runtime,candidateBuild=str(BUILD),candidateBuildSHA256=r.sha(BUILD))
            probe_path=compile_probe(lease,baseline,scripts,compiler,fixture)
            probe=base.verify_probe(probe_path,baseline,scripts,compiler,fixture)
            m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)
            for path,name in PRODUCTS.items():shutil.copy2(BUILD.parent/name,m.RUNTIME/path)
            expected=dict(baseline,**{path:product['artifacts'][name] for path,name in PRODUCTS.items()})
            for path,sha in expected.items():
                if path not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/path)==sha,path
            control.memory_gate();record.update(probeBuildPath=str(probe_path),probeSHA256=probe['probeSHA256'])
            try:m.run_owned(m.parse_args(options),lease)
            finally:
                if folder.exists():r.save(folder/'probe-build.json',probe);r.save(folder/'runner-inputs.json',record)
            assert baseline==r.baseline() and scripts==runner_inputs() and runtime==w.runtime_inputs()
            assert compiler==support.compiler_inputs() and fixture==fixture_inputs()
            raw,actual=w.read_retained_result(folder)
            for path,sha in expected.items():
                if path not in ('application.xml','mods/loader-manifest.txt'):assert actual[path]==sha,path
            assert actual[base.PROBE_PATH]==probe['probeSHA256']
            result=summary(raw);result.update(inputsUnchanged=True,resultSHA256=r.sha(folder/'storage/result.json'))
            r.save(folder/'summary.json',result)
            lease.outcome='passed';lease.note='Candidate loads with native class identity/read checks; lifecycle/performance not accepted'
            print(json.dumps({k:result[k] for k in ('passed','continuous','nativeIdentityVerified','lifecycleVerified')}),flush=True)
        except BaseException as error:
            folder.mkdir(parents=True,exist_ok=True)
            r.save(folder/'runner-failure.json',dict(record,error=repr(error),traceback=traceback.format_exc()))
            lease.outcome='failed';lease.note=repr(error);raise


shared.HERE,shared.VERSION=HERE,VERSION
shared.runner_inputs,shared.fixture_inputs=runner_inputs,fixture_inputs
base.OUT=HERE/'probe-builds'
base.runner_inputs,base.candidate_inputs=runner_inputs,fixture_inputs
if __name__=='__main__':main()
