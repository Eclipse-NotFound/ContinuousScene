"""Apply the isolated low-interference dense-sprint fixture to copied sources.

Only two existing files change. The source-only alicorn patch and all other
helpers remain byte-for-byte copied inputs; no production SWF is rebuilt here.
"""
from pathlib import Path
import shutil


def replace_once(text, old, new):
    assert text.count(old) == 1, ('Review changed source anchor', old)
    return text.replace(old, new, 1)


def transform_motion(text):
    changes = [
        ('    import tests.SceneEncounter;', '    import tests.SceneEncounter;\n    import tests.SceneDenseCombatMetrics;'),
        ('        private static var encounter:SceneEncounter;', '        private static var encounter:SceneEncounter;\n        private static var denseMetrics:SceneDenseCombatMetrics=new SceneDenseCombatMetrics();'),
        ('for(var rcCase:int=0;rcCase<20;++rcCase)', 'for(var rcCase:int=0;rcCase<4;++rcCase)'),
        ('cfg.drawControl=="rcnative"?"rc-native-"+rcCase', 'cfg.drawControl=="rcnative"?"dense-native-"+rcCase'),
        (' || cfg.visual || cfg.nativeSprint)', ' || cfg.visual || !cfg.nativeSprint)'),
        ('Native input fixture requires fixed combat actors and player fire; visual teleport and sprint are unsupported', 'Dense fixture requires native sprint, fixed native shooters, and no visual teleport'),
        ('version:"native-input-motion-3"', 'version:"native-input-dense-sprint-2"'),
        ('Native walking and combat knockback; no sprint/jump input, no fixed-speed or phase-locked motion', 'Native sprint input and combat knockback; stamina unchanged; no jump, fixed speed, or position reset'),
        ('w.ctr.keyRun=false;w.ctr.keyJump=false;w.ctr.keyDash=false;', 'w.ctr.keyRun=moving && Boolean(cfg.nativeSprint);w.ctr.keyJump=false;w.ctr.keyDash=false;'),
        ('nativeInputPlayer=w.gg;', 'nativeInputPlayer=w.gg;\n                        denseMetrics.bind(w,encounter.actorUnits());\n                        report.denseFixture={version:"dense-sprint-2",actors:6,enemyWeapon:"lmg",playerWeapon:"assr",jumpInput:false,staminaRefilled:false,positioning:"one spawn only",sampling:"read-only per-frame object scan; cost retained",limitations:"Six durable HP100000 actors with damage2; player ammo/durability refill and godMode inherited; native firing cadence, reload, physics and AI retained"};\n                        report.observerPolicy={version:"dense-observer-lean-2",settingsDuringTiming:false,segmentProgressWrites:false,segmentCensus:false,finalCensus:true,heartbeatIntervalMs:5000,continuousFramesRetained:true};'),
        ('row.combatWindows=[];', 'row.combatWindows=[];row.denseFrames=denseMetrics.bucket();'),
        ('if(cfg.nativeInputMotion)recordNativeMotion(row.nativeInputMotion,30);', 'if(cfg.nativeInputMotion) {\n                        var densePose:Object=recordNativeMotion(row.nativeInputMotion,30);\n                        denseMetrics.sample(w,row.denseFrames,densePose);\n                    }'),
        ('if(age<(cfg.sleepingRootShort || cfg.drawControl=="rcoffline" || cfg.drawControl=="rcnative"?60:300))return;', 'if(age<(cfg.sleepingRootShort || cfg.drawControl=="rcoffline"?60:300))return;'),
        ('w.cam.celX=w.gg.X*w.cam.scaleV+w.cam.vx+450;', 'w.cam.celX=w.gg.X*w.cam.scaleV+w.cam.vx+450*nativeDirection;'),
        ('Ctr.keyLeft/keyRight; native acceleration, vertical physics and collision', 'Ctr.keyLeft/keyRight/keyRun; native acceleration, vertical physics and collision'),
    ]
    for old, new in changes:
        text = replace_once(text, old, new)
    # All four windows have the same display settings. Phase1 already applied
    # them before warmup: repeating setters here can synchronously persist them.
    text = replace_once(text, '''            setting("light-and-darkness","enabled",!cfg.noLighting && (cfg.sleepingRootShort || cfg.drawControl=="rcoffline" || cfg.drawControl=="rcnative" || index!=4));
            setting("wallblend","enabled",!cfg.noWall && (cfg.sleepingRootShort || cfg.drawControl=="rcoffline" || cfg.drawControl=="rcnative" || index!=6));''', '''            // Dense v2: phase1 settings remain unchanged through all windows.''')
    text = replace_once(text, '''        private static function setting(mod:String,key:String,value:*):void {
''', '''        private static function setting(mod:String,key:String,value:*):void {
            if(continuousPreviousSampleAt>=0)throw new Error("Dense v2 forbids settings mutation after timing starts");
''')
    text = replace_once(text, 'report.samples.push(row);save("progress.json",report);', 'report.samples.push(row); // Dense v2: short heartbeat only during sampling.')
    text = replace_once(text, '''                        var censusBegin:int=getTimer();
                        try {row.activityCensus=SceneActivityCensus.read(w);}
                        finally {if(probeTimingRow!=null)probeTimingCensus+=getTimer()-censusBegin;}
''', '''                        // Dense v2: one full census after the last wall-time sample.
''')
    # This is explicitly outside the continuous sample series. The terminal
    # native frame is still retained; no interval is deleted or corrected.
    text = replace_once(text, '''            closeProbeTiming(true);
            if(rcOffline) {''', '''            closeProbeTiming(true);
            if(error==null && report.samples.length==4 && w && w.grafon.sceneLarge) {
                try {
                    report.finalActivityCensus={startedAtMs:getTimer(),afterFinalSample:true};
                    report.finalActivityCensus.data=SceneActivityCensus.read(w);
                    report.finalActivityCensus.endedAtMs=getTimer();
                } catch(finalCensusError:*) {error="Final dense census failed: "+String(finalCensusError);}
            }
            if(rcOffline) {''')
    return text


def transform_encounter(text):
    text = replace_once(text, 'new Raider("1",4,null,{weap:"autor",tr:1})', 'new Raider("1",4,null,{weap:"lmg",tr:1})')
    return replace_once(text, '        public function sample():void {', '''        public function actorUnits():Array {
            var out:Array=[];for each(var actor:Object in actors)out.push(actor.unit);return out;
        }
        public function sample():void {''')


def prepare(source: Path, destination: Path):
    assert not destination.exists(), 'Never overwrite frozen sources'
    shutil.copytree(source, destination)
    for name, transform in (('ContinuousSceneMotionProbe.as', transform_motion), ('tests/SceneEncounter.as', transform_encounter)):
        path = destination / name
        path.write_text(transform(path.read_text('utf-8-sig')), 'utf-8')
    shutil.copy2(Path(__file__).with_name('SceneDenseCombatMetrics.as'), destination / 'tests/SceneDenseCombatMetrics.as')
