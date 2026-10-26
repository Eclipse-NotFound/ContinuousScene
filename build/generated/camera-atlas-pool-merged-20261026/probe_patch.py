from pathlib import Path
import importlib.util
import shutil
import hashlib

HERE=Path(__file__).resolve().parent
PAGED=HERE.parent/'camera-atlas-paged-20261025'
POOL=HERE
HELPER=HERE/'tests/SceneCameraRasterTrial.as'
CHANGED=['ContinuousSceneMotionProbe.as','SceneRasterPresentation.as','tests/SceneCameraRasterTrial.as']
VERSION='camera-atlas-pool-merged-1'
PRESENTER_SHA='BC0BCA76989B2C2A323D723BD4240F79A1EA48B5F69316A00F9F5D75C1B91E63'

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
paged_patch=load('pool_paused_paged_patch',PAGED/'probe_patch.py')
pool_patch=load('pool_paused_pool_patch',HERE.parent/'camera-atlas-pool-20261026'/'probe_patch.py')

def transform_main(source):
    value=paged_patch.transform(source)
    before='if(cfg.drawControl=="atlas") {\n                if(cfg.benchmark!="scene"'
    after='if(cfg.drawControl=="atlas" && !cfg.presentationCheck) {\n                if(cfg.benchmark!="scene"'
    assert value.count(before)==1
    changed=value.replace(before,after,1)
    assert changed.replace(after,before,1)==value
    return changed

def helper_source():
    value=(PAGED/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig')
    edits=[('version:"camera-atlas-paged-trial-2"','version:"camera-atlas-pool-merged-1",poolPreparation:[]'),
        ('report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();',
         'report.prepareMs=getTimer()-prepareAt;report.prepareEnd=snapshot();preparePool("before-pixels");'),
        ('presenter.clear();applyCamera(views[0].x,views[0].y);',
         'presenter.clear();applyCamera(views[0].x,views[0].y);preparePool("before-timing");'),
        ('presenter.update(world,row.atlas);',
         'if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();'),
        ('        private function applyFrame():void {',
'''        private function preparePool(label:String):void {
            var item:Object={label:label,startedAtMs:getTimer(),before:presenter.snapshot(),memoryBefore:System.totalMemory};
            presenter.preallocate(world);
            item.endedAtMs=getTimer();item.after=presenter.snapshot();item.memoryAfter=System.totalMemory;
            report.poolPreparation.push(item);
        }

        private function applyFrame():void {''')]
    original=value
    for before,after in edits:
        assert value.count(before)==1,(before,value.count(before));value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):
        assert reverse.count(after)==1;reverse=reverse.replace(after,before,1)
    assert reverse==original
    return value


original_helper_source=helper_source
def helper_source():
    source=original_helper_source()
    edits=[('row.atlasStates.push(pending.atlas);',
        'row.atlasStates.push(pending.atlas);row.cameraMs.push(pending.cameraMs);row.presenterMs.push(pending.presenterMs);row.guardMs.push(pending.guardMs);row.snapshotMs.push(pending.snapshotMs);'),
        ('workMs:[],presented:[],atlasStates:[],','workMs:[],presented:[],atlasStates:[],cameraMs:[],presenterMs:[],guardMs:[],snapshotMs:[],'),
        ('            if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();',
         '            var cameraEnd:int=getTimer();\n            if(row.atlas)presenter.update(world,true);else presenter.useNativeForTest();\n            var presenterEnd:int=getTimer();'),
        ('            checkTransform();guard();\n            pending=',
         '            checkTransform();guard();var guardEnd:int=getTimer();\n            pending='),
        ('atlas:presenter.snapshot(),workMs:getTimer()-at};',
         'atlas:presenter.snapshot(),workMs:getTimer()-at};\n            var end:int=getTimer();pending.workMs=end-at;\n            pending.cameraMs=cameraEnd-at;pending.presenterMs=presenterEnd-cameraEnd;\n            pending.guardMs=guardEnd-presenterEnd;pending.snapshotMs=end-guardEnd;')]
    result=source
    for before,after in edits:
        assert result.count(before)==1,(before,result.count(before));result=result.replace(before,after,1)
    reverse=result
    for before,after in reversed(edits):
        assert reverse.count(after)==1;reverse=reverse.replace(after,before,1)
    assert reverse==source
    return result


PRESENTER_EDITS=[
    ('        public var copies:int=0;', '        private var stationarySkips:int=0;\n        public var copies:int=0;'),
    ('            var view:Rectangle=g.sceneViewport();',
'            // beginFrame already restored native tiles. Nothing cached is shown\n            // at rest; native mutations remain visible immediately. Movement\n            // resumes through the complete revision/visibility synchronization.\n            if(!forcePresentation && poseValid && nextX==poseX && nextY==poseY && nextScale==poseScale){\n                ++stationarySkips;return;\n            }\n            var view:Rectangle=g.sceneViewport();'),
    ('return {version:"atlas-pool-1",', 'return {version:"atlas-pool-1",stationarySkips:stationarySkips,')]

PRESENTER_EDITS += [('        private var stationarySkips:int=0;', '        private var stationarySkips:int=0;\n        private var alphaRectChecks:int=0,emptyCopiesAvoided:int=0;'), ('for each(page in pages)if(required[page.key])for each(var bitmap:Bitmap in page.layers)bitmap.visible=true;', 'for each(page in pages)if(required[page.key])for(var displayLayer:int=0;displayLayer<4;++displayLayer)page.layers[displayLayer].visible=page.content[displayLayer];'), ('page.key=px+":"+py;page.px=px;page.py=py;page.used=clock;page.cells=new Array(16);', 'page.key=px+":"+py;page.px=px;page.py=py;page.used=clock;page.cells=new Array(16);page.content=[false,false,false,false];'), ('        private function syncPage(page:Object,byCell:Object,parents:Array,toHide:Array):void {\n            for(var cell:int=0;cell<16;++cell){', '        private function syncPage(page:Object,byCell:Object,parents:Array,toHide:Array):void {\n            page.content=[false,false,false,false];\n            for(var cell:int=0;cell<16;++cell){'), ('record={entry:null,revision:NaN,sources:[null,null,null,null],shown:[false,false,false,false]};', 'record={entry:null,revision:NaN,sources:[null,null,null,null],shown:[false,false,false,false],hasPixels:[false,false,false,false]};'), ('                            if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);\n                            page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;', '                            if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);\n                            var wasNonempty:Boolean=record.hasPixels[i];\n                            // Bounds intersection is conservative: false proves the\n                            // entire centre transparent; true may still include holes.\n                            record.hasPixels[i]=source.getColorBoundsRect(0xFF000000,0,false).intersects(sourceRect);\n                            ++alphaRectChecks;\n                            if(record.hasPixels[i]){page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;}\n                            else {\n                                if(wasNonempty){page.data[i].fillRect(page.rects[cell],0);++cellClears;}\n                                ++emptyCopiesAvoided;\n                            }'), ('                        toHide.push(bitmap);\n                    } else if(record.shown[i])', '                        if(record.hasPixels[i])page.content[i]=true;\n                        toHide.push(bitmap);\n                    } else if(record.shown[i])'), ('rows.push({key:page.key,px:page.px,py:page.py,used:page.used,layers:page.layers.length,visible:shown});', 'rows.push({key:page.key,px:page.px,py:page.py,used:page.used,layers:page.layers.length,visible:shown,layerHasPixels:page.content.concat(),layerVisible:[page.layers[0].visible,page.layers[1].visible,page.layers[2].visible,page.layers[3].visible]});'), ('return {version:"atlas-pool-1",stationarySkips:stationarySkips,', 'return {version:"atlas-pool-1",stationarySkips:stationarySkips,alphaRectChecks:alphaRectChecks,emptyCopiesAvoided:emptyCopiesAvoided,')]

PRESENTER_EDITS += [('    import flash.geom.Rectangle;', '    import flash.geom.Rectangle;\n    import flash.utils.Dictionary;'), ('        private var alphaRectChecks:int=0,emptyCopiesAvoided:int=0;', '        private var alphaRectChecks:int=0,emptyCopiesAvoided:int=0,backgroundMerges:int=0;'), ('            if(!surfaces.length){fallback("no-native-surfaces");return;}', '            if(!surfaces.length){fallback("no-native-surfaces");return;}\n            if(!backgroundCompatible(parents,surfaces)){fallback("background-order-or-effects");return;}'), ('        private function fallback(reason:String):void {', '        private function backgroundCompatible(parents:Array,surfaces:Array):Boolean {\n            var lower:DisplayObjectContainer=parents[1],upper:DisplayObjectContainer=parents[2];\n            if(lower.parent==null || lower.parent!==upper.parent ||\n                lower.parent.getChildIndex(upper)!=lower.parent.getChildIndex(lower)+1)return false;\n            var allowed:Dictionary=new Dictionary();\n            for each(var s:Object in surfaces){allowed[s.bitmaps[1]]=true;allowed[s.bitmaps[2]]=true;}\n            for each(var p:Object in pages){allowed[p.layers[1]]=true;allowed[p.layers[2]]=true;}\n            for each(var parent:DisplayObjectContainer in [lower,upper]) {\n                if(!parent.visible || parent.alpha!=1 || parent.x!=0 || parent.y!=0 || parent.scaleX!=1 || parent.scaleY!=1 ||\n                    parent.rotation!=0 || parent.blendMode!="normal" || parent.mask!=null || parent.filters.length!=0 ||\n                    parent.scrollRect!=null || parent.transform.matrix3D!=null)return false;\n                var color:*=parent.transform.colorTransform;\n                if(color.redMultiplier!=1 || color.greenMultiplier!=1 || color.blueMultiplier!=1 || color.alphaMultiplier!=1 ||\n                    color.redOffset!=0 || color.greenOffset!=0 || color.blueOffset!=0 || color.alphaOffset!=0)return false;\n                for(var index:int=0;index<parent.numChildren;++index) {\n                    var child:*=parent.getChildAt(index);\n                    if(child.visible && !allowed[child])return false;\n                }\n            }\n            return true;\n        }\n\n        private function fallback(reason:String):void {'), ('                        for(i=0;i<4;++i)if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}\n                        page.cells[cell]=null;', '                        for(i=0;i<4;++i)if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}\n                        if(record.shown[1] && !record.shown[2]){page.data[2].fillRect(page.rects[cell],0);++cellClears;}\n                        page.cells[cell]=null;'), ('                var changed:Boolean=record.entry!==surface || record.revision!==surface.revision;\n                var sourceRect:Rectangle=null;', '                var changed:Boolean=record.entry!==surface || record.revision!==surface.revision;\n                var backgroundChanged:Boolean=changed || record.sources[1]!==surface.nativeBuffers[1] ||\n                    record.sources[2]!==surface.nativeBuffers[2] || record.shown[1]!==surface.bitmaps[1].visible ||\n                    record.shown[2]!==surface.bitmaps[2].visible;\n                var sourceRect:Rectangle=null;'), ('                            if(record.hasPixels[i]){page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;}\n                            else {\n                                if(wasNonempty){page.data[i].fillRect(page.rects[cell],0);++cellClears;}\n                                ++emptyCopiesAvoided;\n                            }', '                            if(i==0 || i==3) {\n                                if(record.hasPixels[i]){page.data[i].copyPixels(source,sourceRect,page.points[cell]);++copies;}\n                                else {\n                                    if(wasNonempty){page.data[i].fillRect(page.rects[cell],0);++cellClears;}\n                                    ++emptyCopiesAvoided;\n                                }\n                            } else if(!record.hasPixels[i])++emptyCopiesAvoided;'), ('                    } else if(record.shown[i]){page.data[i].fillRect(page.rects[cell],0);++cellClears;}', '                    } else if(record.shown[i] && (i==0 || i==3)){page.data[i].fillRect(page.rects[cell],0);++cellClears;}'), ('                record.entry=surface;record.revision=surface.revision;\n            }\n        }\n\n        public function beginFrame()', '                var lowerVisible:Boolean=record.shown[1] && record.hasPixels[1];\n                var upperVisible:Boolean=record.shown[2] && record.hasPixels[2];\n                page.content[1]=false;\n                if(lowerVisible || upperVisible)page.content[2]=true;\n                if(backgroundChanged) {\n                    if(sourceRect==null)sourceRect=new Rectangle(surface.gutter,surface.gutter,CELL,CELL);\n                    if(lowerVisible){page.data[2].copyPixels(surface.nativeBuffers[1],sourceRect,page.points[cell]);++copies;}\n                    else {page.data[2].fillRect(page.rects[cell],0);++cellClears;}\n                    if(upperVisible){page.data[2].copyPixels(surface.nativeBuffers[2],sourceRect,page.points[cell],null,null,lowerVisible);++copies;}\n                    ++backgroundMerges;\n                }\n                record.entry=surface;record.revision=surface.revision;\n            }\n        }\n\n        public function beginFrame()'), ('alphaRectChecks:alphaRectChecks,emptyCopiesAvoided:emptyCopiesAvoided,', 'alphaRectChecks:alphaRectChecks,emptyCopiesAvoided:emptyCopiesAvoided,backgroundMerges:backgroundMerges,')]

stage_cost_helper=helper_source
def helper_source():
    value=stage_cost_helper()
    edits=[('    import flash.utils.getQualifiedClassName;',
        '    import flash.display.PNGEncoderOptions;\n    import flash.filesystem.File;\n    import flash.filesystem.FileMode;\n    import flash.filesystem.FileStream;\n    import flash.utils.getDefinitionByName;\n    import flash.utils.getQualifiedClassName;'),
        ('report.complete=true;report.passed=true;clear(w);',
        'report.stationaryRefresh=[];stationaryRefresh(false);stationaryRefresh(true);\n                            report.complete=true;report.passed=true;clear(w);'),
        ('        private function capture():BitmapData {',
        (HERE/'tests/StationaryRefresh.as.inc').read_text('utf-8-sig')+'\n        private function capture():BitmapData {')]
    original=value
    for before,after in edits:
        assert value.count(before)==1;value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
    assert reverse==original
    return value


empty_helper=helper_source
def helper_source():
    source=empty_helper()
    edits=[('report.stationaryRefresh=[];stationaryRefresh(false);stationaryRefresh(true);',
        'mergeFallbackCheck();report.stationaryRefresh=[];stationaryRefresh(false);stationaryRefresh(true);'),
        ('        private function capture():BitmapData {',
        (HERE/'tests/MergeFallback.as.inc').read_text('utf-8-sig')+'\n        private function capture():BitmapData {')]
    value=source
    for before,after in edits:
        assert value.count(before)==1;value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(edits):reverse=reverse.replace(after,before,1)
    assert reverse==source
    return value

def prepare(source:Path,destination:Path):
    assert not destination.exists() and not (source/CHANGED[2]).exists()
    assert hashlib.sha256((POOL/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()==PRESENTER_SHA
    baseline=pool_patch.transform_presenter((source/CHANGED[1]).read_text('utf-8-sig'))
    current=(POOL/'SceneRasterPresentation.as').read_text('utf-8-sig')
    for before,after in reversed(PRESENTER_EDITS):
        assert current.count(after)==1
        current=current.replace(after,before,1)
    assert current==baseline
    assert HELPER.read_text('utf-8-sig')==helper_source()
    shutil.copytree(source,destination)
    (destination/CHANGED[0]).write_text(transform_main((source/CHANGED[0]).read_text('utf-8-sig')),'utf-8',newline='\n')
    shutil.copy2(POOL/'SceneRasterPresentation.as',destination/CHANGED[1])
    shutil.copy2(HELPER,destination/CHANGED[2])

if __name__=='__main__':
    assert not HELPER.exists();HELPER.parent.mkdir(parents=True,exist_ok=True)
    HELPER.write_text(helper_source(),'utf-8',newline='\n')
    print('Prepared source only; no compiler, AIR, or deployment')
