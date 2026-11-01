package {
 import flash.display.Stage;
 import flash.events.MouseEvent;
 import flash.events.KeyboardEvent;
 import flash.events.Event;
 /** Read-only input observation. Never sets keys, selects a target or invokes player control. */
 public class GrabDiagnostics {
  public static var summary:String="右键 / Q 后显示结果";
  public static var last:Object=null;
  public static var recent:Array=[];
  private static var world:Function,enabled:Function,pending:Object,eventSeen:Event;
  public static function init(stage:Stage,getWorld:Function,isEnabled:Function):void {
   world=getWorld;enabled=isEnabled;
   stage.addEventListener(MouseEvent.RIGHT_MOUSE_DOWN,begin,true,10000);
   stage.addEventListener(KeyboardEvent.KEY_DOWN,begin,true,10000);
   stage.addEventListener(MouseEvent.RIGHT_MOUSE_DOWN,routed,false,-10000);
   stage.addEventListener(KeyboardEvent.KEY_DOWN,routed,false,-10000);
  }
  private static function relevant(e:Event):Boolean {return !(e is KeyboardEvent) || KeyboardEvent(e).keyCode==81;}
  private static function begin(e:Event):void {
   if(!enabled() || !relevant(e) || eventSeen===e)return;eventSeen=e;
   var w:*=world(),g:*=GameBridge.get(w,"gg"),loc:*=GameBridge.get(w,"loc");if(!g || !loc)return;
   var p:*=GameBridge.get(g,"pers"),o:*=GameBridge.get(loc,"celObj");
   var line:Boolean=true;
   if(o)try{line=loc.isLine(g.X,g.Y-g.scY*.75,o.X,o.Y-o.scY/2);}catch(err:Error){line=false;}
   pending={source:e is KeyboardEvent?"Q":"右键",age:0,routed:false,wasHeld:GameBridge.get(g,"teleObj")!=null,vision:visibility(w),
    pause:GameBridge.pause(w),control:GameBridge.get(g,"ggControl",false),rat:GameBridge.num(g,"rat"),mana:GameBridge.num(g,"mana"),base:GameBridge.get(loc,"base",false),
    target:o?String(GameBridge.get(o,"nazv",GameBridge.get(o,"id","对象"))):"",cls:o?GameBridge.cls(o):"",possible:GameBridge.get(o,"levitPoss",false),
    cursor:GameBridge.num(o,"onCursor"),mass:GameBridge.num(o,"massa"),limit:GameBridge.num(p,"maxTeleMassa"),distance:GameBridge.num(loc,"celDist"),range:GameBridge.num(p,"teleDist"),
    line:line || GameBridge.num(p,"telemaster")>0 && GameBridge.get(loc,"portOn",false)};
  }
  private static function routed(e:Event):void {
   if(!enabled() || !relevant(e))return;
   if(eventSeen!==e)begin(e); // Events dispatched on Stage itself have no ancestor capture phase.
   if(pending && eventSeen===e)pending.routed=true;
  }
  public static function update(w:*):void {
   if(!pending)return;
   if(!enabled()){pending=null;return;}
   if(++pending.age<2)return;
   var held:*=GameBridge.get(GameBridge.get(w,"gg"),"teleObj");
   if(held)summary="已抓取 "+String(GameBridge.get(held,"nazv",GameBridge.get(held,"id","对象")));
   else if(pending.wasHeld && pending.routed)summary="已释放念力对象";
   else summary=reason(pending);
   pending.result=summary;last=pending;pending=null;
   recent.push(last);if(recent.length>12)recent.shift();
   TdfcLog.line("grab",JSON.stringify(last));
  }
  /** Read the public settings callbacks; never change another mod's settings. */
  public static function visibility(w:*):Object {
   var result:Object={known:false};
   try {
    var main:*=GameBridge.get(w,"main"),carrier:*=main?main.getChildByName("ModSettingsCarrier"):null;
    var api:*=GameBridge.get(carrier,"modAPI");if(!api)return result;
    for each(var page:Object in api.getPages())if(page.modId=="realisticvision") {
     for each(var item:Object in page.items) {
      if(item.key=="enabled")result.enabled=Boolean(item.get());
      else if(item.key=="mode"){result.mode=int(item.get());result.modeName=["原版","仿原版","平滑阴影"][result.mode];}
     }
     result.known=("enabled" in result) && ("mode" in result);break;
    }
   }catch(err:Error){result.known=false;}
   return result;
  }
  public static function reason(s:Object):String {
   if(s.pause)return "暂停中："+s.pause;
   if(!s.routed)return "输入被界面或其他模组拦截"+(s.vision && s.vision.known?"（视野："+(s.vision.enabled?s.vision.modeName:"关闭")+"）":"");
   if(s.base)return "基地内不允许抓取";
   if(!s.control || s.rat)return "当前角色状态不能抓取";
   if(s.mana<200)return "魔力不足（起手需 200）";
   if(!s.target)return "未抓取；鼠标下没有锁定对象";
   if(!s.possible)return "当前目标不能抓取："+s.target;
   if(s.mass>s.limit)return "目标超过念力重量上限";
   if(s.distance>s.range)return "目标超出念力距离";
   if(!s.line)return "目标被地形遮挡";
   return "未抓取；保存诊断查看输入与目标";
  }
 }
}
