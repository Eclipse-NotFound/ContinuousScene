from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-native-near-groups-20261027'
VERSION='camera-native-visible-groups-1'
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('near_group_generation',BASE/'prepare.py')
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'            var x:int=offsetX+960,y:int=offsetY+600;',
        '            var x:int=Math.round(player.X),y:int=Math.round(player.Y);\n            report.cameraRouteFollowsInitialPlayer=true;')
    s=one(s,'localCenterX:960,localCenterY:600,roomGridX:2,roomGridY:4,roomWidth:1920,roomHeight:1000',
        'localCenterX:x-offsetX,localCenterY:y-offsetY,roomGridX:2,roomGridY:4,roomWidth:1920,roomHeight:1000')
    s=one(s,'                var a:BitmapData=capture(),repeat:BitmapData=capture();result.nativeRepeat=compare(a,repeat);',
        '''                var a:BitmapData=capture(),repeat:BitmapData=capture();result.nativeRepeat=compare(a,repeat);
                result.visibleCoverage=coverage(a);
                savePNG("visible-native-"+index+".png",a);
                require(result.visibleCoverage.fraction>=0.15,"Camera is looking at mostly black space");''')
    s=one(s,'        private function savePNG(name:String,b:BitmapData):void {',
        '''        private function coverage(b:BitmapData):Object {
            var rect:Rectangle=new Rectangle(96,80,stage.stageWidth-192,stage.stageHeight-160);
            var pixels:Vector.<uint>=b.getVector(rect),count:int=0;
            for(var i:int=0;i<pixels.length;++i) {
                var p:uint=pixels[i];
                if(Math.max(p>>>16&255,p>>>8&255,p&255)>20)++count;
            }
            return {colored:count,pixels:pixels.length,fraction:count/pixels.length,excludesMainHudMargins:true};
        }
        private function savePNG(name:String,b:BitmapData):void {''')
    return s
def runner_source():
    return (BASE/'run.py').read_text('utf-8-sig').replace(base.VERSION,VERSION).replace('near native cache groups','visible native cache groups')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneNativeGroupCache.as').write_bytes((BASE/'tests/SceneNativeGroupCache.as').read_bytes())
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared visible player-centered camera route with pixel coverage gate')
