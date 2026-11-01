package {
 public class ActionExecutor {
  public static function yieldToNative(b:BrainState):Boolean {
   if(GameBridge.num(b.unit,"levit")<=0)return false;
   restore(b);
   b.order=null;b.cover=null;b.coverCandidates=[];b.until=0;b.decisionAt=-100000;b.stuckUntil=0;b.peek=false;b.peekAt=0;
   b.action=TacticalMind.action("controlled","被念力抓取，暂停战术指令",GameBridge.num(b.unit,"X"),GameBridge.num(b.unit,"Y"));
   b.result="移动与开火已交还原版";b.effect="";
   return true;
  }
  public static function restore(b:BrainState):void {
   try {
    commitGround(b,false);
    if(!isNaN(b.skillWritten) && Math.abs(GameBridge.num(b.unit,"weaponSkill")-b.skillWritten)<0.0001) b.unit.weaponSkill=b.baseSkill;
    if(b.viewWritten) { b.unit.vKonus=b.viewCone; b.unit.vAngle=b.viewAngle; b.unit.overLook=b.viewOver; }
   } catch(e:Error) {} b.skillWritten=NaN; b.viewWritten=false;
  }
  public static function commitGround(b:BrainState,on:Boolean):void {
   if(on) {
    if(!b.groundCommitted){b.jumpBase=GameBridge.num(b.unit,"jumpdy",15);b.climbBase=GameBridge.get(b.unit,"mostLaz",true);b.groundCommitted=true;}
    b.unit.jumpdy=0;b.unit.mostLaz=false;b.unit.isLaz=0;
   } else if(b.groundCommitted) {
    if(GameBridge.num(b.unit,"jumpdy")==0)b.unit.jumpdy=b.jumpBase;
    if(GameBridge.get(b.unit,"mostLaz")===false)b.unit.mostLaz=b.climbBase;
    b.groundCommitted=false;
   }
  }
  public static function assess(b:BrainState,t:int):void {
   if(GameBridge.num(b.unit,"levit")>0)return;
   if(!b.order || !b.previous) return;
   var s:Object=b.sample,pr:Object=b.previous;
   var dx:Number=s.x-b.orderX,dy:Number=s.y-b.orderY;
   var moved:Boolean=dx*dx+dy*dy>64;
   var shot:Boolean=s.weapon===pr.weapon && (s.ammo>=0 && pr.ammo>=0 && s.ammo<pr.ammo || s.shots>pr.shots);
   if(shot) { b.effect="观察到发射信号"; b.result="发射证据已观测，未推断命中"; }
   if(b.order.move) {
    var oldD:Number=Math.abs(b.order.x-b.orderX),newD:Number=Math.abs(b.order.x-s.x);
    var tolerance:Number=["cover","peek","hide"].indexOf(b.order.kind)>=0?4:12;
    if(newD<=tolerance){b.result="已到达目标附近";b.orderAt=t;b.orderX=s.x;b.orderY=s.y;}
    else if(moved && newD<oldD-4) b.result=t-b.lastHit<10 ? "位置接近目标；近期受击，归因不确定" : "位置向目标改善";
    else if(t-b.orderAt>35) { b.result="未见有效位移，已放弃该位置"; b.stuckUntil=t+90; b.cover=null; b.until=0; }
   }
  }
  public static function apply(b:BrainState,g:Object,loc:*,t:int):void {
   if(!b.profile.supported || yieldToNative(b)) return;
   var s:Object=b.sample,a:Object=b.action;
   try {
    // 原版 control() 在下一帧物理移动前会重新发出跳跃/爬梯指令。
    // 短程地面掩体承诺期间暂时关闭这两项能力，结束/换图即归还。
    commitGround(b,["cover","hide","peek"].indexOf(a.kind)>=0 && !s.fly && !s.water && Math.abs(s.y-a.y)<16);
    if(!b.viewWritten) { b.viewCone=GameBridge.num(b.unit,"vKonus"); b.viewAngle=GameBridge.num(b.unit,"vAngle"); b.viewOver=GameBridge.get(b.unit,"overLook",false); b.viewWritten=true; }
    b.unit.overLook=false; b.unit.vKonus=Config.VISION_CONE; b.unit.vAngle=s.face>0 ? 0 : Math.PI;
    if(isNaN(b.baseSkill)) b.baseSkill=s.weaponSkill;
    var move:Boolean=["advance","retreat","cover","peek","hide","search","space","dodge"].indexOf(a.kind)>=0;
    if(!b.order || b.order.kind!=a.kind || Math.abs(b.order.x-a.x)>24) {
     b.order={kind:a.kind,x:a.x,y:a.y,move:move}; b.orderAt=t; b.orderX=s.x; b.orderY=s.y; b.result="已下令，等待结果"; b.effect="";
    }
    // 独占写入点：移动不再拉动枪口；只沿通过体积/地面检查的短路段推进。
    if(move && t>=b.stuckUntil && !s.fixed) {
     var d:Number=a.x-s.x,dir:Number=d<0 ? -1 : 1;
     var arrive:Number=["cover","peek","hide"].indexOf(a.kind)>=0?4:12;
     if(Math.abs(d)>arrive && GameBridge.walkable(loc,s,s.x+dir*Math.min(24,Math.abs(d)),s.y)) {
      b.unit.dx=dir*Math.max(1,Math.min(s.speed,a.kind=="dodge" ? 7 : 5));
      if(a.kind=="dodge" && b.orderAt==t && s.ground && b.confirmed && Math.abs(g.cy-s.cy)<40) b.unit.dy=-GameBridge.num(b.unit,"jumpdy",12)*0.6;
      if(a.kind=="dodge" && (s.fly || s.water)) b.unit.dy=(s.cy>=g.cy ? 1 : -1)*Math.min(s.speed,4);
     } else if(Math.abs(d)<=arrive) { b.unit.dx=0; b.result="已到达目标附近"; }
     else { b.result="路径阻挡，未强推"; b.stuckUntil=t+45; b.cover=null; b.until=0; }
    }
    if(b.confirmed) {
     // Perception owns initial exposure and recent visual recognition. Do not
     // discard a legitimate reacquisition just because exposure decayed in cover.
     b.unit.setCel(g.unit);
     b.unit.celX=g.cx; b.unit.celY=g.cy;
    } else {
     if(!b.observed && GameBridge.get(b.unit,"celUnit")===g.unit) b.unit.setCel(null,b.knownX,b.knownY);
     if(t-b.lastSeen<b.profile.memory && a.kind=="search" && t%30==b.key%30) b.unit.alarma(b.knownX,b.knownY);
    }
    if(a.kind=="suppress") {
     b.unit.celX=a.x; b.unit.celY=a.y-g.height/2;
     b.skillWritten=b.baseSkill*0.45; b.unit.weaponSkill=b.skillWritten;
     if(s.weapon!=null && s.reload<=0) s.weapon.attack();
    } else {
     b.skillWritten=b.baseSkill*(move ? 0.55 : 1); b.unit.weaponSkill=b.skillWritten;
    }
    if(a.kind=="hide" && !GameBridge.clear(loc,s.x,s.cy,g.cx,g.cy)) b.result="已观察到遮挡";
   } catch(e:Error) { b.faults++; b.rejected=e.errorID+": "+e.message; b.result="执行失败"; TdfcLog.line("error","#"+b.key+" "+b.rejected); }
  }
 }
}
