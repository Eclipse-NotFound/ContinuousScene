from pathlib import Path
import importlib.util
import hashlib
import shutil

HERE=Path(__file__).resolve().parent
VERSION='camera-atlas-merged-combat-1'
CHANGED=['ContinuousSceneMotionProbe.as','SceneRasterPresentation.as','tests/SceneCombatAtlasPixels.as']
CANDIDATE=HERE.parent/'camera-atlas-pool-merged-20261026'
PRESENTER_SOURCE=HERE.parent/'camera-atlas-paged-combat-20261025/SceneRasterPresentation.as'
PRESENTER_SHA='AD472C796A8006227C5523E51C5803511C2F3904AE0E970D08136BB37C02AD48'
CANDIDATE_SHA='BC0BCA76989B2C2A323D723BD4240F79A1EA48B5F69316A00F9F5D75C1B91E63'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
pool=load('merged_combat_pool_patch',HERE.parent/'camera-atlas-pool-20261026/probe_patch.py')
candidate=load('merged_combat_candidate_patch',CANDIDATE/'probe_patch.py')

def transform_main(source):
    value=pool.transform_main(source)
    assert value.count('camera-atlas-pool-combat-1')==2
    value=value.replace('camera-atlas-pool-combat-1',VERSION)
    before='    import tests.SceneAtlasChecks;'
    assert value.count(before)==1
    value=value.replace(before,before+'\n    import tests.SceneCombatAtlasPixels;',1)
    before='            closeProbeTiming(true);\n            if(cfg.drawControl=="atlas") {'
    after='            closeProbeTiming(true);\n            if(error==null && cfg.drawControl=="atlas" && report.samples.length==4) {\n                report.combatAtlasPixels=SceneCombatAtlasPixels.run(w,rasterPresentation);\n                check("combat-terminal-atlas-pixels",report.combatAtlasPixels.passed,report.combatAtlasPixels);\n            }\n            if(cfg.drawControl=="atlas") {'
    assert value.count(before)==1;value=value.replace(before,after,1)
    return value

def transform_presenter(source):
    value=pool.transform_presenter(source);baseline=value
    for before,after in candidate.PRESENTER_EDITS:
        assert value.count(before)==1,(before,value.count(before))
        value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(candidate.PRESENTER_EDITS):reverse=reverse.replace(after,before,1)
    assert reverse==baseline
    assert hashlib.sha256(value.encode('utf-8')).hexdigest().upper()==CANDIDATE_SHA
    return value

def prepare(source:Path,destination:Path):
    assert not destination.exists() and not (source/CHANGED[2]).exists()
    assert hashlib.sha256((source/CHANGED[1]).read_bytes()).hexdigest().upper()==PRESENTER_SHA
    shutil.copytree(source,destination)
    (destination/CHANGED[0]).write_text(transform_main((source/CHANGED[0]).read_text('utf-8-sig')),'utf-8',newline='\n')
    presenter=transform_presenter((source/CHANGED[1]).read_text('utf-8-sig'))
    assert presenter==(HERE/CHANGED[1]).read_text('utf-8-sig')
    (destination/CHANGED[1]).write_text(presenter,'utf-8',newline='\n')
    shutil.copy2(HERE/CHANGED[2],destination/CHANGED[2])
