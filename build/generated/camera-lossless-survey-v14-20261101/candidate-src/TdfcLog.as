package {
 import flash.filesystem.File;
 import flash.filesystem.FileMode;
 import flash.filesystem.FileStream;
 import flash.utils.getTimer;
 public class TdfcLog {
  public static var status:String="初始化";
  public static var lastReportPath:String="";
  private static var buffer:Array=[];
  private static var recent:Object={};
  private static var lastReset:int=0;
  private static var session:String=String(new Date().time);
  public static function init():void {line("version","v"+Config.VER+" session="+session);flush();}
  public static function line(feature:String,msg:String):void {
   var key:String=feature+":"+msg,now:int=getTimer();
   if(now-lastReset>10000){recent={};lastReset=now;}
   if(recent[key]!=null && now-int(recent[key])<2000)return;
   recent[key]=now;if(buffer.length>=200)flush();
   buffer.push(new Date().toUTCString()+" [TDFC] "+feature+" "+msg);
  }
  public static function flush():void {
   if(buffer.length==0)return;
   try {
    var f:File=File.applicationStorageDirectory.resolvePath("tdfc.log");
    if(f.exists && f.size>2*1024*1024)f.moveTo(File.applicationStorageDirectory.resolvePath("tdfc.previous.log"),true);
    var fs:FileStream=new FileStream();fs.open(f,FileMode.APPEND);fs.writeUTFBytes(buffer.join("\n")+"\n");fs.close();buffer=[];status="记录正常";
   }catch(e:Error){status="写入失败 "+e.errorID;if(buffer.length>200)buffer=buffer.slice(-100);}
  }
  public static function saveReport(s:String):void {
   try {var f:File=File.applicationStorageDirectory.resolvePath("tdfc-report-"+new Date().time+".txt");var fs:FileStream=new FileStream();fs.open(f,FileMode.WRITE);fs.writeUTFBytes(s);fs.close();lastReportPath=f.nativePath;line("report",f.nativePath);flush();status="诊断已保存到测试/游戏数据目录";}catch(e:Error){status="诊断保存失败 "+e.errorID;}
  }
 }
}
