package tests {
    import flash.geom.Rectangle;
    import flash.utils.getTimer;

    /** Isolated attribution only. Never changes an actor, AI, weapon or projectile. */
    public class SceneCombatCameraHoldProbe {
        public static const VERSION:String="combat-camera-hold-1";
        private var w:*,loc:*,cam:*,player:*,actors:Array,route:Object,api:*;
        private var originalMoved:Boolean,held:Boolean=false,started:Boolean=false,closed:Boolean=false;
        private var heldX:Number,heldY:Number,heldVisualX:Number,heldVisualY:Number;
        private var originalScale:Number,screenX:Number,screenY:Number;
        private var initialCounters:Object,row:Object,index:int=-1;
        private var out:Object={version:VERSION,diagnosticOnly:true,complete:false,incomplete:true,valid:false,
            frames:0,order:[false,true,true,false],windows:[],controlWrites:0,apiWrites:0,
            actorPositionWrites:0,actorVelocityWrites:0,error:null,cleanup:null};

        private static function counters(g:*):Object {
            return {resident:Number(g.sceneResident),warm:Number(g.sceneWarmCount),slices:Number(g.sceneWarmSlices),
                forced:Number(g.sceneWarmForced),misses:Number(g.sceneMisses),redraws:Number(g.sceneRedraws),
                evictions:Number(g.sceneEvictions)};
        }
        private static function restoreView(c:*,g:*,s:Object):void {
            c.vx=s.vx;c.vy=s.vy;c.screenX=s.screenX;c.screenY=s.screenY;
            c.scaleV=s.scaleV;c.quakeX=s.quakeX;c.quakeY=s.quakeY;g.sceneAsyncWarm=s.asyncWarm;
        }
        public static function prepareCache(w:*,route:Object,pre:Object):void {
            var begin:int=getTimer(),g:*=w.grafon,c:*=w.cam,loc:*=w.loc;
            if(!route || !g.sceneLarge || g.scenePreload || c.scaleV!=1 || c.otryv!=0 || c.camRun)
                throw new Error("Camera cache preparation requires the verified large-scene route and ordinary scale1 camera");
            var saved:Object={vx:c.vx,vy:c.vy,screenX:c.screenX,screenY:c.screenY,scaleV:c.scaleV,
                quakeX:c.quakeX,quakeY:c.quakeY,asyncWarm:g.sceneAsyncWarm};
            var p:Object={actor:w.gg,X:w.gg.X,Y:w.gg.Y,dx:w.gg.dx,dy:w.gg.dy,units:loc.units.length};
            var view:Rectangle=g.sceneViewport();
            if(!view)throw new Error("Native viewport unavailable");
            var margin:int=720;
            var l:Number=Math.max(0,Math.floor(Math.min(view.left-margin,route.safeCenterRange.left-c.screenX/2-margin)/320)*320);
            var r:Number=Math.min(loc.limX,Math.ceil(Math.max(view.right+margin,route.safeCenterRange.right+c.screenX/2+margin)/320)*320);
            var t:Number=Math.max(0,Math.floor(Math.min(view.top-margin,route.verifiedBounds.top-c.screenY/2-100-margin)/320)*320);
            var b:Number=Math.min(loc.limY,Math.ceil(Math.max(view.bottom+margin,route.floorY+c.screenY/2-100+margin)/320)*320);
            var keys:Object={},count:int=0;
            for each(var surface:Object in g.sceneSurfaces())keys[surface.cx+":"+surface.cy]=true;
            for(var cx:int=int(l/320);cx<Math.ceil(r/320);++cx)
                for(var cy:int=int(t/320);cy<Math.ceil(b/320);++cy)keys[cx+":"+cy]=true;
            for(var key:String in keys)++count;
            if(count+2>256)throw new Error("Camera preparation exceeds the reviewed 256-resident bound");
            pre.version="combat-camera-prewarm-1";pre.beforeFixtureActors=true;pre.worldStepsCalled=0;
            pre.savedCamera=saved;pre.requested={left:l,right:r,top:t,bottom:b};pre.estimatedResidentUpperBound=count+2;
            pre.before=counters(g);pre.calls=0;pre.drained=false;pre.restored=false;
            try {
                g.sceneAsyncWarm=false;c.vx=-l;c.vy=-t;c.screenX=r-l;c.screenY=b-t;c.quakeX=c.quakeY=0;
                g.sceneTick();++pre.calls;
                restoreView(c,g,saved);g.sceneAsyncWarm=false;
                for(var drain:int=0;drain<64;++drain) {
                    var before:Number=Number(g.sceneWarmSlices);g.sceneTick();++pre.calls;
                    if(Number(g.sceneWarmSlices)==before && g.sceneViewReady()){pre.drained=true;break;}
                }
                if(!pre.drained)throw new Error("Camera preparation did not drain existing warm work");
            } finally {
                restoreView(c,g,saved);
                try {g.sceneTick();++pre.calls;}
                finally {
                    pre.after=counters(g);pre.ms=getTimer()-begin;pre.ready=g.sceneViewReady();
                    pre.restored=c.vx===saved.vx&&c.vy===saved.vy&&c.screenX===saved.screenX&&c.screenY===saved.screenY&&
                        c.scaleV===saved.scaleV&&c.quakeX===saved.quakeX&&c.quakeY===saved.quakeY&&g.sceneAsyncWarm===saved.asyncWarm;
                    pre.actorUnchanged=w.gg===p.actor&&w.gg.X===p.X&&w.gg.Y===p.Y&&w.gg.dx===p.dx&&w.gg.dy===p.dy&&loc.units.length===p.units;
                }
            }
            if(!pre.restored || !pre.actorUnchanged || !pre.ready || g.sceneResident>256)
                throw new Error("Camera preparation failed restoration or unchanged-actor checks");
        }
        private function require(ok:Boolean,message:String):void {
            if(ok)return;
            out.error=message;out.valid=false;out.incomplete=true;
            throw new Error("Combat camera diagnostic: "+message);
        }
        public function start(world:*,units:Array,verifiedRoute:Object):void {
            require(!started,"Duplicate start");
            w=world;loc=w.loc;cam=w.cam;player=w.gg;actors=units.concat();route=verifiedRoute;
            api=w.main.getChildByName("ContinuousSceneCarrier")["nativeAPI"];
            originalMoved=Boolean(cam.moved);originalScale=Number(cam.scaleV);screenX=cam.screenX;screenY=cam.screenY;
            require(originalMoved&&originalScale==1&&actors.length==6&&w.grafon.sceneLarge,"Invalid initial follow/fixture state");
            initialCounters=counters(w.grafon);out.initialCounters=initialCounters;
            out.originalMoved=originalMoved;out.width=screenX;out.height=screenY;out.scale=originalScale;
            out.platform=route.verifiedBounds;started=true;
        }
        public function beginWindow(next:int):void {
            require(started&&!closed&&next==index+1&&next<4,"Window sequence mismatch");
            if(row)require(row.frames.length==300,"Incomplete prior window");
            require(w.cam===cam&&cam.moved===(held?false:originalMoved),"External camera control change");
            var before:Boolean=held;held=next==1||next==2;
            var switchAt:int=getTimer();
            if(before!=held){cam.moved=held?false:originalMoved;++out.controlWrites;}
            if(held&&!before){heldX=cam.vx;heldY=cam.vy;heldVisualX=w.visual.x;heldVisualY=w.visual.y;}
            index=next;row={index:index,held:held,previousHeld:before,switchAtMs:switchAt,switchEndMs:getTimer(),
                frames:[],startCounters:counters(w.grafon),heldX:held?heldX:null,heldY:held?heldY:null};
            out.windows.push(row);
        }
        private function body(u:*):Object {
            return {x:Number(u.X),y:Number(u.Y),dx:Number(u.dx),dy:Number(u.dy),
                left:Number(u.X)-Number(u.scX)/2,right:Number(u.X)+Number(u.scX)/2,
                top:Number(u.Y)-Number(u.scY),bottom:Number(u.Y),stay:Boolean(u.stay),
                levit:Number(u.levit),bound:u.bind!=null};
        }
        private function inside(q:Object,v:Object):Boolean {
            return isFinite(q.left)&&isFinite(q.right)&&isFinite(q.top)&&isFinite(q.bottom)&&
                q.left>=v.left&&q.right<=v.right&&q.top>=v.top&&q.bottom<=v.bottom;
        }
        public function sample(which:int,age:int,at:int,dt:int):void {
            var began:int=getTimer(),f:Object={window:which,index:age,atMs:at,dtMs:dt,held:held,ownMs:0};
            row.frames.push(f);++out.frames;
            try {
                require(which==index&&age==row.frames.length-1&&age<300,"Sample/window mismatch");
                require(w.loc===loc&&w.gg===player&&w.cam===cam&&w.allStat==1&&!w.onPause&&w.t_exit==0,"World identity or active state changed");
                require(cam.moved===(held?false:originalMoved),"Unexpected camera.moved mutation");
                f.camera={vx:Number(cam.vx),vy:Number(cam.vy),X:Number(cam.X),Y:Number(cam.Y),ovy:Number(cam.ovy),
                    moved:Boolean(cam.moved),scale:Number(cam.scaleV),quakeX:Number(cam.quakeX),quakeY:Number(cam.quakeY),
                    visualX:Number(w.visual.x),visualY:Number(w.visual.y),satsX:Number(w.sats.vis.x),satsY:Number(w.sats.vis.y)};
                var s:Number=Number(cam.scaleV);
                f.viewport={left:-Number(w.visual.x)/s,top:-Number(w.visual.y)/s,
                    right:(screenX-Number(w.visual.x))/s,bottom:(screenY-Number(w.visual.y))/s};
                f.player=body(player);f.actors=[];
                for each(var u:* in actors)f.actors.push(body(u));
                f.counters=counters(w.grafon);f.activity=api.activityStats();
                require(s===originalScale&&cam.screenX===screenX&&cam.screenY===screenY&&
                    w.visual.scaleX===s&&w.visual.scaleY===s,"Viewport geometry changed");
                require(w.visual.x===w.sats.vis.x&&w.visual.y===w.sats.vis.y,"Native visual/SATS transform mismatch");
                require(inside(route.verifiedBounds,f.viewport),"Verified fixture platform left viewport");
                require(inside(f.player,f.viewport),"Player collision body left viewport");
                for(var i:int=0;i<actors.length;++i)require(inside(f.actors[i],f.viewport),"Fixture collision body left viewport: "+i);
                if(held)require(cam.vx===heldX&&cam.vy===heldY&&cam.quakeX==0&&cam.quakeY==0&&
                    w.visual.x===heldVisualX&&w.visual.y===heldVisualY,"Held viewport moved/shook; no shake was suppressed");
                for each(var k:String in ["resident","warm","slices","forced","misses","evictions"])
                    require(f.counters[k]===initialCounters[k],"Timed cache counter changed: "+k);
                require(w.grafon.sceneViewReady(),"Native viewport not ready");
                row.endCounters=f.counters;
            } finally {f.ownMs=getTimer()-began;}
        }
        public function clear(success:Boolean):Object {
            if(closed)return out.cleanup;
            closed=true;
            if(started) {
                cam.moved=originalMoved;
                out.cleanup={restored:cam.moved===originalMoved,cameraIdentity:w.cam===cam,
                    originalMoved:originalMoved,finalMoved:Boolean(cam.moved),apiWrites:0,
                    actorPositionWrites:0,actorVelocityWrites:0,obsoleteCoordinatesRestored:false};
            } else out.cleanup={restored:true,started:false,apiWrites:0,actorPositionWrites:0,actorVelocityWrites:0};
            out.complete=success&&started&&out.frames==1200&&out.windows.length==4&&out.error==null;
            for each(var window:Object in out.windows)if(window.frames.length!=300)out.complete=false;
            out.incomplete=!out.complete;out.valid=out.complete&&out.cleanup.restored&&out.cleanup.cameraIdentity;
            return out.cleanup;
        }
        public function snapshot():Object {return out;}
    }
}
