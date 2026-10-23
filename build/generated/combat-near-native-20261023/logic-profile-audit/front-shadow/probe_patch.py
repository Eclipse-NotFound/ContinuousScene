"""Front-buffer shadow experiment over a copied lean-v2 dense probe only.

Head chooses and retains the control; tail never derives it from the advanced
case index. Primary intervals end after the real tail update, including switches.
"""
from pathlib import Path
import shutil


def once(text, old, new):
    assert text.count(old) == 1, ('Source anchor drift', old)
    return text.replace(old, new, 1)


FIELDS = '''
        private static var frontShadow:SceneFrontShadowProbe=new SceneFrontShadowProbe();
        private static var frontStarted:Boolean=false,frontPrepared:Boolean=false,frontMode:Boolean=false;
        private static var frontWindow:int=-99,frontFrameRow:Object=null,frontSampleRow:Object=null,frontSampleSlot:int=-1;
        private static var frontFinishPending:Boolean=false,frontFinishError:String=null,frontInTail:Boolean=false;
        private static var frontVerifyPending:Boolean=false,frontQuiet:int=0,frontQuietKey:String=null;
        private static var frontObserved:Object=null;
'''

METHODS = '''
        private static function frontCopy(value:*):* {return JSON.parse(JSON.stringify(value));}
        private static function frontWarmCounters():Object {
            var result:Object={};
            for each(var key:String in ["sceneResident","sceneWarmCount","sceneWarmSlices","sceneWarmForced","sceneRedraws","sceneEvictions","sceneMisses"])
                result[key]=Number(w.grafon[key]);
            return result;
        }
        private static function frontRestoreView(saved:Object):void {
            w.cam.vx=saved.vx;w.cam.vy=saved.vy;
            w.cam.screenX=saved.screenX;w.cam.screenY=saved.screenY;
            w.cam.scaleV=saved.scaleV;w.cam.quakeX=saved.quakeX;w.cam.quakeY=saved.quakeY;
        }
        private static function frontPrewarmBeforeActors():void {
            var began:int=getTimer();
            if(report.frontShadowPrewarm || encounter || !nativeInputRoute || !w.grafon.sceneLarge || w.grafon.scenePreload)
                throw new Error("Front prewarm requires the verified route before encounter creation");
            var g:*=w.grafon,c:*=w.cam;
            if(Number(c.scaleV)!=1 || c.otryv!=0 || c.camRun)
                throw new Error("Front prewarm only covers the ordinary scale1 player-follow camera");
            var saved:Object={vx:c.vx,vy:c.vy,screenX:c.screenX,screenY:c.screenY,scaleV:c.scaleV,
                quakeX:c.quakeX,quakeY:c.quakeY,asyncWarm:g.sceneAsyncWarm};
            var player:Object={X:w.gg.X,Y:w.gg.Y,dx:w.gg.dx,dy:w.gg.dy,units:loc.units.length};
            var originalView:Rectangle=g.sceneViewport();
            if(!originalView)throw new Error("Front prewarm needs the native viewport");
            // Native player-follow camera: top=Y-screenY/2-100, two-cell warm ring.
            // The extra80 covers normal shake/rounding. Leaving this tested envelope
            // still triggers the original helper's strict counter/identity abort.
            var margin:int=640+80;
            var left:Number=Math.min(originalView.left-margin,nativeInputRoute.safeCenterRange.left-c.screenX/2-margin);
            var right:Number=Math.max(originalView.right+margin,nativeInputRoute.safeCenterRange.right+c.screenX/2+margin);
            var top:Number=Math.min(originalView.top-margin,nativeInputRoute.verifiedBounds.top-c.screenY/2-100-margin);
            var bottom:Number=Math.max(originalView.bottom+margin,nativeFloorY+c.screenY/2-100+margin);
            left=Math.max(0,Math.floor(left/320)*320);top=Math.max(0,Math.floor(top/320)*320);
            right=Math.min(loc.limX,Math.ceil(right/320)*320);bottom=Math.min(loc.limY,Math.ceil(bottom/320)*320);
            var requested:Rectangle=new Rectangle(left,top,right-left,bottom-top),keys:Object={},count:int=0;
            for each(var surface:Object in g.sceneSurfaces())keys[surface.cx+":"+surface.cy]=true;
            for(var cx:int=int(left/320);cx<Math.ceil(right/320);++cx)
                for(var cy:int=int(top/320);cy<Math.ceil(bottom/320);++cy)keys[cx+":"+cy]=true;
            for(var key:String in keys)++count;
            if(count+2>256)throw new Error("Front prewarm would exceed the reviewed resident bound");
            var pre:Object={version:"front-shadow-native-prewarm-1",beforeEncounter:true,worldStepsCalled:0,
                loadingBenchmark:false,performanceAcceptance:false,scenePreloadUsed:false,
                api:"Grafon.sceneTick with temporary viewport; native synchronous sceneRender path",
                initialView:{x:originalView.x,y:originalView.y,width:originalView.width,height:originalView.height},
                requestedView:{x:left,y:top,width:requested.width,height:requested.height},estimatedResidentUpperBound:count+2,
                savedCamera:saved,playerBefore:player,before:frontWarmCounters(),calls:0,drained:false,restored:false};
            report.frontShadowPrewarm=pre;
            try {
                g.sceneAsyncWarm=false;c.vx=-left;c.vy=-top;c.screenX=requested.width;c.screenY=requested.height;
                c.quakeX=c.quakeY=0;
                g.sceneTick();++pre.calls;
                frontRestoreView(saved);
                // Finish an already-existing native warm job without running a
                // World/native frame or creating the six fixture shooters first.
                for(var drain:int=0;drain<64;++drain) {
                    var priorSlices:Number=Number(g.sceneWarmSlices);
                    g.sceneTick();++pre.calls;
                    if(Number(g.sceneWarmSlices)==priorSlices && g.sceneViewReady()){pre.drained=true;break;}
                }
                if(!pre.drained)throw new Error("Front native prewarm did not drain the existing job");
            } finally {
                frontRestoreView(saved);g.sceneAsyncWarm=saved.asyncWarm;
                try {g.sceneTick();++pre.calls;}
                finally {
                    pre.after=frontWarmCounters();pre.testPreparationMs=getTimer()-began;
                    pre.viewReady=g.sceneViewReady();
                    pre.restored=c.vx===saved.vx && c.vy===saved.vy && c.screenX===saved.screenX && c.screenY===saved.screenY &&
                        c.scaleV===saved.scaleV && c.quakeX===saved.quakeX && c.quakeY===saved.quakeY && g.sceneAsyncWarm===saved.asyncWarm;
                    pre.playerUnchanged=w.gg.X===player.X && w.gg.Y===player.Y && w.gg.dx===player.dx && w.gg.dy===player.dy && loc.units.length===player.units;
                    pre.endedAtMs=getTimer();
                }
            }
            if(!pre.restored || !pre.playerUnchanged || !pre.viewReady || g.sceneResident>256)
                throw new Error("Front native prewarm failed restoration/unchanged-actor checks");
        }
        private static function frontHealthy(state:Object):void {
            if(!state.started || state.closed || state.aborted)
                throw new Error("Front shadow rejected current state: "+JSON.stringify(state));
        }
        private static function frontObserveQuiet():void {
            var keys:Array=["sceneResident","sceneWarmCount","sceneWarmSlices","sceneWarmForced","sceneRedraws","sceneEvictions","sceneMisses"];
            var values:Array=[],observed:Object={},changes:Array=[];
            if(!report.frontShadowPreparation)report.frontShadowPreparation={version:"front-shadow-preparation-2",
                frames:0,maxGroundRun:0,maxQuietFrames:0,readyFrames:0,rejections:{},counterChanges:{},history:[]};
            var preparation:Object=report.frontShadowPreparation;
            var changeCounts:Object=preparation.counterChanges;
            for each(var key:String in keys) {
                var value:Number=Number(w.grafon[key]);
                if(!isFinite(value))throw new Error("Missing front shadow stability counter "+key);
                values.push(value);observed[key]=value;
                if(frontObserved && value!==Number(frontObserved[key])) {
                    changes.push({key:key,before:frontObserved[key],after:value});
                    changeCounts[key]=int(changeCounts[key])+1;
                }
            }
            var next:String=values.join(":");
            frontQuiet=next==frontQuietKey && w.grafon.sceneViewReady()?frontQuiet+1:0;
            frontQuietKey=next;frontObserved=observed;
            ++preparation.frames;preparation.lastCounterChanges=changes;
            if(!preparation.firstCounters)preparation.firstCounters=observed;
        }
        private static function frontRecordReadiness(pose:Object):void {
            var preparation:Object=report.frontShadowPreparation,reasons:Array=[];
            var viewReady:Boolean=w.grafon.sceneViewReady();
            var weapon:String=w.gg.currentWeapon?String(w.gg.currentWeapon.id):null;
            var weaponWork:Number=Number(w.gg.t_work);
            if(nativeGroundRun<10)reasons.push("ground-contact-run-under-10");
            if(frontQuiet<20)reasons.push("stable-counters-run-under-20");
            if(!viewReady)reasons.push("view-not-ready");
            if(weapon!="assr")reasons.push("weapon-not-assr");
            if(!(weaponWork<=0))reasons.push("weapon-t-work-not-ready");
            var rejectionCounts:Object=preparation.rejections;
            for each(var reason:String in reasons)
                rejectionCounts[reason]=int(rejectionCounts[reason])+1;
            preparation.maxGroundRun=Math.max(preparation.maxGroundRun,nativeGroundRun);
            preparation.maxQuietFrames=Math.max(preparation.maxQuietFrames,frontQuiet);
            preparation.last={frame:preparation.frames,age:age,groundRun:nativeGroundRun,quietFrames:frontQuiet,
                viewReady:viewReady,weapon:weapon,t_work:weaponWork,work:String(w.gg.work),
                X:w.gg.X,Y:w.gg.Y,dx:w.gg.dx,dy:w.gg.dy,stay:w.gg.stay,floorContact:pose.floorContact,
                warmCounters:frontObserved,reasons:reasons,ready:reasons.length==0};
            if(reasons.length==0) {
                ++preparation.readyFrames;if(!preparation.firstReady)preparation.firstReady=preparation.last;
            }
            if(preparation.frames%30==0)preparation.history.push(preparation.last);
        }
        private static function frontStart():void {
            if(frontStarted)return;
            frontStarted=true;report.frontShadowSetup=frontCopy(frontShadow.start(w));
            frontHealthy(report.frontShadowSetup);
            report.frontShadowSetup.quietFramesBeforeStart=frontQuiet;
        }
        private static function frontHead():void {
            frontFrameRow=null;frontSampleRow=null;frontSampleSlot=-1;frontPrepared=false;
            if(done || !frontStarted || frontFinishPending || (phase!=4 && phase!=108))return;
            try {
                var selected:int=phase==108?-2:index;
                frontMode=phase==108 || selected%4==1 || selected%4==2;
                frontFrameRow=phase==4?row:null;
                if(frontWindow!=selected) {
                    var headAt:int=getTimer();
                    if(frontFrameRow) {
                        frontFrameRow.tickCaseBeginAtMs=frontFrameRow.caseBeginAtMs;
                        frontFrameRow.caseBeginAtMs=headAt;
                        if(selected==0 && !report.continuousSampling.primeTailAtMs)
                            throw new Error("Front timing did not establish the preceding tail");
                    }
                    var beginState:Object=frontShadow.beginWindow(w,frontMode);
                    frontHealthy(beginState);frontWindow=selected;
                    if(frontFrameRow)frontFrameRow.frontShadow={index:selected,enabled:frontMode,
                        beginAtMs:headAt,headModes:[],tailModes:[],headIndices:[],tailIndices:[],
                        beforeTotals:frontCopy(beginState.totals)};
                }
                if(frontFrameRow) {
                    frontFrameRow.frontShadow.headModes.push(frontMode);
                    frontFrameRow.frontShadow.headIndices.push(selected);
                }
                frontShadow.prepareFrame(w);frontPrepared=true;
                frontHealthy(frontShadow.snapshot());
            } catch(error:*) {frontFinishPending=true;frontFinishError="Front head: "+String(error);}
        }
        private static function frontTail():void {
            if(done || !frontStarted)return;
            if(!frontPrepared && frontWindow==-99 && phase==4 && !frontFinishPending) {
                var primeTail:int=getTimer();
                report.continuousSampling.preparationStartedAtMs=report.continuousSampling.startedAtMs;
                report.continuousSampling.primeTailAtMs=primeTail;
                report.continuousSampling.startedAtMs=primeTail;continuousPreviousSampleAt=primeTail;
            }
            var state:Object=null;
            try {
                if(frontPrepared) {
                    frontShadow.update(w,frontMode);frontPrepared=false;
                    state=frontShadow.snapshot();frontHealthy(state);
                    if(frontFrameRow) {
                        frontFrameRow.frontShadow.tailModes.push(frontMode);
                        frontFrameRow.frontShadow.tailIndices.push(frontWindow);
                        if(frontSampleSlot==59) {
                            frontFrameRow.frontShadow.end={window:frontCopy(state.windows[state.windows.length-1]),
                                totals:frontCopy(state.totals),aborted:state.aborted,heldBindings:state.heldBindings,
                                prepared:state.prepared,currentEnabled:state.currentEnabled};
                        }
                    }
                    if(phase==108)++report.frontShadowCheck.tailFrames;
                }
            } catch(error:*) {frontFinishPending=true;frontFinishError="Front tail: "+String(error);}
            // Finalize this frame's original row even when tick replaced the global row.
            if(frontSampleRow && frontSampleSlot>=0) {
                var sampledAt:int=getTimer(),dt:int=sampledAt-continuousPreviousSampleAt;
                frontSampleRow.sampleAtMs[frontSampleSlot]=sampledAt;
                frontSampleRow.continuousFramesMs[frontSampleSlot]=dt;
                frontSampleRow.frames[frontSampleSlot]=dt;continuousPreviousSampleAt=sampledAt;
                if(frontSampleSlot==59)frontSampleRow.caseEndAtMs=sampledAt;
            }
            if(frontVerifyPending && !frontFinishPending) {
                try {
                    report.frontShadowVerification=frontShadow.verify(w);
                    var proof:Object=report.frontShadowVerification;
                    check("front-shadow-pixels",proof.valid && proof.equal && proof.restored,proof);
                    check("front-shadow-real-tail-sync",proof.tailImageChecked && proof.tailSyncsObserved>0 && proof.tailImage && proof.tailImage.equal,proof);
                    check("front-shadow-thirty-native-frames",report.frontShadowCheck.nativeFrames==30 && report.frontShadowCheck.tailFrames==30,report.frontShadowCheck);
                    check("front-shadow-component-real-fire",report.frontShadowCheck.playerShots>0 && report.frontShadowCheck.enemyShots>0,report.frontShadowCheck);
                } catch(verifyError:*) {frontFinishError="Front verification: "+String(verifyError);}
                frontFinishPending=true;
            }
        }
        private static function frontFinishTail():void {
            if(frontFinishPending && !done) {frontInTail=true;finish(frontFinishError);}
        }
'''


def transform_motion(text):
    changes = [
        ('    import tests.SceneEncounter;', '    import tests.SceneEncounter;\n    import tests.SceneFrontShadowProbe;'),
        ('        private static var encounter:SceneEncounter;', '        private static var encounter:SceneEncounter;' + FIELDS),
        ('for(var rcCase:int=0;rcCase<4;++rcCase)', 'for(var rcCase:int=0;rcCase<20;++rcCase)'),
        ('if(age<(cfg.sleepingRootShort || cfg.drawControl=="rcoffline"?60:300))return;', 'if(age<60)return;'),
        ('report.samples.length==4 && w && w.grafon.sceneLarge', 'report.samples.length==20 && w && w.grafon.sceneLarge'),
        ('absoluteStart=getTimer();rasterPresentation.beginFrame();', 'absoluteStart=getTimer();frontHead();rasterPresentation.beginFrame();'),
        ('{lastEnd=getTimer();completeProbeTimingTail(lastEnd);}', '{frontTail();lastEnd=getTimer();completeProbeTimingTail(lastEnd);frontFinishTail();}'),
        ('        private static function finish(error:String=null):void {', METHODS + '''
        private static function finish(error:String=null):void {
            if(frontStarted && !frontInTail && !done) {
                frontFinishPending=true;if(error!=null)frontFinishError=error;return;
            }'''),
        ('            closeProbeTiming(true);', '''            closeProbeTiming(true);
            if(frontStarted) {
                report.frontShadowCleanup=frontShadow.clear();
                report.frontShadowFinal=frontCopy(frontShadow.snapshot());
                if(report.frontShadowFinal.aborted || !report.frontShadowCleanup.restored ||
                    report.frontShadowCleanup.heldBindings || report.frontShadowCleanup.leakedClones!=0 ||
                    report.frontShadowCleanup.nativeDataDisposed!=0 || report.frontShadowCleanup.cleanupErrors!=0)
                    error=(error?error+"\\n":"")+"Front shadow aborted or failed restoration";
            }'''),
        ('        private static function startCase():void {', '''        private static function startCase():void {
            frontStart();
            report.frontShadowTiming={version:"front-shadow-tail-sampling-2",order:[false,true,true,false],
                windows:20,windowFrames:60,headPriority:2147483647,tailPriority:-2147483647,
                controlAlias:"rcnative",primaryEndsAfterTail:true,includesTransitions:true,
                initialAllocationOutsideTiming:true,finalCleanupOutsideTiming:true,tickEvidenceRetained:true,firstIntervalTailToTail:true};'''),
        ('row.sampleAtMs=[];row.continuousFramesMs=[];row.caseBeginAtMs=caseBegin;',
         'row.sampleAtMs=[];row.continuousFramesMs=[];row.tickSampleAtMs=[];row.tickFramesMs=[];row.caseBeginAtMs=caseBegin;'),
        ('                }else if(phase==3) {', '                }else if(phase==3) {\n                    frontObserveQuiet();'),
        ('                    if(cfg.encounter){encounter=new SceneEncounter(w);',
         '                    frontPrewarmBeforeActors();\n                    if(cfg.encounter){encounter=new SceneEncounter(w);'),
        ('                    if(cfg.drawControl=="backgrounds") {\n                        if(!cfg.presentationCheck', '''                    frontRecordReadiness(warmMotion);
                    if(cfg.presentationCheck && cfg.drawControl=="rcnative") {
                        if(w.loc!==loc || w.allStat!=1 || w.onPause || w.t_exit!=0)
                            throw new Error("Front shadow component lost active native world");
                        if(report.frontShadowPreparation.last.ready) {
                            report.frontShadowCheck={version:"front-shadow-native-component-1",groundContactRun:nativeGroundRun,
                                quietFrames:frontQuiet,startPose:warmMotion,nativeFrames:0,tailFrames:0,
                                playerShotStart:playerShotFrames,enemyShotStart:encounter.actualShotFrames,
                                nativeMotion:newNativeMotionBucket()};
                            frontStart();phase=108;age=0;
                            driveNativeInput(false);drivePlayerFire();return;
                        }
                        if(++age>600)throw new Error("Front shadow component did not settle on native ground");
                        driveNativeInput(false);return;
                    }
                    if(cfg.drawControl=="backgrounds") {
                        if(!cfg.presentationCheck'''),
        ('                    report.lastWarm=w.grafon.sceneWarmCount;report.lastDraw=w.grafon.sceneDrawMs;startCase();\n', '''                    if(frontQuiet<20){driveNativeInput(true);drivePlayerFire();return;}
                    report.lastWarm=w.grafon.sceneWarmCount;report.lastDraw=w.grafon.sceneDrawMs;startCase();
'''),
        ('                }else if(phase==95) {', '''                }else if(phase==108) {
                    if(w.loc!==loc || w.allStat!=1 || w.onPause || w.t_exit!=0 || !w.grafon.sceneViewReady())
                        throw new Error("Front shadow component lost active complete scene");
                    encounter.sample();samplePlayerFire();
                    recordNativeMotion(report.frontShadowCheck.nativeMotion,30);
                    ++report.frontShadowCheck.nativeFrames;++age;
                    report.frontShadowCheck.playerShots=playerShotFrames-report.frontShadowCheck.playerShotStart;
                    report.frontShadowCheck.enemyShots=encounter.actualShotFrames-report.frontShadowCheck.enemyShotStart;
                    w.ctr.clearAll();driveNativeInput(false);drivePlayerFire();
                    if(age>=30)frontVerifyPending=true;
                    return;
                }else if(phase==95) {'''),
        ('                    row.sampleAtMs.push(now);row.continuousFramesMs.push(now-continuousPreviousSampleAt);\n                    continuousPreviousSampleAt=now;', '''                    if(frontFrameRow!==row)throw new Error("Front shadow head did not select measured row");
                    frontSampleRow=row;frontSampleSlot=row.frames.length;
                    row.tickSampleAtMs.push(now);row.tickFramesMs.push(now-last);
                    row.sampleAtMs.push(0);row.continuousFramesMs.push(0);'''),
        ('                    row.frames.push(now-last);last=now;', '                    row.frames.push(0);last=now;'),
        ('                    row.caseEndAtMs=getTimer();', '                    row.tickCaseEndAtMs=getTimer();'),
    ]
    for old, new in changes:
        text = once(text, old, new)
    return text


def prepare(source, destination, dense_patcher, helper):
    dense_patcher.prepare(source, destination)
    path = Path(destination) / 'ContinuousSceneMotionProbe.as'
    text = transform_motion(path.read_text('utf-8-sig'))
    path.write_text(text, 'utf-8')
    shutil.copy2(helper, Path(destination) / 'tests/SceneFrontShadowProbe.as')
