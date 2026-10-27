from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-room-axis-baseline-v2-20261027'
VERSION='camera-active-quiet-axis-1'
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
QUIET='''        private function stripHostiles():void {
            var removed:Array=[],objects:int=0,seen:int=0;
            for each(var unit:* in location.units.concat()) {
                if(!unit || unit===player || unit.player || unit.npc || unit.fraction<=0 || unit.fraction>=100 || unit.fraction==player.fraction)continue;
                var detail:Object={className:getQualifiedClassName(unit),x:unit.X,y:unit.Y,fraction:unit.fraction,wasInChain:Boolean(unit.in_chain)};
                unit.disabled=true;unit.remVisual();location.remObj(unit);
                var index:int=location.units.indexOf(unit);require(index>=0,"Quiet actor array changed during removal");location.units.splice(index,1);
                require(!unit.vis || unit.vis.stage==null,"Removed actor visual remains on Stage");
                if("hpbar" in unit && unit.hpbar)require(unit.hpbar.stage==null,"Removed actor HP bar remains on Stage");
                removed.push(detail);
            }
            var Bullet:Class=getDefinitionByName("fe.weapon.Bullet") as Class,obj:*=location.firstObj;
            while(obj!=null) {
                require(++seen<50000,"Object chain cycle during quiet fixture setup");
                var next:*=obj.nobj;
                if(obj is Bullet) {obj.off=true;obj.remVisual();location.remObj(obj);++objects;}
                obj=next;
            }
            world.ctr.clearAll();
            report.quietFixture={removedHostiles:removed,removedProjectiles:objects,terminalPopulationChange:true,
                nativeSimulationPaused:false,hostileChecks:0,remainingUnits:location.units.length,
                limitation:"Private diagnostic population only; no death/loot callbacks and no actor restoration. Camera is scripted, not a player jump."};
            report.simulationTicks=0;
        }
        private function quietGuard():void {
            var hostile:int=0;
            for each(var unit:* in location.units)if(unit && unit!==player && !unit.player && !unit.npc && unit.fraction>0 && unit.fraction<100 && unit.fraction!=player.fraction && unit.sost==1)++hostile;
            ++report.quietFixture.hostileChecks;
            require(hostile==0,"Hostile actor entered quiet camera fixture");
            require(world.onPause===false && world.allStat==1 && world.t_exit==0,"Quiet simulation stopped");
            require(isFinite(player.X+player.Y+player.dx+player.dy+player.hp) && player.hp>0,"Quiet player became invalid");
            require(world.gg===player && world.loc===location,"Quiet identities changed");
        }
'''
def helper_source():
    s=(BASE/'tests/SceneCameraRasterTrial.as').read_text('utf-8-sig').replace('camera-room-axis-baseline-2',VERSION)
    s=one(s,'    import flash.utils.getQualifiedClassName;', '    import flash.utils.getDefinitionByName;\n    import flash.utils.getQualifiedClassName;')
    s=one(s,'/** Terminal, paused-world attribution. Not a combat or gameplay acceptance test. */', '/** Live simulation, no hostile actors, native scripted camera; not jump/combat acceptance. */')
    start=s.index('                limits:[');end=s.index('};\n            world=w;',start)
    s=s[:start]+'''                limits:["Native simulation remains active; hostile actors and existing projectiles are removed only in this private fixture.",
                    "120fps diagnostic; native simulation and Flash callbacks continue, not ordinary gameplay FPS.",
                    "The same native camera script replays horizontal/vertical/combined paths in each map mode.",
                    "No player teleport during measurement; this is not a natural jump test.",
                    "Camera/cache restoration is checked; deliberately removed fixture enemies are not restored.",
                    "All intervals and observer work retained; no new rendering optimization applied."]'''+s[end:]
    s=one(s,'                require(saved.worldVisible===true,"World must start visible");\n                stage.nativeWindow.visible=true;',
        '                require(saved.worldVisible===true,"World must start visible");\n                require(stage.nativeWindow.visible,"Show private window before native game initialization");\n                for(var menuIndex:int=0;menuIndex<world.main.numChildren;++menuIndex)require(getQualifiedClassName(world.main.getChildAt(menuIndex))!="visMainMenu","Native menu remains attached");')
    s=one(s,'                w.onPause=true;\n                require(w.onPause===true && w.gg===player && w.loc===location,"Pause was not applied");',
        '                require(w.onPause===false && w.gg===player && w.loc===location,"Native simulation must remain active");\n                stripHostiles();')
    s=one(s,'                require(w===world,"World argument replaced");guard();', '                require(w===world,"World argument replaced");guard();++report.simulationTicks;')
    s=one(s,'                    if(++settle==12) {', '                    ++settle;\n                    if(settle==60) {')
    s=one(s,'                    require(samePlayer(playerState(),saved.gg),"Player simulation changed while paused");',
        '                    require(world.gg===player && isFinite(player.X+player.Y+player.hp),"Player identity changed during live fixture");')
    s=one(s,'            require(world.onPause===true && world.allStat==1 && world.t_exit==0 && stage.frameRate==120,"Pause/runtime state changed");',
        '            require(world.onPause===false && world.allStat==1 && world.t_exit==0 && stage.frameRate==120,"Active runtime state changed");')
    s=one(s,'            require(samePlayer(playerState(),saved.gg),"Player position/velocity/HP changed during paused attribution");','            quietGuard();')
    s=one(s,'        private function playerState():Object',QUIET+'        private function playerState():Object')
    s=one(s,'            cleanup.pendingOwnedBitmaps=owned.length;cleanup.elapsedMs=getTimer()-at;',
        '            cleanup.pendingOwnedBitmaps=owned.length;cleanup.elapsedMs=getTimer()-at;cleanup.fixturePopulationNotRestored=true;')
    return s
def runner_source():
    s=(HERE.parent/'camera-far-live-detach-20261027/run.py').read_text('utf-8-sig').replace('camera-far-live-detach-1',VERSION)
    s=one(s,'"""Paused moving-camera backdrop/object alpha attribution; diagnostic only."""','"""Matched native camera axes with active quiet simulation; diagnostic only."""')
    a=s.index('def options(name):');b=s.index('\n\ndef metric(',a)
    s=s[:a]+'''def options(name,mode):
    values=reference.options(name)+['--draw-control','tilecrop','--presentation-check']
    for flag,value in [('--benchmark',mode),('--window-width','1296'),('--window-height','759')]:
        i=values.index(flag);values[i+1]=value
    if mode=='normal':
        values=[v for v in values if v!='--expect-no-signs']
        values+=['--native-room-x','2','--native-room-y','4','--native-route-x','480','--native-route-y','119']
    return values
'''+s[b:]
    a=s.index('def summarize(raw):');b=s.index('\n\ndef main():',a)
    s=s[:a]+"summary_module=load('active_quiet_summary',HERE/'summary.py')\nsummarize=summary_module.summarize\n"+s[b:]
    s=one(s,"parser.add_argument('--name',required=True);parser.add_argument('--registry-wait',type=int,default=300)","parser.add_argument('--mode',required=True,choices=['normal','scene']);parser.add_argument('--name',required=True);parser.add_argument('--registry-wait',type=int,default=300)")
    s=one(s,'options=options(args.name),','options=options(args.name,args.mode),')
    s=s.replace('ContinuousScene / far live root detach / 01a13816','ContinuousScene / active quiet camera axes / 01a13816')
    s=s.replace('960 static/moving live-root visibility controls; diagnostic only, no deployment','960 native camera axis intervals, active quiet world; no deployment')
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared active quiet matched camera axes; original paused recipes unchanged')
