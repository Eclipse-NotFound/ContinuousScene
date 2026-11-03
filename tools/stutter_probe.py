"""Compile a probe comparing legacy/candidate culling in the same game process."""
from pathlib import Path
import sys
import stutter_opt as opt

def once(text,old,new):
    assert text.count(old)==1,(old[:80],text.count(old))
    return text.replace(old,new)

def build(tag):
    base=opt.MOD/'build/generated/stutter-culling-abba-20261103'
    source=(base/'ContinuousSceneMotionMod.as').read_text(encoding='utf-8-sig')
    source=once(source,'import tests.SceneEncounter;',
        'import tests.SceneEncounter;\n    import tests.SceneCullingChecks;\n    import tests.SceneBulletBoundaryChecks;\n    import flash.display.BitmapData;')
    source=once(source,'private static var controls:Object={},csStart:int=0,csMs:int=0;',
        '''private static var controls:Object={},csStart:int=0,csMs:int=0;
        private static var legacy:LegacySceneObjectCulling=new LegacySceneObjectCulling();
        private static var candidateMode:Boolean=true;
        private static function legacyFrame(e:Event):void {if(!candidateMode && w && w.allStat==1)legacy.update(w,true);}
        private static function selectCulling(candidate:Boolean):void {
            if(candidate==candidateMode)return;
            candidateMode=candidate;legacy.clear();api.objectCullingEnabledSet(candidate);
        }
        private static function pixelEquivalence():Object {
            var width:int=main.stage.stageWidth,height:int=main.stage.stageHeight;
            var a:BitmapData=new BitmapData(width,height,true,0),b:BitmapData=new BitmapData(width,height,true,0),result:Object;
            try {
                selectCulling(false);legacy.update(w,true);
                a.draw(w.visual,w.visual.transform.matrix);
                selectCulling(true);
                api.objectCullingController().update(w,true);
                b.draw(w.visual,w.visual.transform.matrix);
                var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect),changed:int=0;
                for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i])++changed;
                check("legacy-candidate-visible-pixels",changed==0,{changed:changed,pixels:av.length});
                result={changed:changed,pixels:av.length};
            } finally {a.dispose();b.dispose();}
            return result;
        }''')
    source=once(source,'if(next>=40)api.objectCullingEnabledSet(Boolean([true,false,false,true,false,true,true,false][scheduleIndex]));',
        '''if(next>=40) {
                var mode:Boolean=Boolean([true,true,false,true,true,false,true,false,false,true][scheduleIndex]);
                if(controls.reverse===true && scheduleIndex>=2)mode=!mode;
                selectCulling(mode);
            }''')
    old='''if(combat)return [{phase:47,frames:200},{phase:48,frames:200},
                {phase:47,frames:200},{phase:48,frames:200},
                {phase:47,frames:200},{phase:48,frames:200},
                {phase:47,frames:200},{phase:48,frames:200}];'''
    new='''if(combat) {
                var steps:Array=[];
                for(var i:int=0;i<10;++i)steps.push({phase:i%2==0?47:48,frames:235});
                return steps;
            }'''
    source=once(source,old,new)
    source=once(source,'report.cullingEnabled=api.objectCullingEnabled();',
        '''report.cullingEnabled=api.objectCullingEnabled();
            check("candidate-controller-version",api.objectCullingStats().version=="event-tracked-1");
            report.cullingChecks=SceneCullingChecks.run(api.objectCullingController().constructor as Class);
            report.pixelEquivalence=pixelEquivalence();
            main.stage.addEventListener(Event.ENTER_FRAME,legacyFrame,false,-200);''')
    source=once(source,'if(done)return;done=true;',
        '''if(done)return;done=true;
            if(g && loc) {
                report.mapRows=[];
                for(var my:int=0;my<loc.spaceY;++my) {
                    var mapRow:String="";
                    for(var mx:int=0;mx<loc.spaceX;++mx)mapRow+=String(loc.getTile(mx,my).phis);
                    report.mapRows.push(mapRow);
                }
            }
            main.stage.removeEventListener(Event.ENTER_FRAME,legacyFrame);legacy.clear();''')
    source=once(source,'window:scheduleIndex,cullingEnabled:api.objectCullingEnabled(),',
        'window:scheduleIndex,warmup:scheduleIndex<2,candidate:candidateMode,cullingEnabled:api.objectCullingEnabled(),')
    source=once(source,'row.presentation=api.scenePresentationStatsV1();row.culling=api.objectCullingStats();',
        'row.presentation=api.scenePresentationStatsV1();row.culling=candidateMode?api.objectCullingStats():legacy.stats();')
    source=source.replace('stutter-culling-abba-20261103-v3','stutter-opt-20261103-'+tag)
    if tag.startswith('qualification-'):
        source=once(source,'            enterPhase(10);',
            '''            report.bulletBoundary=SceneBulletBoundaryChecks.run(w);
            check("offscreen-native-control",report.bulletBoundary.offscreen && report.bulletBoundary.controlValid,report.bulletBoundary);
            check("offscreen-native-hit",report.bulletBoundary.cameraDamage>0,report.bulletBoundary);
            finish();''')
    if tag.startswith('cold-'):
        source=once(source,'ROUTE_X:Number=841.8,ROUTE_Y:Number=4960;',
            'ROUTE_X:Number=6200,ROUTE_Y:Number=2960;')
        # Cold traversal must start after the initial visible area is ready,
        # without waiting for all offscreen preload work to become idle.
        start=source.index('                } else if(phase==10) {')
        end=source.index('                } else if(phase>=40 && phase<=54) {',start)
        source=source[:start]+'''                } else if(phase==10) {
                    require(now-warmStarted<=15000,"Initial viewport preparation timed out");
                    ++warmAge;
                    if(warmAge>=30 && g.sceneViewReady() && player.currentWeapon && player.currentWeapon.id=="lmg") {
                        report.preparationCompletedMs=now-warmStarted;
                        main.stage.frameRate=30;report.testFrameRate=main.stage.frameRate;
                        check("actual-lmg-equipped",true);report.combat.weapon=player.currentWeapon.id;
                        scheduleIndex=0;enterPhase(schedule[0].phase);
                    }
'''+source[end:]
        source=once(source,'''if(combat) {
                var steps:Array=[];
                for(var i:int=0;i<10;++i)steps.push({phase:i%2==0?47:48,frames:235});
                return steps;
            }''','if(combat)return [{phase:47,frames:650},{phase:48,frames:650}];')
        source=once(source,'''var mode:Boolean=Boolean([true,true,false,true,true,false,true,false,false,true][scheduleIndex]);
                if(controls.reverse===true && scheduleIndex>=2)mode=!mode;
                selectCulling(mode);''','selectCulling(true);')
        source=once(source,'warmup:scheduleIndex<2,','warmup:false,')
        source=once(source,'cam=w.cam;g=w.grafon;loc=w.loc;player=w.gg;land=w.land;',
            '''cam=w.cam;g=w.grafon;loc=w.loc;player=w.gg;land=w.land;
            main.getChildByName("ContinuousSceneCarrier")["nativeAPI"].chunkDiagnostics={cancelCount:0,cancelWork:0,applyCalls:0,applyScanned:0,markScanned:0,
                stepCount:0,stepMs:0,maxStepMs:0,warmMs:0,forcedMs:0,syncCount:0,syncMs:0,events:[],dirtyKind:null};''')
        source=once(source,'if(g && loc) {','if(g && loc) {\n                report.chunkDiagnostics=api.chunkDiagnostics;')
        source=once(source,'var row:Object={phase:phase,age:age,dtMs:now-prevAt,',
            'var row:Object={phase:phase,age:age,atMs:now,dtMs:now-prevAt,')
        source=once(source,'            report.samples.push(row);',
            '''            var ds:*=api.chunkDiagnostics;
            row.chunk={cancelCount:ds.cancelCount,cancelWork:ds.cancelWork,warmMs:ds.warmMs,forcedMs:ds.forcedMs,
                syncCount:ds.syncCount,syncMs:ds.syncMs,applyScanned:ds.applyScanned,markScanned:ds.markScanned};
            report.samples.push(row);''')
        source=once(source,'private static var candidateMode:Boolean=true;',
            'private static var candidateMode:Boolean=true;\n        private static var lastMove:Number=NaN,blockedFrames:int=0,jumpFrames:int=0;')
        source=once(source,'                    drivePlayerFire();',
            '''                    drivePlayerFire();
                    if(phase==47 || phase==48) {
                        blockedFrames=Math.abs(player.X-lastMove)<.2?blockedFrames+1:0;lastMove=player.X;
                        if(blockedFrames>=12 && player.stay && jumpFrames<=0){jumpFrames=8;blockedFrames=0;}
                        w.ctr.keyJump=jumpFrames>0;if(jumpFrames>0)--jumpFrames;
                    }''')
    if tag.startswith('timing-'):
        source=once(source,'api.activity=observedActivity;api.wake=observedWake;',
            '// Timing pass: keep native activity callbacks unchanged.')
        start=source.index('            row.activity=api.activityStats();')
        end=source.index('            report.samples.push(row);',start)
        source=source[:start]+source[end:]
        source=once(source,'report.ok=error==null;report.error=error;',
            'report.ok=error==null;report.performanceEligible=error==null;report.error=error;')
    if tag.startswith('timing-nofire-'):
        source=once(source,'private static function firing():Boolean {return (phase>=46 && phase<=48) || (phase>=50 && phase<=53);}',
            'private static function firing():Boolean {return false;}')
    legacy=(opt.WORK/'baseline-src/SceneObjectCulling.as').read_text(encoding='utf-8-sig').replace('SceneObjectCulling','LegacySceneObjectCulling')
    sources={'ContinuousSceneMotionMod.as':source,'LegacySceneObjectCulling.as':legacy,
        'ProbeDoc.as':(base/'ProbeDoc.as').read_text(encoding='utf-8-sig'),
        'tests/SceneEncounter.as':(base/'tests/SceneEncounter.as').read_text(encoding='utf-8-sig'),
        'tests/SceneBulletBoundaryChecks.as':(opt.MOD/'src/tests/SceneBulletBoundaryChecks.as').read_text(encoding='utf-8-sig'),
        'tests/SceneCullingChecks.as':(opt.MOD/'src/tests/SceneCullingChecks.as').read_text(encoding='utf-8-sig')}
    opt.compile_sources(tag,sources,'ProbeDoc.as','ContinuousSceneMotionMod.swf',False)

if __name__=='__main__':build(sys.argv[1])
