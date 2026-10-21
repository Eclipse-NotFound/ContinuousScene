"""Registered native crop tests against frozen candidate and current dependencies."""
from pathlib import Path
import argparse, importlib.util, shutil, statistics, json
B=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('native_crop_release_helpers',B/'enemy-release.py');m=r.motion
OUT=B/'generated/native-crop-20261021'
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True)
    p.add_argument('--mode',choices=['pixels','combat','native','normal','visual','warm'],default='pixels')
    p.add_argument('--effects',choices=['off','full'],default='off');p.add_argument('--land',default='random_mane')
    p.add_argument('--installed',action='store_true');p.add_argument('--compile-probe',action='store_true');a=p.parse_args()
    with m.Registration(owner='ContinuousScene / native crop / 01a13816',purpose=a.name,run_dir=m.RUNTIME,evidence=r.E/a.name,wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline()
        if a.compile_probe:
            e=load('native_crop_test_compiler',B/'enemy-speed.py')
            e.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
        m.prepare();shutil.copy2(OUT/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        if not a.installed:shutil.copy2(OUT/'pfe.swf',m.RUNTIME/'pfe.swf')
        options=['--name',a.name,'--high-qos','--land',a.land,'--window-width','2048','--window-height','1123']
        if a.mode=='pixels':options+=['--presentation-check','--draw-control','nativecrop','--expect-no-signs']
        elif a.mode=='native':options+=['--suite','native']
        elif a.mode=='visual':options+=['--visual','--expect-no-signs']
        elif a.mode=='warm':options+=['--raster-check','--expect-no-signs','--short','--speed','24']
        else:
            options+=['--encounter','--fixed-enemies','--benchmark','normal' if a.mode=='normal' else 'scene','--speed','24','--short','--expect-no-signs']
            if a.mode=='combat':options+=['--draw-control','nativecrop']
        options+=['--no-lighting','--no-wall'] if a.effects=='off' else ['--vision']
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(a.name)
        assert r.baseline()==baseline,'Production dependency drift'
        for path,digest in baseline.items():
            if path not in ('pfe.swf','application.xml','mods/loader-manifest.txt'):
                assert inputs[path]==digest,('Test dependency drift',path)
        summary=dict(name=a.name,mode=a.mode,effects=a.effects,checks=len(result['assertions']),host=inputs['pfe.swf'])
        if a.mode in ('combat','normal'):
            assert r.read(r.E/a.name/'process-policy.json')['performanceEligible']
            summary['samples']=[]
            for row in result['samples']:
                f=row['frames'];assert len(f)==300 and row['empty']==0
                summary['samples'].append(dict(name=row['name'],median=statistics.median(f),mean=statistics.mean(f),p95=sorted(f)[284],maximum=max(f),over100=sum(v>100 for v in f),
                    scriptMean=statistics.mean(row['totalScript']),nativeMean=statistics.mean(row['nativeBand']),presentation=row.get('presentation'),shots=row.get('encounter'),empty=row['empty'],misses=row['misses']))
        r.save(OUT/(a.name+'-summary.json'),summary);print(json.dumps(summary),flush=True)
        lease.outcome='passed';lease.note='Requested assertions completed; not a deployment or general performance acceptance'
if __name__=='__main__':main()
