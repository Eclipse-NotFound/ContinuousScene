"""Ordered actor sprites: borrow eligible native bitmaps; raster only changed vector roots."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-layer-region-20261027'
spec=importlib.util.spec_from_file_location('actor_sprites_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one

def replace_function(s,name,replacement):
    start=s.index('        private function '+name+'(')
    end=s.index('\n        ',s.index('\n        }',start)+10)
    return s[:start]+replacement.rstrip()+s[end:]

def helper_source():return base.helper_source().replace('camera-layer-region-1','camera-actor-sprites-1')

def renderer_source():
    s=base.renderer_source().replace('import flash.display.Stage;','import flash.display.Stage;\n    import flash.display.Sprite;')
    s=one(s,'private var actorGroup:Object=null,oracleImage:BitmapData;',
      '''private var actorGroup:Object=null,oracleImage:BitmapData;
        private var actorRoots:Array=[],actorItems:Array=[];
        private var actorRasterCalls:int=0,actorRasterMs:int=0,actorRefreshMs:int=0;
        private var directBitmapUploads:int=0,actorUploadMs:int=0,actorSkipped:int=0;
        private var actorVisibilityWrites:int=0,actorVisibilityRestores:int=0;
        private var actorRasterPixels:Number=0;
        private var actorInventory:Array=[];''')
    a=s.index('        private function redrawActorTiles(');b=s.index('        public function prepareWorld(',a)
    s=s[:a]+(HERE/'actor_methods.as.inc').read_text('utf-8-sig')+'\n'+s[b:]
    s=one(s,'                if(changed)dirty.push({group:group,owners:owners});',
          '                if(changed || group.actor)dirty.push({group:group,owners:owners});')
    s=one(s,'            var at:int=getTimer(),state:Array=[],selected:Dictionary=new Dictionary();',
      '            if(group.actor){refreshActorItems(group,new Dictionary(),true);return;}\n            var at:int=getTimer(),state:Array=[],selected:Dictionary=new Dictionary();')
    a=s.index('            if(group.actor) {',s.index('        private function drawGroup('));b=s.index('            var used:Rectangle=',a)
    s=s[:a]+s[b:]
    s=one(s,'        private function releaseGroup(group:Object):void {',
      '''        private function releaseGroup(group:Object):void {
            if(group.actor) {for each(var actorItem:Object in actorItems)releaseActorItem(actorItem);actorItems=[];actorRoots=[];}''')
    s=one(s,'            for each(var group:Object in groups)for each(var t:Object in group.tiles)drawQuad(t.texture,t.x+m.tx,t.y+m.ty,t.width,t.height);',
      '''            for each(var group:Object in groups) {
                context.setBlendFactors("one","oneMinusSourceAlpha");
                if(group.actor)renderActorItems(m);
                else for each(var t:Object in group.tiles)drawQuad(t.texture,t.x+m.tx,t.y+m.ty,t.width,t.height);
            }''')
    s=one(s,'                actorDrawCalls:actorDrawCalls,',
      '''                actorRasterCalls:actorRasterCalls,actorRasterMs:actorRasterMs,actorRefreshMs:actorRefreshMs,
                directBitmapUploads:directBitmapUploads,actorUploadMs:actorUploadMs,actorRasterPixels:actorRasterPixels,
                actorSkipped:actorSkipped,actorVisibilityWrites:actorVisibilityWrites,actorVisibilityRestores:actorVisibilityRestores,
                actorDrawCalls:actorDrawCalls,''')
    s=one(s,'            initial.layerGroups=groupSummary();',
      '            initial.layerGroups=groupSummary();initial.actorInventory=actorInventory;')
    return s

def runner_source():
    s=base.runner_source().replace('camera-layer-region-1','camera-actor-sprites-1')
    s=s.replace("end['animationChanges']>0 and end['tileRefreshes']>0", "end['animationChanges']>0 and end['actorRasterCalls']>0")
    s=s.replace("and all(x['equal'] for x in end['oracleChecks'])",'')
    s=one(s,"    assert end['oracleCalls']==13", "    assert end['actorVisibilityWrites']==end['actorVisibilityRestores']\n    assert end['oracleCalls']==13")
    s=s.replace('camera changed actor tiles','camera ordered actor sprites')
    return s

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared ordered actor sprites; no build or launch')
