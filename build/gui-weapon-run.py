"""Registered, diagnostic-only GUI.setWeapon attribution on exact BEFC lineage.

Four 300-frame segments use the real-fire 200 px native platform fixture.
Both sides must fire in every segment; every 30-frame boundary retains six
armed living enemies. Natural enemy reload gaps remain visible in evidence.
Unreviewed host/audit/XML pins fail before compilation or launch. No deployment.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import shutil
import statistics
import subprocess
import sys

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B/'generated/gui-weapon-profile-20261022'
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FORMAL_CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
# Pinned after the actual 170-instruction projection, class/asset retention,
# qualified timer binding and final exported binary audit passed.
HOST = '156681B01C0367366CB83C91F1CF71AE2B5975C5E4A252CA44E4C33DCFC58A5A'
HOST_XML = 'F64CF46B16F6AC52CF2117CDE1FBDF4FF3801ECA75D758A7C16DE64BDFFD5D76'
AUDIT = 'F826C05991CDE2A5A770C8C0EA9AE72CFEC9B9AFA5B196410204AEDE102049F5'
TARGET = 'fe.inter.GUI::0:1:setWeapon'
GROUPS = ('weaponHtml', 'textWidth', 'ammoText', 'holder')
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
PROBE_PATH = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('gui_weapon_runner_helpers', B/'enemy-release.py')
m = r.motion


def source_hashes():
    src = B.parent/'src'
    return {p.relative_to(src).as_posix(): r.sha(p) for p in sorted(src.rglob('*.as'))}


def runner_inputs():
    paths = (Path(__file__), B/'enemy-release.py', B/'enemy-speed.py', B/'motion-test.py',
             B/'profile-vision.py', r.ROOT/'mods/ModLoader/tools/test_registry.py',
             r.ROOT/'mods/ModLoader/tools/air_test_process.py')
    return {str(p): r.sha(p) for p in paths}


def compiler_inputs():
    tools = r.enemy.TOOLS
    paths = (r.enemy.JAVA, tools/'flexsdk/lib/mxmlc.jar',
             tools/'airsdk/frameworks/libs/air/airglobal.swc')
    return {str(p): r.sha(p) for p in paths}


def audited_host():
    """Never treat a newly generated audit as its own approval."""
    for name, digest in (('HOST', HOST), ('HOST_XML', HOST_XML), ('AUDIT', AUDIT)):
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789ABCDEF' for c in digest):
            raise RuntimeError('Reviewed GUI.setWeapon '+name+' pin is absent; no compiler or AIR launch allowed')
    build = r.read(OUT/'build.json')
    audit = r.read(OUT/'semantic-audit.json')
    assert build['version'] == 'gui-weapon-profile-1' and build['target'] == TARGET
    assert build['diagnosticOnly'] and not build['performanceEligible'] and not build['deployed']
    assert build['base'] == FORMAL_HOST and build['groups'] == list(GROUPS)
    assert r.sha(OUT/'pfe.swf') == build['candidate'] == audit['candidateSHA256'] == HOST
    assert r.sha(OUT/'pfe.xml') == build['candidateXML'] == audit['candidateXMLSHA256'] == HOST_XML
    assert r.sha(OUT/'semantic-audit.json') == build['audit'] == AUDIT
    assert audit['passed'] and audit['diagnosticOnly'] and not audit['performanceEligible']
    assert audit['auditTarget'] == TARGET and audit['actualChangedBodies'] == [TARGET]
    assert audit['baseSHA256'] == FORMAL_HOST
    assert audit['preservedOriginalLayout'] is True and audit['constructorsPreserved'] is True
    assert audit['nonABCSWFEnvelopePreserved'] and audit['originalConstantPoolPreserved']
    assert not audit['addedFields'] and not audit['addedMethods']
    assert audit['unchangedMethodBodies'] == 5770 and audit['unchangedClassLayouts'] == 1016
    assert audit['timerBinding']['callCount'] == build['timerCalls'] == 18
    assert audit['timerBinding']['allCallsDirectQualified']
    assert audit['wrapperSHA256'] == r.sha(B/'gui-weapon-profile-audit.py')
    assert all(r.sha(Path(path)) == digest for path, digest in build['sourceInputs'].items())
    return build


def compile_probe(lease):
    """Compile only the diagnostic probe, into its own output directory."""
    assert not m.air_pids(), 'Other AIR present; untouched'
    memory = m.memory_status()
    assert memory['availableCommit'] >= 1024 * 1024**2, ('Insufficient commit', memory)
    assert memory['availablePhysical'] >= 1.5 * 1024**3, ('Insufficient physical memory', memory)
    output = OUT/'ContinuousSceneProbe.swf'
    config = output.with_suffix('.xml')
    src, tools = B.parent/'src', r.enemy.TOOLS
    config.write_text(f'''<flex-config><target-player>32.0</target-player><compiler>
<external-library-path><path-element>{tools}/airsdk/frameworks/libs/air/airglobal.swc</path-element></external-library-path>
<source-path><path-element>{src}</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>
</compiler></flex-config>''', 'utf-8')
    command = [str(r.enemy.JAVA), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar',
        str(tools/'flexsdk/lib/mxmlc.jar'), '+flexlib=' + str(tools/'flexsdk/frameworks'),
        '-load-config=' + str(config), '-swf-version=32', '-static-link-runtime-shared-libraries=true',
        '-output=' + str(output), str(src/'ContinuousSceneProbeDoc.as')]
    process = None
    lease.before_launch('GUI.setWeapon isolated probe compiler')
    try:
        process = subprocess.Popen(command)
        lease.child(process.pid)
        code = process.wait()
        if code:
            raise subprocess.CalledProcessError(code, command)
    finally:
        if process is not None:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
            lease.child_stopped()
    return dict(command=command, configSHA256=r.sha(config))


def check_stats(stats, player_shots):
    assert stats['version'] == 'gui-weapon-profile-1'
    assert stats['diagnosticOnly'] is True and stats['performanceEligible'] is False
    # GUI.setWeapon can be called more than once in one game frame. Measure
    # calls, do not impose a fabricated one-call-per-frame cadence.
    keys = ('calls', 'totalMs', 'totalMaxMs') + tuple(g + suffix for g in GROUPS for suffix in ('Ms', 'Calls', 'MaxMs'))
    for key in keys:
        value = stats[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert math.isfinite(value) and value >= 0 and value == int(value), (key, value)
    assert stats['calls'] >= player_shots > 0
    assert stats['holderCalls'] == stats['calls']
    assert 0 <= stats['totalMaxMs'] <= stats['totalMs']
    for key in GROUPS:
        assert 0 < stats[key+'Calls'] <= stats['calls'], (key, stats[key+'Calls'])
        assert stats[key+'MaxMs'] <= stats[key+'Ms']
    assert sum(stats[key+'Ms'] for key in GROUPS) <= stats['totalMs']


def six_armed(encounter):
    assert encounter['alive'] == 6 and encounter['armed'] == 6
    actors = encounter['actors']
    assert len(actors) == 6
    assert all(a['hp'] > 0 and a['weapon'] and a['weapon']['hp'] > 0 for a in actors)


def summarize(result, name, build):
    assert result['driver']['stableMotion']
    assert result['driver']['perFrameMethod'] == 'Unit.setPos (position/bounds/target only)'
    assert result['playerFire']['enabled'] and result['playerFire']['shotFrames'] > 0
    route = result['combatRoute']
    assert route['path'] == route['evidence']['playerPath'] == 200
    assert route['evidence']['version'] == 'existing-flat-combat-route-1' and route['evidence']['selected']
    assert route['checkedNativeSightLines'] == 30 and len(route['enemies']) == 6
    assert result['path']['speed'] == 4 and result['path']['endX'] - result['path']['startX'] == 200
    warmup = result['playerFireWarmup']
    assert warmup['frames'] >= 100 and warmup['quietWarmFrames'] >= 100 and warmup['shotFrames'] >= 5
    assert warmup['encounter']['actualShotFrames'] > 0
    six_armed(warmup['encounter'])
    assert len(result['samples']) == 4
    summary = dict(name=name, diagnosticOnly=True, performanceEligible=False, deployed=False,
        checks=len(result['assertions']), driver=result['driver'], combatRoute=route,
        playerFireWarmup=warmup, hostSHA256=HOST, limitations=build['limitations'], samples=[])
    for row_index, row in enumerate(result['samples']):
        assert len(row['frames']) == 300 and row['empty'] == 0 and row['misses'] == 0
        assert len(row['nativeBand']) == len(row['warm']) == 300
        # The first script interval starts before its recorder is attached.
        assert len(row['totalScript']) in ((299, 300) if row_index == 0 else (300,))
        assert row['enemyShotFrames'] > 0 and row['playerShotFrames'] > 0
        stats = row['guiWeaponProfile']
        check_stats(stats, row['playerShotFrames'])
        six_armed(row['encounter'])
        assert len(row['combatWindows']) == 20
        windows = []
        for wi in range(10):
            pair = sorted((x for x in row['combatWindows'] if x['frame']//30 == wi), key=lambda x:x['frame'])
            assert len(pair) == 2 and [x['frame'] for x in pair] == [wi*30, wi*30+29]
            for sample in pair:
                six_armed(sample['encounter'])
            player = pair[1]['playerShots'] - pair[0]['playerShots']
            enemy = pair[1]['encounter']['actualShotFrames'] - pair[0]['encounter']['actualShotFrames']
            assert player > 0 and enemy >= 0
            windows.append(dict(window=wi, playerShots=player, enemyShots=enemy, population=pair))
        summary['samples'].append(dict(name=row['name'], frames=300, profile=stats,
            perFrame={key:stats[key+'Ms']/300 for key in GROUPS}, totalMsPerFrame=stats['totalMs']/300,
            callsPerFrame=stats['calls']/300, totalMsPerCall=stats['totalMs']/stats['calls'],
            nativeBand=statistics.mean(row['nativeBand']), script=statistics.mean(row['totalScript']),
            scriptSamples=len(row['totalScript']),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            warmed=sum(row['warm']), quietEnemyWindows=sum(w['enemyShots'] == 0 for w in windows), combatWindows=windows))
    return summary


def main():
    if not __debug__:
        raise RuntimeError('This diagnostic runner requires Python assertions; do not use -O')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--compile-probe', action='store_true')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name), 'Evidence name'
    assert not (r.E/args.name).exists(), 'Use a fresh evidence name'
    audited_host()  # Fail closed before occupying the registry or compiling.
    with m.Registration(owner='ContinuousScene / GUI weapon diagnosis / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=r.E/args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline = r.baseline()
        assert baseline['pfe.swf'] == FORMAL_HOST and baseline[CS_PATH] == FORMAL_CS
        build = audited_host()
        sources, scripts, compiler = source_hashes(), runner_inputs(), compiler_inputs()
        if args.compile_probe:
            compilation = compile_probe(lease)
            assert sources == source_hashes() and scripts == runner_inputs(), 'Probe inputs changed during compile'
            assert compiler == compiler_inputs() and build == audited_host(), 'Compiler or audited host changed'
            r.save(OUT/'probe-build.json', dict(sourceSHA256=sources, runnerInputs=scripts,
                compilerInputs=compiler, compilation=compilation,
                probeSHA256=r.sha(OUT/'ContinuousSceneProbe.swf'), hostSHA256=HOST,
                diagnosticOnly=True, performanceEligible=False))
        probe = r.read(OUT/'probe-build.json')
        assert probe['sourceSHA256'] == sources and probe['runnerInputs'] == scripts
        assert probe['compilerInputs'] == compiler
        assert probe['compilation']['configSHA256'] == r.sha(OUT/'ContinuousSceneProbe.xml')
        assert probe['probeSHA256'] == r.sha(OUT/'ContinuousSceneProbe.swf') and probe['hostSHA256'] == HOST
        assert probe['diagnosticOnly'] and not probe['performanceEligible']
        assert r.baseline() == baseline, 'Production drift before preparation'
        m.prepare()
        shutil.copy2(OUT/'pfe.swf', m.RUNTIME/'pfe.swf')
        shutil.copy2(OUT/'ContinuousSceneProbe.swf', m.RUNTIME/PROBE_PATH)
        assert r.sha(m.RUNTIME/'pfe.swf') == HOST
        assert r.sha(m.RUNTIME/PROBE_PATH) == probe['probeSHA256']
        assert r.sha(m.RUNTIME/CS_PATH) == FORMAL_CS, 'An activity/other CS candidate must not be used'
        assert sources == source_hashes() and scripts == runner_inputs(), 'Probe inputs changed before launch'
        assert compiler == compiler_inputs() and build == audited_host(), 'Frozen artifacts changed before launch'
        assert r.baseline() == baseline, 'Production drift before launch'
        options = ['--name', args.name, '--high-qos', '--land', 'random_mane', '--encounter', '--fixed-enemies',
            '--benchmark', 'scene', '--speed', '4', '--short', '--gui-weapon-profile',
            '--window-width', '2048', '--window-height', '1123', '--no-lighting', '--no-wall',
            '--expect-no-signs', '--stable-motion', '--player-fire', '--combat-route', '--combat-route-length', '200']
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert r.baseline() == baseline, 'Production drift'
        assert sources == source_hashes() and scripts == runner_inputs(), 'Probe source/helper changed during run'
        assert compiler == compiler_inputs() and build == audited_host(), 'Frozen artifacts changed during run'
        assert r.sha(OUT/'ContinuousSceneProbe.swf') == probe['probeSHA256']
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[path] == (HOST if path == 'pfe.swf' else digest), path
        assert inputs[PROBE_PATH] == probe['probeSHA256'] and inputs[CS_PATH] == FORMAL_CS
        policy = r.read(r.E/args.name/'process-policy.json')
        assert policy['performanceEligible'] is False and 'GUI.setWeapon' in policy['diagnosticOnly']
        r.save(r.E/args.name/'probe-build.json', probe)
        r.save(r.E/args.name/'runner-inputs.json', dict(options=options, baseline=baseline,
            hostBuild=build, runnerInputs=scripts, compilerInputs=compiler))
        summary = summarize(result, args.name, build)
        r.save(OUT/(args.name+'-summary.json'), summary)
        r.save(r.E/args.name/'gui-weapon-profile-summary.json', summary)
        print(json.dumps(dict(name=args.name, diagnosticOnly=True, performanceEligible=False,
            samples=[{k:v for k,v in row.items() if k not in ('combatWindows', 'profile')}
                     for row in summary['samples']])), flush=True)
        lease.outcome = 'passed'
        lease.note = 'GUI.setWeapon inclusive diagnostic counters; no frame-performance acceptance or deployment'


if __name__ == '__main__':
    main()
