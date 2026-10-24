package {
    import flash.display.Bitmap;
    import flash.display.DisplayObject;
    import flash.utils.Dictionary;

    /** Attribution only: borrow native terrain visibility for one presentation. */
    public class SceneTerrainLayerTrial {
        private var held:Array=[];
        private var ids:Dictionary=new Dictionary(true);
        private var bindings:Dictionary=new Dictionary(true);
        private var bindingsList:Array=[],nodes:Array=[];
        private var bindingsCreated:int=0,bindingsReleased:int=0;
        private var nextId:int=1;
        private var location:*,grafon:*;
        private var mode:String="";
        private var lastApplied:Boolean=false;
        private var applied:Boolean=false;
        private var updates:int=0,hides:int=0,restores:int=0,scanned:int=0;
        private var errors:Array=[];
        private var previousPose:Object=null;

        private function identity(value:*):int {
            if(value==null)return 0;
            if(!ids[value])ids[value]=nextId++;
            return ids[value];
        }
        private function effective(node:DisplayObject):Boolean {
            while(node){if(!node.visible || node.alpha<=0)return false;node=node.parent;}
            return true;
        }
        private function watched(w:*):Array {
            var g:*=w.grafon;
            var nodes:Array=[w.visual,g.visFront,g.visBack,g.visBack2,g.visVoda,g.visLight,g.visSats];
            var names:Array=["world","frontParent","backParent","back2Parent","waterParent","fogParent","satsParent"];
            for(var i:int=0;i<g.visObjs.length;++i){nodes.push(g.visObjs[i]);names.push("objects"+i);}
            var result:Array=[];
            for(i=0;i<nodes.length;++i){
                var d:DisplayObject=nodes[i] as DisplayObject;
                if(!d)throw new Error("Terrain trial missing watched layer "+names[i]);
                result.push({name:names[i],id:identity(d),parent:identity(d.parent),visible:d.visible,
                    effectiveVisible:effective(d),alpha:d.alpha});
            }
            return result;
        }
        private function sameWatched(a:Array,b:Array):Boolean {
            if(a.length!=b.length)return false;
            for(var i:int=0;i<a.length;++i){
                if(a[i].name!=b[i].name || a[i].id!=b[i].id || a[i].parent!=b[i].parent ||
                    a[i].visible!==b[i].visible || a[i].effectiveVisible!==b[i].effectiveVisible || a[i].alpha!==b[i].alpha)return false;
            }
            return true;
        }
        public function beginFrame():void {
            var remaining:int=0,count:int=held.length;
            for(var i:int=0;i<count;++i){
                var entry:Object=held[i];
                try {
                    if(entry.bitmap.parent!==entry.parent || entry.bitmap.bitmapData!==entry.data)
                        errors.push("Borrowed terrain parent/data changed before restoration");
                    if(entry.bitmap.visible!==false)
                        errors.push("Borrowed terrain visibility changed before restoration");
                    entry.bitmap.visible=entry.visible;
                    if(entry.bitmap.visible!==entry.visible)throw new Error("Terrain visibility restoration failed");
                    ++restores;
                } catch(error:*) {errors.push("Restore: "+String(error));held[remaining++]=entry;}
            }
            held.length=remaining;applied=held.length>0;
        }
        public function update(w:*,requestedMode:String,enabled:Boolean):Object {
            if(requestedMode!="terrainback" && requestedMode!="terrainfront")throw new Error("Unknown terrain control");
            if(held.length || errors.length)throw new Error("Terrain restoration guard failed");
            if(location && (location!==w.loc || grafon!==w.grafon))throw new Error("Terrain trial world changed");
            location=w.loc;grafon=w.grafon;mode=requestedMode;
            if(!grafon.sceneLarge)throw new Error("Terrain trial requires the native large scene");
            var before:Array=watched(w),after:Array;
            var parents:Array=[grafon.visFront,grafon.visBack,grafon.visBack2,grafon.visVoda];
            var surfaces:Array=grafon.sceneSurfaces();
            // No borrowed entry can still be in use when its frame fields change.
            nodes.length=0;
            var epoch:int=updates+1;
            var countsBefore:Array=[0,0,0,0],countsAfter:Array=[0,0,0,0];
            var total:Array=[0,0,0,0],targetVisible:int=0,changed:int=0,hash:uint=0;
            if(!surfaces.length)throw new Error("Terrain trial has no native surfaces");
            var outcome:Object;
            try {
                for each(var surface:Object in surfaces){
                    if(!surface.bitmaps || surface.bitmaps.length!=4 || !surface.nativeBuffers || surface.nativeBuffers.length!=4)
                        throw new Error("Terrain surface shape changed");
                    for(var layer:int=0;layer<4;++layer){
                        var bitmap:Bitmap=surface.bitmaps[layer] as Bitmap;
                        if(!bitmap || bitmap.parent!==parents[layer] || bitmap.bitmapData!==surface.nativeBuffers[layer])
                            throw new Error("Terrain bitmap is not its native parent/data");
                        var target:Boolean=mode=="terrainfront"?layer==0:(layer==1 || layer==2);
                        var entry:Object=bindings[bitmap];
                        if(entry==null){
                            entry={bitmap:bitmap,parent:bitmap.parent,data:bitmap.bitmapData,layer:layer,seen:0};
                            bindings[bitmap]=entry;bindingsList.push(entry);++bindingsCreated;
                        } else if(entry.parent!==bitmap.parent || entry.data!==bitmap.bitmapData || entry.layer!=layer)
                            throw new Error("Existing terrain binding parent/data/layer changed");
                        if(entry.seen==epoch)throw new Error("Duplicate native terrain bitmap");
                        entry.seen=epoch;entry.visible=bitmap.visible;entry.target=target;
                        nodes.push(entry);++total[layer];if(entry.visible)++countsBefore[layer];
                        if(target && entry.visible)++targetVisible;
                        hash=uint(hash*31+identity(bitmap));hash=uint(hash*31+identity(bitmap.parent));
                        hash=uint(hash*31+identity(bitmap.bitmapData));
                    }
                }
                // Drop stale references so this observer cannot retain evicted native buffers.
                var kept:int=0;
                for(var bindingIndex:int=0;bindingIndex<bindingsList.length;++bindingIndex){
                    entry=bindingsList[bindingIndex];
                    if(entry.seen==epoch)bindingsList[kept++]=entry;
                    else {delete bindings[entry.bitmap];++bindingsReleased;}
                }
                bindingsList.length=kept;
                for each(entry in nodes)if(enabled && entry.target && entry.visible){
                    // Claim ownership before the setter so a partial failure is restored.
                    held.push(entry);entry.bitmap.visible=false;++hides;++changed;
                }
                for each(entry in nodes){
                    bitmap=entry.bitmap;
                    if(bitmap.parent!==entry.parent || bitmap.bitmapData!==entry.data ||
                        bitmap.visible!==(enabled && entry.target && entry.visible?false:entry.visible))
                        throw new Error("Terrain-only visibility/identity contract failed");
                    if(bitmap.visible)++countsAfter[entry.layer];
                }
                after=watched(w);
                if(!sameWatched(before,after))throw new Error("Terrain control changed a parent/object layer");
                applied=changed>0;++updates;scanned+=nodes.length;
                var matrix:*=w.visual.transform.concatenatedMatrix;
                var camera:Object={vx:w.cam.vx,vy:w.cam.vy,scale:w.cam.scaleV,worldX:w.visual.x,worldY:w.visual.y,
                    quakeX:w.cam.quakeX,quakeY:w.cam.quakeY,a:matrix.a,b:matrix.b,c:matrix.c,d:matrix.d,tx:matrix.tx,ty:matrix.ty};
                var moving:Boolean=previousPose!=null && (camera.vx!=previousPose.vx || camera.vy!=previousPose.vy ||
                    camera.scale!=previousPose.scale || camera.tx!=previousPose.tx || camera.ty!=previousPose.ty);
                outcome={version:"terrain-layer-native-1",mode:mode,enabled:enabled,applied:applied,previousApplied:lastApplied,
                    cameraMoving:moving,camera:camera,surfaces:surfaces.length,nodes:nodes.length,identityHash:hash,
                    totalByLayer:total,beforeVisible:countsBefore,afterVisible:countsAfter,targetVisible:targetVisible,hidden:changed,
                    identityParentDataPreserved:true,nonTargetVisibilityPreserved:true,watchedUnchanged:true,
                    watchedBefore:before,watchedAfter:after,
                    nativeCounters:{resident:grafon.sceneResident,warm:grafon.sceneWarmCount,slices:grafon.sceneWarmSlices,
                        forced:grafon.sceneWarmForced,misses:grafon.sceneMisses},snapshot:snapshot()};
                lastApplied=applied;previousPose=camera;
            } catch(failure:*) {beginFrame();throw failure;}
            return outcome;
        }
        public function snapshot():Object {
            return {version:"terrain-layer-native-1",mode:mode,applied:applied,pendingRestore:held.length,
                updates:updates,hides:hides,restores:restores,nodesScanned:scanned,
                bindingsCreated:bindingsCreated,bindingsReleased:bindingsReleased,liveBindings:bindingsList.length,errors:errors.concat()};
        }
        public function clear():Object {
            var before:Object=snapshot();beginFrame();
            bindingsReleased+=bindingsList.length;bindingsList.length=0;nodes.length=0;
            bindings=new Dictionary(true);ids=new Dictionary(true);location=null;grafon=null;previousPose=null;lastApplied=false;
            var after:Object=snapshot();
            return {before:before,after:after,restored:held.length==0 && hides==restores && errors.length==0,
                errors:errors.concat(),diagnosticOnly:true,performanceEligible:false};
        }
    }
}
