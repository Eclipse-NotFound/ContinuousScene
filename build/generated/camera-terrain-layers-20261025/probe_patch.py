"""Reversible terrain-only visibility attribution, all camera windows moving."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
PATCH_SOURCE=HERE.parent/'camera-axis-motion-20261025/probe_patch.py'
ORIGINAL=HERE.parent/'camera-axis-motion-20261025/tests/SceneCameraRasterTrial.as'
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','tests/SceneCameraRasterTrial.as']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
s=importlib.util.spec_from_file_location('terrain_axis_patch',PATCH_SOURCE)
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
EXTRA_INPUTS=(base.ORIGINAL,base.PATCH_SOURCE,*base.EXTRA_INPUTS)

PIXELS='''        private function pixelCase(point:Object,index:int):void {
            var at:int=getTimer(),result:Object={index:index,x:point.x,y:point.y,passed:false,conditions:[]};
            report.pixels.push(result);
            try {
                require(world.visual.visible===true,"World must remain visible");applyCamera(point.x,point.y);
                require(grafon.sceneViewReady(),"Pixel viewport not prepared");applyLayers(0);
                var original:BitmapData=capture();
                for(var mode:int=1;mode<=3;++mode) {
                    applyLayers(mode);var suppressed:BitmapData=capture();
                    applyLayers(0);var restored:BitmapData=capture();
                    var item:Object={condition:mode,changed:compare(original,suppressed),restored:compare(original,restored)};
                    result.conditions.push(item);
                    require(item.restored.equal,"Terrain visibility did not restore exact pixels");
                }
                result.passed=true;
            } finally {applyLayers(0);disposeOwned();result.elapsedMs=getTimer()-at;}
        }

        private function applyLayers(condition:int):void {
            require(condition>=0 && condition<=3,"Invalid terrain condition");
            for(var i:int=0;i<terrain.length;++i) {
                var item:Object=terrain[i];
                item.target.visible=item.visible && !(i<2?(condition&1):(condition&2));
            }
            require(sameLayers(layerState(),condition),"Terrain visibility did not apply");
        }
        private function layerState():Array {
            var value:Array=[];for each(var item:Object in terrain)value.push(item.target.visible);return value;
        }
        private function sameLayers(value:Array,condition:int):Boolean {
            if(value.length!=4)return false;
            for(var i:int=0;i<4;++i)if(value[i]!==Boolean(terrain[i].visible && !(i<2?(condition&1):(condition&2))))return false;
            return true;
        }

'''

def helper_source():
    source=ORIGINAL.read_text('utf-8-sig');assert source==base.helper_source()
    start=source.index('        private function pixelCase(')
    end=source.index('        private function capture():BitmapData',start)
    edits=[('version:"camera-axis-motion-1"','version:"camera-terrain-layers-1"'),
      ('        private var originalTiles:Array=[];','        private var originalTiles:Array=[];\n        private var terrain:Array=[];'),
      ('                rememberTiles();','''                rememberTiles();
                for each(var layer:DisplayObject in [grafon.visBack,grafon.visBack2,grafon.visFront,grafon.visVoda]) {
                    require(layer!=null && layer.parent===world.visual,"Terrain parent identity mismatch");
                    terrain.push({target:layer,visible:layer.visible});
                }
                report.terrainInitial=layerState();'''),
      ('"World display stays visible in every arm; compare only native camera axes.",','"World stays visible; only native terrain parents are temporarily suppressed, all camera windows moving.",'),
      ('["native-static","native-horizontal","native-vertical","native-combined"]','["native-moving","back-hidden-moving","front-hidden-moving","terrain-hidden-moving"]'),
      ('hidden:false,moving:condition!=0,','hidden:false,moving:true,'),
      ('row.workMs.push(pending.workMs);row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);','row.workMs.push(pending.workMs);row.worldVisible.push(pending.worldVisible);row.windowVisible.push(pending.windowVisible);\n                    require(sameLayers(layerState(),row.condition),"Terrain changed during rendered interval");row.terrain.push(pending.terrain);'),
      ('var target:Object=row.moving?route[age]:views[0];\n            var point:Object={x:row.condition==2?views[0].x:target.x,y:row.condition==1?views[0].y:target.y};','var point:Object=route[age];'),
      ('            applyCamera(point.x,point.y);\n            require(grafon.sceneViewReady(),"Unprepared viewport during timing");','            applyCamera(point.x,point.y);applyLayers(row.condition);\n            require(grafon.sceneViewReady(),"Unprepared viewport during timing");'),
      ('workMs:getTimer()-at,worldVisible:world.visual.visible,windowVisible:stage.nativeWindow.visible};','workMs:getTimer()-at,worldVisible:world.visual.visible,windowVisible:stage.nativeWindow.visible,terrain:layerState()};'),
      ('            try {if(presenter!=null)presenter.clear();}', '            try {if(terrain.length==4){applyLayers(0);cleanup.terrainRestored=sameLayers(layerState(),0);}}catch(eTerrain:Error){cleanup.errors.push("terrain: "+eTerrain.message);}\n            try {if(presenter!=null)presenter.clear();}'),
      (source[start:end],PIXELS)]
    out=source
    for old,new in edits:assert out.count(old)==1,(old,out.count(old));out=out.replace(old,new,1)
    # Add a per-window bounded observation array beside the already present one.
    assert out.count('worldVisible:[],windowVisible:[]')==1
    out=out.replace('worldVisible:[],windowVisible:[]','worldVisible:[],windowVisible:[],terrain:[]',1)
    return out

def transform(source):return base.transform(source)

def prepare(source,destination):
    assert HELPER.read_text('utf-8-sig')==helper_source()
    assert not destination.exists() and not (source/'tests/SceneCameraRasterTrial.as').exists()
    shutil.copytree(source,destination)
    main=destination/'ContinuousSceneMotionProbe.as';main.write_text(transform(main.read_text('utf-8-sig')),'utf-8')
    shutil.copy2(HELPER,destination/'tests/SceneCameraRasterTrial.as')

if __name__=='__main__':
    output=helper_source();HELPER.parent.mkdir(parents=True,exist_ok=True)
    if HELPER.exists():assert HELPER.read_text('utf-8-sig')==output
    else:HELPER.write_text(output,'utf-8')
    print({'helper':sha(HELPER)})
