"""Keep the controlled target fixed and create native shooters after terrain warmup.

The prior setup allowed minutes of combat before sampling. Fixed only applies to
the private player; enemy simulation, damage callbacks and bullets remain native.
"""
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
for old,new,version in [
    ('combat-cost-visible-v27-20261101','combat-cost-target-v29-20261101','combat-cost-target-29'),
    ('camera-temporal-present-v28-20261101','camera-temporal-target-v30-20261101','camera-temporal-target-30'),
]:
    source=BASE/old;target=BASE/new;target.mkdir()
    for name in ['work.py','ScreenPresenter.as','FrameCostProbe.as']:
        if (source/name).exists():shutil.copy2(source/name,target/name)
    shutil.copytree(source/'tests',target/'tests')
    code=(source/'ContinuousSceneMotionMod.as').read_text('utf-8')
    def replace(a,b):
        global code
        assert code.count(a)==1,a
        code=code.replace(a,b)
    replace('version:"'+('combat-cost-visible-27' if 'v29' in new else 'camera-temporal-present-28')+'"','version:"'+version+'"')
    replace('player.knocked=0;', '''player.knocked=0;
            report.fixtureFixedTarget={original:player.fixed,controlled:true,purpose:"Stationary damageable diagnostic target; player physics excluded, not native movement acceptance"};
            player.fixed=true;''')
    replace('if(options.dense){encounter=new SceneEncounter(w);report.encounter=encounter.prepare(placement.x,placement.y,true,false,true,placement);assertThat("six-enemy-fixture",report.encounter.units.length==6,report.encounter);}','// Native shooters are created only after the surrounding terrain is warm.')
    replace('if(phase==20)target(route,age);','if(phase==20)target(route,age);\n                if(phase==30)target("static",0);')
    replace('w.gg.invulner=!options.dense;', 'w.gg.invulner=!options.dense || encounter==null;')
    replace('private static function makeSchedule():void {', '''private static function makeSchedule():void {
            if(options.dense && encounter==null){
                var placement:Object=report.placement;
                encounter=new SceneEncounter(w);report.encounter=encounter.prepare(placement.x,placement.y,true,false,true,placement);
                assertThat("six-enemy-fixture",report.encounter.units.length==6,report.encounter);
                phase=30;age=0;return;
            }''')
    replace('else if(phase==10) {','else if(phase==30){if(++age>=45)makeSchedule();}\n                else if(phase==10) {')
    replace('report.elapsedMs=getTimer()-started;', 'report.elapsedMs=getTimer()-started;report.fixtureActualEnd=player?{fixed:player.fixed,knocked:player.knocked,x:player.X,y:player.Y}:null;')
    if 'v30' in new:
        replace('schedule.push({fps:120,axis:axis,mode:draw,frames:180});','schedule.push({fps:120,axis:axis,mode:draw,frames:90});')
    (target/'ContinuousSceneMotionMod.as').write_text(code,'utf-8')
    print(target)
