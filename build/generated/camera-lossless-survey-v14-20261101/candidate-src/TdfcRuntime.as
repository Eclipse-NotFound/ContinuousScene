package {
 import flash.display.DisplayObjectContainer;
 import flash.display.MovieClip;
 import flash.desktop.NativeApplication;
 import flash.events.Event;
 import flash.system.ApplicationDomain;
 import flash.utils.Dictionary;
 import flash.utils.getTimer;
 public class TdfcRuntime {
  private static var host:DisplayObjectContainer;
  private static var worldClass:Class;
  private static var room:*;
  private static var states:Dictionary=new Dictionary(true);
  private static var all:Array=[];
  private static var nextKey:int=1,frame:int=0;
  public static var tick:int=0;
  public static var status:String="初始化";
  private static var perception:PerceptionModel=new PerceptionModel();
  private static var squads:SquadMind=new SquadMind();
  private static var overlay:DebugOverlay;
  private static var cost:Number=0;
  public static var scenePoolEnabled:Boolean=false;
  public static var sceneValidate:Boolean=false;
  public static var sceneChecks:int=0,sceneFailures:int=0;
  private static var sceneCalls:int=0,sceneReuses:int=0;
  public static function sceneStats():Object {return {tick:tick,cost:cost,active:all.length,calls:sceneCalls,reuses:sceneReuses,checks:sceneChecks,failures:sceneFailures,status:status};}
  private static function sceneSnapshot(u:*,b:BrainState):Object {
   ++sceneCalls;
   var recycled:Object=scenePoolEnabled && b?b.previous:null;
   if(recycled==null)return GameBridge.snapshot(u);
   ++sceneReuses;
   var reference:Object=sceneValidate?GameBridge.snapshot(u):null;
   var out:Object=GameBridge.snapshotInto(u,recycled);
   if(reference)for(var key:String in reference) {
    ++sceneChecks;var a:*=reference[key],v:*=out[key];
    if(a!==v && !(a is Number && v is Number && isNaN(a) && isNaN(v)))++sceneFailures;
   }
   return out;
  }
  public static function init(main:*):void {
   if(host)return;host=main as DisplayObjectContainer;
   if(host && NativeApplication.nativeApplication.applicationID.indexOf("pfe-modsettings-continuous-motion-")==0) {
    var sceneTest:MovieClip=new MovieClip();sceneTest.name="ContinuousSceneTdfcThreat";sceneTest.visible=false;sceneTest.api=GameBridge;sceneTest.runtime=TdfcRuntime;host.addChild(sceneTest);
   }
   if(!host || !host.stage){TdfcLog.line("error","stage unavailable");return;}
   TdfcLog.line("scene-compat","v0.6.4-scene2 distant-enemy scheduling and cached threat classification");
   overlay=new DebugOverlay(host,saveReport);ScenarioRunner.init();overlay.enabled=ScenarioRunner.active;host.stage.addEventListener(Event.ENTER_FRAME,onFrame);
   GrabDiagnostics.init(host.stage,function():*{return worldClass?worldClass["w"]:null;},function():Boolean{return overlay.enabled;});
  }
  private static function reset(loc:*):void {
   PlayerNoise.reset();
   for each(var b:BrainState in all)ActionExecutor.restore(b);
   states=new Dictionary(true);all=[];room=loc;perception.reset();squads.reset();TdfcLog.line("room","reset");
  }
  private static function onFrame(e:Event):void {
   frame++;var w:*=null;
   try {
    if(!worldClass)worldClass=ApplicationDomain.currentDomain.getDefinition("fe.World") as Class;
    w=worldClass["w"];ScenarioRunner.boot(w,frame);
    GrabDiagnostics.update(w);
    var loc:*=GameBridge.get(w,"loc");if(loc!==room)reset(loc);
    var why:String=GameBridge.pause(w);
    if(why)status=why;
    else {
     status="运行";var start:int=getTimer();tick++;sceneCalls=0;sceneReuses=0;
     var gg:*=GameBridge.get(loc,"gg"),g:Object=GameBridge.snapshot(gg);
     PlayerNoise.update(gg);
     ScenarioRunner.combat(w,tick);
     var units:Array=GameBridge.get(loc,"units",[]) as Array,fresh:Array=[],present:Dictionary=new Dictionary(true);
     var sceneGrafon:*=GameBridge.get(w,"grafon"),sceneSleep:Object=null;
     if(GameBridge.get(sceneGrafon,"sceneLarge",false) && "sceneNativeCall" in sceneGrafon)
      sceneSleep=sceneGrafon.sceneNativeCall("sleeping",[loc]);
     for each(var u:* in units) {
      if(sceneSleep && sceneSleep[u]) {
       var remembered:BrainState=states[u];
       if(remembered && remembered.lastSeen>=0)sceneGrafon.sceneNativeCall("wake",[u]);
       else continue;
      }
      if(u===gg)continue;var b:BrainState=states[u];var s:Object=sceneSnapshot(u,b);if(!GameBridge.hostile(s,g))continue;
      if(!b){b=new BrainState(nextKey++,u,EnemyProfile.make(s));states[u]=b;}
      b.previous=b.sample;b.sample=s;fresh.push(b);present[u]=true;ActionExecutor.assess(b,tick);
      if(b.profile.supported)perception.observe(b,g,GameBridge.sense(b,g,loc),tick);
     }
     for each(var old:BrainState in all)if(!present[old.unit]){ActionExecutor.restore(old);delete states[old.unit];}
     all=fresh;perception.deliver(all,tick);perception.schedule(all,tick);squads.frame(all,tick);
     for each(b in all) {
      if(!b.profile.supported){b.action=TacticalMind.action("vanilla",b.profile.excluded,b.sample.x,b.sample.y);continue;}
      if(ActionExecutor.yieldToNative(b)){squads.release(b.sample.fraction,b.key,tick);continue;}
      ScenarioRunner.prepareBrain(b,tick);
      var context:Object=squads.context(b,all,tick);
      var target:Object={x:b.knownX,y:b.knownY,cx:b.knownX,cy:b.knownY-g.height/2,height:g.height,unit:gg,obs:g.obs,maxObs:g.maxObs};
      var dx:Number=b.sample.x-target.x,dy:Number=b.sample.y-target.y,distance:Number=Math.sqrt(dx*dx+dy*dy);
      var aimed:Boolean=false;
      if(b.confirmed && !isNaN(g.rot)){var angle:Number=Math.atan2(b.sample.cy-g.wy,b.sample.x-g.wx)-g.rot;while(angle>Math.PI)angle-=2*Math.PI;while(angle< -Math.PI)angle+=2*Math.PI;aimed=Math.abs(angle)<0.15;}
      // 候选缓存跨决策帧保留，避免扫描节拍与思考节拍错开后永远看不到掩体。
      if(Math.abs(b.sample.x-b.coverScanX)>40 || Math.abs(target.x-b.coverTargetX)>60 || tick-b.coverScanAt>Config.COVER_CACHE_AGE)b.coverCandidates=[];
      if(tick-b.lastSeen<b.profile.memory && tick%Config.COVER_SCAN_EVERY==b.key%Config.COVER_SCAN_EVERY && tick>=b.stuckUntil) {
       b.coverCandidates=GameBridge.covers(b,target,loc,context.side);b.coverScanAt=tick;b.coverScanX=b.sample.x;b.coverTargetX=target.x;
      }
      var coverList:Array=b.coverCandidates;
      var rx:Number=b.sample.x+(dx>=0?150:-150);
      var retreat:Object=GameBridge.walkable(loc,b.sample,rx,b.sample.y)?{x:rx,y:b.sample.y}:null;
      var env:Object={distance:distance,aimed:aimed,covers:coverList,coverSafe:b.cover==null || !GameBridge.clear(loc,b.cover.x,b.cover.y-b.sample.height/2,target.cx,target.cy),retreat:retreat,squad:context,slotOwned:squads.owns(b.sample.fraction,b.key),threat:tick%5==b.key%5?GameBridge.threat(b.sample,loc):null};
      ScenarioRunner.prepareDecision(b,env,tick);
      var before:String=b.action.kind,a:Object=TacticalMind.decide(b,env,tick);
      if(a.kind=="suppress" && before!="suppress" && !squads.claim(b.sample.fraction,b.key,tick,b.until-tick))a=TacticalMind.action("hold","同伴已占用压制位置",target.x,target.y);
      if(before=="suppress" && a.kind!="suppress")squads.release(b.sample.fraction,b.key,tick);
      b.action=a;
      if(before!=a.kind)TdfcLog.line("decision","#"+b.key+" "+b.profile.family+" T"+b.profile.tier+" "+a.kind+" "+a.reason);
      ActionExecutor.apply(b,b.confirmed?g:target,loc,tick);
     }
     cost=getTimer()-start;ScenarioRunner.observe(all,status,tick);
     if(tick%Config.HEARTBEAT_EVERY==0)TdfcLog.line("heartbeat","tick="+tick+" units="+all.length+" cost="+cost+"ms");
    }
   }catch(err:Error){status="TDFC 错误 "+err.errorID;TdfcLog.line("error",err.message+" "+err.getStackTrace());}
   if(frame%3==0){try{overlay.update(w,all,status,tick,cost,TdfcLog.status);if(ScenarioRunner.active && frame%150==0)overlay.capture();}catch(uiErr:Error){TdfcLog.line("ui-error",uiErr.message);}}
   if(frame%30==0)TdfcLog.flush();
  }
  public static function saveReport():void {
   var lines:Array=["TDFC "+Config.VER+" "+status+" tick="+tick,new Date().toUTCString(),"Save: "+JSON.stringify(TestSave.evidence),"Grab: "+JSON.stringify(GrabDiagnostics.last),"GrabRecent: "+JSON.stringify(GrabDiagnostics.recent)];
   var g:Object=GameBridge.snapshot(GameBridge.get(room,"gg"));
   lines.push("Player: "+JSON.stringify({position:[g.x,g.y],center:[g.cx,g.cy],face:g.face,exposure:g.obs,maxExposure:g.maxObs}));
   for each(var b:BrainState in all) {
    var gun:*=GameBridge.get(b.unit,"currentWeapon");
    var aim:Object={beforeOrder:[b.sample.aimX,b.sample.aimY],current:[GameBridge.num(b.unit,"celX"),GameBridge.num(b.unit,"celY")],
     remembered:[b.knownX,b.knownY],visualAge:tick-b.lastVisual,face:GameBridge.num(b.unit,"storona"),viewAngle:GameBridge.num(b.unit,"vAngle"),
     weapon:[GameBridge.num(gun,"X"),GameBridge.num(gun,"Y")],rot:GameBridge.num(gun,"rot"),attached:GameBridge.num(gun,"krep"),ready:GameBridge.get(gun,"ready",false)};
    lines.push("#"+b.key+" "+b.sample.id+" "+b.profile.style+" T"+b.profile.tier+" "+b.profile.source+"\n  position="+b.sample.x+","+b.sample.y+" hp="+b.sample.hp+" fraction="+b.sample.fraction+"\n  evidence="+b.evidence+" age="+(tick-b.lastSeen)+" observed="+b.observed+" confirmed="+b.confirmed+"\n  action="+b.action.kind+" reason="+b.action.reason+" goal="+b.action.x+","+b.action.y+"\n  result="+b.result+" fault="+b.rejected+" stuckUntil="+b.stuckUntil+" suppressCooldown="+b.suppressCooldown+"\n  sense="+JSON.stringify(b.sensing)+"\n  aim="+JSON.stringify(aim));
   }
   TdfcLog.saveReport(lines.join("\n"));
  }
  public static function captureReport():void {if(overlay){overlay.update(worldClass?worldClass["w"]:null,all,status,tick,cost,TdfcLog.status);overlay.capture();}}
  public static function setObservation(enabled:Boolean,w:*):void {if(ScenarioRunner.active && overlay){overlay.enabled=enabled;overlay.update(w,all,status,tick,cost,TdfcLog.status);}}
 }
}
