package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.display.PNGEncoderOptions;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.getDefinitionByName;

    /** Terminal pixel diagnostic for the BEFC native surfaces and atlas helper.
     * No World.step, player teleport, input simulation or performance claim here.
     * The driver must send real Ctr.keySats input between the three public calls.
     * Native impact history remains changed: exit without saving or travelling.
     * Run separately with WallBlend on and off. Pixel equality is always exact.
     */
    public class SceneAtlasChecks {
        private static const NAMES:Array=["ContinuousSceneAtlasFront","ContinuousSceneAtlasBack","ContinuousSceneAtlasBack2","ContinuousSceneAtlasWater"];
        private static var imageSets:int=0;

        public static function run(w:*,present:*,check:Function):Object {
            isolated(check);imageSets=0;
            var g:*=w.grafon,c:*=w.cam,saved:Object=saveView(w);
            if(!g.sceneLarge || w.sats.active || !g.sceneSurfaces().length)
                throw new Error("Atlas checks need an active large scene outside SATS");
            w.swfStage.removeEventListener(Event.DEACTIVATE,w.onDeactivate);
            var result:Object={terminalOnly:true,performanceEligible:false,views:[],mutations:[],sats:[],
                oracle:"same synchronous frame; restore original native bitmap visibility only",
                history:"Exit without saving, travelling or another lifecycle fixture.",wallblend:wallState(w)};
            var baseX:Number=Math.max(0,-Number(c.vx)/Number(c.scaleV));
            var baseY:Number=Math.max(0,-Number(c.vy)/Number(c.scaleV));
            var side:int=int(g.sceneSurfaces()[0].side);
            try {
                check("atlas-wallblend-setting-known",result.wallblend.enabled is Boolean,result.wallblend);
                if(result.wallblend.enabled===true)check("atlas-wallblend-layer-coverage",result.wallblend.count>0,result.wallblend);
                for each(var scale:Number in [0.5,0.8,1.0]) {
                    var moves:Array=[[0,0,0,0],[side-.25,0,0,0],[side+.25,0,17.25,-13.5],
                        [1550.25,320.75,17.25,-13.5],[0,0,0,0]];
                    for(var i:int=0;i<moves.length;++i) {
                        var move:Array=moves[i],tag:String="atlas-view-"+scale+"-"+i;
                        setView(w,present,baseX+move[0],baseY+move[1],scale,move[2],move[3]);
                        check(tag+"-actual-transform",Number(c.scaleV)==scale && Math.abs(w.visual.scaleX-scale)<.00001 &&
                            Math.abs(w.visual.scaleY-scale)<.00001 && Math.abs(w.sats.vis.scaleX-scale)<.00001 &&
                            Math.abs(w.visual.x-(c.vx+move[2]))<.00001 && Math.abs(w.visual.y-(c.vy+move[3]))<.00001 &&
                            c.quakeX==move[2] && c.quakeY==move[3],camera(w));
                        check(tag+"-ready",g.sceneViewReady());
                        result.views.push(compareNow(w,present,check,tag));
                    }
                }
                setView(w,present,baseX,baseY,1,0,0);
                result.sats.push(componentSats(w,present,check,"atlas-component-sats-before"));
                var fixture:Object=findFixture(w,false);
                check("atlas-visible-impact-fixture",fixture!=null,fixture);
                if(!fixture)throw new Error("No visible native solid wall for a nonempty impact check");
                result.impact=fixture;
                var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class;
                // Detached native bullet: terrain branch is genuine, but it is
                // deliberately not counted as player fire or combat performance.
                var bullet:*=new Bullet(w.gg,fixture.x-1,fixture.y,null,false);
                bullet.dx=1;bullet.dy=0;bullet.vel=1;bullet.damage=0;bullet.destroy=0;
                bullet.damageExpl=0;bullet.explRadius=0;bullet.tipDecal=1;bullet.partEmit=false;bullet.off=true;
                mutation(w,present,check,result,"native-bullet-impact",function():void {bullet.run();});
                check("atlas-native-bullet-hit",bullet.tilehit && bullet.babah,
                    {tilehit:bullet.tilehit,babah:bullet.babah,detached:true,unitCollisionSkipped:true});
                fixture=findFixture(w,true);
                check("atlas-visible-breakable-fixture",fixture!=null,fixture);
                if(!fixture)throw new Error("No visible natively destructible wall; coverage must not silently degrade");
                result.breakWall=fixture;
                var tile:*=w.loc.getTile(fixture.tileX,fixture.tileY);
                var damage:Number=Math.max(Number(tile.hp),Number(tile.thre))+1;
                mutation(w,present,check,result,"native-wall-break",function():void {
                    w.loc.hitTile(tile,damage,fixture.x,fixture.y,1);
                });
                check("atlas-native-wall-broken",tile.phis==0,{phis:tile.phis,hp:tile.hp,damage:damage});
                result.sats.push(componentSats(w,present,check,"atlas-component-sats-after"));
                result.copies=present.copies;result.rebuilds=present.rebuilds;result.od=w.sats.od;
                check("atlas-terminal-history-only",true,result.history);
            } finally {
                present.beginFrame();restoreView(w,saved);g.sceneTick();present.update(w,true);
            }
            return result;
        }

        /** Called AFTER a normal World frame has consumed keySats=true. */
        public static function onSatsOpened(w:*,present:*,check:Function):Object {
            isolated(check);
            var state:Object={active:w.sats.active,ui:w.sats.vis.visible,overlay:w.grafon.visSats.visible,allStat:w.allStat};
            check("atlas-real-v-open",state.active && state.ui && state.overlay && state.allStat==2,state);
            check("atlas-real-v-atlas-hidden-before-helper",visibleAtlases(w)==0,visibleAtlases(w));
            // Checking existing native snapshots does not replace the real V
            // capture with a new drawSats call, nor advance animation or AI.
            var result:Object=checkSatsPixels(w,present,check,"atlas-real-v-snapshots",false);
            present.update(w,true);
            check("atlas-real-v-stays-native",visibleAtlases(w)==0);
            result.path="native-sats";result.state=state;return result;
        }

        /** Called AFTER a second normal World frame has consumed keySats=true. */
        public static function onSatsClosed(w:*,present:*,check:Function):Object {
            isolated(check);
            check("atlas-real-v-close",!w.sats.active && !w.grafon.visSats.visible && w.grafon.visObjs[2].visible && w.allStat==1);
            var saved:Object=saveView(w),c:*=w.cam,side:int=int(w.grafon.sceneSurfaces()[0].side);
            var left:Number=-Number(c.vx)/Number(c.scaleV),top:Number=-Number(c.vy)/Number(c.scaleV);
            var result:Object={views:[],movement:"synchronous camera cross-chunk and return; ordinary player-input continuation is external"};
            try {
                result.views.push(compareNow(w,present,check,"atlas-real-v-restored"));
                setView(w,present,left+side+.25,top+.5,saved.s,17.25,-13.5);
                result.views.push(compareNow(w,present,check,"atlas-real-v-move"));
                setView(w,present,left,top,saved.s,saved.qx,saved.qy);
                result.views.push(compareNow(w,present,check,"atlas-real-v-return"));
            } finally {present.beginFrame();restoreView(w,saved);w.grafon.sceneTick();present.update(w,true);}
            return result;
        }

        private static function isolated(check:Function):void {
            var app:String=NativeApplication.nativeApplication.applicationID;
            var prefix:String="pfe-modsettings-continuous-motion-";
            var safe:Boolean=app.indexOf(prefix)==0 && app.length>prefix.length+7;
            check("atlas-isolated-storage",safe,app);
            if(!safe)throw new Error("Atlas checks require unique isolated motion storage");
        }

        private static function saveView(w:*):Object {
            var c:*=w.cam;
            return {vx:c.vx,vy:c.vy,s:c.scaleV,qx:c.quakeX,qy:c.quakeY,
                visual:w.visual.transform.matrix.clone(),satsVisual:w.sats.vis.transform.matrix.clone(),
                overlay:w.grafon.visSats.visible,actors:w.grafon.visObjs[2].visible};
        }
        private static function restoreView(w:*,old:Object):void {
            var c:*=w.cam;c.vx=old.vx;c.vy=old.vy;c.scaleV=old.s;c.quakeX=old.qx;c.quakeY=old.qy;
            w.visual.transform.matrix=old.visual;w.sats.vis.transform.matrix=old.satsVisual;
            w.grafon.visSats.visible=old.overlay;w.grafon.visObjs[2].visible=old.actors;
        }
        private static function setView(w:*,present:*,left:Number,top:Number,scale:Number,qx:Number,qy:Number):void {
            present.beginFrame();var c:*=w.cam;
            left=Math.max(0,Math.min(w.loc.limX-c.screenX/scale,left));
            top=Math.max(0,Math.min(w.loc.limY-c.screenY/scale,top));
            c.scaleV=scale;c.vx=-left*scale;c.vy=-top*scale;c.quakeX=qx;c.quakeY=qy;
            w.visual.scaleX=w.visual.scaleY=w.sats.vis.scaleX=w.sats.vis.scaleY=scale;
            w.visual.x=w.sats.vis.x=c.vx+qx;w.visual.y=w.sats.vis.y=c.vy+qy;
            w.grafon.sceneTick();
        }
        private static function camera(w:*):Object {
            return {scale:w.cam.scaleV,vx:w.cam.vx,vy:w.cam.vy,qx:w.cam.quakeX,qy:w.cam.quakeY,
                visual:w.visual.transform.matrix.toString(),satsVisual:w.sats.vis.transform.matrix.toString(),
                concatenated:w.visual.transform.concatenatedMatrix.toString()};
        }
        private static function parents(w:*):Array {var g:*=w.grafon;return [g.visFront,g.visBack,g.visBack2,g.visVoda];}
        private static function visibleAtlases(w:*):int {
            var count:int=0,ps:Array=parents(w);
            for(var i:int=0;i<4;++i){var b:Bitmap=ps[i].getChildByName(NAMES[i]) as Bitmap;if(b && b.visible)++count;}
            return count;
        }
        private static function wallState(w:*):Object {
            var row:Object={enabled:null,count:0},carrier:*=w.main.getChildByName("ModSettingsCarrier");
            if(carrier)for each(var page:Object in carrier["modAPI"].getPages())if(page.modId=="wallblend")
                for each(var item:Object in page.items)if(item.key=="enabled")row.enabled=item["get"]();
            for each(var p:DisplayObjectContainer in parents(w))for(var i:int=0;i<p.numChildren;++i)
                if(p.getChildAt(i).name=="WallBlendSceneFront" || p.getChildAt(i).name=="WallBlendSceneBack")++row.count;
            return row;
        }
        private static function bindings(w:*):Array {
            var refs:Array=[];
            for each(var s:Object in w.grafon.sceneSurfaces())for(var i:int=0;i<4;++i) {
                var b:Bitmap=s.bitmaps[i];refs.push({surface:s,index:i,b:b,data:b.bitmapData,native:s.nativeBuffers[i],
                    clip:b.scrollRect?b.scrollRect.toString():null,snap:b.pixelSnapping,smooth:b.smoothing,x:b.x,y:b.y,visible:b.visible});
            }
            return refs;
        }
        private static function checkBindings(refs:Array):Boolean {
            for each(var r:Object in refs)if(r.b.bitmapData!==r.data || r.surface.nativeBuffers[r.index]!==r.native ||
                r.data!==r.native || (r.b.scrollRect?r.b.scrollRect.toString():null)!==r.clip ||
                r.b.pixelSnapping!==r.snap || r.b.smoothing!==r.smooth || r.b.x!=r.x || r.b.y!=r.y || r.b.visible!==r.visible)return false;
            return true;
        }
        private static function placement(w:*):Object {
            var ps:Array=parents(w),ss:Array=w.grafon.sceneSurfaces(),row:Object={layers:0,bad:0,wallblend:0,side:w.grafon.sceneChunkSide};
            for(var i:int=0;i<4;++i) {
                var p:DisplayObjectContainer=ps[i],atlas:Bitmap=p.getChildByName(NAMES[i]) as Bitmap;
                if(!atlas){++row.bad;continue;}++row.layers;
                var depth:int=p.getChildIndex(atlas),first:int=p.numChildren;
                for each(var s:Object in ss) {
                    var b:Bitmap=s.bitmaps[i];first=Math.min(first,p.getChildIndex(b));
                    if(int(s.side)!=int(row.side) || (s.side!=320 && s.side!=640) || s.x+s.gutter!=s.cx*s.side || s.y+s.gutter!=s.cy*s.side)++row.bad;
                }
                if(depth!=first-1 || !atlas.visible || !atlas.bitmapData || atlas.scrollRect!=null)++row.bad;
                for(var j:int=0;j<p.numChildren;++j)if(p.getChildAt(j).name=="WallBlendSceneFront" || p.getChildAt(j).name=="WallBlendSceneBack") {
                    ++row.wallblend;if(j<=depth)++row.bad;
                }
            }
            return row;
        }
        private static function capture(w:*):BitmapData {
            var data:BitmapData=new BitmapData(w.main.stage.stageWidth,w.main.stage.stageHeight,false,0);
            data.draw(w.main.stage);return data;
        }
        private static function compareNow(w:*,present:*,check:Function,name:String):Object {
            // Restoring visibility before taking references is preparation only;
            // it never rebuilds native pixels or repairs atlas revision tracking.
            present.beginFrame();var refs:Array=bindings(w),actual:BitmapData=null,expected:BitmapData=null,delta:*=null;
            var result:Object={name:name,path:"atlas",camera:camera(w)};
            try {
                present.update(w,true);result.placement=placement(w);
                check(name+"-native-depth-and-wb",result.placement.layers==4 && result.placement.bad==0,result.placement);
                actual=capture(w);present.beginFrame();
                check(name+"-native-bindings-restored",checkBindings(refs));
                expected=capture(w);delta=actual.compare(expected);result.equal=delta===0;
                if(!result.equal)result.diagnostic=failure(name,actual,expected,delta);
                check(name+"-pixels",result.equal,result);
            } finally {if(delta is BitmapData)delta.dispose();if(actual)actual.dispose();if(expected)expected.dispose();present.update(w,true);}
            return result;
        }
        private static function findFixture(w:*,breakable:Boolean):Object {
            var c:*=w.cam,view:Rectangle=new Rectangle((-c.vx-c.quakeX)/c.scaleV,(-c.vy-c.quakeY)/c.scaleV,c.screenX/c.scaleV,c.screenY/c.scaleV);
            var left:int=Math.max(1,Math.ceil((view.left+80)/40)),right:int=Math.min(w.loc.spaceX-2,Math.floor((view.right-80)/40));
            var top:int=Math.max(1,Math.ceil((view.top+80)/40)),bottom:int=Math.min(w.loc.spaceY-2,Math.floor((view.bottom-80)/40));
            for(var y:int=bottom;y>=top;--y)for(var x:int=left;x<=right;++x) {
                var t:*=w.loc.getTile(x,y),px:Number=x*40+20,py:Number=y*40+20;
                if(!t || t.phis!=1 || t.fake || t.trap || t.door || t.front=="" || t.water>0 || t.mat<1 || t.mat>6 || t.mat==5 || !(t.hp>0) ||
                    px<t.phX1 || px>t.phX2 || py<t.phY1 || py>t.phY2)continue;
                if(breakable && (t.indestruct || !(t.hp>0) || !isFinite(t.hp) || !isFinite(t.thre) || (!w.loc.destroyOn && t.hp>500)))continue;
                return {x:px,y:py,tileX:x,tileY:y,material:t.mat,hp:t.hp,threshold:t.thre};
            }
            return null;
        }
        private static function mutation(w:*,present:*,check:Function,result:Object,name:String,act:Function):void {
            present.beginFrame();var before:Array=[],changed:int=0;
            try {
                for each(var s:Object in w.grafon.sceneSurfaces())if(s.bitmaps[0].visible)before.push({s:s,data:s.nativeBuffers[0].clone()});
                act();var dirty:int=w.grafon.sceneLastDirtyCount;
                // No sceneTick or frame advance between the native mutation and
                // this atlas/native comparison: stale atlas copies must fail.
                var row:Object=compareNow(w,present,check,"atlas-immediate-"+name);
                for each(var r:Object in before) {
                    var diff:*=r.data.compare(r.s.nativeBuffers[0]);if(diff!==0)++changed;if(diff is BitmapData)diff.dispose();
                }
                row.changedNativeSurfaces=changed;row.dirty=dirty;result.mutations.push(row);
                check("atlas-"+name+"-nonempty-native-change",changed>0 && dirty>0,{changed:changed,dirty:dirty});
            } finally {for each(var old:Object in before)old.data.dispose();}
        }

        private static function allVisible(w:*):Array {
            var hidden:Array=[];
            for each(var s:Object in w.grafon.sceneSurfaces())for each(var b:Bitmap in s.bitmaps)if(!b.visible){hidden.push(b);b.visible=true;}
            for each(var p:DisplayObjectContainer in parents(w))for(var i:int=0;i<p.numChildren;++i) {
                b=p.getChildAt(i) as Bitmap;
                if(b && !b.visible && (b.name=="WallBlendSceneFront" || b.name=="WallBlendSceneBack")){hidden.push(b);b.visible=true;}
            }
            return hidden;
        }
        private static function chunkCapture(w:*,s:Object):BitmapData {
            var data:BitmapData=new BitmapData(s.side,s.side,true,0);
            data.draw(w.grafon.visual,new Matrix(1,0,0,1,-s.cx*s.side,-s.cy*s.side));return data;
        }
        private static function checkSatsPixels(w:*,present:*,check:Function,name:String,requireAll:Boolean):Object {
            present.beginFrame();var g:*=w.grafon,hidden:Array=[],shown:Boolean=g.visSats.visible,actors:Boolean=g.visObjs[2].visible;
            var result:Object={name:name,compared:0,missing:0,changed:0,diagnostics:[]},expected:BitmapData=null,delta:*=null;
            try {
                g.visSats.visible=false;g.visObjs[2].visible=true;hidden=allVisible(w);
                for each(var s:Object in g.sceneSurfaces()) {
                    if(!s.sats || !s.sats.bitmapData){++result.missing;continue;}
                    expected=chunkCapture(w,s);++result.compared;delta=s.sats.bitmapData.compare(expected);
                    if(delta!==0){++result.changed;if(result.diagnostics.length<3)result.diagnostics.push(failure(name+"-"+s.cx+"-"+s.cy,s.sats.bitmapData,expected,delta));}
                    if(delta is BitmapData)delta.dispose();delta=null;expected.dispose();expected=null;
                }
                check(name+"-native-snapshot-pixels",result.compared>0 && result.changed==0 && (!requireAll || result.missing==0),result);
            } finally {
                if(delta is BitmapData)delta.dispose();if(expected)expected.dispose();
                for each(var b:Bitmap in hidden)b.visible=false;
                g.visSats.visible=shown;g.visObjs[2].visible=actors;
            }
            return result;
        }
        private static function componentSats(w:*,present:*,check:Function,name:String):Object {
            present.beginFrame();var g:*=w.grafon,refs:Array=bindings(w),result:Object;
            try {
                g.drawSats();result=checkSatsPixels(w,present,check,name,true);
                check(name+"-native-visibility-restored",checkBindings(refs));
                g.onSats(true);present.update(w,true);
                check(name+"-overlay-uses-native",g.visSats.visible && visibleAtlases(w)==0);
                result.path="component-only-native-sats";
            } finally {g.onSats(false);present.update(w,true);}
            compareNow(w,present,check,name+"-restore");return result;
        }
        private static function failure(name:String,actual:BitmapData,expected:BitmapData,delta:*):Object {
            var row:Object={equal:false,count:0,maxDelta:0,samples:[]};
            if(!(delta is BitmapData)){row.compareCode=delta;return row;}
            var rect:Rectangle=delta.getColorBoundsRect(0xFFFFFFFF,0,false);
            row.bounds={x:rect.x,y:rect.y,width:rect.width,height:rect.height};
            var a:Vector.<uint>=actual.getVector(rect),b:Vector.<uint>=expected.getVector(rect);
            for(var i:int=0;i<a.length;++i)if(a[i]!==b[i]) {
                ++row.count;
                for(var shift:int=0;shift<32;shift+=8)row.maxDelta=Math.max(row.maxDelta,Math.abs(int((a[i]>>>shift)&255)-int((b[i]>>>shift)&255)));
                if(row.samples.length<6)row.samples.push({x:rect.x+i%int(rect.width),y:rect.y+int(i/int(rect.width)),actual:a[i].toString(16),native:b[i].toString(16)});
            }
            if(imageSets<6){++imageSets;row.actual=png(name+"-actual",actual);row.reference=png(name+"-native",expected);row.diff=png(name+"-diff",delta);}
            return row;
        }
        private static function png(name:String,data:BitmapData):String {
            var folder:File=File.applicationStorageDirectory.resolvePath("atlas-diagnostics");folder.createDirectory();
            var file:File=folder.resolvePath(name.replace(/[^A-Za-z0-9_.-]/g,"_")+".png"),stream:FileStream=new FileStream();
            try {stream.open(file,FileMode.WRITE);stream.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));}
            finally {stream.close();}return file.nativePath;
        }
    }
}
