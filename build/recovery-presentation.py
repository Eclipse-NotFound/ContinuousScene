"""Test existing cropped-tile prototype on restored host; never deploy it."""
from pathlib import Path
import importlib.util, shutil, statistics
B=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('recovery_presentation_helpers',B/'enemy-release.py')
r=importlib.util.module_from_spec(s);s.loader.exec_module(r);m=r.motion
OUT=B/'generated/recovery-presentation-20261021'

def main():
    OUT.mkdir(exist_ok=True)
    name='recovery-20261021-tilecrop-abba'
    with m.Registration(owner='ContinuousScene / restored-host presentation / 01a13816',
         purpose='Same-instance original/cropped/cropped/original full-population combat',
         run_dir=m.RUNTIME,evidence=OUT/'summary.json',wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline()
        assert baseline['pfe.swf']=='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
        m.prepare()
        shutil.copy2(B/'generated/impact-tests-20261021/ContinuousSceneProbe.swf',
                     m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        m.run_owned(m.parse_args(['--name',name,'--high-qos','--no-lighting','--no-wall',
            '--window-width','2048','--window-height','1123','--land','random_mane',
            '--encounter','--fixed-enemies','--benchmark','scene','--speed','24',
            '--draw-control','tilecrop','--short','--expect-no-signs']),lease)
        result,inputs=r.result(name)
        assert r.baseline()==baseline,'Production dependency drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):
                assert inputs[path]==digest,('Test dependency drift',path)
        assert r.read(r.E/name/'process-policy.json')['performanceEligible']
        samples=[]
        for row in result['samples']:
            f=row['frames'];assert len(f)==300 and row['empty']==0
            samples.append(dict(name=row['name'],median=statistics.median(f),mean=statistics.mean(f),
                p95=sorted(f)[284],maximum=max(f),over100=sum(v>100 for v in f),
                nativeMean=statistics.mean(row['nativeBand']),scriptMean=statistics.mean(row['totalScript']),
                presentation=row.get('presentation'),shots=row.get('encounter'),
                empty=row['empty'],misses=row['misses']))
        summary=dict(status='completed',deployed=False,name=name,samples=samples,
            limitation='Same scene and movement; evolving combat and cache warm-up. Pixel/compatibility gate required before any deployment.')
        r.save(OUT/'summary.json',summary);print(__import__('json').dumps(summary),flush=True)
        lease.outcome='passed';lease.note='Prototype comparison complete; no installation or performance acceptance implied'
if __name__=='__main__':main()
