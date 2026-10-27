from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-active-quiet-axis-20261027'
VERSION='camera-visible-tree-audit-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('tree_axis_generation',BASE/'prepare.py')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'    import flash.desktop.NativeApplication;','    import flash.desktop.NativeApplication;\n    import flash.display.PNGEncoderOptions;\n    import flash.filesystem.File;\n    import flash.filesystem.FileMode;\n    import flash.filesystem.FileStream;')
    s=one(s,'                stripHostiles();','                report.fullTreeBeforeRemoval=SceneDisplayTreeAudit.run(w);\n                require(report.fullTreeBeforeRemoval.complete,"Full native tree audit failed");\n                stripHostiles();')
    s=one(s,'            var x:int=offsetX+960,y:int=offsetY+600;',
        '            var x:int=Math.round(player.X),y:int=Math.round(player.Y);\n            report.cameraRouteFollowsInitialPlayer=true;')
    s=one(s,'localCenterX:960,localCenterY:600,roomGridX:2,roomGridY:4,roomWidth:1920,roomHeight:1000',
        'localCenterX:x-offsetX,localCenterY:y-offsetY,roomGridX:2,roomGridY:4,roomWidth:1920,roomHeight:1000')
    s=one(s,'                    if(settle==60) {','''                    if(settle==1) {
                        report.quietTree=SceneDisplayTreeAudit.run(w);
                        require(report.quietTree.complete,"Quiet tree audit failed");
                    }
                    if(settle==60) {''')
    s=one(s,'                result.nativeRepeat=compare(a,b);result.passed=result.nativeRepeat.equal;',
        '''                result.nativeRepeat=compare(a,b);result.passed=result.nativeRepeat.equal;
                result.visibleCoverage=coverage(a);savePNG("tree-native-"+index+".png",a);
                require(result.visibleCoverage.fraction>=0.15,"Mostly black camera viewport");''')
    pos=s.index('        private function capture()')
    extra='''        private function coverage(b:BitmapData):Object {
            var rect:Rectangle=new Rectangle(96,80,stage.stageWidth-192,stage.stageHeight-160);
            var pixels:Vector.<uint>=b.getVector(rect),count:int=0;
            for(var i:int=0;i<pixels.length;++i) {
                var p:uint=pixels[i];if(Math.max(p>>>16&255,p>>>8&255,p&255)>20)++count;
            }
            return {colored:count,pixels:pixels.length,fraction:count/pixels.length};
        }
        private function savePNG(name:String,b:BitmapData):void {
            var f:FileStream=new FileStream();
            try {f.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);f.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}
            finally {f.close();}
        }

'''
    return s[:pos]+extra+s[pos:]
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace(base.VERSION,VERSION).replace('active quiet camera axes','visible full tree audit')
    s=s.replace('len(after) == 86','len(after) == 87').replace("len(value['frozenSourceSHA256']) == 86","len(value['frozenSourceSHA256']) == 87")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared read-only full display census and visible native camera baseline')
