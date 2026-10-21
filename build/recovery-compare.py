"""Frozen-dependency old/new/new/old combat comparison; never deploys.

Six native armed enemies replace random hostile population in isolated storage.
Layout/path equality is checked; AI random decisions still limit causal claims.
"""
from pathlib import Path
import importlib.util, json, shutil, statistics
B=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('recovery_compare_helpers',B/'enemy-release.py')
r=importlib.util.module_from_spec(s);s.loader.exec_module(r);m=r.motion
OUT=B/'generated/recovery-compare-20261021'
OLD=B/'backups/sats-20261021-154054/pfe.swf'
NEW=B/'generated/impact-native-20261021/pfe.swf'

def main():
    OUT.mkdir(exist_ok=True)
    expected='BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
    assert r.sha(OLD)==r.sha(r.ROOT/'pfe.swf')==expected
    assert r.sha(NEW)=='5432A3B9B6820A94AE15AC0A97B13C4EDC534D3DC6DBED12063E0FE47677B71D'
    with m.Registration(owner='ContinuousScene / regression comparison / 01a13816',
         purpose='Pre-afternoon vs withdrawn host, 6-enemy control, A/B/B/A',
         run_dir=m.RUNTIME,evidence=OUT/'comparison.json',wait=300) as lease:
        assert not m.air_pids(),'Other AIR present; untouched'
        baseline=r.baseline();results=[]
        for index,host in enumerate((OLD,NEW,NEW,OLD)):
            assert r.baseline()==baseline,'Production dependencies changed'
            m.prepare()
            shutil.copy2(B/'generated/impact-tests-20261021/ContinuousSceneProbe.swf',
                         m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
            shutil.copy2(host,m.RUNTIME/'pfe.swf')
            name='recovery-20261021-combat-'+str(index+1)
            m.run_owned(m.parse_args(['--name',name,'--high-qos','--no-lighting','--no-wall',
                '--window-width','2048','--window-height','1123','--land','random_mane',
                '--encounter','--fixed-enemies','--local-enemies','--benchmark','scene',
                '--speed','24','--short','--expect-no-signs']),lease)
            result,inputs=r.result(name)
            assert inputs['pfe.swf']==r.sha(host)
            for path,digest in baseline.items():
                if path not in ('pfe.swf','application.xml','mods/loader-manifest.txt'):
                    assert inputs[path]==digest,('Dependency drift',path)
            assert r.read(r.E/name/'process-policy.json')['performanceEligible']
            samples=[]
            for row in result['samples']:
                frames=row['frames'];assert len(frames)==300 and row['empty']==0
                samples.append(dict(name=row['name'],median=statistics.median(frames),
                    p95=sorted(frames)[284],maximum=max(frames),mean=statistics.mean(frames),
                    over50=sum(x>50 for x in frames),over100=sum(x>100 for x in frames),
                    misses=row.get('misses'),forced=row.get('forced'),shots=row.get('encounter'),
                    nativeMean=statistics.mean(row['nativeBand']),
                    scriptMean=statistics.mean(row['totalScript'])))
            item=dict(name=name,host=r.sha(host),world=result['world'],path=result['path'],
                viewport=result['viewport'],population=result['encounter'],samples=samples)
            results.append(item)
            r.save(OUT/'comparison.json',dict(status='running',results=results,
                  limitation='Controlled population/layout, not deterministic AI or battle state'))
            print(json.dumps(item),flush=True)
        assert r.baseline()==baseline,'Production dependency drift after comparison'
        geometry=[(x['world']['entryRoomTiles'],x['path'],x['viewport']) for x in results]
        matched=all(x==geometry[0] for x in geometry)
        r.save(OUT/'comparison.json',dict(status='completed',layoutPathViewportMatch=matched,
               results=results,baseline=baseline,
               limitation='Controlled population/layout, not deterministic AI or battle state'))
        lease.outcome='passed';lease.note='Four runs completed; regression attribution requires report interpretation'
if __name__=='__main__':main()
