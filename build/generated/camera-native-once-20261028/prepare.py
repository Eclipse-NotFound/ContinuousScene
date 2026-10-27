"""Schedule targets before native World.step; no extra timed Camera.calc call."""
from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-environment-quiet-20261027'
VERSION='camera-native-once-1'

def load(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=load('native_once_base_generator',BASE/'prepare.py');one=base.one

def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'    import flash.display.Stage;','    import flash.display.Stage;\n    import flash.events.Event;')
    s=one(s,'        private var closed:Boolean=false;',
        '        private var closed:Boolean=false;\n        private var cameraHookAdded:Boolean=false;\n        private var plannedSegment:int=-1;\n        private var plannedAge:int=-1;')
    s=one(s,'                framesMs:[],sampleAtMs:[],prepareMs:0,prepareWorkMs:0,pixelMs:0,',
        '                framesMs:[],sampleAtMs:[],prepareMs:0,prepareWorkMs:0,pixelMs:0,\n                nativeSchedules:0,nativeCaptures:0,helperTimedCalcCalls:0,')
    s=one(s,'intervalMeaning:"Applied camera/crop work, next actual frame presentation, then next step entry. No segment-clock resets."',
        'intervalMeaning:"Outgoing native camera state, frame presentation, then next native step and observer entry. Boundary intervals retained; no extra timed helper Camera.calc or segment-clock resets."')
    s=one(s,'                prepareBaseline=counters();report.preparePasses=[];',
        '''                prepareBaseline=counters();report.preparePasses=[];
                // Native MainMenu.mainStep listens on this same Stage at priority 0.
                // Actual camera coordinates are checked after World.step, at priority -1000.
                stage.addEventListener(Event.ENTER_FRAME,beforeNative,false,500);
                cameraHookAdded=true;''')
    s=one(s,'''                        report.fogTimingStart=fogState();report.stabilizationFrames=settle;report.timingStart=snapshot();
                        phase=3;previous=getTimer();report.timingStartAtMs=previous;
                        startWindow();applyFrame();
                    }
                } else if(phase==3) {''',
        '''                        report.stabilizationFrames=settle;phase=31;
                    }
                } else if(phase==31) {
                    // Prime one native frame before starting the measured outgoing intervals.
                    report.fogTimingStart=fogState();report.timingStart=snapshot();
                    phase=3;previous=getTimer();report.timingStartAtMs=previous;
                    startWindow();applyFrame();
                } else if(phase==3) {''')
    s=one(s,'                            report.fogTimingEnd=fogState();report.complete=true;report.passed=true;clear(w);',
        '''                            require(report.nativeSchedules==961 && report.nativeCaptures==960 && report.helperTimedCalcCalls==0,"Native camera schedule/count mismatch");
                            report.fogTimingEnd=fogState();report.complete=true;report.passed=true;clear(w);''')
    s=one(s,'            closed=true;\n            var at:int=getTimer();',
        '''            closed=true;
            if(cameraHookAdded && stage!=null)stage.removeEventListener(Event.ENTER_FRAME,beforeNative);
            cameraHookAdded=false;
            var at:int=getTimer();''')
    s=one(s,'            cleanup.pendingOwnedBitmaps=owned.length;',
        '            cleanup.cameraHookRemoved=!cameraHookAdded;\n            cleanup.pendingOwnedBitmaps=owned.length;')
    s=one(s,'            applyCamera(point.x,point.y);\n            require(grafon.sceneViewReady(),"Unprepared viewport during timing");',
        '''            require(plannedSegment==segment && plannedAge==age,"Native schedule was not consumed at the intended sample");
            require(cam.X==point.x && cam.Y==point.y,"Native camera did not consume the scheduled target");
            ++report.nativeCaptures;
            require(grafon.sceneViewReady(),"Unprepared viewport during timing");''')
    s=one(s,'        private function applyCamera(x:Number,y:Number):void {',
        '''        private function beforeNative(event:Event):void {
            if(closed || (phase!=31 && phase!=3))return;
            try {
                require(event.currentTarget===stage,"Wrong native camera event source");
                var nextSegment:int=segment,nextAge:int=phase==31?0:age+1;
                if(nextAge==120) {
                    if(nextSegment+1<order.length){++nextSegment;nextAge=0;}
                    else nextAge=119; // Final interval still includes one native update.
                }
                var condition:int=order[nextSegment];
                var target:Object=condition==0?views[0]:route[nextAge];
                var x:Number=condition==2?views[0].x:target.x;
                var y:Number=condition==1?views[0].y:target.y;
                require(x==Math.floor(x) && y==Math.floor(y),"Non-integer scheduled camera");
                cam.X=x;cam.Y=y;cam.camRun=true;cam.quakeX=0;cam.quakeY=0;
                world.ctr.keyLook=false;world.ctr.keyZoom=false;
                plannedSegment=nextSegment;plannedAge=nextAge;++report.nativeSchedules;
            } catch(error:Error) {fail(error);}
        }

        private function applyCamera(x:Number,y:Number):void {
            if(phase==31 || phase==3) {
                ++report.helperTimedCalcCalls;
                throw new Error("Extra helper Camera.calc during native-only measurement");
            }''')
    assert s.count('cam.calc(player)')==1
    return s

def runner_source():
    return base.runner_source().replace(base.VERSION,VERSION)

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared native-only timed camera scheduling; no build or game launch')
