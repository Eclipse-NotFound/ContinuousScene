from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-active-quiet-axis-20261027'
VERSION='camera-native-near-groups-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('quiet_group_generation',BASE/'prepare.py')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'    import flash.desktop.NativeApplication;','    import flash.desktop.NativeApplication;\n    import flash.display.PNGEncoderOptions;\n    import flash.filesystem.File;\n    import flash.filesystem.FileMode;\n    import flash.filesystem.FileStream;')
    s=one(s,'        private var order:Array=[0,1,2,3,3,2,1,0];','        private var groupCache:SceneNativeGroupCache=new SceneNativeGroupCache();\n        private var order:Array=[0,4,1,5,2,6,3,7,7,3,6,2,5,1,4,0];')
    s=one(s,'measurementFrames:960','measurementFrames:1920')
    s=one(s,'                makeRoute();','''                makeRoute();
                var bounds:Rectangle=new Rectangle(views[0].x-640-120-128,views[0].y-360-48-128,1280+240+256,720+96+256);
                groupCache.prepare(w,bounds);report.groupCache=groupCache.report;''')
    s=one(s,'prepareRoute=views.concat(route);','prepareRoute=views.concat(route).concat(views).concat(route);')
    s=one(s,'                    var point:Object=prepareRoute[cursor];','                    groupCache.setEnabled(cursor>=views.length+route.length);\n                    var point:Object=prepareRoute[cursor];')
    s=one(s,'                        presenter.clear();applyCamera(views[0].x,views[0].y);','                        groupCache.setEnabled(false);presenter.clear();applyCamera(views[0].x,views[0].y);')
    s=one(s,'            var condition:int=order[segment];age=0;','            var code:int=order[segment],condition:int=code%4;age=0;')
    s=one(s,'row={index:segment,condition:condition,mode:["native-static","native-horizontal","native-vertical","native-combined"][condition],','row={index:segment,code:code,condition:condition,cached:code>=4,mode:(code>=4?"cached-":"native-")+["static","horizontal","vertical","combined"][condition],')
    s=one(s,'            var at:int=getTimer();\n            var target:Object=row.moving?route[age]:views[0];','            var at:int=getTimer();groupCache.setEnabled(row.cached);\n            var target:Object=row.moving?route[age]:views[0];')
    s=one(s,'            var cleanup:Object={restored:true,errors:[],nativeCachesRetained:true,pendingOwnedBitmaps:0};','''            var cleanup:Object={restored:true,errors:[],nativeCachesRetained:true,pendingOwnedBitmaps:0};
            cleanup.groupCache=groupCache.clear();
            if(!cleanup.groupCache.restored || cleanup.groupCache.pendingHolders)cleanup.errors.push("Native group cache failed restoration");''')
    a=s.index('        private function pixelCase(');b=s.index('        private function capture()',a)
    s=s[:a]+'''        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false};report.pixels.push(result);
            try {
                groupCache.setEnabled(false);applyCamera(point.x,point.y);
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                var a:BitmapData=capture(),repeat:BitmapData=capture();result.nativeRepeat=compare(a,repeat);
                require(result.nativeRepeat.equal,"Native repeat pixels changed");
                groupCache.setEnabled(true);var b:BitmapData=capture();result.cached=compare(a,b);
                groupCache.setEnabled(false);var c:BitmapData=capture();result.restore=compare(a,c);
                if(index==0){savePNG("group-native.png",a);savePNG("group-cached.png",b);}
                result.passed=result.cached.maxRGB<=2 && result.cached.maxAlpha==0 && result.restore.equal;
                require(result.passed,"Native group cache pixels differ beyond RGB2/alpha0 or restoration differs");
            } finally {groupCache.setEnabled(false);disposeOwned();result.elapsedMs=getTimer()-at;}
        }
        private function savePNG(name:String,b:BitmapData):void {
            var f:FileStream=new FileStream();
            try {f.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);f.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}
            finally {f.close();}
        }

'''+s[b:]
    return s
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace(base.VERSION,VERSION).replace('active quiet camera axes','near native cache groups')
    s=s.replace('len(after) == 86','len(after) == 87').replace("len(value['frozenSourceSHA256']) == 86","len(value['frozenSourceSHA256']) == 87")
    s=one(s,"'960 native camera axis intervals, active quiet world; no deployment'","'1920 active quiet native/cached camera intervals; no deployment'")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared live near-group native bitmap cache test')
