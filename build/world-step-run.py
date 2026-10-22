"""Registered continuous-combat attribution of an audited World.step host.

Profiling is never performance acceptance. Natural short reload pauses are
recorded, not suppressed by forcing AI. Each measured 300-frame segment must
include actual fire from both sides and retain all six armed fixture actors.
"""
from pathlib import Path
import argparse, importlib.util, json, shutil, statistics

B=Path(__file__).resolve().parent
OUT=B/'generated/world-step-profile-20261022'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

r=load('world_step_runner_helpers',B/'enemy-release.py');m=r.motion

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True)
    parser.add_argument('--compile-probe',action='store_true');parser.add_argument('--registry-wait',type=int,default=600);args=parser.parse_args()
    with m.Registration(owner='ContinuousScene / World step diagnosis / 01a13816',purpose=args.name,
            run_dir=m.RUNTIME,evidence=r.E/args.name,wait=args.registry_wait) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline()
        assert baseline['pfe.swf']=='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
        build=r.read(OUT/'build.json');audit=r.read(OUT/'semantic-audit.json')
        assert build['compiled'] and build['diagnosticOnly'] and not build['performanceEligible']
        assert audit['passed'] and audit['actualChangedBodies']==['fe.World::0:1:step']
        assert r.sha(OUT/'pfe.swf')==build['candidate']==audit['candidateSHA256']
        assert r.sha(OUT/'pfe.xml')==build['candidateXml']==audit['candidateXMLSHA256']
        assert r.sha(OUT/'semantic-audit.json')==build['audit']
        retention=r.read(OUT/'retained.audit.json')
        assert r.sha(OUT/'retained.audit.json')==build['retentionAudit']
        assert retention['rejectedImportedLayout']['rejected'] and not retention['rejectedImportedLayout']['importedClassCopied']
        assert retention['preservedOriginalLayout']['preserved'] and audit['preservedOriginalLayout']['preserved']
        assert retention['preservedOriginalLayout']['onlyCopiedBody']=='fe.World::0:1:step'
        assert audit['wrapperSHA256']==r.sha(B/'world-step-profile-audit.py')
        assert audit['sharedAuditSHA256']==r.sha(B/'bullet-segments-audit.py')
        assert all(r.sha(Path(path))==digest for path,digest in build['sourceInputs'].items())
        assert audit['timerBinding']['callCount']==22 and audit['timerBinding']['allCallsDirectQualified']
        source_hashes=lambda:{p.relative_to(B.parent/'src').as_posix():r.sha(p) for p in (B.parent/'src').rglob('*.as')}
        if args.compile_probe:
            before=source_hashes()
            r.enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
            assert before==source_hashes(),'Probe source changed during compile'
            r.save(OUT/'probe-build.json',dict(sourceSHA256=before,probeSHA256=r.sha(OUT/'ContinuousSceneProbe.swf')))
        probe=r.read(OUT/'probe-build.json')
        assert probe['sourceSHA256']==source_hashes() and probe['probeSHA256']==r.sha(OUT/'ContinuousSceneProbe.swf')
        m.prepare();shutil.copy2(OUT/'pfe.swf',m.RUNTIME/'pfe.swf')
        shutil.copy2(OUT/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options=['--name',args.name,'--high-qos','--encounter','--fixed-enemies','--benchmark','scene',
                 '--speed','4','--short','--world-profile','--window-width','2048','--window-height','1123',
                 '--no-lighting','--no-wall','--expect-no-signs','--stable-motion','--player-fire',
                 '--combat-route','--combat-route-length','200']
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(args.name);assert r.baseline()==baseline,'Production drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):
                assert inputs[path]==(r.sha(OUT/'pfe.swf') if path=='pfe.swf' else digest),path
        assert not r.read(r.E/args.name/'process-policy.json')['performanceEligible']
        assert inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==probe['probeSHA256']
        r.save(r.E/args.name/'probe-build.json',probe)
        summary=dict(name=args.name,diagnosticOnly=True,performanceEligible=False,deployed=False,
                     checks=len(result['assertions']),combatRoute=result['combatRoute'],
                     playerFireWarmup=result['playerFireWarmup'],samples=[])
        for row in result['samples']:
            assert len(row['frames'])==300 and row['empty']==0 and row['misses']==0
            stats=row['worldProfile']
            assert stats['version']=='world-step-profile-1' and stats['calls']==300
            assert stats['errorCalls']==0 and stats['earlyReturnCalls']==0
            for key in build['segments']:assert stats[key+'Calls']==300,(key,stats[key+'Calls'])
            assert row['enemyShotFrames']>0 and row['playerShotFrames']>0
            assert row['encounter']['alive']==6 and row['encounter']['armed']==6
            windows=[]
            for wi in range(10):
                pair=[x for x in row['combatWindows'] if x['frame']//30==wi]
                assert len(pair)==2 and all(x['encounter']['alive']==6 and x['encounter']['armed']==6 for x in pair)
                player=pair[1]['playerShots']-pair[0]['playerShots']
                enemy=pair[1]['encounter']['actualShotFrames']-pair[0]['encounter']['actualShotFrames']
                assert player>0
                windows.append(dict(window=wi,playerShots=player,enemyShots=enemy,population=pair))
            summary['samples'].append(dict(name=row['name'],frames=300,profile=stats,
                perFrame={key:stats[key+'Ms']/300 for key in build['segments']},
                totalMsPerFrame=stats['totalMs']/300,nativeBand=statistics.mean(row['nativeBand']),
                script=statistics.mean(row['totalScript']),playerShots=row['playerShotFrames'],
                enemyShots=row['enemyShotFrames'],warmed=sum(row['warm']),combatWindows=windows))
        r.save(OUT/(args.name+'-summary.json'),summary)
        print(json.dumps(dict(name=args.name,diagnosticOnly=True,samples=[{k:v for k,v in row.items() if k not in ('combatWindows','profile')} for row in summary['samples']])),flush=True)
        lease.outcome='passed';lease.note='World step diagnostic counters only; no frame-performance acceptance or deployment'

if __name__=='__main__':main()
