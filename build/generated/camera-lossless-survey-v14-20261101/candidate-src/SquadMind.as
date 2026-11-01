package {
 /** 压制占用和冷却属于实际友军队伍，角色交换也不能绕过。 */
 public class SquadMind {
  private var slots:Object={};
  public function SquadMind() {}
  public function reset():void { slots={}; }
  private function slot(fr:int):Object { if(!slots[fr]) slots[fr]={owner:0,until:0,cooldown:0}; return slots[fr]; }
  public function frame(all:Array,t:int):void {
   for(var fr:String in slots) {
    var s:Object=slots[fr]; if(!s.owner) continue;
    var owner:BrainState=null;
    for each(var b:BrainState in all) if(b.key==s.owner && b.sample.fraction==int(fr)) owner=b;
    if(owner==null || t>=s.until || owner.action.kind!="suppress" || owner.sample.reload>0 || owner.sample.hp/Math.max(1,owner.sample.maxhp)<0.3)
     release(int(fr),s.owner,t);
   }
  }
  public function available(fr:int,t:int):Boolean { var s:Object=slot(fr); return !s.owner && t>=s.cooldown; }
  public function claim(fr:int,key:int,t:int,duration:int):Boolean {
   if(!available(fr,t)) return false;
   var s:Object=slot(fr); s.owner=key; s.until=t+duration; return true;
  }
  public function release(fr:int,key:int,t:int):void {
   var s:Object=slot(fr); if(s.owner!=key) return;
   s.owner=0; s.until=0; s.cooldown=t+Config.SUPPRESS_COOLDOWN;
  }
  public function owns(fr:int,key:int):Boolean { return slot(fr).owner==key; }
  public function context(b:BrainState,all:Array,t:int):Object {
   var mate:Boolean=false,nearest:Number=1e9,nearX:Number=0,n:int=0;
   for each(var a:BrainState in all) {
    if(a===b || a.sample.fraction!=b.sample.fraction || !a.profile.supported) continue;
    var dx:Number=a.sample.x-b.sample.x,dy:Number=a.sample.y-b.sample.y,d:Number=Math.sqrt(dx*dx+dy*dy);
    if(d>650) continue; n++;
    if(d<nearest) { nearest=d; nearX=a.sample.x; }
    if(a.sample.reload>0 || a.sample.hp/Math.max(1,a.sample.maxhp)<0.3 && t-a.lastHit<90) mate=true;
   }
   return {count:n,coverMate:mate,nearest:nearest,nearX:nearX,canSuppress:available(b.sample.fraction,t),side:b.key%2==0 ? 1 : -1};
  }
 }
}
