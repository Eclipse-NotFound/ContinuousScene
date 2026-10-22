"""Isolated branch attribution; never use instrumented frame times as acceptance."""
from pathlib import Path
import importlib.util, argparse, shutil, json, statistics
B=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('bullet_segments_run_helpers',B/'enemy-release.py');m=r.motion
OUT=B/'generated/bullet-segments-20261021'
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--normal',action='store_true')
    p.add_argument('--stable-motion',action='store_true');p.add_argument('--player-fire',action='store_true')
    p.add_argument('--combat-route',action='store_true')
    p.add_argument('--combat-route-length',type=int,choices=[100,200,400],default=400)
    p.add_argument('--compile-probe',action='store_true');a=p.parse_args()
    if a.player_fire and not a.stable_motion:p.error('--player-fire requires --stable-motion')
    if a.combat_route and not (a.stable_motion and a.player_fire):p.error('--combat-route requires --stable-motion and --player-fire')
    with m.Registration(owner='ContinuousScene / direct bullet attribution / 01a13816',purpose=a.name,run_dir=m.RUNTIME,evidence=r.E/a.name,wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline();assert baseline['pfe.swf']=='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
        build=r.read(OUT/'build.json');audit=r.read(OUT/'semantic-audit.json');timer_audit=r.read(OUT/'timer-binding-audit.json')
        assert build['compiled'] and build['diagnosticOnly'] and not build['performanceEligible']
        assert audit['passed'] and audit['actualChangedBodies']==['fe.weapon.Bullet::0:1:run']
        assert r.sha(OUT/'pfe.swf')==build['candidate']==audit['candidateSHA256']==timer_audit['candidateSHA256']=='B8C54CB07CFADC1EA7965F036104659E7D19DD687C4A859CC059A8D0DE6E3710'
        assert r.sha(OUT/'pfe.xml')==build['candidateXml']==audit['candidateXMLSHA256']==timer_audit['candidateXMLSHA256']
        assert r.sha(OUT/'semantic-audit.json')==build['audit']
        assert timer_audit['passed'] and timer_audit['actualChangedBodies']==['fe.weapon.Bullet::0:1:run']
        assert timer_audit['timerBinding']['allCallsDirectQualified'] and timer_audit['timerBinding']['callCount']==9
        for field,script in [('auditImplementationSHA256','bullet-segments-audit.py'),('auditSupportSHA256','stationary-threat-audit.py'),('semanticComparatorSHA256','native-crop-audit.py')]:
            assert timer_audit[field]==r.sha(B/script),('Diagnostic audit implementation changed',script)
        source_hashes=lambda:{p.relative_to(B.parent/'src').as_posix():r.sha(p) for p in (B.parent/'src').rglob('*.as')}
        if a.compile_probe:
            before=source_hashes()
            r.enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
            assert before==source_hashes(),'Probe source changed during compile'
            r.save(OUT/'probe-build.json',dict(sourceSHA256=before,probeSHA256=r.sha(OUT/'ContinuousSceneProbe.swf')))
        probe_build=r.read(OUT/'probe-build.json')
        assert probe_build['probeSHA256']==r.sha(OUT/'ContinuousSceneProbe.swf'),'Probe binary changed'
        assert probe_build['sourceSHA256']==source_hashes(),'Probe is stale; compile current reviewed sources'
        m.prepare();shutil.copy2(OUT/'pfe.swf',m.RUNTIME/'pfe.swf')
        shutil.copy2(OUT/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options=['--name',a.name,'--high-qos','--encounter','--fixed-enemies','--benchmark','normal' if a.normal else 'scene','--speed','24','--short','--bullet-segments','--window-width','2048','--window-height','1123','--no-lighting','--no-wall','--expect-no-signs']
        if a.stable_motion:options+=['--stable-motion']
        if a.player_fire:options+=['--player-fire']
        if a.combat_route:options+=['--combat-route','--combat-route-length',str(a.combat_route_length)]
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(a.name);assert r.baseline()==baseline,'Production drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):
                assert inputs[path]==(r.sha(OUT/'pfe.swf') if path=='pfe.swf' else digest),path
        assert not r.read(r.E/a.name/'process-policy.json')['performanceEligible']
        assert inputs['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==probe_build['probeSHA256']
        r.save(r.E/a.name/'probe-build.json',probe_build)
        if a.stable_motion:assert result['driver']['stableMotion']
        if a.player_fire:assert result['playerFire']['enabled'] and result['playerFire']['shotFrames']>30
        summary=dict(name=a.name,diagnosticOnly=True,performanceEligible=False,deployed=False,
                     checks=len(result['assertions']),driver=result.get('driver'),playerFire=result.get('playerFire'),
                     playerFireWarmup=result.get('playerFireWarmup'),combatRoute=result.get('combatRoute'),
                     path=result.get('path'),samples=[])
        for row in result['samples']:
            assert len(row['frames'])==300 and row['empty']==0
            stats=row.get('bulletSegments')
            assert stats and stats['version']=='bullet-segments-1' and stats['calls']>0,'No native Bullet segment samples'
            if a.player_fire:assert row['playerShotFrames']>0,('Player did not actually fire',row['name'])
            if a.combat_route:
                assert row['enemyShotFrames']>0 and row['encounter']['alive']==6 and row['encounter']['armed']==6
                windows=row['combatWindows'];assert len(windows)==20
                for wi in range(10):
                    pair=sorted((x for x in windows if x['frame']//30==wi),key=lambda x:x['frame'])
                    assert len(pair)==2 and [x['frame']%30 for x in pair]==[0,29]
                    assert all(x['encounter']['alive']==6 and x['encounter']['armed']==6 for x in pair)
                    assert pair[1]['encounter']['actualShotFrames']>pair[0]['encounter']['actualShotFrames'],('No actual enemy shot in measured 30-frame window',row['name'],wi)
                    assert pair[1]['playerShots']>pair[0]['playerShots'],('No actual player shot in measured 30-frame window',row['name'],wi)
            summary['samples'].append(dict(name=row['name'],frames=300,script=statistics.mean(row['totalScript']),
                native=statistics.mean(row['nativeBand']),bullet=stats,shots=row.get('encounter'),
                playerShotFrames=row.get('playerShotFrames'),enemyShotFrames=row.get('enemyShotFrames'),
                combatWindows=row.get('combatWindows'),misses=row['misses'],warmed=sum(row['warm'])))
        r.save(OUT/(a.name+'-summary.json'),summary)
        concise={k:v for k,v in summary.items() if k not in ('combatRoute','playerFireWarmup')}
        concise['samples']=[{k:v for k,v in row.items() if k not in ('shots','combatWindows')} for row in summary['samples']]
        print(json.dumps(concise),flush=True)
        lease.outcome='passed';lease.note='Diagnostic branch timings, not performance acceptance or deployment'
if __name__=='__main__':main()
