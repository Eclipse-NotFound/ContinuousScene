package {
 import flash.display.DisplayObjectContainer;
 import flash.display.Sprite;
 import flash.events.MouseEvent;
 import flash.events.KeyboardEvent;
 import flash.events.Event;
 import flash.system.ApplicationDomain;
 /** Isolated scenario only: real stage right-button event -> native player control -> held object. */
 public class TelekinesisFixture {
  private static var uiActors:Array=[];
  public static function prepareUI(w:*):void {
   var g:*=w.loc.gg,loc:*=w.loc,c:Class=ApplicationDomain.currentDomain.getDefinition("fe.unit.UnitRaider") as Class;
   var u:*=new c("1",1,null,{weap:"autor",tr:1});u.putLoc(loc,g.X+110,g.Y);loc.addObj(u);loc.units.push(u);u.maxhp=5000;u.hp=5000;
   u.setPos(openPosition(loc,g,u),g.Y);
   if(u.currentWeapon)u.currentWeapon.damage=0;uiActors.push({unit:u,x:u.X,y:u.Y,held:false});
   c=ApplicationDomain.currentDomain.getDefinition("fe.unit.Mine") as Class;
   u=new c("mine",1);u.putLoc(loc,g.X-100,g.Y);u.setVis(true);u.sens=0;loc.addObj(u);loc.units.push(u);
   u.setPos(openPosition(loc,g,u,true),g.Y);uiActors.push({unit:u,x:u.X,y:u.Y,held:false});
   TdfcLog.line("scenario","telekinesis UI ready: targets held at spawn positions only until first grab");TdfcLog.flush();
  }
  public static function sampleUI(w:*,frame:int):void {
   for each(var a:Object in uiActors) {
    var u:*=a.unit;if(u.loc!==w.loc)continue;
    if(u.levit>0)a.held=true;
    if(!a.held){u.setPos(a.x,a.y);u.dx=0;u.dy=0;}
   }
  }
  private static function openPosition(loc:*,g:*,u:*,left:Boolean=false):Number {
   var offsets:Array=left?[-180,-120,-240,240,180,120]:[120,-120,180,-180,240,-240];
   for each(var offset:int in offsets) {
    var xx:Number=g.X+offset,yy:Number=g.Y-u.scY/2,clear:Boolean=loc.isLine(g.X,g.Y-g.scY*.75,xx,yy),obj:*=loc.firstObj;
    if(!GameBridge.standable(loc,xx,g.Y,GameBridge.snapshot(u)))continue;
    while(obj && clear) {
     if(obj!==u && obj!==g && GameBridge.num(obj,"prior")>=u.prior && xx>GameBridge.num(obj,"X1") && xx<GameBridge.num(obj,"X2") && yy>GameBridge.num(obj,"Y1") && yy<GameBridge.num(obj,"Y2"))clear=false;
     obj=GameBridge.get(obj,"nobj");
    }
    if(clear)return xx;
   }
   throw new Error("No clear native pick location for "+GameBridge.cls(u));
  }
  private static function blockedPosition(loc:*,g:*,u:*):Object {
   for(var radius:int=80;radius<=600;radius+=40)for(var yy:int=-160;yy<=160;yy+=40)for each(var direction:int in [-1,1]) {
    var x:Number=g.X+radius*direction,y:Number=g.Y+yy;
    if(!GameBridge.standable(loc,x,y,GameBridge.snapshot(u)))continue;
    if(loc.isLine(g.X,g.Y-g.scY*.75,x,y-u.scY/2))continue;
    var obj:*=loc.firstObj,clear:Boolean=true;
    while(obj && clear) {
     if(obj!==u && obj!==g && GameBridge.num(obj,"prior")>=u.prior && x>GameBridge.num(obj,"X1") && x<GameBridge.num(obj,"X2") && y-u.scY/2>GameBridge.num(obj,"Y1") && y-u.scY/2<GameBridge.num(obj,"Y2"))clear=false;
     obj=GameBridge.get(obj,"nobj");
    }
    if(clear)return {x:x,y:y};
   }
   return null;
  }
  public static function run(w:*):Object {
   var result:Object={pass:true,checks:[]},g:*=w.loc.gg,loc:*=w.loc;
   result.player={level:w.pers.level,mana:g.mana,maxTeleMassa:w.pers.maxTeleMassa,teleDist:w.pers.teleDist,base:loc.base,rat:g.rat,control:g.ggControl,black:w.black,telemaster:w.pers.telemaster,portOn:loc.portOn};
   result.vision=GrabDiagnostics.visibility(w);
   var host:DisplayObjectContainer=w.swfStage;
   // A child target exercises Stage capture AND bubble listeners, as real inputs do.
   var input:Sprite=new Sprite();host.addChild(input);
   var routed:Boolean=false;
   var route:Function=function(e:Event):void {routed=true;};
   host.addEventListener(MouseEvent.RIGHT_MOUSE_DOWN,route,false,-20000);
   host.addEventListener(KeyboardEvent.KEY_DOWN,route,false,-20000);
   try {for each(var name:String in ["fe.unit.UnitAlicorn","fe.unit.UnitRaider","fe.unit.Mine"]) {
    var c:Class=ApplicationDomain.currentDomain.getDefinition(name) as Class;
    var u:*=name=="fe.unit.Mine"?new c("mine",1):name=="fe.unit.UnitAlicorn"?new c("3",31):new c("1",1,null,{weap:"autor",tr:1});
    u.putLoc(loc,g.X+35,g.Y);loc.addObj(u);loc.units.push(u);
    if(name=="fe.unit.Mine")u.setVis(true); // A mine must have been detected before native telekinesis permits it.
    var openX:Number=openPosition(loc,g,u);
    for each(var debug:Boolean in [false,true]) {for each(var key:String in ["right","Q"]) {
     TdfcRuntime.setObservation(debug,w);
     g.dropTeleObj();g.ctr.clearAll();g.control();
     u.setPos(openX,g.Y);u.dx=0;u.dy=0;
     w.celX=u.X;w.celY=u.Y-u.scY/2;loc.celObj=null;
     loc.step(); // Native object cursor checks and Location selection; do not inject celObj/onCursor.
     var check:Object={target:name,source:key,debug:debug,levitPoss:u.levitPoss,mass:u.massa,line:loc.isLine(g.X,g.Y-g.scY*.75,u.X,u.Y-u.scY/2),distance:loc.celDist};
     check.selected=GameBridge.cls(loc.celObj);check.isVis=u.isVis;check.onCursor=u.onCursor;
     check.bounds=[u.X1,u.Y1,u.X2,u.Y2];check.mouse=[w.celX,w.celY];
     routed=false;
     if(key=="Q")input.dispatchEvent(new KeyboardEvent(KeyboardEvent.KEY_DOWN,true,false,113,81));
     else input.dispatchEvent(new MouseEvent(MouseEvent.RIGHT_MOUSE_DOWN,true));
     check.routed=routed;
     check.keyTele=g.ctr.keyTele;check.keyAction=g.ctr.keyAction;
     g.control();check.held=g.teleObj===u;check.levit=u.levit;
     if(name=="fe.unit.UnitRaider" && check.held) {
      var brain:BrainState=new BrainState(900,u,EnemyProfile.make(GameBridge.snapshot(u)));
      brain.sample=GameBridge.snapshot(u);brain.action={kind:"suppress",x:g.X,y:g.Y};brain.baseSkill=u.weaponSkill;
      var skill:Number=u.weaponSkill,view:Number=u.vKonus;
      ActionExecutor.apply(brain,GameBridge.snapshot(g),loc,100);
      check.yielded=u.weaponSkill==skill && u.vKonus==view && !brain.viewWritten;
      if(!check.yielded)result.pass=false;ActionExecutor.restore(brain);
     }
     if(key=="Q")input.dispatchEvent(new KeyboardEvent(KeyboardEvent.KEY_UP,true,false,113,81));
     else input.dispatchEvent(new MouseEvent(MouseEvent.RIGHT_MOUSE_UP,true));
     g.control();check.releasedInput=!g.ctr.keyTele;
     result.checks.push(check);if(!check.held || !check.releasedInput)result.pass=false;
     g.dropTeleObj();
    }}
    if(name=="fe.unit.UnitAlicorn") {
     var blocked:Object=blockedPosition(loc,g,u);result.occlusion=[];
     // The late-game save may legitimately bypass LOS with telemaster + portOn.
     // Disable that perk only for this isolated native-LOS control, then restore it.
     var savedTelemaster:int=g.pers.telemaster;
     try {g.pers.telemaster=0;if(blocked)for each(key in ["right","Q"]) {
      g.dropTeleObj();g.ctr.clearAll();g.control();u.setPos(blocked.x,blocked.y);u.dx=0;u.dy=0;
      w.celX=u.X;w.celY=u.Y-u.scY/2;loc.celObj=null;loc.step();
      check={source:key,selected:GameBridge.cls(loc.celObj),telemaster:g.pers.telemaster,line:loc.isLine(g.X,g.Y-g.scY*.75,u.X,u.Y-u.scY/2)};routed=false;
      if(key=="Q")input.dispatchEvent(new KeyboardEvent(KeyboardEvent.KEY_DOWN,true,false,113,81));
      else input.dispatchEvent(new MouseEvent(MouseEvent.RIGHT_MOUSE_DOWN,true));
      check.routed=routed;check.keyTele=g.ctr.keyTele;g.control();check.heldAny=g.teleObj!=null;check.heldTarget=GameBridge.cls(g.teleObj);
      if(check.line || check.heldAny)result.pass=false;result.occlusion.push(check);
      if(key=="Q")input.dispatchEvent(new KeyboardEvent(KeyboardEvent.KEY_UP,true,false,113,81));
      else input.dispatchEvent(new MouseEvent(MouseEvent.RIGHT_MOUSE_UP,true));
      g.control();g.dropTeleObj();
     }} finally {g.pers.telemaster=savedTelemaster;}
    }
    u.exterminate();
   }} finally {
    host.removeEventListener(MouseEvent.RIGHT_MOUSE_DOWN,route);
    host.removeEventListener(KeyboardEvent.KEY_DOWN,route);
    host.removeChild(input);
   }
   return result;
  }
 }
}
