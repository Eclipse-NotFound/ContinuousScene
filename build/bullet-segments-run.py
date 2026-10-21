"""Isolated branch attribution; never use instrumented frame times as acceptance."""
from pathlib import Path
import importlib.util, argparse, shutil, json, statistics
B=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('bullet_segments_run_helpers',B/'enemy-release.py');m=r.motion
OUT=B/'generated/bullet-segments-20261021'
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--normal',action='store_true');p.add_argument('--compile-probe',action='store_true');a=p.parse_args()
    with m.Registration(owner='ContinuousScene / direct bullet attribution / 01a13816',purpose=a.name,run_dir=m.RUNTIME,evidence=r.E/a.name,wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline();assert baseline['pfe.swf']=='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
        build=r.read(OUT/'build.json');audit=r.read(OUT/'semantic-audit.json')
        assert build['compiled'] and build['diagnosticOnly'] and not build['performanceEligible']
        assert audit['passed'] and audit['actualChangedBodies']==['fe.weapon.Bullet::0:1:run']
        assert r.sha(OUT/'pfe.swf')==build['candidate']==audit['candidateSHA256']
        assert r.sha(OUT/'pfe.xml')==build['candidateXml']==audit['candidateXMLSHA256']
        assert r.sha(OUT/'semantic-audit.json')==build['audit']
        if a.compile_probe:r.enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
        m.prepare();shutil.copy2(OUT/'pfe.swf',m.RUNTIME/'pfe.swf')
        shutil.copy2(OUT/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options=['--name',a.name,'--high-qos','--encounter','--fixed-enemies','--benchmark','normal' if a.normal else 'scene','--speed','24','--short','--bullet-segments','--window-width','2048','--window-height','1123','--no-lighting','--no-wall','--expect-no-signs']
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(a.name);assert r.baseline()==baseline,'Production drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):
                assert inputs[path]==(r.sha(OUT/'pfe.swf') if path=='pfe.swf' else digest),path
        assert not r.read(r.E/a.name/'process-policy.json')['performanceEligible']
        summary=dict(name=a.name,diagnosticOnly=True,checks=len(result['assertions']),samples=[])
        for row in result['samples']:
            assert len(row['frames'])==300 and row['empty']==0
            summary['samples'].append(dict(name=row['name'],frames=300,script=statistics.mean(row['totalScript']),native=statistics.mean(row['nativeBand']),bullet=row.get('bulletSegments'),shots=row.get('encounter'),misses=row['misses']))
        r.save(OUT/(a.name+'-summary.json'),summary);print(json.dumps(summary),flush=True)
        lease.outcome='passed';lease.note='Diagnostic branch timings, not performance acceptance or deployment'
if __name__=='__main__':main()
