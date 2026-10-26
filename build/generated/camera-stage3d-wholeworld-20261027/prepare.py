"""Generate an isolated whole-world, frozen-picture feasibility diagnostic."""
from pathlib import Path
import ast

HERE = Path(__file__).resolve().parent
SEED = HERE.parent/'camera-stage3d-entry-20261027'

def replace_one(source, old, new):
    assert source.count(old) == 1, (old[:90], source.count(old))
    return source.replace(old, new, 1)

def helper_source():
    s=(SEED/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig')
    s=replace_one(s,'camera-stage3d-entry-1','camera-stage3d-wholeworld-1')
    s=replace_one(s,'private var closed:Boolean=false;', 'private var closed:Boolean=false;\n        private var captureBounds:Rectangle;')
    s=replace_one(s,'World.onPause stops simulation; Flash timelines and other frame callbacks remain live.',
        'Simulation paused; currently playing world MovieClips stopped identically in both arms. Other callbacks remain live.')
    s=replace_one(s,'Hardware backdrop and two background layers; native objects, foreground and light remain. GPU readback plus Stage.draw is not OS screenshot acceptance.',
        'Whole-world fixed snapshot plus backdrop on Stage3D; native UI remains. Frozen animation is a feasibility ceiling, never gameplay acceptance. Readback composition is not an OS screenshot.')
    s=replace_one(s,'This is not an enemy-free gameplay run: simulation is paused, while timelines and other callbacks can continue.',
        'Not enemy-free or combat gameplay: world MovieClips and simulation are frozen. No production path or real animation compatibility.')
    s=replace_one(s,'prepareRoute=views.concat(route);prepareAt=getTimer();', '''prepareRoute=views.concat(route);
                for each(var validationPoint:Object in views)for each(var validationOffset:Object in [{x:1,y:0},{x:0,y:1},{x:120,y:120}])prepareRoute.push({x:validationPoint.x+validationOffset.x,y:validationPoint.y+validationOffset.y});
                prepareAt=getTimer();''')
    s=replace_one(s,'prepareBaseline=counters();report.preparePasses=[];presenter.prepareContext(w);',
        'prepareBaseline=counters();report.preparePasses=[];presenter.prepareContext(w);presenter.freezeTimelines(w);')
    s=replace_one(s,'if(grafon.sceneViewReady()) {presenter.update(world,true);presenter.clear();++cursor;retries=0;}', '''if(grafon.sceneViewReady()) {
                        var matrix:Matrix=world.visual.transform.concatenatedMatrix;
                        var viewport:Rectangle=new Rectangle(-matrix.tx,-matrix.ty,stage.stageWidth,stage.stageHeight);
                        captureBounds=captureBounds==null?viewport:captureBounds.union(viewport);
                        ++cursor;retries=0;
                    }''')
    s=replace_one(s,'phase=1;pixelAt=getTimer();', '''// Fixed native natural preparation before capturing the enlarged picture.
                            for(var warmIndex:int=0;warmIndex<views.length;++warmIndex) {
                                applyCamera(views[warmIndex].x,views[warmIndex].y);
                                warmNative(views[warmIndex],warmIndex);disposeOwned();
                            }
                            presenter.prepareWorld(world,captureBounds);report.frozenPicture=presenter.snapshot();
                            phase=1;pixelAt=getTimer();''')
    s=replace_one(s,'require(world.visual.visible===true,"World visibility changed");',
        'require(world.visual.visible===!presenter.active,"World visibility differs from active presentation");')
    s=replace_one(s,'var condition:int=order[segment];age=0;',
        'presenter.auditTimelines();\n            var condition:int=order[segment];age=0;')
    s=replace_one(s,'var a:BitmapData=capture();',
        'presenter.auditTimelines();var a:BitmapData=warmNative(point,100+index);')
    s=replace_one(s,'result.passed=result.candidate.maxRGB<=2 && result.candidate.maxAlpha==0 && result.restore.equal;', '''result.visualAccepted=result.candidate.maxRGB<=2 && result.candidate.maxAlpha==0;
                result.passed=result.visualAccepted && result.restore.equal;''')
    # Strict pixels: a failed snapshot does not proceed to the timing portion.
    s=replace_one(s,'        private function savePixel(name:String,data:BitmapData):void {',
        (HERE.parent/'camera-world-scroll-routewarm-20261027/warmup.as.inc').read_text('utf-8-sig')+
        '\n        private function savePixel(name:String,data:BitmapData):void {')
    s=s.replace('GPU background','GPU whole-world snapshot')
    return s

def renderer_source():
    seed=(SEED/'SceneTilePresentation.as').read_text('utf-8-sig')
    imports=seed[:seed.index('    /** Terminal')]
    imports=imports.replace('    import flash.geom.Rectangle;', '    import flash.geom.Rectangle;\n    import flash.geom.Point;')
    shader=seed[seed.index('        private function shader('):seed.index('        private function style(')]
    styles=seed[seed.index('        private function style('):]
    return imports+(HERE/'renderer.as.inc').read_text('utf-8-sig')+shader+styles

def runner_source():
    s=(SEED/'run.py').read_text('utf-8-sig')
    s=replace_one(s,'Hardware backdrop and native background textures; terminal diagnostic only.',
        'Whole-world fixed-picture Stage3D feasibility; not gameplay acceptance.')
    s=s.replace('camera-stage3d-entry-1','camera-stage3d-wholeworld-1')
    start=s.index('def summarize(raw):')
    end=s.index('\ndef main():',start)
    s=s[:start]+(HERE/'summarize.py.inc').read_text('utf-8-sig')+s[end:]
    s=s.replace('camera Stage3D backgrounds','camera whole-world fixed-picture Stage3D')
    s=s.replace('960 native versus hardware background frames; diagnostic only, no deployment',
        '960 frozen native versus whole-picture GPU intervals; feasibility only, no deployment')
    return s

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    runner=runner_source();ast.parse(runner)
    (HERE/'run.py').write_text(runner,'utf-8')
    print('Generated isolated whole-world diagnostic sources; no build or launch')
