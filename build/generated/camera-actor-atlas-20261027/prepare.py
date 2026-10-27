"""One synchronous native capture for a packed batch of changed actor roots."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-actor-frames-scan-20261027'
spec=importlib.util.spec_from_file_location('actor_atlas_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one
def helper_source():return base.helper_source().replace('camera-actor-frames-scan-1','camera-actor-atlas-1')
def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var actorRasterPixels:Number=0;',
      '''private var actorRasterPixels:Number=0;
        private var actorAtlas:BitmapData;
        private var atlasPasses:int=0,atlasRoots:int=0,atlasDrawMs:int=0,atlasCopyMs:int=0;
        private var actorTransformWrites:int=0,actorTransformRestores:int=0;''')
    a=s.index('        private function findPose(');b=s.index('        private function redrawActorTiles(',a)
    s=s[:a]+'''        private function findPose(owner:DisplayObject,key:String):Object {return null;}
        private function savePose(owner:DisplayObject,key:String,pixels:BitmapData):void {}
'''+s[b:]
    a=s.index('        private function actorRect(');b=s.index('        private function directBitmap(',a)
    s=s[:a]+'''        private function actorRect(node:DisplayObject):Rectangle {
            ++dirtyOwnerReads;
            var m:Matrix=root.transform.concatenatedMatrix;
            var rect:Rectangle=node.transform.pixelBounds;rect.offset(-m.tx,-m.ty);
            rect=rect.union(node.getBounds(root));
            require(isFinite(rect.x)&&isFinite(rect.y)&&isFinite(rect.width)&&isFinite(rect.height),"Invalid actor bounds");
            if(rect.isEmpty())return rect;
            rect.inflate(16,16);
            // The complete root must fit its atlas slot, including portions outside
            // the camera union, or those portions could bleed into a neighbour slot.
            return new Rectangle(Math.floor(rect.x),Math.floor(rect.y),Math.ceil(rect.right)-Math.floor(rect.x),Math.ceil(rect.bottom)-Math.floor(rect.y));
        }
'''+s[b:]
    a=s.index('            var signatures:Dictionary=');b=s.index('            var requests:Array=',a)
    s=s[:a]+s[b:]
    s=one(s,'item.shown=node.visible && node.alpha>0 && !rect.isEmpty();',
      'item.shown=node.visible && node.alpha>0 && !rect.isEmpty() && rect.intersects(bounds);')
    s=one(s,'releaseActorItem(item);rect.inflate(32,32);rect=rect.intersection(bounds);',
      'releaseActorItem(item);rect.inflate(32,32);')
    s=one(s,'item.poseKey=poseKey(state,item.rect,signatures[node]?signatures[node]:"");','item.poseKey="";')
    a=s.index('            // Isolate each requested root');b=s.index('            actorRefreshMs+=',a)
    s=s[:a]+'            if(requests.length)captureActorBatch(layer,requests);\n'+s[b:]
    s=one(s,'        private function renderActorItems(',
      (HERE/'atlas_methods.as.inc').read_text('utf-8-sig')+'\n        private function renderActorItems(')
    s=one(s,'            if(scratch){disposePixels(scratch);scratch=null;}',
      '            if(actorAtlas){disposePixels(actorAtlas);actorAtlas=null;}\n            if(scratch){disposePixels(scratch);scratch=null;}')
    s=one(s,'                poseHits:poseHits,',
      '                atlasPasses:atlasPasses,atlasRoots:atlasRoots,atlasDrawMs:atlasDrawMs,atlasCopyMs:atlasCopyMs,actorTransformWrites:actorTransformWrites,actorTransformRestores:actorTransformRestores,\n                poseHits:poseHits,')
    return s
def runner_source():
    s=base.runner_source().replace('camera-actor-frames-scan-1','camera-actor-atlas-1')
    s=one(s,"    assert end['poseBytes']==0 and end['poseEntries']==0", "    assert end['poseBytes']==0 and end['poseEntries']==0 and end['poseHits']==0\n    assert end['actorTransformWrites']==end['actorTransformRestores'] and end['atlasPasses']>0")
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared bounded native capture batches; no build or launch')
