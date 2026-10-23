package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.BitmapDataChannel;
    import flash.display.MovieClip;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.system.ApplicationDomain;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    /** Independent synchronous component check. Caller pins the exact host bytes.
     * Strict equality and the user-approved RGB tolerance are reported separately.
     * Every planned comparison executes; a pixel mismatch never stops later cases.
     * No display attachment, native step, save, or production cache installation.
     */
    public class SceneDecalStampProof {
        public static const VERSION:String = "decal-stamp-copy-pixels-1";
        public static const REQUIRED_HOST:String = "80CFD8CF3138EE59CBF6EDA0A1824A9EC960F413BD95E4B90D41DD0322B4FD3D";
        private static const SIDE:int = 400;

        public static function run(w:*):Object {
            var began:int=getTimer();
            var report:Object={version:VERSION,requiredHostSHA256:REQUIRED_HOST,
                diagnosticOnly:true,performanceEligible:false,valid:false,equal:false,tolerancePassed:false,
                completedAllCases:false,hostStateUnchanged:false,phase:"binding",cases:[],artwork:[],error:null,
                exactCases:0,toleranceCases:0,failedCases:0,invalidCases:0,executionErrors:[],
                tolerance:{red:1,green:1,blue:1,alpha:0,units:"integer 8-bit channel values"},
                coverage:{sameOrigin:true,adjacent320:true,allNativeMultiframePaintFrames:true,
                    repeatedSamePosition:true,interleavedOverlap:true,worldEdge:false,partialSourceStamp:false,
                    erase:false,hardlight:false,alphaChangingColorTransform:false},
                cleanup:{created:0,disposed:0,outstanding:0,errors:[],displayObjectsAttached:0},
                limitations:["Normal paint with alphaMultiplier=1 and alphaOffset=0 only; erase/hardlight and alpha-changing transforms are not qualified.",
                    "Caller verifies exact 80CF host bytes before launch; runtime identity proves only its lookup domain.",
                    "Fresh native static-shape artwork only; no production cache is installed.",
                    "RGB tolerance is per channel <=1/255; alpha must be exactly equal. equal remains strict equality.",
                    "Sequences accumulate both targets independently and compare only after the final operation; intermediate RGB is never reset or corrected.",
                    "Adjacent artwork is fully enclosed by the 80px shared gutter. World-edge clipping, partial stamp data and larger artwork remain untested.",
                    "This isolated component result proves neither live region dispatch, deferred replay nor speed. elapsedMs is diagnostic duration only.",
                    "Host-state observation covers the listed references/scalars, not every native buffer byte."]};
            var saved:Object=null;
            var ctx:Object={report:report,owned:[],classes:{},began:began};
            try {
                var app:String=NativeApplication.nativeApplication.applicationID;
                if(app.indexOf("pfe-modsettings-continuous-")!=0)
                    throw new Error("An isolated ContinuousScene application ID is required");
                if(!w || !w.main || !w.grafon || !w.loc || !w.gg)
                    throw new Error("Native world/main/grafon/location/player required");
                saved=hostState(w);
                var domain:ApplicationDomain=w.main.loaderInfo.applicationDomain as ApplicationDomain;
                if(!domain || !domain.hasDefinition("fe.World") ||
                    domain.getDefinition("fe.World")!==Object(w).constructor ||
                    !domain.hasDefinition("fe.graph.Grafon") ||
                    domain.getDefinition("fe.graph.Grafon")!==Object(w.grafon).constructor)
                    throw new Error("Main loader domain is not the actual World/Grafon domain; no lookup fallback");
                report.binding={world:getQualifiedClassName(w),grafon:getQualifiedClassName(w.grafon),
                    source:"w.main.loaderInfo.applicationDomain",identityMatched:true,applicationID:app};
                verifyChannelScan(ctx);
                var specs:Array=[["bullet_dyr",1],["bullet_metal",1],["bullet_tre",5],
                    ["bullet_wood",3],["expl_tre",5],["metal_tre",3],["punch_tre",4],["plaexpl_tre",5]];
                for each(var spec:Array in specs) {
                    if(!domain.hasDefinition(String(spec[0])))throw new Error("Missing native art: "+spec[0]);
                    var factory:Class=domain.getDefinition(String(spec[0])) as Class;
                    var clip:MovieClip=new factory();clip.stop();
                    if(getQualifiedClassName(clip)!=spec[0] || clip.totalFrames!=spec[1])
                        throw new Error("Native artwork identity/frame count mismatch: "+spec[0]);
                    ctx.classes[spec[0]]=factory;report.artwork.push({name:spec[0],frames:clip.totalFrames});
                }
                var plans:Array=makePlans(specs),sequences:Array=makeSequences(specs);
                report.plannedSinglePlans=plans.length;report.plannedSequencePlans=sequences.length;
                report.plannedSameOriginCases=plans.length+sequences.length;
                report.plannedAdjacentCases=(plans.length+sequences.length)*3;
                report.plannedCases=(plans.length+sequences.length)*4;
                report.plannedSingleCases=plans.length*4;report.plannedSequenceCases=sequences.length*4;
                var plan:Object;
                for(var phase:int=0;phase<2;++phase) {
                    report.phase=phase==0?"same-origin":"adjacent-320";
                    for each(plan in plans) {
                        try {exercise(ctx,plan,phase);}
                        catch(caseError:*) {report.executionErrors.push({name:plan.name,phase:report.phase,error:String(caseError)});}
                    }
                    for each(plan in sequences) {
                        try {exerciseSequence(ctx,plan,phase);}
                        catch(sequenceError:*) {report.executionErrors.push({name:plan.name,phase:report.phase,error:String(sequenceError)});}
                    }
                }
                report.completedAllCases=report.cases.length==report.plannedCases && report.executionErrors.length==0;
                report.valid=report.completedAllCases && report.invalidCases==0;
                report.equal=report.valid && report.exactCases==report.plannedCases;
                report.tolerancePassed=report.valid && report.toleranceCases==report.plannedCases;
                report.phase="complete";
            } catch(error:*) {
                report.error=error is Error?Error(error).name+": "+Error(error).message:String(error);
                report.valid=false;report.equal=false;report.tolerancePassed=false;
            } finally {
                disposeAll(ctx);report.cleanup.outstanding=report.cleanup.created-report.cleanup.disposed;
                report.hostStateUnchanged=saved!=null && sameHost(w,saved) &&
                    report.cleanup.outstanding==0 && report.cleanup.errors.length==0;
                if(!report.hostStateUnchanged) {report.valid=false;report.equal=false;report.tolerancePassed=false;}
                report.elapsedMs=getTimer()-began;
            }
            return report;
        }

        private static function makePlans(specs:Array):Array {
            var rows:Array=[];
            var geometries:Array=[[1,0,.25,.5],[1.7,.71,.5,.25],[-1.35,-.47,.75,.5],[.65,2.17,.5,.75]];
            // Preserve every original normal-paint geometry and original odd-frame case.
            for(var gi:int=0;gi<geometries.length;++gi)
                rows.push({name:"paint-normal-geometry"+gi,paint:"bullet_tre",frame:3,
                    operation:"paint",blend:"normal",geometry:geometries[gi],color:gi%3});
            // All 25 native multi-frame paint frames, including the formerly omitted even frames.
            for each(var spec:Array in specs)if(int(spec[1])>1)
                for(var frame:int=1;frame<=int(spec[1]);++frame)
                    rows.push({name:String(spec[0])+"-frame"+frame,paint:String(spec[0]),frame:frame,
                        operation:"paint",blend:"normal",geometry:geometries[frame%geometries.length],color:frame%3});
            return rows;
        }
        private static function makeSequences(specs:Array):Array {
            var rows:Array=[];
            for each(var spec:Array in specs)if(int(spec[1])>1) {
                rows.push({name:"repeat8-"+spec[0],paint:String(spec[0]),frames:int(spec[1]),
                    kind:"repeat-same-position",steps:8});
                rows.push({name:"interleaved12-"+spec[0],paint:String(spec[0]),frames:int(spec[1]),
                    kind:"interleaved-overlap",steps:12});
            }
            // Repeat the precise r4 mismatch geometry; exact geometry0 cases
            // alone cannot establish whether a known 1-channel error accumulates.
            rows.push({name:"known-r4-repeat8-bullet_tre-frame5",paint:"bullet_tre",frames:5,
                kind:"repeat-known-r4",steps:8,geometry:[1.7,.71,.5,.25]});
            rows.push({name:"known-r4-repeat32-bullet_tre-frame5",paint:"bullet_tre",frames:5,
                kind:"repeat-known-r4",steps:32,geometry:[1.7,.71,.5,.25]});
            return rows;
        }
        private static function prepared(ctx:Object,name:String,frame:int,geometry:Array,colorIndex:int,
            phase:int,offsetX:Number=0,offsetY:Number=0):Object {
            var paint:MovieClip=art(ctx,name,frame);
            var scale:Number=Number(geometry[0]),angle:Number=Number(geometry[1]);
            var x:Number=(phase==0?200:360)+Number(geometry[2])+offsetX;
            var y:Number=(phase==0?200:360)+Number(geometry[3])+offsetY;
            var radius:Number=extent(null,paint,scale,angle),allowed:Number=phase==0?140:24;
            if(radius>allowed)scale*=allowed/radius;
            var ct:ColorTransform=color(colorIndex),matrix:Matrix=transform(scale,angle,x,y);
            if(!enclosed(paint,matrix,phase))throw new Error("Fixture does not enclose full artwork: "+name);
            var stamp:BitmapData=bitmap(ctx);
            paint.scaleX=paint.scaleY=scale;
            paint.rotation=angle; // Preserve native degrees measurement vs radians draw matrix.
            stamp.draw(paint,matrix,ct,"normal",null,true);
            if(empty(stamp))throw new Error("Empty native source stamp: "+name);
            return {paint:paint,stamp:stamp,scale:scale,requestedScale:geometry[0],angle:angle,x:x,y:y,
                ct:ct,width:Math.round(paint.width/2+2)*2,height:Math.round(paint.height/2+2)*2};
        }
        private static function applyPrepared(ctx:Object,expected:BitmapData,actual:BitmapData,
            item:Object,ox:int,oy:int):void {
            var local:Matrix=transform(item.scale,item.angle,item.x-ox,item.y-oy);
            var shift:Matrix=new Matrix(1,0,0,1,-ox,-oy);
            // Each path preserves its own current alpha; never copy expected pixels into actual.
            paintWithAlpha(ctx,expected,item.paint,local,item.ct,"normal",item.x,item.y,item.width,item.height,ox,oy);
            paintWithAlpha(ctx,actual,item.stamp,shift,null,"normal",item.x,item.y,item.width,item.height,ox,oy);
        }
        private static function metadata(item:Object):Object {
            return {paintClass:getQualifiedClassName(item.paint),frame:item.paint.currentFrame,
                totalFrames:item.paint.totalFrames,scale:item.scale,requestedScale:item.requestedScale,
                angleRadians:item.angle,nativeMeasurementDegrees:item.angle,x:item.x,y:item.y,color:colorValues(item.ct)};
        }
        private static function exercise(ctx:Object,plan:Object,phase:int):void {
            var start:int=ctx.owned.length;
            try {
                var item:Object=prepared(ctx,plan.paint,plan.frame,plan.geometry,int(plan.color),phase);
                var destinations:Array=phase==0?[[0,0]]:[[320,0],[0,320],[320,320]];
                for each(var position:Array in destinations) {
                    var base:BitmapData=pattern(ctx,position[0],position[1]);
                    var expected:BitmapData=own(ctx,base.clone()),actual:BitmapData=own(ctx,base.clone());
                    applyPrepared(ctx,expected,actual,item,position[0],position[1]);
                    record(ctx,{name:plan.name,phase:ctx.report.phase,kind:"single",operation:"paint",blend:"normal",
                        paintClass:getQualifiedClassName(item.paint),frame:item.paint.currentFrame,totalFrames:item.paint.totalFrames,
                        scale:item.scale,requestedScale:item.requestedScale,angleRadians:item.angle,
                        nativeMeasurementDegrees:item.angle,x:item.x,y:item.y,color:colorValues(item.ct),
                        sourceOrigin:[0,0],targetOrigin:position,steps:[metadata(item)],stepCount:1,
                        worldEdgeCovered:false,partialSourceCovered:false},base,expected,actual);
                    disposeOne(ctx,actual);disposeOne(ctx,expected);disposeOne(ctx,base);
                }
            } finally {disposeSince(ctx,start);}
        }
        private static function exerciseSequence(ctx:Object,plan:Object,phase:int):void {
            var start:int=ctx.owned.length;
            try {
                var items:Array=[],steps:Array=[];
                for(var i:int=0;i<plan.steps;++i) {
                    var known:Boolean=plan.kind=="repeat-known-r4";
                    var repeated:Boolean=known || plan.kind=="repeat-same-position";
                    var geometry:Array=known?plan.geometry:(repeated?[1,0,.25,.5]:(i%2==0?[.9,.71,.5,.25]:[-.9,-.47,.75,.5]));
                    var frame:int=repeated?int(plan.frames):(i%int(plan.frames))+1;
                    var item:Object=prepared(ctx,plan.paint,frame,geometry,repeated?2:i%3,phase,
                        repeated?0:(i%2==0?-3.25:3.25),repeated?0:(i%2==0?-1.5:1.5));
                    items.push(item);steps.push(metadata(item));
                }
                var destinations:Array=phase==0?[[0,0]]:[[320,0],[0,320],[320,320]];
                for each(var position:Array in destinations) {
                    var base:BitmapData=pattern(ctx,position[0],position[1]);
                    var expected:BitmapData=own(ctx,base.clone()),actual:BitmapData=own(ctx,base.clone());
                    for each(item in items)applyPrepared(ctx,expected,actual,item,position[0],position[1]);
                    record(ctx,{name:plan.name,phase:ctx.report.phase,kind:plan.kind,operation:"paint",blend:"normal",
                        sourceOrigin:[0,0],targetOrigin:position,steps:steps,stepCount:plan.steps,
                        finalOnlyComparison:true,intermediateResets:0,knownR4Counterexample:plan.kind=="repeat-known-r4",
                        worldEdgeCovered:false,partialSourceCovered:false},base,expected,actual);
                    disposeOne(ctx,actual);disposeOne(ctx,expected);disposeOne(ctx,base);
                }
            } finally {disposeSince(ctx,start);}
        }
        private static function record(ctx:Object,row:Object,base:BitmapData,expected:BitmapData,actual:BitmapData):void {
            var positive:Boolean=changed(ctx,expected,base),diff:Object=compare(ctx,expected,actual);
            row.positiveChange=positive;row.valid=positive;row.exact=diff.count==0;
            row.tolerancePassed=positive && diff.alphaCount==0 && diff.maxARGB[1]<=1 && diff.maxARGB[2]<=1 && diff.maxARGB[3]<=1;
            row.diffCount=diff.count;row.maxChannelDelta=diff.maxChannelDelta;row.details=diff;
            row.elapsedSinceStartMs=getTimer()-ctx.began;
            ctx.report.cases.push(row);
            if(!positive)++ctx.report.invalidCases;
            if(row.exact && positive)++ctx.report.exactCases;
            if(row.tolerancePassed)++ctx.report.toleranceCases;else ++ctx.report.failedCases;
            if(ctx.report.cases.length%16==0)
                trace("[SceneDecalStampProof] completed="+ctx.report.cases.length+" elapsedMs="+row.elapsedSinceStartMs);
        }

        private static function art(ctx:Object,name:String,frame:int):MovieClip {
            var factory:Class = ctx.classes[name] as Class;
            var clip:MovieClip = new factory(); clip.gotoAndStop(frame);
            if(clip.currentFrame != frame || clip.filters.length != 0)
                throw new Error("Unexpected native timeline/filter: " + name);
            return clip;
        }

        private static function transform(scale:Number,angle:Number,x:Number,y:Number):Matrix {
            var m:Matrix = new Matrix();
            if(scale != 1) m.scale(scale,scale);
            if(angle != 0) m.rotate(angle);
            m.tx=x; m.ty=y; return m;
        }

        private static function transformed(clip:MovieClip,m:Matrix):Rectangle {
            if(!clip) return new Rectangle();
            var b:Rectangle=clip.getBounds(clip);
            var pts:Array=[m.transformPoint(new Point(b.left,b.top)),m.transformPoint(new Point(b.right,b.top)),
                m.transformPoint(new Point(b.left,b.bottom)),m.transformPoint(new Point(b.right,b.bottom))];
            var l:Number=Infinity,t:Number=Infinity,r:Number=-Infinity,bottom:Number=-Infinity;
            for each(var p:Point in pts) {l=Math.min(l,p.x);t=Math.min(t,p.y);r=Math.max(r,p.x);bottom=Math.max(bottom,p.y);}
            return new Rectangle(l,t,r-l,bottom-t);
        }

        private static function extent(cut:MovieClip,paint:MovieClip,scale:Number,angle:Number):Number {
            var radius:Number=0,m:Matrix=transform(scale,angle,0,0);
            for each(var clip:MovieClip in [cut,paint]) if(clip) {
                var b:Rectangle=transformed(clip,m);
                radius=Math.max(radius,Math.abs(b.left),Math.abs(b.right),Math.abs(b.top),Math.abs(b.bottom));
            }
            if(!isFinite(radius) || radius<=0) throw new Error("Invalid native artwork extent");
            return radius;
        }

        private static function enclosed(clip:MovieClip,m:Matrix,phase:int):Boolean {
            if(!clip) return true;
            var b:Rectangle=transformed(clip,m),low:int=phase==0?8:328;
            return !b.isEmpty() && b.left>=low && b.top>=low && b.right<=392 && b.bottom<=392;
        }

        private static function color(index:int):ColorTransform {
            if(index==1) return new ColorTransform(.72,.9,1.1,1,11,-7,5,0);
            if(index==2) return new ColorTransform(1.1,.8,.6,1,-9,13,21,0);
            return new ColorTransform();
        }
        private static function colorValues(ct:ColorTransform):Array {
            return [ct.redMultiplier,ct.greenMultiplier,ct.blueMultiplier,ct.alphaMultiplier,
                ct.redOffset,ct.greenOffset,ct.blueOffset,ct.alphaOffset];
        }

        // Native sceneDecalPaint alpha preservation (unchanged by the 80CF lighting-only host patch), including its asymmetric
        // source rounding/destination truncation. Each target reads its own alpha.
        private static function paintWithAlpha(ctx:Object,target:BitmapData,source:*,m:Matrix,
            ct:ColorTransform,blend:String,x:Number,y:Number,width:int,height:int,ox:int,oy:int):void {
            var sx:Number=Math.max(x-width/2,0),sy:Number=Math.max(y-height/2,0);
            var destination:Rectangle=new Rectangle(int(sx),int(sy),width,height);
            var dx:int=nearestEven(sx)-destination.x,dy:int=nearestEven(sy)-destination.y;
            var area:Rectangle=destination.intersection(new Rectangle(ox,oy,SIDE,SIDE));
            area.offset(-ox,-oy);
            var alpha:BitmapData=null;
            try {
                if(!area.isEmpty()) {
                    alpha=own(ctx,new BitmapData(int(area.width),int(area.height),false,0));
                    var sample:Rectangle=area.clone();sample.offset(dx,dy);
                    alpha.copyChannel(target,sample,new Point(),BitmapDataChannel.ALPHA,BitmapDataChannel.GREEN);
                }
                if(source is BitmapData) {
                    // Only the already transformed actual stamp takes this path.
                    // Keep its full source rect; copyPixels clips the integer translation to the target.
                    if(blend!="normal" || ct!=null || m.a!=1 || m.b!=0 || m.c!=0 || m.d!=1 ||
                        m.tx!=-ox || m.ty!=-oy)
                        throw new Error("Stamp copy requires normal composition and the original integer translation");
                    var stamp:BitmapData=source as BitmapData;
                    target.copyPixels(stamp,stamp.rect,new Point(-ox,-oy),null,null,true);
                } else target.draw(source,m,blend=="normal"?ct:null,blend,null,true);
                if(alpha) target.copyChannel(alpha,alpha.rect,area.topLeft,BitmapDataChannel.GREEN,BitmapDataChannel.ALPHA);
            } finally { if(alpha) disposeOne(ctx,alpha); }
        }
        private static function nearestEven(value:Number):int {
            var low:Number=Math.floor(value),fraction:Number=value-low;
            return int(fraction<.5?low:fraction>.5?low+1:low%2==0?low:low+1);
        }

        private static function pattern(ctx:Object,ox:int,oy:int):BitmapData {
            var b:BitmapData=bitmap(ctx),alphas:Array=[0,1,64,128,254,255];
            for(var y:int=0;y<SIDE;y+=8) for(var x:int=0;x<SIDE;x+=8) {
                var ix:int=(x+ox)/8,iy:int=(y+oy)/8;
                var a:uint=alphas[(ix+iy*3)%alphas.length];
                var rgb:uint=(((ix*37+iy*11)&255)<<16)|(((ix*13+iy*47)&255)<<8)|((ix*53+iy*7)&255);
                b.fillRect(new Rectangle(x,y,8,8),(a<<24)|rgb);
            }
            return b;
        }
        private static function empty(b:BitmapData):Boolean { return b.getColorBoundsRect(0xFF000000,0,false).isEmpty(); }
        private static function changed(ctx:Object,a:BitmapData,b:BitmapData):Boolean {
            var d:*=a.compare(b),yes:Boolean=d is BitmapData;
            if(yes) disposeOne(ctx,own(ctx,BitmapData(d)));
            else if(d!==0) throw new Error("Unexpected comparison code " + d);
            return yes;
        }
        private static function verifyChannelScan(ctx:Object):void {
            var start:int=ctx.owned.length;
            try {
                var a:BitmapData=own(ctx,new BitmapData(8,8,true,0));
                var b:BitmapData=own(ctx,a.clone());
                var specs:Array=[[[0,0,0x7F000000,0x80000000]],
                    [[7,7,0xFF102030,0xFF112030]],
                    [[7,0,0x7F000000,0x80000000],[0,7,0xFF102030,0xFF102031]],
                    [[0,0,0xFF102030,0xFF102130],[7,7,0x7F000000,0x80000000]]];
                var expectedCounts:Array=[[1,1,0],[1,0,1],[2,1,1],[2,1,1]];
                for(var index:int=0;index<specs.length;++index) {
                    var points:Array=specs[index];
                    a.fillRect(a.rect,0);b.fillRect(b.rect,0);
                    for each(var point:Array in points) {
                        a.setPixel32(point[0],point[1],uint(point[2]));
                        b.setPixel32(point[0],point[1],uint(point[3]));
                    }
                    var av:Vector.<uint> =a.getVector(a.rect),bv:Vector.<uint> =b.getVector(b.rect);
                    for(var y:int=0;y<8;++y)for(var x:int=0;x<8;++x)
                        if(av[y*8+x]!=a.getPixel32(x,y) || bv[y*8+x]!=b.getPixel32(x,y))
                            throw new Error("ARGB vector differs from source getPixel32");
                    av=null;bv=null;
                    var diff:Object=compare(ctx,a,b);
                    if(diff.scannedPixels!=64 || diff.count!=expectedCounts[index][0] ||
                        diff.alphaCount!=expectedCounts[index][1] || diff.rgbCount!=expectedCounts[index][2] ||
                        diff.maxChannelDelta!=1 || diff.violatingCount!=diff.alphaCount)
                        throw new Error("Full-channel scan sentinel omitted alpha or RGB changes: "+index);
                }
                ctx.report.comparisonScanCheck={passed:true,cases:specs.length,
                    alphaOnly:true,rgbOnly:true,oppositeCorners:true,fullScan:true,usesCompareBounds:false,
                    rawVectorMatchesGetPixel32:true};
            } finally {disposeSince(ctx,start);}
        }
        private static function compare(ctx:Object,a:BitmapData,b:BitmapData):Object {
            var result:Object={count:0,alphaCount:0,rgbCount:0,violatingCount:0,rgbBeyondToleranceCount:0,
                maxChannelDelta:0,maxARGB:[0,0,0,0],bounds:null,violationBounds:null,examples:[],failureExamples:[],scannedPixels:0};
            if(a.width!=b.width || a.height!=b.height)throw new Error("Comparison dimensions mismatch");
            var width:int=a.width,height:int=a.height;
            result.scannedPixels=width*height;
            var left:int=width,top:int=height,right:int=-1,bottom:int=-1;
            var badLeft:int=width,badTop:int=height,badRight:int=-1,badBottom:int=-1;
            var aPixels:Vector.<uint> =a.getVector(a.rect),bPixels:Vector.<uint> =b.getVector(b.rect);
            if(aPixels.length!=width*height || bPixels.length!=width*height)
                throw new Error("Incomplete ARGB vector");
            var pixelIndex:int=0;
            // AIR's compare difference bitmap cannot bound alpha-only changes reliably.
            // Read every actual source pixel; sentinels verify getVector vs getPixel32.
            // These vectors are local component scratch data, never a game cache.
            for(var y:int=0;y<height;++y)for(var x:int=0;x<width;++x) {
                var av:uint=aPixels[pixelIndex],bv:uint=bPixels[pixelIndex];++pixelIndex;
                if(av==bv)continue;
                ++result.count;
                var alphaDifferent:Boolean=(av>>>24)!=(bv>>>24),rgbBeyond:Boolean=false;
                if(alphaDifferent)++result.alphaCount;
                if((av&0xFFFFFF)!=(bv&0xFFFFFF))++result.rgbCount;
                var deltas:Array=[];
                for(var n:int=0;n<4;++n) {
                    var delta:int=Math.abs(int((av>>>(24-n*8))&255)-int((bv>>>(24-n*8))&255));
                    deltas.push(delta);result.maxARGB[n]=Math.max(result.maxARGB[n],delta);
                    result.maxChannelDelta=Math.max(result.maxChannelDelta,delta);
                    if(n>0 && delta>1)rgbBeyond=true;
                }
                if(rgbBeyond)++result.rgbBeyondToleranceCount;
                left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);
                if(result.examples.length<12)result.examples.push({x:x,y:y,direct:hex(av),stamp:hex(bv),deltaARGB:deltas});
                if(alphaDifferent || rgbBeyond) {
                    ++result.violatingCount;badLeft=Math.min(badLeft,x);badTop=Math.min(badTop,y);
                    badRight=Math.max(badRight,x);badBottom=Math.max(badBottom,y);
                    if(result.failureExamples.length<12)result.failureExamples.push({x:x,y:y,direct:hex(av),stamp:hex(bv),deltaARGB:deltas});
                }
            }
            if(result.count>0)result.bounds=[left,top,right-left+1,bottom-top+1];
            if(result.violatingCount>0)result.violationBounds=[badLeft,badTop,badRight-badLeft+1,badBottom-badTop+1];
            aPixels=null;bPixels=null;
            return result;
        }
        private static function hex(value:uint):String {
            var s:String=value.toString(16).toUpperCase();while(s.length<8)s="0"+s;return "0x"+s;
        }
        private static function bitmap(ctx:Object):BitmapData { return own(ctx,new BitmapData(SIDE,SIDE,true,0)); }
        private static function own(ctx:Object,b:BitmapData):BitmapData {ctx.owned.push(b);++ctx.report.cleanup.created;return b;}
        private static function disposeOne(ctx:Object,b:BitmapData):void {
            var i:int=ctx.owned.indexOf(b);if(i<0)return;
            try {b.dispose();ctx.owned[i]=null;++ctx.report.cleanup.disposed;}
            catch(e:Error) {ctx.report.cleanup.errors.push(e.message);}
        }
        private static function disposeSince(ctx:Object,start:int):void {
            for(var i:int=ctx.owned.length-1;i>=start;--i) if(ctx.owned[i]) disposeOne(ctx,ctx.owned[i]);
            // Keep a failed disposal referenced so the outer finally retries it.
        }
        private static function disposeAll(ctx:Object):void {disposeSince(ctx,0);}
        private static function hostState(w:*):Object {
            var g:*=w.grafon;
            return {loc:w.loc,gg:w.gg,g:g,front:g.frontBmp,back:g.visBack,back2:g.visBack2,water:g.visVoda,
                backChildren:g.visBack.numChildren,back2Children:g.visBack2.numChildren,waterChildren:g.visVoda.numChildren,
                resident:g.sceneResident,dirty:g.sceneLastDirtyCount,color:w.loc.cTransform,x:w.gg.X,y:w.gg.Y};
        }
        private static function sameHost(w:*,s:Object):Boolean {
            try {
                var g:*=w.grafon;
                return w.loc===s.loc && w.gg===s.gg && g===s.g && g.frontBmp===s.front &&
                    g.visBack===s.back && g.visBack2===s.back2 && g.visVoda===s.water &&
                    g.visBack.numChildren===s.backChildren && g.visBack2.numChildren===s.back2Children &&
                    g.visVoda.numChildren===s.waterChildren &&
                    g.sceneResident===s.resident && g.sceneLastDirtyCount===s.dirty &&
                    w.loc.cTransform===s.color && w.gg.X===s.x && w.gg.Y===s.y;
            } catch(e:Error) { return false; }
            return false; // Legacy Flex requires an explicit terminal return.
        }
    }
}
