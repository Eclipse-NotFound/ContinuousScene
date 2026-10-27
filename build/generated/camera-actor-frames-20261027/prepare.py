"""Bounded memoization of observed actor/effect poses, using parent-faithful captures."""
from pathlib import Path
import importlib.util,ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-actor-sprites-20261027'
spec=importlib.util.spec_from_file_location('actor_frames_seed',BASE/'prepare.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
one=base.one

def helper_source():
    s=base.helper_source().replace('camera-actor-sprites-1','camera-actor-frames-1')
    s=one(s,'                            report.complete=true;report.passed=true;clear(w);',
       '                            phase=7;cursor=0;presenter.clear();')
    s=one(s,'            } catch(error:Error) {fail(error);}\n            return closed;',
      '''                else if(phase==7) {
                    pixelCase(views[cursor],1000+cursor);++cursor;
                    if(cursor==views.length) {
                        report.pixelsValid=report.visualAccepted;
                        report.complete=true;report.passed=true;clear(w);
                    }
                }
            } catch(error:Error) {fail(error);}
            return closed;''')
    return s

def renderer_source():
    s=base.renderer_source()
    s=one(s,'private var actorRasterPixels:Number=0;',
      '''private var actorRasterPixels:Number=0;
        private var posePool:Array=[],poseBytes:Number=0,posePeak:Number=0,poseClock:int=0;
        private var poseHits:int=0,poseMisses:int=0,poseEvictions:int=0,poseSkipped:int=0;
        private var clipIds:Dictionary=new Dictionary(),clipIdCounter:int=0;''')
    s=one(s,'        private function redrawActorTiles(',
      (HERE/'pose_methods.as.inc').read_text('utf-8-sig')+'\n        private function redrawActorTiles(')
    s=one(s,'            var began:int=getTimer(),layer:DisplayObjectContainer=group.nodes[0] as DisplayObjectContainer;',
      '''            actorRoots=group.actorRoots?group.actorRoots:[];actorItems=group.actorItems?group.actorItems:[];
            var began:int=getTimer(),layer:DisplayObjectContainer=group.nodes[0] as DisplayObjectContainer;''')
    s=one(s,'layer===world.grafon.visObjs[2] && style(layer)',
      '(layer===world.grafon.visObjs[2] || layer===world.grafon.visObjs[4]) && style(layer)')
    s=one(s,'            require(layer.numChildren==actorRoots.length,"Actor root lifecycle changed");',
      '''            group.actorRoots=actorRoots;group.actorItems=actorItems;
            require(layer.numChildren==actorRoots.length,"Actor root lifecycle changed");
            var signatures:Dictionary=new Dictionary();
            for each(var poseWatch:Object in group.watch) {
                if(!clipIds[poseWatch.node])clipIds[poseWatch.node]=++clipIdCounter;
                var before:String=signatures[poseWatch.owner]?signatures[poseWatch.owner]:"";
                signatures[poseWatch.owner]=before+clipIds[poseWatch.node]+":"+poseWatch.node.currentFrame+"/"+poseWatch.node.totalFrames+";";
            }''')
    s=one(s,'!item.rect.equals(rect)', '!item.rect.containsRect(rect)')
    a=s.index('                        if(item.bitmap || item.pixels==null || item.width!=rect.width');b=s.index('\n                    }\n                } else ++actorSkipped;',a)
    s=s[:a]+'''                        if(item.bitmap || item.pixels==null || item.rect==null || !item.rect.containsRect(rect)) {
                            releaseActorItem(item);rect.inflate(32,32);rect=rect.intersection(bounds);
                            item.rect=rect;item.width=int(rect.width);item.height=int(rect.height);
                            require(item.width<=2048 && item.height<=2048,"Actor image bound exceeded");
                            item.pixels=newPixels(item.width,item.height);
                        }
                        item.matrix=new Matrix(1,0,0,1,item.rect.x,item.rect.y);
                        item.poseKey=poseKey(state,item.rect,signatures[node]?signatures[node]:"");
                        var pose:Object=findPose(node,item.poseKey);
                        if(pose) {
                            item.pixels.copyPixels(pose.pixels,pose.pixels.rect,new Point());++copies;++poseHits;
                            uploadAt=getTimer();
                            if(item.texture==null)item.texture=upload(item.pixels);
                            else{item.texture.uploadFromBitmapData(item.pixels);++uploads;}
                            actorUploadMs+=getTimer()-uploadAt;
                        } else {++poseMisses;requests.push(item);}'''+s[b:]
    s=one(s,'if(first)actorInventory.push({index:i,', 'if(first)actorInventory.push({group:group.index,index:i,')
    s=one(s,'                    uploadAt=getTimer();\n                    if(item.texture==null)',
      '                    savePose(item.node,item.poseKey,item.pixels);\n                    uploadAt=getTimer();\n                    if(item.texture==null)')
    s=one(s,'        private function renderActorItems(camera:Matrix):void {',
      '        private function renderActorItems(camera:Matrix,group:Object):void {\n            actorItems=group.actorItems;')
    s=one(s,'            require(actorGroup && oracleImage,"Actor oracle missing");',
      '            require(actorGroup && oracleImage,"Actor oracle missing");actorItems=actorGroup.actorItems;')
    s=one(s,'current.nodes.push(node);if(node===g.visObjs[2]){current.actor=true;actorGroup=current;}',
      'current.nodes.push(node);if(node===g.visObjs[2]){current.actor=true;actorGroup=current;}else if(node===g.visObjs[4])current.actor=true;')
    s=one(s,'if(group.actor) {for each(var actorItem:Object in actorItems)',
      'if(group.actor) {actorItems=group.actorItems?group.actorItems:[];for each(var actorItem:Object in actorItems)')
    s=one(s,'if(group.actor)renderActorItems(m);','if(group.actor)renderActorItems(m,group);')
    s=one(s,'            for each(var group:Object in groups)releaseGroup(group);',
      '            for each(var pose:Object in posePool)disposePixels(pose.pixels);posePool=[];poseBytes=0;\n            for each(var group:Object in groups)releaseGroup(group);')
    s=one(s,'                actorRasterCalls:actorRasterCalls,',
      '                poseHits:poseHits,poseMisses:poseMisses,poseEvictions:poseEvictions,poseSkipped:poseSkipped,poseBytes:poseBytes,posePeak:posePeak,poseEntries:posePool.length,\n                actorRasterCalls:actorRasterCalls,')
    return s

def runner_source():
    s=base.runner_source().replace('camera-actor-sprites-1','camera-actor-frames-1')
    s=s.replace("end['oracleCalls']==13 and len(end['oracleChecks'])==13", "end['oracleCalls']==18 and len(end['oracleChecks'])==18")
    s=s.replace("end['captures']==13 and trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==260", "end['captures']==18 and trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==335")
    s=s.replace("len(trial['pixels'])==13 and len(trial['nativeWarmups'])==18", "len(trial['pixels'])==18 and len(trial['nativeWarmups'])==23")
    s=one(s,"    assert end['actorVisibilityWrites']==end['actorVisibilityRestores']", "    assert end['poseBytes']==0 and end['poseEntries']==0\n    assert end['actorVisibilityWrites']==end['actorVisibilityRestores']")
    return s

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    (HERE/'tests/SceneCameraRasterTrial.as').write_text(helper_source(),'utf-8')
    (HERE/'SceneTilePresentation.as').write_text(renderer_source(),'utf-8')
    s=runner_source();ast.parse(s);(HERE/'run.py').write_text(s,'utf-8')
    print('Prepared bounded pose cache with after-timing image checks; no build or launch')
