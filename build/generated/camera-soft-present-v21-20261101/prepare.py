from pathlib import Path
import shutil

here=Path(__file__).resolve().parent
root=here.parents[4]
base=here.parent/'camera-static-groups-v15-20261101'
src=(base/'ContinuousSceneMotionMod.as').read_text('utf-8')
src=src.replace('import flash.display.BitmapData;', 'import flash.display.BitmapData;\n    import flash.display.PNGEncoderOptions;\n    import tests.SceneEncounter;\n    import tests.SceneCombatRoute;')
src=src.replace('private static var fill:StaticObjectGroups=new StaticObjectGroups();', 'private static var fill:ScreenPresenter=new ScreenPresenter();\n        private static var encounter:SceneEncounter;\n        private static var shotLast:int=0,shotDelta:int=0;')
src=src.replace('camera-static-groups-15','camera-soft-present-21')
src=src.replace('preAt=getTimer();','preAt=getTimer();\n            fill.restore();')
src=src.replace('var placement:Object=CameraProbePlatform.select(w,2200,2200);', 'var placement:Object=options.dense?SceneCombatRoute.select(w,2200,2200,200):CameraProbePlatform.select(w,2200,2200);')
src=src.replace('report.placement=placement;', 'report.placement=placement;\n            if(options.dense){encounter=new SceneEncounter(w);report.encounter=encounter.prepare(placement.x,placement.y,true,false,true,placement);assertThat("six-enemy-fixture",report.encounter.units.length==6,report.encounter);}')
src=src.replace('centerX=player.X*cam.scaleV;', 'centerX=(player.X+(options.dense?300:0))*cam.scaleV;')
src=src.replace('for each(var draw:String in ["full","fill","fill","full"])','for each(var draw:String in ["full","half","edge","edge","half","full"])')
src=src.replace('frames:300','frames:180')
src=src.replace('fill.setEnabled(w,mode=="fill");drawing=mode;', 'fill.update(w,mode);drawing=mode;')
src=src.replace('age=0;previousAt=0;rows=[];phase=20;', 'fill.restore();age=0;previousAt=0;rows=[];phase=20;')
src=src.replace('activity:api.activityStats()', 'activity:api.activityStats(),presenterStart:fill.stats(),combatStart:encounter?encounter.snapshot():null')
src=src.replace('drawPolicy();\n                    var px:', 'drawPolicy();\n                    if(encounter)encounter.sample();\n                    var px:')
src=src.replace('if(mode=="fill")assertThat("fill-active-"+index,mark.fill.active && mark.fill.groups>0 && mark.fill.errors==0,mark.fill);', 'if(mode!="full")assertThat("candidate-active-"+index,mark.fill.hidden && mark.fill.overlayVisible,mark.fill);\n                        mark.combatEnd=encounter?encounter.snapshot():null;')
start=src.index('        private static function pixelCheck():void {')
end=src.index('        private static function finish(',start)
src=src[:start]+'''        private static function savePNG(name:String,data:BitmapData):void {
            var file:FileStream=new FileStream();file.open(File.applicationStorageDirectory.resolvePath(name+".png"),FileMode.WRITE);
            file.writeBytes(data.encode(data.rect,new PNGEncoderOptions()));file.close();
        }
        private static function pixelCheck():void {
            report.qualityCapability=[];var original:String=main.stage.quality;
            try {
                for each(var quality:String in ["high","medium","low","best","high"]){
                    main.stage.quality=quality;
                    report.qualityCapability.push({requested:quality,readback:main.stage.quality});
                }
            }finally{main.stage.quality=original;}
            report.qualityRestored=main.stage.quality;
            var a:BitmapData=captureWorld();savePNG("native-high",a);report.pixels=[];
            for each(var variant:String in ["half","edge","soft","half-low"]){
                fill.update(w,variant);var b:BitmapData=fill.capturePresented();
                savePNG(variant,b);report.pixels.push({mode:variant,difference:compareImages(a,b),stats:fill.stats()});b.dispose();
                fill.restore();b=captureWorld();var diff:Object=compareImages(a,b);b.dispose();
                assertThat("native-restored-"+variant,diff.changed==0 && w.visual.visible,diff);
            }
            a.dispose();fill.clear();
        }
''' +src[end:]
(here/'ContinuousSceneMotionMod.as').write_text(src,'utf-8')
(here/'tests').mkdir(exist_ok=True)
for name in ['SceneEncounter.as','SceneCombatRoute.as']:
    shutil.copy2(root/'mods/ContinuousScene/src/tests'/name,here/'tests'/name)
work=(base/'work.py').read_text('utf-8')
work=work.replace("for p in HERE.iterdir() if p.suffix", "for p in HERE.rglob('*') if p.suffix")
work=work.replace("'nativePresentation':args.native_presentation}","'nativePresentation':args.native_presentation,'dense':args.dense}")
work=work.replace("p.add_argument('--small',action='store_true');", "p.add_argument('--small',action='store_true');p.add_argument('--dense',action='store_true');")
work=work.replace('object viewport optimization','quality and dense enemy evaluation')
(here/'work.py').write_text(work,'utf-8')
print('Prepared v21; no formal files changed')
