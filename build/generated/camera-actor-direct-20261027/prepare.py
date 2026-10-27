"""Stable actor image storage and direct-root drawing with native filtered fallback."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-actor-sprites-20261027'
spec=importlib.util.spec_from_file_location('actor_direct_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one

def helper_source():return base.helper_source().replace('camera-actor-sprites-1','camera-actor-direct-1')

def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var actorRasterPixels:Number=0;',
       'private var actorRasterPixels:Number=0;private var actorDirectCalls:int=0,actorDirectMs:int=0,actorParentCalls:int=0,actorParentMs:int=0;')
    s=one(s,'!item.rect.equals(rect)', '!item.rect.containsRect(rect)')
    a=s.index('                        if(item.bitmap || item.pixels==null || item.width!=rect.width');b=s.index('\n                    }\n                } else ++actorSkipped;',a)
    s=s[:a]+'''                        if(item.bitmap || item.pixels==null || item.rect==null || !item.rect.containsRect(rect)) {
                            releaseActorItem(item);
                            rect.inflate(32,32);rect=rect.intersection(bounds);
                            item.rect=rect;item.width=int(rect.width);item.height=int(rect.height);
                            require(item.width<=2048 && item.height<=2048,"Actor image bound exceeded");
                            item.pixels=newPixels(item.width,item.height);
                        }
                        item.matrix=new Matrix(1,0,0,1,item.rect.x,item.rect.y);requests.push(item);'''+s[b:]
    s=one(s,'directBitmap:item.bitmap!=null,bounds:',
      'rootFilters:node.filters.length,rootMask:node.mask!=null,rootScroll:node.scrollRect!=null,directBitmap:item.bitmap!=null,bounds:')
    a=s.index('            // Isolate each requested root');b=s.index('            actorRefreshMs+=',a)
    s=s[:a]+'''            var filtered:Array=[];
            for each(item in requests) {
                node=item.node;
                if(node.filters.length || node.mask || node.scrollRect || node.transform.matrix3D) {filtered.push(item);continue;}
                var directAt:int=getTimer();
                var area:Rectangle=item.rect.clone();area.offset(-bounds.x,-bounds.y);
                scratch.fillRect(area,0);
                var drawMatrix:Matrix=node.transform.matrix;
                drawMatrix.tx-=bounds.x;drawMatrix.ty-=bounds.y;
                // Source's own matrix/color are passed explicitly; camera is absent.
                // Descendant filters remain native; filtered roots take the parent path.
                scratch.draw(node,drawMatrix,node.transform.colorTransform,null,area,true);
                item.pixels.copyPixels(scratch,area,new Point());copies+=2;
                ++actorRasterCalls;++actorDirectCalls;
                var directMs:int=getTimer()-directAt;actorDirectMs+=directMs;actorRasterMs+=directMs;
                actorRasterPixels+=Number(item.width)*item.height;
                uploadAt=getTimer();
                if(item.texture==null)item.texture=upload(item.pixels);
                else{item.texture.uploadFromBitmapData(item.pixels);++uploads;}
                actorUploadMs+=getTimer()-uploadAt;
            }
            // Only root filters/masks need isolation through their original parent.
            if(filtered.length)try {
                for each(node in actorRoots){saved.push(node.visible);if(node.visible){node.visible=false;++actorVisibilityWrites;}}
                for each(item in filtered) {
                    node=item.node;node.visible=true;
                    try {
                        var drawAt:int=getTimer();area=item.rect.clone();area.offset(-bounds.x,-bounds.y);
                        scratch.fillRect(area,0);
                        scratch.draw(layer,new Matrix(1,0,0,1,-bounds.x,-bounds.y),null,null,area,true);
                        item.pixels.copyPixels(scratch,area,new Point());copies+=2;
                        ++actorRasterCalls;++actorParentCalls;
                        var parentMs:int=getTimer()-drawAt;actorParentMs+=parentMs;actorRasterMs+=parentMs;
                        actorRasterPixels+=Number(item.width)*item.height;
                    } finally {node.visible=false;}
                    uploadAt=getTimer();
                    if(item.texture==null)item.texture=upload(item.pixels);
                    else{item.texture.uploadFromBitmapData(item.pixels);++uploads;}
                    actorUploadMs+=getTimer()-uploadAt;
                }
            } finally {
                for(i=0;i<saved.length;++i)if(actorRoots[i].visible!==saved[i]){actorRoots[i].visible=saved[i];++actorVisibilityRestores;}
            }
'''+s[b:]
    s=one(s,'                actorRasterCalls:actorRasterCalls,',
      '                actorDirectCalls:actorDirectCalls,actorDirectMs:actorDirectMs,actorParentCalls:actorParentCalls,actorParentMs:actorParentMs,\n                actorRasterCalls:actorRasterCalls,')
    return s

def runner_source():return base.runner_source().replace('camera-actor-sprites-1','camera-actor-direct-1')

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared stable actor images and direct source capture; no build or launch')
