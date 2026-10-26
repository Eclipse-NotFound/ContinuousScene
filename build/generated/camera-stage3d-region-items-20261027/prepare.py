"""Measure region drawing from ordered display roots instead of the whole world."""
from pathlib import Path
import importlib.util
import ast
HERE = Path(__file__).resolve().parent
BASE = HERE.parent/'camera-stage3d-region-refresh-20261027'
spec = importlib.util.spec_from_file_location('region_items_base', BASE/'prepare.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
one = base.one


def helper_source():
    s = base.helper_source().replace('camera-stage3d-region-refresh-1', 'camera-stage3d-region-items-1')
    return s.replace('One fixed 512x512 world-space region is redrawn each GPU interval over the frozen whole-world cache.',
        'One fixed 512x512 region is redrawn from live ordered display roots, skipping outside filter-free roots. Frozen style classification is diagnostic-only.')


def renderer_source():
    s = base.renderer_source()
    s = one(s, 'private var regionFirstAlphaBounds:Object;', '''private var regionFirstAlphaBounds:Object;
        private var safeRegionCull:Dictionary=new Dictionary(),knownRegionCull:Dictionary=new Dictionary();
        private var regionCullClassifications:int=0,regionItemsDrawn:int=0,regionItemsSkipped:int=0;
        private var regionSelectionMs:int=0,regionItemDrawMs:int=0,regionRootQueries:int=0;
        private var splitLayers:Array=[];''')
    s = one(s, '                initial.sourceLayers="fixed world cache plus one freshly drawn 512-square region; native UI retained";', '''                initial.sourceLayers="fixed world cache plus ordered-root region redraw; native UI retained";
                var graph:*=world.grafon;
                splitLayers=[graph.visBack,graph.visBack2,graph.visFront];
                for each(var objectLayer:* in graph.visObjs)splitLayers.push(objectLayer);
                // Only known empty wrapper Sprites may be flattened; unknown layers
                // and grouped effects remain a single native draw.
                initial.regionCullLimit="Filter/mask eligibility is memoized only because poses/styles are frozen. Not a production dynamic tracker.";''')
    s = one(s, '                refreshPixels.draw(root,refreshMatrix,null,null,null,true);', '                drawRegionItems();')
    s = one(s, '                savePixel("refresh-region-1",refreshPixels);', '''                savePixel("refresh-region-1",refreshPixels);
                var reference:BitmapData=null,referenceVisible:Boolean=root.visible;
                try {
                    reference=new BitmapData(512,512,true,0);++allocated;root.visible=true;
                    reference.draw(root,refreshMatrix,null,null,null,true);++copies;
                    savePixel("refresh-native-1",reference);
                } finally {root.visible=referenceVisible;if(reference){reference.dispose();++bitmapDisposals;}}''')
    s = one(s, '        private function upload(pixels:BitmapData):RectangleTexture {', '''        private function drawRegionItems():void {
            var container:DisplayObjectContainer=root as DisplayObjectContainer;
            var rootMatrix:Matrix=root.transform.concatenatedMatrix;rootMatrix.invert();
            for(var i:int=0;i<container.numChildren;++i) {
                var layer:DisplayObject=container.getChildAt(i);
                if(layer==null || !layer.visible || layer.alpha==0)continue;
                var children:DisplayObjectContainer=layer as DisplayObjectContainer;
                var flatten:Boolean=children!=null && splitLayers.indexOf(layer)>=0 && style(layer) && layer.scrollRect==null &&
                    neutralColor(layer.transform.colorTransform) && identity(layer.transform.matrix);
                if(flatten) {
                    // Masks crossing immediate siblings must remain grouped.
                    for(var k:int=0;k<children.numChildren;++k) {
                        var probe:DisplayObject=children.getChildAt(k);
                        if(probe!=null && probe.mask!=null){flatten=false;break;}
                    }
                }
                if(flatten)for(var j:int=0;j<children.numChildren;++j)drawRegionItem(children.getChildAt(j),rootMatrix);
                else drawRegionItem(layer,rootMatrix);
            }
        }
        private function identity(m:Matrix):Boolean {
            return m.a==1 && m.b==0 && m.c==0 && m.d==1 && m.tx==0 && m.ty==0;
        }
        private function cullSafe(node:DisplayObject):Boolean {
            if(knownRegionCull[node])return safeRegionCull[node];
            ++regionCullClassifications;
            var stack:Array=[node],safe:Boolean=true;
            while(stack.length) {
                var child:DisplayObject=stack.pop() as DisplayObject;
                if(child==null)continue;
                if(child.filters.length || child.mask!=null || child.scrollRect!=null || child.transform.matrix3D!=null){safe=false;break;}
                var branch:DisplayObjectContainer=child as DisplayObjectContainer;
                if(branch)for(var i:int=0;i<branch.numChildren;++i)stack.push(branch.getChildAt(i));
            }
            knownRegionCull[node]=true;safeRegionCull[node]=safe;return safe;
        }
        private function drawRegionItem(node:DisplayObject,inverseRoot:Matrix):void {
            ++regionRootQueries;
            if(node==null || !node.visible || node.alpha==0){++regionItemsSkipped;return;}
            var at:int=getTimer();
            if(cullSafe(node)) {
                var extent:Rectangle=node.getBounds(root);
                // One extra pixel retains antialiasing at the edge; filtered or
                // masked subtrees never use geometric culling.
                extent.inflate(1,1);
                if(!extent.intersects(refreshArea)){
                    ++regionItemsSkipped;regionSelectionMs+=getTimer()-at;return;
                }
            }
            var matrix:Matrix=node.transform.concatenatedMatrix;matrix.concat(inverseRoot);
            matrix.tx-=refreshArea.x;matrix.ty-=refreshArea.y;
            regionSelectionMs+=getTimer()-at;at=getTimer();
            refreshPixels.draw(node,matrix,node.transform.colorTransform,node.blendMode,null,true);
            ++regionItemsDrawn;regionItemDrawMs+=getTimer()-at;
        }
        private function upload(pixels:BitmapData):RectangleTexture {''')
    s = one(s, 'regionFirstAlphaBounds:regionFirstAlphaBounds};',
        'regionFirstAlphaBounds:regionFirstAlphaBounds,regionRootQueries:regionRootQueries,regionItemsDrawn:regionItemsDrawn,regionItemsSkipped:regionItemsSkipped,regionCullClassifications:regionCullClassifications,regionSelectionMs:regionSelectionMs,regionItemDrawMs:regionItemDrawMs};')
    return s


def runner_source():
    s = base.runner_source().replace('camera-stage3d-region-refresh-1', 'camera-stage3d-region-items-1')
    s = one(s, "end['allocated']==end['texturesCreated']+1", "end['allocated']==end['texturesCreated']+2")
    s = s.replace('camera bounded-region refresh cost', 'camera ordered-root region refresh cost')
    return s


if __name__ == '__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(), 'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(), 'utf-8')
    code = runner_source()
    ast.parse(code)
    (HERE/'run.py').write_text(code, 'utf-8')
    print('Generated ordered-root region cost diagnostic; no build or launch')
