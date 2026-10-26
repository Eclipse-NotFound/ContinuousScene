"""Inspect one ordered-root draw; deliberately perform no frame-rate windows."""
from pathlib import Path
import importlib.util
import ast
HERE = Path(__file__).resolve().parent
BASE = HERE.parent/'camera-stage3d-region-items-20261027'
spec = importlib.util.spec_from_file_location('item_profile_base', BASE/'prepare.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
one = base.one


def helper_source():
    s = base.helper_source().replace('camera-stage3d-region-items-1','camera-stage3d-item-profile-1')
    start = s.index('                } else if(phase==2) {')
    end = s.index('                } else if(phase==3) {',start)
    s = s[:start]+'''                } else if(phase==2) {
                    report.itemProfile=presenter.itemProfile();
                    report.profileOnly=true;report.measurementFrames=0;
                    report.intervalMeaning="No interval windows; first-draw CPU profile only.";
                    report.complete=true;report.passed=true;clear(w);
'''+s[end:]
    return s


def renderer_source():
    s = base.renderer_source()
    s = one(s,'private var splitLayers:Array=[];',
        'private var splitLayers:Array=[],regionProfile:Array=[];\n        private var cullReasons:Dictionary=new Dictionary();')
    s = one(s,'if(child.filters.length || child.mask!=null || child.scrollRect!=null || child.transform.matrix3D!=null){safe=false;break;}', '''if(child.filters.length || child.mask!=null || child.scrollRect!=null || child.transform.matrix3D!=null) {
                    safe=false;cullReasons[node]={descendant:getQualifiedClassName(child),
                        filter:child.filters.length?getQualifiedClassName(child.filters[0]):null,
                        mask:child.mask!=null,scroll:child.scrollRect!=null,matrix3D:child.transform.matrix3D!=null};break;
                }''')
    s = one(s,'            ++regionItemsDrawn;regionItemDrawMs+=getTimer()-at;', '''            var drawMs:int=getTimer()-at;++regionItemsDrawn;regionItemDrawMs+=drawMs;
            if(regionRasterCalls==0) {
                var geometry:Rectangle=node.getBounds(root),bitmap:Bitmap=node as Bitmap;
                regionProfile.push({className:getQualifiedClassName(node),name:node.name,drawMs:drawMs,
                    blend:node.blendMode,alpha:node.alpha,cacheAsBitmap:node.cacheAsBitmap,
                    bounds:{x:geometry.x,y:geometry.y,width:geometry.width,height:geometry.height},
                    geometricIntersection:geometry.intersects(refreshArea),cullSafe:safeRegionCull[node],cullReason:cullReasons[node],
                    matrix:{a:matrix.a,b:matrix.b,c:matrix.c,d:matrix.d,tx:matrix.tx,ty:matrix.ty},
                    bitmapWidth:bitmap&&bitmap.bitmapData?bitmap.bitmapData.width:0,
                    bitmapHeight:bitmap&&bitmap.bitmapData?bitmap.bitmapData.height:0});
            }''')
    s = one(s,'        private function upload(pixels:BitmapData):RectangleTexture {',
        '        public function itemProfile():Array {return regionProfile.concat();}\n        private function upload(pixels:BitmapData):RectangleTexture {')
    return s


def runner_source():
    s = base.runner_source().replace('camera-stage3d-region-items-1','camera-stage3d-item-profile-1')
    start=s.index('def summarize(raw):');end=s.index('\n\ndef main():',start)
    s=s[:start]+'''def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config'];assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck']
    assert cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    t=raw['cameraRaster'];clean=raw['cameraRasterCleanup'];p=clean['presentation']
    assert t['version']==VERSION and t['complete'] and t['passed'] and not t['errors'] and t['profileOnly']
    assert clean==t['cleanup'] and clean['restored'] and not clean['errors'] and clean['pendingOwnedBitmaps']==0
    assert not t['framesMs'] and not t['sampleAtMs'] and not t['windows']
    assert p['regionRasterCalls']==13 and p['uploads']==p['texturesCreated']+13
    assert p['copies']==p['allocated']-1+13 and p['allocated']==p['disposed']==p['texturesCreated']+2
    assert p['texturesCreated']==p['texturesDisposed'] and p['contextCreates']==p['contextDisposals']==1
    assert not p['active'] and not p['ready'] and p['gpuBytes']==0 and not p['error']
    assert p['clipsStopped']==p['clipsResumed'] and p['timelinesRestored'] and not p['timelineChanges']
    assert p['captureCullRestored'] and p['worldPrepared'] and p['observationSteps']==8
    assert len(t['pixels'])==13 and len(t['nativeWarmups'])==18
    assert t['pixelBitmapsCreated']==t['pixelBitmapsDisposed']==260 and not t['pixelDisposeErrors']
    assert all(x['passed'] and len(x['checks'])==3 and all(c['pixels']['equal'] for c in x['checks']) for x in t['nativeWarmups'])
    assert all(x['restore']['equal'] and x['restore']['differentPixels']==0 for x in t['pixels'])
    assert t['visualAccepted']==t['pixelsValid']==all(x['visualAccepted'] for x in t['pixels'])
    assert t['itemProfile'] and all(x['drawMs']>=0 for x in t['itemProfile'])
    groups={}
    for item in t['itemProfile']:
        key=item['className'];row=groups.setdefault(key,dict(className=key,count=0,drawMs=0,outsideGeometry=0,uncullable=0))
        row['count']+=1;row['drawMs']+=item['drawMs']
        row['outsideGeometry']+=not item['geometricIntersection'];row['uncullable']+=not item['cullSafe']
    return dict(version=VERSION,complete=True,profileOnly=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,
        deployed=False,frames=0,arms={},pairs=[],visualAccepted=t['visualAccepted'],cleanup=clean,
        classes=sorted(groups.values(),key=lambda x:x['drawMs'],reverse=True),items=t['itemProfile'],
        limits=['First-draw object costs only; no frame-rate windows or movement-pair claim.',
                'Outside geometric bounds do not prove filtered pixels are outside.',
                'The failed ordered-root renderer remains rejected; this profile only locates its work.'])
'''+s[end:]
    s=s.replace('camera ordered-root region refresh cost','camera one-draw item profile')
    s=s.replace('960 native versus 512-square region refresh intervals; cost diagnostic only, no deployment',
        'One-draw item profile and 13 pixel/restoration checks; no frame-rate windows or deployment')
    s=one(s,"arms=summary['arms'],pairs=summary['pairs']", "frames=0,classes=summary['classes'][:8]")
    return s


if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    code=runner_source();ast.parse(code);(HERE/'run.py').write_text(code,'utf-8')
    # Same immutable seed and transformer; only this directory's generator differs.
    patch=(BASE/'probe_patch.py').read_text('utf-8-sig')
    patch=patch.replace("camera-stage3d-region-refresh-20261027/probe_patch.py", "camera-stage3d-region-items-20261027/probe_patch.py")
    patch=patch.replace('region_items_patch_seed','item_profile_patch_seed').replace('region_items_generation','item_profile_generation')
    ast.parse(patch);(HERE/'probe_patch.py').write_text(patch,'utf-8')
    print('Generated one-draw item profiling diagnostic; no frame-rate loop, build, or launch')
