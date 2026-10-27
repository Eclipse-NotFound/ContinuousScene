"""Keep top effect layers native instead of CPU-rasterizing and uploading them."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-layer-region-20261027'
VERSION='camera-native-effects-overlay-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b,1)
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-layer-region-1',VERSION)
    s=one(s,'require(world.visual.visible===!presenter.active,"World visibility differs from active presentation");',
        'require(world.visual.visible===true,"Native upper world layers must remain visible");')
    return s
def renderer_source():
    s=(BASE/'SceneTilePresentation.as').read_text('utf-8-sig')
    s=one(s,'private var groups:Array=[],worldChildren:Array=[],scratch:BitmapData;', '''private var groups:Array=[],worldChildren:Array=[],scratch:BitmapData;
        private var nativeTail:Array=[];
        private var originalLayerVisibility:Dictionary=new Dictionary();
        private var lowerLayerCount:int=0;''')
    s=one(s,'parents=[backdrop,root];parentVisible=[backdrop.visible,root.visible];',
        'parents=[backdrop];parentVisible=[backdrop.visible];')
    s=one(s,'var current:Object=null;', '''var current:Object=null;
            var nativeStart:int=container.getChildIndex(g.visObjs[4]);
            require(nativeStart>container.getChildIndex(g.visObjs[2]),"Native upper layer ordering invalid");''')
    s=one(s,'var node:DisplayObject=container.getChildAt(i);require(node!=null,"Null direct world layer");worldChildren.push(node);', '''var node:DisplayObject=container.getChildAt(i);require(node!=null,"Null direct world layer");worldChildren.push(node);
                originalLayerVisibility[node]=node.visible;
                if(i>=nativeStart){nativeTail.push(node);continue;}
                parents.push(node);parentVisible.push(node.visible);++lowerLayerCount;''')
    needle='if(!selected[node] && node.visible){node.visible=false;++layerWrites;}'
    assert s.count(needle)==2
    s=s.replace(needle,'''var selectedVisible:Boolean=selected[node] && originalLayerVisibility[node];
                    if(node.visible!==selectedVisible){node.visible=selectedVisible;++layerWrites;}''')
    s=one(s,'initial.sourceLayers="Ordered layer groups with frame-driven cache invalidation; Flash timelines remain live";', '''initial.sourceLayers="GPU lower layers, native visObjs[4] and complete ordered tail; Flash timelines remain live";
            initial.lowerLayerCount=lowerLayerCount;initial.nativeTailCount=nativeTail.length;
            initial.nativeTailClasses=[];
            for each(var tail:DisplayObject in nativeTail)initial.nativeTailClasses.push(getQualifiedClassName(tail));''')
    s=one(s,'if(!active){backdrop.visible=false;root.visible=false;plane.visible=true;active=true;++enables;}\n            require(!root.visible && !backdrop.visible,"Native world was re-enabled");render(false);', '''if(!active){
                for(var hidden:int=0;hidden<parents.length;++hidden)parents[hidden].visible=false;
                plane.visible=true;active=true;++enables;
            }
            require(root.visible && !backdrop.visible,"Native overlay world/backdrop state changed");
            for each(var hiddenLayer:DisplayObject in parents)require(!hiddenLayer.visible,"Cached lower layer re-enabled");
            render(false);''')
    s=one(s,'return {active:active,parents:active?2:0,actualCache:',
        'return {active:active,parents:active?parents.length:0,lowerLayerCount:lowerLayerCount,nativeTailCount:nativeTail.length,nativeRootVisible:root!=null && root.visible,actualCache:')
    # No new parent, coordinate, alpha, blend, animation or filter mutations.
    assert 'root.visible=false' not in s
    return s
def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-layer-region-1',VERSION)
    s=s.replace("pixel['presentation']['parents']==2", "pixel['presentation']['parents']==end['lowerLayerCount']+1")
    s=one(s,"all(v is (not cached) for v in row['worldVisible'])", "all(v is True for v in row['worldVisible'])")
    s=one(s,"p['parents']==(2 if cached else 0)", "p['parents']==(end['lowerLayerCount']+1 if cached else 0)")
    s=one(s,"    assert end['layerWrites']==end['layerRestores'] and end['animationChanges']>0 and end['tileRefreshes']>0", """    assert end['layerWrites']==end['layerRestores'] and end['animationChanges']>0 and end['tileRefreshes']>0
    assert end['nativeRootVisible'] and end['lowerLayerCount']>0 and end['nativeTailCount']>0
    assert end['initial']['lowerLayerCount']==end['lowerLayerCount'] and end['initial']['nativeTailCount']==end['nativeTailCount']""")
    s=one(s,"            assert p['liveAnimation'] and p['clipsStopped']==p['clipsResumed']==0", """            assert p['liveAnimation'] and p['clipsStopped']==p['clipsResumed']==0
            assert p['nativeRootVisible'] and p['lowerLayerCount']==end['lowerLayerCount'] and p['nativeTailCount']==end['nativeTailCount']""")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'SceneTilePresentation.as',renderer_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared native upper effects overlay with GPU lower layers; no build or launch')
