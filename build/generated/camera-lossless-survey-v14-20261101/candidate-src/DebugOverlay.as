package {
   import modlocales.tactics.TDFCLocale;
 import flash.display.Sprite;
 import flash.display.DisplayObjectContainer;
 import flash.display.DisplayObject;
 import flash.text.TextField;
 import flash.text.TextFormat;
 import flash.events.MouseEvent;
 import flash.events.Event;
 import flash.geom.Point;
 import flash.display.BitmapData;
 import flash.filesystem.File;
 import flash.filesystem.FileMode;
 import flash.filesystem.FileStream;
 import flash.utils.ByteArray;
 public class DebugOverlay {
  public var enabled:Boolean=false;
  private var root:Sprite=new Sprite(),marks:Sprite=new Sprite(),panel:Sprite=new Sprite();
  private var toggle:Sprite;
  private var toggleText:TextField,detail:TextField;
  private var labels:Object={};
  private var selected:int=0;
  private var parent:DisplayObjectContainer;
  private var report:Function;
  private var draggingPanel:Boolean=false;
  private static const PANEL_HEIGHT:int=430;
  public function get dragging():Boolean {return draggingPanel;}
  public function DebugOverlay(host:DisplayObjectContainer,onReport:Function) {
   parent=host;report=onReport;root.name="TDFC_DebugRoot";root.mouseEnabled=false;
   host.addChild(root);root.addChild(marks);marks.mouseEnabled=false;
   toggle=button("TDFC · 观察",0,0,function(e:MouseEvent):void {enabled=!enabled;});
   toggleText=toggle.getChildAt(0) as TextField;root.addChild(toggle);root.addChild(panel);panel.x=Math.max(12,host.stage.stageWidth-352);panel.y=120;
   panel.graphics.beginFill(0x101c27,0.94);panel.graphics.drawRoundRect(0,0,340,PANEL_HEIGHT,10);panel.graphics.endFill();
   var grip:Sprite=button("TDFC 调试（拖动）",6,5,null,205);grip.name="TDFC_DragGrip";panel.addChild(grip);
   grip.addEventListener(MouseEvent.MOUSE_DOWN,function(e:MouseEvent):void {draggingPanel=true;panel.startDrag();e.stopImmediatePropagation();});
   // Observe release before a child can consume it; leaving the window also ends dragging.
   host.stage.addEventListener(MouseEvent.MOUSE_UP,endDrag,true);
   host.stage.addEventListener(MouseEvent.MOUSE_UP,endDrag);
   host.stage.addEventListener(Event.MOUSE_LEAVE,endDrag);
   host.stage.addEventListener(Event.DEACTIVATE,endDrag);
   panel.addChild(button("保存诊断",225,5,function(e:MouseEvent):void {report();}));
   detail=text(326,PANEL_HEIGHT-53,12);detail.x=7;detail.y=39;panel.addChild(detail);panel.visible=false;
  }
  private function endDrag(e:Event=null):void {if(draggingPanel){panel.stopDrag();draggingPanel=false;}}
  private function text(w:int,h:int,size:int=12):TextField {
   var t:TextField=new TextField();t.width=w;t.height=h;t.defaultTextFormat=new TextFormat("Microsoft YaHei",size,0xe5edf5);t.multiline=true;t.wordWrap=true;t.selectable=false;t.mouseEnabled=false;return t;
  }
  private function button(s:String,x:int,y:int,fn:Function,width:int=108):Sprite {
   var b:Sprite=new Sprite();b.x=x;b.y=y;b.buttonMode=true;b.mouseChildren=false;
   var t:TextField=text(width,30);TDFCLocale.bind(t,s,true);t.x=6;t.y=4;b.addChild(t);
   b.graphics.beginFill(0x243b50,0.96);b.graphics.drawRoundRect(0,0,t.width,30,6);b.graphics.endFill();
   b.addEventListener(MouseEvent.MOUSE_DOWN,function(e:MouseEvent):void {e.stopPropagation();});
   // Releases must reach native controls even if a press began outside the overlay.
   b.addEventListener(MouseEvent.CLICK,function(e:MouseEvent):void {e.stopPropagation();if(fn!=null)fn(e);});return b;
  }
  private function mark(key:int):Sprite {
   if(labels[key])return labels[key];var k:int=key;
   var b:Sprite=button("",0,0,function(e:MouseEvent):void {selected=k;});
   (b.getChildAt(0) as TextField).width=230;(b.getChildAt(0) as TextField).height=52;
   b.graphics.clear();b.graphics.beginFill(0x142230,0.85);b.graphics.drawRoundRect(0,0,230,52,6);b.graphics.endFill();
   marks.addChild(b);labels[key]=b;return b;
  }
  public function update(world:*,all:Array,status:String,tick:int,cost:Number,logStatus:String):void {
   if(!parent.stage)return;
   if(parent.getChildIndex(root)!=parent.numChildren-1)parent.setChildIndex(root,parent.numChildren-1);
   toggle.x=parent.stage.stageWidth-120;toggle.y=12;
   TDFCLocale.bind(toggleText,"TDFC "+(enabled?"观察中":status=="运行"?"运行":"状态"),true);
   panel.visible=marks.visible=enabled;if(!enabled){endDrag();return;}
   panel.x=Math.max(0,Math.min(parent.stage.stageWidth-340,panel.x));panel.y=Math.max(0,Math.min(parent.stage.stageHeight-PANEL_HEIGHT,panel.y));
   marks.graphics.clear();var alive:Object={};var count:int=0;var chosen:BrainState;
   var visual:DisplayObject=GameBridge.get(world,"visual") as DisplayObject;
   var loc:*=GameBridge.get(world,"loc"),player:*=GameBridge.get(loc,"gg");
   var occupied:Array=[];
   if(visual)for each(var b:BrainState in all) {
    var s:Object=b.sample;if(!s)continue;
    var p:Point=root.globalToLocal(visual.localToGlobal(new Point(s.x,s.y-s.height)));
    var foot:Point=root.globalToLocal(visual.localToGlobal(new Point(s.x,s.y)));
    if(foot.x< -s.width || p.x>parent.stage.stageWidth+s.width || foot.y<0 || p.y>parent.stage.stageHeight)continue;
    count++;alive[b.key]=true;
    if(selected==0)selected=b.key;
    var label:Sprite=mark(b.key);label.visible=true;placeLabel(label,p,occupied);
    occupied.push({x:label.x,y:label.y});
    var blocked:Boolean=player!=null && !GameBridge.clear(loc,s.x,s.cy,GameBridge.num(player,"X"),GameBridge.num(player,"Y")-20);
    label.alpha=blocked?0.65:0.96;
    marks.graphics.lineStyle(1,blocked?0x718397:0x6fe0e5,0.5);marks.graphics.moveTo(foot.x,foot.y);marks.graphics.lineTo(label.x+4,label.y+48);
    var tx:TextField=label.getChildAt(0) as TextField;
    TDFCLocale.bind(tx,"#"+b.key+" "+s.id+" · "+(b.profile.supported?"思维 "+b.profile.tier:"原版")+" · "+int(s.hp)+" HP\n"+(blocked?"[遮挡] ":"")+name(b.action.kind)+" | "+b.result,true);
    if(b.key==selected) {
     chosen=b;marks.graphics.lineStyle(1,0x6fe0e5,0.8);marks.graphics.drawRect(p.x-s.width/2,p.y,s.width,foot.y-p.y);
     var gun:*=GameBridge.get(b.unit,"currentWeapon");
     if(gun!=null) {
      var gx:Number=GameBridge.num(gun,"X"),gy:Number=GameBridge.num(gun,"Y"),rot:Number=GameBridge.num(gun,"rot");
      var muzzle:Point=root.globalToLocal(visual.localToGlobal(new Point(gx,gy)));
      var ray:Point=root.globalToLocal(visual.localToGlobal(new Point(gx+Math.cos(rot)*200,gy+Math.sin(rot)*200)));
      var aim:Point=root.globalToLocal(visual.localToGlobal(new Point(GameBridge.num(b.unit,"celX"),GameBridge.num(b.unit,"celY"))));
      marks.graphics.lineStyle(2,0xffb454,0.95);marks.graphics.moveTo(muzzle.x,muzzle.y);marks.graphics.lineTo(ray.x,ray.y);marks.graphics.drawCircle(aim.x,aim.y,6);
     }
     marks.graphics.lineStyle(1,0x6fe0e5,0.8);
     if(b.action && b.profile.supported) {var goal:Point=root.globalToLocal(visual.localToGlobal(new Point(b.action.x,b.action.y)));marks.graphics.moveTo(foot.x,foot.y);marks.graphics.lineTo(goal.x,goal.y);marks.graphics.drawCircle(goal.x,goal.y,5);}
     if(b.profile.supported) {
      var eye:Point=root.globalToLocal(visual.localToGlobal(new Point(s.x,s.cy))),face:Number=s.face>0?0:Math.PI;
      for each(var ang:Number in [face-Config.VISION_CONE/2,face+Config.VISION_CONE/2]) {var edge:Point=root.globalToLocal(visual.localToGlobal(new Point(s.x+Math.cos(ang)*350,s.cy+Math.sin(ang)*350)));marks.graphics.moveTo(eye.x,eye.y);marks.graphics.lineTo(edge.x,edge.y);}
     }
    }
   }
   for(var key:String in labels)if(!alive[key]){marks.removeChild(labels[key]);delete labels[key];}
   var head:String="v"+Config.VER+" · "+status+" · 战术帧 "+tick+"\n屏幕敌人 "+count+" / 房间记录 "+all.length+" · 更新 "+cost.toFixed(1)+" ms\n日志："+logStatus+"\n";
   head+="念力："+GrabDiagnostics.summary+"\n";
   if(chosen)head+="\n#"+chosen.key+" "+chosen.profile.style+(chosen.profile.supported?"\n思维 "+chosen.profile.tier+" · "+chosen.profile.tierName+"\n"+chosen.profile.source+"\n情报："+chosen.evidence+(chosen.evidence=="无"?"":"（"+Math.max(0,tick-chosen.lastSeen)+" 帧前）"):"\nTDFC 不接管该兵种")+"\n行动："+name(chosen.action.kind)+"\n原因："+chosen.action.reason+"\n结果："+chosen.result+(chosen.rejected?"\n限制："+chosen.rejected:"");
   else head+="\n点击敌人标签查看原因、目标点与视野方向。\n淡色标签＝玩家与敌人之间有墙体遮挡。\n视野线示意方向，不代表最终察觉距离。\n所有墙后信息仅用于调试。\n测试场景通过独立测试启动器运行。";
   if(chosen && chosen.profile.supported)head+="\n目击："+(chosen.observed?"有":"无")+" · 目标："+(chosen.confirmed?"已确认":"未确认")+"\n橙线＝实际枪口 · 橙圈＝瞄准点";
   if(ScenarioRunner.active)head+="\n"+TestSave.status;
   TDFCLocale.bind(detail,head,true);
  }
  private function freeSpot(x:Number,y:Number,occupied:Array):Boolean {
   if(x<0 || y<0 || x+230>parent.stage.stageWidth || y+52>parent.stage.stageHeight-4)return false;
   if(x<panel.x+340 && x+230>panel.x && y<panel.y+PANEL_HEIGHT && y+52>panel.y)return false;
   if(x<toggle.x+108 && x+230>toggle.x && y<toggle.y+30 && y+52>toggle.y)return false;
   for each(var b:Object in occupied)if(Math.abs(x-b.x)<234 && Math.abs(y-b.y)<56)return false;
   return true;
  }
  private function placeLabel(label:Sprite,p:Point,occupied:Array):void {
   var wantX:Number=Math.max(0,Math.min(parent.stage.stageWidth-230,p.x-80)),wantY:Number=Math.max(0,p.y-54);
   label.x=wantX;label.y=wantY;if(freeSpot(wantX,wantY,occupied))return;
   var best:Number=1e12;
   // 越界后向可用空间排布，不把所有顶部标签钳在 y=0。
   for(var x:int=4;x+230<=parent.stage.stageWidth;x+=234)for(var y:int=4;y+52<parent.stage.stageHeight;y+=56) {
    if(!freeSpot(x,y,occupied))continue;
    var score:Number=(x-wantX)*(x-wantX)+(y-wantY)*(y-wantY);
    if(score<best){best=score;label.x=x;label.y=y;}
   }
  }
  public function capture():void {
   if(!ScenarioRunner.active || !parent.stage)return;
   try {
    var bitmap:BitmapData=new BitmapData(parent.stage.stageWidth,parent.stage.stageHeight,false,0x111111);
    bitmap.draw(parent);
    var f:File=new File(File.applicationDirectory.resolvePath("tdfc-test-screen.png").nativePath),fs:FileStream=new FileStream();
    var data:ByteArray=PngCapture.encode(bitmap);
    fs.open(f,FileMode.WRITE);fs.writeBytes(data);fs.close();bitmap.dispose();
   }catch(e:Error){TdfcLog.line("capture-error",e.message);}
  }
  public static function name(k:String):String {var n:Object={idle:"待机",vanilla:"原版接管",controlled:"念力控制中",advance:"推进",retreat:"撤退",cover:"寻找掩体",hide:"掩体隐藏",peek:"探头",search:"搜索",space:"散开",dodge:"避线",hold:"守位射击",suppress:"压制"};return n[k]||k;}
 }
}
