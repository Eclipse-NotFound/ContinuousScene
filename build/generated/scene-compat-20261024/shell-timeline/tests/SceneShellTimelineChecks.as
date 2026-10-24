package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.MovieClip;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.display.Stage;
    import flash.events.Event;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.system.ApplicationDomain;
    import flash.utils.Dictionary;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Terminal component only: fresh native one-frame shell clones, then <=2 real frames. */
    public class SceneShellTimelineChecks {
        private var w:*;
        private var location:*;
        private var player:*;
        private var units:*;
        private var objects:*;
        private var oldPause:*=null;
        private var paused:Boolean=false;
        private var stage:Stage;
        private var holder:Sprite;
        private var pairs:Array=[];
        private var arms:Array=[];
        private var owned:Array=[];
        private var started:int;
        private var frameEvents:int=0;
        private var waitTicks:int=0;
        private var complete:Boolean=false;
        private var finished:Boolean=false;
        private var report:Object;
        private const CAPTURE:Rectangle=new Rectangle(-128,-128,256,256);

        public function begin(world:*):void {
            started=getTimer();w=world;
            report={version:"shell-timeline-components-1",diagnosticOnly:true,terminalOnly:true,
                performanceEligible:false,candidateEligible:false,globalQueueTimingVerified:false,
                passed:false,immediatePassed:false,localFramePassed:false,cases:[],errors:[],
                rng:{calls:0,policy:"One original Math.random draw per arm; no seed reset or compensation"},
                restore:{passed:false},cleanup:{passed:false,clones:0,stoppedClones:0,bitmaps:0,disposedBitmaps:0},
                limitations:[
                    "Only three fresh visualGilza pairs are tested; no real Part, weapon or world array is changed.",
                    "The native gilza emitter must have anim=0 and the exact host visualGilza class. Each fresh clip must be frame 1 of 1 with exactly one Shape before its first stop/goto/draw.",
                    "Each arm consumes the original one random draw. Later cacheAsBitmap, X/Y, rotation, scale and color operations are identical.",
                    "Off-screen owned stage children receive real ENTER_FRAME while world.onPause is true. This is local timeline acceptance, not gameplay or FPS measurement.",
                    "Sequential A/B calls may drain a shared global frame-script queue. Pixel/state agreement does not prove global queue order or that deferred work was eliminated.",
                    "Terminate this isolated process without saving or continuing gameplay."
                ]};
            try {
                var app:String=NativeApplication.nativeApplication.applicationID;
                if(app.indexOf("pfe-modsettings-continuous-motion-")!=0)
                    throw new Error("Isolated continuous-motion application required");
                if(!w || !w.main || !w.loc || !w.gg || !w.grafon || !w.grafon.sceneLarge)
                    throw new Error("Initialized real large scene required");
                var ad:ApplicationDomain=w.main.loaderInfo.applicationDomain;
                var wc:Class=ad.getDefinition("fe.World") as Class;
                var ec:Class=ad.getDefinition("fe.graph.Emitter") as Class;
                var art:Class=ad.getDefinition("visualGilza") as Class;
                var emitter:*=ec[new QName("","arr")]["gilza"];
                if(wc[new QName("","w")]!==w || !emitter || emitter.anim!==0 ||
                    emitter.visClass!==art || emitter.vis!=="visualGilza")
                    throw new Error("Native World/gilza emitter/class identity or anim=0 mismatch");
                location=w.loc;player=w.gg;units=location.units;objects=location.objs;
                stage=w.main.stage as Stage;if(!stage)throw new Error("Native stage missing");
                report.applicationID=app;
                report.nativeIdentity={world:true,emitter:true,artClass:"visualGilza",anim:emitter.anim,
                    emitterID:emitter.id,locationClass:getQualifiedClassName(location)};
                oldPause=w.onPause;w.onPause=true;paused=true;
                holder=new Sprite();holder.name="ContinuousSceneShellTimelineOwned";
                holder.x=-8192;holder.y=-8192;holder.mouseEnabled=false;holder.mouseChildren=false;
                var modes:Array=[
                    {name:"native-color",x:11.25,y:-7.5,rotation:0,scaleX:1,scaleY:1,color:location.cTransform},
                    {name:"rotated-small",x:-4.5,y:8.25,rotation:-37.5,scaleX:.75,scaleY:.75,color:new ColorTransform()},
                    {name:"mirrored-tint",x:5.25,y:3.5,rotation:123,scaleX:-1.25,scaleY:1.25,color:new ColorTransform(.8,1.16,.8,1,2,-1,3)}
                ];
                var all:Boolean=true;
                for each(var mode:Object in modes) {
                    var a:Object=fresh(art,"native"),b:Object=fresh(art,"stop");
                    var pair:Object={a:a,b:b,row:{name:mode.name,passed:false,
                        input:{x:mode.x,y:mode.y,rotation:mode.rotation,scaleX:mode.scaleX,scaleY:mode.scaleY,color:colorValues(mode.color)},
                        fresh:{native:a.fresh,stop:b.fresh}}};
                    pairs.push(pair);report.cases.push(pair.row);
                    operate(a,true,mode);operate(b,false,mode);
                    pair.row.firstOperation={native:a.operation,stop:b.operation};
                    // No goto or draw occurred before operate. Adding the owned containers
                    // follows initVis, like native Emitter.cast -> Location.addObj.
                    a.container.addChild(a.clip);b.container.addChild(b.clip);
                    pair.row.immediate=comparePair(pair,true);
                    pair.row.immediatePassed=pair.row.immediate.passed;
                    if(!pair.row.immediatePassed)all=false;
                    holder.addChild(a.container);holder.addChild(b.container);
                }
                report.immediatePassed=all && pairs.length==3;
                if(!report.immediatePassed) {
                    report.errors.push("Immediate equivalence failed; real-frame stage not entered");complete=true;
                } else {
                    stage.addEventListener(Event.ENTER_FRAME,onStageFrame,false,int.MAX_VALUE);
                    stage.addChild(holder);
                    report.frameWaitStartedAtMs=getTimer();
                }
            } catch(error:*) {report.errors.push(String(error));complete=true;}
        }

        public function tick():Boolean {
            if(complete || finished)return true;
            ++waitTicks;
            try {
                if(w.loc!==location || w.gg!==player || !w.onPause || holder.parent!==stage)
                    throw new Error("Paused native context or owned stage parent changed");
                var ready:Boolean=frameEvents>=1;
                for each(var arm:Object in arms)if(arm.frameEvents<1)ready=false;
                if(!ready && waitTicks>=2)throw new Error("No real stage and per-clip ENTER_FRAME within two ticks");
                if(ready) {
                    var all:Boolean=true;
                    for each(var pair:Object in pairs) {
                        pair.row.afterFrame=comparePair(pair,false);
                        pair.row.frameEvents={native:pair.a.frameEvents,stop:pair.b.frameEvents};
                        pair.row.passed=pair.row.immediatePassed && pair.row.afterFrame.passed;
                        if(!pair.row.passed)all=false;
                    }
                    report.localFramePassed=all && pairs.length==3;complete=true;
                }
            } catch(error:*) {report.errors.push(String(error));complete=true;}
            return complete;
        }

        public function finish():Object {
            if(finished)return report;finished=true;
            try {
                if(!complete)report.errors.push("Component interrupted before local frame acceptance");
                report.frameEvents=frameEvents;report.stageEnterFrames=frameEvents;report.waitTicks=waitTicks;
                report.restore={passed:false,worldRefsUnchanged:w && location && w.loc===location && w.gg===player &&
                    location.units===units && location.objs===objects,pauseRestored:false};
            } finally {
                try {
                    if(stage)stage.removeEventListener(Event.ENTER_FRAME,onStageFrame);
                } catch(cleanError:*) {report.errors.push("Owned display cleanup: "+String(cleanError));}
                for each(var arm:Object in arms) {
                    try {
                        if(arm.listener is Function) {
                            arm.clip.removeEventListener(Event.ADDED,arm.listener,true);
                            arm.clip.removeEventListener(Event.REMOVED,arm.listener,true);
                            arm.clip.removeEventListener(Event.FRAME_CONSTRUCTED,arm.listener);
                        }
                        if(arm.frameListener is Function)arm.clip.removeEventListener(Event.ENTER_FRAME,arm.frameListener);
                        arm.clip.stop();++report.cleanup.stoppedClones;
                        if(arm.clip.parent)arm.clip.parent.removeChild(arm.clip);
                    } catch(armError:*) {report.errors.push("Clone cleanup: "+String(armError));}
                }
                try {if(holder && holder.parent)holder.parent.removeChild(holder);}
                catch(holderError:*) {report.errors.push("Holder cleanup: "+String(holderError));}
                for each(var bitmap:BitmapData in owned) {
                    try {bitmap.dispose();++report.cleanup.disposedBitmaps;}
                    catch(bitmapError:*) {report.errors.push("Bitmap cleanup: "+String(bitmapError));}
                }
                if(paused)w.onPause=oldPause;
                report.restore.pauseRestored=paused && w.onPause===oldPause;
                report.restore.passed=report.restore.worldRefsUnchanged && report.restore.pauseRestored;
                report.cleanup.holderDetached=!holder || holder.parent==null;
                report.cleanup.passed=report.cleanup.clones==report.cleanup.stoppedClones &&
                    report.cleanup.bitmaps==report.cleanup.disposedBitmaps && report.cleanup.holderDetached;
                report.passed=report.immediatePassed && report.localFramePassed && report.restore.passed &&
                    report.cleanup.passed && report.errors.length==0;
                report.elapsedMs=getTimer()-started;
            }
            return report;
        }

        private function fresh(art:Class,label:String):Object {
            var clip:MovieClip=new art() as MovieClip;
            if(!clip)throw new Error("Native visualGilza construction failed");
            var arm:Object={clip:clip,label:label,container:new Sprite(),ids:new Dictionary(),sequence:{next:1},events:[],frameEvents:0};
            arms.push(arm);++report.cleanup.clones;
            // This qualification reads native state only, with no pre-goto, stop or draw.
            arm.fresh={className:getQualifiedClassName(clip),totalFrames:clip.totalFrames,currentFrame:clip.currentFrame,
                isPlaying:clip.isPlaying,children:clip.numChildren,shape:clip.numChildren==1 && clip.getChildAt(0) is Shape,
                parentAbsent:clip.parent==null,stageAbsent:clip.stage==null,
                constructorMatches:Object(clip)[new QName("","constructor")]===art};
            if(!arm.fresh.constructorMatches || arm.fresh.className!="visualGilza" || arm.fresh.totalFrames!=1 ||
                arm.fresh.currentFrame!=1 || !arm.fresh.shape || !arm.fresh.parentAbsent || !arm.fresh.stageAbsent)
                throw new Error("Fresh native one-frame/one-Shape visualGilza qualification failed");
            arm.before=snapshot(arm);arm.fresh.tree=arm.before;
            arm.listener=function(e:Event):void {
                arm.events.push({type:e.type,targetClass:getQualifiedClassName(e.target)});
            };
            arm.frameListener=function(e:Event):void {++arm.frameEvents;};
            clip.addEventListener(Event.ADDED,arm.listener,true);clip.addEventListener(Event.REMOVED,arm.listener,true);
            clip.addEventListener(Event.FRAME_CONSTRUCTED,arm.listener);
            clip.addEventListener(Event.ENTER_FRAME,arm.frameListener,false,int.MAX_VALUE);
            return arm;
        }

        private function operate(arm:Object,nativeGoto:Boolean,mode:Object):void {
            var clip:MovieClip=arm.clip;
            var random:Number=Math.random();++report.rng.calls;
            var chosen:int=Math.floor(random*clip.totalFrames+1);
            if(chosen!=1 || clip.totalFrames!=1 || clip.currentFrame!=1)
                throw new Error("Original random frame selection is not the qualified frame 1");
            if(nativeGoto)clip.gotoAndStop(chosen);else clip.stop();
            arm.operation={random:random,chosen:chosen,call:nativeGoto?"gotoAndStop(1)":"stop()",
                after:snapshot(arm),events:arm.events.concat()};
            if(clip.currentFrame!=1 || clip.isPlaying)throw new Error("First operation did not stop on native frame 1");
            // Native Part.initVis order; Emitter then applies scale/color before addObj.
            clip.cacheAsBitmap=true;clip.x=mode.x;clip.y=mode.y;clip.rotation=mode.rotation;
            clip.scaleX=mode.scaleX;clip.scaleY=mode.scaleY;clip.transform.colorTransform=mode.color;
        }

        private function comparePair(pair:Object,immediate:Boolean):Object {
            var a:Object=pair.a,b:Object=pair.b;
            var sa:Object=snapshot(a),sb:Object=snapshot(b);
            var pa:BitmapData=capture(a.container),pb:BitmapData=capture(b.container);
            var afterA:Array=snapshot(a),afterB:Array=snapshot(b);
            var out:Object={pixels:comparePixels(pa,pb),treeEqual:equal(sa,sb),captureStable:equal(sa,afterA) && equal(sb,afterB),
                firstOperationStateEqual:equal(a.operation.after,b.operation.after),
                firstOperationEventsEqual:equal(a.operation.events,b.operation.events),
                references:{native:referencesStable(a.before,afterA),stop:referencesStable(b.before,afterB)},
                events:{native:a.events.concat(),stop:b.events.concat()},
                nativeTree:afterA,stopTree:afterB,
                boundsContained:CAPTURE.containsRect(a.container.getBounds(a.container)) && CAPTURE.containsRect(b.container.getBounds(b.container)),
                borderClear:borderClear(pa) && borderClear(pb)};
            out.eventsEqual=equal(out.events.native,out.events.stop);
            if(immediate) {a.immediatePixels=pa;b.immediatePixels=pb;a.immediateTree=afterA;b.immediateTree=afterB;}
            else {
                out.nativeStablePixels=comparePixels(a.immediatePixels,pa);
                out.stopStablePixels=comparePixels(b.immediatePixels,pb);
                out.nativeStableTree=equal(a.immediateTree,afterA);out.stopStableTree=equal(b.immediateTree,afterB);
            }
            out.passed=out.pixels.equal && out.treeEqual && out.captureStable && out.firstOperationStateEqual && out.firstOperationEventsEqual && out.references.native &&
                out.references.stop && out.eventsEqual && out.boundsContained && out.borderClear &&
                (immediate || (out.nativeStablePixels.equal && out.stopStablePixels.equal && out.nativeStableTree && out.stopStableTree));
            return out;
        }
        private function onStageFrame(e:Event):void {++frameEvents;}
        private function snapshot(arm:Object):Array {
            var rows:Array=[];walk(arm.clip,"root",rows,arm.ids,arm.sequence);return rows;
        }
        private function walk(value:DisplayObject,path:String,rows:Array,ids:Dictionary,sequence:Object):void {
            if(!ids[value])ids[value]=sequence.next++;
            var m:Matrix=value.transform.matrix,c:DisplayObjectContainer=value as DisplayObjectContainer;
            var row:Object={path:path,id:ids[value],className:getQualifiedClassName(value),children:c?c.numChildren:0,
                matrix:[m.a,m.b,m.c,m.d,m.tx,m.ty],color:colorValues(value.transform.colorTransform),
                visible:value.visible,alpha:value.alpha,cacheAsBitmap:value.cacheAsBitmap,blendMode:value.blendMode,
                filterCount:value.filters.length,maskAbsent:value.mask==null};
            if(value is MovieClip) {
                var clip:MovieClip=value as MovieClip;row.currentFrame=clip.currentFrame;row.totalFrames=clip.totalFrames;row.isPlaying=clip.isPlaying;
            }
            rows.push(row);if(c)for(var i:int=0;i<c.numChildren;++i)walk(c.getChildAt(i),path+"/"+i,rows,ids,sequence);
        }
        private function referencesStable(before:Array,after:Array):Boolean {
            if(before.length!=after.length)return false;
            for(var i:int=0;i<before.length;++i)if(before[i].id!=after[i].id || before[i].path!=after[i].path)return false;
            return true;
        }
        private function capture(root:Sprite):BitmapData {
            var data:BitmapData=new BitmapData(256,256,true,0);owned.push(data);++report.cleanup.bitmaps;
            data.draw(root,new Matrix(1,0,0,1,128,128));return data;
        }
        private function comparePixels(a:BitmapData,b:BitmapData):Object {
            var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect);
            var count:int=0,alpha:int=0,maxRGB:int=0,maxAlpha:int=0;
            for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i]) {
                ++count;var da:int=Math.abs(int(av[i]>>>24)-int(bv[i]>>>24));
                if(da){++alpha;maxAlpha=Math.max(maxAlpha,da);}
                for(var shift:int=0;shift<24;shift+=8)maxRGB=Math.max(maxRGB,Math.abs(int((av[i]>>>shift)&255)-int((bv[i]>>>shift)&255)));
            }
            return {equal:count==0,differentPixels:count,alphaDifferentPixels:alpha,maxRGBDelta:maxRGB,maxAlphaDelta:maxAlpha,scannedPixels:av.length};
        }
        private function borderClear(data:BitmapData):Boolean {
            for(var x:int=0;x<data.width;++x)if((data.getPixel32(x,0)>>>24)!=0 || (data.getPixel32(x,data.height-1)>>>24)!=0)return false;
            for(var y:int=0;y<data.height;++y)if((data.getPixel32(0,y)>>>24)!=0 || (data.getPixel32(data.width-1,y)>>>24)!=0)return false;
            return true;
        }
        private function colorValues(ct:ColorTransform):Array {
            return [ct.redMultiplier,ct.greenMultiplier,ct.blueMultiplier,ct.alphaMultiplier,ct.redOffset,ct.greenOffset,ct.blueOffset,ct.alphaOffset];
        }
        private function equal(a:*,b:*):Boolean {return JSON.stringify(a)==JSON.stringify(b);}
    }
}
