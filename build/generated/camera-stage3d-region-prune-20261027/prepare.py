"""One whole-root region draw with conservatively bounded shadow roots hidden."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-stage3d-region-refresh-20261027'
spec=importlib.util.spec_from_file_location('region_prune_base',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one


def helper_source():
    s=base.helper_source().replace('camera-stage3d-region-refresh-1','camera-stage3d-region-prune-1').replace(
        'One fixed 512x512 world-space region is redrawn each GPU interval over the frozen whole-world cache.',
        'One fixed 512-square region uses a whole-root native draw with conservatively bounded shadow roots temporarily hidden. Frozen pose bounds only; not a dynamic tracker.')
    return one(s,'report.frozenPicture=presenter.snapshot();',
        'report.cullInventory=presenter.cullEvidence();report.frozenPicture=presenter.snapshot();')


def renderer_source():
    s=base.renderer_source()
    s=one(s,'    import flash.geom.ColorTransform;', '    import flash.filters.BitmapFilter;\n    import flash.geom.ColorTransform;')
    s=one(s,'private var regionFirstAlphaBounds:Object;', '''private var regionFirstAlphaBounds:Object;
        private var cullRoots:Array=[],cullHidden:Array=[],cullChecks:Array=[],cullInventory:Array=[];
        private var maskOwners:Dictionary=new Dictionary();
        private var cullReference:BitmapData;
        private var cullCalls:int=0,cullWrites:int=0,cullRestores:int=0,cullVerifyDraws:int=0;
        private var boundsImagesAllocated:int=0,boundsImagesDisposed:int=0,boundsPeakBytes:Number=0;
        private var boundsNodes:int=0,cullScanned:int=0,cullUnsupported:int=0,cullPrepareMs:int=0;
        private var cullRestored:Boolean=true;''')
    s=one(s,'                refreshTexture=upload(refreshPixels);',
        '                refreshTexture=upload(refreshPixels);\n                cullReference=new BitmapData(512,512,true,0);++allocated;')
    s=one(s,'require(captureCullRestored,"Capture culling flag did not restore");auditTimelines();',
        'require(captureCullRestored,"Capture culling flag did not restore");auditTimelines();prepareCullRoots();')
    s=one(s,'                refreshPixels.draw(root,refreshMatrix,null,null,null,true);', '                drawCulledRegion();')
    s=one(s,'refreshTexture.uploadFromBitmapData(refreshPixels);++uploads;regionUploadMs+=getTimer()-at;',
        'refreshTexture.uploadFromBitmapData(refreshPixels);++uploads;regionUploadMs+=getTimer()-at;\n            if(regionRasterCalls<=13)verifyCulledRegion();')
    s=one(s,'        private function upload(pixels:BitmapData):RectangleTexture {', '''        private function prepareCullRoots():void {
            var at:int=getTimer(),stack:Array=[stage];
            while(stack.length) {
                var visited:DisplayObject=stack.pop() as DisplayObject;if(visited==null)continue;
                var mask:DisplayObject=visited.mask;
                while(mask!=null){maskOwners[mask]=true;mask=mask.parent;}
                var branch:DisplayObjectContainer=visited as DisplayObjectContainer;
                if(branch)for(var k:int=0;k<branch.numChildren;++k)stack.push(branch.getChildAt(k));
            }
            for each(var layer:DisplayObjectContainer in world.grafon.visObjs) {
                if(!layer.visible || !style(layer) || layer.scrollRect!=null || !neutralColor(layer.transform.colorTransform))continue;
                var lm:Matrix=layer.transform.matrix;
                if(lm.a!=1 || lm.b!=0 || lm.c!=0 || lm.d!=1 || lm.tx!=0 || lm.ty!=0)continue;
                for(var i:int=0;i<layer.numChildren;++i) {
                    var node:DisplayObject=layer.getChildAt(i);if(node==null || !node.visible || node.alpha==0)continue;
                    ++cullScanned;if(maskOwners[node]){++cullUnsupported;continue;}
                    boundsNodes=0;
                    var result:Object=effectBounds(node);
                    if(result==null){++cullUnsupported;continue;}
                    if(!result.shadow)continue;
                    var extent:Rectangle=mapRect(result.rect,node.transform.matrix);
                    extent.inflate(2,2);
                    if(extent.intersects(refreshArea))continue;
                    cullRoots.push({node:node,parent:layer,extent:extent,matrix:node.transform.matrix});
                    cullInventory.push({className:getQualifiedClassName(node),name:node.name,
                        extent:{x:extent.x,y:extent.y,width:extent.width,height:extent.height}});
                }
            }
            require(cullRoots.length>0 && cullRoots.length<2500,"No bounded shadow roots selected");
            cullPrepareMs=getTimer()-at;
            initial.cullLimit="Bounds memoized for frozen poses only; live changes need invalidation before production.";
            initial.cullCount=cullRoots.length;
        }
        public function cullEvidence():Array {return cullInventory.concat();}
        private function rigid(m:Matrix):Boolean {
            return m!=null && Math.abs(m.a)==1 && m.b==0 && m.c==0 && Math.abs(m.d)==1 &&
                isFinite(m.tx) && isFinite(m.ty);
        }
        private function mapRect(rect:Rectangle,m:Matrix):Rectangle {
            var a:Point=m.transformPoint(new Point(rect.left,rect.top));
            var b:Point=m.transformPoint(new Point(rect.right,rect.bottom));
            return new Rectangle(Math.min(a.x,b.x),Math.min(a.y,b.y),Math.abs(b.x-a.x),Math.abs(b.y-a.y));
        }
        private function effectBounds(node:DisplayObject):Object {
            // Restrict transforms to unit translations/reflections so filter pixel
            // extents cannot shrink under scale. Masks and scrollRect stay native.
            if(++boundsNodes>1024 || node.mask!=null || node.scrollRect!=null || node.transform.matrix3D!=null ||
                !rigid(node.transform.matrix) || maskOwners[node])return null;
            var extent:Rectangle=node.getBounds(node),shadow:Boolean=false;
            if(!isFinite(extent.x) || !isFinite(extent.y) || !isFinite(extent.width) || !isFinite(extent.height))return null;
            var branch:DisplayObjectContainer=node as DisplayObjectContainer;
            if(branch)for(var i:int=0;i<branch.numChildren;++i) {
                var child:DisplayObject=branch.getChildAt(i);if(child==null)continue;
                var childBounds:Object=effectBounds(child);if(childBounds==null)return null;
                extent=extent.union(mapRect(childBounds.rect,child.transform.matrix));shadow=shadow||childBounds.shadow;
            }
            for each(var filter:BitmapFilter in node.filters) {
                var kind:String=getQualifiedClassName(filter);
                if(kind!="flash.filters::DropShadowFilter" && kind!="flash.filters::GlowFilter" &&
                    kind!="flash.filters::BlurFilter" && kind!="flash.filters::ColorMatrixFilter")return null;
                if(kind=="flash.filters::DropShadowFilter")shadow=true;
                var w:int=Math.ceil(extent.width)+4,h:int=Math.ceil(extent.height)+4;
                if(w<1 || h<1 || w>2048 || h>2048)return null;
                var probe:BitmapData=null;
                try {
                    probe=new BitmapData(w,h,true,0);++allocated;++boundsImagesAllocated;
                    boundsPeakBytes=Math.max(boundsPeakBytes,w*h*4);
                    // The API uses the actual BitmapData size for clipping filters.
                    // Use the full same-sized source, never a one-pixel placeholder.
                    var output:Rectangle=probe.generateFilterRect(probe.rect,filter);
                    if(!isFinite(output.x) || !isFinite(output.y) || !isFinite(output.width) || !isFinite(output.height))return null;
                    var padX:Number=Math.max(0,-output.left,output.right-w)+2;
                    var padY:Number=Math.max(0,-output.top,output.bottom-h)+2;
                    // Symmetric expansion remains conservative under reflections.
                    extent.inflate(padX,padY);
                } finally {if(probe){probe.dispose();++bitmapDisposals;++boundsImagesDisposed;}}
            }
            return {rect:extent,shadow:shadow};
        }
        private function drawCulledRegion():void {
            require(cullHidden.length==0,"Prior region visibility not restored");cullRestored=false;
            try {
                for each(var item:Object in cullRoots) {
                    require(item.node.parent===item.parent && sameMatrix(item.node.transform.matrix,item.matrix),"Frozen cull root moved");
                    if(item.node.visible){cullHidden.push(item.node);item.node.visible=false;++cullWrites;}
                }
                refreshPixels.draw(root,refreshMatrix,null,null,null,true);++cullCalls;
            } finally {
                for each(var changed:DisplayObject in cullHidden){changed.visible=true;++cullRestores;}
                cullHidden.length=0;cullRestored=true;
            }
        }
        private function verifyCulledRegion():void {
            var wasVisible:Boolean=root.visible,comparison:Object=null;
            try {
                root.visible=true;cullReference.fillRect(cullReference.rect,0);
                cullReference.draw(root,refreshMatrix,null,null,null,true);++copies;++cullVerifyDraws;
                comparison=cullReference.compare(refreshPixels);
                var equal:Boolean=comparison is Number && Number(comparison)==0;
                cullChecks.push({call:regionRasterCalls,equal:equal,selected:cullRoots.length,restored:cullRestored});
                if(regionRasterCalls==1 || !equal) {
                    savePixel("cull-native-"+regionRasterCalls,cullReference);
                    savePixel("cull-pruned-"+regionRasterCalls,refreshPixels);
                }
                require(equal,"Conservative shadow bounds changed region pixels");
            } finally {
                root.visible=wasVisible;
                if(comparison is BitmapData){++allocated;BitmapData(comparison).dispose();++bitmapDisposals;}
            }
        }
        private function upload(pixels:BitmapData):RectangleTexture {''')
    s=one(s,'            if(refreshPixels){refreshPixels.dispose();refreshPixels=null;++bitmapDisposals;}',
        '            if(refreshPixels){refreshPixels.dispose();refreshPixels=null;++bitmapDisposals;}\n            if(cullReference){cullReference.dispose();cullReference=null;++bitmapDisposals;}')
    s=one(s,'regionFirstAlphaBounds:regionFirstAlphaBounds};',
        'regionFirstAlphaBounds:regionFirstAlphaBounds,cullCalls:cullCalls,cullWrites:cullWrites,cullRestores:cullRestores,cullRestored:cullRestored,cullPending:cullHidden.length,cullVerifyDraws:cullVerifyDraws,cullChecks:cullChecks.concat(),cullScanned:cullScanned,cullUnsupported:cullUnsupported,cullPrepareMs:cullPrepareMs,boundsImagesAllocated:boundsImagesAllocated,boundsImagesDisposed:boundsImagesDisposed,boundsPeakBytes:boundsPeakBytes};')
    return s


def runner_source():
    s=base.runner_source().replace('camera-stage3d-region-refresh-1','camera-stage3d-region-prune-1')
    s=one(s,"end['allocated']==end['texturesCreated']+1", "end['allocated']==end['texturesCreated']+2+end['boundsImagesAllocated']")
    s=one(s,"end['copies']==end['allocated']-1+493", "end['copies']==end['allocated']-end['boundsImagesAllocated']-2+493+13")
    s=one(s,"assert end['uploads']==end['texturesCreated']+493", """assert end['uploads']==end['texturesCreated']+493
    assert end['cullCalls']==493 and end['cullVerifyDraws']==13
    assert end['cullWrites']==end['cullRestores'] and end['cullRestored'] and end['cullPending']==0
    assert end['boundsImagesAllocated']==end['boundsImagesDisposed']>0
    assert len(end['cullChecks'])==13 and all(x['equal'] and x['restored'] for x in end['cullChecks'])""")
    s=one(s,"assert p['copies']==p['allocated']-1+p['regionRasterCalls']", """assert p['copies']==p['allocated']-p['boundsImagesAllocated']-2+p['regionRasterCalls']+13
            assert p['cullCalls']==p['regionRasterCalls'] and p['cullVerifyDraws']==13
            assert p['cullRestored'] and p['cullWrites']==p['cullRestores'] and p['cullPending']==0""")
    return s.replace('camera bounded-region refresh cost','camera bounded-shadow batch pruning cost')


if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    code=runner_source();ast.parse(code);(HERE/'run.py').write_text(code,'utf-8')
    patch=(BASE/'probe_patch.py').read_text('utf-8-sig')
    patch=patch.replace('camera-stage3d-wholeworld-settle-20261027/probe_patch.py','camera-stage3d-region-refresh-20261027/probe_patch.py')
    patch=patch.replace('region_refresh_patch_seed','region_prune_patch_seed').replace('region_refresh_generation','region_prune_generation')
    ast.parse(patch);(HERE/'probe_patch.py').write_text(patch,'utf-8')
    print('Generated conservative shadow-root batch pruning diagnostic; no build or launch')
