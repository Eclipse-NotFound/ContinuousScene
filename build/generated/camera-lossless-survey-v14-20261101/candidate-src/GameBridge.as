package {
 import flash.utils.getQualifiedClassName;
 import flash.utils.Dictionary;
 /** 所有游戏对象接触集中于此；决策本身只使用可替换的普通数据快照。 */
 public class GameBridge {
  public static function get(o:*,k:String,d:*=null):* { try { if(o!=null && k in o) return o[k]; } catch(e:Error) {} return d; }
  public static function num(o:*,k:String,d:Number=0):Number { var v:*=get(o,k,d); var n:Number=Number(v); return isNaN(n) ? d : n; }
  public static function cls(u:*):String { try { return getQualifiedClassName(u).split("::").pop(); } catch(e:Error) {} return "?"; }
  public static function pause(w:*):String {
   if(w==null) return "等待世界";
   if(get(get(w,"verror"),"visible",false)) return "游戏错误";
   if(get(get(w,"mm"),"active",false)) return "主菜单";
   if(get(w,"onPause",false)) return "游戏暂停";
   if(get(w,"catPause",false)) return "剧情暂停";
   if(get(get(w,"pip"),"active",false)) return "背包/状态界面";
   if(get(get(w,"sats"),"active",false)) return "SATS";
   if(get(get(w,"stand"),"active",false) || get(get(w,"gui"),"guiPause",false)) return "交互暂停";
   if(num(w,"allStat")!=1 || num(w,"comLoad",-1)>=0 || num(w,"t_exit")>0) return "加载/换图";
   var g:*=get(get(w,"loc"),"gg");
   if(g==null || num(g,"sost")!=1) return "等待玩家";
   return "";
  }
  public static function snapshot(u:*,player:*=null):Object {
   var w:*=get(u,"currentWeapon"); var x:Number=num(u,"X"), y:Number=num(u,"Y");
   var tip:int=int(num(w,"tip"));
   var role:String=w==null || tip<3 ? "melee" : tip==4 ? "thrower" : tip==5 ? "magic" : num(w,"kol",1)>1 ? "shotgun" : "gun";
   return {unit:u,cls:cls(u),id:String(get(u,"id","")),family:String(get(u,"parentId","")),level:num(u,"level"),hero:num(u,"hero"),boss:get(u,"boss",false),
    x:x,y:y,cx:x+num(u,"scX",40)*num(u,"storona",1)/4,cy:y-num(u,"scY",40)/2,
    width:num(u,"scX",40),height:num(u,"scY",40),face:num(u,"storona",1),dx:num(u,"dx"),dy:num(u,"dy"),
    hp:num(u,"hp"),maxhp:num(u,"maxhp",1),fraction:int(num(u,"fraction")),alive:num(u,"sost") == 1,
    npc:get(u,"npc",false),disabled:get(u,"disabled",false) || get(u,"trigDis",false) || get(u,"unres",false),
    role:role,weapon:w,weaponId:String(get(w,"id","")),gun:tip==3,ammo:num(w,"hold",-1),shots:num(w,"kol_shoot"),reload:num(w,"t_reload"),
    rot:num(w,"rot",NaN),wx:num(w,"X",x),wy:num(w,"Y",y-20),weaponSkill:num(u,"weaponSkill",1),
    target:get(u,"celUnit"),aimX:num(u,"celX"),aimY:num(u,"celY"),ground:get(u,"stay",false),fly:get(u,"isFly",false),water:get(u,"isPlav",false),fixed:get(u,"fixed",false),
    speed:num(u,"runSpeed",num(u,"maxSpeed",3)),jump:num(u,"jumpdy",12),noise:num(u,"noise"),obs:num(u,"obs"),maxObs:num(u,"maxObs",1)};
  }
  public static function snapshotInto(u:*,out:Object):Object {
   var w:*=get(u,"currentWeapon"); var x:Number=num(u,"X"), y:Number=num(u,"Y");
   var tip:int=int(num(w,"tip"));
   var role:String=w==null || tip<3 ? "melee" : tip==4 ? "thrower" : tip==5 ? "magic" : num(w,"kol",1)>1 ? "shotgun" : "gun";
   out.unit=u;
   out.cls=sceneClass(u);
   out.id=String(get(u,"id",""));
   out.family=String(get(u,"parentId",""));
   out.level=num(u,"level");
   out.hero=num(u,"hero");
   out.boss=get(u,"boss",false);
   out.x=x;
   out.y=y;
   out.cx=x+num(u,"scX",40)*num(u,"storona",1)/4;
   out.cy=y-num(u,"scY",40)/2;
   out.width=num(u,"scX",40);
   out.height=num(u,"scY",40);
   out.face=num(u,"storona",1);
   out.dx=num(u,"dx");
   out.dy=num(u,"dy");
   out.hp=num(u,"hp");
   out.maxhp=num(u,"maxhp",1);
   out.fraction=int(num(u,"fraction"));
   out.alive=num(u,"sost") == 1;
   out.npc=get(u,"npc",false);
   out.disabled=get(u,"disabled",false) || get(u,"trigDis",false) || get(u,"unres",false);
   out.role=role;
   out.weapon=w;
   out.weaponId=String(get(w,"id",""));
   out.gun=tip==3;
   out.ammo=num(w,"hold",-1);
   out.shots=num(w,"kol_shoot");
   out.reload=num(w,"t_reload");
   out.rot=num(w,"rot",NaN);
   out.wx=num(w,"X",x);
   out.wy=num(w,"Y",y-20);
   out.weaponSkill=num(u,"weaponSkill",1);
   out.target=get(u,"celUnit");
   out.aimX=num(u,"celX");
   out.aimY=num(u,"celY");
   out.ground=get(u,"stay",false);
   out.fly=get(u,"isFly",false);
   out.water=get(u,"isPlav",false);
   out.fixed=get(u,"fixed",false);
   out.speed=num(u,"runSpeed",num(u,"maxSpeed",3));
   out.jump=num(u,"jumpdy",12);
   out.noise=num(u,"noise");
   out.obs=num(u,"obs");
   out.maxObs=num(u,"maxObs",1);
   return out;
  }
  public static function hostile(s:Object,g:Object):Boolean {
   return s.alive && !s.npc && !s.disabled && s.fraction>0 && s.fraction<100 && s.fraction!=g.fraction;
  }
  public static function tile(loc:*,x:Number,y:Number):* { try { return loc.getAbsTile(x,y); } catch(e:Error) {} return null; }
  public static function solid(loc:*,x:Number,y:Number):Boolean {
   var t:*=tile(loc,x,y); if(t==null) return true;
   return num(t,"phis")==1 && x>=num(t,"phX1",-1e9) && x<=num(t,"phX2",1e9) && y>=num(t,"phY1",-1e9) && y<=num(t,"phY2",1e9);
  }
  public static function clear(loc:*,x:Number,y:Number,tx:Number,ty:Number):Boolean {
   var n:int=Math.ceil(Math.max(Math.abs(tx-x),Math.abs(ty-y))/9);
   for(var i:int=1;i<n;i++) if(solid(loc,x+(tx-x)*i/n,y+(ty-y)*i/n)) return false;
   return true;
  }
  public static function sense(b:BrainState,g:Object,loc:*):Object {
   var s:Object=b.sample;
   var dx:Number=g.cx-s.x,dy:Number=g.cy-(s.y-s.height*0.7);
   var distance:Number=Math.sqrt(dx*dx+dy*dy);
   var los:Boolean=distance<1000 && clear(loc,s.x,s.y-s.height*0.7,g.cx,g.cy);
   var angle:Number=Math.atan2(dy,dx)-(s.face>0 ? 0 : Math.PI);
   while(angle>Math.PI) angle-=Math.PI*2; while(angle< -Math.PI) angle+=Math.PI*2;
   var front:Boolean=Math.abs(angle)<=Config.VISION_CONE/2;
   var look:Number=0, hear:Number=0;
   try {
    // Native control can turn the body before this sample. Its look() also reads
    // our cone angle, so synchronise that owned field before asking about sight.
    if(b.viewWritten)b.unit.vAngle=s.face>0?0:Math.PI;
    look=Number(b.unit.look(g.unit,false)); hear=Number(b.unit.listen(g.unit));
   } catch(e:Error) { b.rejected="感知接口不可用: "+e.errorID; }
   return {los:los,distance:distance,front:front,visible:los && front && look>0,look:look,heard:hear>0,hearing:hear};
  }
  public static function standable(loc:*,x:Number,y:Number,s:Object):Boolean {
   var half:Number=Math.max(10,s.width*0.35);
   return !solid(loc,x,y-4) && !solid(loc,x-half,y-s.height*0.55) && !solid(loc,x+half,y-s.height*0.55)
    && (s.fly || s.water || solid(loc,x,y+8));
  }
  public static function walkable(loc:*,s:Object,x:Number,y:Number):Boolean {
   if(Math.abs(y-s.y)>20 && !s.fly && !s.water) return false;
   if(!standable(loc,x,y,s)) return false;
   var n:int=Math.max(1,Math.ceil(Math.abs(x-s.x)/18));
   for(var i:int=1;i<=n;i++) {
    var xx:Number=s.x+(x-s.x)*i/n;
    if(!standable(loc,xx,s.y+(y-s.y)*i/n,s)) return false;
   }
   return true;
  }
  public static function covers(b:BrainState,g:Object,loc:*,side:int=0):Array {
   var out:Array=[],s:Object=b.sample;
   for each(var d:int in [-240,-180,-120,-60,60,120,180,240]) {
    var x:Number=s.x+d,y:Number=s.y;
    if(!walkable(loc,s,x,y)) continue;
    if(clear(loc,x,y-s.height/2,g.cx,g.cy)) continue;
    var peekX:Number=NaN;
    for each(var pd:int in [-36,36,-48,48,-60,60]) {
     if(walkable(loc,{x:x,y:y,width:s.width,height:s.height,fly:s.fly,water:s.water},x+pd,y)
      && clear(loc,x+pd-8,y-s.height/2,g.cx,g.cy) && clear(loc,x+pd+8,y-s.height/2,g.cx,g.cy)) { peekX=x+pd; break; }
    }
    out.push({x:x,y:y,peekX:peekX,score:Math.abs(d)+(isNaN(peekX) ? 100 : 0)+(side!=0 && (x-g.x)*side<0 ? 90 : 0)});
   }
   out.sortOn("score",Array.NUMERIC); return out;
  }
  public static const sceneThreatVersion:String="0.6.4-scene2";
  public static var sceneThreatFast:Boolean=true;
  private static var sceneClasses:Dictionary=new Dictionary(true);
  private static function sceneClass(o:Object):String {
   var cached:String=sceneClasses[o];
   if(cached!=null)return cached;
   cached=cls(o);sceneClasses[o]=cached;return cached;
  }
  public static function sceneThreatReference(s:Object,loc:*):Object {

   var o:*=get(loc,"firstObj"); var n:int=0;
   while(o!=null && n++<256) {
    var c:String=getQualifiedClassName(o).split("::").pop(); var v:Number=num(o,"vel");
    if((c=="Bullet" || c=="SmartBullet") && get(o,"owner")!==s.unit && num(o,"liv")>0 && v>0 && v<60) {
     var angle:Number=num(o,"rot"),vx:Number=Math.cos(angle)*v-s.dx,vy:Number=Math.sin(angle)*v+num(o,"ddy")-s.dy;
     var ox:Number=num(o,"X")-s.x,oy:Number=num(o,"Y")-s.cy;
     var vv:Number=vx*vx+vy*vy,t:Number=vv>0 ? Math.max(0,Math.min(3,-(ox*vx+oy*vy)/vv)) : 0;
     var r:Number=24+num(o,"explRadius");
     if((ox+vx*t)*(ox+vx*t)+(oy+vy*t)*(oy+vy*t)<r*r) return {x:num(o,"X"),y:num(o,"Y"),kind:c};
    }
    o=get(o,"nobj");
   }
   return null;
  
  }
  public static function threat(s:Object,loc:*):Object {
   if(!sceneThreatFast)return sceneThreatReference(s,loc);

   var o:*=get(loc,"firstObj"); var n:int=0;
   while(o!=null && n++<256) {
    var c:String=sceneClass(o); var v:Number=(c=="Bullet" || c=="SmartBullet")?num(o,"vel"):0;
    if((c=="Bullet" || c=="SmartBullet") && get(o,"owner")!==s.unit && num(o,"liv")>0 && v>0 && v<60) {
     var angle:Number=num(o,"rot"),vx:Number=Math.cos(angle)*v-s.dx,vy:Number=Math.sin(angle)*v+num(o,"ddy")-s.dy;
     var ox:Number=num(o,"X")-s.x,oy:Number=num(o,"Y")-s.cy;
     var vv:Number=vx*vx+vy*vy,t:Number=vv>0 ? Math.max(0,Math.min(3,-(ox*vx+oy*vy)/vv)) : 0;
     var r:Number=24+num(o,"explRadius");
     if((ox+vx*t)*(ox+vx*t)+(oy+vy*t)*(oy+vy*t)<r*r) return {x:num(o,"X"),y:num(o,"Y"),kind:c};
    }
    o=get(o,"nobj");
   }
   return null;
  }
 }
}
