"""Hold only the private player's knockback coefficient at zero for attribution.

Native damage, enemy logic, weapons, bullets, and rendering continue. This is
explicitly a controlled diagnostic, not native combat performance acceptance.
"""
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
source = BASE / 'combat-cost-v26-20261101'
target = BASE / 'combat-cost-visible-v27-20261101'
target.mkdir()
for name in ['work.py', 'ScreenPresenter.as', 'FrameCostProbe.as']:
    shutil.copy2(source / name, target / name)
shutil.copytree(source / 'tests', target / 'tests')
code = (source / 'ContinuousSceneMotionMod.as').read_text('utf-8')
def replace(old, new):
    global code
    assert code.count(old) == 1, old
    code = code.replace(old, new)
replace('version:"combat-cost-26"', 'version:"combat-cost-visible-27"')
replace('report.placement=placement;', '''report.placement=placement;
            report.fixtureKnockback={original:player.knocked,controlled:0,purpose:"Keep the private target on the selected floor; not native gameplay acceptance"};
            player.knocked=0;''')
replace('getTimer()-now,System.totalMemory]);', 'getTimer()-now,System.totalMemory,encounter?encounter.currentVisible:0]);')
replace('mark.actualFrameRate=main.stage.frameRate;', '''var onscreen:Boolean=true,multiple:int=0;
                        for each(var rr:Array in rows){
                            if(rr[11]<0 || rr[11]>=main.stage.stageWidth || rr[12]<0 || rr[12]>=main.stage.stageHeight)onscreen=false;
                            if(rr[15]>=3)++multiple;
                        }
                        mark.visibleQualification={playerOnscreen:onscreen,atLeastThreeEnemyFrames:multiple,frames:rows.length};
                        assertThat("on-screen-combat-"+index,onscreen && multiple>=rows.length*.9,mark.visibleQualification);
                        mark.actualFrameRate=main.stage.frameRate;''')
replace('"probePostMs","memoryBytes"];', '"probePostMs","memoryBytes","onScreenEnemies"];')
(target / 'ContinuousSceneMotionMod.as').write_text(code, 'utf-8')
actor = target / 'tests/SceneEncounter.as'
code = actor.read_text('utf-8')
replace('public var targetFrames:int=0,shots:int=0,movingFrames:int=0,actualShotFrames:int=0;', 'public var targetFrames:int=0,shots:int=0,movingFrames:int=0,actualShotFrames:int=0,currentVisible:int=0;')
replace('public function sample():void {', 'public function sample():void {\n            currentVisible=0;')
replace('if(u.sost!=1)continue;\n                if(u.celUnit===w.gg)', '''if(u.sost!=1)continue;
                var sx:Number=u.X*w.visual.scaleX+w.visual.x,sy:Number=(u.Y-u.scY/2)*w.visual.scaleY+w.visual.y;
                if(sx>=0 && sx<w.main.stage.stageWidth && sy>=0 && sy<w.main.stage.stageHeight && u.vis && u.vis.visible && u.vis.parent)++currentVisible;
                if(u.celUnit===w.gg)''')
actor.write_text(code, 'utf-8')
print(target)
