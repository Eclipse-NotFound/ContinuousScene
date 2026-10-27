from pathlib import Path
import ast,importlib.util,shutil
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-visible-room-scout-20261027'
VERSION='camera-visible-room-atlas-1'
ATLAS=HERE.parent/'camera-persistent-fullpage-20261027/ScenePersistentAtlas.as'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('visible_room_atlas_base',BASE/'prepare.py');one=base.one
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'    import flash.desktop.NativeApplication;','    import flash.desktop.NativeApplication;\n    import ScenePersistentAtlas;')
    s=one(s,'        private var world:*;','        private var atlas:ScenePersistentAtlas=new ScenePersistentAtlas();\n        private var world:*;')
    s=one(s,'private var order:Array=[0,1,2,3,3,2,1,0];','private var order:Array=[0,4,1,5,2,6,3,7,7,3,6,2,5,1,4,0];')
    s=one(s,'measurementFrames:960','measurementFrames:1920')
    s=one(s,'                            phase=1;pixelAt=getTimer();','''                            var allocationAt:int=getTimer();atlas.preallocate(world);
                            report.atlasPrepareMs=getTimer()-allocationAt;report.atlasPrepared=atlas.snapshot();
                            phase=1;pixelAt=getTimer();''')
    s=one(s,'            try {if(presenter!=null)presenter.clear();}', '''            try {atlas.clear();cleanup.atlas=atlas.snapshot();}catch(ae:Error){cleanup.errors.push("atlas: "+ae.message);}
            try {if(presenter!=null)presenter.clear();}''')
    s=one(s,'            var condition:int=order[segment];age=0;','            var condition:int=order[segment]%4;age=0;')
    s=one(s,'row={index:segment,condition:condition,mode:["native-static","native-horizontal","native-vertical","native-combined"][condition],',
       'row={index:segment,condition:condition,cached:order[segment]>=4,mode:(order[segment]>=4?"atlas-":"native-")+["static","horizontal","vertical","combined"][condition],')
    s=one(s,'            applyCamera(point.x,point.y);\n            require(grafon.sceneViewReady(),"Unprepared viewport during timing");', '''            if(!row.cached)atlas.useNativeForTest();
            applyCamera(point.x,point.y);
            if(row.cached){atlas.update(world,true,true);require(atlas.presented,"Atlas unexpectedly fell back during timing");}
            require(grafon.sceneViewReady(),"Unprepared viewport during timing");''')
    s=one(s,'                require(world.visual.visible===true,"World must remain visible");applyCamera(point.x,point.y);',
      '                require(world.visual.visible===true,"World must remain visible");atlas.useNativeForTest();applyCamera(point.x,point.y);')
    s=one(s,'                require(result.passed,"Native consecutive captures changed");','''                require(result.passed,"Native consecutive captures changed");
                atlas.update(world,true,true);require(atlas.presented,"Atlas unavailable at pixel view");
                var cached:BitmapData=capture();result.cached=compare(a,cached);savePNG("atlas-"+index+".png",cached);
                atlas.useNativeForTest();var restored:BitmapData=capture();result.restore=compare(a,restored);
                require(result.cached.maxAlpha==0 && result.cached.maxRGB<=2 && result.restore.equal,"Atlas pixel or restoration failure");''')
    s=one(s,'                        report.stabilizationFrames=settle;report.timingStart=snapshot();',
      '                        report.atlasTimingStart=atlas.snapshot();report.stabilizationFrames=settle;report.timingStart=snapshot();')
    s=one(s,'                            report.complete=true;report.passed=true;clear(w);',
      '                            report.atlasTimingEnd=atlas.snapshot();report.complete=true;report.passed=true;clear(w);')
    return s
def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION)
    s=s.replace('== 86','== 87')
    s=one(s,'    assert r.sha(frozen/\'tests/SceneCameraRasterTrial.as\') == r.sha(patch.HELPER)',
      '    assert r.sha(frozen/\'tests/SceneCameraRasterTrial.as\') == r.sha(patch.HELPER)\n    assert r.sha(frozen/\'ScenePersistentAtlas.as\')==r.sha(patch.ATLAS)')
    s=s.replace('960 native camera axis intervals','1920 visible-room native/atlas intervals')
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    target=HERE/'ScenePersistentAtlas.as'
    if target.exists():assert target.read_bytes()==ATLAS.read_bytes()
    else:shutil.copy2(ATLAS,target)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared unchanged 1280 atlas in validated interior room; no production changes')
