from pathlib import Path
import hashlib
import importlib.util
import shutil

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-atlas-short-combat-20261026'
VERSION='camera-atlas-budget-combat-1'
CHANGED=['ContinuousSceneMotionProbe.as','SceneRasterPresentation.as']
PRESENTER_SOURCE=HERE.parent/'camera-atlas-paged-combat-20261025/SceneRasterPresentation.as'
PRESENTER_SHA='AD472C796A8006227C5523E51C5803511C2F3904AE0E970D08136BB37C02AD48'

spec=importlib.util.spec_from_file_location('budget_short_patch',OLD/'probe_patch.py')
short=importlib.util.module_from_spec(spec);spec.loader.exec_module(short)

def transform_main(text):
    value=short.transform(text)
    assert value.count('camera-atlas-short-combat-1')==2
    return value.replace('camera-atlas-short-combat-1',VERSION)

def transform_presenter(text):
    edits=[
        ('private var fallbackReason:String="";',
         'private var fallbackReason:String="";\n        private var allocationsLastUpdate:int=0;'),
        ('requestedPages=0;requestedKeys=[];fallbackReason="";\n            if(!enabled',
         'requestedPages=0;requestedKeys=[];fallbackReason="";allocationsLastUpdate=0;\n            if(!enabled'),
        ('var toHide:Array=[];\n            for(py=',
         'var toHide:Array=[];\n            var allocationBudget:int=forcePresentation?LIMIT*4:1;\n            var pending:int=0;\n            for(py='),
        ('page.used=clock;\n                syncPage(page,byCell,parents,toHide);',
         'page.used=clock;\n                if(page.layers.length<4 && allocationBudget>0){\n                    var beforeAlloc:int=allocations;\n                    buildPageLayers(page,parents,surfaces,allocationBudget);\n                    var made:int=allocations-beforeAlloc;\n                    allocationBudget-=made;allocationsLastUpdate+=made;\n                }\n                if(page.layers.length==4)syncPage(page,byCell,parents,toHide);\n                else ++pending;'),
        ('if(useAtlas){','if(useAtlas && pending==0){'),
        ('presented=useAtlas;','presented=useAtlas && pending==0;'),
        ('            var anchors:Array=[];\n            for(var i:int=0;i<4;++i)anchors.push(nativeAnchor(parents[i],surfaces,i));\n',''),
        ('            peakPages=Math.max(peakPages,pages.length);\n            try {\n                for(i=0;i<4;++i){',
         '            peakPages=Math.max(peakPages,pages.length);\n            return page;\n        }\n\n        private function buildPageLayers(page:Object,parents:Array,surfaces:Array,budget:int):void {\n            try {\n                while(page.layers.length<4 && budget>0){\n                    var i:int=page.layers.length;\n                    var anchor:Bitmap=nativeAnchor(parents[i],surfaces,i);'),
        ('var bitmap:Bitmap=new Bitmap(data,anchors[i].pixelSnapping,anchors[i].smoothing);',
         'var bitmap:Bitmap=new Bitmap(data,anchor.pixelSnapping,anchor.smoothing);'),
        ('bitmap.name=NAMES[i];bitmap.x=px*PAGE;bitmap.y=py*PAGE;bitmap.visible=false;',
         'bitmap.name=NAMES[i];bitmap.x=page.px*PAGE;bitmap.y=page.py*PAGE;bitmap.visible=false;'),
        ('parents[i].addChildAt(bitmap,parents[i].getChildIndex(anchors[i]));',
         'parents[i].addChildAt(bitmap,parents[i].getChildIndex(anchor));--budget;'),
        ('            return page;\n        }\n\n        private function syncPage',
         '        }\n\n        private function syncPage'),
        ('var attached:int=0,live:int=0;',
         'var attached:int=0,live:int=0,ready:int=0,pending:int=0;'),
        ('resident.push(page.key);var shown:Boolean=false;',
         'resident.push(page.key);var shown:Boolean=false;\n                if(page.layers.length==4)++ready;\n                else if(requestedKeys.indexOf(page.key)>=0)++pending;'),
        ('used:page.used,layers:page.layers.length,visible:shown}',
         'used:page.used,layers:page.layers.length,visible:shown,ready:page.layers.length==4}'),
        ('version:"atlas-paged-1",presented:',
         'version:"atlas-budget-1",allocationsLastUpdate:allocationsLastUpdate,readyPages:ready,partialPages:pages.length-ready,pendingPages:pending,presented:')
    ]
    result=text
    for before,after in edits:
        assert result.count(before)==1,(before,result.count(before))
        result=result.replace(before,after,1)
    # Exact unchanged remainder; individual edits are also asserted once.
    restore=result
    for before,after in reversed(edits):
        if not after:continue
        assert restore.count(after)==1,after
        restore=restore.replace(after,before,1)
    # The sole deletion is restored at its original unique adjacent declaration.
    removed=edits[6][0]
    anchor='            var page:Object={key:px+":"+py'
    assert restore.count(anchor)==1
    restore=restore.replace(anchor,removed+anchor,1)
    assert restore==text
    return result

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
