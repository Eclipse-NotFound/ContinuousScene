"""Isolated, manifest-frozen scheduler observations. Never deploys."""
from pathlib import Path
import argparse, importlib.util, json, shutil
B=Path(__file__).resolve().parent
OUT=B/'generated/activity-telemetry-20261022'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
r=load('activity_telemetry_helpers',B/'enemy-release.py');m=r.motion

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True)
    parser.add_argument('--compile',action='store_true');parser.add_argument('--compile-probe',action='store_true')
    parser.add_argument('--registry-wait',type=int,default=600)
    args=parser.parse_args()
    with m.Registration(owner='ContinuousScene / activity telemetry / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=r.E/args.name,wait=args.registry_wait) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline();source=r.read(OUT/'source-provenance.json')
        assert baseline['pfe.swf']==source['host'] and baseline['mods/ContinuousScene/release/ContinuousSceneMod.swf']==source['baseline']
        assert source['diagnosticOnly'] and source['reverseInsertionCheck'] and source['changed']==['NativeSceneActivity.as']
        assert r.sha(B/'activity-telemetry-build.py')==source['builderSHA256']
        for name in source['sourceClosure']:
            assert r.sha(OUT/'original-source'/name)==source['before'][name]
            assert r.sha(OUT/'source'/name)==source['after'][name]
        assert {p.name for p in (OUT/'source').glob('*.as')}==set(source['sourceClosure'])
        if args.compile:
            r.enemy.compile_as(OUT/'source','ContinuousSceneDoc.as',OUT/'ContinuousSceneMod.swf')
            for name in source['sourceClosure']:assert r.sha(OUT/'source'/name)==source['after'][name]
            r.save(OUT/'build.json',dict(diagnosticOnly=True,deployed=False,
                sourceProvenanceSHA256=r.sha(OUT/'source-provenance.json'),candidateSHA256=r.sha(OUT/'ContinuousSceneMod.swf')))
        build=r.read(OUT/'build.json')
        assert build['diagnosticOnly'] and not build['deployed']
        assert build['sourceProvenanceSHA256']==r.sha(OUT/'source-provenance.json')
        assert build['candidateSHA256']==r.sha(OUT/'ContinuousSceneMod.swf')
        probe_dir=OUT
        hashes=lambda:{p.relative_to(B.parent/'src').as_posix():r.sha(p) for p in (B.parent/'src').rglob('*.as')}
        if args.compile_probe:
            before=hashes()
            r.enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',probe_dir/'ContinuousSceneProbe.swf')
            assert before==hashes(),'Probe source changed during build'
            r.save(probe_dir/'probe-build.json',dict(sourceSHA256=before,probeSHA256=r.sha(probe_dir/'ContinuousSceneProbe.swf')))
        probe=r.read(probe_dir/'probe-build.json')
        assert probe['probeSHA256']==r.sha(probe_dir/'ContinuousSceneProbe.swf')
        assert probe['sourceSHA256']==hashes()
        m.prepare()
        shutil.copy2(OUT/'ContinuousSceneMod.swf',m.RUNTIME/'mods/ContinuousScene/release/ContinuousSceneMod.swf')
        shutil.copy2(probe_dir/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options=['--name',args.name,'--high-qos','--activity-telemetry','--encounter','--fixed-enemies',
                 '--benchmark','scene','--speed','4','--short','--window-width','2048','--window-height','1123',
                 '--no-lighting','--no-wall','--expect-no-signs','--stable-motion','--player-fire',
                 '--combat-route','--combat-route-length','200']
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(args.name);assert r.baseline()==baseline,'Production drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):
                assert inputs[path]==(build['candidateSHA256'] if path=='mods/ContinuousScene/release/ContinuousSceneMod.swf' else digest),path
        assert inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==probe['probeSHA256']
        assert not r.read(r.E/args.name/'process-policy.json')['performanceEligible']
        summary=dict(name=args.name,diagnosticOnly=True,deployed=False,checks=len(result['assertions']),samples=[])
        assert len(result['samples'])==4
        for row in result['samples']:
            assert len(row['frames'])==300 and row['empty']==0 and row['misses']==0
            assert row['playerShotFrames']>0 and row['enemyShotFrames']>0
            assert row['encounter']['alive']==6 and row['encounter']['armed']==6
            observations=row['activity'];assert len(observations)==10
            observations=observations+[row['activityEnd']]
            for item in observations:
                assert item['version']=='activity-telemetry-1' and item['telemetry']['errors']==0
                current=item['telemetry']['current']
                assert current['baseActive']+current['threatActive']+current['graceActive']==item['awake']
                for peak in item['telemetry']['interval']['maxima']:
                    assert peak['baseActive']+peak['threatActive']+peak['graceActive']==peak['awake']
            summary['samples'].append(dict(name=row['name'],playerShots=row['playerShotFrames'],enemyShots=row['enemyShotFrames'],
                maxAwake=max(x['telemetry']['interval']['maxAwake'] for x in observations),observations=observations,
                activityStart=row['activityStart'],activityCensus=row['activityCensus']))
        r.save(r.E/args.name/'source-provenance.json',source);r.save(r.E/args.name/'probe-build.json',probe)
        r.save(OUT/(args.name+'-summary.json'),summary)
        print(json.dumps(dict(name=args.name,samples=[{k:v for k,v in x.items() if k not in ('observations','activityCensus')} for x in summary['samples']])),flush=True)
        lease.outcome='passed';lease.note='Scheduler observations only; no frame-performance acceptance or deployment'

if __name__=='__main__':main()
