package {
 /** 保留原版脚步/枪声产生与衰减，只限制响度；不把普通移动变成全局警报。 */
 public class PlayerNoise {
  private static var player:*;
  private static var originalRun:Number=NaN,lastRun:Number=NaN;
  public static function reset():void {
   try {if(player && GameBridge.num(player,"noiseRun")==lastRun)player.noiseRun=originalRun;}catch(e:Error){}
   player=null;originalRun=lastRun=NaN;
  }
  public static function cap(value:Number):Number {return Math.max(0,Math.min(Config.NOISE_MAX,value));}
  public static function update(g:*):void {
   if(player!==g){reset();player=g;originalRun=GameBridge.num(g,"noiseRun",200);}
   // 不干预其他模组后来设置的基础脚步值，蹲姿只影响脚步，不消除开枪响声。
   var current:Number=GameBridge.num(g,"noiseRun",200);
   if(!isNaN(lastRun) && current!=lastRun)originalRun=current;
   lastRun=Math.min(originalRun,GameBridge.get(g,"isSit",false)?Config.NOISE_SNEAK:Config.NOISE_RUN);
   g.noiseRun=lastRun;
   g.noise=cap(GameBridge.num(g,"noise"));
  }
 }
}
