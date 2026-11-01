package {
 import flash.filesystem.File;
 import flash.filesystem.FileMode;
 import flash.filesystem.FileStream;
 import flash.net.ObjectEncoding;
 /** 槽位已由启动器复制到隔离存储；此类只由精确测试身份调用。 */
 public class TestSave {
  public static var status:String="未载入存档";
  public static var evidence:Object={verified:false};
  private static var expected:Object;
  public static function begin(w:*,options:Object):void {
   var data:Object;
   if(options.fresh===true) {
    status="明确选择新档";evidence={verified:true,fresh:true};
    w.newGame(-1,"TDFC Test",null);return;
   }
   if(options.saveFile) {
    var f:File=new File(String(options.saveFile));
    if(!f.exists)throw new Error("存档副本不存在："+f.nativePath);
    var fs:FileStream=new FileStream();
    try {fs.open(f,FileMode.READ);fs.objectEncoding=ObjectEncoding.AMF3;data=fs.readObject();}
    finally {fs.close();}
   } else {
    if(options.saveSlot===undefined)throw new Error("未指定存档；请使用测试启动器，或明确选择新档");
    data=w.getSave(int(options.saveSlot));
   }
   expected=describe(data);
   evidence={verified:false,source:options.saveSource,sha256:options.saveSha256,slot:options.saveSlot,expected:expected};
   status="正在载入 "+expected.name+" / Lv."+expected.level+" / "+expected.land;
   TdfcLog.line("save",status+" source="+options.saveSource);
   // newGame(99) 先创建 GUI/SATS 再读取 loaddata，无须先新建角色。
   w.loaddata=data;w.newGame(99,"TDFC Test",null);
   // 原版不恢复随机地图实例，Game.init 会把随机地点的角色送回基地。
   var land:*=w.game.lands[expected.land];
   expected.loadLand=(!land || land.rnd) ? "rbl" : expected.land;
  }
  public static function describe(data:Object):Object {
   if(!data || data.est!=1 || !data.pers || !data.game || !data.invent)
    throw new Error("存档为空或格式不完整；不会回退新档");
   return {name:data.pers.persName,level:data.pers.level,land:data.game.land,date:data.date,version:data.ver};
  }
  public static function verify(w:*):void {
   if(evidence.fresh)return;
   var actual:Object={name:w.pers.persName,level:w.pers.level,land:w.game.curLandId};
   evidence.actual=actual;
   if(actual.name!==expected.name || actual.level!=expected.level || actual.land!==expected.loadLand)
    throw new Error("读档核验不一致："+JSON.stringify(evidence));
   evidence.verified=true;
   status="存档已核验："+actual.name+" · Lv."+actual.level+" · "+actual.land;
   TdfcLog.line("save",status);
  }
 }
}
