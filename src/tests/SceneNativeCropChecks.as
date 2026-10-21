package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.PNGEncoderOptions;
    import flash.display.Sprite;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;

    /** Terminal, isolated pixel checks for native full buffers / cropped display.
     * No world step occurs inside this helper. Mutation oracles bind the CURRENT
     * native buffers directly and never call sceneTick to repair a stale crop.
     * Run separately with WB enabled and disabled. This is not a timing run.
     * Private impact history is intentionally retained: exit without saving,
     * travelling or running any later lifecycle fixture.
     */
    public class SceneNativeCropChecks {
        public static function run(w:*,check:Function):Object {
            var app:String=NativeApplication.nativeApplication.applicationID;
            var safe:Boolean=app.indexOf("pfe-modsettings-continuous-motion-")==0;
            check("crop-isolated-storage",safe,app);
            if(!safe)throw new Error("Native crop checks require isolated motion storage");
            var g:*=w.grafon,c:*=w.cam;
            check("crop-host-contract",g.sceneLarge && ("sceneCropPresentation" in g));
            if(!g.sceneLarge || !("sceneCropPresentation" in g))throw new Error("Native crop host required");
            check("crop-host-version",("sceneCropVersion" in g) && g.sceneCropVersion=="native-crop-1");
            w.swfStage.removeEventListener(Event.DEACTIVATE,w.onDeactivate);
            var saved:Object={enabled:g.sceneCropPresentation,vx:c.vx,vy:c.vy,s:c.scaleV,
                sx:c.screenX,sy:c.screenY,qx:c.quakeX,qy:c.quakeY,
                visual:w.visual.transform.matrix.clone(),satsVisual:w.sats.vis.transform.matrix.clone(),
                overlay:g.visSats.visible,actors:g.visObjs[2].visible};
            var result:Object={terminalOnly:true,performanceEligible:false,views:[],mutations:[],sats:[],
                oracle:"same synchronous frame; temporary full native buffer binding with original gutter scrollRect",
                wallblend:wallState(w),history:"Exit without save, travel or another lifecycle fixture."};
            var baseX:Number=Math.max(0,(-c.vx-c.quakeX)/Number(c.scaleV));
            var baseY:Number=Math.max(0,(-c.vy-c.quakeY)/Number(c.scaleV));
            try {
                g.onSats(false);g.sceneCropPresentation=true;
                check("crop-wallblend-setting-known",result.wallblend.enabled is Boolean,result.wallblend);
                if(result.wallblend.enabled===true)check("crop-wallblend-active-layer-coverage",result.wallblend.front+result.wallblend.back>0,result.wallblend);
                // Real camera/display scales, rather than setZoom choices that
                // can all clamp to 1 on a wide test window.
                for each(var scale:Number in [0.5,0.8,1.0]) {
                    for(var offset:int=0;offset<3;++offset) {
                        var left:Number=offset==2?Math.max(0,w.loc.limX-c.screenX/scale):baseX+offset*1550.25;
                        setView(w,left,baseY+(offset==1?320.75:0),scale,offset==1?17.25:0,offset==1?-13.5:0);
                        var tag:String="crop-view-"+scale+"-"+offset;
                        check(tag+"-actual-scale",Number(c.scaleV)==scale && Math.abs(w.visual.scaleX-scale)<0.0001 && Math.abs(w.visual.scaleY-scale)<0.0001,
                            {camera:c.scaleV,displayX:w.visual.scaleX,displayY:w.visual.scaleY});
                        check(tag+"-ready",g.sceneViewReady());
                        result.views.push(compareNow(w,check,tag));
                    }
                }
                setView(w,baseX,baseY,1,0,0);
                // Toggle both ways and check native buffer identity. Old-mode
                // bindings must not leave cropped pixels or stale scrollRects.
                var nativeRefs:Array=[];
                for each(var entry:Object in g.sceneSurfaces())nativeRefs.push({entry:entry,buffers:entry.nativeBuffers.concat()});
                g.sceneCropPresentation=false;g.sceneTick();
                var identity:Boolean=true,oldBinding:Boolean=true;
                for each(var record:Object in nativeRefs)for(var n:int=0;n<4;++n) {
                    if(record.entry.nativeBuffers[n]!==record.buffers[n])identity=false;
                    var raster:Bitmap=record.entry.bitmaps[n];
                    var clip:Rectangle=raster.scrollRect;
                    if(raster.bitmapData!==record.buffers[n] || clip==null || clip.x!=record.entry.gutter || clip.y!=record.entry.gutter || clip.width!=record.entry.side || clip.height!=record.entry.side)oldBinding=false;
                }
                check("crop-switch-off-native-identity",identity);
                check("crop-switch-off-restores-full-bindings",oldBinding);
                g.sceneCropPresentation=true;g.sceneTick();compareNow(w,check,"crop-switch-on");
                var fixture:Object=findFixture(w);
                check("crop-visible-solid-fixture",fixture!=null,fixture);
                if(!fixture)throw new Error("No visible foreground tile for nonempty mutation coverage");
                var x:Number=fixture.x,y:Number=fixture.y;
                result.fixture=fixture;
                result.sats.push(sats(w,check,"crop-sats-before"));
                mutation(w,check,result,"decal",0,function():void {g.decal(null,SceneDecalMetalPaint,x+.25,y+.5,1,0,"normal");});
                mutation(w,check,result,"paint",1,function():void {g.paint(int(x-24),int(y),int(x+24),int(y+24),false);});
                var tile:*=w.loc.getTile(int(x/40),int(y/40));
                var oldWater:Number=tile.water;
                try {
                    tile.water=1;
                    mutation(w,check,result,"water-add",3,function():void {g.drawWater(tile,false);});
                    tile.water=0;
                    mutation(w,check,result,"water-erase",3,function():void {g.drawWater(tile,false);});
                } finally {tile.water=oldWater;}
                mutation(w,check,result,"gwall",0,function():void {g.gwall(tile.X,tile.Y);});
                // This exercises tileDie's rendering hook, not Tile.die's
                // collision/quest/physics lifecycle (covered by other suites).
                mutation(w,check,result,"wall-break-mark",0,function():void {g.tileDie(tile,1);});
                result.hiddenMutation=mutateHidden(w,check);
                result.sats.push(sats(w,check,"crop-sats-after-mutations"));
                result.sats.push(sats(w,check,"crop-sats-repeat"));
                check("crop-terminal-history-only",true,result.history);
                result.copies=("sceneCropCopies" in g)?g.sceneCropCopies:null;
                result.allocations=("sceneCropAllocations" in g)?g.sceneCropAllocations:null;
                result.od=w.sats.od;
            } finally {
                g.onSats(false);g.sceneCropPresentation=saved.enabled;
                c.vx=saved.vx;c.vy=saved.vy;c.scaleV=saved.s;c.screenX=saved.sx;c.screenY=saved.sy;c.quakeX=saved.qx;c.quakeY=saved.qy;
                w.visual.transform.matrix=saved.visual;w.sats.vis.transform.matrix=saved.satsVisual;
                g.sceneTick();g.visSats.visible=saved.overlay;g.visObjs[2].visible=saved.actors;
            }
            return result;
        }

        private static function setView(w:*,left:Number,top:Number,scale:Number,qx:Number,qy:Number):void {
            var c:*=w.cam;
            left=Math.max(0,Math.min(w.loc.limX-c.screenX/scale,left));
            top=Math.max(0,Math.min(w.loc.limY-c.screenY/scale,top));
            c.scaleV=scale;c.vx=-left*scale;c.vy=-top*scale;c.quakeX=qx;c.quakeY=qy;
            w.visual.scaleX=w.visual.scaleY=w.sats.vis.scaleX=w.sats.vis.scaleY=scale;
            w.visual.x=w.sats.vis.x=c.vx+qx;w.visual.y=w.sats.vis.y=c.vy+qy;
            w.grafon.sceneTick();
        }

        private static function wallState(w:*):Object {
            var state:Object={enabled:null,front:0,back:0};
            var carrier:*=w.main.getChildByName("ModSettingsCarrier");
            if(carrier)for each(var page:Object in carrier["modAPI"].getPages())if(page.modId=="wallblend")
                for each(var item:Object in page.items)if(item.key=="enabled")state.enabled=item["get"]();
            for each(var p:Sprite in [w.grafon.visFront,w.grafon.visBack])for(var i:int=0;i<p.numChildren;++i) {
                var b:Bitmap=p.getChildAt(i) as Bitmap;
                if(b && b.name=="WallBlendSceneFront")++state.front;
                if(b && b.name=="WallBlendSceneBack")++state.back;
            }
            return state;
        }

        private static function bindNative(w:*):Array {
            var saved:Array=[];
            try {
                for each(var s:Object in w.grafon.sceneSurfaces())for(var i:int=0;i<4;++i) {
                    var b:Bitmap=s.bitmaps[i];
                    saved.push({bitmap:b,data:b.bitmapData,clip:b.scrollRect,smoothing:b.smoothing,snapping:b.pixelSnapping});
                    var smoothing:Boolean=b.smoothing;
                    var snapping:String=b.pixelSnapping;
                    b.bitmapData=s.nativeBuffers[i];b.scrollRect=new Rectangle(s.gutter,s.gutter,s.side,s.side);
                    b.smoothing=smoothing;b.pixelSnapping=snapping;
                }
            } catch(error:Error) {restoreBinding(saved);throw error;}
            return saved;
        }

        private static function restoreBinding(saved:Array):void {
            for each(var r:Object in saved){r.bitmap.bitmapData=r.data;r.bitmap.scrollRect=r.clip;r.bitmap.smoothing=r.smoothing;r.bitmap.pixelSnapping=r.snapping;}
        }

        private static function capture(w:*):BitmapData {
            var pixels:BitmapData=new BitmapData(w.main.stage.stageWidth,w.main.stage.stageHeight,false,0);
            pixels.draw(w.main.stage);return pixels;
        }

        private static function compareNow(w:*,check:Function,name:String):Object {
            var g:*=w.grafon,visible:int=0,badGeometry:int=0,badPixels:int=0;
            var actual:BitmapData=capture(w),expected:BitmapData=null,delta:*=null,saved:Array=[];
            try {
                for each(var s:Object in g.sceneSurfaces())for(var i:int=0;i<4;++i) {
                    var b:Bitmap=s.bitmaps[i];if(!b.visible)continue;++visible;
                    if(b.bitmapData===s.nativeBuffers[i] || b.scrollRect!=null || b.bitmapData==null || b.bitmapData.width!=s.side || b.bitmapData.height!=s.side || b.x!=s.cx*s.side || b.y!=s.cy*s.side)++badGeometry;
                    if(!b.bitmapData)continue;
                    var central:BitmapData=new BitmapData(s.side,s.side,true,0);
                    try {
                        central.copyPixels(s.nativeBuffers[i],new Rectangle(s.gutter,s.gutter,s.side,s.side),new Point());
                        delta=b.bitmapData.compare(central);if(delta!==0)++badPixels;if(delta is BitmapData)delta.dispose();delta=null;
                    } finally {central.dispose();}
                }
                check(name+"-visible-crop-geometry",visible>0 && badGeometry==0,{visible:visible,bad:badGeometry});
                check(name+"-current-native-centres",visible>0 && badPixels==0,{visible:visible,bad:badPixels});
                // No sceneTick, display update helper or frame advance here.
                saved=bindNative(w);expected=capture(w);restoreBinding(saved);saved=[];
                delta=actual.compare(expected);
                var diagnostic:Object=null;
                if(delta!==0) {
                    diagnostic=failureImages(name,actual,expected,delta);
                    diagnostic.surfaces=surfaceState(w,false);
                    diagnostic.camera={vx:w.cam.vx,vy:w.cam.vy,qx:w.cam.quakeX,qy:w.cam.quakeY,scale:w.cam.scaleV,
                        visual:w.visual.transform.matrix.toString(),visualConcatenated:w.visual.transform.concatenatedMatrix.toString()};
                    diagnostic.variants=clipVariants(w,expected,name,null);
                }
                check(name+"-whole-stage-pixels",delta===0,{zoom:w.cam.scaleV,wallblend:wallState(w),diagnostic:diagnostic});
                return {name:name,zoom:w.cam.scaleV,visible:visible,geometryFailures:badGeometry,pixelFailures:badPixels,wholeStageEqual:delta===0,diagnostic:diagnostic};
            } finally {if(saved.length)restoreBinding(saved);if(delta is BitmapData)delta.dispose();actual.dispose();if(expected)expected.dispose();}
            return null;
        }

        private static function findFixture(w:*):Object {
            var view:Rectangle=w.grafon.sceneViewport();if(!view)return null;
            var left:int=Math.max(1,Math.ceil((view.left+80)/40)),right:int=Math.min(w.loc.spaceX-2,Math.floor((view.right-80)/40));
            var top:int=Math.max(1,Math.ceil((view.top+80)/40)),bottom:int=Math.min(w.loc.spaceY-2,Math.floor((view.bottom-80)/40));
            for(var y:int=bottom;y>=top;--y)for(var x:int=left;x<=right;++x) {
                var tile:*=w.loc.getTile(x,y);
                if(tile && tile.front!="" && tile.phis>0 && !tile.fake && !tile.trap)return {x:x*40+20,y:y*40+20,tileX:x,tileY:y};
            }
            return null;
        }

        private static function mutation(w:*,check:Function,result:Object,name:String,layer:int,act:Function):void {
            var before:Array=[],changed:int=0;
            try {
                for each(var s:Object in w.grafon.sceneSurfaces())if(s.bitmaps[layer].visible)before.push({surface:s,data:s.nativeBuffers[layer].clone()});
                act();
                // This check is immediately after the public drawing call.
                var row:Object=compareNow(w,check,"crop-immediate-"+name);
                for each(var r:Object in before) {
                    var diff:*=r.data.compare(r.surface.nativeBuffers[layer]);if(diff!==0)++changed;if(diff is BitmapData)diff.dispose();
                }
                row.changedNativeSurfaces=changed;row.dirty=w.grafon.sceneLastDirtyCount;
                check("crop-"+name+"-native-dirty",row.dirty>0,row.dirty);
                check("crop-"+name+"-nonempty-native-change",changed>0,changed);
                result.mutations.push(row);
            } finally {for each(var old:Object in before)old.data.dispose();}
        }

        private static function mutateHidden(w:*,check:Function):Object {
            var chosen:Object=null;
            for each(var surface:Object in w.grafon.sceneSurfaces())
                if(!surface.bitmaps[0].visible && surface.cx*surface.side+160<w.loc.limX && surface.cy*surface.side+160<w.loc.limY){chosen=surface;break;}
            check("crop-hidden-dirty-fixture",chosen!=null);
            if(!chosen)throw new Error("Need an offscreen resident surface for SATS freshness coverage");
            var before:BitmapData=chosen.nativeBuffers[0].clone(),diff:*=null;
            try {
                w.grafon.gwall(int((chosen.cx*chosen.side+160)/40),int((chosen.cy*chosen.side+160)/40));
                diff=before.compare(chosen.nativeBuffers[0]);
                check("crop-hidden-native-content-changed",diff!==0,{cx:chosen.cx,cy:chosen.cy});
                check("crop-hidden-mutation-remains-hidden",!chosen.bitmaps[0].visible);
                compareNow(w,check,"crop-immediate-hidden-mutation");
                return {cx:chosen.cx,cy:chosen.cy,nativeChanged:diff!==0};
            } finally {before.dispose();if(diff is BitmapData)diff.dispose();}
            return null;
        }

        private static function sats(w:*,check:Function,name:String):Object {
            var g:*=w.grafon,hidden:Array=[],bindings:Array=[],references:Array=[],visibility:Array=[];
            var changed:int=0,missing:int=0,hiddenCount:int=0,flags:Boolean=true;
            var failures:Array=[];
            g.onSats(false);
            try {
                for each(var s:Object in g.sceneSurfaces())for each(var b:Bitmap in s.bitmaps)visibility.push({bitmap:b,visible:b.visible});
                for each(var p:Sprite in [g.visFront,g.visBack])for(var i:int=0;i<p.numChildren;++i) {
                    b=p.getChildAt(i) as Bitmap;
                    if(b && (b.name=="WallBlendSceneFront" || b.name=="WallBlendSceneBack"))visibility.push({bitmap:b,visible:b.visible});
                }
                bindings=bindNative(w);
                for each(var v:Object in visibility)if(!v.visible){v.bitmap.visible=true;hidden.push(v.bitmap);++hiddenCount;}
                for each(s in g.sceneSurfaces()) {
                    var data:BitmapData=new BitmapData(s.side,s.side,true,0);
                    data.draw(g.visual,new Matrix(1,0,0,1,-s.cx*s.side,-s.cy*s.side));
                    references.push({surface:s,data:data});
                }
                for each(b in hidden)b.visible=false;hidden=[];restoreBinding(bindings);bindings=[];
                // Candidate must synchronise ALL resident crops itself, including
                // hidden/dirty surfaces, before native SATS reveals them.
                g.drawSats();
                for each(var r:Object in references) {
                    if(!r.surface.sats || !r.surface.sats.bitmapData){++missing;continue;}
                    var diff:*=r.data.compare(r.surface.sats.bitmapData);
                    if(diff!==0) {
                        ++changed;
                        if(failures.length<2) {
                            var key:String=name+"-"+r.surface.cx+"-"+r.surface.cy;
                            var detail:Object=failureImages(key,r.surface.sats.bitmapData,r.data,diff);
                            detail.cx=r.surface.cx;detail.cy=r.surface.cy;
                            detail.surfaces=surfaceState(w,true,new Rectangle(r.surface.cx*r.surface.side-r.surface.gutter,r.surface.cy*r.surface.side-r.surface.gutter,r.surface.side+2*r.surface.gutter,r.surface.side+2*r.surface.gutter));
                            // Distinguish a crop error from a draw-time change in
                            // actors/effects: repeat the full-native oracle AFTER
                            // capture, in this same synchronous call. Do not use
                            // this repeat to relax the original equality check.
                            var repeat:BitmapData=nativeSatsRepeat(w,r.surface);
                            try {
                                detail.referenceRepeat=diffStats(repeat,r.data);
                                detail.actualVsReferenceRepeat=diffStats(r.surface.sats.bitmapData,repeat);
                                detail.repeatImage=png(key+"-reference-repeat",repeat);
                            } finally {repeat.dispose();}
                            detail.variants=clipVariants(w,r.data,key,r.surface);
                            failures.push(detail);
                        }
                    }
                    if(diff is BitmapData)diff.dispose();
                }
                for each(v in visibility)if(v.bitmap.visible!==v.visible)flags=false;
                check(name+"-all-resident-pixels",references.length>0 && missing==0 && changed==0,{resident:references.length,missing:missing,changed:changed,failures:failures});
                check(name+"-hidden-coverage",hiddenCount>0,hiddenCount);
                check(name+"-visibility-restored",flags);
                g.onSats(true);check(name+"-native-overlay-and-actors",g.visSats.visible && !g.visObjs[2].visible);
                g.onSats(false);check(name+"-close-restores-actors",!g.visSats.visible && g.visObjs[2].visible);
                return {name:name,resident:references.length,hidden: hiddenCount,missing:missing,changed:changed,failures:failures};
            } finally {
                for each(b in hidden)b.visible=false;if(bindings.length)restoreBinding(bindings);
                for each(var ref:Object in references)ref.data.dispose();g.onSats(false);
            }
            return null;
        }

        private static function png(name:String,data:BitmapData):String {
            var folder:File=File.applicationStorageDirectory.resolvePath("native-crop-diagnostics");folder.createDirectory();
            var file:File=folder.resolvePath(name.replace(/[^A-Za-z0-9_.-]/g,"_")+".png");
            var stream:FileStream=new FileStream();
            try {stream.open(file,FileMode.WRITE);stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));}
            finally {stream.close();}
            return file.nativePath;
        }

        private static function failureImages(name:String,actual:BitmapData,expected:BitmapData,diff:*):Object {
            var result:Object=diffStats(actual,expected,diff);
            result.actual=png(name+"-actual",actual);result.reference=png(name+"-reference",expected);
            result.diff=diff is BitmapData?png(name+"-diff",diff):null;
            return result;
        }

        private static function diffStats(actual:BitmapData,expected:BitmapData,known:*=null):Object {
            var owned:Boolean=known===null,delta:*=owned?actual.compare(expected):known;
            var result:Object={equal:delta===0,count:0,bbox:null,maxDelta:0,maxChannels:{a:0,r:0,g:0,b:0},samples:[]};
            try {
                if(delta===0)return result;
                if(!(delta is BitmapData)){result.compareCode=delta;return result;}
                var bounds:Rectangle=delta.getColorBoundsRect(0xFFFFFFFF,0,false);
                result.bbox={x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height};
                if(bounds.isEmpty())return result;
                var a:Vector.<uint> = actual.getVector(bounds),b:Vector.<uint> = expected.getVector(bounds);
                var channelNames:Array=["b","g","r","a"];
                for(var i:int=0;i<a.length;++i)if(a[i]!==b[i]) {
                    ++result.count;
                    for(var channel:int=0;channel<4;++channel) {
                        var shift:int=channel*8;
                        var amount:int=Math.abs(int((a[i]>>>shift)&255)-int((b[i]>>>shift)&255));
                        result.maxDelta=Math.max(result.maxDelta,amount);
                        result.maxChannels[channelNames[channel]]=Math.max(result.maxChannels[channelNames[channel]],amount);
                    }
                    if(result.samples.length<8)result.samples.push({x:bounds.x+i%int(bounds.width),y:bounds.y+int(i/int(bounds.width)),actual:a[i].toString(16),reference:b[i].toString(16)});
                }
                return result;
            } finally {if(owned && delta is BitmapData)delta.dispose();}
            return result;
        }

        private static function surfaceState(w:*,includeHidden:Boolean,area:Rectangle=null):Array {
            var rows:Array=[];
            for each(var s:Object in w.grafon.sceneSurfaces()) {
                if(area && !area.intersects(new Rectangle(s.cx*s.side,s.cy*s.side,s.side,s.side)))continue;
                for(var layer:int=0;layer<4;++layer) {
                    var b:Bitmap=s.bitmaps[layer];if(!includeHidden && !b.visible)continue;
                    rows.push({cx:s.cx,cy:s.cy,layer:layer,revision:s.revision,visible:b.visible,
                        width:b.bitmapData?b.bitmapData.width:null,height:b.bitmapData?b.bitmapData.height:null,
                        nativeWidth:s.nativeBuffers[layer].width,nativeHeight:s.nativeBuffers[layer].height,
                        nativeIdentity:b.bitmapData===s.nativeBuffers[layer],x:b.x,y:b.y,
                        smoothing:b.smoothing,snapping:b.pixelSnapping,clip:b.scrollRect?b.scrollRect.toString():null,
                        matrix:b.transform.matrix.toString(),concatenated:b.transform.concatenatedMatrix.toString()});
                }
            }
            return rows;
        }

        private static function allVisible(w:*):Array {
            var hidden:Array=[];
            for each(var s:Object in w.grafon.sceneSurfaces())for each(var b:Bitmap in s.bitmaps)
                if(!b.visible){hidden.push(b);b.visible=true;}
            for each(var p:Sprite in [w.grafon.visFront,w.grafon.visBack])for(var i:int=0;i<p.numChildren;++i) {
                b=p.getChildAt(i) as Bitmap;
                if(b && !b.visible && (b.name=="WallBlendSceneFront" || b.name=="WallBlendSceneBack")){hidden.push(b);b.visible=true;}
            }
            return hidden;
        }

        private static function satsCapture(w:*,surface:Object):BitmapData {
            var data:BitmapData=new BitmapData(surface.side,surface.side,true,0);
            data.draw(w.grafon.visual,new Matrix(1,0,0,1,-surface.cx*surface.side,-surface.cy*surface.side));
            return data;
        }

        private static function nativeSatsRepeat(w:*,surface:Object):BitmapData {
            var bindings:Array=[],hidden:Array=[];
            try {bindings=bindNative(w);hidden=allVisible(w);return satsCapture(w,surface);}
            finally {for each(var b:Bitmap in hidden)b.visible=false;if(bindings.length)restoreBinding(bindings);}
            return null;
        }

        /** Diagnostic switches only. Original pixel assertions remain strict. */
        private static function clipVariants(w:*,expected:BitmapData,name:String,surface:Object):Array {
            var changes:Array=[],hidden:Array=[],rows:Array=[];
            var variants:Array=[{clip:false,snap:"auto"},{clip:false,snap:"never"},{clip:false,snap:"always"},
                {clip:true,snap:"auto"},{clip:true,snap:"never"},{clip:true,snap:"always"}];
            try {
                if(surface)hidden=allVisible(w);
                for each(var s:Object in w.grafon.sceneSurfaces())for each(var b:Bitmap in s.bitmaps)
                    if(b.bitmapData && b.bitmapData.width==s.side && b.bitmapData.height==s.side)
                        changes.push({bitmap:b,clip:b.scrollRect,snap:b.pixelSnapping,smoothing:b.smoothing,side:s.side});
                for each(var variant:Object in variants) {
                    for each(var old:Object in changes) {
                        old.bitmap.scrollRect=variant.clip?new Rectangle(0,0,old.side,old.side):null;
                        old.bitmap.pixelSnapping=variant.snap;old.bitmap.smoothing=old.smoothing;
                    }
                    var pixels:BitmapData=surface?satsCapture(w,surface):capture(w);
                    try {
                        var row:Object=diffStats(pixels,expected);
                        row.mode=(variant.clip?"zero-clip":"no-clip")+"-"+variant.snap;
                        row.changedBindings=changes.length;
                        if(row.equal)row.matchImage=png(name+"-variant-"+row.mode,pixels);
                        rows.push(row);
                    } finally {pixels.dispose();}
                }
            } finally {
                for each(old in changes){old.bitmap.scrollRect=old.clip;old.bitmap.pixelSnapping=old.snap;old.bitmap.smoothing=old.smoothing;}
                for each(b in hidden)b.visible=false;
            }
            return rows;
        }
    }
}
