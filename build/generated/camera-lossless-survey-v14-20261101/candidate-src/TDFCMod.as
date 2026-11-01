package
{
   import flash.display.Sprite;

   /**
    * TDFC 模组文档类（默认包，文件名 = 类名）。
    *
    * 加载契约（shared-knowledge/knowledge-validation/discoveries/mod-loader-patch-structure.md）：
    *  - 游戏补丁 loader 用 getDefinition("<文档类名>") 取类后调 cls.init(this)；
    *  - 实参是 MainFE 实例，从 main.stage 注册事件。
    */
   public class TDFCMod extends Sprite
   {
      public function TDFCMod()
      {
         super();
      }

      public static function init(main:*):void
      {
         TdfcLog.init();    // 内部先打版本标记行
         TdfcRuntime.init(main);
      }
   }
}
