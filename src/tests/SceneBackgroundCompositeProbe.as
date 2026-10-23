package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Sprite;
    import flash.display.Stage;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Diagnostic only: composite two adjacent native background layers.
     * prepareFrame(w) precedes native logic; update(w,enabled) follows it.
     * The two parent visibility flags are held, not toggled every frame. Native
     * child visibility, buffers, matrices and revisions remain authoritative.
     * Equal pixels are NOT assumed: verify() must test the actual camera view.
     */
    public class SceneBackgroundCompositeProbe {
        public static const VERSION:String="native-background-composite-diagnostic-4";
        private static const SIDE:int=320, GUTTER:int=40, SIZE:int=400, MAX_PAIRS:int=128;
        private static const WALL_VERSION:String="0.5.9-scene", WALL_RESIDUE:String="WallBlendBackgroundLayer";
        private var world:*,location:*,grafon:*;
        private var visual:DisplayObjectContainer,lower:DisplayObjectContainer,upper:DisplayObjectContainer;
        private var presentation:Sprite;
        private var records:Dictionary=new Dictionary();
        private var pool:Array=[],settingGetters:Array=[];
        private var wallEnabledGetter:Function,residue:Bitmap,residueData:BitmapData;
        private var residueChecked:Boolean=false,residueInvalid:Boolean=false;
        private var held:Boolean=false;
        private var originalLower:Boolean,originalUpper:Boolean;
        private var zero:Point=new Point();
        private var updates:int=0,appliedUpdates:int=0,prepareCalls:int=0,restores:int=0;
        private var copies:int=0,allocations:int=0,reuses:int=0,disposals:int=0;
        private var updateCost:int=0,copyCost:int=0,prepareCost:int=0;
        private var parentWrites:int=0,conflicts:int=0,errorCount:int=0;
        private var errors:Array=[];
        private var last:Object={applied:false,reason:"new",pairs:0};

        /** No normal-frame display writes. Restore before native V/SATS capture,
         * pause, travel or a changed location. No event listener is installed. */
        public function prepareFrame(w:*):void {
            var start:int=getTimer();++prepareCalls;
            try {if(held && (!sameContext(w) || unsafeState(w) || wallStateReason()!="" || !residueStable()))beginFrame();}
            catch(error:Error){beginFrame();note(error);}
            finally {prepareCost+=getTimer()-start;}
        }
        public function beginFrame():void {
            if(presentation && presentation.visible)presentation.visible=false;
            if(!held)return;
            if(lower && lower.visible!==originalLower){lower.visible=originalLower;++parentWrites;}
            if(upper && upper.visible!==originalUpper){upper.visible=originalUpper;++parentWrites;}
            held=false;++restores;
        }
        private function sameContext(w:*):Boolean {
            return w && w===world && w.loc===location && w.grafon===grafon &&
                w.visual===visual && grafon.visBack===lower && grafon.visBack2===upper;
        }
        private function unsafeState(w:*):Boolean {
            return !w || !w.loc || !w.grafon || !w.grafon.sceneLarge || w.allStat!=1 ||
                w.onPause || w.t_exit!=0 || (w.ctr && w.ctr.keySats) ||
                (w.sats && w.sats.active) || (w.grafon.visSats && w.grafon.visSats.visible);
        }
        private function note(error:Error):void {
            ++errorCount;if(errors.length<8)errors.push({update:updates,message:error.message});
        }
        private function fallback(reason:String):void {
            beginFrame();last.applied=false;last.reason=reason;
        }
        private function bind(w:*):void {
            clear();world=w;location=w.loc;grafon=w.grafon;visual=w.visual as DisplayObjectContainer;
            lower=grafon.visBack as DisplayObjectContainer;upper=grafon.visBack2 as DisplayObjectContainer;
            // The settings closure is the existing cross-domain public API.
            // Sibling SWF classes are not visible from this probe's domain.
            // Native structure is checked independently; do not invent status.
            var carrier:*=w.main.getChildByName("ModSettingsCarrier");
            if(!carrier)throw new Error("Cannot establish disabled presentation mods");
            var wanted:Array=["wallblend","realisticvision","light-and-darkness"];
            var pages:Array=carrier["modAPI"].getPages();
            for each(var id:String in wanted) {
                var found:Object=null;
                for each(var page:Object in pages)if(page.modId==id)
                    for each(var item:Object in page.items)if(item.key=="enabled" && item["get"] is Function)found=item;
                if(found==null)throw new Error("Missing enabled setting for "+id);
                settingGetters.push(found);
                if(id=="wallblend")wallEnabledGetter=found["get"] as Function;
            }
        }
        private function neutral(node:DisplayObject):Boolean {
            if(!node || node.alpha!=1 || node.blendMode!="normal" || node.mask ||
                node.filters.length || node.cacheAsBitmap || node.transform.matrix3D!=null)return false;
            var c:ColorTransform=node.transform.colorTransform;
            return c.redMultiplier==1 && c.greenMultiplier==1 && c.blueMultiplier==1 && c.alphaMultiplier==1 &&
                c.redOffset==0 && c.greenOffset==0 && c.blueOffset==0 && c.alphaOffset==0;
        }
        private function identity(node:DisplayObject):Boolean {
            var m:Matrix=node.transform.matrix;
            return m && m.a==1 && m.b==0 && m.c==0 && m.d==1 && m.tx==0 && m.ty==0;
        }
        private function wallStateReason():String {
            if(wallEnabledGetter==null)return "wallblend-enabled-getter-unavailable";
            var enabled:*;
            try {enabled=wallEnabledGetter();}
            catch(error:Error){last.wallBlendReadError=error.message;return "wallblend-enabled-getter-unavailable";}
            last.wallBlend={enabled:enabled,statusRead:false,
                source:"public-enabled-setting-and-actual-display-tree",
                requiredBuildVersion:WALL_VERSION};
            if(enabled!==false)return "wallblend-not-disabled";
            return "";
        }
        private function contextReason(w:*):String {
            if(unsafeState(w))return "inactive-or-sats";
            var wallReason:String=wallStateReason();if(wallReason)return wallReason;
            if(!residueStable())return "wallblend-residue-changed";
            if(!visual || !lower || !upper || lower===upper || grafon.visual!==visual ||
                lower.parent!==visual || upper.parent!==visual ||
                visual.getChildIndex(upper)!=visual.getChildIndex(lower)+1)return "backgrounds-not-adjacent";
            if(!neutral(lower) || !neutral(upper) || !identity(lower) || !identity(upper) ||
                lower.scrollRect || upper.scrollRect)return "background-parent-effects";
            for(var node:DisplayObject=visual;node && !(node is Stage);node=node.parent) {
                if(!neutral(node) || node.scrollRect || !node.visible)return "ancestor-effects";
                var m:Matrix=node.transform.matrix;
                if(!m || m.b!=0 || m.c!=0 || m.a<=0 || m.d<=0 || m.a!=m.d ||
                    !isFinite(m.tx) || !isFinite(m.ty))return "ancestor-transform";
            }
            if(!isFinite(Number(w.cam.scaleV)) || Number(w.cam.scaleV)<=0)return "camera-scale";
            for each(var setting:Object in settingGetters)if(setting["get"]()!==false)return "presentation-mod-enabled";
            if(held) {
                if(lower.visible || upper.visible || !presentation || !presentation.visible) {
                    ++conflicts;return "owned-visibility-changed";
                }
            } else if(!lower.visible || !upper.visible)return "native-background-hidden";
            if(presentation && (presentation.parent!==visual ||
                visual.getChildIndex(presentation)!=visual.getChildIndex(upper)+1))return "composite-depth-changed";
            return "";
        }
        private function bitmapReason(b:Bitmap,data:BitmapData,s:Object):String {
            if(!b || !data || b.bitmapData!==data || data.width!=SIZE || data.height!=SIZE ||
                !data.transparent || !neutral(b))return "native-bitmap-binding-or-effects";
            var m:Matrix=b.transform.matrix,r:Rectangle=b.scrollRect;
            if(!m || m.a!=1 || m.b!=0 || m.c!=0 || m.d!=1 || m.tx!=s.cx*SIDE || m.ty!=s.cy*SIDE ||
                !r || r.x!=GUTTER || r.y!=GUTTER || r.width!=SIDE || r.height!=SIDE)return "native-bitmap-geometry";
            return "";
        }
        /** BEFC keeps one constructor scratch Bitmap at index zero. Its internal
         * identity is unavailable: accept only this explicit hidden sentinel shape.
         * The one separately checked WB 0.5.9 disabled residue is not a scratch. */
        private function scratch(parent:DisplayObjectContainer):Boolean {
            if(parent.numChildren<1)return false;
            var b:Bitmap=parent.getChildAt(0) as Bitmap;
            return b && !b.visible && b.bitmapData && b.bitmapData.width==SIZE && b.bitmapData.height==SIZE &&
                b.bitmapData.transparent && neutral(b) && identity(b) && b.scrollRect==null;
        }

        /** The pinned WB 14112 build hides its ordinary-room layer on disable,
         * then returns before the scene branch that would dispose it. Source:
         * generated/wb-motion-source/WallBlendMod.as setEnabled/onFrame;
         * BackgroundBlendLayer.update creates this exact name and dimensions.
         * Runner pins WB14112; enabled=false plus the actual complete native
         * structure check replaces inaccessible sibling-class status counters.
         * This is a fixed-build structural exception, not a private-owner read.
         * Never alter, detach or composite this still-hidden layer. */
        private function permittedWallResidue(b:Bitmap):Boolean {
            return b && getQualifiedClassName(b)=="flash.display::Bitmap" && b.name===WALL_RESIDUE &&
                !b.visible && b.bitmapData && b.bitmapData.width==1920 && b.bitmapData.height==1000 &&
                b.bitmapData.transparent && b.pixelSnapping=="auto" && !b.smoothing &&
                neutral(b) && identity(b) && b.scrollRect==null;
        }
        private function residueStable():Boolean {
            if(residueInvalid)return false;
            if(!residueChecked || !residue)return true;
            if(residue.parent!==lower || lower.numChildren<2 || lower.getChildAt(1)!==residue ||
                residue.bitmapData!==residueData || !permittedWallResidue(residue)) {
                residueInvalid=true;return false;
            }
            return true;
        }
        private function nativeStructure(surfaces:Array):Boolean {
            if(int(grafon.sceneChunkSide)!=SIDE || upper.numChildren!=surfaces.length+1 ||
                !scratch(lower) || !scratch(upper))return false;
            var extra:int=lower.numChildren-surfaces.length-1;
            if(extra!=0 && extra!=1)return false;
            var next:Bitmap=extra==1?lower.getChildAt(1) as Bitmap:null;
            if(extra==1 && !permittedWallResidue(next))return false;
            if(!residueChecked) {
                residue=next;residueData=next?next.bitmapData:null;residueChecked=true;
            } else if(next!==residue || (next && next.bitmapData!==residueData)) {
                residueInvalid=true;return false;
            }
            if(!residueStable())return false;
            last.allowedWallResidues=extra;
            if(next)last.wallResidue={name:next.name,width:1920,height:1000,visible:next.visible,
                index:1,identityTracked:true,unchanged:true};
            return true;
        }

        /** Failure evidence only. Do not infer or accept a new scratch identity
         * from this description, and never change a rejected display node. */
        private function describeNode(node:DisplayObject,owners:Dictionary):Object {
            if(!node)return null;
            var out:Object={className:getQualifiedClassName(node),name:node.name,
                surfaceMember:owners[node]!=null};
            if(owners[node]!=null)out.surface={cx:owners[node].cx,cy:owners[node].cy};
            try {
                out.visible=node.visible;out.alpha=node.alpha;out.blendMode=node.blendMode;
                out.cacheAsBitmap=node.cacheAsBitmap;
                out.mask=node.mask?{className:getQualifiedClassName(node.mask),name:node.mask.name}:null;
                var fs:Array=node.filters;out.filterCount=fs.length;out.filterTypes=[];
                for each(var filter:Object in fs)out.filterTypes.push(getQualifiedClassName(filter));
                var m:Matrix=node.transform.matrix,r:Rectangle=node.scrollRect;
                out.matrix=m?{a:m.a,b:m.b,c:m.c,d:m.d,tx:m.tx,ty:m.ty}:null;
                out.hasMatrix3D=node.transform.matrix3D!=null;
                out.scrollRect=r?{x:r.x,y:r.y,width:r.width,height:r.height}:null;
                var c:ColorTransform=node.transform.colorTransform;
                out.colorTransform=[c.redMultiplier,c.greenMultiplier,c.blueMultiplier,c.alphaMultiplier,
                    c.redOffset,c.greenOffset,c.blueOffset,c.alphaOffset];
                if(node is Bitmap) {
                    var b:Bitmap=Bitmap(node);out.pixelSnapping=b.pixelSnapping;out.smoothing=b.smoothing;
                    out.bitmapData=b.bitmapData?{}:null;
                    if(b.bitmapData)try {
                        out.bitmapData.width=b.bitmapData.width;out.bitmapData.height=b.bitmapData.height;
                        out.bitmapData.transparent=b.bitmapData.transparent;
                    } catch(dataError:Error){out.bitmapData.error=dataError.message;}
                }
            } catch(error:Error){out.readError=error.message;}
            return out;
        }
        private function describeParent(parent:DisplayObjectContainer,surfaces:Array,layer:int):Object {
            var owners:Dictionary=new Dictionary(),s:Object;
            for each(s in surfaces)if(s && s.bitmaps && s.bitmaps.length>layer && s.bitmaps[layer])owners[s.bitmaps[layer]]=s;
            var out:Object={layer:layer,className:getQualifiedClassName(parent),name:parent.name,
                numChildren:parent.numChildren,expectedChildren:surfaces.length+1,
                allowedDisabledWallResidues:layer==1 && residue!=null?1:0,
                expectedSurfaces:surfaces.length,surfaceMembers:0,nonSurfaceCount:0,
                nonSurfaceTypes:{},nonSurfaceDetails:[],nonSurfaceDetailsLimit:16,
                firstChild:parent.numChildren?describeNode(parent.getChildAt(0),owners):null};
            try {out.scratchAccepted=scratch(parent);}catch(error:Error){out.scratchError=error.message;}
            for(var i:int=0;i<parent.numChildren;++i) {
                var node:DisplayObject=parent.getChildAt(i);
                if(owners[node]!=null){++out.surfaceMembers;continue;}
                ++out.nonSurfaceCount;
                var cls:String=getQualifiedClassName(node);
                out.nonSurfaceTypes[cls]=int(out.nonSurfaceTypes[cls])+1;
                if(out.nonSurfaceDetails.length<16) {
                    var detail:Object=describeNode(node,owners);detail.index=i;out.nonSurfaceDetails.push(detail);
                }
            }
            out.unlistedNonSurfaceCount=out.nonSurfaceCount-out.nonSurfaceDetails.length;
            return out;
        }
        private function structureFailure(surfaces:Array):Object {
            var out:Object={sceneChunkSide:grafon.sceneChunkSide,surfaces:surfaces.length,
                expectedChildren:surfaces.length+1};
            try {out.lower=describeParent(lower,surfaces,1);}catch(error:Error){out.lowerError=error.message;}
            try {out.upper=describeParent(upper,surfaces,2);}catch(upperError:Error){out.upperError=upperError.message;}
            return out;
        }

        public function update(w:*,enabled:Boolean):void {
            var start:int=getTimer();++updates;
            last={applied:false,enabled:enabled,reason:"native",pairs:0,surfaces:0,scratchSentinels:0,
                allowedWallResidues:0,
                nativeVisibleBitmaps:0,compositeBitmaps:0,displayBitmapsRemoved:0,copies:0,copyCost:0};
            try {
                if(!enabled){fallback("disabled");return;}
                if(unsafeState(w)){fallback("inactive-or-sats");return;}
                if(!sameContext(w))bind(w);
                var reason:String=contextReason(w);
                if(reason){fallback(reason);return;}
                var surfaces:Array=grafon.sceneSurfaces();last.surfaces=surfaces.length;
                if(!nativeStructure(surfaces)) {
                    last.structureFailure=structureFailure(surfaces);
                    fallback("foreign-child-or-native-scratch-mismatch");return;
                }
                last.scratchSentinels=2;
                var owners:Dictionary=new Dictionary(),selected:Array=[],needed:Dictionary=new Dictionary();
                var s:Object,b:Bitmap,u:Bitmap,i:int;
                for each(s in surfaces) {
                    if(!s || int(s.side)!=SIDE || int(s.gutter)!=GUTTER || s.x!=s.cx*SIDE-GUTTER ||
                        s.y!=s.cy*SIDE-GUTTER || !s.bitmaps || s.bitmaps.length!=4 ||
                        !s.nativeBuffers || s.nativeBuffers.length!=4 || !isFinite(Number(s.revision))) {
                        fallback("surface-shape");return;
                    }
                    b=s.bitmaps[1] as Bitmap;u=s.bitmaps[2] as Bitmap;
                    if(!b || !u || b.parent!==lower || u.parent!==upper || owners[b] || b.visible!==u.visible) {
                        fallback("surface-ownership-or-visibility");return;
                    }
                    owners[b]=s;
                }
                // Native ordering must agree in BOTH layers, including hidden
                // chunks; no assumption about sceneSurfaces dictionary order.
                var lowerStart:int=residue?2:1;
                for(i=lowerStart;i<lower.numChildren;++i) {
                    s=owners[lower.getChildAt(i)];
                    if(!s || upper.getChildAt(i-lowerStart+1)!==s.bitmaps[2]){fallback("native-order-mismatch");return;}
                    b=s.bitmaps[1];u=s.bitmaps[2];
                    if(!b.visible)continue;
                    reason=bitmapReason(b,s.nativeBuffers[1],s);
                    if(!reason)reason=bitmapReason(u,s.nativeBuffers[2],s);
                    if(reason || b.pixelSnapping!=u.pixelSnapping || b.smoothing!=u.smoothing) {
                        fallback(reason || "native-sampling-mismatch");return;
                    }
                    selected.push(s);needed[s]=true;
                }
                if(!selected.length || selected.length>MAX_PAIRS){fallback("visible-pair-limit");return;}
                if(!presentation) {
                    presentation=new Sprite();presentation.name="SceneBackgroundCompositeDiagnostic";
                    presentation.mouseEnabled=false;presentation.mouseChildren=false;presentation.visible=false;
                    visual.addChildAt(presentation,visual.getChildIndex(upper)+1);
                }
                for(var old:Object in records)if(!needed[old])release(old);
                for(i=0;i<selected.length;++i) {
                    s=selected[i];b=s.bitmaps[1];u=s.bitmaps[2];
                    var record:Object=records[s];
                    if(!record) {
                        var composite:Bitmap;
                        if(pool.length){composite=pool.pop();++reuses;}
                        else {composite=new Bitmap(new BitmapData(SIZE,SIZE,true,0));++allocations;}
                        composite.name="SceneBackgroundComposite";composite.pixelSnapping=b.pixelSnapping;
                        composite.smoothing=b.smoothing;composite.scrollRect=b.scrollRect.clone();
                        composite.transform.matrix=b.transform.matrix.clone();
                        record={bitmap:composite,revision:NaN,back:null,back2:null};records[s]=record;
                        presentation.addChild(composite);
                    }
                    composite=record.bitmap;
                    if(record.revision!==s.revision || record.back!==s.nativeBuffers[1] || record.back2!==s.nativeBuffers[2]) {
                        var copyStart:int=getTimer();
                        composite.bitmapData.copyPixels(s.nativeBuffers[1],s.nativeBuffers[1].rect,zero,null,null,false);
                        composite.bitmapData.copyPixels(s.nativeBuffers[2],s.nativeBuffers[2].rect,zero,null,null,true);
                        var elapsed:int=getTimer()-copyStart;copyCost+=elapsed;last.copyCost+=elapsed;
                        copies+=2;last.copies+=2;record.revision=s.revision;
                        record.back=s.nativeBuffers[1];record.back2=s.nativeBuffers[2];
                    }
                    if(presentation.getChildIndex(composite)!=i)presentation.setChildIndex(composite,i);
                }
                if(!held) {
                    originalLower=lower.visible;originalUpper=upper.visible;
                    lower.visible=false;upper.visible=false;parentWrites+=2;held=true;
                }
                if(!presentation.visible)presentation.visible=true;
                last.applied=true;last.reason="composited";last.pairs=selected.length;
                last.nativeVisibleBitmaps=selected.length*2;last.compositeBitmaps=selected.length;
                last.displayBitmapsRemoved=selected.length;++appliedUpdates;
            } catch(error:Error) {note(error);fallback("error-restored");}
            finally {updateCost+=getTimer()-start;}
        }
        private function release(s:Object):void {
            var record:Object=records[s],b:Bitmap=record.bitmap;
            if(b.parent)b.parent.removeChild(b);
            if(pool.length<MAX_PAIRS)pool.push(b);
            else {b.bitmapData.dispose();b.bitmapData=null;++disposals;}
            delete records[s];
        }
        public function clear():void {
            beginFrame();
            for(var s:Object in records)release(s);
            for each(var b:Bitmap in pool){b.bitmapData.dispose();b.bitmapData=null;++disposals;}
            pool=[];records=new Dictionary();
            if(presentation && presentation.parent)presentation.parent.removeChild(presentation);
            presentation=null;world=null;location=null;grafon=null;visual=null;lower=null;upper=null;settingGetters=[];
            wallEnabledGetter=null;residue=null;residueData=null;residueChecked=false;residueInvalid=false;
        }
        public function snapshot():Object {
            return {version:VERSION,diagnosticOnly:true,performanceAcceptance:false,updates:updates,
                appliedUpdates:appliedUpdates,prepareCalls:prepareCalls,restores:restores,parentWrites:parentWrites,
                copies:copies,allocations:allocations,reuses:reuses,disposals:disposals,
                liveCopies:allocations-disposals,pool:pool.length,heldParents:held?2:0,
                attachedCompositeBitmaps:presentation?presentation.numChildren:0,
                updateCost:updateCost,copyCost:copyCost,prepareCost:prepareCost,
                conflicts:conflicts,errors:errorCount,errorDetails:errors.concat(),last:last,
                requiredWallBlendVersion:WALL_VERSION,wallStatusRead:false,
                wallEligibilitySource:"public-enabled-setting-and-actual-display-tree",
                trackedWallResidues:residue?1:0,residueIdentityInvalid:residueInvalid,
                pixelStatus:"Requires same-frame verify at each camera/zoom; compositing and resampling need not commute",
                scope:"BEFC 400px backgrounds; WB14112/RV/LAD disabled; only one exact hidden WB1920 residue allowed; no SATS",
                scratchIdentity:"Two hidden first-child sentinels match BEFC structure; internal field identity is not read",
                residueIdentity:"Pinned WB14112/public enabled getter and complete actual child ownership; unique index-1 hidden residue with stable node/data identity; private owner/status is not read",
                limitation:"Same-value external visibility writes cannot be distinguished; source pixel changes must advance revision"};
        }
        private function capture(w:*):BitmapData {
            var data:BitmapData=new BitmapData(w.main.stage.stageWidth,w.main.stage.stageHeight,false,0);
            data.draw(w.main.stage);return data;
        }
        private function references(w:*):Array {
            var result:Array=[];
            for each(var parent:DisplayObjectContainer in [w.grafon.visBack,w.grafon.visBack2]) {
                result.push({parent:parent,visible:parent.visible,owner:parent.parent,count:parent.numChildren});
                for(var i:int=0;i<parent.numChildren;++i) {
                    var b:Bitmap=parent.getChildAt(i) as Bitmap;
                    if(!b)throw new Error("Non-bitmap background child at verification");
                    result.push({b:b,parent:parent,index:i,data:b.bitmapData,visible:b.visible,
                        matrix:b.transform.matrix.toString(),clip:b.scrollRect?b.scrollRect.toString():null,
                        snap:b.pixelSnapping,smooth:b.smoothing});
                }
            }
            return result;
        }
        private function unchanged(refs:Array):Boolean {
            for each(var r:Object in refs) {
                if(r.b) {
                    var b:Bitmap=r.b;
                    if(b.parent!==r.parent || r.parent.getChildAt(r.index)!==b || b.bitmapData!==r.data ||
                        b.visible!==r.visible || b.transform.matrix.toString()!=r.matrix ||
                        (b.scrollRect?b.scrollRect.toString():null)!==r.clip ||
                        b.pixelSnapping!==r.snap || b.smoothing!==r.smooth)return false;
                } else if(r.parent.parent!==r.owner || r.parent.visible!==r.visible || r.parent.numChildren!=r.count)return false;
            }
            return true;
        }
        /** Terminal/same-frame only. Leaves the complete original presentation
         * restored, disposes every probe image, and never advances native logic. */
        public function verify(w:*):Object {
            beginFrame();
            var result:Object={version:VERSION,diagnosticOnly:true,sameFrame:true,applied:false,equal:false,
                restored:false,bindingsRestored:false,changedPixels:0,maxChannelDifference:0};
            var before:BitmapData=null,after:BitmapData=null,restored:BitmapData=null;
            var delta:*=null,restoreDelta:*=null,refs:Array=null;
            try {
                refs=references(w);before=capture(w);update(w,true);
                result.state=snapshot();result.applied=held && last.applied;
                if(!result.applied)result.reason=last.reason;
                else {
                    result.camera={scale:w.cam.scaleV,x:w.visual.x,y:w.visual.y};
                    after=capture(w);clear();restored=capture(w);
                    delta=after.compare(before);restoreDelta=restored.compare(before);
                    result.equal=delta===0;result.restored=restoreDelta===0;result.bindingsRestored=unchanged(refs);
                    if(delta is BitmapData) {
                        for(var y:int=0;y<before.height;++y) {
                            var a:Vector.<uint>=before.getVector(new Rectangle(0,y,before.width,1));
                            var b:Vector.<uint>=after.getVector(new Rectangle(0,y,after.width,1));
                            for(var x:int=0;x<a.length;++x)if(a[x]!=b[x]) {
                                ++result.changedPixels;
                                for(var shift:int=0;shift<=24;shift+=8)
                                    result.maxChannelDifference=Math.max(result.maxChannelDifference,
                                        Math.abs(int((a[x]>>>shift)&255)-int((b[x]>>>shift)&255)));
                            }
                        }
                    } else if(delta!==0)result.compareError=delta;
                }
            } catch(error:Error){note(error);result.error=error.message;}
            finally {
                clear();
                if(refs)result.bindingsRestored=unchanged(refs);
                if(delta is BitmapData)delta.dispose();if(restoreDelta is BitmapData)restoreDelta.dispose();
                if(before)before.dispose();if(after)after.dispose();if(restored)restored.dispose();
                result.cleanup=snapshot();
            }
            return result;
        }
    }
}
