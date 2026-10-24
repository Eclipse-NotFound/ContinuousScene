package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.events.Event;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.system.ApplicationDomain;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Terminal synchronous component. No Unit constructor, animate, AI or weapon call. */
    public class SceneTurretTimelineChecks {
        public static function run(w:*):Object {
            var started:int=getTimer();
            var out:Object={version:"turret-timeline-sync-1",diagnosticOnly:true,performanceEligible:false,
                terminalOnly:true,passed:false,synchronousPassed:false,inconclusive:false,
                timelineAdvanceVerified:false,candidateEligible:false,cases:[],coverage:[],
                restore:{passed:false},cleanup:{createdClones:0,stoppedClones:0,createdBitmaps:0,disposedBitmaps:0},
                limitations:[
                    "Detached native art clones only; no explicit real unit, weapon, AI, physics, RNG or game-frame call is made.",
                    "All numeric outer frames are inspected. A frame without an inner puha is reported explicitly and cannot establish a firing-animation claim.",
                    "Same-frame gotoAndStop is compared with a stopped/same-frame no-op. No tolerance is applied to pixels, recursive frame state, reference changes or observed events.",
                    "No ENTER_FRAME advancement is performed. Muzzle duration, loop/stop timing, on-stage FocusManager and later queued construction remain unverified.",
                    "A native goto may synchronously drain unrelated pending frame scripts. Only the selected real turret and world references are checked; this isolated process must terminate without saving.",
                    "A synchronous pass is only permission to investigate a separate real-frame component; never production or performance qualification."
                ]};
            var oldPause:*=null,paused:Boolean=false,real:*=null,realSaved:Object=null;
            var realIds:Dictionary=new Dictionary(),realSequence:Object={next:1};
            try {
                var app:String=NativeApplication.nativeApplication.applicationID;
                if(app.indexOf("pfe-modsettings-continuous-motion-")!=0)
                    throw new Error("Isolated continuous-motion application required");
                if(!w || !w.main || !w.gg || !w.loc || !w.grafon || !w.grafon.sceneLarge)
                    throw new Error("Initialized real large scene required");
                var ad:ApplicationDomain=w.main.loaderInfo.applicationDomain;
                var wc:Class=ad.getDefinition("fe.World") as Class;
                var tc:Class=ad.getDefinition("fe.unit.UnitTurret") as Class;
                if(wc[new QName("","w")]!==w)throw new Error("Actual host World identity mismatch");
                var turretCount:int=0,classes:Array=[];
                for each(var unit:* in w.loc.units) {
                    if(unit is tc && unit.loc===w.loc && unit.vis && unit.vis.osn && unit.vis.osn.puha is MovieClip) {
                        ++turretCount;
                        var className:String=getQualifiedClassName(unit.vis.osn.puha);
                        if(classes.indexOf(className)<0)classes.push(className);
                        if(real==null)real=unit;
                    }
                }
                if(real==null)throw new Error("No existing host-domain native turret with a puha visual");
                var actual:MovieClip=real.vis.osn.puha as MovieClip;
                var definitionName:String=getQualifiedClassName(actual);
                var art:Class=ad.getDefinition(definitionName) as Class;
                if(art==null || Object(actual)[new QName("","constructor")]!==art || !(actual is art))
                    throw new Error("Native art class identity mismatch");
                if(actual.totalFrames<1 || actual.totalFrames>32)
                    throw new Error("Unexpected native outer timeline length");
                if(real.tr<1 || real.tr>actual.totalFrames)
                    throw new Error("Observed turret tr is outside its native timeline");
                out.applicationID=app;
                out.nativeIdentity={world:true,turret:true,art:true,unitIndex:w.loc.units.indexOf(real),
                    className:getQualifiedClassName(real),artClass:definitionName,actualTr:real.tr,
                    actualFrame:actual.currentFrame,totalFrames:actual.totalFrames,turretCount:turretCount,
                    observedArtClasses:classes,testedArtClasses:[definitionName],allObservedArtClassesCovered:classes.length==1};
                realSaved=realState(w,real,realIds,realSequence);
                oldPause=w.onPause;w.onPause=true;paused=true;
                var all:Boolean=true;
                for(var tr:int=1;tr<=actual.totalFrames;++tr) {
                    var descriptor:Object=describeFrame(art,tr,out.cleanup);
                    out.coverage.push(descriptor);
                    var modes:Array=descriptor.hasInner?[{name:"stopped-1",frame:1,playing:false}]:
                        [{name:"no-inner",frame:0,playing:false}];
                    if(descriptor.hasInner && descriptor.innerFrames>=2) {
                        var frames:Array=[2,Math.max(2,Math.ceil(descriptor.innerFrames/2)),descriptor.innerFrames];
                        var seen:Array=[];
                        for each(var frame:int in frames)if(seen.indexOf(frame)<0) {
                            seen.push(frame);modes.push({name:"playing-"+frame,frame:frame,playing:true});
                        }
                    }
                    for each(var mode:Object in modes) {
                        var row:Object=runCase(art,tr,mode,out.cleanup);
                        out.cases.push(row);if(!row.passed)all=false;
                    }
                }
                out.synchronousPassed=all && out.cases.length>0 && classes.length==1;
                if(classes.length!=1) {
                    out.inconclusive=true;out.reason="Multiple native art classes observed; this narrow component covers one class only";
                }
            } catch(error:*) {
                out.error=String(error);out.inconclusive=true;out.synchronousPassed=false;
            } finally {
                if(paused)w.onPause=oldPause;
                if(realSaved!=null) {
                    try {
                        var restored:Object=realState(w,real,realIds,realSequence);
                        out.restore={passed:equal(realSaved,restored) && w.onPause===oldPause,
                            nativeStateEqual:equal(realSaved,restored),pauseRestored:w.onPause===oldPause,
                            before:realSaved,after:restored};
                    } catch(restoreError:*) {out.restore={passed:false,error:String(restoreError)};}
                }
                out.cleanup.passed=out.cleanup.createdClones==out.cleanup.stoppedClones &&
                    out.cleanup.createdBitmaps==out.cleanup.disposedBitmaps;
                out.passed=out.synchronousPassed && out.restore.passed && out.cleanup.passed;
                out.elapsedMs=getTimer()-started;
            }
            return out;
        }

        private static function describeFrame(art:Class,tr:int,cleanup:Object):Object {
            var clip:MovieClip=null,result:Object=null;
            try {
                clip=new art() as MovieClip;++cleanup.createdClones;
                if(clip==null)throw new Error("Native art constructor did not return MovieClip");
                clip.gotoAndStop(tr);
                var inner:MovieClip=innerOf(clip);
                result={outerFrame:tr,hasInner:inner!=null,innerClass:inner?getQualifiedClassName(inner):null,
                    innerFrames:inner?inner.totalFrames:0};
            } finally {if(clip){stopTree(clip);++cleanup.stoppedClones;}}
            return result;
        }

        private static function runCase(art:Class,tr:int,mode:Object,cleanup:Object):Object {
            var a:MovieClip=null,b:MovieClip=null,la:Object=null,lb:Object=null,bitmaps:Array=[];
            var result:Object={name:"tr-"+tr+"-"+mode.name,outerFrame:tr,innerInput:mode,passed:false};
            try {
                a=new art() as MovieClip;++cleanup.createdClones;
                b=new art() as MovieClip;++cleanup.createdClones;
                if(!a || !b || a===b || a.parent || b.parent || a.stage || b.stage)
                    throw new Error("Two independent detached native MovieClips required");
                a.gotoAndStop(tr);b.gotoAndStop(tr);
                configureInner(a,mode);configureInner(b,mode);
                var ia:Dictionary=new Dictionary(),ib:Dictionary=new Dictionary();
                var sa:Object={next:1},sb:Object={next:1};
                la=listen(a);lb=listen(b);
                // Fixed local capture rectangle for both before/after. Bounds and a transparent
                // border guard reject clipping rather than accepting matching cropped pictures.
                var bounds:Rectangle=a.getBounds(a).union(b.getBounds(b));
                bounds.x=Math.floor(bounds.x)-64;bounds.y=Math.floor(bounds.y)-64;
                bounds.width=Math.ceil(bounds.width)+129;bounds.height=Math.ceil(bounds.height)+129;
                if(bounds.width<1 || bounds.height<1 || bounds.width>2048 || bounds.height>2048)
                    throw new Error("Native art capture bounds exceed component limit");
                result.captureRect=[bounds.x,bounds.y,bounds.width,bounds.height];
                var a0:Object=snapshot(a,ia,sa),b0:Object=snapshot(b,ib,sb);
                var pa0:BitmapData=capture(a,bounds,bitmaps,cleanup),pb0:BitmapData=capture(b,bounds,bitmaps,cleanup);
                var aBefore:Object=snapshot(a,ia,sa),bBefore:Object=snapshot(b,ib,sb);
                result.baselinePixels=comparePixels(pa0,pb0);
                result.baselineTreeEqual=equal(aBefore,bBefore);
                result.captureOracleStable=equal(a0,aBefore) && equal(b0,bBefore);
                if(!result.baselinePixels.equal || !result.baselineTreeEqual || !result.captureOracleStable)
                    throw new Error("Independent native clone baseline or capture oracle differs");
                resetEvents(la);resetEvents(lb);
                if(a.currentFrame!=tr || b.currentFrame!=tr || a.isPlaying || b.isPlaying)
                    throw new Error("Outer timeline must be stopped at the requested same frame");
                a.gotoAndStop(tr);
                var guarded:Boolean=b.currentFrame==tr && !b.isPlaying;
                if(!guarded)b.gotoAndStop(tr);
                var aImmediate:Object=snapshot(a,ia,sa),bImmediate:Object=snapshot(b,ib,sb);
                var pa:BitmapData=capture(a,bounds,bitmaps,cleanup),pb:BitmapData=capture(b,bounds,bitmaps,cleanup);
                var aAfter:Object=snapshot(a,ia,sa),bAfter:Object=snapshot(b,ib,sb);
                result.guardSkipped=guarded;
                result.pixels=comparePixels(pa,pb);
                result.boundsContainAfter=bounds.containsRect(a.getBounds(a)) && bounds.containsRect(b.getBounds(b));
                result.transparentBorder=transparentBorder(pa) && transparentBorder(pb);
                result.immediateTreeEqual=equal(aImmediate,bImmediate);
                result.afterTreeEqual=equal(aAfter,bAfter);
                result.captureAfterStable=equal(aImmediate,aAfter) && equal(bImmediate,bAfter);
                result.nativeReferenceChanges=referenceChanges(aBefore,aAfter);
                result.guardReferenceChanges=referenceChanges(bBefore,bAfter);
                result.referencesEqual=equal(result.nativeReferenceChanges,result.guardReferenceChanges);
                result.nativeEvents=la.events.concat();result.guardEvents=lb.events.concat();
                result.eventsEqual=equal(result.nativeEvents,result.guardEvents);
                result.before={native:aBefore,guard:bBefore};
                result.immediate={native:aImmediate,guard:bImmediate};
                result.after={native:aAfter,guard:bAfter};
                result.passed=guarded && result.pixels.equal && result.boundsContainAfter && result.transparentBorder &&
                    result.immediateTreeEqual && result.afterTreeEqual && result.captureAfterStable &&
                    result.referencesEqual && result.eventsEqual;
            } catch(error:*) {result.error=String(error);result.passed=false;}
            finally {
                if(la)unlisten(a,la);if(lb)unlisten(b,lb);
                for each(var data:BitmapData in bitmaps){data.dispose();++cleanup.disposedBitmaps;}
                if(a){stopTree(a);++cleanup.stoppedClones;}if(b){stopTree(b);++cleanup.stoppedClones;}
            }
            return result;
        }

        private static function innerOf(outer:MovieClip):MovieClip {
            var key:QName=new QName("","puha");
            return key in outer?outer[key] as MovieClip:null;
        }
        private static function configureInner(outer:MovieClip,mode:Object):void {
            var inner:MovieClip=innerOf(outer);
            if(mode.frame==0){if(inner)throw new Error("Unexpected inner clip");return;}
            if(!inner || mode.frame>inner.totalFrames)throw new Error("Requested inner frame is absent");
            if(mode.playing)inner.gotoAndPlay(mode.frame);else inner.gotoAndStop(mode.frame);
            if(inner.currentFrame!=mode.frame || inner.isPlaying!==mode.playing)
                throw new Error("Native inner timeline did not retain requested input state");
        }
        private static function stopTree(value:DisplayObject):void {
            if(value is MovieClip)(value as MovieClip).stop();
            var c:DisplayObjectContainer=value as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i)stopTree(c.getChildAt(i));
        }
        private static function identity(value:*,ids:Dictionary,sequence:Object):int {
            if(value==null)return 0;if(!ids[value])ids[value]=sequence.next++;return int(ids[value]);
        }
        private static function normalizedName(name:String):String {
            return /^instance[0-9]+$/.test(name)?"<automatic-instance-name>":name;
        }
        private static function snapshot(root:MovieClip,ids:Dictionary,sequence:Object):Object {
            var result:Object={tree:[],innerID:identity(innerOf(root),ids,sequence)};
            walk(root,"root",result.tree,ids,sequence);return result;
        }
        private static function walk(value:DisplayObject,path:String,rows:Array,ids:Dictionary,sequence:Object):void {
            var m:Matrix=value.transform.matrix,ct:*=value.transform.colorTransform;
            var rect:Rectangle=value.scrollRect,c:DisplayObjectContainer=value as DisplayObjectContainer;
            var row:Object={path:path,id:identity(value,ids,sequence),name:normalizedName(value.name),
                className:getQualifiedClassName(value),children:c?c.numChildren:0,visible:value.visible,
                alpha:value.alpha,blendMode:value.blendMode,cacheAsBitmap:value.cacheAsBitmap,
                mask:identity(value.mask,ids,sequence),matrix:m?[m.a,m.b,m.c,m.d,m.tx,m.ty]:null,
                color:[ct.redMultiplier,ct.greenMultiplier,ct.blueMultiplier,ct.alphaMultiplier,
                    ct.redOffset,ct.greenOffset,ct.blueOffset,ct.alphaOffset],
                scroll:rect?[rect.x,rect.y,rect.width,rect.height]:null,filters:[]};
            for each(var filter:* in value.filters) {
                var f:Object={className:getQualifiedClassName(filter)};
                for each(var key:String in ["alpha","angle","blurX","blurY","color","distance","hideObject",
                    "inner","knockout","quality","strength","matrix","colors","alphas","ratios"])
                    if(key in filter)f[key]=filter[key] is Array?filter[key].concat():filter[key];
                row.filters.push(f);
            }
            if(value is MovieClip) {
                var clip:MovieClip=value as MovieClip;
                row.frame=clip.currentFrame;row.label=clip.currentFrameLabel;row.currentLabel=clip.currentLabel;
                row.isPlaying=clip.isPlaying;row.totalFrames=clip.totalFrames;
            }
            rows.push(row);
            if(c)for(var i:int=0;i<c.numChildren;++i)walk(c.getChildAt(i),path+"/"+i,rows,ids,sequence);
        }
        private static function referenceChanges(before:Object,after:Object):Array {
            var result:Array=[],old:Object={},now:Object={};
            for each(var row:Object in before.tree)old[row.path]=row.id;
            for each(row in after.tree){now[row.path]=row.id;if(old[row.path]!==row.id)result.push({path:row.path,before:old[row.path],after:row.id});}
            for each(row in before.tree)if(!(row.path in now))result.push({path:row.path,before:row.id,after:null});
            if(before.innerID!=after.innerID)result.push({path:"named-puha",before:before.innerID,after:after.innerID});
            return result;
        }
        private static function listen(root:MovieClip):Object {
            var out:Object={events:[],clips:[]};
            out.listener=function(e:Event):void {
                var target:DisplayObject=e.target as DisplayObject;
                out.events.push({type:e.type,className:target?getQualifiedClassName(target):null,
                    name:target?normalizedName(target.name):null,
                    frame:target is MovieClip?(target as MovieClip).currentFrame:null});
            };
            root.addEventListener(Event.ADDED,out.listener,true);
            root.addEventListener(Event.REMOVED,out.listener,true);
            collectClips(root,out.clips);
            for each(var clip:MovieClip in out.clips)clip.addEventListener(Event.FRAME_CONSTRUCTED,out.listener);
            return out;
        }
        private static function collectClips(value:DisplayObject,clips:Array):void {
            if(value is MovieClip)clips.push(value);
            var c:DisplayObjectContainer=value as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i)collectClips(c.getChildAt(i),clips);
        }
        private static function resetEvents(value:Object):void {value.events.length=0;}
        private static function unlisten(root:MovieClip,value:Object):void {
            root.removeEventListener(Event.ADDED,value.listener,true);root.removeEventListener(Event.REMOVED,value.listener,true);
            for each(var clip:MovieClip in value.clips)clip.removeEventListener(Event.FRAME_CONSTRUCTED,value.listener);
        }
        private static function capture(root:MovieClip,bounds:Rectangle,owned:Array,cleanup:Object):BitmapData {
            var bitmap:BitmapData=new BitmapData(int(bounds.width),int(bounds.height),true,0);
            owned.push(bitmap);++cleanup.createdBitmaps;
            bitmap.draw(root,new Matrix(1,0,0,1,-bounds.x,-bounds.y));return bitmap;
        }
        private static function comparePixels(a:BitmapData,b:BitmapData):Object {
            var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect);
            var count:int=0,alpha:int=0,maxRGB:int=0,maxAlpha:int=0;
            for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i]) {
                ++count;
                var da:int=Math.abs(int(av[i]>>>24)-int(bv[i]>>>24));
                if(da){++alpha;maxAlpha=Math.max(maxAlpha,da);}
                for(var shift:int=0;shift<24;shift+=8)
                    maxRGB=Math.max(maxRGB,Math.abs(int((av[i]>>>shift)&255)-int((bv[i]>>>shift)&255)));
            }
            return {equal:count==0,differentPixels:count,alphaDifferentPixels:alpha,maxRGBDelta:maxRGB,maxAlphaDelta:maxAlpha,
                width:a.width,height:a.height,scannedPixels:av.length};
        }
        private static function transparentBorder(bitmap:BitmapData):Boolean {
            for(var x:int=0;x<bitmap.width;++x)if((bitmap.getPixel32(x,0)>>>24)!=0 || (bitmap.getPixel32(x,bitmap.height-1)>>>24)!=0)return false;
            for(var y:int=0;y<bitmap.height;++y)if((bitmap.getPixel32(0,y)>>>24)!=0 || (bitmap.getPixel32(bitmap.width-1,y)>>>24)!=0)return false;
            return true;
        }
        private static function realState(w:*,unit:*,ids:Dictionary,sequence:Object):Object {
            return {world:identity(w,ids,sequence),loc:identity(w.loc,ids,sequence),player:identity(w.gg,ids,sequence),
                units:identity(w.loc.units,ids,sequence),unit:identity(unit,ids,sequence),unitLoc:identity(unit.loc,ids,sequence),
                vis:identity(unit.vis,ids,sequence),osn:identity(unit.vis.osn,ids,sequence),
                weapon:identity(unit.currentWeapon,ids,sequence),tr:unit.tr,X:unit.X,Y:unit.Y,dx:unit.dx,dy:unit.dy,
                visual:snapshot(unit.vis.osn.puha as MovieClip,ids,sequence)};
        }
        private static function equal(a:*,b:*):Boolean {return JSON.stringify(a)==JSON.stringify(b);}
    }
}
