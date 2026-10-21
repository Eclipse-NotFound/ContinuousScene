package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.Sprite;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;

    /** Test-only legacy screenshot oracle, evaluated in the same world/frame. */
    public class SceneSatsChecks {
        private static function png(name:String,data:BitmapData):void {
            var stream:FileStream=new FileStream();
            try {stream.open(File.applicationStorageDirectory.resolvePath(name.split(":").join("-")+".png"),FileMode.WRITE);
                stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));}
            finally {stream.close();}
        }
        private static function view(w:*):Rectangle {
            var c:*=w.cam,s:Number=c.scaleV>0?c.scaleV:1;
            var r:Rectangle=new Rectangle((-c.vx-c.quakeX)/s,(-c.vy-c.quakeY)/s,c.screenX/s,c.screenY/s);
            r.inflate(8,8);return r;
        }
        private static function legacy(w:*,area:Rectangle):Object {
            var g:*=w.grafon,hidden:Array=[],result:Object={pixels:{},ms:0,draws:0};
            var shown:Boolean=g.visSats.visible,actors:Boolean=g.visObjs[2].visible;
            var raster:Bitmap,entry:Object,data:BitmapData;
            g.visSats.visible=false;g.visObjs[2].visible=true;
            var start:int=getTimer();
            try {
                for each(entry in g.sceneSurfaces())for each(raster in entry.bitmaps)
                    if(!raster.visible){hidden.push(raster);raster.visible=true;}
                for each(var p:Sprite in [g.visFront,g.visBack])for(var i:int=0;i<p.numChildren;++i) {
                    raster=p.getChildAt(i) as Bitmap;
                    if(raster && !raster.visible && (raster.name=="WallBlendSceneFront" || raster.name=="WallBlendSceneBack"))
                    {hidden.push(raster);raster.visible=true;}
                }
                for each(entry in g.sceneSurfaces()) {
                    var side:int=entry.side;
                    data=new BitmapData(side,side,true,0);
                    data.draw(g.visual,new Matrix(1,0,0,1,-entry.cx*side,-entry.cy*side));++result.draws;
                    if(area.intersects(new Rectangle(entry.cx*side,entry.cy*side,side,side)))
                        result.pixels[entry.cx+":"+entry.cy]=data;
                    else data.dispose();
                    data=null;
                }
            } finally {
                if(data)data.dispose();for each(raster in hidden)raster.visible=false;
                g.visSats.visible=shown;g.visObjs[2].visible=actors;
            }
            result.ms=getTimer()-start;return result;
        }
        public static function run(w:*,check:Function):Object {
            if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-")!=0)
                throw new Error("SATS checks require isolated storage");
            var g:*=w.grafon,c:*=w.cam,result:Object={cases:[]},frozenReference:Object={};
            check("sats-host-version",("sceneSatsVersion" in g) && g.sceneSatsVersion=="sats-viewport-1");
            var saved:Object={vx:c.vx,vy:c.vy,scale:c.scaleV,width:c.screenX,height:c.screenY,qx:c.quakeX,qy:c.quakeY};
            var offsets:Array=[[0,0,1],[640,-320,1],[1280,320,.75],[640,-320,1],[0,0,1],[320,0,.5],[320,0,1]];
            var maxResident:int=0,maxAttached:int=0,sawOffscreen:Boolean=false;
            try {
                g.onSats(false);
                for(var k:int=0;k<offsets.length;++k) {
                    var before:Object={},entry:Object;
                    for each(entry in g.sceneSurfaces())if(entry.sats)before[entry.cx+":"+entry.cy]=entry.sats.bitmapData;
                    c.scaleV=offsets[k][2];c.screenX=k==6?saved.width+160:saved.width;c.screenY=k==6?saved.height+80:saved.height;
                    var left:Number=Math.max(0,Math.min(w.loc.limX-c.screenX/c.scaleV,-saved.vx/saved.scale+offsets[k][0]));
                    var top:Number=Math.max(0,Math.min(w.loc.limY-c.screenY/c.scaleV,-saved.vy/saved.scale+offsets[k][1]));
                    c.vx=-left*c.scaleV;c.vy=-top*c.scaleV;c.quakeX=k==2?17:0;c.quakeY=k==2?-13:0;
                    // Geometry preparation is outside screenshot timing. Hide only
                    // the overlay so this tick does not pre-capture the new view.
                    var wasShown:Boolean=g.visSats.visible;g.visSats.visible=false;
                    g.sceneTick();
                    g.visSats.visible=wasShown;
                    var ref:Object=legacy(w,view(w));
                    var start:int=getTimer();
                    if(k==0)g.drawSats();else g.sceneTick();
                    var elapsed:int=getTimer()-start,copies:int=0,attached:int=0,compared:int=0,changed:int=0,liveChanged:int=0,newChanged:int=0;
                    var reusable:Boolean=true;
                    for each(entry in g.sceneSurfaces()) {
                        var key:String=entry.cx+":"+entry.cy;
                        if(entry.sats){++copies;if(entry.sats.parent)++attached;}
                        if(before[key] && entry.sats && before[key]!==entry.sats.bitmapData)reusable=false;
                        var liveExpected:BitmapData=ref.pixels[key];if(!liveExpected)continue;
                        // SATS freezes pixels at their first exposure. Preparing
                        // new geometry/effect buffers must not redefine an old
                        // snapshot's oracle to the newly drawn live scene.
                        var expected:BitmapData=frozenReference[key];
                        if(entry.sats) {
                            var liveDelta:*=liveExpected.compare(entry.sats.bitmapData);
                            if(liveDelta!==0){++liveChanged;if(!expected)++newChanged;if(liveDelta is BitmapData)liveDelta.dispose();}
                        }
                        if(!expected){expected=liveExpected;frozenReference[key]=expected;}
                        else liveExpected.dispose();
                        ++compared;
                        if(!entry.sats)++changed;
                        else {
                            var delta:*=expected.compare(entry.sats.bitmapData);
                            if(delta!==0){++changed;if(delta is BitmapData){
                                if(k==0 && changed<=3){png("sats-"+key+"-expected",expected);png("sats-"+key+"-actual",entry.sats.bitmapData);png("sats-"+key+"-diff",delta);}
                                delta.dispose();}}
                        }
                    }
                    check("sats-pixels-"+k,compared>0 && changed==0,{compared:compared,changed:changed});
                    check("sats-frozen-reuse-"+k,reusable);
                    check("sats-actors-restored-"+k,g.visObjs[2].visible==(k==0));
                    maxResident=Math.max(maxResident,g.sceneResident);maxAttached=Math.max(maxAttached,attached);
                    if(g.sceneResident>attached)sawOffscreen=true;
                    result.cases.push({index:k,legacyMs:ref.ms,candidateMs:elapsed,legacyDraws:ref.draws,copies:copies,attached:attached,compared:compared,changed:changed,liveChanged:liveChanged,newChanged:newChanged});
                    g.onSats(true);
                }
                // Reopen after world changes must not reuse stale snapshots.
                g.onSats(false);var cleared:Boolean=true;
                for each(entry in g.sceneSurfaces())if(entry.sats)cleared=false;
                check("sats-close-releases-all-copies",cleared && !g.visSats.visible && g.visObjs[2].visible);
                g.drawSats();g.onSats(true);check("sats-reopen-has-image",g.visSats.numChildren>1);
                g.onSats(false);
                result.maxResident=maxResident;result.maxAttached=maxAttached;
                check("sats-test-explored-beyond-one-view",sawOffscreen,{resident:maxResident,attached:maxAttached});
                // Component-only ABBA, same world/frame after exploring more
                // than one viewport. This is not a frame-rate measurement.
                result.openingTiming=[];
                for each(var approach:String in ["legacy","candidate","candidate","legacy"]) {
                    var openingStart:int=getTimer(),openingMs:int;
                    if(approach=="legacy") {
                        var openingRef:Object=legacy(w,view(w));openingMs=openingRef.ms;
                        for each(var openingData:BitmapData in openingRef.pixels)openingData.dispose();
                    } else {g.drawSats();openingMs=getTimer()-openingStart;g.onSats(false);}
                    result.openingTiming.push({approach:approach,ms:openingMs,resident:g.sceneResident});
                }
            } finally {
                for each(var frozenData:BitmapData in frozenReference)frozenData.dispose();
                g.onSats(false);c.vx=saved.vx;c.vy=saved.vy;c.scaleV=saved.scale;c.screenX=saved.width;c.screenY=saved.height;
                c.quakeX=saved.qx;c.quakeY=saved.qy;g.sceneTick();
            }
            return result;
        }
    }
}
