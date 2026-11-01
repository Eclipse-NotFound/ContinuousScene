package {
 /** 只作决定，不读取游戏类，也不直接写入游戏对象。 */
 public class TacticalMind {
  public static function endSuppression(b:BrainState,t:int):void {
   b.suppressEnd=t; b.suppressCooldown=t+Config.SUPPRESS_COOLDOWN;
  }
  public static function decide(b:BrainState,e:Object,t:int):Object {
   var s:Object=b.sample,p:Object=b.profile;
   if(!p.supported) return action("vanilla",p.excluded,s.x,s.y);
   var known:Boolean=t-b.lastSeen<p.memory;
   var hp:Number=s.hp/Math.max(1,s.maxhp);
   if(b.action.kind=="suppress") {
    if(t<b.until && known && e.slotOwned && s.reload<=0 && hp>=0.3) return action("suppress",b.confirmed ? "掩护同伴·目击目标" : "掩护同伴·最后报告",b.knownX,b.knownY);
    endSuppression(b,t); b.until=0;
   }
   if(b.action.kind=="dodge" && t<b.until) return b.action;
   if(e.threat && t>=b.dodgeCooldown && t>=b.stuckUntil && !s.fixed) {
    b.dodgeCooldown=t+45; b.until=t+8;
    return action("dodge","慢弹接近",s.x+(s.x>=e.threat.x ? 65 : -65),s.y);
   }
   if(!known) { b.cover=null; return action("idle","没有可靠目标信息",s.x,s.y); }
   if(hp<p.retreatRatio && t-b.lastHit<120 && t>=b.retreatCooldown && !s.fixed) {
    if(b.action.kind!="retreat") { b.until=t+120; b.retreatCooldown=t+240; }
    if(e.distance>110 && e.retreat) return action("retreat","低血且近期受伤",e.retreat.x,e.retreat.y);
   }
   if(b.action.kind=="retreat" && t<b.until && e.distance>110 && t>=b.stuckUntil) return b.action;
   if(e.squad.coverMate && e.squad.canSuppress && s.gun && s.reload<=0 && hp>=0.5 && p.tier>=2
    && t>=b.suppressCooldown && b.evidence!="听觉区域" && t-b.lastSeen<90) {
    b.until=t+p.suppressDuration;
    return action("suppress","同伴换弹或负伤，需要掩护",b.knownX,b.knownY);
   }
   if(b.cover && (b.action.kind=="cover" || b.action.kind=="hide" || b.action.kind=="peek")) {
    if(t>=b.until || e.distance<110 || t<b.stuckUntil || e.coverSafe===false) {
     b.rejected=t>=b.until?"掩体承诺到期":e.distance<110?"敌人逼近掩体":t<b.stuckUntil?"掩体移动受阻":"掩体不再遮挡目标";
     b.cover=null; b.coverCooldown=t+90;
    }
    else if(Math.abs(s.x-b.cover.x)>4 && b.action.kind=="cover") return action("cover","前往已选掩体",b.cover.x,b.cover.y);
    else {
     if(b.action.kind=="cover")b.peekAt=t+45;
     if(!b.peek && t>=b.peekAt && s.reload<=0 && !isNaN(b.cover.peekX)){b.peek=true;b.peekAt=0;}
     if(b.peek) {
      // 射击窗口从真正走到探头位置后开始，路程不吃掉射击时间。
      if(Math.abs(s.x-b.cover.peekX)<=4 && b.peekAt==0)b.peekAt=t+18;
      if(s.reload>0 || b.peekAt>0 && t>=b.peekAt){b.peek=false;b.peekAt=t+45;}
      else return action("peek","前往射界，抵达后短时开火",b.cover.peekX,b.cover.y);
     }
     return action("hide",s.reload>0 ? "掩体内换弹" : "掩体内等待射击窗口",b.cover.x,b.cover.y);
    }
   }
   if(!b.confirmed) return action("search",b.evidence+"；搜索最后位置",b.knownX,b.knownY);
   if(t-b.decisionAt<p.reaction && b.action.kind!="idle") return b.action;
   b.decisionAt=t;
   var pressured:Boolean=t-b.lastHit<60 || e.aimed || s.reload>0;
   if(s.role!="melee" && pressured && t>=b.coverCooldown && t>=b.stuckUntil && e.covers.length>0
     && (p.aggression<0.9 || hp<0.6 || s.reload>0) && (p.tier>=2 || hp<0.4 || s.reload>0)) {
    b.cover=chooseCover(e.covers,p); b.peek=false; b.peekAt=t+45; b.until=t+210;
    return action("cover","受压，找到可达遮挡点",b.cover.x,b.cover.y);
   }
   if(e.aimed && t>=b.dodgeCooldown && t>=b.stuckUntil && !s.fixed && e.distance<420 && e.distance>90) {
    b.dodgeCooldown=t+60; b.until=t+7;
    return action("dodge","确认被瞄准，短促避线",s.x+(s.x>=b.knownX ? 65 : -65),s.y);
   }
   if(e.squad.nearest<65 && s.role!="melee" && e.distance>130 && t>=b.stuckUntil)
    return action("space","与同伴过近，留出射界",s.x+(s.x>=e.squad.nearX ? 60 : -60),s.y);
   var wanted:Number=s.role=="melee" ? 45 : s.role=="shotgun" ? 150 : p.family=="ranger" ? 320 : 200;
   if(e.distance>wanted+70 && (p.aggression>=0.6 || s.role=="melee" || s.role=="shotgun" || e.distance>520))
    return action("advance",p.style+"，接近有效射程",b.knownX+(s.x>b.knownX ? wanted : -wanted),b.knownY);
   return action("hold",s.reload>0 ? "换弹中" : p.style+"，保持射击窗口",b.knownX,b.knownY);
  }
  public static function action(k:String,r:String,x:Number,y:Number):Object { return {kind:k,reason:r,x:x,y:y}; }
  public static function chooseCover(candidates:Array,p:Object):Object {
   var best:Object=candidates[0],score:Number=1e9;
   for(var i:int=0;i<Math.min(candidates.length,p.coverOptions);i++) {
    var c:Object=candidates[i];
    var value:Number=c.score+(p.tier>=3 && isNaN(c.peekX)?180:0);
    if(value<score){score=value;best=c;}
   }
   return best;
  }
 }
}
