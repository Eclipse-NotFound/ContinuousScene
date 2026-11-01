package {
 import flash.utils.getTimer;
 /** 仅隔离测试：在真实地形中找一组“暴露→可达掩体→可探头”的位置，不改地图。 */
 public class CoverFixture {
  private static var points:Array=[];
  private static var scanned:Boolean=false,a:int=0,z:int=0;
  public static var found:Object;
  public static function locate(loc:*,s:Object,playerHeight:Number):Boolean {
   if(!scanned) {
    scanned=true;
    for(var y:int=80;y<GameBridge.num(loc,"spaceY")*40-40;y+=40)
     for(var x:int=60;x<GameBridge.num(loc,"spaceX")*40-40;x+=20)
      if(GameBridge.standable(loc,x,y-1,s) && !GameBridge.solid(loc,x,y-51))points.push({x:x,y:y-1});
   }
   var start:int=getTimer();
   while(a<points.length && getTimer()-start<5) {
    var p:Object=points[a],g:Object=points[z++];
    if(z>=points.length){a++;z=0;}
    var dx:Number=Math.abs(p.x-g.x),dy:Number=Math.abs(p.y-g.y);
    if(dx<120 || dx>420 || dy<40 || dy>240)continue;
    s.x=p.x;s.y=p.y;
    if(!GameBridge.clear(loc,p.x,p.y-s.height/2,g.x,g.y-playerHeight/2))continue;
    var b:BrainState=new BrainState(1,null,null);b.sample=s;
    var c:Array=GameBridge.covers(b,{x:g.x,cx:g.x,cy:g.y-playerHeight/2},loc);
    for each(var candidate:Object in c)if(!isNaN(candidate.peekX) && Math.abs(candidate.x-p.x)>=40) {
     g.cy=g.y-playerHeight/2;found={enemy:p,player:g,cover:candidate};return true;
    }
   }
   if(a>=points.length)throw new Error("当前地形没有符合条件的掩体测试位置");
   return false;
  }
 }
}
