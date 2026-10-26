"""Independent native-renderer identity, descriptor and interval review."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_renderer_audit',HERE.parent/'camera-stage3d-wholeworld-settle-20261027/verify_runs.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


def review(mode):
    name='camera-native-'+mode+'-20261027-r1';folder=base.E/name
    rec=base.read(folder/'runner-inputs.json');build=base.read(folder/'probe-build.json')
    raw=base.read(folder/'storage/result.json');summary=base.read(folder/'summary.json')
    actual={k.replace('\\','/'):v for k,v in base.read(folder/'inputs.json').items()}
    policy=base.read(folder/'process-policy.json');loader=base.read(folder/'loader-check.json')
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for group in ('baseline','runtimeInputs'):
        for path,digest in rec[group].items():assert base.sha(base.ROOT/path)==digest,(mode,group,path)
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for path,digest in rec[group].items():assert base.sha(Path(path))==digest,(mode,group,path)
    source=Path(build['frozenSourcePath']);assert len(build['frozenSourceSHA256'])==86
    for path,digest in build['frozenSourceSHA256'].items():assert base.sha(source/path)==digest,path
    assert base.sha(Path(build['probePath']))==build['probeSHA256']==rec['probeSHA256']
    assert base.sha(Path(build['sourceOrigin']))==build['sourceOriginSHA256']
    assert base.sha(Path(build['configPath']))==build['configSHA256']
    for key,digest in rec['baseline'].items():
        if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    assert actual['application.xml']==rec['runtimeDescriptor']['duringSHA256']
    assert rec['runtimeDescriptor']['restored']
    assert base.sha(HERE.parents[2]/'build/runtime/application.xml')==rec['runtimeDescriptor']['beforeSHA256']
    descriptor=base.read(folder/'launch-descriptor.json')
    assert descriptor==rec['launchDescriptor']
    data=descriptor['text'].replace('\r\n','\n').replace('\n','\r\n').encode('utf-8')
    assert hashlib.sha256(data).hexdigest().upper()==descriptor['sha256']
    doc=ET.fromstring(descriptor['text']);ns={'a':doc.tag.split('}')[0][1:]}
    app_id=doc.findtext('a:id',namespaces=ns)
    assert re.fullmatch(r'pfe-modsettings-continuous-motion-[0-9a-f]{32}',app_id)
    assert doc.findtext('a:initialWindow/a:renderMode',namespaces=ns)==mode
    assert doc.find('a:initialWindow/a:depthAndStencil',ns) is None
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert rec['memoryBeforeAir']['availableCommit']>=4*1024**3 and rec['memoryBeforeAir']['availablePhysical']>=2*1024**3
    t=raw['cameraRaster'];clean=t['cleanup']
    assert raw['ok'] and raw['error'] is None and t['complete'] and t['passed'] and not t['errors']
    assert t['airRenderMode']==mode and t['windowPixelsNotCaptured']
    assert all(x['className']!='visMainMenu' for x in t['nativeMenuChildren'])
    assert t['stage']['width']==1280 and t['stage']['height']==720 and t['testZoom']==1
    assert clean==raw['cameraRasterCleanup'] and clean['restored'] and not clean['errors'] and clean['pendingOwnedBitmaps']==0
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==10
    assert len(t['pixels'])==5 and all(p['nativeRepeat']['equal'] and p['nativeRepeat']['differentPixels']==0 for p in t['pixels'])
    assert t['zeroRasterWork'] and all(x==0 for x in t['timingRasterDelta'].values())
    assert len(t['windows'])==8 and len(t['framesMs'])==960
    clock=t['timingStartAtMs'];deltas=[];stamps=[]
    for row,condition in zip(t['windows'],(0,1,2,3,3,2,1,0)):
        assert row['condition']==condition and row['startAtMs']==clock and len(row['framesMs'])==120
        assert all(row['worldVisible']) and all(row['windowVisible']) and not row['hidden']
        assert all(p==t['timingStart']['gg'] for p in row['gg'])
        xs,ys=set(row['vx']),set(row['vy'])
        assert (len(xs)>1)==(condition in (1,3)) and (len(ys)>1)==(condition in (2,3))
        for stamp,interval in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-clock==interval and interval>=0
            clock=stamp;stamps.append(stamp);deltas.append(interval)
        assert row['endAtMs']==clock
    assert deltas==t['framesMs'] and stamps==t['sampleAtMs']
    assert clock==t['timingEndAtMs'] and sum(deltas)==t['timingElapsedMs']==clock-t['timingStartAtMs']
    arms={name:base.metric([x for row in t['windows'] if row['mode']==name for x in row['framesMs']])
        for name in ('native-static','native-horizontal','native-vertical','native-combined')}
    return dict(name=name,mode=mode,inputIntegrity=True,resultSHA256=base.sha(folder/'storage/result.json'),
        probeSHA256=build['probeSHA256'],source=source.parent.name,pid=policy['pid'],appId=app_id,
        frames=960,arms=arms,roomAxis=t['roomAxis'],stage=t['stage'],world=raw['world'],player=t['initial']['gg'],
        descriptorRestored=True,actualWindowMode=t['airRenderMode'],windowPixelsNotCaptured=True),t,rec


def main():
    direct,dt,dr=review('direct');gpu,gt,gr=review('gpu')
    assert direct['probeSHA256']==gpu['probeSHA256'] and direct['source']==gpu['source']
    for key in ('baseline','runtimeInputs','runnerInputs','compilerInputs','fixtureInputs'):
        assert dr[key]==gr[key],key
    assert direct['appId']!=gpu['appId'] and direct['roomAxis']==gpu['roomAxis'] and direct['stage']==gpu['stage']
    assert dt['route']==gt['route']
    for d,g in zip(dt['windows'],gt['windows']):
        assert d['vx']==g['vx'] and d['vy']==g['vy'],'Camera paths differ'
    changes={name:gpu['arms'][name]['mean']-direct['arms'][name]['mean'] for name in direct['arms']}
    result=dict(runs=[direct,gpu],cameraPathsIdentical=True,meanDeltaMs=changes,
        sameWorldSummary=direct['world']==gpu['world'],sameInitialPlayer=direct['player']==gpu['player'],
        diagnosticOnly=True,deployed=False,visualAcceptance=False,
        limits=['Distinct runs with active Flash timelines; not identical live visual state or real gameplay.',
                'Software BitmapData.draw stability is not GPU-window pixel equality; filters may be omitted.'])
    path=HERE/'pair-review.json';assert not path.exists()
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(arms={r['mode']:r['arms'] for r in result['runs']},meanDeltaMs=changes,
        sameWorldSummary=result['sameWorldSummary'],sameInitialPlayer=result['sameInitialPlayer'])))


if __name__=='__main__':main()
