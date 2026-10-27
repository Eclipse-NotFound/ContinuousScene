from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'camera-visible-room-scout-20261027'
VERSION='camera-visible-room-fog-history-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('fog_history_generation_base',BASE/'prepare.py');one=base.one
def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'            report.referenceSite.tileHash=tileHash;', '''            report.referenceSite.tileHash=tileHash;
            report.fogHistory={before:fogState(),resetCells:0,nonzeroBeforeReset:0,terminalOnly:true};
            // Setup-only control: both modes must start exploration at the same
            // verified platform, not inherit different room-entry sight history.
            for(var fx:int=0;fx<location.spaceX;++fx)for(var fy:int=0;fy<location.spaceY;++fy) {
                var fogTile:*=location.space[fx][fy];
                if(fogTile.visi!=0 || fogTile.t_visi!=0)++report.fogHistory.nonzeroBeforeReset;
                fogTile.visi=0;fogTile.t_visi=0;++report.fogHistory.resetCells;
            }
            grafon.setLight();report.fogHistory.afterReset=fogState();''')
    s=one(s,'++report.referenceSite.spawnCalls;', '++report.referenceSite.spawnCalls;location.isRelight=true;')
    s=one(s,'                result.visibleCoverage=coverage(a);', '                result.fog=fogState();result.visibleCoverage=coverage(a);')
    s=one(s,'                        report.stabilizationFrames=settle;report.timingStart=snapshot();',
      '                        report.fogTimingStart=fogState();report.stabilizationFrames=settle;report.timingStart=snapshot();')
    s=one(s,'                            report.complete=true;report.passed=true;clear(w);',
      '                            report.fogTimingEnd=fogState();report.complete=true;report.passed=true;clear(w);')
    extra=(HERE/'fog-state.as.inc').read_text('utf-8-sig')
    s=one(s,'        private function selectReferenceSite():void {',extra+'\n        private function selectReferenceSite():void {')
    return s
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared identical initial sight history control; normal simulation remains active')
