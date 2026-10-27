from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-border-cache-20261027'
VERSION='camera-opaque-tiles-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('opaque_border_generation',BASE/'prepare.py')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'        private var borders:Array=[];\n        private var borderEnabled:Boolean=false;','        private var opaque:SceneOpaqueTiles=new SceneOpaqueTiles();')
    s=one(s,'                initBorders();\n','')
    s=one(s,'                            report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();','                            report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();\n                            report.opaqueTiles=opaque.init(world);')
    s=one(s,'"Only four exterior border cacheAsBitmap flags differ; all intervals and switch costs retained."','"Only fully opaque native terrain buffers use nontransparent copies; original pixels, crop, transform and ordering remain. All intervals retained."')
    s=one(s,'stage.stageWidth==1280 && stage.stageHeight==720,"Matched camera baseline requires 1280x720 content"','stage.stageWidth==1920 && stage.stageHeight==1080,"Opaque tiles require 1920x1080 content"')
    s=one(s,'            cleanup.borderCachesRestored=!borderEnabled;','            cleanup.opaqueTiles=opaque.clear();\n            if(!cleanup.opaqueTiles.restored)cleanup.errors.push("Opaque tile cleanup failed");')
    start=s.index('        private function initBorders()');end=s.index('        private function coverage(',start)
    s=s[:start]+'''        private function checkBorders():void {opaque.audit();}
        private function setBorders(enabled:Boolean):void {opaque.setEnabled(enabled);}

'''+s[end:]
    s=s.replace('setBorders','setOpaque').replace('checkBorders','checkOpaque').replace('row.uncached','row.opaque').replace('uncached:code>=4','opaque:code>=4').replace('"uncached-"','"opaque-"').replace('result.uncached','result.opaque').replace('border-uncached-','opaque-copy-').replace('border-native-','opaque-native-').replace('border restore: ','opaque restore: ')
    s=one(s,'            checkTransform();guard();checkOpaque();','            checkTransform();guard();checkOpaque();\n            var shown:Object=opaque.visibleStats();row.opaqueVisible.push(shown);')
    s=one(s,'                framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],','                opaqueVisible:[],framesMs:[],sampleAtMs:[],vx:[],vy:[],cameraX:[],cameraY:[],gg:[],scene:[],workMs:[],')
    return s
def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION).replace('exterior border native cache','native opaque terrain copies')
    s=one(s,"('--window-width','1296'),('--window-height','759')","('--window-width','1936'),('--window-height','1119')")
    return s.replace('len(after) == 86','len(after) == 87').replace("len(value['frozenSourceSHA256']) == 86","len(value['frozenSourceSHA256']) == 87").replace('border-cache camera','opaque terrain camera')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared whole-buffer opaque copies with native pixels/crop/order retained')
