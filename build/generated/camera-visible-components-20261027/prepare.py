from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-visible-tree-audit-20261027'
VERSION='camera-visible-components-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('component_tree_generation',BASE/'prepare.py')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'    import flash.display.Stage;','    import flash.display.Stage;\n    import flash.events.Event;')
    s=one(s,'        private var world:*;','''        private var componentTargets:Array=[];
        private var componentMode:int=0;
        private const COMPONENTS:Array=["native","no-light","no-terrain","no-decor","no-actors","no-backdrop","no-gui","no-world"];
        private var world:*;''')
    order=[]
    for axis in range(4):
        for component in range(1,8):order.extend([axis,component*4+axis])
    order+=list(reversed(order))
    s=one(s,'private var order:Array=[0,1,2,3,3,2,1,0];','private var order:Array='+str(order).replace(' ','')+';')
    s=one(s,'measurementFrames:960','measurementFrames:6720')
    s=one(s,'getTimer()-beginAt<180000','getTimer()-beginAt<420000')
    s=one(s,'"All intervals and observer work retained; no new rendering optimization applied."','"Visibility omissions are diagnostic controls, not optimizations; all intervals and switch costs retained."')
    s=one(s,'                report.fullTreeBeforeRemoval=SceneDisplayTreeAudit.run(w);\n                require(report.fullTreeBeforeRemoval.complete,"Full native tree audit failed");','                initComponents();')
    s=one(s,'                    if(settle==1) {\n                        report.quietTree=SceneDisplayTreeAudit.run(w);\n                        require(report.quietTree.complete,"Quiet tree audit failed");\n                    }\n','')
    s=one(s,'                    if(age==120)','                    if(age==60)')
    s=one(s,'            require(stage.stageWidth==1280 && stage.stageHeight==720,"Matched camera baseline requires 1280x720 content");','            require(stage.stageWidth==1920 && stage.stageHeight==1080,"Component diagnosis requires 1920x1080 content");')
    s=one(s,'            var condition:int=order[segment];age=0;\n            row={index:segment,condition:condition,mode:["native-static","native-horizontal","native-vertical","native-combined"][condition],\n                hidden:false,moving:condition!=0,startAtMs:previous,','''            var code:int=order[segment],condition:int=code%4,component:int=int(code/4);age=0;
            row={index:segment,code:code,component:component,condition:condition,mode:COMPONENTS[component]+"-"+["static","horizontal","vertical","combined"][condition],
                exitChecks:0,hidden:component==7,moving:condition!=0,startAtMs:previous,''')
    s=one(s,'            var target:Object=row.moving?route[age]:views[0];','            var target:Object=row.moving?route[age*2]:views[0];')
    s=one(s,'            require(world.visual.visible===true,"World visibility changed");','            applyComponent(row.component);checkComponents();')
    s=one(s,'            disposeOwned();\n            if(saved!=null && saved.ready)','''            disposeOwned();
            if(stage)stage.removeEventListener(Event.EXIT_FRAME,onComponentExit);
            try {applyComponent(0);checkComponents();cleanup.componentsRestored=true;} catch(componentError:Error){cleanup.componentsRestored=false;cleanup.errors.push("component restore: "+componentError.message);}
            if(saved!=null && saved.ready)''')
    start=s.index('        private function pixelCase(');end=s.index('        private function coverage(',start)
    pixel='''        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false,controls:[]};
            report.pixels.push(result);
            try {
                applyComponent(0);applyCamera(point.x,point.y);checkComponents();
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");
                var a:BitmapData=capture(),repeat:BitmapData=capture();
                result.nativeRepeat=compare(a,repeat);releaseSnapshot(repeat);
                require(result.nativeRepeat.equal,"Native repeated image differs");
                result.visibleCoverage=coverage(a);savePNG("components-native-"+index+".png",a);
                require(result.visibleCoverage.fraction>=0.15,"Mostly black camera viewport");
                for(var mode:int=1;mode<COMPONENTS.length;++mode) {
                    applyComponent(mode);checkComponents();var changed:BitmapData=capture();
                    var entry:Object={component:mode,name:COMPONENTS[mode],changed:compare(a,changed)};
                    if(index==0)savePNG("components-"+COMPONENTS[mode]+".png",changed);
                    releaseSnapshot(changed);
                    applyComponent(0);checkComponents();var restored:BitmapData=capture();
                    entry.restore=compare(a,restored);releaseSnapshot(restored);result.controls.push(entry);
                    require(entry.restore.equal,"Component restore differs");
                }
                result.passed=true;
            } finally {applyComponent(0);disposeOwned();result.elapsedMs=getTimer()-at;}
        }
        private function releaseSnapshot(b:BitmapData):void {
            var index:int=owned.indexOf(b);require(index>=0,"Unknown pixel bitmap");
            b.dispose();owned.splice(index,1);++report.pixelBitmapsDisposed;
        }
        private function initComponents():void {
            report.components={targets:[],visibilityWrites:0,applyCalls:0,checks:0,exitChecks:0,mode:0};
            addComponent(world.visual,"world",7);
            addComponent(grafon.visLight,"light",1);
            for each(var name:String in ["visBack","visBack2","visFront","visVoda"])addComponent(grafon[name],name,2);
            for each(var layer:int in [0,1,3])addComponent(grafon.visObjs[layer],"objects-"+layer,3);
            for each(layer in [2,4,5])addComponent(grafon.visObjs[layer],"objects-"+layer,4);
            addComponent(grafon.visFon,"backdrop",5);
            var gui:DisplayObject=null;
            for(var i:int=0;i<world.main.numChildren;++i)if(getQualifiedClassName(world.main.getChildAt(i))=="visualGUI") {
                require(gui==null,"Duplicate native GUI");gui=world.main.getChildAt(i);
            }
            require(gui!=null,"Missing native GUI");addComponent(gui,"native-gui",6);
            require(componentTargets.length==14,"Wrong component target count");
            stage.addEventListener(Event.EXIT_FRAME,onComponentExit,false,int.MIN_VALUE);
        }
        private function addComponent(d:DisplayObject,name:String,mode:int):void {
            require(d!=null && d.parent!=null,"Missing component "+name);
            componentTargets.push({target:d,name:name,mode:mode,parent:d.parent,visible:d.visible});
            report.components.targets.push({name:name,mode:mode,className:getQualifiedClassName(d),visible:d.visible});
        }
        private function applyComponent(mode:int):void {
            if(report.components==null)return;
            require(mode>=0 && mode<COMPONENTS.length,"Unknown component mode");
            for each(var t:Object in componentTargets) {
                require(t.target.parent===t.parent,"Component parent changed");
                var v:Boolean=mode==t.mode?false:t.visible;
                if(t.target.visible!==v){t.target.visible=v;++report.components.visibilityWrites;}
            }
            componentMode=mode;report.components.mode=mode;++report.components.applyCalls;
        }
        private function checkComponents():void {
            for each(var t:Object in componentTargets) {
                require(t.target.parent===t.parent && t.target.visible===(componentMode==t.mode?false:t.visible),"Component visibility/parent changed: "+t.name);
            }
            if(report.components)++report.components.checks;
        }
        private function onComponentExit(e:Event):void {
            if(closed || phase!=3)return;
            try {checkComponents();++report.components.exitChecks;++row.exitChecks;}
            catch(error:Error){fail(error);}
        }

'''
    return s[:start]+pixel+s[end:]
def runner_source():
    s=(BASE.parent/'camera-active-quiet-axis-20261027/run.py').read_text('utf-8-sig')
    s=s.replace('camera-active-quiet-axis-1',VERSION).replace('active quiet camera axes','visible component attribution')
    s=one(s,"('--window-width','1296'),('--window-height','759')","('--window-width','1936'),('--window-height','1119')")
    return s.replace('960 native camera axis intervals','6720 component camera intervals')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared 1920x1080 visible component controls; 6720 complete camera intervals')
