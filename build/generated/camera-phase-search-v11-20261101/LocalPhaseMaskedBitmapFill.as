package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getTimer;

    /** Layer-attribution diagnostic based on the rounded local-phase helper.
     * Mask bits 0..3 select visFront/visBack/visBack2/visVoda respectively.
     * The mask is fixed at construction. Unselected native layers are qualified
     * and allowed in the native tree, but are never owned, hidden or redrawn.
     * Four groups remain; unselected groups are empty. Selected layers retain
     * the exact rounded texture phase and existing pixel-revision behavior.
     * The full-layer predecessor still differs in actual 2/3 alpha pixels.
     * This diagnostic is not a pixel-equivalent or production optimization.
     */
    public class LocalPhaseMaskedBitmapFill {
        private static const CELL:int=320;
        public var phaseOverride:Number=NaN;
        private var layerMask:int;
        private var selectedLayerCount:int=0;
        private static const SCALE_STEP:Number=1/65536;
        private static const SCALE_EPSILON:Number=1e-10;
        private var observedCameraScale:Number=NaN,observedMatrixScale:Number=NaN;
        private var observedRootScaleX:Number=NaN,observedRootScaleY:Number=NaN;
        private var observedScaleEncoding:String="unobserved";
        private var observedLocalMatrix:Object=null;
        private var observedLocalScaleEncoding:String="unobserved";
        private var observedRootXEncoding:String="unobserved",observedRootYEncoding:String="unobserved";
        private var observedAncestorMatrices:Array=[];
        private var observedAncestorChainComplete:Boolean=false;
        private var world:*,location:*,grafon:*;
        private var parents:Array=[],groups:Array=[],bindings:Array=[],extras:Array=[];
        private var records:Dictionary=new Dictionary();
        private var owned:Dictionary=new Dictionary();
        private var localNodes:Dictionary=new Dictionary();
        private var listening:Boolean=false,active:Boolean=false;
        private var treeEpoch:int=0,boundEpoch:int=-1;
        private var resident:int=-1,redraws:int=-1,evictions:int=-1;
        private var viewKey:String="";
        private var updates:int=0,enables:int=0,clears:int=0,treeEvents:int=0;
        private var bindingRefreshes:int=0,commandRebuilds:int=0,stableFrames:int=0;
        private var revisionReads:int=0,revisionChanges:int=0,bitmapQualifications:int=0;
        private var pixelOnlyChanges:int=0,pixelOnlyFrames:int=0;
        private var visibilityReads:int=0,alphaWrites:int=0,alphaRestores:int=0;
        private var nodesCreated:int=0,nodesRemoved:int=0,liveRecords:int=0;
        private var localNodesCreated:int=0,localNodesRemoved:int=0,peakLocalNodes:int=0;
        private var commands:int=0,peakCommands:int=0;
        private var fallbackCount:int=0,contractRejections:int=0,internalErrors:int=0,cleanupErrors:int=0;
        private var lastFallback:String="",lastError:String="";
        private var updateMs:int=0,maxUpdateMs:int=0,lastUpdateMs:int=0;

        public function LocalPhaseMaskedBitmapFill(mask:int=15) {
            if(mask<1 || mask>15)throw new ArgumentError("Layer mask must be 1..15");
            layerMask=mask;
            for(var layer:int=0;layer<4;++layer)
                if((layerMask & (1<<layer))!=0)++selectedLayerCount;
        }

        public function update(w:*,enabled:Boolean):void {
            var started:int=getTimer();++updates;
            try {
                if(!enabled){clear();lastFallback="disabled";return;}
                var reason:String=unsupported(w);
                if(reason!=""){fallback(reason,false);return;}
                var nextParents:Array=[w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda];
                if(active && (world!==w || location!==w.loc || grafon!==w.grafon || !sameParents(nextParents)))clear();
                if(!active) {
                    world=w;location=w.loc;grafon=w.grafon;parents=nextParents;
                    for each(var parent:DisplayObjectContainer in parents) {
                        parent.addEventListener(Event.ADDED,onTreeMutation);
                        parent.addEventListener(Event.REMOVED,onTreeMutation);
                    }
                    listening=true;active=true;++enables;
                }
                for(var groupIndex:int=0;groupIndex<groups.length;++groupIndex)
                    require(groups[groupIndex].parent===parents[groupIndex] &&
                        groups[groupIndex].node.parent===parents[groupIndex] && groups[groupIndex].node.visible,
                        "presentation node changed");
                // Native base bitmaps are hidden extras. Other visible terrain
                // children are not safely reorderable into the four graphics nodes.
                for each(var extra:DisplayObject in extras)
                    require(!extra.visible,"unknown visible terrain child");
                var changed:Boolean=false,pixelChanged:Boolean=false;
                if(boundEpoch!=treeEpoch || resident!=grafon.sceneResident ||
                    redraws!=grafon.sceneRedraws || evictions!=grafon.sceneEvictions) {
                    refreshBindings();changed=true;
                }
                // sceneApply has no monotonic public dirty epoch. Revision reads
                // are plain AS object fields, not native Bitmap property getters.
                // They also catch repeated one-cell writes with the same dirty count.
                for each(var binding:Object in bindings) {
                    ++revisionReads;
                    if(binding.revision!==binding.surface.revision) {
                        var drawingChanged:Boolean=qualify(binding);
                        binding.revision=binding.surface.revision;++revisionChanges;
                        if(drawingChanged)changed=true;
                        else {++pixelOnlyChanges;pixelChanged=true;}
                    }
                }
                var view:Rectangle=grafon.sceneViewport();
                require(view!=null && !view.isEmpty(),"missing native viewport");
                var key:String=Math.floor(view.left/CELL)+":"+Math.floor(view.top/CELL)+":"+
                    Math.ceil(view.right/CELL)+":"+Math.ceil(view.bottom/CELL)+"@"+observedMatrixScale;
                if(changed || key!=viewKey) {rebuildCommands();viewKey=key;}
                else if(pixelChanged)++pixelOnlyFrames;
                else ++stableFrames;
                require(commands>0 && groups.length==4,"empty active presentation");
                lastFallback="";
            } catch(error:Error) {
                var contract:Boolean=error.message.indexOf("contract: ")==0;
                if(contract)++contractRejections;else {++internalErrors;lastError=error.message;}
                fallback(error.message,true);
            } finally {
                lastUpdateMs=getTimer()-started;updateMs+=lastUpdateMs;maxUpdateMs=Math.max(maxUpdateMs,lastUpdateMs);
            }
        }

        private function unsupported(w:*):String {
            if(!w || !w.loc || !w.grafon || !w.visual || !w.cam)return "world-not-ready";
            if(!w.grafon.sceneLarge || w.grafon.sceneChunkSide!=CELL)return "not-native-320-scene";
            if(w.sats.active || w.grafon.visSats.visible)return "sats";
            var cameraScale:Number=Number(w.cam.scaleV);
            observedCameraScale=cameraScale;observedScaleEncoding="unqualified";
            if(!isFinite(cameraScale) || cameraScale<0.5 || cameraScale>1 ||
                w.cam.quakeX!=0 || w.cam.quakeY!=0)return "zoom-or-shake";
            var root:DisplayObject=w.visual as DisplayObject;
            if(!root || !root.stage || !root.visible || root.alpha!=1 || root.filters.length ||
                root.mask!=null || root.scrollRect!=null || root.blendMode!="normal" || root.transform.matrix3D!=null)
                return "world-effects-or-visibility";
            var m:Matrix=root.transform.concatenatedMatrix;
            observedMatrixScale=m.a;observedRootScaleX=root.scaleX;observedRootScaleY=root.scaleY;
            if(!isFinite(m.a) || m.a<0.5 || m.a>1 || m.a!=m.d || m.b!=0 || m.c!=0 ||
                !isFinite(m.tx) || !isFinite(m.ty) ||
                m.tx!=Math.floor(m.tx) || m.ty!=Math.floor(m.ty))return "fractional-or-non-uniform-geometry";
            var localMatrix:Matrix=root.transform.matrix;
            observedLocalMatrix=matrixRecord(localMatrix);
            observedAncestorMatrices=[];observedAncestorChainComplete=false;
            observedRootXEncoding=scaleEncoding(observedRootScaleX,cameraScale);
            observedRootYEncoding=scaleEncoding(observedRootScaleY,cameraScale);
            observedLocalScaleEncoding=localMatrix?scaleEncoding(localMatrix.a,cameraScale):"rejected";
            observedScaleEncoding=scaleEncoding(m.a,cameraScale);
            // Getter, local matrix and concatenated matrix may expose different
            // native numeric representations of the same requested scale.
            if(observedRootXEncoding=="rejected" || observedRootYEncoding=="rejected" ||
                !localMatrix || localMatrix.a!=localMatrix.d || localMatrix.b!=0 || localMatrix.c!=0 ||
                observedLocalScaleEncoding=="rejected")return "root-scale-or-local-matrix-mismatch";
            if(observedScaleEncoding=="rejected")return "camera-matrix-scale-mismatch";
            // Prove that ancestors add no linear transform independently of
            // native matrix rounding. Include Stage's read-only default matrix.
            var ancestor:DisplayObject=root.parent;
            var reachedStage:Boolean=false;
            while(ancestor!=null) {
                var ancestorMatrix:Matrix=ancestor.transform.matrix;
                var ancestor3D:Boolean=ancestor.transform.matrix3D!=null;
                observedAncestorMatrices.push({name:ancestor.name,isStage:ancestor===root.stage,
                    matrix:matrixRecord(ancestorMatrix),hasMatrix3D:ancestor3D});
                if(!ancestorMatrix || ancestor3D || ancestorMatrix.a!=1 || ancestorMatrix.d!=1 ||
                    ancestorMatrix.b!=0 || ancestorMatrix.c!=0)return "ancestor-linear-transform";
                if(ancestor===root.stage)reachedStage=true;
                ancestor=ancestor.parent;
            }
            observedAncestorChainComplete=reachedStage;
            if(!reachedStage)return "ancestor-chain-missing-stage";
            if(!neutralColor(root.transform.concatenatedColorTransform,1))return "world-color-transform";
            var pp:Array=[w.grafon.visFront,w.grafon.visBack,w.grafon.visBack2,w.grafon.visVoda];
            for each(var parent:DisplayObjectContainer in pp) {
                if(!parent || parent.parent!==root || !parent.visible || parent.x!=0 || parent.y!=0 ||
                    parent.scaleX!=1 || parent.scaleY!=1 || parent.rotation!=0 || parent.blendMode!="normal" ||
                    parent.mask!=null || parent.filters.length || parent.scrollRect!=null || parent.transform.matrix3D!=null)
                    return "terrain-parent-effects-or-geometry";
                if(!neutralColor(parent.transform.colorTransform,parent.alpha))return "terrain-parent-color-transform";
            }
            return "";
        }

        private function scaleEncoding(value:Number,ideal:Number):String {
            if(!isFinite(value) || value<0.5 || value>1)return "rejected";
            if(Math.abs(value-ideal)<=SCALE_EPSILON)return "exact-number";
            var lower:Number=Math.floor(ideal/SCALE_STEP)*SCALE_STEP;
            var upper:Number=Math.ceil(ideal/SCALE_STEP)*SCALE_STEP;
            if(Math.abs(value-lower)<=SCALE_EPSILON)return "compatible-fixed16-lower";
            if(Math.abs(value-upper)<=SCALE_EPSILON)return "compatible-fixed16-upper";
            return "rejected";
        }

        private function matrixRecord(value:Matrix):Object {
            return value?{a:value.a,b:value.b,c:value.c,d:value.d,tx:value.tx,ty:value.ty}:null;
        }

        private function neutralColor(color:ColorTransform,alpha:Number):Boolean {
            return color.redMultiplier==1 && color.greenMultiplier==1 && color.blueMultiplier==1 &&
                color.alphaMultiplier==alpha && color.redOffset==0 && color.greenOffset==0 &&
                color.blueOffset==0 && color.alphaOffset==0;
        }

        private function sameParents(next:Array):Boolean {
            if(parents.length!=4)return false;
            for(var i:int=0;i<4;++i)if(parents[i]!==next[i])return false;
            return true;
        }

        private function onTreeMutation(event:Event):void {
            if(owned[event.target])return;
            ++treeEvents;++treeEpoch;
        }

        private function qualify(binding:Object):Boolean {
            var surface:Object=binding.surface;
            var drawingChanged:Boolean=false;
            require(surface.side==CELL && surface.bitmaps && surface.bitmaps.length==4 &&
                surface.nativeBuffers && surface.nativeBuffers.length==4 && isFinite(Number(surface.revision)),"native surface shape");
            require(surface.cx==binding.cx && surface.cy==binding.cy && surface.gutter==binding.gutter,"native surface geometry");
            for(var layer:int=0;layer<4;++layer) {
                ++bitmapQualifications;
                var bitmap:Bitmap=surface.bitmaps[layer] as Bitmap;
                var data:BitmapData=surface.nativeBuffers[layer] as BitmapData;
                var item:Object=bitmap?records[bitmap]:null;
                require(bitmap!=null && data!=null && bitmap.parent===parents[layer] && bitmap.bitmapData===data,"native bitmap identity");
                require(bitmap.x==binding.cx*CELL && bitmap.y==binding.cy*CELL,"native bitmap origin");
                var rect:Rectangle=bitmap.scrollRect;
                require(rect!=null && rect.x==binding.gutter && rect.y==binding.gutter && rect.width==CELL && rect.height==CELL,"native bitmap crop");
                require(data.width>=binding.gutter+CELL && data.height>=binding.gutter+CELL,"native buffer bounds");
                var m:Matrix=bitmap.transform.matrix;
                require(m.a==1 && m.b==0 && m.c==0 && m.d==1 && bitmap.transform.matrix3D==null,"native bitmap transform");
                require(neutralColor(bitmap.transform.colorTransform,item?0:1) && bitmap.filters.length==0 &&
                    bitmap.mask==null && bitmap.blendMode=="normal","native bitmap style");
                if(item)require(item.data===data && item.parent===parents[layer],"native buffer replaced without tree refresh");
                else if((layerMask & (1<<layer))!=0) {
                    // Only selected native bitmaps are owned. Unselected ones
                    // must retain the original alpha=1 qualification on revisions.
                    item={bitmap:bitmap,data:data,parent:parents[layer],alpha:bitmap.alpha};
                    records[bitmap]=item;++liveRecords;
                }
                var previous:Object=binding.layers[layer];
                if(previous==null || previous.bitmap!==bitmap || previous.data!==data ||
                    previous.x!=bitmap.x || previous.y!=bitmap.y || previous.gutter!=binding.gutter ||
                    previous.smooth!==bitmap.smoothing)drawingChanged=true;
                binding.layers[layer]={bitmap:bitmap,data:data,x:bitmap.x,y:bitmap.y,
                    gutter:binding.gutter,smooth:bitmap.smoothing};
            }
            // A pure pixel write retains the same borrowed BitmapData and commands.
            // This optimization requires runtime proof of Flash's live-fill update.
            return drawingChanged;
        }

        private function refreshBindings():void {
            var surfaces:Array=grafon.sceneSurfaces(),allowed:Dictionary=new Dictionary();
            require(surfaces.length>0,"missing native surfaces");
            surfaces.sort(function(a:Object,b:Object):Number{return a.cy==b.cy?a.cx-b.cx:a.cy-b.cy;});
            var next:Array=[],cells:Object={};
            for each(var surface:Object in surfaces) {
                require(isFinite(Number(surface.cx)) && isFinite(Number(surface.cy)) &&
                    surface.cx==Math.floor(surface.cx) && surface.cy==Math.floor(surface.cy) &&
                    isFinite(Number(surface.gutter)) && surface.gutter>=0 && surface.gutter==Math.floor(surface.gutter),"native cell geometry");
                var key:String=surface.cx+":"+surface.cy;require(!cells[key],"duplicate native cell");cells[key]=true;
                var binding:Object={surface:surface,cx:surface.cx,cy:surface.cy,gutter:surface.gutter,revision:surface.revision,layers:[]};
                qualify(binding);next.push(binding);
                for each(var item:Object in binding.layers)allowed[item.bitmap]=true;
            }
            for(var missing:Object in records)if(!allowed[missing])restoreRecord(missing as Bitmap);
            var nextExtras:Array=[];
            for(var layer:int=0;layer<4;++layer) {
                var parent:DisplayObjectContainer=parents[layer],anchor:int=parent.numChildren;
                for each(binding in next)anchor=Math.min(anchor,parent.getChildIndex(binding.layers[layer].bitmap));
                require(anchor<parent.numChildren,"missing native display anchor");
                if(groups.length<4) {
                    var node:Sprite=new Sprite();node.name="ContinuousSceneLocalPhaseMaskedBitmapFill"+layer;
                    node.mouseEnabled=false;node.mouseChildren=false;owned[node]=true;
                    parent.addChildAt(node,anchor);groups.push({parent:parent,node:node});++nodesCreated;
                } else {
                    node=groups[layer].node;
                    require(groups[layer].parent===parent && node.parent===parent,"presentation parent changed");
                    // A recreated native cell may be inserted before our node.
                    // Keep the same minimum-native anchor used by the old algorithm.
                    if(parent.getChildIndex(node)>anchor)parent.setChildIndex(node,anchor);
                }
                for(var i:int=0;i<parent.numChildren;++i) {
                    var child:DisplayObject=parent.getChildAt(i);
                    if(!allowed[child] && !owned[child]) {
                        require(!child.visible,"unknown visible terrain child");nextExtras.push(child);
                    }
                }
            }
            require(nextExtras.length<=16,"unsupported extra terrain child count");
            // Complete qualification before changing selected native alpha.
            // All four layers remain in allowed; unselected native children are
            // legitimate visible terrain and must never be hidden or restored.
            for each(binding in next)for(layer=0;layer<4;++layer) {
                if((layerMask & (1<<layer))==0)continue;
                item=binding.layers[layer];
                if(item.bitmap.alpha!=0){item.bitmap.alpha=0;++alphaWrites;}
            }
            bindings=next;extras=nextExtras;boundEpoch=treeEpoch;
            resident=grafon.sceneResident;redraws=grafon.sceneRedraws;evictions=grafon.sceneEvictions;
            ++bindingRefreshes;viewKey="";
        }

        private function rebuildCommands():void {
            commands=0;
            var wanted:Dictionary=new Dictionary();
            require(isFinite(observedMatrixScale) && observedMatrixScale>0,"missing observed sampling scale");
            for(var layer:int=0;layer<4;++layer) {
                if((layerMask & (1<<layer))==0)continue;
                var node:Sprite=groups[layer].node,order:int=0;
                for each(var binding:Object in bindings) {
                    var item:Object=binding.layers[layer];++visibilityReads;
                    if(!item.bitmap.visible)continue;
                    wanted[item.bitmap]=true;
                    var localRecord:Object=localNodes[item.bitmap];
                    var localNode:Sprite;
                    if(localRecord==null) {
                        localNode=new Sprite();localNode.name="ContinuousSceneLocalPhaseCell"+layer;
                        localNode.mouseEnabled=false;localNode.mouseChildren=false;
                        // Mark ownership before ADDED bubbles to the native parent.
                        owned[localNode]=true;localRecord={node:localNode,group:node};
                        localNodes[item.bitmap]=localRecord;++localNodesCreated;
                        node.addChildAt(localNode,order);
                    } else {
                        localNode=localRecord.node;
                        require(localRecord.group===node && localNode.parent===node,"local presentation parent changed");
                        if(node.getChildIndex(localNode)!=order)node.setChildIndex(localNode,order);
                    }
                    ++order;
                    localNode.x=item.x;localNode.y=item.y;
                    var scaledGutter:Number=item.gutter*observedMatrixScale;
                    var phase:Number=isNaN(phaseOverride)?Math.round((scaledGutter-Math.floor(scaledGutter))/observedMatrixScale):phaseOverride;
                    // Keep the native cell's local origin and rectangle. Only the
                    // borrowed texture's phase differs from the old world fill.
                    // Rebuilds occur on binding/grid/scale/drawing changes only;
                    // pure in-place source pixel revisions retain the live fill.
                    localNode.graphics.clear();
                    localNode.graphics.beginBitmapFill(item.data,new Matrix(1,0,0,1,-item.gutter+phase,-item.gutter+phase),false,item.smooth);
                    localNode.graphics.drawRect(0,0,CELL,CELL);localNode.graphics.endFill();++commands;
                }
            }
            for(var missing:Object in localNodes)if(!wanted[missing])releaseLocalNode(missing as Bitmap);
            ++commandRebuilds;peakCommands=Math.max(peakCommands,commands);
            peakLocalNodes=Math.max(peakLocalNodes,localNodesCreated-localNodesRemoved);
            require(localNodesCreated-localNodesRemoved==commands,"local presentation command accounting");
        }

        private function releaseLocalNode(bitmap:Bitmap):void {
            var record:Object=localNodes[bitmap];if(!record)return;
            var node:Sprite=record.node;
            node.graphics.clear();
            // REMOVED must still see owned[node] before the entry is deleted.
            if(node.parent)node.parent.removeChild(node);
            require(node.parent==null,"local presentation remains attached");
            delete owned[node];delete localNodes[bitmap];++localNodesRemoved;
        }

        private function restoreRecord(bitmap:Bitmap):void {
            var item:Object=records[bitmap];if(!item)return;
            releaseLocalNode(bitmap);
            bitmap.alpha=item.alpha;++alphaRestores;
            require(bitmap.alpha===item.alpha,"native alpha restoration");
            delete records[bitmap];--liveRecords;
        }

        private function fallback(reason:String,fromError:Boolean):void {
            ++fallbackCount;lastFallback=reason;
            try {clear();}catch(error:Error){lastError=(lastError?lastError+"; ":"")+error.message;}
        }

        public function clear():void {
            if(!active && !listening && groups.length==0 && liveRecords==0 && localNodesCreated==localNodesRemoved)return;
            var problems:Array=[];
            if(listening)for each(var parent:DisplayObjectContainer in parents) {
                parent.removeEventListener(Event.ADDED,onTreeMutation);
                parent.removeEventListener(Event.REMOVED,onTreeMutation);
            }
            listening=false;
            for(var localBitmap:Object in localNodes)try {releaseLocalNode(localBitmap as Bitmap);}
                catch(localError:Error){problems.push(localError.message);}
            for each(var group:Object in groups)try {
                var node:Sprite=group.node;node.graphics.clear();
                if(node.parent)node.parent.removeChild(node);
                require(node.parent==null,"presentation node remains attached");++nodesRemoved;
            }catch(nodeError:Error){problems.push(nodeError.message);}
            for(var nativeObject:Object in records)try {restoreRecord(nativeObject as Bitmap);}
                catch(nativeError:Error){problems.push(nativeError.message);}
            if(active)++clears;
            active=false;world=null;location=null;grafon=null;parents=[];groups=[];bindings=[];extras=[];
            records=new Dictionary();owned=new Dictionary();localNodes=new Dictionary();boundEpoch=-1;resident=redraws=evictions=-1;viewKey="";commands=0;
            if(problems.length){cleanupErrors+=problems.length;throw new Error("Presentation cleanup: "+problems.join("; "));}
            require(liveRecords==0 && nodesCreated==nodesRemoved && localNodesCreated==localNodesRemoved,"presentation resource accounting");
        }

        public function stats():Object {
            return {version:"local-phase-masked-fill-1",diagnosticOnly:true,mask:layerMask,selectedLayerCount:selectedLayerCount,active:active,presented:active && commands>0,updates:updates,enables:enables,clears:clears,
                observedCameraScale:observedCameraScale,observedMatrixScale:observedMatrixScale,
                observedRootScaleX:observedRootScaleX,observedRootScaleY:observedRootScaleY,
                observedScaleEncoding:observedScaleEncoding,
                observedScaleDifference:observedMatrixScale-observedCameraScale,
                observedLocalMatrix:observedLocalMatrix,observedLocalScaleEncoding:observedLocalScaleEncoding,
                observedRootXEncoding:observedRootXEncoding,observedRootYEncoding:observedRootYEncoding,
                observedAncestorMatrices:observedAncestorMatrices.concat(),
                observedAncestorChainComplete:observedAncestorChainComplete,
                liveNodes:nodesCreated-nodesRemoved,nodesCreated:nodesCreated,nodesRemoved:nodesRemoved,
                liveLocalNodes:localNodesCreated-localNodesRemoved,localNodesCreated:localNodesCreated,localNodesRemoved:localNodesRemoved,peakLocalNodes:peakLocalNodes,
                liveNativeRecords:liveRecords,boundSurfaces:bindings.length,commands:commands,peakCommands:peakCommands,
                treeEpoch:treeEpoch,boundEpoch:boundEpoch,treeEvents:treeEvents,bindingRefreshes:bindingRefreshes,
                commandRebuilds:commandRebuilds,stableFrames:stableFrames,revisionReads:revisionReads,revisionChanges:revisionChanges,
                bitmapQualifications:bitmapQualifications,pixelOnlyChanges:pixelOnlyChanges,pixelOnlyFrames:pixelOnlyFrames,visibilityReads:visibilityReads,alphaWrites:alphaWrites,alphaRestores:alphaRestores,
                fallbackCount:fallbackCount,contractRejections:contractRejections,internalErrors:internalErrors,cleanupErrors:cleanupErrors,
                lastFallback:lastFallback,lastError:lastError,updateMs:updateMs,lastUpdateMs:lastUpdateMs,maxUpdateMs:maxUpdateMs,
                ownBitmapAllocations:0,sourcePixelCopies:0,sourceBitmapDisposals:0};
        }

        private function require(value:Boolean,reason:String):void {
            if(!value)throw new Error("contract: "+reason);
        }
    }
}


