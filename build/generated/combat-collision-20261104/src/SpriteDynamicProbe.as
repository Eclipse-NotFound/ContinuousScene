package
{
    import flash.desktop.NativeApplication;
    import flash.display.MovieClip;
    import flash.display.Sprite;
    import flash.utils.getTimer;

    /** Does `flash.display.Sprite` accept a dynamic property at runtime in this
     *  AIR build? The ContinuousScene host candidate stores its bullet bucket
     *  table on `World.w.visual`, which the game creates as `new Sprite()`
     *  (World.as:414). If Sprite were sealed the write would throw #1069 inside
     *  sceneTick, so this must be proven before deploying.
     *
     *  A user-defined sealed class is the negative control: it must throw. */
    public class SpriteDynamicProbe extends Sprite
    {
        public function SpriteDynamicProbe()
        {
            var lines:Array = [];
            var spriteOk:Boolean = false;
            var spriteError:String = null;
            try
            {
                var plain:Sprite = new Sprite();
                var payload:Object = {"cell": 512, "buckets": [1, 2, 3]};
                plain["csBulletGrid"] = payload;
                var readBack:Object = plain["csBulletGrid"];
                spriteOk = readBack === payload;
                plain["csBulletGrid"] = null;
                spriteOk = spriteOk && plain["csBulletGrid"] == null;
            }
            catch (error:Error)
            {
                spriteError = error.message;
            }
            var sealedError:String = null;
            try
            {
                var sealed:SealedStandIn = new SealedStandIn();
                var value:Object = sealed["csBulletGrid"];
                lines.push("sealed read returned " + value);
            }
            catch (error2:Error)
            {
                sealedError = error2.errorID + ":" + error2.message;
            }
            var movieOk:Boolean = false;
            var movieError:String = null;
            try
            {
                var clip:MovieClip = new MovieClip();
                var moviePayload:Object = {"cell": 512, "buckets": [1, 2, 3]};
                clip["__csBulletGridV1"] = moviePayload;
                movieOk = clip["__csBulletGridV1"] === moviePayload;
                clip["__csBulletGridV1"] = null;
                movieOk = movieOk && clip["__csBulletGridV1"] == null;
            }
            catch (error3:Error)
            {
                movieError = error3.errorID + ":" + error3.message;
            }
            lines.push("movieClipDynamic=" + movieOk + " movieError=" + movieError);
            lines.push("spriteDynamic=" + spriteOk + " spriteError=" + spriteError);
            lines.push("sealedControlError=" + sealedError);
            var verdict:String = movieOk && movieError == null && sealedError != null && !spriteOk ? "PASS" : "FAIL";
            lines.push("verdict=" + verdict);
            for each (var line:String in lines)
            {
                trace(line);
            }
            flash.utils.setTimeout(function():void
            {
                NativeApplication.nativeApplication.exit(0);
            }, 200);
        }
    }
}
