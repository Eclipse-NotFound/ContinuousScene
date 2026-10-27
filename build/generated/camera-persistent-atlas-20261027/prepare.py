from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-border-cache-20261027'
VERSION='camera-persistent-atlas-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('persistent_border_generation',BASE/'prepare.py');presentation=load('persistent_generation',HERE/'presentation.py')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'    import flash.display.Stage;','    import flash.display.Stage;\n    import flash.events.Event;\n    import SceneClassicAtlas;\n    import ScenePersistentAtlas;')
    s=one(s,'        private var borders:Array=[];\n        private var borderEnabled:Boolean=false;','''        private var classic:SceneClassicAtlas=new SceneClassicAtlas();
        private var persistent:ScenePersistentAtlas=new ScenePersistentAtlas();
        private var rendererMode:int=0;''')
    order=[]
    for a in range(4):order.extend([a,a+4,a+8])
    order+=list(reversed(order))
    s=one(s,'private var order:Array=[0,4,1,5,2,6,3,7,7,3,6,2,5,1,4,0];','private var order:Array='+str(order).replace(' ','')+';')
    s=one(s,'measurementFrames:1920','measurementFrames:2880')
    s=one(s,'                initBorders();','                stage.addEventListener(Event.ENTER_FRAME,beforeNativeFrame,false,2000000);')
    s=one(s,'                            report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();','''                            report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();
                            var allocateAt:int=getTimer();classic.preallocate(world);persistent.preallocate(world);
                            report.atlasPrepareMs=getTimer()-allocateAt;
                            report.atlasPrepared={classic:classic.snapshot(),persistent:persistent.snapshot()};''')
    s=one(s,'"Only four exterior border cacheAsBitmap flags differ; all intervals and switch costs retained."','"Compare native, old merged atlas, and persistent event-indexed merged atlas. Identical pixels/page size, complete intervals and switches retained."')
    s=one(s,'stage.stageWidth==1280 && stage.stageHeight==720,"Matched camera baseline requires 1280x720 content"','stage.stageWidth==1920 && stage.stageHeight==1080,"Atlas diagnosis requires 1920x1080 content"')
    s=one(s,'            var code:int=order[segment],condition:int=code%4;age=0;\n            row={index:segment,code:code,condition:condition,uncached:code>=4,mode:(code>=4?"uncached-":"native-")+["static","horizontal","vertical","combined"][condition],','''            var code:int=order[segment],condition:int=code%4,variant:int=int(code/4);age=0;
            row={index:segment,code:code,condition:condition,variant:variant,mode:["native-","classic-","persistent-"][variant]+["static","horizontal","vertical","combined"][condition],''')
    s=one(s,'                framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],','                atlas:[],framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],')
    s=one(s,'            var at:int=getTimer();setBorders(row.uncached);','            var at:int=getTimer();setRenderer(row.variant);')
    s=one(s,'            checkTransform();guard();checkBorders();','''            checkTransform();guard();
            if(rendererMode==1)classic.update(world,true,true);else if(rendererMode==2)persistent.update(world,true,true);
            var atlasState:Object={classic:classic.snapshot(),persistent:persistent.snapshot()};row.atlas.push(atlasState);
            require(rendererMode==0?(!atlasState.classic.presented && !atlasState.persistent.presented):
                rendererMode==1?(atlasState.classic.presented && !atlasState.persistent.presented):(!atlasState.classic.presented && atlasState.persistent.presented),"Wrong atlas presentation state");''')
    s=one(s,'            try {setBorders(false);checkBorders();} catch(borderError:Error){cleanup.errors.push("border restore: "+borderError.message);}\n            cleanup.borderCachesRestored=!borderEnabled;','''            if(stage)stage.removeEventListener(Event.ENTER_FRAME,beforeNativeFrame);
            try {setRenderer(0);classic.clear();persistent.clear();} catch(atlasError:Error){cleanup.errors.push("atlas restore: "+atlasError.message);}
            cleanup.atlas={classic:classic.snapshot(),persistent:persistent.snapshot()};
            if(cleanup.atlas.classic.ownedBitmaps || cleanup.atlas.persistent.ownedBitmaps)cleanup.errors.push("Atlas pixel stores remain");''')
    start=s.index('        private function pixelCase(');end=s.index('        private function coverage(',start)
    extra='''        private function beforeNativeFrame(event:Event):void {
            // This is the old renderer's required native restoration. The new
            // renderer deliberately keeps its own display binding through World.step.
            classic.beginFrame();
        }
        private function setRenderer(mode:int):void {
            if(rendererMode==mode)return;
            classic.useNativeForTest();persistent.useNativeForTest();rendererMode=mode;
        }
        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false,variants:[]};
            report.pixels.push(result);
            try {
                setRenderer(0);applyCamera(point.x,point.y);
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                var a:BitmapData=capture(),repeat:BitmapData=capture();
                result.nativeRepeat=compare(a,repeat);result.visibleCoverage=coverage(a);
                require(result.nativeRepeat.equal && result.visibleCoverage.fraction>=0.15,"Unstable or mostly black native viewport");
                savePNG("atlas-native-"+index+".png",a);
                for(var variant:int=1;variant<=2;++variant) {
                    setRenderer(variant);
                    if(variant==1)classic.update(world,true,true);else persistent.update(world,true,true);
                    var state:Object=variant==1?classic.snapshot():persistent.snapshot();
                    require(state.presented,"Atlas pixel case fell back");
                    var b:BitmapData=capture();
                    var item:Object={variant:variant,state:state,changed:compare(a,b)};
                    savePNG("atlas-"+variant+"-"+index+".png",b);
                    setRenderer(0);var restored:BitmapData=capture();item.restore=compare(a,restored);
                    result.variants.push(item);
                    require(item.changed.maxRGB<=2 && item.changed.maxAlpha==0 && item.restore.equal,"Atlas pixel/restore mismatch");
                }
                result.passed=true;
            } finally {setRenderer(0);disposeOwned();result.elapsedMs=getTimer()-at;}
        }

'''
    return s[:start]+extra+s[end:]
def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION).replace('exterior border native cache','persistent merged atlas')
    s=one(s,"('--window-width','1296'),('--window-height','759')","('--window-width','1936'),('--window-height','1119')")
    return s.replace('len(after) == 86','len(after) == 88').replace("len(value['frozenSourceSHA256']) == 86","len(value['frozenSourceSHA256']) == 88").replace('1920 border-cache camera','2880 persistent atlas camera')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('SceneClassicAtlas.as',presentation.classic_source()),('ScenePersistentAtlas.as',presentation.persistent_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared original merged and persistent atlas with active visible camera comparison')
