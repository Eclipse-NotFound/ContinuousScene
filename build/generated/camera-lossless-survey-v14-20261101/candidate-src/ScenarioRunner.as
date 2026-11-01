package {
 import flash.desktop.NativeApplication;
 import flash.system.ApplicationDomain;
 import flash.filesystem.File;
 import flash.filesystem.FileStream;
 import flash.filesystem.FileMode;
 /** 只有精确测试身份且存在显式场景文件才会开档/拉怪；正常游戏无此副作用。 */
 public class ScenarioRunner {
  public static var active:Boolean=false;
  private static var started:Boolean=false,spawned:Boolean=false,done:Boolean=false;
  private static var born:int=0,startTick:int=0,frameStart:int=0;
  private static var actors:Array=[];
  private static var initial:Object={};
  private static var seen:Object={};
  private static var options:Object={};
  private static var pauseAt:int=-1,pauseTick:int=-1,pauseOK:Boolean=false;
  private static var saveChecked:Boolean=false,travelSent:Boolean=false;
  public static function init():void {
   if(NativeApplication.nativeApplication.applicationID!=Config.TEST_APP_ID)return;
   var f:File=File.applicationDirectory.resolvePath("tdfc-test.json");if(!f.exists)return;
   try{var fs:FileStream=new FileStream();fs.open(f,FileMode.READ);options=JSON.parse(fs.readUTFBytes(fs.bytesAvailable));fs.close();active=true;TdfcLog.line("scenario","ACTIVE "+options.scenario);}catch(e:Error){TdfcLog.line("scenario-error",e.message);}
  }
  public static function boot(w:*,frame:int):void {
   if(!active || done || !w)return;
   if(frame%150==0)writeStatus(w,frame);
   if(frameStart==0)frameStart=frame;
   if(GameBridge.get(GameBridge.get(w,"verror"),"visible",false)) {finish(false,"game error: "+GameBridge.get(GameBridge.get(GameBridge.get(w,"verror"),"txt"),"text","unknown"));return;}
   if(frame-frameStart>3600 && !spawned){finish(false,"world boot timeout");return;}
   if(options.scenario!="observe" && started && GameBridge.num(w,"allStat")>=1 && GameBridge.get(GameBridge.get(w,"pip"),"active",false)) {
    try{w.pip.onoff(-1);}catch(pipError:Error){TdfcLog.line("scenario-error",pipError.message);}
   }
   if(!started && GameBridge.get(w,"landData")!=null && GameBridge.get(w,"allLandsLoaded",false)) {
    try{w.mm.active=false;TestSave.begin(w,options);started=true;born=frame;}catch(e:Error){TestSave.status="读档失败："+e.message;finish(false,"boot "+e.message);}return;
   }
   var settle:int=options.scenario=="aim-check"?45:180;
   if(started && !spawned && frame-born>settle && GameBridge.get(GameBridge.get(w,"loc"),"gg")!=null && (GameBridge.pause(w)=="" || options.scenario=="observe" && GameBridge.num(w,"allStat")>=1)) {
    try {
     if(!saveChecked){TestSave.verify(w);saveChecked=true;}
     if(options.scenario=="load-check" || options.scenario=="observe") {
      spawned=true;writeStatus(w,frame);finish(true,TestSave.status);return;
     }
     if(options.travelLand) {
      if(!travelSent) {
       travelSent=true;born=frame;w.pers.healAll();
       if(w.game.curLandId!=options.travelLand)w.game.gotoLand(String(options.travelLand));
       TdfcLog.line("scenario","travel requested "+options.travelLand);return;
      }
      if(w.game.curLandId!=options.travelLand || GameBridge.get(GameBridge.get(w,"land"),"act")==null || w.land.act.id!=options.travelLand)return;
     }
     var loc:*=w.loc,g:*=loc.gg;
     if(options.scenario=="aim-check") {
      spawned=true;seen.aim=AimFixture.run(w);
      if(!seen.aim.pass){finish(false,JSON.stringify(seen.aim));return;}
      AimFixture.beginLive(w);return;
     }
     if(options.scenario=="telekinesis-ui") {
      spawned=true;TelekinesisFixture.prepareUI(w);return;
     }
     if(options.scenario=="telekinesis-check") {
      spawned=true;
      seen.telekinesis=TelekinesisFixture.run(w);
      finish(seen.telekinesis.pass,JSON.stringify(seen.telekinesis));return;
     }
     if(options.scenario=="cover-check") {
      if(actors.length==0)add(loc,g,"fe.unit.UnitRanger",1,36,0);
      if(!CoverFixture.locate(loc,GameBridge.snapshot(actors[0]),GameBridge.num(g,"scY",40)))return;
      g.setPos(CoverFixture.found.player.x,CoverFixture.found.player.y);g.maxhp=10000;g.hp=10000;
      actors[0].setPos(CoverFixture.found.enemy.x,CoverFixture.found.enemy.y);
      initial[0]={x:actors[0].X,y:actors[0].Y};
      spawned=true;startTick=TdfcRuntime.tick;TdfcLog.line("scenario","cover fixture "+JSON.stringify(CoverFixture.found));return;
     }
     g.maxhp=10000;g.hp=10000;
     add(loc,g,"fe.unit.UnitRaider",1,4,140);
     add(loc,g,"fe.unit.UnitRanger",1,28,210);
     add(loc,g,"fe.unit.UnitRanger",3,40,270);
     spawned=true;startTick=TdfcRuntime.tick;TdfcLog.line("scenario","spawned="+actors.length);
    }catch(ex:Error){finish(false,"load/spawn "+ex.message);}
   }
   if(spawned && options.scenario=="aim-check"){AimFixture.prepareLive();return;}
   if(options.scenario=="telekinesis-ui"){if(spawned)TelekinesisFixture.sampleUI(w,frame);return;}
   if(spawned && pauseAt<0 && TdfcRuntime.tick-startTick>300) {pauseAt=frame;pauseTick=TdfcRuntime.tick;w.onPause=true;}
   if(pauseAt>=0 && frame-pauseAt>=30 && !pauseOK) {pauseOK=TdfcRuntime.tick==pauseTick;w.onPause=false;if(!pauseOK){finish(false,"tactical clock advanced while paused");return;}TdfcLog.line("scenario","PASS pause clock");}
  }
  private static function add(loc:*,g:*,name:String,tr:int,level:int,offset:int):void {
   var c:Class=ApplicationDomain.currentDomain.getDefinition(name) as Class;
   var u:*=new c(String(tr),level,null,{weap:"autor",tr:tr});
   u.maxhp=500;u.hp=500;u.putLoc(loc,g.X+offset,g.Y);u.level=level;loc.addObj(u);loc.units.push(u);
   if(u.currentWeapon!=null)u.currentWeapon.damage=2;
   actors.push(u);initial[actors.length-1]={x:u.X,y:u.Y};
  }
  public static function combat(w:*,t:int):void {
   if(!active || !spawned || done)return;
   if(options.scenario=="telekinesis-ui" || options.scenario=="aim-check")return;
   var g:*=w.loc.gg;g.hp=g.maxhp;
   if(options.scenario=="cover-check") {g.setPos(CoverFixture.found.player.x,CoverFixture.found.player.y);g.dx=0;g.dy=0;}
   if(t%120==0){try{g.pers.healAll();}catch(e:Error){}}
   g.noise=400; // 测试中的明确听觉刺激，不是模组正常噪声规则。
   if(t-startTick>180 && (t-startTick)%240==0 && actors.length>1) {
    var v:*=actors[1];if(GameBridge.num(v,"sost")==1){v.hp=100;v.hp-=5;}
   }
  }
  public static function observe(all:Array,status:String,t:int):void {
   if(!active || !spawned || done)return;
   if(options.scenario=="telekinesis-ui")return;
   if(options.scenario=="aim-check") {
    var live:Object=AimFixture.observeLive(all);
    if(live){seen.liveAim=live;finish(live.pass,JSON.stringify(live));}return;
   }
   for each(var b:BrainState in all) {
    if(actors.indexOf(b.unit)<0)continue;
    seen[b.action.kind]=true;
    if(b.profile.family=="ranger" && b.profile.supported)seen.ranger=true;
    if(b.effect!="")seen.shot=true;
    var pos:Object=initial[actors.indexOf(b.unit)];
    if(Math.abs(b.sample.x-pos.x)>30)seen.moved=true;
    if(options.scenario=="cover-check") {
     var target:Object=CoverFixture.found.player;
     var clear:Boolean=GameBridge.clear(GameBridge.get(b.unit,"loc"),b.sample.x,b.sample.cy,target.x,target.cy);
     if(seen.moved && !clear && b.action.kind=="hide")seen.covered=true;
     if(seen.covered && clear && b.action.kind=="peek")seen.peeked=true;
     if(seen.covered && seen.peeked){finish(true,"real terrain: movement, cover occlusion and peek visibility verified");return;}
     if(t%30==0)TdfcLog.line("fixture","x="+int(b.sample.x)+" y="+int(b.sample.y)+" h="+b.sample.height+" action="+b.action.kind+" goal="+int(b.action.x)+" clear="+clear+" result="+b.result);
    }
    if(b.faults>0){finish(false,"executor error "+b.rejected);return;}
   }
   var duration:int=int(options.ticks || 1200);
   if(t-startTick>=duration) {
    if(options.scenario=="cover-check"){finish(false,"cover fixture did not observe movement/occlusion/peek: "+JSON.stringify(seen));return;}
    var ok:Boolean=seen.ranger && seen.moved && pauseOK && seen.shot && TestSave.evidence.verified;
    finish(ok,"ranger="+Boolean(seen.ranger)+" moved="+Boolean(seen.moved)+" shot="+Boolean(seen.shot)+" suppress="+Boolean(seen.suppress)+" pause="+pauseOK);
   }
  }
  public static function prepareDecision(b:BrainState,e:Object,t:int):void {
   if(!active || !spawned || done || options.scenario!="cover-check" || actors.indexOf(b.unit)<0)return;
   e.aimed=true;e.threat=null;
  }
  public static function prepareBrain(b:BrainState,t:int):void {
   if(!active || !spawned || done || options.scenario!="cover-check" || actors.indexOf(b.unit)<0)return;
   // 固定测试输入：已知目标和持续压力；只验决策执行后的真实位置/射线变化。
   // 视觉确认与情报公平性由独立的 PerceptionModel 测试验证。
   var p:Object=CoverFixture.found.player;
   b.knownX=p.x;b.knownY=p.y;b.lastSeen=t;b.lastHit=t;b.confirmed=true;b.evidence="测试压力";
  }
  private static function finish(ok:Boolean,reason:String):void {
   done=true;if(!ok)TestSave.status="测试失败："+reason;TdfcLog.line("scenario",(ok?"PASS ":"FAIL ")+reason);TdfcRuntime.saveReport();TdfcRuntime.captureReport();TdfcLog.flush();
   try{var f:File=new File(File.applicationDirectory.resolvePath("tdfc-test-result.json").nativePath);var fs:FileStream=new FileStream();fs.open(f,FileMode.WRITE);fs.writeUTFBytes(JSON.stringify({pass:ok,reason:reason,observed:seen,save:TestSave.evidence,version:Config.VER,run:options.run}));fs.close();}catch(e:Error){TdfcLog.line("scenario-error",e.message);}
   if(options.exit!==false)NativeApplication.nativeApplication.exit(ok?0:1);
  }
  private static function writeStatus(w:*,frame:int):void {
   try{var fs:FileStream=new FileStream();fs.open(new File(File.applicationDirectory.resolvePath("tdfc-test-status.json").nativePath),FileMode.WRITE);fs.writeUTFBytes(JSON.stringify({frame:frame,tick:TdfcRuntime.tick,status:TdfcRuntime.status,started:started,spawned:spawned,save:TestSave.evidence,allLandsLoaded:GameBridge.get(w,"allLandsLoaded"),loadLog:GameBridge.get(w,"load_log",""),logging:TdfcLog.status,run:options.run}));fs.close();}catch(e:Error){}
  }
 }
}
