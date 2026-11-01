package {
 /** 信息年龄和持续确认由真实战术时间驱动；报告不是实时目标引用。 */
 public class PerceptionModel {
  private var pending:Array=[];
  public function PerceptionModel() {}
  public function reset():void { pending=[]; }
  public function observe(b:BrainState,g:Object,sense:Object,t:int):void {
   b.sensing=sense;
   b.observed=sense.visible;
   b.heard=sense.heard;
   if(sense.visible) b.confirm++; else b.confirm=0;
   var recognized:Boolean=t-b.lastVisual<b.profile.memory;
   b.confirmed=sense.visible && (recognized || b.confirm>=b.profile.confirm && g.obs>=g.maxObs);
   if(b.confirmed) {
    b.knownX=g.x; b.knownY=g.y; b.lastSeen=t; b.lastVisual=t; b.evidence="目击";
   } else if(sense.heard && t-b.lastHeard>=60 && t-b.lastSeen>30) {
    // 可复现的有限位置误差；听觉不会获得精确追踪能力。
    var seed:int=(b.key*37+t*13)%181;
    b.knownX=g.x+seed-90; b.knownY=g.y;
    b.lastSeen=t; b.lastHeard=t; b.evidence="听觉区域";
   }
   if(b.previous && b.sample.hp<b.previous.hp) b.lastHit=t;
  }
  public function schedule(all:Array,t:int):void {
   for each(var b:BrainState in all) {
    var hurt:Boolean=b.lastHit==t && t-b.lastSeen<90 && b.evidence!="听觉区域";
    if(!b.profile.supported || (!b.confirmed && !hurt) || t-b.lastReport<Config.REPORT_COOLDOWN) continue;
    b.lastReport=t;
    for each(var r:BrainState in all) {
     if(r===b || !r.profile.supported || r.sample.fraction!=b.sample.fraction) continue;
     var dx:Number=r.sample.x-b.sample.x,dy:Number=r.sample.y-b.sample.y;
     var d:Number=Math.sqrt(dx*dx+dy*dy);
     if(d>Config.REPORT_RANGE) continue;
     pending.push({to:r,source:b,at:t+b.profile.reportDelay+Math.max(1,int(d/Config.REPORT_SPEED)),seen:b.lastSeen,x:b.knownX,y:b.knownY,fraction:b.sample.fraction,hurt:hurt});
    }
   }
  }
  public function deliver(all:Array,t:int):void {
   for(var i:int=pending.length-1;i>=0;i--) {
    var p:Object=pending[i]; if(p.at>t) continue; pending.splice(i,1);
    var b:BrainState=p.to;
    if(all.indexOf(b)<0 || all.indexOf(p.source)<0 || b.sample.fraction!=p.fraction || p.source.sample.fraction!=p.fraction) continue;
    if(b.lastSeen>=p.seen || t-p.seen>b.profile.memory) continue;
    b.knownX=p.x; b.knownY=p.y; b.lastSeen=p.seen; b.evidence=(p.hurt?"同伴受击报告 #":"同伴报告 #")+p.source.key;
   }
  }
 }
}
