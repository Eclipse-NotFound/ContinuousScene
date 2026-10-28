package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.events.Event;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;

    /** Terminal-only observation of native same-frame gotoAndStop.
     * Never calls animate(), World.step(), play(), or a production guard.
     * A native frame script may mutate the real visual. Exit without saving,
     * travelling, further performance samples, or returning to gameplay.
     */
    public class ScenePlayerTimelineChecks {
        public static function run(w:*):Object {
            var result:Object={version:"player-same-frame-timeline-1",diagnosticOnly:true,
                performanceEligible:false,terminalOnly:true,passed:false,inconclusive:false,
                cases:[],limitations:[
                    "Only the already stopped current body pose is observed; no other pose or transition is selected.",
                    "Synchronous captures cannot prove behavior at the next native timeline/render event.",
                    "Same-frame equality does not prove a production guard, cross-frame equivalence, or performance benefit.",
                    "No marker is deliberately changed, so an idempotent frame script may remain unobservable.",
                    "Native goto may have side effects that cannot be undone. Exit without saving or further gameplay."
                ],cleanup:{listenersRemoved:false,bitmapsDisposed:0}};
            var owned:Array=[],clips:Array=[],root:DisplayObjectContainer=null,body:MovieClip=null;
            var counters:Object={added:0,removed:0,frameConstructed:0};
            var listener:Function=function(e:Event):void {
                if(e.type==Event.ADDED)++counters.added;
                else if(e.type==Event.REMOVED)++counters.removed;
                else if(e.type==Event.FRAME_CONSTRUCTED)++counters.frameConstructed;
            };
            var rootListening:Boolean=false;
            try {
                if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")!=0)
                    return inconclusive(result,"An isolated continuous-motion test application is required");
                if(!w || !w.gg || !w.swfStage || !w.gg.vis)
                    return inconclusive(result,"No native player visual/stage");
                if(w.sats && w.sats.active)return inconclusive(result,"SATS is active");
                root=w.gg.vis as DisplayObjectContainer;
                body=path(root,["osn","body"]) as MovieClip;
                if(!root || !body || !root.stage)return inconclusive(result,"The real native body is not on stage");
                result.eligibility={className:getQualifiedClassName(body),frame:body.currentFrame,
                    label:body.currentFrameLabel,isPlaying:body.isPlaying,osnLabel:path(root,["osn"]).currentFrameLabel};
                if(body.isPlaying)return inconclusive(result,"Current body is playing; stopping it would change the test state");
                if(body.currentFrame<1)return inconclusive(result,"Current body has no valid native frame");
                var width:int=w.swfStage.stageWidth,height:int=w.swfStage.stageHeight;
                if(width<=0 || height<=0 || width>4096 || height>4096)
                    return inconclusive(result,"Stage capture dimensions are outside the diagnostic bound");
                var ancestor:DisplayObject=root;
                while(ancestor) {
                    if(!ancestor.visible || ancestor.alpha<=0)
                        return inconclusive(result,"Player visual has an invisible ancestor");
                    ancestor=ancestor.parent;
                }
                if(!root.getBounds(w.swfStage).intersects(new Rectangle(0,0,width,height)))
                    return inconclusive(result,"Player visual is outside the captured viewport");
                var ids:Dictionary=new Dictionary(),sequence:Object={next:1};
                collectClips(root,clips);
                root.addEventListener(Event.ADDED,listener,true);
                root.addEventListener(Event.REMOVED,listener,true);
                rootListening=true;
                for each(var clip:MovieClip in clips)clip.addEventListener(Event.FRAME_CONSTRUCTED,listener);

                // Two captures with no native call reject a noisy oracle first.
                var initial:Object=snapshot(w,root,ids,sequence),eventsBefore:Object=eventCopy(counters);
                var first:BitmapData=capture(w,width,height,owned);
                var second:BitmapData=capture(w,width,height,owned);
                var before:Object=snapshot(w,root,ids,sequence);
                var baseline:Object=compareCase("capture-noop",initial,before,first,second,
                    eventDifference(eventsBefore,counters));
                result.cases.push(baseline);
                if(!baseline.passed)return inconclusive(result,"Same-frame capture/tree oracle is not stable");

                var expectedFrame:int=body.currentFrame;
                for(var i:int=0;i<2;++i) {
                    if(path(root,["osn","body"])!==body || body.isPlaying || body.currentFrame!=expectedFrame)
                        throw new Error("Body identity, stopped state, or target frame changed before native call");
                    eventsBefore=eventCopy(counters);
                    body.gotoAndStop(expectedFrame);
                    var immediate:Object=snapshot(w,root,ids,sequence);
                    var afterPixels:BitmapData=capture(w,width,height,owned);
                    var after:Object=snapshot(w,root,ids,sequence);
                    var row:Object=compareCase("native-same-frame-"+(i+1),before,after,second,afterPixels,
                        eventDifference(eventsBefore,counters));
                    row.requestedFrame=expectedFrame;
                    row.immediateTreeEqual=equal(before.tree,immediate.tree);
                    row.immediateReferencesEqual=equal(before.references,immediate.references);
                    row.immediateStateEqual=equal(before.state,immediate.state);
                    row.afterCaptureStable=equal(immediate,after);
                    row.passed=row.passed && row.immediateTreeEqual && row.immediateReferencesEqual
                        && row.immediateStateEqual && row.afterCaptureStable;
                    result.cases.push(row);
                    if(!row.passed)break;
                    before=after;second=afterPixels;
                }
                result.events=eventCopy(counters);
                result.passed=result.cases.length==3;
                for each(row in result.cases)if(!row.passed)result.passed=false;
            } catch(error:Error) {
                result.passed=false;result.error={name:error.name,id:error.errorID,message:error.message};
            } finally {
                if(rootListening) {
                    root.removeEventListener(Event.ADDED,listener,true);
                    root.removeEventListener(Event.REMOVED,listener,true);
                }
                for each(clip in clips)clip.removeEventListener(Event.FRAME_CONSTRUCTED,listener);
                result.cleanup.listenersRemoved=true;
                for each(var bitmap:BitmapData in owned) {
                    bitmap.dispose();++result.cleanup.bitmapsDisposed;
                }
            }
            return result;
        }

        private static function inconclusive(result:Object,reason:String):Object {
            result.passed=false;result.inconclusive=true;result.reason=reason;return result;
        }
        private static function path(value:*,names:Array):* {
            for each(var key:String in names) {
                if(value==null || !(key in value))return null;
                value=value[key];
            }
            return value;
        }
        private static function identity(value:*,ids:Dictionary,sequence:Object):int {
            if(value==null)return 0;
            if(!ids[value])ids[value]=sequence.next++;
            return int(ids[value]);
        }
        private static function collectClips(value:DisplayObject,clips:Array):void {
            if(value is MovieClip)clips.push(value);
            var container:DisplayObjectContainer=value as DisplayObjectContainer;
            if(container)for(var i:int=0;i<container.numChildren;++i)collectClips(container.getChildAt(i),clips);
        }
        private static function snapshot(w:*,root:DisplayObjectContainer,ids:Dictionary,sequence:Object):Object {
            var out:Object={tree:[],references:{},state:{}};
            walk(root,out.tree,ids,sequence);
            var names:Array=["osn","osn.body","osn.body.head","osn.body.head.morda",
                "osn.body.head.morda.eye","osn.body.head.morda.hair","osn.body.head.morda.konec",
                "osn.body.head.morda.magic","osn.body.tail","osn.body.sleg1","osn.body.sleg1.mark",
                "osn.body.rwing","osn.body.lwing","osn.body.pip1","osn.body.pip2",
                "osn.body.frleg3","osn.body.flleg3"];
            for each(var name:String in names)out.references[name]=identity(path(root,name.split(".")),ids,sequence);
            var u:*=w.gg,weapon:*=u.currentWeapon;
            out.references.player=identity(u,ids,sequence);
            out.references.visual=identity(u.vis,ids,sequence);
            out.references.currentWeapon=identity(weapon,ids,sequence);
            out.references.weaponOwner=identity(path(weapon,["owner"]),ids,sequence);
            out.references.weaponVisual=identity(path(weapon,["vis"]),ids,sequence);
            out.references.weaponParent=identity(path(weapon,["vis","parent"]),ids,sequence);
            out.references.childArray=identity(u.childObjs,ids,sequence);
            out.references.children=[];
            for each(var child:* in u.childObjs)out.references.children.push(identity(child,ids,sequence));
            out.state.player=fields(u,["X","Y","dx","dy","weaponX","weaponY","magicX","magicY",
                "celX","celY","storona","stay","isSit","isLaz","levit","animState"]);
            out.state.weapon=fields(weapon,["X","Y","rot","hold","t_attack","t_reload","t_pump",
                "ready","off","hp","durability"]);
            out.state.mark=fields(path(root,["osn","body","sleg1","mark"]),["visible","alpha"]);
            var morda:*=path(root,["osn","body","head","morda"]);
            var end:*=path(morda,["konec"]);
            if(morda is DisplayObject && end is DisplayObject) {
                var global:Point=(morda as DisplayObject).localToGlobal(new Point(end.x,end.y));
                out.state.magicEndGlobal=[global.x,global.y];
                if(root.parent) {
                    var local:Point=root.parent.globalToLocal(global);
                    out.state.magicEndParent=[local.x,local.y];
                }
            } else out.state.magicEndGlobal=null;
            return out;
        }
        private static function walk(value:DisplayObject,rows:Array,ids:Dictionary,sequence:Object):void {
            var matrix:Matrix=value.transform.matrix,ct:*=value.transform.colorTransform;
            var rect:Rectangle=value.scrollRect,container:DisplayObjectContainer=value as DisplayObjectContainer;
            var row:Object={id:identity(value,ids,sequence),parent:identity(value.parent,ids,sequence),
                name:value.name,className:getQualifiedClassName(value),index:value.parent?value.parent.getChildIndex(value):-1,
                children:container?container.numChildren:0,visible:value.visible,alpha:value.alpha,
                blendMode:value.blendMode,cacheAsBitmap:value.cacheAsBitmap,mask:identity(value.mask,ids,sequence),
                matrix:matrix?[matrix.a,matrix.b,matrix.c,matrix.d,matrix.tx,matrix.ty]:null,
                color:[ct.redMultiplier,ct.greenMultiplier,ct.blueMultiplier,ct.alphaMultiplier,
                    ct.redOffset,ct.greenOffset,ct.blueOffset,ct.alphaOffset],
                scroll:rect?[rect.x,rect.y,rect.width,rect.height]:null,filters:[]};
            for each(var filter:* in value.filters) {
                var f:Object=fields(filter,["alpha","angle","blurX","blurY","color","distance","hideObject",
                    "inner","knockout","quality","strength","matrix","colors","alphas","ratios"]);
                f.className=getQualifiedClassName(filter);row.filters.push(f);
            }
            if(value is MovieClip) {
                var clip:MovieClip=value as MovieClip;
                row.frame=clip.currentFrame;row.label=clip.currentFrameLabel;row.currentLabel=clip.currentLabel;
                row.isPlaying=clip.isPlaying;row.totalFrames=clip.totalFrames;
            }
            rows.push(row);
            if(container)for(var i:int=0;i<container.numChildren;++i)walk(container.getChildAt(i),rows,ids,sequence);
        }
        private static function fields(value:*,names:Array):Object {
            var result:Object={};
            if(value==null)return result;
            for each(var key:String in names)if(key in value) {
                var item:*=value[key];
                if(item==null || item is String || item is Number || item is Boolean)result[key]=item;
                else if(item is Array)result[key]=(item as Array).concat();
            }
            return result;
        }
        private static function capture(w:*,width:int,height:int,owned:Array):BitmapData {
            var bitmap:BitmapData=new BitmapData(width,height,true,0xFF000000);
            owned.push(bitmap);bitmap.draw(w.swfStage);return bitmap;
        }
        private static function compareCase(name:String,before:Object,after:Object,a:BitmapData,b:BitmapData,events:Object):Object {
            var pixels:Object=comparePixels(a,b),tree:Boolean=equal(before.tree,after.tree);
            var refs:Boolean=equal(before.references,after.references),state:Boolean=equal(before.state,after.state);
            return {name:name,passed:pixels.equal && tree && refs && state
                    && events.added==0 && events.removed==0 && events.frameConstructed==0,
                pixels:pixels,treeEqual:tree,referencesEqual:refs,stateEqual:state,events:events,
                before:before,after:after};
        }
        private static function comparePixels(a:BitmapData,b:BitmapData):Object {
            var compared:*=a.compare(b);
            if(compared is Number)return {equal:compared===0,compareCode:compared,width:a.width,height:a.height};
            var diff:BitmapData=compared as BitmapData;
            var count:int=0,maxDelta:int=0;
            try {
                var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect);
                for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i]) {
                    ++count;
                    for(var shift:int=0;shift<=24;shift+=8)
                        maxDelta=Math.max(maxDelta,Math.abs(int((av[i]>>>shift)&255)-int((bv[i]>>>shift)&255)));
                }
            } finally {if(diff)diff.dispose();}
            return {equal:false,differentPixels:count,maxChannelDelta:maxDelta,width:a.width,height:a.height};
        }
        private static function equal(a:*,b:*):Boolean {return JSON.stringify(a)==JSON.stringify(b);}
        private static function eventCopy(value:Object):Object {
            return {added:value.added,removed:value.removed,frameConstructed:value.frameConstructed};
        }
        private static function eventDifference(before:Object,after:Object):Object {
            return {added:after.added-before.added,removed:after.removed-before.removed,
                frameConstructed:after.frameConstructed-before.frameConstructed};
        }
    }
}
