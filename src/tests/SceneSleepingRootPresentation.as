package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Sprite;
    import flash.display.Stage;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Diagnostic only. Moves sleeping exact UnitRaider / UnitSlaver roots off-stage.
     * No wrappers, logic-list changes, visibility writes, or native add/remVisual.
     * The candidate scheduler invokes restoration before both resume call sites.
     */
    public class SceneSleepingRootPresentation {
        private var world:*,location:*,api:*;
        private var visual:DisplayObjectContainer;
        private var layers:Array,layerParents:Array;
        private var orders:Dictionary=new Dictionary();
        private var held:Dictionary=new Dictionary();
        private var rejected:Dictionary=new Dictionary(true);
        private var records:Array=[];
        private var parking:Sprite=new Sprite();
        private var gate:Function;
        private var installed:Boolean=false,valid:Boolean=true,clearing:Boolean=false;
        private var changed:int=0,restored:int=0,abandoned:int=0,claimed:int=0,callbacks:int=0;
        private var sleepCalls:int=0,wakeCalls:int=0,restoreBeforeWake:int=0,errors:int=0;
        private var elapsed:int=0,maxElapsed:int=0,conflicts:Array=[],skips:Object={};
        private var skipsByClass:Object={},claimEventsByClass:Object={};
        private var lastWake:Object;

        public function SceneSleepingRootPresentation() {
            var self:SceneSleepingRootPresentation=this;
            gate=function(u:*,sleeping:Boolean,clips:int=-1):void {self.onActivity(u,sleeping,clips);};
        }

        public function update(w:*,enabled:Boolean):void {
            try {
                if(!enabled){clear();return;}
                if(!valid)return;
                if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")!=0)
                    throw new Error("Sleeping-root diagnostic requires isolated motion storage");
                if(installed) {
                    if(!sameContext(w))throw new Error("World, location or native layer identity changed");
                    if(!api.setActivityPresentationGate(gate,gate))throw new Error("Presentation gate externally replaced");
                    return;
                }
                if(!w || !w.loc || !w.grafon.sceneLarge || w.onPause || w.allStat!=1)
                    throw new Error("Sleeping-root diagnostic requires active continuous scene");
                world=w;location=w.loc;visual=w.visual as DisplayObjectContainer;
                api=w.main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
                if(!api || !("setActivityPresentationGate" in api))throw new Error("Reviewed sleeping-root candidate is required");
                layers=w.grafon.visObjs.concat();layerParents=[];
                if(layers.length!=6 || !visual)throw new Error("Unexpected native display layers");
                orders=new Dictionary();rejected=new Dictionary(true);
                for each(var layer:DisplayObjectContainer in layers) {
                    if(!layer || !layer.parent)throw new Error("Detached native layer");
                    layerParents.push(layer.parent);
                    var order:Array=[];
                    for(var i:int=0;i<layer.numChildren;++i)order.push(layer.getChildAt(i));
                    orders[layer]=order;
                }
                if(!api.setActivityPresentationGate(gate,null))throw new Error("Another presentation gate is installed");
                installed=true;
            }catch(error:*){fail("update",error);}
        }

        private function sameContext(w:*):Boolean {
            if(!w || w!==world || w.loc!==location || w.visual!==visual || !w.grafon.sceneLarge)return false;
            if(w.grafon.visObjs.length!=layers.length)return false;
            for(var i:int=0;i<layers.length;++i)
                if(w.grafon.visObjs[i]!==layers[i] || layers[i].parent!==layerParents[i])return false;
            return true;
        }

        private function onActivity(u:*,sleeping:Boolean,clips:int=-1):void {
            var begin:int=getTimer();++callbacks;
            try {
                if(!installed || !valid || clearing)return;
                if(!sameContext(world))throw new Error("Native context changed inside activity callback");
                var record:Object=held[u];
                if(!sleeping) {
                    ++wakeCalls;
                    lastWake={clips:clips,wasParked:record!=null,restored:false};
                    if(record){restore(record);++restoreBeforeWake;lastWake.restored=true;}
                    return;
                }
                ++sleepCalls;
                if(record) {
                    record.nativeClips=clips;
                    validateOwnership(record);
                    for each(var parked:Object in record.roots)if(!outside(parked.bounds)) {
                        restore(record);skip(u,"viewport-approached");break;
                    }
                    return;
                }
                if(rejected[u])return;
                var unitClass:String=getQualifiedClassName(u);
                // Slaver only changes parentId/kolTrs in its constructor. Do
                // not broaden to UnitPon or all Raider subclasses: Merc/Encl
                // own separate arm roots; other subclasses need review.
                if(unitClass!="fe.unit::UnitRaider" && unitClass!="fe.unit::UnitSlaver")
                    {skip(u,"other-class");return;}
                if(u.loc!==location || u===world.gg || u.player || u.npc || u.boss || u.sost!=1 || !u.in_chain)
                    {skip(u,"unit-state");return;}
                if(!(u.childObjs is Array)){skip(u,"no-explicit-child-array");return;}
                record=collect(u);
                if(!record)return;
                record.nativeClips=clips;
                // Publish ownership before the first transfer so partial writes
                // remain recoverable if a display-list operation fails.
                held[u]=record;records.push(record);++claimed;
                var claimCounts:Object=claimEventsByClass;
                claimCounts[unitClass]=int(claimCounts[unitClass])+1;
                for each(var item:Object in record.roots) {
                    parking.addChild(item.root);item.parked=true;++changed;
                }
                validateOwnership(record);
            }catch(error:*){fail("callback",error);}
            finally {var ms:int=getTimer()-begin;elapsed+=ms;maxElapsed=Math.max(maxElapsed,ms);}
        }

        private function collect(u:*):Object {
            var record:Object={unit:u,location:location,body:u.vis,hpbar:u.hpbar,
                childArray:u.childObjs,children:[],roots:[]};
            var seen:Dictionary=new Dictionary();
            if(!addRoot(record,u,"vis",seen) || !addRoot(record,u,"hpbar",seen))return null;
            for each(var child:* in u.childObjs) {
                record.children.push(child);
                if(!child)continue;
                if(!("owner" in child) || child.owner!==u || child.in_chain)
                    {skip(u,"independent-child");return null;}
                if(!addRoot(record,child,"vis",seen))return null;
            }
            if(!record.roots.length){skip(u,"no-roots");return null;}
            return record;
        }

        private function addRoot(record:Object,owner:*,field:String,seen:Dictionary):Boolean {
            var root:DisplayObject=owner[field] as DisplayObject;
            if(!root)return true;
            if(seen[root])return true;
            seen[root]=true;
            var parent:DisplayObjectContainer=root.parent;
            var order:Array=parent?orders[parent]:null;
            var index:int=order?order.indexOf(root):-1;
            if(index<0){skip(record.unit,"not-an-original-direct-layer-root");return false;}
            var clips:Array=[];
            if(!safeTree(root,clips)){skip(record.unit,"filter-mask-or-playing-timeline");return false;}
            var bounds:Rectangle=root.getBounds(visual);
            if(!outside(bounds)){skip(record.unit,"root-near-viewport");return false;}
            record.roots.push({owner:owner,field:field,root:root,parent:parent,order:order,index:index,
                previous:index>0?order[index-1]:null,next:index+1<order.length?order[index+1]:null,
                bounds:bounds,clips:clips,parked:false,x:root.x,y:root.y,sx:root.scaleX,sy:root.scaleY,
                rotation:root.rotation,alpha:root.alpha,visible:root.visible,cache:root.cacheAsBitmap,blend:root.blendMode});
            return true;
        }

        private function safeTree(node:DisplayObject,clips:Array):Boolean {
            if(node.mask || node.filters.length || node.scrollRect)return false;
            var mc:MovieClip=node as MovieClip;
            if(mc) {
                if(mc.totalFrames>1 && mc.isPlaying)return false;
                clips.push({clip:mc,frame:mc.currentFrame,playing:mc.isPlaying});
            }
            var container:DisplayObjectContainer=node as DisplayObjectContainer;
            if(container)for(var i:int=0;i<container.numChildren;++i)
                if(!safeTree(container.getChildAt(i),clips))return false;
            return true;
        }

        private function outside(bounds:Rectangle):Boolean {
            var c:*=world.cam,s:Number=c.scaleV;
            if(!bounds || !isFinite(bounds.x) || !isFinite(bounds.y) || !isFinite(bounds.width)
                || !isFinite(bounds.height) || !isFinite(s) || s<=0)throw new Error("Invalid display/view bounds");
            if(bounds.isEmpty())return true;
            var left:Number=-c.vx/s-320,top:Number=-c.vy/s-320;
            return bounds.right<left || bounds.left>left+c.screenX/s+640
                || bounds.bottom<top || bounds.top>top+c.screenY/s+640;
        }

        private function validateOwnership(record:Object):void {
            var u:*=record.unit;
            if(u.loc!==record.location || u.vis!==record.body || u.hpbar!==record.hpbar
                || u.childObjs!==record.childArray || u.childObjs.length!=record.children.length)
                throw new Error("Unit or attachment identity changed");
            for(var i:int=0;i<record.children.length;++i)
                if(u.childObjs[i]!==record.children[i])throw new Error("Child object list changed");
            for each(var item:Object in record.roots) {
                if(item.owner[item.field]!==item.root)throw new Error("Visual root replaced");
                if(item.parked && item.root.parent!==parking)throw new Error("Parked root externally removed or reparented");
                if(!item.parked && item.root.parent!==item.parent)throw new Error("Original root parent changed");
                if(item.parent.parent!==layerParents[layers.indexOf(item.parent)])throw new Error("Original layer detached");
            }
        }

        private function restore(record:Object,strict:Boolean=true):void {
            if(strict)validateOwnership(record);
            for each(var item:Object in record.roots) {
                if(!item.parked)continue;
                var root:DisplayObject=item.root;
                // On failure, restore other roots independently. Never steal a
                // root already taken by native code or revive a replaced one.
                if(!strict && (root.parent!==parking || item.owner[item.field]!==root
                    || record.unit.loc!==record.location || !record.unit.in_chain)) {
                    if(root.parent===parking)parking.removeChild(root);
                    item.parked=false;++abandoned;continue;
                }
                if(!strict && item.parent.parent!==layerParents[layers.indexOf(item.parent)]) {
                    // An old layer was rebuilt/removed. Native redraw owns the
                    // new display tree; do not put old roots into that tree.
                    if(root.parent===parking)parking.removeChild(root);
                    item.parked=false;++abandoned;continue;
                }
                if(strict && (root.x!=item.x || root.y!=item.y || root.scaleX!=item.sx || root.scaleY!=item.sy
                    || root.rotation!=item.rotation || root.alpha!=item.alpha || root.visible!=item.visible
                    || root.cacheAsBitmap!=item.cache || root.blendMode!=item.blend || root.mask || root.filters.length))
                    throw new Error("Parked root presentation externally changed");
                if(strict)for each(var frame:Object in item.clips)
                    if(frame.clip.currentFrame!=frame.frame || frame.clip.isPlaying!=frame.playing)
                        throw new Error("Parked timeline changed");
                // Find a surviving original neighbor. Numeric indices alone
                // become stale when bullets/units are appended or removed.
                var parent:DisplayObjectContainer=item.parent,next:DisplayObject=null,previous:DisplayObject=null;
                var at:int=-1;
                for(var j:int=item.index+1;j<item.order.length;++j)
                    if(item.order[j].parent===parent){next=item.order[j];break;}
                for(j=item.index-1;j>=0;--j)
                    if(item.order[j].parent===parent){previous=item.order[j];break;}
                if(strict && next && previous && parent.getChildIndex(previous)>=parent.getChildIndex(next))
                    throw new Error("Original neighbor order externally changed");
                if(next)at=parent.getChildIndex(next);
                else if(previous)at=parent.getChildIndex(previous)+1;
                else if(parent.numChildren==0)at=0;
                else if(!strict)at=parent.numChildren;
                else throw new Error("No surviving original order anchor");
                parent.addChildAt(root,at);item.parked=false;++restored;
            }
            delete held[record.unit];
            var index:int=records.indexOf(record);if(index>=0)records.splice(index,1);
        }

        private function skip(u:*,reason:String):void {
            rejected[u]=true;var counts:Object=skips;counts[reason]=int(counts[reason])+1;
            var name:String=getQualifiedClassName(u),byClass:Object=skipsByClass[name];
            if(!byClass)skipsByClass[name]=byClass={};
            byClass[reason]=int(byClass[reason])+1;
        }

        /** Terminal synchronous check: caller may enable for one native frame
         * first, so zero-clips candidates have a real scheduler observation.
         * A successful zero-clips test intentionally calls native wake once;
         * exit immediately afterwards without saving or further timing.
         */
        public function verify(w:*):Object {
            var baseline:BitmapData,candidate:BitmapData,after:BitmapData;
            var result:Object={version:"sleeping-root-pixels-2",terminalOnly:true,diagnosticOnly:true,
                performanceAcceptance:false,valid:false,equal:false,restoredEqual:false,
                oracle:"Three BitmapData.draw(stage) captures in one synchronous frame",
                zeroClipsWake:{status:"inconclusive",reason:"No native-observed zero-clips parked unit"},
                history:"Native wake changes one unit's engaged latch. Exit without saving, travelling or further timing."};
            try {
                update(w,true);
                if(!valid || !installed)throw new Error("Presentation callback could not be installed");
                var known:Dictionary=new Dictionary();
                for each(var previous:Object in records)
                    if(previous.nativeClips>=0)known[previous.unit]={clips:previous.nativeClips};
                clear();
                if(!snapshot().valid || snapshot().pendingRestore!=0)throw new Error("Initial native restore failed");
                var stage:Stage=w.main.stage as Stage;
                if(!stage || stage.stageWidth<1 || stage.stageHeight<1 || stage.stageWidth>4096 || stage.stageHeight>2160)
                    throw new Error("Unsupported pixel-check viewport");
                result.view={width:stage.stageWidth,height:stage.stageHeight,quality:stage.quality,
                    cameraScale:w.cam.scaleV,vx:w.cam.vx,vy:w.cam.vy};
                baseline=capture(stage);
                update(w,true);
                var sleeping:Object=api.sleeping(location);
                if(!sleeping)throw new Error("No native sleep dictionary");
                for each(var unit:* in location.units)if(sleeping[unit])
                    onActivity(unit,true,known[unit]?int(known[unit].clips):-1);
                result.parked=snapshot();
                if(!result.parked.valid || result.parked.pendingRestore==0)throw new Error("No safe sleeping roots were actually detached");
                var zero:* = null;
                for each(var parked:Object in records)if(parked.nativeClips==0 && known[parked.unit]){zero=parked.unit;break;}
                candidate=capture(stage);
                clear();
                after=capture(stage);
                result.detached=compare(baseline,candidate);result.restored=compare(baseline,after);
                result.equal=result.detached.equal;result.restoredEqual=result.restored.equal;
                if(!snapshot().valid || snapshot().pendingRestore!=0)throw new Error("Native display restoration failed");
                if(zero && sleeping[zero]) {
                    update(w,true);onActivity(zero,true,0);
                    var claimed:Object=held[zero];
                    if(!claimed)throw new Error("Observed zero-clips unit could not be re-claimed");
                    var beforeWake:int=restoreBeforeWake;
                    api.wake(zero);
                    var restoredParents:Boolean=true;
                    for each(var root:Object in claimed.roots)
                        if(root.root.parent!==root.parent)restoredParents=false;
                    result.zeroClipsWake={status:"failed",nativeClips:lastWake?lastWake.clips:-1,
                        wasParked:lastWake && lastWake.wasParked,callbackRestored:lastWake && lastWake.restored,
                        restoredBeforeResume:restoreBeforeWake==beforeWake+1 && held[zero]==null,
                        restoredParents:restoredParents,sleepEntryRemoved:!sleeping[zero],
                        unit:{id:zero.id,x:zero.X,y:zero.Y},engagedLatchChanged:true};
                    if(lastWake && lastWake.clips==0 && lastWake.wasParked && lastWake.restored
                        && restoreBeforeWake==beforeWake+1 && restoredParents && held[zero]==null && !sleeping[zero])
                        result.zeroClipsWake.status="passed";
                }
                result.valid=result.equal && result.restoredEqual && result.zeroClipsWake.status!="failed";
            }catch(error:*) {fail("verify",error);result.error=String(error);}
            finally {
                clear();
                if(baseline)baseline.dispose();if(candidate)candidate.dispose();if(after)after.dispose();
            }
            result.cleanup=snapshot();
            result.valid=result.valid && result.cleanup.valid && result.cleanup.pendingRestore==0 && !result.cleanup.enabled;
            result.passed=result.valid;
            result.complete=result.valid && result.zeroClipsWake.status=="passed";
            return result;
        }

        private static function capture(stage:Stage):BitmapData {
            var pixels:BitmapData=new BitmapData(stage.stageWidth,stage.stageHeight,false,0);
            try {pixels.draw(stage);}catch(error:*) {pixels.dispose();throw error;}
            return pixels;
        }

        private static function compare(a:BitmapData,b:BitmapData):Object {
            var delta:* = a.compare(b);
            if(delta===0)return {equal:true,changedPixels:0};
            if(!(delta is BitmapData))return {equal:false,compareCode:delta};
            var bounds:Rectangle=delta.getColorBoundsRect(0xffffffff,0,false),count:int=0;
            try {
                for(var y:int=int(bounds.top);y<bounds.bottom;++y)for(var x:int=int(bounds.left);x<bounds.right;++x)
                    if(a.getPixel32(x,y)!=b.getPixel32(x,y))++count;
            }finally {delta.dispose();}
            return {equal:false,changedPixels:count,bounds:{x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height}};
        }

        private function fail(where:String,error:*):void {
            valid=false;++errors;
            if(conflicts.length<12)conflicts.push({where:where,message:String(error)});
            if(!clearing)clear();
        }

        public function clear():void {
            if(clearing)return;
            clearing=true;
            try {
                if(installed) {
                    installed=false;
                    if(!api.setActivityPresentationGate(null,gate)) {
                        valid=false;++errors;
                        if(conflicts.length<12)conflicts.push({where:"clear",message:"Gate ownership changed; external callback retained"});
                    }
                }
                var pending:Array=records.concat();
                for each(var record:Object in pending) {
                    try {restore(record);}catch(error:*) {
                        valid=false;++errors;
                        if(conflicts.length<12)conflicts.push({where:"restore",message:String(error)});
                        // Retain external alpha/frame/transform values while
                        // returning every still-owned root to its native layer.
                        try {restore(record,false);}catch(recovery:*) {
                            ++errors;
                            if(conflicts.length<12)conflicts.push({where:"recovery",message:String(recovery)});
                        }
                    }
                }
            }finally {clearing=false;}
        }

        public function snapshot():Object {
            var roots:int=0,zeroClips:int=0;
            for each(var record:Object in records) {
                if(record.nativeClips==0)++zeroClips;
                for each(var item:Object in record.roots)if(item.parked)++roots;
            }
            var skipCopy:Object={};for(var key:String in skips)skipCopy[key]=skips[key];
            var classesCopy:Object={},claimsCopy:Object={};
            for(var className:String in skipsByClass) {
                var reasons:Object=skipsByClass[className],reasonCopy:Object={};
                for(key in reasons)reasonCopy[key]=reasons[key];
                classesCopy[className]=reasonCopy;
            }
            for(className in claimEventsByClass)claimsCopy[className]=claimEventsByClass[className];
            return {version:"sleeping-root-probe-2",diagnosticOnly:true,performanceAcceptance:false,
                valid:valid && errors==0 && abandoned==0,enabled:installed,changed:changed,restored:restored,abandoned:abandoned,
                pendingRestore:roots,parkedUnits:records.length,claimedUnits:claimed,
                nativeObservedZeroClipsUnits:zeroClips,
                callbacks:callbacks,sleepCalls:sleepCalls,wakeCalls:wakeCalls,restoreBeforeWake:restoreBeforeWake,
                callbackMs:elapsed,maxCallbackMs:maxElapsed,errors:errors,conflicts:conflicts.concat(),skips:skipCopy,
                allowedClasses:["fe.unit::UnitRaider","fe.unit::UnitSlaver"],skipsByClass:classesCopy,claimEventsByClass:claimsCopy,
                parkingOnStage:parking.stage!=null,parkingChildren:parking.numChildren};
        }
    }
}
