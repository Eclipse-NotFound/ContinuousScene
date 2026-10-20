package {
 import flash.desktop.NativeApplication;import flash.display.*;import flash.events.*;import flash.filesystem.*;import flash.utils.*;
 public class SingleSceneProbeMod {
  private static var main:*,w:*,api:*,loc:*,player:*,old:*,bullet:*,wall:*,box:*,beforeHP:Number;
  private static var phase:int=0,frames:int=0,start:int,entry:int,done:Boolean=false,doc:XML;
  private static var report:Object={checks:[],errors:[]};
  private static var pose:Object;
  private static var modeSetting:Object;
  public static function init(host:*):void{if(NativeApplication.nativeApplication.applicationID.indexOf("pfe-cs-authoring-")!=0)return;main=host;start=getTimer();main.stage.addEventListener(Event.ENTER_FRAME,before,false,1000);main.stage.addEventListener(Event.ENTER_FRAME,tick,false,-1100);}
  private static function before(e:Event):void {
   if(done||phase!=21||!box)return;
   w.ctr.clearAll();w.gg.ctr.clearAll();w.gg.setLocPos(pose.x,pose.y);w.gg.dx=w.gg.dy=w.gg.osndx=w.gg.osndy=0;w.gg.isTake=0;
   w.celX=box.X;w.celY=box.Y-box.scY/2;w.cam.celX=w.celX*w.cam.scaleV+w.cam.vx;w.cam.celY=w.celY*w.cam.scaleV+w.cam.vy;
   box.onCursor=box.prior;w.loc.celObj=box;w.loc.celDist=(pose.x-box.X)*(pose.x-box.X)+(pose.y-box.Y)*(pose.y-box.Y);
   w.ctr.keyAction=w.gg.ctr.keyAction=frames>=5&&frames<35;
  }
  private static function findContainer():void {
   for each(var o:* in loc.objs){
    if(o.X<1920||!o.inter||o.dead||o.invis||o.door>0)continue;var i:*=o.inter;
    if(!i.active||i.open||i.action!=1||!i.cont||i.cont=="empty"||i.lock>0||i.mine>0||i.needSkill||i.allact||i.cons||i.prob||i.t_action>20||i.scrAct||i.scrOpen||i.actFun)continue;
    for each(var dy:Number in [0,-20,20,-40,40])for each(var dx:Number in [-65,65,-100,100,-40,40]){
     var x:Number=o.X+dx,y:Number=o.Y+dy;
     if(dx*dx+dy*dy>w.actionDist||loc.collisionUnit(x,y,w.gg.scX,w.gg.scY))continue;
     if(loc.isLine(x,y-w.gg.scY*.75,o.X,o.Y-o.scY/2,o)){box=o;pose={x:x,y:y};return;}
    }
   }
  }
  private static function check(n:String,b:Boolean,d:*=null):void{report.checks.push({name:n,ok:b,detail:d});}
  private static function image(n:String):void{var b:BitmapData=new BitmapData(main.stage.stageWidth,main.stage.stageHeight,false,0);b.draw(main.stage);var s:FileStream=new FileStream();s.open(File.applicationStorageDirectory.resolvePath(n+".png"),FileMode.WRITE);s.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));s.close();b.dispose();}
  private static function read():XML{var s:FileStream=new FileStream();s.open(File.applicationDirectory.resolvePath("mods/ContinuousScene/maps/active.xml"),FileMode.READ);var d:XML=new XML(s.readUTFBytes(s.bytesAvailable));s.close();return d;}
  private static function write(d:XML):void{var s:FileStream=new FileStream();s.open(new File(File.applicationDirectory.resolvePath("mods/ContinuousScene/maps/active.xml").nativePath),FileMode.WRITE);s.writeUTFBytes(d.toXMLString());s.close();}
  private static function arrived(id:String):Boolean{return w.land&&w.land.act.id==id&&w.game.curLandId==id&&w.t_exit==0&&w.allStat==1&&w.ng_wait==0;}
  private static function next(p:int):void{phase=p;frames=0;}
  private static function tick(e:Event):void{if(done)return;try{
   w=getDefinitionByName("fe.World")["w"];if(getTimer()-start>200000)throw new Error("timeout phase "+phase);
   if(w&&w.verror&&w.verror.visible)throw new Error(w.verror.txt.text);
   if(w&&w.gg){w.godMode=true;w.gg.invulner=true;}
   frames++;
   if(phase==0&&w&&w.mm&&w.mm.loaded&&w.allLandsLoaded&&w.textLoaded){
    var carrier:*=main.getChildByName("ContinuousSceneCarrier");if(!carrier||!carrier.sceneAPI.ready)return;
    api=carrier.sceneAPI;check("candidate-version",api.version=="0.9.0",api.version);
    var settings:*=main.getChildByName("ModSettingsCarrier");if(!settings||!settings.modAPI)return;
    for each(var page:Object in settings.modAPI.getPages())if(page.modId=="continuousscene")for each(var field:Object in page.items)if(field.key=="nativeEnabled")modeSetting=field;
    if(!modeSetting)return;modeSetting["set"](false);
    doc=read();w.grafon.scenePreload=false;w.mm.active=false;w.newGame(-1,"Single Map",{propusk:true});next(1);
   }else if(phase==1&&w.ng_wait==0&&w.allStat==1&&w.gg&&w.loc){
    if(!w.gg.ggControl||w.pip.noAct){frames=0;w.ctr.keyPressed=w.ctr.keyPressed2=true;return;}
    if(frames<20)return;w.ctr.clearAll();w.pers.healAll();entry=getTimer();api.travel();next(2);
   }else if(phase==2&&arrived("continuous_scene")&&frames>20){
    loc=w.loc;player=w.gg;report.loadMs=getTimer()-entry;
    var locations:int=0;for each(var column:* in w.land.locs)for each(var rowLoc:* in column)for each(var one:* in rowLoc)if(one)locations++;
    check("one-location",locations==1,locations);
    check("whole-grid",loc.spaceX==192&&loc.spaceY==50,[loc.spaceX,loc.spaceY]);
    check("large-raster-active",w.grafon.sceneLarge);check("view-ready",w.grafon.sceneViewReady());
    check("native-mode-independent",modeSetting["get"]()===false);
    check("spawn",w.gg.X>200&&w.gg.X<400,[w.gg.X,w.gg.Y]);
    report.objectCounts={objects:loc.objs.length,units:loc.units.length,acts:loc.acts.length,backgrounds:loc.backobjs.length};
    check("far-objects-created",loc.objs.some(function(o:*,i:int,a:Array):Boolean{return o.X>4800;}));
    var fixed:int=0,matched:int=0;var missing:Array=[];var used:Array=[];
    var data:*=getDefinitionByName("fe.AllData")["d"];
    for each(var n:XML in doc.room.obj){var id:String=String(n.@id);var def:XMLList=data.obj.(@id==id);if(!def.length()||String(def.@tip)!="box")continue;fixed++;
     var size:int=int(def.@size);if(size<=0)size=1;var found:Boolean=false;
     for each(var o:* in loc.objs)if(used.indexOf(o)<0&&o.id==id&&Math.abs(o.begX-(Number(n.@x)+size*0.5)*40)<1&&Math.abs(o.begY-((Number(n.@y)+1)*40-1))<1){matched++;used.push(o);found=true;break;}
     if(!found)missing.push({id:id,x:Number(n.@x),y:Number(n.@y),size:size});}
    check("authored-boxes-present",fixed>0&&matched==fixed,{expected:fixed,actual:matched,missing:missing});
    image("game-entry");
    // Direct native damage verifies ordinary interior material behavior in the single grid.
    for(var x:int=2;x<190&&!wall;x++)for(var y:int=2;y<48;y++){var t:*=loc.space[x][y];if(t.phis==1&&!t.indestruct&&t.hp>0&&t.hp<6000){wall=t;break;}}
    check("destructible-material-present",wall!=null);
    if(wall){loc.hitTile(wall,Math.max(wall.hp,wall.thre)+1,wall.X*40+20,wall.Y*40+20,9);check("wall-break-removes-collision",wall.phis==0);}
    // Camera jump is a rendering test, not a claim that the route was walked.
    findContainer();check("remote-container-interaction-coverage",box!=null);next(21);
   }else if(phase==21&&(!box||frames>=40||box.inter.cont=="empty")){
    check("native-E-loots-authored-container",box&&box.inter.cont=="empty",box?{id:box.id,x:box.X,y:box.Y,open:box.inter.open}:null);
    w.ctr.clearAll();w.gg.ctr.clearAll();w.gg.setLocPos(5700,879);next(3);
   }else if(phase==3&&frames>25){
    check("same-scene-at-far-edge",w.loc===loc&&w.gg===player&&w.gg.loc===loc);check("far-view-ready",w.grafon.sceneViewReady());image("game-far");
    w.pip.onoff(3,1);next(4);
   }else if(phase==4&&frames>10){
    image("game-map");check("native-map-created",w.land.map&&w.land.map.width>=192,w.land.map?[w.land.map.width,w.land.map.height]:null);
    w.pip.onoff(-1);w.saveGame(3);w.comLoad=3;old=w.land;next(5);
   }else if(phase==5&&w.comLoad==-1&&w.land!==old&&arrived("continuous_scene")&&frames>20){
    check("save-load-size",w.loc.spaceX==192&&w.loc.spaceY==50);check("save-load-terrain",!wall||w.loc.space[wall.X][wall.Y].phis==0);
    api.travel();next(6);
   }else if(phase==6&&arrived(w.game.baseId)&&frames>15){
    check("return-to-base",!w.grafon.sceneLarge);
    // Change a far tile and an object in the isolated authored file, then use the real entry again.
    doc=read();var row:Array=String(doc.room.a[40]).split('.');row[170]='N';doc.room.a[40]=<a>{row.join('.')}</a>;
    doc.room.appendChild(<obj id="box" x="169" y="40" code="reload-proof"/>);doc.room.@sceneRevision="authored-test-reload";write(doc);
    api.travel();next(7);
   }else if(phase==7&&arrived("continuous_scene")&&frames>20){
    check("fresh-file-tile-loaded",w.loc.space[170][40].front=="N");
    check("fresh-scene-created",w.loc!==loc);
    // AllData box has size=2: its native center is (169+1)*40, not the one-cell default.
    var farBoxes:Array=[];for each(var fresh:* in w.loc.objs)if(fresh.id=="box"&&fresh.begX>=6600)farBoxes.push({x:fresh.begX,y:fresh.begY});
    check("fresh-file-object-loaded",w.loc.objs.some(function(o:*,i:int,a:Array):Boolean{return o.id=="box"&&o.begX==6800&&o.begY==1639;}),farBoxes);
    finish();
   }
  }catch(error:Error){finish(error.message+"\n"+error.getStackTrace());}}
  private static function finish(error:String=null):void{done=true;if(error)report.errors.push(error);report.ok=!error;for each(var c:Object in report.checks)if(!c.ok)report.ok=false;report.elapsed=getTimer()-start;var s:FileStream=new FileStream();s.open(File.applicationStorageDirectory.resolvePath("game-result.json"),FileMode.WRITE);s.writeUTFBytes(JSON.stringify(report,null,2));s.close();NativeApplication.nativeApplication.exit(report.ok?0:1);}
 }
}
