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
    p.add_argument('--mode',choices=['world','objects','objectgroups','effects','sleepclips','implicitpause','mousetree','shortlayers','compact','compactshort','fog','objectviewport','unitviewport','bulletblend','playercache'],required=True)
    p.add_argument('--pixels',action='store_true')
    p.add_argument('--stable-motion',action='store_true');p.add_argument('--player-fire',action='store_true')
    p.add_argument('--combat-route',action='store_true')
    p.add_argument('--combat-route-length',type=int,choices=[100,200,400],default=400)
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
        assert probe_build['sourceSHA256']=={p.relative_to(B.parent/'src').as_posix():r.sha(p) for p in (B.parent/'src').rglob('*.as')},'Probe is stale; compile current reviewed sources'
        m.prepare();shutil.copy2(OUT/'ContinuousSceneProbe.swf',m.RUNTIME/'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf')
        options=['--name',a.name,'--high-qos','--encounter','--fixed-enemies','--benchmark','scene','--speed','24','--short','--draw-control',a.mode,'--window-width','2048','--window-height','1123','--no-lighting','--no-wall','--expect-no-signs']
        if a.pixels:options+=['--presentation-check']
        if a.stable_motion:options+=['--stable-motion']
        if a.player_fire:options+=['--player-fire']
        if a.combat_route:options+=['--combat-route','--combat-route-length',str(a.combat_route_length)]
        m.run_owned(m.parse_args(options),lease)
        result,inputs=r.result(a.name);assert r.baseline()==baseline,'Production drift'
        for path,digest in baseline.items():
            if path not in ('application.xml','mods/loader-manifest.txt'):assert inputs[path]==digest,path
        if a.mode not in ('objectviewport','compact','compactshort') or a.pixels:assert not r.read(r.E/a.name/'process-policy.json')['performanceEligible']
        r.save(r.E/a.name/'probe-build.json',probe_build)
        summary=dict(name=a.name,mode=a.mode,diagnosticOnly=True,deployed=False,checks=len(result['assertions']),sleepingTimelines=result.get('sleepingTimelines'),driver=result.get('driver'),playerFire=result.get('playerFire'),playerFireWarmup=result.get('playerFireWarmup'),samples=[])
        summary['combatRoute']=result.get('combatRoute')
        for row in result.get('samples',[]):
            f=row['frames'];assert len(f)==300 and row['empty']==0
            if a.combat_route:
                assert row['enemyShotFrames']>0 and row['encounter']['alive']==6 and row['encounter']['armed']==6
                for wi in range(10):
                    pair=[x for x in row['combatWindows'] if x['frame']//30==wi]
                    assert len(pair)==2 and all(x['encounter']['alive']==6 and x['encounter']['armed']==6 for x in pair)
                    assert pair[1]['encounter']['actualShotFrames']>pair[0]['encounter']['actualShotFrames'],('No actual enemy shot in measured 30-frame window',row['name'],wi)
            summary['samples'].append(dict(name=row['name'],frames=300,median=statistics.median(f),mean=statistics.mean(f),p95=sorted(f)[284],maximum=max(f),over100=sum(x>100 for x in f),script=statistics.mean(row['totalScript']),native=statistics.mean(row['nativeBand']),shots=row.get('encounter'),presentation=row.get('presentation'),misses=row['misses']))
            if row.get('implicitHeld'):summary['samples'][-1]['meanImplicitHeld']=statistics.mean(row['implicitHeld'])
            if row.get('mouseTree'):summary['samples'][-1]['mouseTree']=row['mouseTree']
            if 'compactImpacts' in row:summary['samples'][-1]['compactImpacts']=row['compactImpacts']
            if 'playerShotFrames' in row:summary['samples'][-1]['playerShotFrames']=row['playerShotFrames']
        if a.mode=='shortlayers':
            ds=result['displaySummary'];frames=result['displayFrames']
            assert ds['complete'] and ds['cleanup']['restored'] and not ds['aborted'] and len(frames)==1500
            assert result['displayEmpty']==0 and result['displayMisses']==0
            summary['displaySummary']=ds;summary['displayGroups']={};summary['displayView']=result['displayView']
            summary['displayWindows']=[]
            for wi in range(50):
                window=[v for v in frames if v['window']==wi]
                assert len(window)==30 and len({v['control'] for v in window})==1
                assert sum('encounter' in v for v in window)==2
                assert all(v['encounter']['alive']==6 and v['encounter']['armed']==6 for v in window if 'encounter' in v)
                assert sum(v.get('enemyShots',0) for v in window)>0,('Enemies did not shoot in display window',wi)
                shots=sum(v['playerShot'] for v in window)
                if a.player_fire:assert shots>0,('Player did not shoot in display window',wi)
                summary['displayWindows'].append(dict(window=wi,control=window[0]['control'],playerShotFrames=shots,enemyShots=sum(v.get('enemyShots',0) for v in window),enemyTargets=sum(v.get('enemyTargets',0) for v in window),population=[v['encounter'] for v in window if 'encounter' in v]))
            for control in ('all','none','boxes','units','effects'):
                rows=[v for v in frames if v['control']==control and v['eligible']]
                assert len(rows)==290,(control,len(rows))
                dt=[v['dt'] for v in rows]
                summary['displayGroups'][control]=dict(frames=len(rows),median=statistics.median(dt),mean=statistics.mean(dt),p95=sorted(dt)[275],native=statistics.mean(v['currentNativeBand'] for v in rows),scriptBeforeProbe=statistics.mean(v['currentScriptBeforeProbe'] for v in rows),residualNotRenderCPU=statistics.mean(v['dt']-v['currentScriptBeforeProbe'] for v in rows),playerShotFrames=sum(v['playerShot'] for v in rows),enemyShots=sum(v.get('enemyShots',0) for v in rows))
            if a.player_fire:assert result['playerFire']['shotFrames']>30
        if a.mode=='compactshort':
            data=result['compactShort'];assert len(data['frames'])==800 and data['empty']==0 and data['misses']==0
            summary['compactWindows']=[]
            for wi,enabled in enumerate(data['order']):
                rows=[x for x in data['frames'] if x['window']==wi and not x['transition']]
                assert len(rows)==99 and all(x['compact']==enabled for x in rows)
                window=[x for x in data['frames'] if x['window']==wi]
                assert sum('encounter' in x for x in window)==2
                assert all(x['encounter']['alive']==6 and x['encounter']['armed']==6 for x in window if 'encounter' in x)
                assert sum(x.get('enemyShots',0) for x in rows)>0,('Enemies did not shoot in compact window',wi)
                if a.player_fire:assert sum(x['playerShot'] for x in rows)>0,('Player did not shoot in compact window',wi)
                dt=[x['dt'] for x in rows]
                summary['compactWindows'].append(dict(window=wi,enabled=enabled,median=statistics.median(dt),mean=statistics.mean(dt),p95=sorted(dt)[94],native=statistics.mean(x['native'] for x in rows),scriptBeforeProbe=statistics.mean(x['scriptBeforeProbe'] for x in rows),playerShotFrames=sum(x['playerShot'] for x in rows),enemyShots=sum(x.get('enemyShots',0) for x in rows),enemyTargets=sum(x.get('enemyTargets',0) for x in rows),population=[x['encounter'] for x in window if 'encounter' in x]))
        if a.mode in ('bulletblend','playercache') and not a.pixels:
            key='bulletBlend' if a.mode=='bulletblend' else 'playerCache'
            data=result[key];assert len(data['frames'])==800 and data['empty']==0 and data['misses']==0
            assert result[key+'Cleanup']['valid'] and result[key+'Cleanup']['pendingRestore']==0
            summary['blendWindows']=[];summary['toggleKind']=a.mode;summary['warmed']=data['warmed'];summary['toggleCleanup']=result[key+'Cleanup']
            for wi,enabled in enumerate(data['order']):
                window=[x for x in data['frames'] if x['window']==wi]
                rows=[x for x in window if not x['transition']]
                assert len(rows)==99 and all(x['enabled']==enabled for x in rows)
                assert sum('encounter' in x for x in window)==2
                assert all(x['encounter']['alive']==6 and x['encounter']['armed']==6 for x in window if 'encounter' in x)
                assert sum(x.get('enemyShots',0) for x in rows)>0,('Enemies did not shoot in toggle window',wi)
                assert sum(x['playerShot'] for x in rows)>0,('Player did not shoot in toggle window',wi)
                dt=[x['dt'] for x in rows]
                summary['blendWindows'].append(dict(window=wi,enabled=enabled,median=statistics.median(dt),mean=statistics.mean(dt),p95=sorted(dt)[94],native=statistics.mean(x['native'] for x in rows),scriptBeforeProbe=statistics.mean(x['scriptBeforeProbe'] for x in rows),probeMs=sum(x.get('probeMs',0) for x in rows),playerShots=sum(x['playerShot'] for x in rows),enemyShots=sum(x.get('enemyShots',0) for x in rows),probe=data['windows'][wi]))
        if a.pixels:summary['presentation']=result.get('presentation')
        r.save(OUT/(a.name+'-summary.json'),summary)
        concise={k:v for k,v in summary.items() if k not in ('combatRoute','playerFireWarmup','displayWindows','sleepingTimelines')}
        for key in ('samples','compactWindows'):
            if key in concise:concise[key]=[{k:v for k,v in row.items() if k not in ('shots','population')} for row in concise[key]]
        print(json.dumps(concise),flush=True)
        lease.outcome='passed';lease.note='Isolated attribution only; not a performance acceptance or deployment'
if __name__=='__main__':main()
