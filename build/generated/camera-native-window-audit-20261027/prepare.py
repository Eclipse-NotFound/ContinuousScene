"""Fixed prewarm + three exact software roundtrips, deferred owned-window close."""
from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-native-window-switch-20261027'
spec=importlib.util.spec_from_file_location('native_window_original_recipe',BASE/'prepare.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
one=old.one

def helper_source():
    s=old.helper_source().replace('camera-native-window-switch-1','camera-native-window-audit-1')
    s=one(s,'import flash.display.Stage;', '''import flash.display.Stage;
    import flash.display.PNGEncoderOptions;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;''')
    s=one(s,'private var nativeMode:int=0;', 'private var nativeMode:int=0;\n        private var closeWait:int=0;')
    s=one(s,'switchNativeWindow(cursor%3);var point:Object=prepareRoute[cursor];','var point:Object=prepareRoute[cursor];')
    s=one(s,'if(closed)return true;', 'if(closed)return finishOwnedClose();')
    s=one(s,'return closed;', 'return closed && finishOwnedClose();')
    s=one(s,'extra.close();require(extra.closed,"Owned window did not close");++cleanup.ownedWindowsClosed;',
        'extra.close();if(extra.closed)++cleanup.ownedWindowsClosed;')
    s=one(s,'private function makeNativeWindows():void {', '''private function finishOwnedClose():Boolean {
            if(report==null || report.cleanup==null)return true;
            var total:int=0;
            for each(var window:NativeWindow in extraWindows)if(window.closed)++total;
            report.cleanup.ownedWindowsClosed=total;
            if(total==extraWindows.length)return true;
            if(++closeWait<60)return false;
            report.cleanup.errors.push("Owned windows did not close after 60 frame callbacks");
            report.cleanup.restored=false;report.passed=false;report.complete=false;
            report.errors.push("Deferred close failed");return true;
        }

        private function savePNG(b:BitmapData,name:String):void {
            var path:File=File.applicationStorageDirectory.resolvePath(name);
            var stream:FileStream=new FileStream();
            try {stream.open(path,FileMode.WRITE);stream.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}
            finally {stream.close();}
        }

        private function makeNativeWindows():void {''')
    begin=s.index('                var a:BitmapData=capture(),b:BitmapData=capture();')
    end=s.index('\n            } finally {disposeOwned();result.elapsedMs=getTimer()-at;}',begin)
    s=s[:begin]+'''                // One fixed warm roundtrip per camera position. Do not retry until passing.
                switchNativeWindow(1);switchNativeWindow(2);switchNativeWindow(0);
                result.roundtrips=[];
                for(var pass:int=0;pass<3;++pass) {
                    var a:BitmapData=capture(),b:BitmapData=capture();
                    var trip:Object={index:pass,nativeRepeat:compare(a,b)};result.roundtrips.push(trip);
                    switchNativeWindow(1);var d:BitmapData=capture();trip.newDirect=compare(a,d);
                    switchNativeWindow(2);var c:BitmapData=capture();trip.newAuto=compare(a,c);
                    switchNativeWindow(0);var back:BitmapData=capture();trip.restored=compare(a,back);
                    if(index==0 && pass==0) {
                        savePNG(a,"window-original.png");savePNG(d,"window-direct.png");
                        savePNG(c,"window-auto.png");savePNG(back,"window-restored.png");
                    }
                    trip.passed=trip.nativeRepeat.equal && trip.newDirect.equal && trip.newAuto.equal && trip.restored.equal;
                    result.nativeRepeat=trip.nativeRepeat;result.newDirect=trip.newDirect;
                    result.newAuto=trip.newAuto;result.restored=trip.restored;
                    disposeOwned();
                    require(trip.passed,"Warm same-world Stage transfer changed software pixels");
                }
                result.passed=true;''' +s[end:]
    return s

def runner_source():
    s=old.runner_source().replace('camera-native-window-switch-1','camera-native-window-audit-1')
    s=s.replace("trial['pixelBitmapsDisposed']==25", "trial['pixelBitmapsDisposed']==75")
    s=one(s,"        assert check['passed']", """        assert check['passed'] and len(check['roundtrips'])==3
        for trip in check['roundtrips']:
            assert trip['passed']
            for key in ('nativeRepeat','newDirect','newAuto','restored'):
                assert trip[key]['equal'] and trip[key]['differentPixels']==trip[key]['maxRGB']==trip[key]['maxAlpha']==0""")
    return s

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared fixed warm transfer audit; original failure remains unchanged')
