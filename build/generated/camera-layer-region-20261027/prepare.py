"""One actor-layer draw, with fixed capture coordinates and a dirty destination clip."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-layer-tiles-20261027'
spec=importlib.util.spec_from_file_location('layer_region_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():return base.helper_source().replace('camera-layer-tiles-1','camera-layer-region-1')
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var dirtyOwnerReads:int=0;',
        'private var dirtyOwnerReads:int=0,actorDrawCalls:int=0,actorDrawMs:int=0;private var actorDirtyPixels:Number=0;')
    s=one(s,'            dirtyTilesMax=Math.max(dirtyTilesMax,count);', '''            dirtyTilesMax=Math.max(dirtyTilesMax,count);
            var dirtyUnion:Rectangle=null;
            for(var dirtyKey:String in dirty)dirtyUnion=dirtyUnion==null?dirty[dirtyKey].clone():dirtyUnion.union(dirty[dirtyKey]);
            if(dirtyUnion!=null) {
                var actor:DisplayObject=group.nodes[0];
                require(group.nodes.length==1 && actor===world.grafon.visObjs[2] && style(actor) && actor.scrollRect==null &&
                    sameMatrix(actor.transform.matrix,new Matrix()) && neutralColor(actor.transform.colorTransform),"Actor layer must be neutral identity");
                var drawAt:int=getTimer();
                scratch.fillRect(dirtyUnion,0);
                scratch.draw(actor,new Matrix(1,0,0,1,-bounds.x,-bounds.y),null,null,dirtyUnion,true);
                ++copies;++actorDrawCalls;actorDrawMs+=getTimer()-drawAt;actorDirtyPixels+=dirtyUnion.width*dirtyUnion.height;
            }''')
    s=one(s,'                maskedDraw(group,tile.pixels,area);++tileRefreshes;',
        '                tile.pixels.copyPixels(scratch,area,new Point());++copies;++tileRefreshes;')
    s=one(s,'tileRefreshes:tileRefreshes,tileRefreshMs:',
        'actorDrawCalls:actorDrawCalls,actorDrawMs:actorDrawMs,actorDirtyPixels:actorDirtyPixels,tileRefreshes:tileRefreshes,tileRefreshMs:')
    return s
def runner_source():return base.runner_source().replace('camera-layer-tiles-1','camera-layer-region-1')
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared single actor-layer clipped update; no build or launch')
