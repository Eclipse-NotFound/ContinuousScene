"""Separate ARGB-copy verification from same-scene repeat-copy ABBA timing."""
from pathlib import Path
import importlib.util,argparse,shutil,statistics,json
B=Path(__file__).resolve().parent;OUT=B/'generated/unit-blit-20261022'
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('unit_blit_run_helpers',B/'enemy-release.py');m=r.motion
def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--verify',action='store_true');p.add_argument('--compile-probe',action='store_true');a=p.parse_args()
    with m.Registration(owner='ContinuousScene / unit bitmap repeat / 01a13816',purpose=a.name,run_dir=m.RUNTIME,evidence=r.E/a.name,wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline();meta=r.read(OUT/'build.json');audit=r.read(OUT/'audit.json')
        assert baseline['pfe.swf']==meta['base'] and audit['passed']
        assert r.sha(OUT/'pfe.swf')==meta['candidate']==audit['candidateSHA256']
        assert r.sha(OUT/'audit.json')==meta['audit']
        if a.compile_probe:r.enemy.compile_as(B.parent/'src','ContinuousSceneProbeDoc.as',OUT/'ContinuousSceneProbe.swf')
        m.prepare();shutil.copy2(OUT/'pfe.swf',m.RUNTIME/'pfe.swf')
        shutil.copy2(OUT/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options=['--name',a.name,'--high-qos','--encounter','--fixed-enemies','--benchmark','scene','--speed','24','--short','--draw-control','unitblit','--window-width','2048','--window-height','1123','--no-lighting','--no-wall','--expect-no-signs']
        if a.verify:options+=['--blit-verify']
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(a.name);assert r.baseline()==baseline,'Production drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):assert inputs[path]==(meta['candidate'] if path=='pfe.swf' else digest),path
        assert r.read(r.E/a.name/'process-policy.json')['performanceEligible']!=a.verify
        assert len(result['samples'])==4
        summary=dict(name=a.name,pixelVerification=a.verify,diagnosticOnly=a.verify,deployed=False,checks=len(result['assertions']),p95Method='nearest-rank ceil(0.95*n)-1',samples=[])
        for phase,row in enumerate(result['samples']):
            f=row['frames'];assert len(f)==300 and row['empty']==0 and row['blit']['mismatches']==0
            blit=row['blit'];assert blit['enabled']==(phase in (1,2)) and blit['verify']==a.verify
            assert blit['calls']>0 and blit['repeats']>0
            assert blit['skipped']==(blit['repeats'] if phase in (1,2) else 0)
            assert blit['verified']==(blit['repeats'] if a.verify else 0)
            summary['samples'].append(dict(name=row['name'],median=statistics.median(f),mean=statistics.mean(f),p95=sorted(f)[284],maximum=max(f),over100=sum(x>100 for x in f),script=statistics.mean(row['totalScript']),native=statistics.mean(row['nativeBand']),blit=row['blit'],shots=row.get('encounter'),misses=row['misses']))
        r.save(OUT/(a.name+'-summary.json'),summary);print(json.dumps(summary),flush=True)
        lease.outcome='passed';lease.note='Pixel verification or isolated repeat-copy ABBA complete; not deployment approval'
if __name__=='__main__':main()
