from pathlib import Path
import ast, importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-visible-tree-audit-20261027'
VERSION='camera-border-cache-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('border_tree_generation',BASE/'prepare.py')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'        private var world:*;','        private var borders:Array=[];\n        private var borderEnabled:Boolean=false;\n        private var world:*;')
    s=one(s,'private var order:Array=[0,1,2,3,3,2,1,0];','private var order:Array=[0,4,1,5,2,6,3,7,7,3,6,2,5,1,4,0];')
    s=s.replace('measurementFrames:960','measurementFrames:1920')
    s=one(s,'"All intervals and observer work retained; no new rendering optimization applied."','"Only four exterior border cacheAsBitmap flags differ; all intervals and switch costs retained."')
    s=one(s,'                report.fullTreeBeforeRemoval=SceneDisplayTreeAudit.run(w);\n                require(report.fullTreeBeforeRemoval.complete,"Full native tree audit failed");','                initBorders();')
    s=one(s,'                    if(settle==1) {\n                        report.quietTree=SceneDisplayTreeAudit.run(w);\n                        require(report.quietTree.complete,"Quiet tree audit failed");\n                    }\n','')
    s=one(s,'            var condition:int=order[segment];age=0;\n            row={index:segment,condition:condition,mode:["native-static","native-horizontal","native-vertical","native-combined"][condition],','            var code:int=order[segment],condition:int=code%4;age=0;\n            row={index:segment,code:code,condition:condition,uncached:code>=4,mode:(code>=4?"uncached-":"native-")+["static","horizontal","vertical","combined"][condition],')
    s=one(s,'            var at:int=getTimer();\n            var target:Object=row.moving?route[age]:views[0];','            var at:int=getTimer();setBorders(row.uncached);\n            var target:Object=row.moving?route[age]:views[0];')
    s=one(s,'            checkTransform();guard();','            checkTransform();guard();checkBorders();')
    s=one(s,'            disposeOwned();\n            if(saved!=null && saved.ready)', '            disposeOwned();\n            try {setBorders(false);checkBorders();} catch(borderError:Error){cleanup.errors.push("border restore: "+borderError.message);}\n            cleanup.borderCachesRestored=!borderEnabled;\n            if(saved!=null && saved.ready)')
    s=one(s,'                var a:BitmapData=capture(),b:BitmapData=capture();\n                result.nativeRepeat=compare(a,b);result.passed=result.nativeRepeat.equal;', '''                setBorders(false);checkBorders();
                var a:BitmapData=capture(),b:BitmapData=capture();
                result.nativeRepeat=compare(a,b);
                setBorders(true);checkBorders();var changed:BitmapData=capture();
                result.uncached=compare(a,changed);
                savePNG("border-uncached-"+index+".png",changed);
                setBorders(false);checkBorders();var restored:BitmapData=capture();
                result.restore=compare(a,restored);
                result.passed=result.nativeRepeat.equal && result.restore.equal && result.uncached.maxAlpha==0 && result.uncached.maxRGB<=2;''')
    s=one(s,'savePNG("tree-native-"+index+".png",a);','savePNG("border-native-"+index+".png",a);')
    s=one(s,'            } finally {disposeOwned();result.elapsedMs=getTimer()-at;}','            } finally {setBorders(false);disposeOwned();result.elapsedMs=getTimer()-at;}')
    pos=s.index('        private function coverage(')
    extra='''        private function initBorders():void {
            report.borderCaches={targets:[],disableWrites:0,restoreWrites:0,checks:0,enabled:false};
            for each(var name:String in ["ramT","ramB","ramL","ramR"]) {
                var d:DisplayObject=grafon[name] as DisplayObject;
                require(d!=null && d.parent===world.visual && d.cacheAsBitmap,"Unexpected native exterior border");
                require(d.filters.length==0 && d.mask==null && d.scrollRect==null,"Unexpected border effect");
                borders.push({target:d,cache:d.cacheAsBitmap});
                var bounds:Rectangle=d.getBounds(stage);
                report.borderCaches.targets.push({name:name,width:bounds.width,height:bounds.height,cache:d.cacheAsBitmap});
            }
            require(borders.length==4,"Incomplete borders");
        }
        private function checkBorders():void {
            for each(var b:Object in borders) {
                require(b.target.parent===world.visual,"Border parent changed");
                require(b.target.cacheAsBitmap===(borderEnabled?false:b.cache),"Border cache changed unexpectedly");
            }
            if(report.borderCaches)++report.borderCaches.checks;
        }
        private function setBorders(enabled:Boolean):void {
            if(enabled==borderEnabled)return;
            checkBorders();
            for each(var b:Object in borders) {
                b.target.cacheAsBitmap=enabled?false:b.cache;
                if(enabled)++report.borderCaches.disableWrites;else ++report.borderCaches.restoreWrites;
            }
            borderEnabled=enabled;report.borderCaches.enabled=enabled;checkBorders();
        }

'''
    return s[:pos]+extra+s[pos:]
def runner_source():
    s=(BASE.parent/'camera-active-quiet-axis-20261027/run.py').read_text('utf-8-sig')
    return s.replace('camera-active-quiet-axis-1',VERSION).replace('active quiet camera axes','exterior border native cache').replace('960 native camera axis intervals','1920 border-cache camera intervals')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared exterior-border cache comparison: active visible scene, complete 1920 intervals')
