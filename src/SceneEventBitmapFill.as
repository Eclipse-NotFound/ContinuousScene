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

    /** Diagnostic only. Native-owned 320px terrain, effects disabled, unit integer camera.
     * The drawing/alpha algorithm is unchanged from the measured four-node bitmap fill.
     * Full bitmap qualification is performed on binding/dirty events, not each frame.
     */
    public class SceneEventBitmapFill {
        private static const CELL:int=320;
        private var world:*,location:*,grafon:*;
        private var parents:Array=[],groups:Array=[],bindings:Array=[],extras:Array=[];
        private var records:Dictionary=new Dictionary();
        private var owned:Dictionary=new Dictionary();
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
        private var commands:int=0,peakCommands:int=0;
        private var fallbackCount:int=0,contractRejections:int=0,internalErrors:int=0,cleanupErrors:int=0;
        private var lastFallback:String="",lastError:String="";
        private var updateMs:int=0,maxUpdateMs:int=0,lastUpdateMs:int=0;

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
                    Math.ceil(view.right/CELL)+":"+Math.ceil(view.bottom/CELL);
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
            if(w.cam.scaleV!=1 || w.cam.quakeX!=0 || w.cam.quakeY!=0)return "zoom-or-shake";
            var root:DisplayObject=w.visual as DisplayObject;
            if(!root || !root.stage || !root.visible || root.alpha!=1 || root.filters.length ||
                root.mask!=null || root.scrollRect!=null || root.blendMode!="normal" || root.transform.matrix3D!=null)
                return "world-effects-or-visibility";
            var m:Matrix=root.transform.concatenatedMatrix;
            if(m.a!=1 || m.b!=0 || m.c!=0 || m.d!=1 || !isFinite(m.tx) || !isFinite(m.ty) ||
                m.tx!=Math.floor(m.tx) || m.ty!=Math.floor(m.ty))return "fractional-or-non-unit-geometry";
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
                else {
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
                    var node:Sprite=new Sprite();node.name="ContinuousSceneEventBitmapFill"+layer;
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
            // Complete qualification before changing any new native alpha.
            for each(binding in next)for each(item in binding.layers)
                if(item.bitmap.alpha!=0){item.bitmap.alpha=0;++alphaWrites;}
            bindings=next;extras=nextExtras;boundEpoch=treeEpoch;
            resident=grafon.sceneResident;redraws=grafon.sceneRedraws;evictions=grafon.sceneEvictions;
            ++bindingRefreshes;viewKey="";
        }

        private function rebuildCommands():void {
            commands=0;
            for(var layer:int=0;layer<4;++layer) {
                var node:Sprite=groups[layer].node;node.graphics.clear();
                for each(var binding:Object in bindings) {
                    var item:Object=binding.layers[layer];++visibilityReads;
                    if(!item.bitmap.visible)continue;
                    // Exact old mapping: borrow the original 400px buffer and
                    // fill only its 320px centre, retaining the 40px sample offset.
                    node.graphics.beginBitmapFill(item.data,new Matrix(1,0,0,1,item.x-item.gutter,item.y-item.gutter),false,item.smooth);
                    node.graphics.drawRect(item.x,item.y,CELL,CELL);node.graphics.endFill();++commands;
                }
            }
            ++commandRebuilds;peakCommands=Math.max(peakCommands,commands);
        }

        private function restoreRecord(bitmap:Bitmap):void {
            var item:Object=records[bitmap];if(!item)return;
            bitmap.alpha=item.alpha;++alphaRestores;
            require(bitmap.alpha===item.alpha,"native alpha restoration");
            delete records[bitmap];--liveRecords;
        }

        private function fallback(reason:String,fromError:Boolean):void {
            ++fallbackCount;lastFallback=reason;
            try {clear();}catch(error:Error){lastError=(lastError?lastError+"; ":"")+error.message;}
        }

        public function clear():void {
            if(!active && !listening && groups.length==0 && liveRecords==0)return;
            var problems:Array=[];
            if(listening)for each(var parent:DisplayObjectContainer in parents) {
                parent.removeEventListener(Event.ADDED,onTreeMutation);
                parent.removeEventListener(Event.REMOVED,onTreeMutation);
            }
            listening=false;
            for each(var group:Object in groups)try {
                var node:Sprite=group.node;node.graphics.clear();
                if(node.parent)node.parent.removeChild(node);
                require(node.parent==null,"presentation node remains attached");++nodesRemoved;
            }catch(nodeError:Error){problems.push(nodeError.message);}
            for(var nativeObject:Object in records)try {restoreRecord(nativeObject as Bitmap);}
                catch(nativeError:Error){problems.push(nativeError.message);}
            if(active)++clears;
            active=false;world=null;location=null;grafon=null;parents=[];groups=[];bindings=[];extras=[];
            records=new Dictionary();owned=new Dictionary();boundEpoch=-1;resident=redraws=evictions=-1;viewKey="";commands=0;
            if(problems.length){cleanupErrors+=problems.length;throw new Error("Presentation cleanup: "+problems.join("; "));}
            require(liveRecords==0 && nodesCreated==nodesRemoved,"presentation resource accounting");
        }

        public function stats():Object {
            return {version:"event-bitmap-fill-2",diagnosticOnly:true,active:active,presented:active && commands>0,updates:updates,enables:enables,clears:clears,
                liveNodes:nodesCreated-nodesRemoved,nodesCreated:nodesCreated,nodesRemoved:nodesRemoved,
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
