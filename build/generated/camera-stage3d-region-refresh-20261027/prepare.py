"""Measure a bounded 512-square native redraw over the fixed whole-world cache."""
from pathlib import Path
import importlib.util
import ast

HERE = Path(__file__).resolve().parent
BASE = HERE.parent/'camera-stage3d-wholeworld-settle-20261027'
spec = importlib.util.spec_from_file_location('region_refresh_base', BASE/'prepare.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
one = base.one


def helper_source():
    s = base.helper_source().replace('camera-stage3d-wholeworld-settle-1', 'camera-stage3d-region-refresh-1')
    s = one(s, 'private var captureBounds:Rectangle;', 'private var captureBounds:Rectangle,captureIntersection:Rectangle;')
    s = one(s, 'captureBounds=captureBounds==null?viewport:captureBounds.union(viewport);',
        'captureBounds=captureBounds==null?viewport:captureBounds.union(viewport);\n'
        '                        captureIntersection=captureIntersection==null?viewport.clone():captureIntersection.intersection(viewport);')
    s = one(s, 'presenter.auditTimelines();presenter.prepareWorld(world,captureBounds);',
        'presenter.auditTimelines();presenter.configureRefreshArea(captureIntersection);presenter.prepareWorld(world,captureBounds);')
    s = one(s, 'Whole-world fixed snapshot plus backdrop on Stage3D; native UI remains. Frozen animation is a feasibility ceiling, never gameplay acceptance. Readback composition is not an OS screenshot.',
        'One fixed 512x512 world-space region is redrawn each GPU interval over the frozen whole-world cache. Cost diagnostic only: this does not track all dynamic objects or validate gameplay. Readback is not an OS screenshot.')
    return s


def renderer_source():
    s = base.renderer_source()
    s = one(s, 'private var backdropTexture:RectangleTexture;', '''private var backdropTexture:RectangleTexture;
        private var refreshArea:Rectangle,refreshIntersection:Rectangle,refreshScissor:Rectangle;
        private var refreshMatrix:Matrix,refreshPixels:BitmapData,refreshTexture:RectangleTexture;
        private var regionRasterCalls:int=0,regionRasterMs:int=0,regionUploadMs:int=0;
        private var regionFirstAlphaBounds:Object;''')
    s = one(s, '        public function prepareWorld(w:*,area:Rectangle):void {', '''        public function configureRefreshArea(intersection:Rectangle):void {
            require(!worldPrepared && refreshArea==null && intersection!=null,"Single bounded refresh area required");
            require(intersection.width>=512 && intersection.height>=512,"Prepared viewport intersection too small");
            refreshIntersection=intersection.clone();
            refreshArea=new Rectangle(Math.floor(intersection.x+(intersection.width-512)/2),
                Math.floor(intersection.y+(intersection.height-512)/2),512,512);
            require(intersection.containsRect(refreshArea),"Refresh area must be visible throughout route");
            refreshMatrix=new Matrix(1,0,0,1,-refreshArea.x,-refreshArea.y);
            refreshScissor=new Rectangle(0,0,512,512);
        }
        public function prepareWorld(w:*,area:Rectangle):void {''')
    s = one(s, '                worldPrepared=true;', '''                require(refreshArea!=null && bounds.containsRect(refreshArea),"Refresh area outside world capture");
                refreshPixels=new BitmapData(512,512,true,0);++allocated;
                refreshTexture=upload(refreshPixels);
                worldPrepared=true;
                initial.refreshArea={x:refreshArea.x,y:refreshArea.y,width:512,height:512};
                initial.refreshIntersection={x:refreshIntersection.x,y:refreshIntersection.y,width:refreshIntersection.width,height:refreshIntersection.height};
                initial.sourceLayers="fixed world cache plus one freshly drawn 512-square region; native UI retained";''')
    s = one(s, '        private function upload(pixels:BitmapData):RectangleTexture {', '''        private function refreshRegion():void {
            require(active && refreshPixels!=null && refreshTexture!=null,"Missing persistent region buffer");
            var at:int=getTimer(),wasVisible:Boolean=root.visible;
            try {
                root.visible=true;
                refreshPixels.fillRect(refreshPixels.rect,0);
                refreshPixels.draw(root,refreshMatrix,null,null,null,true);
                ++copies;++regionRasterCalls;
            } finally {root.visible=wasVisible;}
            regionRasterMs+=getTimer()-at;at=getTimer();
            refreshTexture.uploadFromBitmapData(refreshPixels);++uploads;regionUploadMs+=getTimer()-at;
            if(regionRasterCalls==1) {
                var occupied:Rectangle=refreshPixels.getColorBoundsRect(0xff000000,0,false);
                regionFirstAlphaBounds={x:occupied.x,y:occupied.y,width:occupied.width,height:occupied.height};
                savePixel("refresh-region-1",refreshPixels);
            }
        }
        private function upload(pixels:BitmapData):RectangleTexture {''')
    s = one(s, 'require(!root.visible && !backdrop.visible,"Native world was re-enabled");render(false);',
        'require(!root.visible && !backdrop.visible,"Native world was re-enabled");refreshRegion();render(false);')
    s = one(s, '            if(readback){context.drawToBitmapData(destination);++captures;}', '''            refreshScissor.x=refreshArea.x+m.tx;refreshScissor.y=refreshArea.y+m.ty;
            require(refreshScissor.x>=0 && refreshScissor.y>=0 && refreshScissor.right<=width && refreshScissor.bottom<=height,
                "Refresh region left prepared viewport intersection");
            context.setScissorRectangle(refreshScissor);
            try {
                // Opaque backdrop replaces the old world pixels, including pixels that
                // become transparent. Blending new content over the old tile would ghost.
                drawQuad(backdropTexture,0,0,width,height);
                drawQuad(refreshTexture,refreshScissor.x,refreshScissor.y,512,512);
            } finally {context.setScissorRectangle(null);}
            if(readback){context.drawToBitmapData(destination);++captures;}''')
    s = one(s, '            if(backdropTexture){backdropTexture.dispose();backdropTexture=null;++texturesDisposed;}',
        '''            if(refreshTexture){refreshTexture.dispose();refreshTexture=null;++texturesDisposed;}
            if(refreshPixels){refreshPixels.dispose();refreshPixels=null;++bitmapDisposals;}
            if(backdropTexture){backdropTexture.dispose();backdropTexture=null;++texturesDisposed;}''')
    s = one(s, 'frameScriptDrains:frameScriptDrains.concat()};',
        'frameScriptDrains:frameScriptDrains.concat(),regionRasterCalls:regionRasterCalls,regionRasterMs:regionRasterMs,regionUploadMs:regionUploadMs,regionFirstAlphaBounds:regionFirstAlphaBounds};')
    return s


def runner_source():
    s = base.runner_source().replace('camera-stage3d-wholeworld-settle-1', 'camera-stage3d-region-refresh-1')
    s = one(s, "assert end['enables']==end['restores'] and end['allocated']==end['disposed']==end['copies']",
        "assert end['enables']==end['restores'] and end['allocated']==end['disposed']")
    s = one(s, "assert end['texturesCreated']==end['texturesDisposed']>1 and end['allocated']==end['texturesCreated']+1", """assert end['texturesCreated']==end['texturesDisposed']>2 and end['allocated']==end['texturesCreated']+1
    assert end['regionRasterCalls']==493 and end['copies']==end['allocated']-1+493
    assert end['uploads']==end['texturesCreated']+493
    assert end['initial']['refreshArea']['width']==end['initial']['refreshArea']['height']==512
    assert end['regionFirstAlphaBounds']['width']>0 and end['regionFirstAlphaBounds']['height']>0""")
    s = one(s, "assert all(p[k]==first[k] for k in ('uploads','texturesCreated','allocated','disposed','copies','clipsStopped'))", """assert all(p[k]==first[k] for k in ('texturesCreated','allocated','disposed','clipsStopped'))
            assert p['copies']==p['allocated']-1+p['regionRasterCalls']
            assert p['uploads']==p['texturesCreated']+p['regionRasterCalls']""")
    s = one(s, "assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==first['copies']",
        "assert row['endAtMs']==previous and row['copiesEnd']-row['copiesStart']==(120 if cached else 0)")
    s = one(s, "'Whole-world fixed picture with identically frozen MovieClips; no animated gameplay or combat claim.',",
        "'Only a fixed 512-square region is refreshed, with identically frozen poses. No dynamic coverage or gameplay claim.',")
    s = s.replace('ContinuousScene / camera whole-world fixed-picture Stage3D / 01a13816',
        'ContinuousScene / camera bounded-region refresh cost / 01a13816')
    s = s.replace('960 frozen native versus whole-picture GPU intervals; feasibility only, no deployment',
        '960 native versus 512-square region refresh intervals; cost diagnostic only, no deployment')
    return s


if __name__ == '__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(), 'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(), 'utf-8')
    code = runner_source()
    ast.parse(code)
    (HERE/'run.py').write_text(code, 'utf-8')
    print('Generated bounded region refresh cost diagnostic; no build or launch')
