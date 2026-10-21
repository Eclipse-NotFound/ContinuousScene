"""Formal-host display attribution; hidden visual phases are never acceptance."""
from pathlib import Path
import importlib.util, argparse, shutil, json, statistics
B=Path(__file__).resolve().parent

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('combat_display_helpers',B/'enemy-release.py');m=r.motion
OUT=B/'generated/combat-display-20261022'

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True)
    p.add_argument('--mode',choices=['world','objects','objectgroups','effects','sleepclips','implicitpause','mousetree','fog','objectviewport'],required=True)
    p.add_argument('--pixels',action='store_true')
    p.add_argument('--compile-probe',action='store_true');a=p.parse_args()
    OUT.mkdir(exist_ok=True)
    with m.Registration(owner='ContinuousScene / display attribution / 01a13816',purpose=a.name,run_dir=m.RUNTIME,evidence=r.E/a.name,wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline();assert baseline['pfe.swf']=='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
        if a.compile_probe:
            source_hashes={p.relative_to(B.parent/'src').as_posix():r.sha(p) for p in (B.parent/'src').rglob('*.as')}
            r.enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
            assert source_hashes=={p.relative_to(B.parent/'src').as_posix():r.sha(p) for p in (B.parent/'src').rglob('*.as')},'Probe source changed during compile'
            r.save(OUT/'probe-build.json',dict(sourceSHA256=source_hashes,probeSHA256=r.sha(OUT/'ContinuousSceneProbe.swf')))
        probe_build=r.read(OUT/'probe-build.json');assert probe_build['probeSHA256']==r.sha(OUT/'ContinuousSceneProbe.swf')
        m.prepare();shutil.copy2(OUT/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options=['--name',a.name,'--high-qos','--encounter','--fixed-enemies','--benchmark','scene','--speed','24','--short','--draw-control',a.mode,'--window-width','2048','--window-height','1123','--no-lighting','--no-wall','--expect-no-signs']
        if a.pixels:options+=['--presentation-check']
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(a.name);assert r.baseline()==baseline,'Production drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):assert inputs[path]==digest,path
        if a.mode!='objectviewport' or a.pixels:assert not r.read(r.E/a.name/'process-policy.json')['performanceEligible']
        r.save(r.E/a.name/'probe-build.json',probe_build)
        summary=dict(name=a.name,mode=a.mode,diagnosticOnly=True,deployed=False,checks=len(result['assertions']),sleepingTimelines=result.get('sleepingTimelines'),samples=[])
        for row in result.get('samples',[]):
            f=row['frames'];assert len(f)==300 and row['empty']==0
            summary['samples'].append(dict(name=row['name'],frames=300,median=statistics.median(f),mean=statistics.mean(f),p95=sorted(f)[284],maximum=max(f),over100=sum(x>100 for x in f),script=statistics.mean(row['totalScript']),native=statistics.mean(row['nativeBand']),shots=row.get('encounter'),presentation=row.get('presentation'),misses=row['misses']))
            if row.get('implicitHeld'):summary['samples'][-1]['meanImplicitHeld']=statistics.mean(row['implicitHeld'])
            if row.get('mouseTree'):summary['samples'][-1]['mouseTree']=row['mouseTree']
        r.save(OUT/(a.name+'-summary.json'),summary);print(json.dumps(summary),flush=True)
        lease.outcome='passed';lease.note='Hidden display attribution only; not a performance acceptance or deployment'
if __name__=='__main__':main()
