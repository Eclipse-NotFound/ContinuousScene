"""Audit the short item profile without promoting it to a frame-rate trial."""
from pathlib import Path
import importlib.util
import json
from collections import defaultdict

HERE = Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('item_profile_identity',HERE.parent/'camera-stage3d-wholeworld-settle-20261027/verify_runs.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
NAME='camera-stage3d-item-profile-20261027-r1'


def main():
    folder=base.E/NAME
    rec=base.read(folder/'runner-inputs.json');build=base.read(folder/'probe-build.json')
    raw=base.read(folder/'storage/result.json');policy=base.read(folder/'process-policy.json')
    loader=base.read(folder/'loader-check.json');summary=base.read(folder/'summary.json')
    actual={k.replace('\\','/'):v for k,v in base.read(folder/'inputs.json').items()}
    assert len(rec['baseline'])==526 and len(rec['runtimeInputs'])==13
    for group in ('baseline','runtimeInputs'):
        for path,digest in rec[group].items():assert base.sha(base.ROOT/path)==digest,(group,path)
    for group in ('runnerInputs','compilerInputs','fixtureInputs'):
        for path,digest in rec[group].items():assert base.sha(Path(path))==digest,(group,path)
    source=Path(build['frozenSourcePath']);assert len(build['frozenSourceSHA256'])==86
    for path,digest in build['frozenSourceSHA256'].items():assert base.sha(source/path)==digest,path
    assert base.sha(Path(build['probePath']))==build['probeSHA256']==rec['probeSHA256']
    assert base.sha(Path(build['sourceOrigin']))==build['sourceOriginSHA256']
    assert base.sha(Path(build['configPath']))==build['configSHA256']
    for key,digest in rec['baseline'].items():
        if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key
    assert actual['mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf']==build['probeSHA256']
    assert len(loader['sessions'])==1 and all(loader['loaded'].values())
    assert policy['desktopPolicy']=='private' and not policy['performanceEligible']
    assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort') and not policy.get('runFailure')
    assert rec['memoryBeforeAir']['availableCommit']>=4*1024**3 and rec['memoryBeforeAir']['availablePhysical']>=2*1024**3
    t=raw['cameraRaster'];clean=t['cleanup'];p=clean['presentation']
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    assert t['complete'] and t['passed'] and not t['errors'] and t['profileOnly']
    assert not t['framesMs'] and not t['sampleAtMs'] and not t['windows'] and t['measurementFrames']==0
    assert clean==raw['cameraRasterCleanup'] and clean['restored'] and not clean['errors']
    assert clean['pendingOwnedBitmaps']==0 and t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==260
    assert p['allocated']==p['disposed']==10 and p['texturesCreated']==p['texturesDisposed']==8
    assert p['contextCreates']==p['contextDisposals']==1 and p['gpuBytes']==0 and not p['active'] and not p['ready']
    assert p['clipsStopped']==p['clipsResumed'] and p['timelinesRestored'] and not p['timelineChanges']
    assert p['regionRasterCalls']==13 and p['copies']==22 and p['uploads']==21
    assert len(t['pixels'])==13 and len(t['nativeWarmups'])==18
    assert all(x['passed'] and all(v['pixels']['equal'] for v in x['checks']) for x in t['nativeWarmups'])
    assert all(x['restore']['equal'] and x['restore']['differentPixels']==0 for x in t['pixels'])
    assert summary['frames']==0 and summary['profileOnly'] and summary['items']==t['itemProfile']
    items=t['itemProfile'];groups=defaultdict(lambda:dict(count=0,drawMs=0,outsideGeometry=0,outsideDrawMs=0))
    for item in items:
        assert item['drawMs']>=0
        reason=item.get('cullReason') or {}
        key=(item['className'],reason.get('filter'),reason.get('mask',False),reason.get('scroll',False))
        row=groups[key];row['count']+=1;row['drawMs']+=item['drawMs']
        if not item['geometricIntersection']:
            row['outsideGeometry']+=1;row['outsideDrawMs']+=item['drawMs']
    rows=[dict(className=k[0],filter=k[1],mask=k[2],scroll=k[3],**v) for k,v in groups.items()]
    rows.sort(key=lambda x:x['drawMs'],reverse=True)
    review=dict(inputIntegrity=True,formalFiles=526,runtimeFiles=13,sourceFiles=86,
        resultSHA256=base.sha(folder/'storage/result.json'),probeSHA256=build['probeSHA256'],
        frozenSource=source.parent.name,pid=policy['pid'],profileOnly=True,frames=0,deployed=False,
        firstDrawItems=len(items),firstDrawMs=sum(x['drawMs'] for x in items),
        outsideGeometricBounds=sum(not x['geometricIntersection'] for x in items),groups=rows,
        visualAccepted=t['visualAccepted'],cleanup=clean,
        limit='First-draw cost, no stable-frame or gameplay result. Geometric exclusion does not exclude filtered pixels.')
    path=HERE/'run-review.json';assert not path.exists()
    path.write_text(json.dumps(review,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(firstDrawItems=review['firstDrawItems'],firstDrawMs=review['firstDrawMs'],groups=rows[:12])))


if __name__=='__main__':main()
