package tests {
    import flash.desktop.NativeApplication;
    import flash.display.BitmapData;
    import flash.display.BitmapDataChannel;
    import flash.display.MovieClip;
    import flash.display.Sprite;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    /** ISOLATED PROBE END ONLY: call after every save/travel/repaint check, then
     * exit the probe. Pixels/revisions are restored; private sceneMarks cannot
     * be safely removed and must never be saved or replayed after this helper.
     * Single-frame wrappers contain real native artwork at a fixed native frame.
     */
    public class SceneDecalChecks {
        public static function run(w:*):Array {
            var result:Array=[];
            var isolatedId:String=NativeApplication.nativeApplication.applicationID;
            if(isolatedId!="pfe-modsettings-continuous-scene" && isolatedId.indexOf("pfe-modsettings-continuous-motion-")!=0) {
                add(result,"decal-isolated-probe-required",false);return result;
            }
            if(!w || !w.loc || !w.grafon || !w.grafon.sceneLarge) {
                add(result,"decal-large-scene-required",false);return result;
            }
            var cases:Array=[
                {name:"small-bullet-corner",cut:null,paint:SceneDecalMetalPaint,x:2560,y:640,scale:1,angle:0,blend:"normal"},
                {name:"rotated-scaled-bullet",cut:SceneDecalBulletCut,paint:SceneDecalCrackPaint,x:2559.5,y:640.25,scale:2.35,angle:0.71,blend:"hardlight"},
                {name:"mirrored-rotated-bullet",cut:SceneDecalBulletCut,paint:SceneDecalCrackPaint,x:2560.25,y:639.5,scale:-3.25,angle:-0.47,blend:"hardlight"}
            ];
            try {
                var explosion:MovieClip=new SceneDecalExplosionPaint();
                var artBounds:Rectangle=explosion.getBounds(explosion);
                var span:Number=Math.max(artBounds.width,artBounds.height);
                if(span<=0) throw new Error("Native explosion artwork has empty bounds");
                // Deliberately reaches beyond the old +/-512px centre rejection.
                cases.push({name:"large-explosion",cut:null,paint:SceneDecalExplosionPaint,
                    x:3840,y:1600,scale:Math.max(8,1400/span),angle:0.36,blend:"hardlight"});
                for each(var test:Object in cases) exercise(w,result,test);
            } catch(error:Error) {add(result,"decal-check-exception",false,error.message);}
            add(result,"decal-history-end-only",true,"Private sceneMarks now contain test artwork. Exit this isolated process; do not save, travel, or redraw.");
            // The caller may stop at its first failed assertion. Retain every
            // already-executed case without writing a game save or advancing a frame.
            try {
                var report:FileStream=new FileStream();
                try {
                    report.open(File.applicationStorageDirectory.resolvePath("scene-decal-checks.json"),FileMode.WRITE);
                    report.writeUTFBytes(JSON.stringify({reference:"single-local-native-canvas",assertions:result},null,2));
                } finally {report.close();}
            } catch(reportError:Error) {add(result,"decal-report-write",false,reportError.message);}
            return result;
        }

        public static function nativeArt(name:String,frame:int):MovieClip {
            var factory:Class=getDefinitionByName(name) as Class;
            var art:MovieClip=new factory();
            art.gotoAndStop(Math.min(frame,art.totalFrames));
            return art;
        }

        private static function exercise(w:*,rows:Array,test:Object):void {
            var g:*=w.grafon;
            var records:Array=[],surfaces:Array=g.sceneSurfaces();
            var template:BitmapData,expected:BitmapData,difference:BitmapData;
            var reference:BitmapData,referenceBefore:BitmapData,nativeLocal:BitmapData,nativePureDraw:BitmapData;
            var oldDirty:int=g.sceneLastDirtyCount,oldRedraws:int=g.sceneRedraws;
            var oldColor:ColorTransform=w.loc.cTransform;
            var started:int=getTimer();
            try {
                if(!surfaces.length) throw new Error("No resident surfaces");
                var full:Rectangle=surfaces[0].nativeBuffers[0].rect;
                // This is one periodic WORLD image. Overlapping chunk gutters
                // must contain the same pixels, independent of enumeration order.
                var templateX:int=surfaces[0].x,templateY:int=surfaces[0].y;
                template=worldPattern(full.width,full.height,templateX,templateY);
                for each(var surface:Object in surfaces) {
                    var front:BitmapData=surface.nativeBuffers[0];
                    if(front.width!=template.width || front.height!=template.height) throw new Error("Nonuniform surface size");
                    if((surface.x-templateX)%80!=0 || (surface.y-templateY)%80!=0)
                        throw new Error("Surface origins do not share the world pattern period");
                    records.push({surface:surface,data:front.clone(),revision:surface.revision});
                    front.copyPixels(template,template.rect,new Point());
                }
                var region:Object="sceneRegionStyle" in g ? g.sceneRegionStyle(w.loc,test.x,test.y) : null;
                var color:ColorTransform=region?region.cTransform:oldColor;
                var prefix:String="decal-"+test.name;
                // Flash computes transformed display bounds independently of the
                // production culler. Include the native alpha-restoration box as
                // well as cut/paint geometry, then add a generous exterior margin.
                // Native decal runs ONCE here. Running it separately on distant
                // chunks would clamp negative local y to zero and manufacture
                // alpha-copy rounding artifacts along every chunk's upper edge.
                var extent:Object=referenceExtent(test);
                var canvas:Rectangle=extent.canvas;
                referenceBefore=worldPattern(canvas.width,canvas.height,canvas.x,canvas.y);
                reference=referenceBefore.clone();
                nativeReference(reference,test.cut,test.paint,test.x-canvas.x,test.y-canvas.y,
                    test.scale,test.angle,test.blend,color);
                var delta:*=reference.compare(referenceBefore);
                var referenceChange:Rectangle=null;
                if(delta is BitmapData) {
                    difference=delta;referenceChange=difference.getColorBoundsRect(0xFFFFFFFF,0,false);
                    difference.dispose();difference=null;
                }
                var enclosed:Boolean=referenceChange && !referenceChange.isEmpty() &&
                    referenceChange.left>=64 && referenceChange.top>=64 &&
                    referenceChange.right<=reference.width-64 && referenceChange.bottom<=reference.height-64;
                add(rows,prefix+"-reference-encloses-native-output",enclosed,
                    {canvas:canvas.toString(),art:extent.art,alpha:extent.alpha,
                     changed:referenceChange?referenceChange.toString():null,minimumEdgeMargin:64});
                if(!enclosed) throw new Error("Native reference output reaches its canvas edge or is empty");
                referenceBefore.dispose();referenceBefore=null;
                g.decal(test.cut,test.paint,test.x,test.y,test.scale,test.angle,test.blend);
                var pixelChunks:int=0,dirtyChunks:int=0,missingDirty:int=0,badRevisions:int=0;
                var actualPixelChunks:int=0,actualMissingDirty:int=0;
                var alphaMismatchPixels:int=0,maxAlphaDelta:int=0,rejectedColorPixels:int=0;
                var insideAlphaMismatchPixels:int=0,rejectedAlphaPixels:int=0,differencePixels:int=0;
                var acceptedOutsideRasterPixels:int=0,rejectedOutsideRasterPixels:int=0;
                var nativeRoundingPixels:int=0,nativeRoundingChunks:int=0,unexplainedCompareChunks:int=0;
                var mismatches:Array=[],changedChunks:Array=[],dirty:Array=[];
                var changedWorld:Rectangle=null;
                for each(var saved:Object in records) {
                    surface=saved.surface;front=surface.nativeBuffers[0];
                    var revisionDelta:int=surface.revision-saved.revision;
                    if(revisionDelta!=0 && revisionDelta!=1) ++badRevisions;
                    if(revisionDelta!=0) {++dirtyChunks;dirty.push(surface);}
                    expected=template.clone();
                    var window:Rectangle=canvas.intersection(new Rectangle(surface.x,surface.y,full.width,full.height));
                    if(!window.isEmpty()) {
                        var source:Rectangle=window.clone();source.offset(-canvas.x,-canvas.y);
                        expected.copyPixels(reference,source,new Point(window.x-surface.x,window.y-surface.y));
                    }
                    // Every chunk is still checked, including every pixel wholly
                    // outside the independent reference canvas (unchanged pattern).
                    delta=expected.compare(template);
                    var actualChanged:Boolean=delta is BitmapData;
                    if(delta is BitmapData) {
                        difference=delta;
                        var localChange:Rectangle=difference.getColorBoundsRect(0xFFFFFFFF,0,false);
                        difference.dispose();difference=null;
                        localChange.offset(surface.x,surface.y);
                        changedWorld=changedWorld==null?localChange:changedWorld.union(localChange);
                        ++pixelChunks;changedChunks.push([surface.cx,surface.cy]);
                        if(revisionDelta==0) ++missingDirty;
                    }
                    delta=front.compare(expected);
                    if(delta!==0) {
                        var detail:Object={cx:surface.cx,cy:surface.cy,error:delta is BitmapData?"pixels":delta};
                        if(delta is BitmapData) {
                            difference=delta;detail.bounds=difference.getColorBoundsRect(0xFFFFFFFF,0,false).toString();
                            difference.dispose();difference=null;
                        }
                        // If actual differs from the oracle, inspect its own
                        // changed pixels too: omitted dirty revisions must fail
                        // even while the strict raster assertion is failing.
                        var actualPatternDelta:*=front.compare(template);
                        actualChanged=actualPatternDelta is BitmapData;
                        if(actualChanged) {
                            difference=actualPatternDelta;difference.dispose();difference=null;
                        }
                        // Within the world alpha-write box, alpha remains exact
                        // and any RGB difference needs the original local call.
                        // Outside it, compare each differing ARGB pixel against
                        // an independent native cut+draw without alpha copying.
                        nativeLocal=template.clone();
                        nativeReference(nativeLocal,test.cut,test.paint,test.x-surface.x,test.y-surface.y,
                            test.scale,test.angle,test.blend,color);
                        detail.nativeLocalVsGlobal=pixelDelta(expected,nativeLocal,surface.x,surface.y);
                        detail.actualVsNativeLocal=pixelDelta(nativeLocal,front,surface.x,surface.y);
                        // The old local alpha clamp can erase pixels outside the
                        // world box, so it cannot validate pure rasterization.
                        nativePureDraw=template.clone();
                        nativeReference(nativePureDraw,test.cut,test.paint,test.x-surface.x,test.y-surface.y,
                            test.scale,test.angle,test.blend,color,false);
                        detail.outsideAlphaPureNativeDraw=pureDrawDiagnostics(expected,front,nativePureDraw,
                            surface.x,surface.y,extent.alphaWriteBounds as Rectangle);
                        detail.actualVsGlobal=pixelDelta(expected,front,surface.x,surface.y,nativeLocal,
                            nativePureDraw,extent.alphaWriteBounds as Rectangle);
                        nativePureDraw.dispose();nativePureDraw=null;
                        var globalStats:Object=detail.actualVsGlobal;
                        alphaMismatchPixels+=globalStats.alphaDifferenceCount;
                        insideAlphaMismatchPixels+=globalStats.insideAlphaDifferenceCount;
                        rejectedAlphaPixels+=globalStats.rejectedAlphaDifferenceCount;
                        differencePixels+=globalStats.count;
                        acceptedOutsideRasterPixels+=globalStats.acceptedOutsideRasterDifferenceCount;
                        rejectedOutsideRasterPixels+=globalStats.rejectedOutsideRasterDifferenceCount;
                        maxAlphaDelta=Math.max(maxAlphaDelta,globalStats.maxAlphaDelta);
                        rejectedColorPixels+=globalStats.rejectedNativeColorDifferenceCount;
                        nativeRoundingPixels+=globalStats.acceptedNativeColorDifferenceCount;
                        if(globalStats.acceptedNativeColorDifferenceCount>0) ++nativeRoundingChunks;
                        if(globalStats.count==0) ++unexplainedCompareChunks;
                        detail.nativeEquivalent=globalStats.count>0 && globalStats.rejectedAlphaDifferenceCount==0 &&
                            globalStats.rejectedNativeColorDifferenceCount==0 && globalStats.rejectedOutsideRasterDifferenceCount==0;
                        nativeLocal.dispose();nativeLocal=null;
                        mismatches.push(detail);
                    }
                    if(actualChanged) {
                        ++actualPixelChunks;
                        if(revisionDelta==0) ++actualMissingDirty;
                    }
                    expected.dispose();expected=null;
                }
                add(rows,prefix+"-native-alpha-preservation",insideAlphaMismatchPixels==0 && rejectedAlphaPixels==0 &&
                    differencePixels<=64 && unexplainedCompareChunks==0,
                    {surfaces:records.length,pixels:records.length*template.width*template.height,
                     exactGlobalMatch:mismatches.length==0,alphaDifferenceCount:alphaMismatchPixels,maxAlphaDelta:maxAlphaDelta,
                     insideAlphaDifferenceCount:insideAlphaMismatchPixels,insideAlphaTolerance:0,
                     rejectedAlphaDifferenceCount:rejectedAlphaPixels,outsideRawChannelTolerance:8,
                     differencePixelCount:differencePixels,differencePixelLimit:64,
                     acceptedOutsideRasterPixels:acceptedOutsideRasterPixels,rejectedOutsideRasterPixels:rejectedOutsideRasterPixels,
                     alphaRule:"Inside the native world alpha box: exact alpha. Outside: each differing alpha pixel must match independent pure-native-draw ARGB exactly and all raw channels differ by at most 8. At most 64 total differing pixels per case, including gutters.",
                     unexplainedCompareChunks:unexplainedCompareChunks});
                add(rows,prefix+"-native-equivalent-buffer-pixels",insideAlphaMismatchPixels==0 && rejectedAlphaPixels==0 &&
                    rejectedColorPixels==0 && rejectedOutsideRasterPixels==0 && differencePixels<=64 && unexplainedCompareChunks==0,
                    {surfaces:records.length,pixels:records.length*template.width*template.height,
                     referenceCanvas:canvas.toString(),exactGlobalMatch:mismatches.length==0,
                     nativeRoundingPixels:nativeRoundingPixels,nativeRoundingChunks:nativeRoundingChunks,
                     rejectedColorPixels:rejectedColorPixels,alphaDifferenceCount:alphaMismatchPixels,
                     insideAlphaDifferenceCount:insideAlphaMismatchPixels,insideAlphaTolerance:0,
                     rejectedAlphaDifferenceCount:rejectedAlphaPixels,outsideRawChannelTolerance:8,
                     differencePixelCount:differencePixels,differencePixelLimit:64,
                     acceptedOutsideRasterPixels:acceptedOutsideRasterPixels,rejectedOutsideRasterPixels:rejectedOutsideRasterPixels,
                     premultipliedProductTolerance:255,normalizedPremultipliedTolerance:1/255,
                     roundingRule:"Inside alpha box: exact alpha; differing RGB must match native-local ARGB and abs(A*C-Aref*Cref)<=255 per RGB channel. Outside alpha box: every differing ARGB pixel must match independent pure-native-draw ARGB exactly and raw A/R/G/B delta<=8. Whole case has at most 64 differing pixels, including repeated gutters.",
                     mismatchChunks:mismatches.length,mismatches:mismatches});
                add(rows,prefix+"-crosses-neighbour-and-gutter",pixelChunks>=4 && missingDirty==0 && actualMissingDirty==0,
                    {pixelChunks:pixelChunks,dirtyChunks:dirtyChunks,missingDirty:missingDirty,
                     actualPixelChunks:actualPixelChunks,actualMissingDirty:actualMissingDirty,changedChunks:changedChunks});
                // Transparent native geometry can legitimately exceed the
                // changed-pixel box. Bound conservative dispatch by independent
                // Flash geometry plus the original alpha-restoration rectangle,
                // with a vector/antialias rim; never use production bounds or
                // the much larger reference canvas as the locality allowance.
                var outside:int=0,allowed:int=0;
                var locality:Rectangle=Rectangle(extent.geometryAndAlpha).clone();
                var margin:Number=16+Math.abs(Number(test.scale))*4;
                locality.inflate(margin,margin);
                if(changedWorld) {
                    for each(surface in surfaces)
                        if(locality.intersects(new Rectangle(surface.x,surface.y,template.width,template.height))) ++allowed;
                    for each(surface in dirty)
                        if(!locality.intersects(new Rectangle(surface.x,surface.y,template.width,template.height))) ++outside;
                }
                add(rows,prefix+"-dirty-work-is-local",changedWorld!=null && missingDirty==0 && actualMissingDirty==0 && outside==0 &&
                    dirtyChunks==g.sceneLastDirtyCount && dirtyChunks<records.length && badRevisions==0,
                    {dirty:dirtyChunks,oraclePixelChunks:pixelChunks,conservativeCandidates:allowed,outside:outside,
                     geometryAndAlpha:extent.geometryAndAlpha.toString(),antialiasMargin:margin,locality:locality.toString(),
                     dispatcher:g.sceneLastDirtyCount,badRevisions:badRevisions,elapsedMs:getTimer()-started});
                add(rows,prefix+"-no-terrain-redraw",g.sceneRedraws==oldRedraws && w.loc.cTransform===oldColor);
                if(test.name=="large-explosion")
                    add(rows,prefix+"-exceeds-old-centre-cutoff",changedWorld && (changedWorld.width>1024 || changedWorld.height>1024),
                        changedWorld?changedWorld.toString():null);
            } catch(error:Error) {add(rows,"decal-"+test.name+"-exception",false,error.message);}
            finally {
                for each(var record:Object in records) {
                    record.surface.nativeBuffers[0].copyPixels(record.data,record.data.rect,new Point());
                    record.surface.revision=record.revision;record.data.dispose();
                }
                g.sceneLastDirtyCount=oldDirty;w.loc.cTransform=oldColor;
                if(template) template.dispose();if(expected) expected.dispose();if(difference) difference.dispose();
                if(reference) reference.dispose();if(referenceBefore) referenceBefore.dispose();
                if(nativeLocal) nativeLocal.dispose();
                if(nativePureDraw) nativePureDraw.dispose();
            }
        }

        /** Full per-pixel diagnostics for one mismatching chunk. getPixel32
         * reports actual ARGB channel values, unlike BitmapData.compare's
         * encoded difference image. Counts include overlapping gutter copies;
         * world coordinates in the examples identify the same physical pixel.
         */
        private static function pixelDelta(expected:BitmapData,actual:BitmapData,worldX:int,worldY:int,
                                           nativeLocal:BitmapData=null,nativePureDraw:BitmapData=null,
                                           alphaBounds:Rectangle=null):Object {
            if(expected.width!=actual.width || expected.height!=actual.height)
                throw new Error("Diagnostic bitmap dimensions do not match");
            var count:int=0,maxA:int=0,maxR:int=0,maxG:int=0,maxB:int=0;
            var alphaCount:int=0,colorCount:int=0,overPremultipliedTolerance:int=0;
            var maxPremultipliedR:int=0,maxPremultipliedG:int=0,maxPremultipliedB:int=0;
            var nativeColorMismatch:int=0,acceptedNativeColor:int=0,rejectedNativeColor:int=0;
            var insideAlphaCount:int=0,rejectedAlphaCount:int=0;
            var insideDifferences:int=0,outsideDifferences:int=0,acceptedOutside:int=0,rejectedOutside:int=0;
            var left:int=expected.width,top:int=expected.height,right:int=-1,bottom:int=-1;
            var examples:Array=[];
            for(var y:int=0;y<expected.height;++y) {
                for(var x:int=0;x<expected.width;++x) {
                    var expectedValue:uint=expected.getPixel32(x,y),actualValue:uint=actual.getPixel32(x,y);
                    if(expectedValue==actualValue) continue;
                    ++count;
                    var expectedAlpha:int=expectedValue>>>24,actualAlpha:int=actualValue>>>24;
                    if(expectedAlpha!=actualAlpha) ++alphaCount;
                    var colorDifferent:Boolean=(expectedValue&0xFFFFFF)!=(actualValue&0xFFFFFF);
                    if(colorDifferent) ++colorCount;
                    // Keep the integer products: rounding normalized colors
                    // before comparison could silently admit a larger error.
                    var premultipliedR:int=Math.abs(((expectedValue>>>16)&255)*expectedAlpha-((actualValue>>>16)&255)*actualAlpha);
                    var premultipliedG:int=Math.abs(((expectedValue>>>8)&255)*expectedAlpha-((actualValue>>>8)&255)*actualAlpha);
                    var premultipliedB:int=Math.abs((expectedValue&255)*expectedAlpha-(actualValue&255)*actualAlpha);
                    maxPremultipliedR=Math.max(maxPremultipliedR,premultipliedR);
                    maxPremultipliedG=Math.max(maxPremultipliedG,premultipliedG);
                    maxPremultipliedB=Math.max(maxPremultipliedB,premultipliedB);
                    var withinVisibleStep:Boolean=premultipliedR<=255 && premultipliedG<=255 && premultipliedB<=255;
                    if(!withinVisibleStep) ++overPremultipliedTolerance;
                    var localValue:uint=nativeLocal?nativeLocal.getPixel32(x,y):0;
                    var insideAlpha:Boolean=alphaBounds!=null && alphaBounds.contains(worldX+x,worldY+y);
                    if(nativeLocal && colorDifferent && (nativePureDraw==null || insideAlpha)) {
                        if(localValue!=actualValue) ++nativeColorMismatch;
                        if(localValue==actualValue && withinVisibleStep && expectedAlpha==actualAlpha) ++acceptedNativeColor;
                        else ++rejectedNativeColor;
                    }
                    var da:int=Math.abs(expectedAlpha-actualAlpha);
                    var dr:int=Math.abs(((expectedValue>>>16)&255)-((actualValue>>>16)&255));
                    var dg:int=Math.abs(((expectedValue>>>8)&255)-((actualValue>>>8)&255));
                    var db:int=Math.abs((expectedValue&255)-(actualValue&255));
                    var pureValue:uint=nativePureDraw?nativePureDraw.getPixel32(x,y):0;
                    var outsideEquivalent:Boolean=false;
                    if(nativePureDraw) {
                        if(insideAlpha) {
                            ++insideDifferences;
                            if(da!=0) {++insideAlphaCount;++rejectedAlphaCount;}
                        } else {
                            ++outsideDifferences;
                            outsideEquivalent=pureValue==actualValue && da<=8 && dr<=8 && dg<=8 && db<=8;
                            if(outsideEquivalent) ++acceptedOutside;
                            else {
                                ++rejectedOutside;
                                if(da!=0) ++rejectedAlphaCount;
                            }
                        }
                    }
                    maxA=Math.max(maxA,da);maxR=Math.max(maxR,dr);
                    maxG=Math.max(maxG,dg);maxB=Math.max(maxB,db);
                    left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);
                    if(examples.length<12) examples.push({x:x,y:y,worldX:worldX+x,worldY:worldY+y,
                        expected:argbHex(expectedValue),actual:argbHex(actualValue),
                        nativeLocal:nativeLocal?argbHex(localValue):null,nativeLocalMatchesActual:nativeLocal?localValue==actualValue:null,
                        insideNativeAlphaBox:nativePureDraw?insideAlpha:null,
                        pureNativeDraw:nativePureDraw?argbHex(pureValue):null,
                        pureNativeDrawMatchesActual:nativePureDraw?pureValue==actualValue:null,
                        outsideAlphaRasterEquivalent:nativePureDraw && !insideAlpha?outsideEquivalent:null,
                        rawChannelDelta:[da,dr,dg,db],
                        premultipliedProductDelta:[premultipliedR,premultipliedG,premultipliedB]});
                }
            }
            return {count:count,maxAlphaDelta:maxA,maxRedDelta:maxR,maxGreenDelta:maxG,maxBlueDelta:maxB,
                alphaDifferenceCount:alphaCount,colorDifferenceCount:colorCount,
                maxPremultipliedProductRedDelta:maxPremultipliedR,maxPremultipliedProductGreenDelta:maxPremultipliedG,
                maxPremultipliedProductBlueDelta:maxPremultipliedB,premultipliedProductTolerance:255,
                normalizedPremultipliedTolerance:1/255,overPremultipliedToleranceCount:overPremultipliedTolerance,
                nativeLocalColorMismatchCount:nativeLocal?nativeColorMismatch:null,
                acceptedNativeColorDifferenceCount:nativeLocal?acceptedNativeColor:null,
                rejectedNativeColorDifferenceCount:nativeLocal?rejectedNativeColor:null,
                insideAlphaDifferenceCount:nativePureDraw?insideAlphaCount:null,
                rejectedAlphaDifferenceCount:nativePureDraw?rejectedAlphaCount:null,
                insideAlphaBoxDifferenceCount:nativePureDraw?insideDifferences:null,
                outsideAlphaBoxDifferenceCount:nativePureDraw?outsideDifferences:null,
                acceptedOutsideRasterDifferenceCount:nativePureDraw?acceptedOutside:null,
                rejectedOutsideRasterDifferenceCount:nativePureDraw?rejectedOutside:null,
                outsideRawChannelTolerance:8,
                bounds:count?new Rectangle(left,top,right-left+1,bottom-top+1).toString():null,
                examples:examples,exampleLimit:12};
        }

        private static function argbHex(value:uint):String {
            var hex:String=value.toString(16).toUpperCase();
            while(hex.length<8) hex="0"+hex;
            return "0x"+hex;
        }

        /** Diagnose every pixel outside the independently measured world alpha
         * destination. These counters never participate in pass/fail decisions.
         * Keep mismatches against the global oracle even when pure draw agrees
         * exactly, so the evidence distinguishes raster rounding from copying.
         */
        private static function pureDrawDiagnostics(expected:BitmapData,actual:BitmapData,pure:BitmapData,
                                                    worldX:int,worldY:int,alphaBounds:Rectangle):Object {
            var outsidePixels:int=0,actualPureDifferences:int=0,globalDifferencesOutside:int=0;
            var globalDifferencesInside:int=0,globalDifferencesMatchingPure:int=0;
            var maxA:int=0,maxR:int=0,maxG:int=0,maxB:int=0;
            var samples:Array=[];
            for(var y:int=0;y<actual.height;++y) {
                for(var x:int=0;x<actual.width;++x) {
                    var expectedValue:uint=expected.getPixel32(x,y),actualValue:uint=actual.getPixel32(x,y);
                    if(alphaBounds && alphaBounds.contains(worldX+x,worldY+y)) {
                        if(expectedValue!=actualValue) ++globalDifferencesInside;
                        continue;
                    }
                    ++outsidePixels;
                    var pureValue:uint=pure.getPixel32(x,y);
                    if(expectedValue!=actualValue) {
                        ++globalDifferencesOutside;
                        if(actualValue==pureValue) ++globalDifferencesMatchingPure;
                    }
                    if(actualValue!=pureValue) {
                        ++actualPureDifferences;
                        maxA=Math.max(maxA,Math.abs(int(actualValue>>>24)-int(pureValue>>>24)));
                        maxR=Math.max(maxR,Math.abs(int((actualValue>>>16)&255)-int((pureValue>>>16)&255)));
                        maxG=Math.max(maxG,Math.abs(int((actualValue>>>8)&255)-int((pureValue>>>8)&255)));
                        maxB=Math.max(maxB,Math.abs(int(actualValue&255)-int(pureValue&255)));
                    }
                    if((expectedValue!=actualValue || actualValue!=pureValue) && samples.length<12)
                        samples.push({x:x,y:y,worldX:worldX+x,worldY:worldY+y,
                            expectedGlobal:argbHex(expectedValue),actual:argbHex(actualValue),pureNativeDraw:argbHex(pureValue),
                            actualMatchesPureNativeDraw:actualValue==pureValue,
                            globalMatchesPureNativeDraw:expectedValue==pureValue});
                }
            }
            return {diagnosticOnly:true,alphaWorldWriteBounds:alphaBounds?alphaBounds.toString():null,
                outsidePixels:outsidePixels,actualVsPureNativeDrawDifferenceCount:actualPureDifferences,
                maxAlphaDelta:maxA,maxRedDelta:maxR,maxGreenDelta:maxG,maxBlueDelta:maxB,
                globalDifferencePixelsOutsideAlpha:globalDifferencesOutside,
                globalDifferencePixelsInsideAlpha:globalDifferencesInside,
                globalDifferencePixelsExactlyMatchingPureNativeDraw:globalDifferencesMatchingPure,
                samples:samples,exampleLimit:12};
        }

        private static function worldPattern(width:int,height:int,x:int,y:int):BitmapData {
            var data:BitmapData=new BitmapData(width,height,true,0xFFA6B4C2);
            // Original chunk-local x=10/y=20 correspond to world x=50/y=60
            // modulo 80 because each 320px chunk has a 40px leading gutter.
            var stripe:int=int(Math.floor((x-50)/80))*80+50;
            for(;stripe<x+width;stripe+=80) data.fillRect(new Rectangle(stripe-x,0,4,height),0);
            stripe=int(Math.floor((y-60)/80))*80+60;
            for(;stripe<y+height;stripe+=80) data.fillRect(new Rectangle(0,stripe-y,width,3),0x70A6B4C2);
            return data;
        }

        private static function referenceExtent(test:Object):Object {
            var container:Sprite=new Sprite(),union:Rectangle=null,artRects:Array=[];
            var alpha:Rectangle=null,alphaWrite:Rectangle=null;
            for each(var factory:Class in [test.cut,test.paint]) {
                if(!factory) continue;
                var art:MovieClip=new factory();
                if(factory===test.paint) {
                    // The original alpha box uses degrees for these dimensions,
                    // even though the actual BitmapData draw matrix uses radians.
                    art.scaleX=art.scaleY=test.scale;art.rotation=test.angle;
                    var alphaWidth:int=Math.round(art.width/2+2)*2;
                    var alphaHeight:int=Math.round(art.height/2+2)*2;
                    alpha=new Rectangle(test.x-alphaWidth/2,test.y-alphaHeight/2,alphaWidth,alphaHeight);
                    // Native copyChannel destination Point truncates after its
                    // nonnegative clamp. Compute independently of production.
                    alphaWrite=new Rectangle(int(Math.max(test.x-alphaWidth/2,0)),
                        int(Math.max(test.y-alphaHeight/2,0)),alphaWidth,alphaHeight);
                }
                var matrix:Matrix=new Matrix();matrix.scale(test.scale,test.scale);matrix.rotate(test.angle);
                matrix.tx=test.x;matrix.ty=test.y;art.transform.matrix=matrix;
                container.addChild(art);
                var bounds:Rectangle=art.getBounds(container);
                artRects.push(bounds.toString());
                if(!bounds.isEmpty()) union=union?union.union(bounds):bounds.clone();
            }
            if(alpha) union=union?union.union(alpha):alpha.clone();
            if(!union || union.isEmpty() || !isFinite(union.x) || !isFinite(union.y) ||
               !isFinite(union.width) || !isFinite(union.height)) throw new Error("Invalid independent native reference extent");
            // This margin is not a production candidate bound. Real raster output
            // must also remain 64px inside it; a too-small oracle fails explicitly.
            var margin:int=Math.max(320,Math.ceil(Math.abs(Number(test.scale))*32));
            var left:int=Math.floor((union.left-margin)/80)*80;
            var top:int=Math.floor((union.top-margin)/80)*80;
            var right:int=Math.ceil((union.right+margin)/80)*80;
            var bottom:int=Math.ceil((union.bottom+margin)/80)*80;
            return {canvas:new Rectangle(left,top,right-left,bottom-top),geometryAndAlpha:union.clone(),
                art:artRects,alpha:alpha?alpha.toString():null,alphaWriteBounds:alphaWrite};
        }

        /** Independent transcription of unpatched 1.02 Grafon.decal: includes
         * its radians-for-matrix/degrees-for-width behavior and source rectangle
         * arithmetic. No chunk bounds, scene APIs, replay, or production helpers.
         */
        private static function nativeReference(target:BitmapData,cut:Class,paint:Class,x:Number,y:Number,
                                                scale:Number,angle:Number,blend:String,color:ColorTransform,
                                                restoreAlpha:Boolean=true):void {
            var matrix:Matrix=new Matrix();
            if(scale!=1) matrix.scale(scale,scale);
            if(angle!=0) matrix.rotate(angle);
            matrix.tx=x;matrix.ty=y;
            if(cut) {
                var hole:MovieClip=new cut();
                target.draw(hole,matrix,null,"erase",null,true);
            }
            if(paint) {
                var art:MovieClip=new paint();
                art.scaleX=art.scaleY=scale;art.rotation=angle;
                var width:int=Math.round(art.width/2+2)*2;
                var height:int=Math.round(art.height/2+2)*2;
                if(!restoreAlpha) {
                    target.draw(art,matrix,blend=="normal"?color:null,blend,null,true);
                    return;
                }
                var alpha:BitmapData=new BitmapData(width,height,false,0);
                try {
                    var dx:Number=0,dy:Number=0;
                    if(x-width/2<0) dx=-(x-width/2);
                    if(y-height/2<0) dy=-(y-height/2);
                    var area:Rectangle=new Rectangle(x-width/2+dx,y-height/2+dy,x+width/2+dx,y+height/2+dy);
                    alpha.copyChannel(target,area,new Point(),BitmapDataChannel.ALPHA,BitmapDataChannel.GREEN);
                    target.draw(art,matrix,blend=="normal"?color:null,blend,null,true);
                    target.copyChannel(alpha,new Rectangle(0,0,width,height),new Point(x-width/2+dx,y-height/2+dy),
                        BitmapDataChannel.GREEN,BitmapDataChannel.ALPHA);
                } finally {alpha.dispose();}
            }
        }
        private static function add(rows:Array,name:String,ok:Boolean,detail:*=null):void {
            rows.push({name:name,ok:ok,detail:detail});
        }
    }
}
