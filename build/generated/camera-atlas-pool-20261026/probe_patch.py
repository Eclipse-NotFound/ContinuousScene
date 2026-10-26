from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-short-combat-20261026'
VERSION='camera-atlas-pool-combat-1'
CHANGED=['ContinuousSceneMotionProbe.as','SceneRasterPresentation.as']
PRESENTER_SOURCE=HERE.parent/'camera-atlas-paged-combat-20261025/SceneRasterPresentation.as'
PRESENTER_SHA='AD472C796A8006227C5523E51C5803511C2F3904AE0E970D08136BB37C02AD48'
spec=importlib.util.spec_from_file_location('pool_short_patch',OLD/'probe_patch.py')
short=importlib.util.module_from_spec(spec);spec.loader.exec_module(short)

def replace_one(text,before,after):
    assert text.count(before)==1,(before,text.count(before))
    return text.replace(before,after,1)

def transform_main(text):
    value=short.transform(text)
    assert value.count('camera-atlas-short-combat-1')==2
    value=value.replace('camera-atlas-short-combat-1',VERSION)
    if 'import flash.system.System;' not in value:
        value=replace_one(value,'    import flash.utils.getTimer;','    import flash.system.System;\n    import flash.utils.getTimer;')
    value=replace_one(value,'rasterPresentation.update(w,altered);',
        'if(altered)rasterPresentation.update(w,true);else rasterPresentation.useNativeForTest();')
    anchor='                    report.lastWarm=w.grafon.sceneWarmCount;report.lastDraw=w.grafon.sceneDrawMs;startCase();\n'
    added='''                    if(cfg.drawControl=="atlas") {
                        report.atlasPoolPreparation={startedAtMs:getTimer(),before:rasterPresentation.snapshot(),memoryBefore:System.totalMemory};
                        rasterPresentation.preallocate(w);
                        report.atlasPoolPreparation.endedAtMs=getTimer();
                        report.atlasPoolPreparation.after=rasterPresentation.snapshot();
                        report.atlasPoolPreparation.memoryAfter=System.totalMemory;
                    }
'''+anchor
    value=replace_one(value,anchor,added)
    return value

def transform_presenter(text):
    value=replace_one(text,'private var pages:Array=[];','private var pages:Array=[];\n        private var freePages:Array=[];\n        private var poolLocation:*;')
    value=replace_one(value,'            var g:*=w.grafon;',
        '            if(poolLocation!==w.loc || pages.length+freePages.length!=LIMIT){clear();fallbackReason="pool-not-prepared";return;}\n            var g:*=w.grafon;')
    value=replace_one(value,'if(changedParent)clear();','if(changedParent){clear();fallbackReason="pool-not-prepared";return;}')
    start=value.index('        private function createPage(')
    end=value.index('        private function syncPage(',start)
    original_create=value[start:end]
    value=value[:start]+'''        public function preallocate(w:*):void {
            if(poolLocation===w.loc && pages.length+freePages.length==LIMIT)return;
            clear();
            if(!w || !w.loc || !w.grafon.sceneLarge)throw new Error("Pool requires a loaded large scene");
            poolLocation=location=w.loc;
            try {
                for(var slot:int=0;slot<LIMIT;++slot){
                    var page:Object={key:"",px:0,py:0,layers:[],data:[],cells:new Array(16),points:[],rects:[],used:0,reused:false};
                    freePages.push(page);
                    for(var cell:int=0;cell<16;++cell){
                        page.points.push(new Point((cell%4)*CELL,int(cell/4)*CELL));
                        page.rects.push(new Rectangle((cell%4)*CELL,int(cell/4)*CELL,CELL,CELL));
                    }
                    for(var i:int=0;i<4;++i){
                        var data:BitmapData=new BitmapData(PAGE,PAGE,true,0);
                        page.data.push(data);++allocations;liveBytes+=LAYER_BYTES;allocatedBytes+=LAYER_BYTES;
                        peakBytes=Math.max(peakBytes,liveBytes);
                        var bitmap:Bitmap=new Bitmap(data);bitmap.name=NAMES[i];bitmap.visible=false;
                        page.layers.push(bitmap);
                    }
                }
            } catch(error:*) {clear();throw error;}
        }

        /** Benchmark-only native arm; the product disable path remains clear(). */
        public function useNativeForTest():void {
            beginFrame();requestedPages=0;requestedKeys=[];poseValid=false;
            fallbackReason="disabled-or-native-scene";
        }

        private function createPage(px:int,py:int,parents:Array,surfaces:Array):Object {
            if(pages.length>=LIMIT || !freePages.length)throw new Error("Prepared atlas pool exhausted");
            var page:Object=freePages.pop();
            page.key=px+":"+py;page.px=px;page.py=py;page.used=clock;page.cells=new Array(16);
            pages.push(page);++pagesCreated;++rebuilds;peakPages=Math.max(peakPages,pages.length);
            try {
                for(var i:int=0;i<4;++i){
                    var anchor:Bitmap=nativeAnchor(parents[i],surfaces,i);
                    if(page.reused)page.data[i].fillRect(page.data[i].rect,0);
                    var bitmap:Bitmap=page.layers[i];
                    bitmap.pixelSnapping=anchor.pixelSnapping;bitmap.smoothing=anchor.smoothing;
                    bitmap.x=px*PAGE;bitmap.y=py*PAGE;bitmap.visible=false;
                    parents[i].addChildAt(bitmap,parents[i].getChildIndex(anchor));
                }
                page.reused=true;
            } catch(error:*) {dropAt(pages.indexOf(page),false);throw error;}
            return page;
        }

'''+value[end:]
    before='''            for each(var bitmap:Bitmap in page.layers){if(bitmap.parent)bitmap.parent.removeChild(bitmap);bitmap.bitmapData=null;}
            for each(var data:BitmapData in page.data){data.dispose();++disposals;liveBytes-=LAYER_BYTES;}
            page.layers=[];page.data=[];page.cells=[];
            pages.splice(index,1);++pagesDisposed;if(evicted)++evictions;'''
    after='''            for each(var bitmap:Bitmap in page.layers){if(bitmap.parent)bitmap.parent.removeChild(bitmap);bitmap.visible=false;}
            page.cells=[];page.key="";freePages.push(page);
            pages.splice(index,1);++pagesDisposed;if(evicted)++evictions;'''
    value=replace_one(value,before,after)
    value=replace_one(value,'return {version:"atlas-paged-1",presented:',
        'return {version:"atlas-pool-1",freePages:freePages.length,poolPages:pages.length+freePages.length,poolReady:poolLocation!=null,ownedBitmaps:allocations-disposals,presented:')
    value=replace_one(value,'            location=null;poseValid=false;poseX=poseY=poseScale=NaN;',
'''            while(freePages.length){
                var page:Object=freePages.pop();
                for each(var bitmap:Bitmap in page.layers){if(bitmap.parent)bitmap.parent.removeChild(bitmap);bitmap.bitmapData=null;}
                for each(var data:BitmapData in page.data){data.dispose();++disposals;liveBytes-=LAYER_BYTES;}
                page.layers=[];page.data=[];page.cells=[];
            }
            poolLocation=null;location=null;poseValid=false;poseX=poseY=poseScale=NaN;''')
    # Outside the explicitly replaced allocation/lifecycle blocks, synchronization
    # remains byte-identical, including native layer identities and pixel copies.
    for name,next_name in [('syncPage','beginFrame'),('beginFrame','dropAt')]:
        def block(source):
            a=source.index(' function '+name+'(');b=source.index(' function '+next_name+'(',a)
            return source[a:source.rfind('\n',a,b)]
        assert block(text)==block(value),name
    assert original_create.count('new BitmapData')==1 and value.count('new BitmapData')==1
    return value

def prepare(source:Path,destination:Path):
    assert not destination.exists()
    assert hashlib.sha256((source/'SceneRasterPresentation.as').read_bytes()).hexdigest().upper()==PRESENTER_SHA
    shutil.copytree(source,destination)
    (destination/CHANGED[0]).write_text(transform_main((source/CHANGED[0]).read_text('utf-8-sig')),'utf-8',newline='\n')
    actual=transform_presenter((source/CHANGED[1]).read_text('utf-8-sig'))
    assert actual==(HERE/'SceneRasterPresentation.as').read_text('utf-8-sig')
    (destination/CHANGED[1]).write_text(actual,'utf-8',newline='\n')

if __name__=='__main__':
    assert hashlib.sha256(PRESENTER_SOURCE.read_bytes()).hexdigest().upper()==PRESENTER_SHA
    target=HERE/'SceneRasterPresentation.as';assert not target.exists()
    target.write_text(transform_presenter(PRESENTER_SOURCE.read_text('utf-8-sig')),'utf-8',newline='\n')
    print('Prepared source only; no compiler, AIR, or deployment')
