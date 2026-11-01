from pathlib import Path
import shutil
here=Path(__file__).resolve().parent
old=here.parent/'camera-native-quality-v23-20261101'
for name in ['ScreenPresenter.as','work.py']:
    shutil.copy2(old/name,here/name)
shutil.copytree(old/'tests',here/'tests',dirs_exist_ok=True)
src=(old/'ContinuousSceneMotionMod.as').read_text('utf-8').replace('camera-native-quality-23','camera-native-combat-24')
src=src.replace('w.gg.invulner=true;', 'w.gg.invulner=!options.dense;')
src=src.replace('["full","medium","low","late","late","low","medium","full"]','["full","medium","low","low","medium","full"]')
src=src.replace('mark.combatEnd=encounter?encounter.snapshot():null;', '''mark.combatEnd=encounter?encounter.snapshot():null;
                        if(encounter)assertThat("native-enemy-fire-"+index,
                            mark.combatEnd.alive==6 && mark.combatEnd.actualShotFrames-mark.combatStart.actualShotFrames>0
                            && mark.combatEnd.targetFrames-mark.combatStart.targetFrames>0,
                            {start:mark.combatStart,end:mark.combatEnd});''')
# Persist complete blocks between sampling windows, not inside an interval.
src=src.replace('if(++index>=schedule.length){finish();return;}enterBlock();', '''if(++index>=schedule.length){finish();return;}
                        var partial:FileStream=new FileStream();partial.open(File.applicationStorageDirectory.resolvePath("partial.json"),FileMode.WRITE);
                        partial.writeUTFBytes(JSON.stringify(report));partial.close();enterBlock();''')
(here/'ContinuousSceneMotionMod.as').write_text(src,'utf-8')
print('Prepared v24 with targetable player and native-shot assertions; no product changes')
