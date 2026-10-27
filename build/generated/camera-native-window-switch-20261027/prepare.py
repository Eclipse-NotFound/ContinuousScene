"""Generate same-world native direct/auto window attribution; never launch."""
from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-native-gpu-20261027'
VERSION='camera-native-window-switch-1'

def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b,1)

def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-native-gpu-1',VERSION)
    s=one(s,'import flash.display.Stage;', '''import flash.display.Stage;
    import flash.display.NativeWindow;
    import flash.display.NativeWindowInitOptions;
    import flash.display.NativeWindowSystemChrome;''')
    s=one(s,'private var snd:Class;', '''private var originalStage:Stage;
        private var stages:Array=[];
        private var stageRoots:Array=[];
        private var extraWindows:Array=[];
        private var nativeMode:int=0;
        private var snd:Class;''')
    s=one(s,'private var order:Array=[0,1,2,3,3,2,1,0];','private var order:Array=[0,1,2,3,4,5,5,4,3,2,1,0];')
    s=s.replace('measurementFrames:960','measurementFrames:1440')
    s=one(s,'world=w;presenter=p;','world=w;presenter=p;report.nativeWindows=[];report.stageSwitches=[];report.windowPixelsNotCaptured=true;')
    s=one(s,'stage.nativeWindow.visible=true;', '''originalStage=stage;
                stages=[stage];
                for(var rootIndex:int=0;rootIndex<stage.numChildren;++rootIndex)stageRoots.push(stage.getChildAt(rootIndex));
                require(stageRoots.length>0,"No Stage roots");
                report.originalRootClasses=[];
                for each(var root:DisplayObject in stageRoots)report.originalRootClasses.push(getQualifiedClassName(root));
                stage.nativeWindow.visible=true;''')
    s=one(s,'makeRoute();', 'makeNativeWindows();makeRoute();')
    s=one(s,'var point:Object=prepareRoute[cursor];','switchNativeWindow(cursor%3);var point:Object=prepareRoute[cursor];')
    s=one(s,'pixelCase(views[cursor],cursor);++cursor;','switchNativeWindow(0);pixelCase(views[cursor],cursor);++cursor;')
    s=one(s,'row.workMs.push(pending.workMs);', 'row.nativeMode.push(pending.nativeMode);row.renderer.push(pending.renderer);row.workMs.push(pending.workMs);')
    s=one(s,'if(saved!=null && saved.ready) {','''if(saved!=null && saved.ready) {
                try {switchNativeWindow(0);}
                catch(stageRestore:Error){cleanup.errors.push("Stage restore: "+stageRestore.message);}''')
    s=one(s,'cleanup.pendingOwnedBitmaps=owned.length;', '''cleanup.ownedWindowsCreated=extraWindows.length;cleanup.ownedWindowsClosed=0;
            for each(var extra:NativeWindow in extraWindows)try {
                require(extra.stage.numChildren==0,"Owned window still contains native roots");
                extra.close();require(extra.closed,"Owned window did not close");++cleanup.ownedWindowsClosed;
            }catch(windowClose:Error){cleanup.errors.push("Window close: "+windowClose.message);}
            if(originalStage!=null)try {
                require(stage===originalStage && world.swfStage===originalStage && world.main.stage===originalStage,"Original Stage not restored");
                require(originalStage.numChildren==stageRoots.length,"Original Stage root count mismatch");
                for(var restoreRoot:int=0;restoreRoot<stageRoots.length;++restoreRoot)
                    require(originalStage.getChildAt(restoreRoot)===stageRoots[restoreRoot],"Original Stage root order mismatch");
            }catch(rootRestore:Error){cleanup.errors.push("Stage roots: "+rootRestore.message);}
            cleanup.pendingOwnedBitmaps=owned.length;''')
    s=one(s,'require(stage.stageWidth==1280 && stage.stageHeight==720,"Matched camera baseline requires 1280x720 content");',
        'require(stage.stageWidth==2032 && stage.stageHeight==1084,"Native window comparison requires 2032x1084 content");')
    s=one(s,'var x:int=offsetX+960,y:int=offsetY+600;', 'var x:int=offsetX+960,y:int=offsetY+400;')
    s=one(s,'localCenterX:960,localCenterY:600,', 'localCenterX:960,localCenterY:400,')
    s=one(s,'var condition:int=order[segment];age=0;', 'var condition:int=order[segment];age=0;switchNativeWindow(int(condition/2));')
    s=one(s,'mode:["native-static","native-horizontal","native-vertical","native-combined"][condition]',
        'mode:["original-static","original-moving","direct-static","direct-moving","auto-static","auto-moving"][condition]')
    s=one(s,'hidden:false,moving:condition!=0,','hidden:false,moving:condition%2==1,')
    s=one(s,'worldVisible:[],windowVisible:[],start:snapshot()', 'worldVisible:[],windowVisible:[],nativeMode:[],renderer:[],start:snapshot()')
    s=one(s,'var point:Object={x:row.condition==2?views[0].x:target.x,y:row.condition==1?views[0].y:target.y};','var point:Object=target;')
    s=one(s,'pending={vx:cam.vx,', 'pending={nativeMode:nativeMode,renderer:stage.nativeWindow.renderMode,vx:cam.vx,')
    s=one(s,'var a:BitmapData=capture(),b:BitmapData=capture();\n                result.nativeRepeat=compare(a,b);result.passed=result.nativeRepeat.equal;\n                require(result.passed,"Native consecutive captures changed");', '''var a:BitmapData=capture(),b:BitmapData=capture();
                result.nativeRepeat=compare(a,b);
                switchNativeWindow(1);var d:BitmapData=capture();result.newDirect=compare(a,d);
                switchNativeWindow(2);var c:BitmapData=capture();result.newAuto=compare(a,c);
                switchNativeWindow(0);var back:BitmapData=capture();result.restored=compare(a,back);
                result.passed=result.nativeRepeat.equal && result.newDirect.equal && result.newAuto.equal && result.restored.equal;
                require(result.passed,"Software capture changed after same-world Stage transfer");''')
    s=one(s,'private function makeRoute():void {', '''private function makeNativeWindows():void {
            report.nativeWindows.push({index:0,renderer:stage.nativeWindow.renderMode,width:stage.stageWidth,height:stage.stageHeight,quality:stage.quality});
            require(stage.nativeWindow.renderMode=="direct","Original window must be direct");
            for each(var renderer:String in ["direct","auto"]) {
                var options:NativeWindowInitOptions=new NativeWindowInitOptions();
                options.renderMode=renderer;options.systemChrome=NativeWindowSystemChrome.NONE;
                options.transparent=false;options.resizable=false;options.minimizable=false;options.maximizable=false;
                var window:NativeWindow=new NativeWindow(options);
                extraWindows.push(window);
                window.title=NativeApplication.nativeApplication.applicationID+"-native-"+renderer;
                window.width=originalStage.stageWidth;window.height=originalStage.stageHeight;
                window.x=originalStage.nativeWindow.x;window.y=originalStage.nativeWindow.y;
                var target:Stage=window.stage;stages.push(target);
                target.scaleMode=originalStage.scaleMode;target.align=originalStage.align;
                target.quality=originalStage.quality;target.color=originalStage.color;target.frameRate=120;
                require(target.stageWidth==originalStage.stageWidth && target.stageHeight==originalStage.stageHeight,"New Stage size differs");
                require(window.renderMode==renderer,"Requested native renderer not accepted");
                report.nativeWindows.push({index:stages.length-1,renderer:window.renderMode,width:target.stageWidth,height:target.stageHeight,quality:target.quality});
            }
        }

        private function switchNativeWindow(index:int):void {
            if(originalStage==null)return;
            require(index>=0 && index<stages.length,"Invalid native window index");
            var target:Stage=stages[index];if(stage===target)return;
            var source:Stage=stage,at:int=getTimer(),count:int=stageRoots.length;
            require(source.numChildren==count && target.numChildren==0,"Unexpected Stage children before transfer");
            var matrices:Array=[],frames:Array=[];
            for(var i:int=0;i<count;++i) {
                var root:DisplayObject=stageRoots[i];
                require(source.getChildAt(i)===root,"Stage root order changed");
                matrices.push(root.transform.matrix.clone());
            }
            for(i=0;i<count;++i)target.addChild(stageRoots[i]);
            world.swfStage=target;stage=target;nativeMode=index;
            source.nativeWindow.visible=false;target.nativeWindow.visible=true;
            require(source.numChildren==0 && target.numChildren==count && world.main.stage===target,"Stage transfer failed");
            require(stage.stageWidth==2032 && stage.stageHeight==1084 && stage.quality===report.stage.quality,"Stage properties changed");
            for(i=0;i<count;++i)require(target.getChildAt(i)===stageRoots[i] && sameMatrix(stageRoots[i].transform.matrix,matrices[i]),"Root matrix/order changed");
            report.stageSwitches.push({index:index,atMs:at,workMs:getTimer()-at,renderer:stage.nativeWindow.renderMode,rootCount:count});
        }

        private function makeRoute():void {''')
    s=one(s,'world.main.stage===stage,"World identities changed"', 'world.main.stage===stage && world.swfStage===stage,"World identities changed"')
    s=s.replace('World display stays visible in every arm; compare only native camera axes.',
        'Same world and animation tree is reparented between native windows; transfers can invoke stage lifecycle callbacks.')
    return s

def runner_source():
    s=(BASE/'run.py').read_text('utf-8-sig').replace('camera-native-gpu-1',VERSION)
    s=s.replace("'--window-width','1296'","'--window-width','2048'").replace("'--window-height','759'","'--window-height','1123'")
    s=s.replace("choices=['normal','scene']", "choices=['scene']")
    start=s.index('def summarize(raw):');end=s.index('\ndef main():',start)
    s=s[:start]+SUMMARY+'\n\n'+s[end:]
    s=s.replace('ContinuousScene / native GPU renderer camera axes / 01a13816','ContinuousScene / same-world native windows / 01a13816')
    s=s.replace('960 native renderer camera-axis intervals; OS pixels and filter compatibility unverified, no deployment',
        '1440 same-world native window intervals; software roundtrip exact, OS pixels unverified, no deployment')
    return s

SUMMARY='''def summarize(raw):
    assert raw['ok'] and raw['error'] is None and not raw['samples']
    cfg=raw['config'];trial=raw['cameraRaster'];cleanup=raw['cameraRasterCleanup']
    assert cfg['drawControl']=='tilecrop' and cfg['presentationCheck'] and cfg['noLighting'] and cfg['noWall'] and not cfg['vision']
    assert trial['version']==VERSION and trial['complete'] and trial['passed'] and not trial['errors']
    assert trial['roomAxis']['continuous'] is (cfg['benchmark']=='scene')
    assert trial['airRenderMode']=='direct' and trial['windowPixelsNotCaptured']
    assert trial['stage']==dict(width=2032,height=1084,quality='HIGH')
    assert [x['renderer'] for x in trial['nativeWindows']]==['direct','direct','auto']
    assert all(x['width']==2032 and x['height']==1084 and x['quality']=='HIGH' for x in trial['nativeWindows'])
    assert cleanup==trial['cleanup'] and cleanup['restored'] and not cleanup['errors'] and cleanup['pendingOwnedBitmaps']==0
    assert cleanup['ownedWindowsCreated']==cleanup['ownedWindowsClosed']==2
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==25
    assert trial['pixelsValid'] and len(trial['pixels'])==5
    for check in trial['pixels']:
        assert check['passed']
        for key in ('nativeRepeat','newDirect','newAuto','restored'):
            c=check[key];assert c['equal'] and c['differentPixels']==c['maxRGB']==c['maxAlpha']==0
    assert trial['testFrameRate']==120 and trial['stabilizationFrames']==12
    assert trial['zeroRasterWork'] and all(v==0 for v in trial['timingRasterDelta'].values())
    assert len(trial['windows'])==12 and len(trial['framesMs'])==len(trial['sampleAtMs'])==1440
    previous=trial['timingStartAtMs'];intervals=[];stamps=[];rows=[]
    names=['original-static','original-moving','direct-static','direct-moving','auto-static','auto-moving']
    initial=trial['timingStart']
    for i,(row,condition) in enumerate(zip(trial['windows'],[0,1,2,3,4,5,5,4,3,2,1,0])):
        assert row['index']==i and row['condition']==condition and row['mode']==names[condition]
        assert row['startAtMs']==previous and row['hidden'] is False and row['moving'] is (condition%2==1)
        for key in ('framesMs','sampleAtMs','vx','vy','cameraX','cameraY','gg','scene','workMs','worldVisible','windowVisible','nativeMode','renderer'):assert len(row[key])==120,key
        assert all(x is True for x in row['worldVisible']+row['windowVisible'])
        assert set(row['nativeMode'])=={condition//2}
        assert set(row['renderer'])=={'auto' if condition>=4 else 'direct'}
        assert (len(set(row['vx']))>1)==row['moving'] and (len(set(row['vy']))>1)==row['moving']
        assert all(v==initial['gg'] for v in row['gg'])
        for scene in row['scene']:
            for key in ('sceneRedraws','sceneDrawMs','sceneResident','sceneEvictions','sceneMisses','sceneWarmCount','sceneWarmSlices','sceneWarmForced'):
                assert scene[key]==initial['scene'][key]
        for stamp,dt in zip(row['sampleAtMs'],row['framesMs']):assert stamp-previous==dt and dt>=0;previous=stamp
        assert row['endAtMs']==previous and row['copiesEnd']==row['copiesStart']==row['allocatedEnd']==row['allocatedStart']==0
        intervals.extend(row['framesMs']);stamps.extend(row['sampleAtMs'])
        rows.append(dict(index=i,mode=row['mode'],frame=metric(row['framesMs']),work=metric(row['workMs'])))
    assert intervals==trial['framesMs'] and stamps==trial['sampleAtMs']
    assert previous==trial['timingEndAtMs'] and sum(intervals)==trial['timingElapsedMs']==previous-trial['timingStartAtMs']
    arms={name:metric([v for row in trial['windows'] if row['mode']==name for v in row['framesMs']]) for name in names}
    pairs=[dict(baseIndex=a,candidateIndex=b,candidateMinusBaseMs=rows[b]['frame']['mean']-rows[a]['frame']['mean']) for a,b in [(1,3),(1,5),(10,8),(10,6),(3,5),(8,6)]]
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,gameplayAcceptance=False,deployed=False,
        airRenderMode='direct',windowPixelsNotCaptured=True,roomAxis=trial['roomAxis'],rows=rows,arms=arms,pairs=pairs,
        viewport=raw['viewport'],world=raw['world'],pixels=trial['pixels'],cleanup=cleanup,stageSwitches=trial['stageSwitches'],
        limits=['Paused simulation, live Flash timelines; not gameplay FPS.','Stage reparenting invokes lifecycle callbacks; original/new direct is a control.',
            'Software Stage.draw is not an OS window capture.','All transfer and observation costs retained in continuous intervals.'])
'''

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for path,code in [(HERE/'tests/SceneCameraRasterTrial.as',helper_source()),(HERE/'run.py',runner_source())]:
        if path.suffix=='.py':ast.parse(code)
        if path.exists():assert path.read_text('utf-8-sig')==code,path
        else:path.write_text(code,'utf-8')
    print('Prepared isolated same-world native window comparison; no build or launch')
