package {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.Sprite;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.Dictionary;
    import flash.utils.getDefinitionByName;
    import flash.utils.getTimer;

    /** Candidate component. Explicit install only; no game/input/store lifecycle. */
    public class SatsVisibleGuard {
        public static var enabled:Boolean=true;
        public static var stats:Object={opens:0,closes:0,clears:0,refreshes:0,captures:0,captureMs:0,attached:0};
        private static var states:Dictionary=new Dictionary(true);
        private static var worldClass:Class;

        public static function install(main:*):void {
            var carrier:*=main.getChildByName("ContinuousSceneCarrier");
            if(!carrier || !carrier["nativeAPI"])throw new Error("SATS guard requires current ContinuousScene nativeAPI");
            worldClass=getDefinitionByName("fe.World") as Class;
            carrier["nativeAPI"]["satsVisibleV3"]=handle;
            carrier["nativeAPI"]["satsVisibleStatsV3"]=stats;
        }

        // 1=open before native onSats(true); 0=after sceneTick has ensured geometry;
        // 2=close after native onSats(false); 3=before native sceneClear.
        // A scene reset cleans even when disabled or already outside a large map.
        // Target selection and all snapshot capture semantics remain native.
        public static function handle(g:*,mode:int):Boolean {
            if(mode==1 || mode==3)ScenePresentationCoordinator.clear(mode==1?"sats-open":"scene-clear");
            if(mode==3){clear(g);stats.clears++;return true;}
            if(mode==2){clear(g);stats.closes++;return true;}
            if(!enabled || !g.sceneLarge)return false;
            var w:*=worldClass["w"];
            var list:Array=g.sceneSurfaces();
            var state:Object=states[g];
            if(mode==1 || state==null || state.loc!==w.loc) {
                clear(g);clearEntries(list);
                // Preserve identity defense for callers replacing a location.
                // sceneClear explicitly releases this back-reference; a weak
                // Dictionary alone would not release value -> loc -> grafon.
                state={loc:w.loc,entries:[]};states[g]=state;stats.opens++;
            } else {stats.refreshes++;}
            var camera:*=w.cam;
            var scale:Number=camera.scaleV>0?camera.scaleV:1;
            var view:Rectangle=new Rectangle((-camera.vx-camera.quakeX)/scale,
                (-camera.vy-camera.quakeY)/scale,camera.screenX/scale,camera.screenY/scale);
            view.inflate(8,8); // Native 4px SATS blur, conservatively in world units.
            var pending:Array=[],needed:Dictionary=new Dictionary(true),entry:Object;
            var captured:Bitmap;
            for each(entry in list) {
                var side:int=int(entry.side);
                if(side!=320 && side!=640)throw new Error("Unexpected native SATS surface side: "+side);
                var area:Rectangle=new Rectangle(entry.cx*side,entry.cy*side,side,side);
                if(!view.intersects(area))continue;
                needed[entry]=true;
                captured=entry.sats as Bitmap;
                if(captured==null)pending.push(entry);
                else if(captured.parent!==g.visSats)g.visSats.addChild(captured);
            }
            // Keep frozen copies for a return pan but do not make the blur layer
            // span all previously explored chunks. No change to live unit roots.
            for each(entry in state.entries) {
                captured=entry.sats as Bitmap;
                if(captured && !needed[entry] && captured.parent===g.visSats)
                    g.visSats.removeChild(captured);
            }
            if(pending.length)capture(w,g,pending,list,state);
            stats.attached=g.visSats.numChildren;
            return true;
        }

        private static function capture(w:*,g:*,pending:Array,list:Array,state:Object):void {
            var hidden:Array=[],actors:Sprite=g.visObjs[2] as Sprite;
            var shown:Boolean=g.visSats.visible,actorsShown:Boolean=actors.visible;
            var data:BitmapData=null,entry:Object,raster:Bitmap;
            var started:int=getTimer();
            g.visSats.visible=false;
            if(shown)actors.visible=true; // Recreate the pre-onSats actor layer for later exposures.
            // Production object culling hides offscreen subtrees behind wrapper
            // visibility; a capture must draw the same full resident tree the
            // native snapshot always drew, then restore the culling state.
            var culling:*=ContinuousSceneMod.objectCulling;
            var cullingSuspended:Boolean=false;
            try {
                if(culling)cullingSuspended=culling.suspendForCapture();
                // Match the existing all-resident source tree exactly. Restrict
                // only the destination cells; do not batch or shift raster origins.
                for each(entry in list)for each(raster in entry.bitmaps)
                    if(!raster.visible){hidden.push(raster);raster.visible=true;}
                for each(var parent:Sprite in [g.visFront,g.visBack])
                    for(var i:int=0;i<parent.numChildren;i++) {
                        raster=parent.getChildAt(i) as Bitmap;
                        if(raster && !raster.visible &&
                           (raster.name=="WallBlendSceneFront" || raster.name=="WallBlendSceneBack")) {
                            hidden.push(raster);raster.visible=true;
                        }
                    }
                for each(entry in pending) {
                    var side:int=int(entry.side);
                    data=new BitmapData(side,side,true,0);
                    data.draw(g.visual,new Matrix(1,0,0,1,-entry.cx*side,-entry.cy*side));
                    var bitmap:Bitmap=new Bitmap(data,"auto",true);
                    bitmap.x=entry.cx*side;bitmap.y=entry.cy*side;
                    g.visSats.addChild(bitmap);entry.sats=bitmap;data=null;
                    state.entries.push(entry);stats.captures++;
                }
            } finally {
                if(cullingSuspended)culling.resumeFromCapture();
                if(data)data.dispose();
                for each(raster in hidden)raster.visible=false;
                actors.visible=actorsShown;g.visSats.visible=shown;
                stats.captureMs+=getTimer()-started;
            }
        }

        private static function clearEntries(entries:Array):void {
            for each(var entry:Object in entries) {
                var bitmap:Bitmap=entry.sats as Bitmap;
                if(bitmap==null)continue;
                if(bitmap.parent)bitmap.parent.removeChild(bitmap);
                if(bitmap.bitmapData) {
                    // Native sceneDrop may already have disposed this surface
                    // during travel/replacement. Do not mask other failures.
                    try {if(bitmap.bitmapData.width>0)bitmap.bitmapData.dispose();}
                    catch(disposed:Error){if(disposed.errorID!=2015)throw disposed;}
                }
                bitmap.bitmapData=null;entry.sats=null;
            }
        }

        public static function clear(g:*):void {
            var state:Object=states[g];
            if(state){clearEntries(state.entries);delete states[g];}
        }
    }
}
