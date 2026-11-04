package tests {
    import flash.desktop.NativeApplication;
    import flash.display.Sprite;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;

    /** Standalone deterministic runner for the culling suites: no game, no
     * window, no save files. The result JSON goes to the AIR storage directory
     * (applicationDirectory is read-only under AIR) and is traced as well.
     * Exit code: 0 = all pass, 1 = assertion failure, 2 = harness fault. */
    public class CullingChecksApp extends Sprite {
        public function CullingChecksApp() {
            var rows:Array=[],error:String="",stack:String="",harnessFault:Boolean=false,failures:Array=[];
            try { appendAll(rows,SceneCullingChecks.run(SceneObjectCulling)); }
            catch(fault:Error) { harnessFault=true;error="SceneCullingChecks: "+fault.message;stack=fault.getStackTrace(); }
            if(!harnessFault) {
                try { appendAll(rows,SceneCullingScaleChecks.run(SceneObjectCulling)); }
                catch(fault2:Error) { harnessFault=true;error="SceneCullingScaleChecks: "+fault2.message;stack=fault2.getStackTrace(); }
            }
            var pass:int=0;
            for each(var row:Object in rows) {
                if(row.ok)pass++;
                else failures.push({name:row.name,detail:row.detail});
            }
            var result:Object={ok:!harnessFault && failures.length==0,pass:pass,fail:failures.length,
                error:error,stack:stack,failures:failures,rows:rows,version:"culling-checks-1"};
            var text:String=JSON.stringify(result);
            trace("CS-CULLING-CHECKS "+text);
            try {
                var file:File=File.applicationStorageDirectory.resolvePath("cs-culling-checks-result.json");
                var stream:FileStream=new FileStream();
                try {stream.open(file,FileMode.WRITE);stream.writeUTFBytes(text);}
                finally {stream.close();}
                trace("CS-CULLING-CHECKS-PATH "+file.nativePath);
            } catch(writeError:Error) {
                trace("CS-CULLING-CHECKS-WRITE-FAILED "+writeError.message);
            }
            var code:int=harnessFault?2:(failures.length?1:0);
            NativeApplication.nativeApplication.exit(code);
        }
        private function appendAll(target:Array,rows:Array):void {
            for each(var row:Object in rows)target.push(row);
        }
    }
}
