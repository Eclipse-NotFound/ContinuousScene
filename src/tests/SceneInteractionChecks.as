package tests {
    import flash.desktop.NativeApplication;
    import flash.utils.getDefinitionByName;
    import flash.utils.getQualifiedClassName;

    /** Isolated-driver helper. Call beforeFrame before World.step and afterFrame
     *  after it, once per actual game frame. Do not drive the player elsewhere
     *  while active. dispose() restores every field changed by this fixture and
     *  removes its box; ordinary simulation time is intentionally allowed to run.
     *
     *  This tests the native E execution gate with a deliberately selected native
     *  Box. It does not pretend that selecting a target proves natural mouse
     *  discovery. A real Interact opens the empty box; no inventory item, XP,
     *  native terrain, save slot, script, or puzzle is added or changed.
     */
    public class SceneInteractionChecks {
        public var done:Boolean = false;
        public var result:Object = {ok:false,checks:[],records:[],selection:"explicit native Box target; native E execution"};
        private var w:*, loc:*, gg:*, box:*;
        private var savedPlayer:Object, savedKeys:Object, savedWorld:Object, savedCamera:Object;
        private var savedTelemaster:int, savedPort:Boolean, savedTarget:*, savedDistance:Number;
        private var countExisted:Boolean, oldCount:*;
        private var fixture:Object;
        private var cases:Array = [
            {name:"solid wall blocks E without telemaster",telemaster:0,port:true,opens:false},
            {name:"native telemaster permits box E through wall",telemaster:1,port:true,opens:true},
            {name:"portOff restores wall restriction with telemaster",telemaster:1,port:false,opens:false}
        ];
        private var current:int = 0;
        private var phase:int = 0;
        private var entered:Boolean = false;
        private var cleaned:Boolean = false;
        private var started:Boolean = false;
        private var inputRecord:Object;
        private var extended:Boolean = false;
        private var large:Boolean = false;
        private var visiblePose:Object;
        private var savedSkills:Object;
        private var heldFrames:int = 10;
        private static const PLAYER_FIELDS:Array = ["X","Y","X1","X2","Y1","Y2","dx","dy","osndx","osndy","isTake"];

        /** mode="extended" is a separate regression suite; the default stays
         *  the original three E presses / nine actual frames. Extended uses
         *  real E lockpicking and Y activation, with controlled player placement
         *  after a visible start. No Interact completion method is called.
         */
        public function SceneInteractionChecks(world:*, minTileX:int = -1, mode:String = "basic") {
            w=world; loc=w ? w.loc : null; gg=w ? w.gg : null;
            try {
                if(mode!="basic" && mode!="extended") throw new Error("Unknown interaction check mode: "+mode);
                extended=mode=="extended";
                var appId:String=String(NativeApplication.nativeApplication.applicationID);
                if(appId.indexOf("pfe-modsettings-continuous-")!=0)
                    throw new Error("Interaction fixture requires isolated ContinuousScene AIR ID");
                if(!loc || !gg || gg.loc!==loc || !loc.active || loc.base || loc.prob)
                    throw new Error("Use an active non-base factory room without a native puzzle");
                if(w.allStat!=1 || w.onPause || w.t_exit!=0 || !gg.ggControl || gg.disabled || gg.trigDis || gg.t_emerg>0 || gg.actionObj || gg.teleObj ||
                   gg.rat!=0 || gg.sats.que.length || gg.work=="lurk" || gg.work=="unlurk" || gg.work=="res")
                    throw new Error("Player must be freely controllable with no pending action or telekinesis");
                savedPlayer=snapshot(gg,PLAYER_FIELDS);
                if(extended) {
                    savedPlayer.t_action=gg.t_action; savedPlayer.mt_action=gg.mt_action;
                    savedSkills=snapshot(w.pers,["hacker","hackerMaster","lockPickTime"]);
                    large=loc.spaceX>48 || loc.spaceY>25;
                    cases=[
                        {name:"visible E hack completes",kind:"hold",telemaster:0,port:true,occlude:false,opens:true},
                        {name:"E hack cancels after physical occlusion",kind:"hold",telemaster:0,port:true,occlude:true,opens:!large},
                        {name:"telemaster retains E hack through wall",kind:"hold",telemaster:1,port:true,occlude:true,opens:true},
                        {name:"portOff cancels occluded E hack",kind:"hold",telemaster:1,port:false,occlude:true,opens:!large},
                        {name:"visible Y activation completes",kind:"crack",telemaster:0,port:true,occlude:false,opens:true},
                        {name:"Y activation blocked by physical wall",kind:"crack",telemaster:0,port:true,occlude:true,opens:!large},
                        {name:"telemaster retains Y activation through wall",kind:"crack",telemaster:1,port:true,occlude:true,opens:true},
                        {name:"portOff blocks Y activation through wall",kind:"crack",telemaster:1,port:false,occlude:true,opens:!large}
                    ];
                    result.mode=mode; result.large=large;
                    result.policy="large scenes revalidate LOS; ordinary rooms preserve native behavior";
                    result.selection="explicit native Box target; native E hack/Y activation; controlled relocation after E start";
                }
                savedWorld=snapshot(w,["celX","celY"]);
                savedCamera=snapshot(w.cam,["celX","celY"]);
                savedKeys={};
                for each(var key:XML in w.ctr.keyXML.key) {
                    var id:String=String(key.@id);
                    if(id in w.ctr) savedKeys[id]=w.ctr[id];
                }
                for each(id in ["keyDubLeft","keyDubRight","keyDubSit","keyFly","keyTest1"])
                    if(id in w.ctr) savedKeys[id]=w.ctr[id];
                savedTelemaster=w.pers.telemaster; savedPort=loc.portOn;
                savedTarget=loc.celObj; savedDistance=loc.celDist;
                started=true;
                if(loc.land.kolAll) {
                    countExisted=loc.land.kolAll.hasOwnProperty("case");
                    oldCount=loc.land.kolAll["case"];
                }
                var BoxClass:Class=getDefinitionByName("fe.loc.Box") as Class;
                box=new BoxClass(loc,"case",0,0,<obj id="case" set="1" inter="1" cont="empty" lock="0" mine="0" knop="1" time="0"/>);
                // Decorative mounting suppresses this fixture's own falling; it
                // never binds collision tiles and is not added to loc.objs.
                box.wall=1; box.stay=true; box.sndOpen=box.sndClose="";
                box.code="continuous-scene-interaction-fixture";
                box.inter.xp=0; box.inter.allact=""; box.inter.prob=null;
                box.inter.cons=null; box.inter.actFun=null;
                if(minTileX<0) minTileX=loc.spaceX>48?48:2;
                fixture=findWall(minTileX);
                if(!fixture && minTileX>2) fixture=findWall(2);
                if(!fixture) throw new Error("No safe solid-wall interaction fixture found");
                if(extended) {
                    visiblePose=findVisiblePose();
                    if(!visiblePose) throw new Error("No unobstructed player pose near the wall fixture");
                    result.visiblePose=visiblePose;
                }
                moveBox(fixture.bx,fixture.by);
                loc.addObj(box);
                result.fixture=fixture;
                result.boxClass=getQualifiedClassName(box);
                result.interactionClass=getQualifiedClassName(box.inter);
                result.original={telemaster:savedTelemaster,portOn:savedPort,playerX:savedPlayer.X,playerY:savedPlayer.Y};
                result.background=auditBackground();
                check(true,"real native box and physical wall fixture created");
            } catch(error:Error) {
                result.error=error.message;
                check(false,"interaction fixture setup");
                dispose(); done=true;
            }
        }

        public function beforeFrame():void {
            if(done || cleaned) return;
            if(extended) { beforeExtendedFrame(); return; }
            try {
                if(w.loc!==loc || w.gg!==gg) throw new Error("Location/player changed during interaction check");
                entered=w.allStat==1 && !w.onPause && w.t_exit==0;
                if(!entered) throw new Error("Game paused during interaction check");
                for(var key:String in savedKeys) w.ctr[key]=false;
                placePlayer(fixture.px,fixture.py);
                moveBox(fixture.bx,fixture.by);
                w.pers.telemaster=cases[current].telemaster;
                loc.portOn=cases[current].port;
                if(phase==0) {
                    box.inter.open=false; box.inter.active=true;
                    box.inter.action=1; box.inter.knop=1; box.inter.is_act=false;
                    box.inter.is_ready=true; box.inter.setAct("open",0);
                    box.inter.update();
                }
                var tx:Number=box.X, ty:Number=box.Y-box.scY/2;
                w.celX=tx; w.celY=ty;
                w.cam.celX=tx*w.cam.scaleV+w.cam.vx;
                w.cam.celY=ty*w.cam.scaleV+w.cam.vy;
                // Deliberately seed the selected native object. No direct call
                // to act(), actOsn(), or setAct(open,1) is made by the fixture.
                box.onCursor=box.prior;
                loc.celObj=box;
                loc.celDist=(gg.X-box.X)*(gg.X-box.X)+(gg.Y-box.Y)*(gg.Y-box.Y);
                w.ctr.keyAction=phase==1;
                if(phase==1) inputRecord={
                    name:cases[current].name,telemaster:w.pers.telemaster,portOn:loc.portOn,
                    isLine:loc.isLine(gg.X,gg.Y-gg.scY*.75,tx,ty,box),
                    distanceSquared:loc.celDist,actionDistanceSquared:w.actionDist,
                    selectedClass:getQualifiedClassName(loc.celObj),selectedCode:loc.celObj.code,
                    player:{x:gg.X,y:gg.Y,eyeY:gg.Y-gg.scY*.75},target:{x:tx,y:ty},
                    before:state(),expectedOpen:cases[current].opens
                };
            } catch(error:Error) {
                result.error=error.message; check(false,"interaction frame preparation");
                dispose(); done=true;
            }
        }

        public function afterFrame():void {
            if(done || cleaned || !entered) return;
            if(extended) { afterExtendedFrame(); return; }
            try {
                if(phase==1) {
                    inputRecord.after=state();
                    inputRecord.selectedAfter=loc.celObj ? getQualifiedClassName(loc.celObj) : null;
                    inputRecord.success=Boolean(box.inter.open);
                    result.records.push(inputRecord);
                    check(inputRecord.isLine===false,"physical wall occludes ray: "+cases[current].name);
                    check(inputRecord.distanceSquared<=inputRecord.actionDistanceSquared,"interaction remains within native range: "+cases[current].name);
                    check(Boolean(box.inter.open)==Boolean(cases[current].opens),cases[current].name);
                }
                // Release for a real native frame after each press. This also
                // restores UnitPlayer's private actionReady latch naturally.
                if(++phase==3) {
                    phase=0;
                    if(++current==cases.length) {
                        dispose(); done=true;
                        result.ok=result.checks.every(function(item:Object,index:int,list:Array):Boolean {return item.ok;});
                    }
                }
            } catch(error:Error) {
                result.error=error.message; check(false,"interaction frame observation");
                dispose(); done=true;
            }
        }

        public function dispose():void {
            if(cleaned) return;
            cleaned=true;
            try {
                if(box) {
                    if(box.in_chain) loc.remObj(box);
                    else box.remVisual();
                    if(box.shad && box.shad.parent) box.shad.parent.removeChild(box.shad);
                }
                if(started && loc.land.kolAll) {
                    if(countExisted) loc.land.kolAll["case"]=oldCount;
                    else delete loc.land.kolAll["case"];
                }
            } finally {
                if(started) {
                    restore(gg,savedPlayer); restore(w,savedWorld); restore(w.cam,savedCamera);
                    restore(w.ctr,savedKeys);
                    if(savedSkills) restore(w.pers,savedSkills);
                    w.pers.telemaster=savedTelemaster; loc.portOn=savedPort;
                    loc.celObj=savedTarget; loc.celDist=savedDistance;
                    if(gg.actionObj && box && gg.actionObj===box.inter) gg.actionObj=null;
                }
                result.cleaned=true;
            }
        }

        private function state():Object {
            var saved:Object={}; box.inter.save(saved);
            return {open:box.inter.open,active:box.inter.active,isAct:box.inter.is_act,
                action:box.inter.action,saveOpen:saved.open,saveLoot:saved.loot,
                playerActionTargetsBox:gg.actionObj===box.inter,lock:box.inter.lock,mine:box.inter.mine,
                remaining:gg.t_action};
        }
        private function beforeExtendedFrame():void {
            try {
                if(w.loc!==loc || w.gg!==gg) throw new Error("Location/player changed during extended interaction check");
                entered=w.allStat==1 && !w.onPause && w.t_exit==0;
                if(!entered) throw new Error("Game paused during extended interaction check");
                for(var key:String in savedKeys) w.ctr[key]=false;
                var test:Object=cases[current];
                var occluded:Boolean=Boolean(test.occlude) && (test.kind=="crack" || phase>=2);
                placePlayer(occluded?fixture.px:visiblePose.x,occluded?fixture.py:visiblePose.y);
                moveBox(fixture.bx,fixture.by);
                w.pers.telemaster=test.telemaster; loc.portOn=test.port;
                // Guaranteed native terminal unlock with no lockpick/item use.
                // getChance(1-10) is exactly 1, and native duration is 6 frames.
                w.pers.hacker=10; w.pers.hackerMaster=10; w.pers.lockPickTime=10;
                if(phase==0) {
                    box.inter.open=false; box.inter.active=true; box.inter.action=1;
                    box.inter.knop=1; box.inter.is_act=false; box.inter.is_ready=true;
                    box.inter.cont="empty"; box.inter.at_once=1; box.inter.t_action=0;
                    box.inter.lockKey=null; box.inter.lockTip=2; box.inter.lockLevel=0;
                    box.inter.mineTip=6; box.inter.noRuna=false;
                    box.inter.successUnlock=null; box.inter.fiascoUnlock=null;
                    box.inter.successRemine=null; box.inter.fiascoRemine=null;
                    box.inter.setAct("open",0);
                    box.inter.setAct("lock",test.kind=="hold"?1:0);
                    box.inter.setAct("mine",test.kind=="crack"?1:0);
                    box.inter.update(); box.inter.sndAct="";
                    inputRecord={name:test.name,kind:test.kind,telemaster:test.telemaster,portOn:test.port,
                        expectedOpen:test.opens,frames:[],started:false};
                }
                var tx:Number=box.X,ty:Number=box.Y-box.scY/2;
                w.celX=tx;w.celY=ty;
                w.cam.celX=tx*w.cam.scaleV+w.cam.vx;w.cam.celY=ty*w.cam.scaleV+w.cam.vy;
                box.onCursor=box.prior;loc.celObj=box;
                loc.celDist=(gg.X-box.X)*(gg.X-box.X)+(gg.Y-box.Y)*(gg.Y-box.Y);
                w.ctr.keyAction=test.kind=="hold" && phase>=1 && phase<=heldFrames;
                w.ctr.keyCrack=test.kind=="crack" && phase==1;
                inputRecord.frames.push({phase:phase,occluded:occluded,
                    isLine:loc.isLine(gg.X,gg.Y-gg.scY*.75,tx,ty,box),
                    distanceSquared:loc.celDist,actionDistanceSquared:w.actionDist,
                    keyAction:w.ctr.keyAction,keyCrack:w.ctr.keyCrack,before:state()});
            } catch(error:Error) {
                result.error=error.message;check(false,"extended interaction frame preparation");
                dispose();done=true;
            }
        }
        private function afterExtendedFrame():void {
            try {
                var test:Object=cases[current];
                var row:Object=inputRecord.frames[inputRecord.frames.length-1];
                row.after=state();
                row.lineAfter=loc.isLine(gg.X,gg.Y-gg.scY*.75,box.X,box.Y-box.scY/2,box);
                if(phase==1 && test.kind=="hold") {
                    inputRecord.started=gg.actionObj===box.inter;
                    check(inputRecord.started,"native E created pending hack: "+test.name);
                    check(row.isLine===true && row.lineAfter===true,"hack starts with clear LOS: "+test.name);
                }
                if(phase==1 && test.kind=="crack" || phase==2 && test.kind=="hold") {
                    check(row.isLine===!Boolean(test.occlude),"fixture LOS at decisive input: "+test.name);
                    check(row.lineAfter===!Boolean(test.occlude),"fixture LOS after native movement: "+test.name);
                    check(row.distanceSquared<=row.actionDistanceSquared,"fixture remains within native range: "+test.name);
                    if(test.kind=="hold" && test.occlude && large && !test.opens)
                        check(gg.actionObj!==box.inter,"occluded hack canceled before completion: "+test.name);
                }
                var last:int=test.kind=="hold"?heldFrames+1:2;
                if(phase==last) {
                    inputRecord.after=state();inputRecord.success=Boolean(box.inter.open);
                    result.records.push(inputRecord);
                    check(Boolean(box.inter.open)==Boolean(test.opens),test.name);
                    check(!gg.actionObj,"native release clears pending action: "+test.name);
                    phase=0;
                    if(++current==cases.length) {
                        dispose();done=true;
                        result.ok=result.checks.every(function(item:Object,index:int,list:Array):Boolean{return item.ok;});
                    }
                } else ++phase;
            } catch(error:Error) {
                result.error=error.message;check(false,"extended interaction frame observation");
                dispose();done=true;
            }
        }
        private function findVisiblePose():Object {
            // Search only the same 200 px native interaction neighbourhood.
            for each(var oy:Number in [0,-20,20,-40,40,-80,80])
                for each(var ox:Number in [0,-40,40,-80,80,-120,120]) {
                    var x:Number=fixture.bx+ox,y:Number=fixture.by+oy;
                    if(x-gg.scX/2<0 || x+gg.scX/2>=loc.spaceX*40 || y-gg.scY<0 || y>=loc.spaceY*40) continue;
                    if(ox*ox+oy*oy>w.actionDist || loc.collisionUnit(x,y,gg.scX,gg.scY)) continue;
                    if(loc.isLine(x,y-gg.scY*.75,fixture.bx,fixture.by-box.scY/2,box)) return {x:x,y:y};
                }
            return null;
        }
        private function check(ok:Boolean,name:String):void { result.checks.push({ok:ok,name:name}); }
        private function snapshot(owner:*,fields:Array):Object {
            var out:Object={}; for each(var key:String in fields) if(key in owner) out[key]=owner[key]; return out;
        }
        private function restore(owner:*,values:Object):void { for(var key:String in values) owner[key]=values[key]; }
        private function placePlayer(x:Number,y:Number):void {
            gg.X=x; gg.Y=y; gg.X1=x-gg.scX/2; gg.X2=x+gg.scX/2; gg.Y1=y-gg.scY; gg.Y2=y;
            gg.dx=gg.dy=0; if("osndx" in gg) gg.osndx=0; if("osndy" in gg) gg.osndy=0;
            if("isTake" in gg) gg.isTake=0;
        }
        private function moveBox(x:Number,y:Number):void {
            box.X=x; box.Y=y; box.X1=x-box.scX/2; box.X2=x+box.scX/2; box.Y1=y-box.scY; box.Y2=y;
            box.inter.X=x; box.inter.Y=y;
            if(box.vis) {box.vis.x=x;box.vis.y=y;}
            if(box.shad) {box.shad.x=x;box.shad.y=y+2;}
        }
        private function findWall(minX:int):Object {
            for(var x:int=Math.max(2,minX);x<loc.spaceX-3;++x)
                for(var y:int=3;y<loc.spaceY-3;++y) {
                    var tile:*=loc.getTile(x,y);
                    if(tile.phis!=1 || tile.door || tile.zForm || tile.diagon) continue;
                    var px:Number=(x-1)*40, py:Number=(y+1)*40-1;
                    var bx:Number=(x+2)*40, by:Number=py-gg.scY*.75+box.scY/2;
                    var found:Object=tryWall(tile,px,py,bx,by);
                    if(found) return found;
                    // A native floor/ceiling is an equally valid wall; useful
                    // when no vertical passage has enough body clearance.
                    px=(x+.5)*40; py=y*40-1; bx=px; by=(y+1)*40+box.scY+8;
                    found=tryWall(tile,px,py,bx,by);
                    if(found) return found;
                }
            return null;
        }
        private function tryWall(tile:*,px:Number,py:Number,bx:Number,by:Number):Object {
            if(loc.collisionUnit(px,py,gg.scX,gg.scY) || loc.collisionUnit(bx,by,box.scX,box.scY)) return null;
            if((px-bx)*(px-bx)+(py-by)*(py-by)>w.actionDist) return null;
            if(loc.isLine(px,py-gg.scY*.75,bx,by-box.scY/2,box)) return null;
            return {px:px,py:py,bx:bx,by:by,blockers:rayBlockers(px,py-gg.scY*.75,bx,by-box.scY/2),wall:{x:tile.X,y:tile.Y,phis:tile.phis,
                front:tile.front,back:tile.back,phX1:tile.phX1,phX2:tile.phX2,phY1:tile.phY1,phY2:tile.phY2}};
        }
        private function rayBlockers(x1:Number,y1:Number,x2:Number,y2:Number):Array {
            var WorldClass:Class=getDefinitionByName("fe.World") as Class;
            var dx:Number=x2-x1,dy:Number=y2-y1;
            var steps:int=int(Math.floor(Math.max(Math.abs(dx),Math.abs(dy))/Number(WorldClass["maxdelta"])))+1;
            var rows:Array=[],seen:Object={};
            for(var i:int=1;i<steps;++i) {
                var x:Number=x1+dx*i/steps,y:Number=y1+dy*i/steps;
                var tile:*=loc.getAbsTile(Math.floor(x),Math.floor(y));
                if(tile.phis!=1 || x<tile.phX1 || x>tile.phX2 || y<tile.phY1 || y>tile.phY2) continue;
                var key:String=tile.X+":"+tile.Y;
                if(!seen[key]) rows.push({x:tile.X,y:tile.Y,phis:tile.phis,front:tile.front,back:tile.back,door:Boolean(tile.door)});
                seen[key]=true;
            }
            return rows;
        }
        private function auditBackground():Object {
            var count:int=0, examples:Array=[];
            for(var x:int=0;x<loc.spaceX;++x) for(var y:int=0;y<loc.spaceY;++y) {
                var tile:*=loc.getTile(x,y);
                if(tile.phis==0 && tile.back!="") {
                    ++count;
                    if(examples.length<6) examples.push({x:x,y:y,front:tile.front,back:tile.back,phis:tile.phis});
                }
            }
            return {nonSolidBackdropTiles:count,examples:examples,
                meaning:"Native background walls are decoration; they do not block E rays. Count alone is not a regression."};
        }
    }
}
