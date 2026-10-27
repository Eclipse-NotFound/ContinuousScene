"""Refresh changed actor tiles, with a complete layer image as a pixel oracle."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-layer-dirty-20261027'
spec=importlib.util.spec_from_file_location('layer_tiles_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one


def helper_source():return base.helper_source().replace('camera-layer-dirty-1','camera-layer-tiles-1')


def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var groups:Array=[],worldChildren:Array=[],scratch:BitmapData;', '''private var groups:Array=[],worldChildren:Array=[],scratch:BitmapData;
        private var actorGroup:Object=null,oracleImage:BitmapData;
        private var tileRefreshes:int=0,tileRefreshMs:int=0,tileUploadMs:int=0,tileSkipChanges:int=0;
        private var dirtyTilesMax:int=0,oracleCalls:int=0,oracleChecks:Array=[];
        private var dirtyOwnerReads:int=0;''')
    a=s.index('        private function collectWatch(');b=s.index('        public function prepareWorld(',a)
    methods=(HERE/'tile_methods.as.inc').read_text('utf-8-sig')
    s=s[:a]+methods+s[b:]
    s=one(s,'current.nodes.push(node);','current.nodes.push(node);if(node===g.visObjs[2]){current.actor=true;actorGroup=current;}')
    s=one(s,'for each(var group:Object in groups){drawGroup(group);collectWatch(group);}',
          'for each(var group:Object in groups){drawGroup(group);collectWatch(group);}\n                oracleImage=newPixels(int(bounds.width),int(bounds.height));')
    a=s.index('        private function refreshChangedLayers():void {');b=s.index('        private function drawGroup(',a)
    s=s[:a]+(HERE/'refresh_method.as.inc').read_text('utf-8-sig')+s[b:]
    s=one(s,'var used:Rectangle=scratch.getColorBoundsRect(0xff000000,0,false);', '''if(group.actor) {
                for each(var actorTile:Object in group.tiles) {
                    actorTile.pixels.copyPixels(scratch,actorTile.rect,new Point());++copies;
                    actorTile.texture.uploadFromBitmapData(actorTile.pixels);++uploads;
                }
                if(!group.initialized) {
                    group.initialized=true;
                    for(var ay:int=0;ay<bounds.height;ay+=512)for(var ax:int=0;ax<bounds.width;ax+=512) {
                        var ar:Rectangle=new Rectangle(ax,ay,Math.min(512,bounds.width-ax),Math.min(512,bounds.height-ay));
                        var actorPixels:BitmapData=newPixels(int(ar.width),int(ar.height));
                        actorPixels.copyPixels(scratch,ar,new Point());++copies;
                        var alpha:Rectangle=actorPixels.getColorBoundsRect(0xff000000,0,false);
                        if(alpha.isEmpty()){disposePixels(actorPixels);continue;}
                        group.tiles.push({pixels:actorPixels,rect:ar,x:bounds.x+ax,y:bounds.y+ay,width:ar.width,height:ar.height,
                            texture:upload(actorPixels),key:ax+":"+ay});
                    }
                }
                var actorElapsed:int=getTimer()-at;layerRasterMs+=actorElapsed;group.rasterMs+=actorElapsed;return;
            }
            var used:Rectangle=scratch.getColorBoundsRect(0xff000000,0,false);''')
    s=one(s,'render(true,destination);if(captures==1)savePixel("gpu-raw-1",destination);',
          'verifyActorTiles();render(true,destination);if(captures==1)savePixel("gpu-raw-1",destination);')
    s=one(s,'if(scratch){disposePixels(scratch);scratch=null;}',
          'if(scratch){disposePixels(scratch);scratch=null;}if(oracleImage){disposePixels(oracleImage);oracleImage=null;}')
    s=one(s,'liveAnimation:true,layerRasterCalls:', '''tileRefreshes:tileRefreshes,tileRefreshMs:tileRefreshMs,tileUploadMs:tileUploadMs,tileSkipChanges:tileSkipChanges,
                dirtyTilesMax:dirtyTilesMax,dirtyOwnerReads:dirtyOwnerReads,oracleCalls:oracleCalls,oracleChecks:oracleChecks.concat(),
                liveAnimation:true,layerRasterCalls:''')
    return s


def runner_source():
    s=base.runner_source().replace('camera-layer-dirty-1','camera-layer-tiles-1')
    s=one(s,"and end['layerRasterCalls']>len(end['groups'])", "and end['tileRefreshes']>0")
    s=one(s,"    assert 'software' not in", "    assert end['oracleCalls']==13 and len(end['oracleChecks'])==13 and all(x['equal'] for x in end['oracleChecks'])\n    assert 'software' not in")
    s=s.replace('camera live timeline layer cache','camera changed actor tiles')
    return s


if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared changed actor tiles and complete native-layer oracle; no build or launch')
