package {
 import flash.system.ApplicationDomain;
 /** Isolated actual-game regression: native Location.step, production sensing and aiming. */
 public class AimFixture {
  private static var liveUnit:*,liveWorld:*,livePose:Object,liveFrame:int;
  private static var liveResult:Object;
  private static function hold(u:*,x:Number,y:Number):void {
   // Unit.setPos also calls setCel(), so it cannot be used for a repeated aim fixture.
   u.X=x;u.Y=y;u.X1=x-u.scX/2;u.X2=x+u.scX/2;u.Y1=y-u.scY;u.Y2=y;u.dx=0;u.dy=0;
  }
  private static function position(loc:*,u:*,g:*):Object {
   var s:Object=GameBridge.snapshot(u);
   for(var y:int=119;y<GameBridge.num(loc,"spaceY")*40-40;y+=40)
    for(var x:int=100;x<GameBridge.num(loc,"spaceX")*40-340;x+=40) {
     if(!GameBridge.standable(loc,x,y,s))continue;
     var poses:Array=[{x:x+180,y:y},{x:x+280,y:y-70}];
     var valid:Boolean=true;
     for each(var p:Object in poses) {
      if(GameBridge.solid(loc,p.x,p.y-5) || GameBridge.solid(loc,p.x,p.y-g.scY*.75)
       || !loc.isLine(x,y-u.scY*.75,p.x,p.y-g.scY*.6))valid=false;
     }
     if(valid)return {enemy:{x:x,y:y},poses:poses};
    }
   throw new Error("No clear aiming fixture in this room");
  }
  public static function beginLive(w:*):void {
   liveWorld=w;liveFrame=0;
   var c:Class=ApplicationDomain.currentDomain.getDefinition("fe.unit.UnitSlaver") as Class;
   liveUnit=new c("1",30,null,{weap:"autor",tr:1});
   liveUnit.putLoc(w.loc,w.loc.gg.X,w.loc.gg.Y);w.loc.addObj(liveUnit);w.loc.units.push(liveUnit);
   liveUnit.hp=liveUnit.maxhp=10000;liveUnit.level=30;liveUnit.oduplenie=0;liveUnit.storona=1;
   livePose=position(w.loc,liveUnit,w.loc.gg);
   liveResult={pass:true,fixture:livePose,phases:[],trace:[]};
   for(var i:int=0;i<2;i++)liveResult.phases.push({phase:i,samples:0,matched:0,visible:0,confirmed:0,aligned:0,maxError:0,maxAngleError:0});
   w.loc.gg.obs=w.loc.gg.maxObs*2;
   prepareLive();
  }
  public static function prepareLive():void {
   if(!liveUnit)return;
   var g:*=liveWorld.loc.gg,p:Object=livePose.poses[int(liveFrame/180)];
   hold(liveUnit,livePose.enemy.x,livePose.enemy.y);liveUnit.hp=liveUnit.maxhp;
   // visibility is a distance, not a 0..1 flag (UnitPlayer.actions uses 2000).
   hold(g,p.x,p.y);g.hp=g.maxhp;g.noise=400;g.visibility=2000;g.stealthMult=1;
  }
  /** Observe the actual ENTER_FRAME runtime. No direct perception/decision calls here. */
  public static function observeLive(all:Array):Object {
   if(!liveUnit)return null;
   var b:BrainState;
   for each(var candidate:BrainState in all)if(candidate.unit===liveUnit)b=candidate;
   if(!b)throw new Error("Live aiming actor missing from runtime");
   var g:Object=GameBridge.snapshot(liveWorld.loc.gg),gun:*=liveUnit.currentWeapon;
   var error:Number=Math.sqrt(Math.pow(liveUnit.celX-g.cx,2)+Math.pow(liveUnit.celY-g.cy,2));
   var expected:Number=Math.atan2(g.cy-gun.Y,gun.krep>0?Math.abs(g.cx-gun.X)*liveUnit.storona:g.cx-gun.X);
   var angle:Number=gun.rot-expected;
   while(angle>Math.PI)angle-=Math.PI*2;while(angle< -Math.PI)angle+=Math.PI*2;
   var phase:int=int(liveFrame/180),check:Object=liveResult.phases[phase];
   if(liveFrame%180>=120) {
    check.samples++;if(error<4)check.matched++;if(b.observed)check.visible++;
    if(b.confirmed)check.confirmed++;if(Math.abs(angle)<.05)check.aligned++;
    check.maxError=Math.max(check.maxError,error);check.maxAngleError=Math.max(check.maxAngleError,Math.abs(angle));
   }
   if(liveFrame%30==0 || liveFrame%180==179)liveResult.trace.push({frame:liveFrame,phase:phase,observed:b.observed,confirmed:b.confirmed,
    player:[g.cx,g.cy],aim:[liveUnit.celX,liveUnit.celY],face:liveUnit.storona,action:b.action.kind,error:error,angleError:angle,faults:b.faults,
    sense:b.sensing,eyes:[liveUnit.eyeX,liveUnit.eyeY],visibility:liveWorld.loc.gg.visibility,stealth:liveWorld.loc.gg.stealthMult,vision:liveUnit.vision});
   if(b.faults>0)liveResult.pass=false;
   liveFrame++;
   if(liveFrame<360)return null;
   for each(check in liveResult.phases)if(check.matched<45 || check.visible<45 || check.confirmed<45 || check.aligned<45)liveResult.pass=false;
   return liveResult;
  }
  public static function run(w:*):Object {
   var result:Object={pass:true,cases:[]},loc:*=w.loc,g:*=loc.gg;
   // Freeze unrelated actors only inside this self-exiting isolated test.
   for each(var other:* in loc.units)if(other!==g)other.disabled=true;
   g.hp=g.maxhp=10000;g.invulner=false;g.visibility=2000;g.stealthMult=1;
   for each(var modded:Boolean in [false,true]) {
    var c:Class=ApplicationDomain.currentDomain.getDefinition("fe.unit.UnitSlaver") as Class;
    var u:*=new c("1",30,null,{weap:"autor",tr:1});
    u.putLoc(loc,g.X,g.Y);loc.addObj(u);loc.units.push(u);u.hp=u.maxhp=10000;u.level=30;
    var fixture:Object=position(loc,u,g),b:BrainState=new BrainState(1,u,EnemyProfile.make(GameBridge.snapshot(u)));
    var perception:PerceptionModel=new PerceptionModel();u.storona=1;u.oduplenie=0;g.obs=g.maxObs*2;
    var item:Object={modded:modded,fixture:fixture,phases:[],trace:[]};
    for(var phase:int=0;phase<2;phase++) {
     var matched:int=0,visible:int=0,confirmed:int=0,nativeTarget:int=0,maxError:Number=0;
     for(var frame:int=0;frame<240;frame++) {
      var t:int=phase*240+frame+1,p:Object=fixture.poses[phase];
      hold(g,p.x,p.y);g.hp=g.maxhp;g.noise=400;
      hold(u,fixture.enemy.x,fixture.enemy.y);u.hp=u.maxhp;
      loc.step();
      var gs:Object=GameBridge.snapshot(g);b.previous=b.sample;b.sample=GameBridge.snapshot(u);
      var nativeAim:Array=[u.celX,u.celY];
      var sense:Object=GameBridge.sense(b,gs,loc);
      if(modded) {
       ActionExecutor.assess(b,t);perception.observe(b,gs,sense,t);
       var target:Object={x:b.knownX,y:b.knownY,cx:b.knownX,cy:b.knownY-gs.height/2,height:gs.height,unit:g,obs:gs.obs,maxObs:gs.maxObs};
       var delta:Number=Math.abs(b.sample.x-target.x);
       b.action=TacticalMind.decide(b,{distance:delta,threat:null,slotOwned:false,squad:{coverMate:false,canSuppress:false,nearest:1000,nearX:0},covers:[],retreat:null,aimed:false},t);
       ActionExecutor.apply(b,b.confirmed?gs:target,loc,t);
      }
      var ex:Number=GameBridge.num(u,"celX")-gs.cx,ey:Number=GameBridge.num(u,"celY")-gs.cy;
      var error:Number=Math.sqrt(ex*ex+ey*ey);
      if(frame>=180) {
       if(error<4)matched++;if(sense.visible)visible++;if(b.confirmed)confirmed++;if(u.celUnit===g)nativeTarget++;
       maxError=Math.max(maxError,error);
      }
      if(frame%10==0 || frame==239)item.trace.push({phase:phase,frame:frame,face:u.storona,viewAngle:u.vAngle,look:sense.look,visible:sense.visible,obs:g.obs,maxObs:g.maxObs,
       confirmed:b.confirmed,confirm:b.confirm,known:[b.knownX,b.knownY],player:[gs.cx,gs.cy],aim:[u.celX,u.celY],nativeAim:nativeAim,weapon:[GameBridge.num(u.currentWeapon,"X"),GameBridge.num(u.currentWeapon,"Y")],rot:GameBridge.num(u.currentWeapon,"rot"),target:u.celUnit===g,action:b.action.kind,error:error});
     }
     var check:Object={phase:phase,matched:matched,visible:visible,confirmed:confirmed,nativeTarget:nativeTarget,maxError:maxError};item.phases.push(check);
     if(matched<45 || visible<45)result.pass=false;
    }
    if(modded) {
     // Reproduce the native-control -> TDFC boundary when an enemy turns toward
     // an already visible player. Leave the cone at the previous frame's facing.
     hold(g,fixture.poses[0].x,fixture.poses[0].y);hold(u,fixture.enemy.x,fixture.enemy.y);
     u.storona=-1;b.sample=GameBridge.snapshot(u);b.action={kind:"hold",x:g.X,y:g.Y};b.confirmed=false;
     ActionExecutor.apply(b,GameBridge.snapshot(g),loc,500);
     u.storona=1;u.eyeX=u.X+u.scX*.25;u.eyeY=u.Y-u.scY*.75;b.sample=GameBridge.snapshot(u);
     var turnSense:Object=GameBridge.sense(b,GameBridge.snapshot(g),loc);
     item.turn={front:turnSense.front,los:turnSense.los,look:turnSense.look,visible:turnSense.visible,face:u.storona,viewAngle:u.vAngle};
     if(!turnSense.visible)result.pass=false;
     u.storona=-1;u.eyeX=u.X-u.scX*.25;b.sample=GameBridge.snapshot(u);
     var hiddenSense:Object=GameBridge.sense(b,GameBridge.snapshot(g),loc);
     perception.observe(b,GameBridge.snapshot(g),hiddenSense,501);
     ActionExecutor.apply(b,{unit:g,cx:b.knownX,cy:b.knownY-g.scY/2,height:g.scY},loc,501);
     var memoryX:Number=b.knownX,memoryY:Number=b.knownY;
     hold(g,fixture.poses[0].x,fixture.poses[0].y);g.obs=0;
     u.storona=1;u.eyeX=u.X+u.scX*.25;b.sample=GameBridge.snapshot(u);
     gs=GameBridge.snapshot(g);var returnSense:Object=GameBridge.sense(b,gs,loc);
     perception.observe(b,gs,returnSense,502);b.action={kind:"hold",x:g.X,y:g.Y};
     ActionExecutor.apply(b,gs,loc,502);
     for(var settle:int=0;settle<30;settle++)u.currentWeapon.actions();
     var gun:*=u.currentWeapon;
     var expected:Number=Math.atan2(gs.cy-gun.Y,gun.krep>0?Math.abs(gs.cx-gun.X)*u.storona:gs.cx-gun.X);
     var angleError:Number=gun.rot-expected;
     while(angleError>Math.PI)angleError-=Math.PI*2;while(angleError< -Math.PI)angleError+=Math.PI*2;
     item.reacquire={hiddenVisible:hiddenSense.visible,returnVisible:returnSense.visible,confirmed:b.confirmed,target:u.celUnit===g,
      oldKnown:[memoryX,memoryY],known:[b.knownX,b.knownY],player:[gs.cx,gs.cy],aim:[u.celX,u.celY],angleError:angleError};
     if(hiddenSense.visible || !returnSense.visible || !b.confirmed || u.celUnit!==g || Math.abs(u.celX-gs.cx)>1 || Math.abs(u.celY-gs.cy)>1 || Math.abs(angleError)>.05)result.pass=false;
    }
    ActionExecutor.restore(b);u.exterminate();result.cases.push(item);
   }
   return result;
  }
 }
}
