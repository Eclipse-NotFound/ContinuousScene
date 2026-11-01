package {
 /** 一名敌人的记忆、当前承诺与可核对结果。 */
 public class BrainState {
  public var key:int;
  public var unit:*;
  public var profile:Object;
  public var sample:Object;
  public var previous:Object;
  public var lastSeen:int=-100000;
  public var lastVisual:int=-100000;
  public var sensing:Object;
  public var knownX:Number=0;
  public var knownY:Number=0;
  public var evidence:String="无";
  public var confirm:int=0;
  public var lastReport:int=-100000;
  public var lastHeard:int=-100000;
  public var lastHit:int=-100000;
  public var observed:Boolean=false;
  public var confirmed:Boolean=false;
  public var heard:Boolean=false;
  public var action:Object={kind:"idle",reason:"等待",x:0,y:0};
  public var until:int=0;
  public var decisionAt:int=-100000;
  public var suppressEnd:int=-100000;
  public var suppressCooldown:int=-100000;
  public var dodgeCooldown:int=-100000;
  public var coverCooldown:int=-100000;
  public var retreatCooldown:int=-100000;
  public var cover:Object;
  public var coverCandidates:Array=[];
  public var coverScanAt:int=-100000;
  public var coverScanX:Number=NaN;
  public var coverTargetX:Number=NaN;
  public var peek:Boolean=false;
  public var peekAt:int=0;
  public var order:Object;
  public var orderAt:int=0;
  public var orderX:Number=0;
  public var orderY:Number=0;
  public var result:String="尚未下令";
  public var effect:String="";
  public var faults:int=0;
  public var rejected:String="";
  public var stuckUntil:int=0;
  public var baseSkill:Number=NaN;
  public var skillWritten:Number=NaN;
  public var viewAngle:Number=NaN;
  public var viewCone:Number=NaN;
  public var viewOver:*;
  public var viewWritten:Boolean=false;
  public var groundCommitted:Boolean=false;
  public var jumpBase:Number=NaN;
  public var climbBase:Boolean=true;
  public function BrainState(n:int,u:*,p:Object) { key=n; unit=u; profile=p; }
 }
}
