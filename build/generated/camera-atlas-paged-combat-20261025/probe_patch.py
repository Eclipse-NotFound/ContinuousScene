"""B7ED 85-source fixture: old telemetry + tested paging + six native SMG10s."""
from pathlib import Path
import hashlib
import importlib.util
import shutil

VERSION = 'camera-atlas-paged-smg10-combat-1'
FIXTURE_VERSION = 'dense-sprint-smg10-1'
HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'camera-atlas-motion-combat-20261025'
CHANGED = ['ContinuousSceneMotionProbe.as', 'SceneRasterPresentation.as', 'tests/SceneEncounter.as']
OLD_PATCH_SHA = '27EBF3820AA75C8CC6ACD60C25F9EB2EEE9D6B1BB08A0F3E42B31650324CD3E6'
OLD_TRANSFORM_SHA = 'ABCA304942738E54DEB303F27EAB932FAAF824DADFC3695917B31D56B1F86BF5'
PAGED_TRANSFORM_SHA = '76AD29F53659810CBCCACB1EFEE047CF43750E3348F521D36986D5D56394D53D'
PAGED_RAW_SHA = 'AD472C796A8006227C5523E51C5803511C2F3904AE0E970D08136BB37C02AD48'
ENCOUNTER_RAW_SHA = '448A2BD8C710132B9EBF3FC7D9C2EB18B35B9118EA669948231617E0914707AA'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


assert sha(OLD / 'probe_patch.py') == OLD_PATCH_SHA
assert sha(OLD / 'presentation_transform.py') == OLD_TRANSFORM_SHA
assert sha(HERE / 'presentation_transform.py') == PAGED_TRANSFORM_SHA
assert sha(HERE / 'SceneRasterPresentation.as') == PAGED_RAW_SHA
old = load('paged_combat_original_telemetry', OLD / 'probe_patch.py')
variant = load('paged_combat_tested_presentation', HERE / 'presentation_transform.py')

MAIN_EDITS = (
    ('version:"dense-sprint-2",actors:6,enemyWeapon:"lmg"',
     'version:"dense-sprint-smg10-1",actors:6,enemyWeapon:"smg10"'),
    ('worldX:[],worldY:[],worldScaleX:[],worldScaleY:[],quakeX:[],quakeY:[],copies:[],rebuilds:[],',
     'worldX:[],worldY:[],worldScaleX:[],worldScaleY:[],quakeX:[],quakeY:[],copies:[],rebuilds:[],\n'
     '                states:[],matrixA:[],matrixB:[],matrixC:[],matrixD:[],matrixTX:[],matrixTY:[],\n'
     '                worldOnStage:[],satsActive:[],satsVisible:[],chunkSide:[],'),
    ('                            atlasPriorEnabled=altered;atlasPriorPresented=rasterPresentation.presented;',
     '                            var atlasMatrix:*=w.visual.transform.concatenatedMatrix;\n'
     '                            row.atlasMotion.states.push(rasterPresentation.snapshot());\n'
     '                            row.atlasMotion.matrixA.push(atlasMatrix.a);row.atlasMotion.matrixB.push(atlasMatrix.b);\n'
     '                            row.atlasMotion.matrixC.push(atlasMatrix.c);row.atlasMotion.matrixD.push(atlasMatrix.d);\n'
     '                            row.atlasMotion.matrixTX.push(atlasMatrix.tx);row.atlasMotion.matrixTY.push(atlasMatrix.ty);\n'
     '                            row.atlasMotion.worldOnStage.push(w.visual.stage!=null);\n'
     '                            row.atlasMotion.satsActive.push(Boolean(w.sats.active));\n'
     '                            row.atlasMotion.satsVisible.push(Boolean(w.grafon.visSats.visible));\n'
     '                            row.atlasMotion.chunkSide.push(w.grafon.sceneChunkSide);\n'
     '                            atlasPriorEnabled=altered;atlasPriorPresented=rasterPresentation.presented;'),
    ('Actual fractional translation and native shake are retained. RGB2/alpha0 compatibility is not established by this timing run.',
     'Native movement and shake remain unchanged. The tested paged helper falls back on unsupported geometry; this combat timing does not establish visual acceptance.'),
)
ENCOUNTER_EDITS = (
    ('new Raider("1",4,null,{weap:"lmg",tr:1})', 'new Raider("1",4,null,{weap:"smg10",tr:1})'),
    ('if(!u.currentWeapon || u.currentWeapon.tip<3 || !/Unit(Raider|Merc|Ranger|Slaver|Zebra|Encl)$/.test(kind))continue;',
     'if(!u.currentWeapon || (u.currentWeapon.tip<3 && !(fixed && u.currentWeapon.id=="smg10")) || !/Unit(Raider|Merc|Ranger|Slaver|Zebra|Encl)$/.test(kind))continue;'),
    ('weapon:gun?{id:gun.id,hold:gun.hold,holder:gun.holder,attack:gun.t_attack,reload:gun.t_reload,hp:gun.hp,jammed:gun.jammed}:null});',
     'weapon:gun?{id:gun.id,hold:gun.hold,holder:gun.holder,attack:gun.t_attack,reload:gun.t_reload,hp:gun.hp,jammed:gun.jammed}:null,\n'
     '                    weaponStats:gun?{id:gun.id,tip:gun.tip,rapid:gun.rapid,knock:gun.otbros,knockMult:gun.otbrosMult,\n'
     '                        ammoKnock:gun.ammoOtbros,holder:gun.holder,reloadTicks:gun.reload,speed:gun.speed,damage:gun.damage}:null});'),
)


def replace_checked(source, edits):
    result = source
    for before, after in edits:
        assert result.count(before) == 1, before
        result = result.replace(before, after, 1)
    restored = result
    for before, after in reversed(edits):
        assert restored.count(after) == 1, after
        restored = restored.replace(after, before, 1)
    assert restored == source
    return result


def transform(source):
    original = old.transform(source)
    assert original.count('atlas-motion-combat-1') == 2
    changed = replace_checked(original, MAIN_EDITS)
    return changed.replace('atlas-motion-combat-1', VERSION)


def encounter_transform(source):
    return replace_checked(source, ENCOUNTER_EDITS)


def prepare(source, destination):
    assert not destination.exists()
    assert len(list(source.rglob('*.as'))) + len(list(source.rglob('*.as.inc'))) == 85
    assert sha(source / CHANGED[0]) == old.MAIN_RAW_SHA256
    assert sha(source / CHANGED[2]) == ENCOUNTER_RAW_SHA
    assert sha(HERE / CHANGED[1]) == PAGED_RAW_SHA
    assert (HERE / CHANGED[1]).read_text('utf-8-sig') == variant.transform((source / CHANGED[1]).read_text('utf-8-sig'))
    shutil.copytree(source, destination)
    (destination / CHANGED[0]).write_text(transform((source / CHANGED[0]).read_text('utf-8-sig')), 'utf-8')
    shutil.copy2(HERE / CHANGED[1], destination / CHANGED[1])
    (destination / CHANGED[2]).write_text(encounter_transform((source / CHANGED[2]).read_text('utf-8-sig')), 'utf-8')
