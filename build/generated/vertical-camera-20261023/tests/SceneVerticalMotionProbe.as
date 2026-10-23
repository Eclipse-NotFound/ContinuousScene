// Frozen parent vertical-motion source SHA256 1EF84F431C1669F6F02C50ECB215AC6F1BD96354E832599AC37E75846C8C2761
package tests {
    import flash.system.System;
    import flash.utils.getTimer;

    /** Isolated native-input diagnosis. No position/velocity or terrain writes. */
    public class SceneVerticalMotionProbe {
        public static const VERSION:String="vertical-camera-1";
        private const ORDER:Array=["still","jump","jump","jump","jump","still"];
        private const KEYS:Array=["sceneResident","sceneWarmCount","sceneWarmSlices","sceneWarmForced","sceneRedraws","sceneMisses","sceneEvictions"];
        private var w:*,loc:*,player:*,route:Object,out:Object,row:Object;
        private var epoch:int=0,index:int=0,age:int=0,serial:int=0,groundRun:int=0,quiet:int=0;
        private var stage:String="calibrate",lastKey:String="",previous:int,priorHead:int=0;
        private var direction:int=1,hold:int=0,cycle:Object=null,anchor:Number;
        private var wantGrowth:Boolean,ended:Boolean=false,large:Boolean;
        private var camera:*,originalCamMoved:Boolean,cameraHeld:Boolean=false;
        private var cameraRestores:int=0;

        public function start(world:*,verifiedRoute:Object,grow:Boolean):Object {
            w=world;loc=w.loc;player=w.gg;route=verifiedRoute;large=Boolean(w.grafon.sceneLarge);wantGrowth=grow&&large;
            anchor=(Number(route.playerX)+Number(route.endX))/2;
            out={version:VERSION,diagnosticOnly:true,performanceAcceptance:false,valid:false,complete:false,error:null,
                order:ORDER.concat(),windowFrames:120,growthRequested:grow,windows:[],timeline:[],jumps:[],
                route:route,initialUnits:loc.units.length,forcedPositionCalls:0,fixtureActorsAdded:0,playerFireRequested:false,
                sceneMarks:{available:false,reason:"Grafon.sceneMarks is private; revision is not a marks count"},
                sceneLarge:large,setup:{startedAtMs:getTimer()},growth:null,cleanup:null,
                headroom:{verifiedClearance:route.floorY-route.verifiedBounds.top,playerHeight:Number(player.scY),
                    guaranteedVerticalTravel:route.floorY-route.verifiedBounds.top-Number(player.scY),
                    limitation:"Clearance is a minimum, not a measured ceiling. Jumps may hit an original ceiling; actual height/rise/fall/landing are required."},
                limitations:["One initial spawn is performed by the enclosing fixture; all later motion is native input.",
                    "God mode/invulnerability are inherited; natural actors and their AI remain present.",
                    "The initial resident set is naturally warmed by walking/jumping, not forced to a fixed size.",
                    "Only camera.moved is held false in windows 2/3; native jump and actor display remain active.",
                    "Camera-related attribution only; no production or near-native performance acceptance.",
                    "Mode windows and intervening native settling/preparation are retained separately in timeline."]};
            camera=w.cam;originalCamMoved=Boolean(camera.moved);
            out.cameraControl={originalMoved:originalCamMoved,holdWindows:[2,3],followWindows:[1,4],restores:[]};
            require(large&&!grow,"Camera diagnosis requires a scene without resident growth");
            require(originalCamMoved,"Camera.moved was already false; follow/hold contrast is unavailable");
            require(w.cam.scaleV==1,"Scale1 scene required");
            if(grow&&!large)out.growth={applied:false,reason:"Native room has no continuous resident cache"};
            neutral();previous=getTimer();out.timelineStartedAtMs=previous;return out;
        }
        private function require(ok:Boolean,message:String):void {
            if(ok)return;out.error=message;throw new Error(message);
        }
        private function counters():Object {
            var result:Object={available:large};
            for each(var key:String in KEYS){var value:Number=large?Number(w.grafon[key]):0;require(isFinite(value),"Missing "+key);result[key]=value;}
            return result;
        }
        private function signature(value:Object):String {
            return [value.sceneResident,value.sceneWarmCount,value.sceneWarmSlices,value.sceneWarmForced,value.sceneRedraws,value.sceneMisses,value.sceneEvictions].join(":");
        }
        private function memory():Object {
            var result:Object={totalMemoryBytes:System.totalMemoryNumber,privateMemoryBytes:null};
            try {var sys:*=System;var value:Number=Number(sys["privateMemory"]);if(isFinite(value)&&value>0)result.privateMemoryBytes=value;}catch(ignored:Error){}
            return result;
        }
        private function surfaces():Object {
            if(!large)return {available:false,count:0,revisionSum:null,maximumRevision:null};
            var list:Array=w.grafon.sceneSurfaces(),sum:Number=0,max:Number=0;
            for each(var surface:Object in list){sum+=Number(surface.revision);max=Math.max(max,Number(surface.revision));}
            return {available:true,count:list.length,revisionSum:sum,maximumRevision:max,meaning:"All layers; not exact front writes or mark count"};
        }
        private function activity():Object {
            return w.main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].activityStats();
        }
        private function pose():Object {
            var u:*=player,c:*=w.ctr;
            require(w.gg===player&&w.loc===loc&&w.cam===camera,"Actor/location/camera changed");
            require(camera.moved===(cameraHeld?false:originalCamMoved),"External camera.moved change");
            require(w.allStat==1&&!w.onPause&&w.t_exit==0&&u.ggControl,"Native simulation inactive");
            require(isFinite(u.X)&&isFinite(u.Y)&&isFinite(u.dx)&&isFinite(u.dy),"Nonfinite native motion");
            require(u.X>=route.safeCenterRange.left&&u.X<=route.safeCenterRange.right,"Player left verified platform; no reset");
            var contact:Boolean=u.stay&&Math.abs(u.Y-route.floorY)<.01&&Math.abs(u.dy)<.01;
            return {x:u.X,y:u.Y,dx:u.dx,dy:u.dy,stay:Boolean(u.stay),floorContact:contact,
                cameraX:w.cam.vx,cameraY:w.cam.vy,quakeX:w.cam.quakeX,quakeY:w.cam.quakeY,
                cameraHeld:cameraHeld,cameraMoved:Boolean(camera.moved),originalCamMoved:originalCamMoved,
                left:Boolean(c.keyLeft),right:Boolean(c.keyRight),jump:Boolean(c.keyJump),run:Boolean(c.keyRun),attack:Boolean(c.keyAttack),
                jumpNumb:u.jumpNumb,levit:u.levit,isFly:Boolean(u.isFly)};
        }
        private function observeJump(p:Object):void {
            if(!cycle)return;
            cycle.minimumY=Math.min(Number(cycle.minimumY),Number(p.y));
            if(p.y<route.floorY-1&&p.dy<-.1)cycle.rose=true;
            if(cycle.rose&&p.dy>.1)cycle.fell=true;
            if(cycle.rose&&p.floorContact) {
                cycle.landed=true;cycle.endFrame=serial;cycle.endEpoch=epoch;cycle.endWindow=stage=="sample"?index:-1;
                cycle.height=route.floorY-Number(cycle.minimumY);out.jumps.push(cycle);cycle=null;hold=0;
            } else require(serial-int(cycle.startFrame)<180,"Native jump did not complete within 180 frames");
        }
        private function neutral():void {w.ctr.clearAll();}
        private function controls(mode:String,p:Object):void {
            neutral();var c:*=w.ctr;
            if(mode=="walk") {
                if(player.X>=route.endX)direction=-1;else if(player.X<=route.playerX)direction=1;
                c.keyLeft=direction<0;c.keyRight=direction>0;
            } else if(mode=="center") {
                c.keyLeft=player.X>anchor+8;c.keyRight=player.X<anchor-8;
            }
            if(mode=="jump"&&cycle==null&&groundRun>=2) {
                cycle={startFrame:serial,startEpoch:epoch,startWindow:stage=="sample"?index:-1,
                    minimumY:p.y,rose:false,fell:false,landed:false};hold=7;
            }
            if(mode!="jump")hold=0;
            c.keyJump=hold>0;if(hold>0)--hold;
            c.keyRun=false;c.keyDash=false;c.keyAttack=false;
        }
        private function holdCamera(enabled:Boolean):void {
            require(camera===w.cam,"Camera identity changed before window");
            require(camera.moved===originalCamMoved&&!cameraHeld,"Previous window did not restore camera flag");
            cameraHeld=enabled;
            if(enabled)camera.moved=false;
        }
        private function releaseCamera(reason:String):void {
            if(camera!=null) {
                var wasHeld:Boolean=cameraHeld;
                camera.moved=originalCamMoved;cameraHeld=false;
                if(wasHeld)++cameraRestores;
                if(out&&out.cameraControl)out.cameraControl.restores.push({reason:reason,window:index,
                    wasHeld:wasHeld,restored:camera.moved===originalCamMoved});
            }
        }
        private function beginWindow(p:Object,at:int):void {
            require(Math.abs(p.dx)<.01&&!p.left&&!p.right,"Window began before horizontal settling");
            holdCamera(index==2||index==3);
            row={epoch:epoch,index:index,mode:ORDER[index],frames:[],startedAtMs:at,startPose:p,
                startCounters:counters(),startSurfaces:surfaces(),startMemory:memory(),startActivity:activity(),
                cameraHeld:cameraHeld,originalCamMoved:originalCamMoved,heldX:camera.vx,heldY:camera.vy};
            out.windows.push(row);stage="sample";age=0;controls(String(row.mode),p);
        }
        private function closeWindow(p:Object,at:int):void {
            row.endedAtMs=at;row.endPose=p;row.endCounters=counters();row.endSurfaces=surfaces();
            row.endMemory=memory();row.endActivity=activity();
            row.steady=signature(row.startCounters)==signature(row.endCounters);
            require(row.steady,"Camera sample changed resident/warm/miss counters");
            row.completedJumps=0;row.jumpHeights=[];
            for each(var jump:Object in out.jumps)if(jump.startEpoch==epoch&&jump.endEpoch==epoch&&jump.startWindow==index&&jump.endWindow==index) {
                if(jump.rose&&jump.fell&&jump.landed&&Number(jump.height)>1){++row.completedJumps;row.jumpHeights.push(jump.height);}
            }
            if(row.mode=="jump")require(row.completedJumps>=1,"Jump window lacks a complete native rise/fall/landing above 1px");
            releaseCamera("window-boundary");row.cameraRestored=camera.moved===originalCamMoved&&!cameraHeld;
            ++index;age=0;stage="settle";controls("center",p);
            if(index<6)return;
            out.complete=true;out.endedAtMs=at;out.valid=true;ended=true;clear();
        }
        /** Called once per native frame at the existing late probe listener. */
        public function step(head:int,lastTail:int,nativeBand:int):Boolean {
            if(ended)return true;
            var now:int=getTimer(),p:Object=pose(),count:Object=counters(),key:String=signature(count);
            ++serial;groundRun=p.floorContact?groundRun+1:0;
            quiet=key==lastKey&&(!large||w.grafon.sceneViewReady())?quiet+1:0;lastKey=key;
            observeJump(p);require(!p.isFly&&Number(p.levit)==0,"Flight/levitation is outside native jump comparison");
            var frame:Object={serial:serial,atMs:now,dtMs:now-previous,phase:stage,epoch:epoch,window:index,
                pose:p,counters:count,nativeBandMs:nativeBand,priorScriptMs:priorHead>0?lastTail-priorHead:null};
            if(serial%30==0){frame.memory=memory();frame.activity=activity();}
            out.timeline.push(frame);previous=now;priorHead=head;++age;
            if(stage=="calibrate") {
                controls(age<=120?"walk":age<=240?"jump":"center",p);
                if(age>=240&&Math.abs(p.x-anchor)<=12&&Math.abs(p.dx)<.01&&!p.left&&!p.right&&groundRun>=10&&quiet>=20&&cycle==null) {
                    out.setup.endedAtMs=now;out.setup.frames=serial;out.setup.counters=count;
                    out.setup.memory=memory();out.setup.anchorPose=p;stage="settle";age=0;
                }
                require(age<1200,"Natural viewport/landing calibration did not settle");
            } else if(stage=="settle") {
                controls("center",p);
                if(Math.abs(p.x-anchor)<=12&&Math.abs(p.dx)<.01&&!p.left&&!p.right&&groundRun>=10&&quiet>=20&&cycle==null)beginWindow(p,now);
                require(age<600,"Native return to anchor did not settle");
            } else {
                require(Math.abs(p.dx)<.01&&!p.left&&!p.right,"Pure vertical/still window gained horizontal motion");
                require(signature(count)==signature(row.startCounters),"Prewarm/miss/resident change during camera sample");
                require(p.cameraHeld==row.cameraHeld&&p.cameraMoved===!row.cameraHeld,"Camera control state mismatch");
                if(row.cameraHeld)require(p.cameraX==row.heldX&&p.cameraY==row.heldY&&p.quakeX==0&&p.quakeY==0,"Held viewport moved or shook");
                row.frames.push(frame);
                if(age>=120)closeWindow(p,now);else controls(String(row.mode),p);
            }
            return ended;
        }
        public function clear():Object {
            try {if(w&&w.ctr)neutral();}
            finally {
                releaseCamera("clear");
                out.cleanup={keysCleared:true,positionWrites:0,velocityWrites:0,displayBindingsChanged:0,nativeDataDisposed:0,
                    cameraOriginalMoved:originalCamMoved,cameraMoved:camera==null?null:Boolean(camera.moved),
                    cameraHeld:cameraHeld,cameraRestored:camera!=null&&camera.moved===originalCamMoved,heldRestores:cameraRestores};
            }
            return out.cleanup;
        }
        public function snapshot():Object{return out;}
    }
}
