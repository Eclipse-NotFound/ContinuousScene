"""Exact 29AF SMG source: viewport union + terminal read-only Box census."""
from pathlib import Path
import hashlib
import shutil

HERE = Path(__file__).resolve().parent
VERSION = 'static-box-census-runner-1'
SOURCE_PROBE = '29AF34571E7181139C682AA32A160E2C217C1B02B295E6DCBD6931D8DB7F94E5'
MAIN_RAW_SHA = '5087CBB3D6FA9E1F92E1F24D5D386D7CA48F7D5974F56352AB8DEC25CE856333'
CHANGED = ['ContinuousSceneMotionProbe.as', 'tests/SceneStaticBoxCensus.as']

OBSERVER = '''        // Read-only inverse display transform: includes actual zoom, shake and ancestry.
        private static function staticBoxViewportSample():Array {
            if(!w || !w.visual || w.visual.stage!==main.stage || w.loc!==loc)
                throw new Error("Static Box viewport lost original world/stage");
            if(staticBoxVisual==null)staticBoxVisual=w.visual;
            if(staticBoxVisual!==w.visual)throw new Error("Static Box visual identity changed");
            var sw:Number=main.stage.stageWidth,sh:Number=main.stage.stageHeight;
            var matrix:Matrix=w.visual.transform.concatenatedMatrix.clone();
            var det:Number=matrix.a*matrix.d-matrix.b*matrix.c;
            if(!isFinite(sw) || !isFinite(sh) || sw<=0 || sh<=0 ||
                !isFinite(matrix.a) || !isFinite(matrix.b) || !isFinite(matrix.c) || !isFinite(matrix.d) ||
                !isFinite(matrix.tx) || !isFinite(matrix.ty) || !isFinite(det) || det==0)
                throw new Error("Static Box viewport transform invalid");
            matrix.invert();
            var x0:Number=matrix.tx,y0:Number=matrix.ty;
            var x1:Number=matrix.a*sw+matrix.tx,y1:Number=matrix.b*sw+matrix.ty;
            var x2:Number=matrix.c*sh+matrix.tx,y2:Number=matrix.d*sh+matrix.ty;
            var x3:Number=x1+matrix.c*sh,y3:Number=y1+matrix.d*sh;
            var left:Number=Math.min(x0,x1,x2,x3),right:Number=Math.max(x0,x1,x2,x3);
            var top:Number=Math.min(y0,y1,y2,y3),bottom:Number=Math.max(y0,y1,y2,y3);
            if(!isFinite(left) || !isFinite(top) || !isFinite(right) || !isFinite(bottom) ||
                right<=left || bottom<=top)throw new Error("Static Box viewport bounds invalid");
            if(staticBoxViewportUnion==null)staticBoxViewportUnion=new Rectangle(left,top,right-left,bottom-top);
            else {
                var ul:Number=Math.min(staticBoxViewportUnion.left,left),ut:Number=Math.min(staticBoxViewportUnion.top,top);
                var ur:Number=Math.max(staticBoxViewportUnion.right,right),ub:Number=Math.max(staticBoxViewportUnion.bottom,bottom);
                staticBoxViewportUnion.x=ul;staticBoxViewportUnion.y=ut;
                staticBoxViewportUnion.width=ur-ul;staticBoxViewportUnion.height=ub-ut;
            }
            ++staticBoxViewportCount;
            return [sw,sh,matrix.a,matrix.b,matrix.c,matrix.d,matrix.tx,matrix.ty,left,top,right,bottom];
        }
'''

TERMINAL = '''            if(error==null && report.samples.length==4 && w && w.grafon.sceneLarge) {
                try {
                    report.staticBoxCensus={startedAtMs:getTimer(),afterFinalSample:true,
                        diagnosticOnly:true,performanceEligible:false,viewportObservations:staticBoxViewportCount,
                        coordinateSpace:"w.visual",routeSamples:1200,segmentBoundaries:4,
                        viewportColumns:["stageWidth","stageHeight","inverseA","inverseB","inverseC","inverseD",
                            "inverseTX","inverseTY","left","top","right","bottom"]};
                    if(cfg.drawControl!="rcnative" || staticBoxViewportCount!=1204 || staticBoxViewportUnion==null)
                        throw new Error("Static Box census requires all route viewports");
                    report.staticBoxCensus.viewportUnion={x:staticBoxViewportUnion.x,y:staticBoxViewportUnion.y,
                        width:staticBoxViewportUnion.width,height:staticBoxViewportUnion.height};
                    report.staticBoxCensus.data=SceneStaticBoxCensus.read(w,staticBoxViewportUnion);
                    report.staticBoxCensus.endedAtMs=getTimer();
                    if(!report.staticBoxCensus.data.complete || report.staticBoxCensus.data.truncated ||
                        report.staticBoxCensus.data.errors.length>0 || !report.staticBoxCensus.data.contextUnchanged)
                        throw new Error("Static Box terminal census incomplete");
                } catch(staticBoxError:*) {
                    if(report.staticBoxCensus)report.staticBoxCensus.endedAtMs=getTimer();
                    error="Static Box census failed: "+String(staticBoxError);
                }
            }
'''

EDITS = (
    ('    import flash.geom.Rectangle;', '    import flash.geom.Rectangle;\n    import flash.geom.Matrix;'),
    ('    import tests.SceneActivityCensus;', '    import tests.SceneActivityCensus;\n    import tests.SceneStaticBoxCensus;'),
    ('        private static var continuousPreviousSampleAt:int=-1;',
     '        private static var continuousPreviousSampleAt:int=-1;\n'
     '        private static var staticBoxViewportUnion:Rectangle=null,staticBoxVisual:*=null;\n'
     '        private static var staticBoxViewportCount:int=0;'),
    ('            if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];',
     '            if(cfg.drawControl)cases=["draw-baseline-a","draw-control-b","draw-control-b-repeat","draw-baseline-a-repeat"];\n'
     '            if(cfg.drawControl!="rcnative" || cfg.benchmark!="scene" || !cfg.nativeInputMotion || !cfg.nativeSprint ||\n'
     '                !cfg.playerFire || !cfg.fixedEnemies || !cfg.combatRoute || !cfg.stableMotion || cfg.presentationCheck || cfg.sleepingRootShort)\n'
     '                throw new Error("Static Box census requires unchanged four-window native SMG fixture");'),
    ('        private static function finish(error:String=null):void {', OBSERVER + '        private static function finish(error:String=null):void {'),
    ('            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {',
     '            closeProbeTiming(true);\n' + TERMINAL + '            if(cfg.drawControl=="atlas") {'),
    ('            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
     '            row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;\n'
     '            row.staticBoxViewports=[];row.staticBoxViewportMs=[];\n'
     '            var boxBoundaryAt:int=getTimer();\n'
     '            row.staticBoxViewportBoundary=staticBoxViewportSample();\n'
     '            row.staticBoxViewportBoundaryMs=getTimer()-boxBoundaryAt;'),
    ('                    var now:int=getTimer();\n                    if(continuousPreviousSampleAt<0)',
     '                    var boxViewportAt:int=getTimer();\n'
     '                    row.staticBoxViewports.push(staticBoxViewportSample());\n'
     '                    row.staticBoxViewportMs.push(getTimer()-boxViewportAt);\n'
     '                    var now:int=getTimer();\n                    if(continuousPreviousSampleAt<0)'),
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def reverse(source):
    for old, new in reversed(EDITS):
        assert source.count(new) == 1, new
        source = source.replace(new, old, 1)
    return source


def transform(source):
    original = source
    for old, new in EDITS:
        assert source.count(old) == 1, old
        source = source.replace(old, new, 1)
    assert reverse(source) == original
    return source


def prepare(source, destination):
    assert not destination.exists()
    assert sha(source / 'ContinuousSceneMotionProbe.as') == MAIN_RAW_SHA
    assert len([p for p in source.rglob('*') if p.is_file()]) == 85
    shutil.copytree(source, destination)
    (destination / 'ContinuousSceneMotionProbe.as').write_text(transform(
        (source / 'ContinuousSceneMotionProbe.as').read_text('utf-8-sig')), 'utf-8')
    shutil.copy2(HERE / 'SceneStaticBoxCensus.as', destination / 'tests/SceneStaticBoxCensus.as')
