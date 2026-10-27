from pathlib import Path
import ast, importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-visible-room-fog-history-20261027'
SAMPLER=HERE.parent/'scene-compat-20261024/combat-sampler-v3/tests/SceneCombatSampler.as'
VERSION='camera-visible-room-sampling-1'

def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('room_sampling_base',BASE/'prepare.py');one=base.one

def sampler_source():
    s=SAMPLER.read_text('utf-8-sig').replace('SceneCombatSampler','SceneCameraSampler')
    s=s.replace('295','115').replace('299','119')
    s=one(s,'windows.length==4','windows.length==8')
    s=one(s,'current.sampleTimesValid &&',
        'current.timeDiagnostics!=null && current.timeDiagnostics.byType.cpu.bad==0 &&')
    s=one(s,'version:"combat-sampler-3"','version:"room-camera-sampler-1"')
    s=one(s,'"ENTER_FRAME priority max age115 through before MotionProbe.tick age119; 5 main updates; final low-priority tail/EXIT_FRAME/RENDER excluded"',
        '"Before applying camera age115 through next helper entry after age119: five outgoing camera/render intervals, with intervening native updates. Mixed allocation/CPU iterator order is recorded, not used as a CPU clock."')
    return s

def helper_source():
    s=base.helper_source().replace(base.VERSION,VERSION)
    s=one(s,'        private var world:*;',
        '        private var sampler:SceneCameraSampler=new SceneCameraSampler();\n        private var world:*;')
    s=one(s,'            if(closed)return true;\n            try {',
        '            if(closed)return true;\n            if(phase==3)sampler.beforeTick(segment,age);\n            try {')
    s=one(s,'                    if(age==120) {',
        '                    if(age==120) {\n                        row.cpuSampling=sampler.complete(segment);')
    s=one(s,'            var at:int=getTimer();\n            var target:Object=row.moving?',
        '            sampler.head(segment,age,row.mode);\n            var at:int=getTimer();\n            var target:Object=row.moving?')
    s=one(s,'            try {if(presenter!=null)presenter.clear();}',
        '            try {report.cpuSampling=sampler.finish();}catch(se:Error){cleanup.errors.push("sampler: "+se.message);}\n            try {if(presenter!=null)presenter.clear();}')
    s=one(s,'"All intervals and observer work retained; no new rendering optimization applied."',
        '"Each axis window samples five outgoing frames; all intervals and sampler aggregation remain recorded. This is CPU occurrence attribution, not performance acceptance."')
    return s

def runner_source():
    s=base.runner_source().replace(base.VERSION,VERSION).replace('== 86','== 87')
    s=one(s,"    assert r.sha(frozen/'tests/SceneCameraRasterTrial.as') == r.sha(patch.HELPER)",
        "    assert r.sha(frozen/'tests/SceneCameraRasterTrial.as') == r.sha(patch.HELPER)\n    assert r.sha(frozen/'tests/SceneCameraSampler.as') == r.sha(patch.SAMPLER)")
    return s

if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('tests/SceneCameraSampler.as',sampler_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared bounded CPU occurrence sampling in the visible room; no production edits')
