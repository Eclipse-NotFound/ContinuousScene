"""Measure full native viewport redraw plus texture upload on every GPU interval."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-stage3d-wholeworld-settle-20261027'
spec=importlib.util.spec_from_file_location('viewport_refresh_base',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():
    s=base.helper_source().replace('camera-stage3d-wholeworld-settle-1','camera-stage3d-viewport-refresh-1')
    s=one(s,'Whole-world fixed snapshot plus backdrop on Stage3D; native UI remains. Frozen animation is a feasibility ceiling, never gameplay acceptance. Readback composition is not an OS screenshot.',
        'Entire viewport is redrawn and uploaded on every GPU interval. Poses are frozen identically to isolate refresh cost; actual combat and OS-window acceptance remain untested.')
    return s
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var backdropTexture:RectangleTexture;', '''private var backdropTexture:RectangleTexture;
        private var worldPixels:BitmapData,worldTexture:RectangleTexture;
        private var fullRasterCalls:int=0,fullRasterMs:int=0,fullUploadMs:int=0;''')
    start=s.index('        public function prepareWorld(');end=s.index('        private function upload(',start)
    s=s[:start]+'''        public function prepareWorld(w:*,area:Rectangle):void {
            require(w===world && context && !worldPrepared && !active,"Single-use viewport preparation required");
            auditTimelines();require(root.visible && backdrop.visible,"Native world/backdrop must be visible");
            require(style(root) && root.scrollRect==null && unit(root.transform.concatenatedMatrix) && neutralColor(root.transform.concatenatedColorTransform),"Unsupported world style/transform");
            require(style(backdrop) && backdrop.scrollRect==null,"Unsupported backdrop style");
            require(!DisplayObjectContainer(root).contains(backdrop),"Backdrop cannot be inside world");
            var ancestor:DisplayObject=root.parent;
            while(ancestor && ancestor!==stage){require(style(ancestor) && neutralColor(ancestor.transform.colorTransform),"World ancestor effect unsupported");ancestor=ancestor.parent;}
            parents=[backdrop,root];parentVisible=[backdrop.visible,root.visible];
            var pixels:BitmapData=null;
            try {
                pixels=new BitmapData(width,height,true,0);++allocated;
                pixels.draw(backdrop,backdrop.transform.concatenatedMatrix,backdrop.transform.concatenatedColorTransform,null,null,true);++copies;
                require(pixels.getColorBoundsRect(0xff000000,0xff000000,false).isEmpty(),"Backdrop capture must be opaque");
                backdropTexture=upload(pixels);
                worldPixels=new BitmapData(width,height,true,0);++allocated;
                worldTexture=upload(worldPixels);textures.push({texture:worldTexture});
                worldPrepared=true;captureCullRestored=true;
                initial.captureBounds={width:width,height:height};initial.worldTiles=1;
                initial.sourceLayers="full viewport redrawn and uploaded every GPU interval; native UI retained";
                initial.timelineCount=clips.length;initial.clipsStopped=clipsStopped;
                initial.culling="native viewport culling untouched";
            } finally {if(pixels){pixels.dispose();++bitmapDisposals;}}
        }
        private function refreshWorld():void {
            require(active && worldPixels!=null && worldTexture!=null,"Missing persistent viewport buffer");
            var at:int=getTimer(),wasVisible:Boolean=root.visible;
            try {
                root.visible=true;
                worldPixels.fillRect(worldPixels.rect,0);
                worldPixels.draw(root,root.transform.concatenatedMatrix,null,null,null,true);
                ++copies;++fullRasterCalls;
            } finally {root.visible=wasVisible;}
            fullRasterMs+=getTimer()-at;at=getTimer();
            worldTexture.uploadFromBitmapData(worldPixels);++uploads;fullUploadMs+=getTimer()-at;
        }
'''+s[end:]
    s=one(s,'require(!root.visible && !backdrop.visible,"Native world was re-enabled");render(false);',
        'require(!root.visible && !backdrop.visible,"Native world was re-enabled");refreshWorld();render(false);')
    s=one(s,'''var m:Matrix=root.transform.concatenatedMatrix;
            for each(var t:Object in textures)drawQuad(t.texture,t.x+m.tx,t.y+m.ty,t.width,t.height);''',
        'drawQuad(worldTexture,0,0,width,height);')
    s=one(s,'for each(var t:Object in textures){t.texture.dispose();++texturesDisposed;}textures=[];',
        'for each(var t:Object in textures){t.texture.dispose();++texturesDisposed;}textures=[];worldTexture=null;\n            if(worldPixels){worldPixels.dispose();worldPixels=null;++bitmapDisposals;}')
    s=one(s,'frameScriptDrains:frameScriptDrains.concat()};',
        'frameScriptDrains:frameScriptDrains.concat(),fullRasterCalls:fullRasterCalls,fullRasterMs:fullRasterMs,fullUploadMs:fullUploadMs};')
    return s
def runner_source():
    s=base.runner_source().replace('camera-stage3d-wholeworld-settle-1','camera-stage3d-viewport-refresh-1')
    s=one(s,"assert end['enables']==end['restores'] and end['allocated']==end['disposed']==end['copies']", "assert end['enables']==end['restores'] and end['allocated']==end['disposed']==2")
    s=one(s,"assert end['texturesCreated']==end['texturesDisposed']>1 and end['allocated']==end['texturesCreated']+1", """assert end['texturesCreated']==end['texturesDisposed']==2
    assert end['fullRasterCalls']==493 and end['copies']==494 and end['uploads']==495""")
    s=one(s,"assert all(p[k]==first[k] for k in ('uploads','texturesCreated','allocated','disposed','copies','clipsStopped'))", """assert all(p[k]==first[k] for k in ('texturesCreated','allocated','disposed','clipsStopped'))
            assert p['copies']==p['fullRasterCalls']+1 and p['uploads']==p['fullRasterCalls']+2""")
    s=one(s,"assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==first['copies']", "assert row['endAtMs']==previous and row['copiesEnd']-row['copiesStart']==(120 if cached else 0)")
    s=one(s,"'Whole-world fixed picture with identically frozen MovieClips; no animated gameplay or combat claim.',", "'Viewport redrawn/uploaded every GPU interval with identical fixed poses; measures refresh cost, not animated gameplay.',")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Generated per-interval viewport redraw/upload diagnostic; no build or launch')
