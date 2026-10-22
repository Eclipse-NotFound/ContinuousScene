"""Registered, diagnostic-only Location.step attribution on exact BEFC lineage.

Four 300-frame segments use the existing 200 px native platform fixture. Both
sides must really fire in every segment; every 30-frame boundary must retain
six armed living enemies. Natural short enemy reload pauses remain observable.
Only the isolated host and probe are replaced. No activity candidate or deploy.
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
OUT = B/'generated/location-step-profile-20261022'
FORMAL_HOST = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
FORMAL_CS = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
HOST = '349F04D4CEA7CE70E0DCCA16D91A79DF7F9D42BD05479E74E343F15DE77041C2'
HOST_XML = 'FC97B74E392E368823F1D6BB2803CC6AA9B91D2011F2223A584BB8E8A30E2CC5'
AUDIT = '14993A0C854F8CC669E33F32B64247A6F3E2F4B2C9D860DBDB29C11E852364C5'
TARGET = 'fe.loc.Location::0:1:step'
GROUPS = ('player', 'activity', 'objects', 'unit', 'box', 'bullet', 'other', 'unitCoord', 'lighting', 'post')
CS_PATH = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
PROBE_PATH = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('location_step_runner_helpers', B/'enemy-release.py')
m = r.motion


def source_hashes():
    src = B.parent/'src'
    return {p.relative_to(src).as_posix(): r.sha(p) for p in sorted(src.rglob('*.as'))}


def runner_inputs():
    paths = (Path(__file__), B/'enemy-release.py', B/'enemy-speed.py', B/'motion-test.py',
             B/'profile-vision.py', r.ROOT/'mods/ModLoader/tools/test_registry.py',
             r.ROOT/'mods/ModLoader/tools/air_test_process.py')
    return {str(p): r.sha(p) for p in paths}


def audited_host():
    build = r.read(OUT/'build.json')
    audit = r.read(OUT/'semantic-audit.json')
    assert build['version'] == 'location-step-profile-1' and build['target'] == TARGET
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
    assert audit['activationProof']['diagnosticLocals'] == 30
    assert audit['activationProof']['receiverEvidence']['numericSlotOperations'] == 307
    assert audit['activationProof']['receiverEvidence']['activationObjectEscapes'] is False
    assert audit['wrapperSHA256'] == r.sha(B/'location-step-profile-audit.py')
    assert all(r.sha(Path(path)) == digest for path, digest in build['sourceInputs'].items())
    return build


def compile_probe(lease):
    """Same 512 MiB compiler recipe, with explicit ownership and memory checks."""
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
    lease.before_launch('Location.step isolated probe compiler')
    try:
        process = subprocess.Popen(command)
        lease.child(process.pid)
        code = process.wait()
        if code:raise subprocess.CalledProcessError(code, command)
    finally:
        if process is not None:
            if process.poll() is None:process.kill(); process.wait(timeout=15)
            lease.child_stopped()


def check_stats(stats):
    assert stats['version'] == 'location-step-profile-1' and stats['calls'] == 300
    assert stats['diagnosticOnly'] is True and stats['performanceEligible'] is False
    assert stats['errorCalls'] == 0, 'Caught native object error invalidates profiling'
    for key in ('totalMs', 'totalMaxMs') + tuple(g + suffix for g in GROUPS for suffix in ('Ms', 'Calls', 'MaxMs')):
        value = stats[key]
        assert isinstance(value, (int, float)) and not isinstance(value, bool)
        assert math.isfinite(value) and value >= 0 and value == int(value), (key, value)
    for key in ('player', 'activity', 'objects', 'post'):
        assert stats[key+'Calls'] == 300, (key, stats[key+'Calls'])
    for key in ('unitCoord', 'lighting'):assert 0 <= stats[key+'Calls'] <= 300
    assert stats['unitCalls'] > 0 and stats['bulletCalls'] > 0
    assert sum(stats[key+'Ms'] for key in ('unit', 'box', 'bullet', 'other')) <= stats['objectsMs']
    assert sum(stats[key+'Ms'] for key in ('player', 'activity', 'objects', 'unitCoord', 'lighting', 'post')) <= stats['totalMs']


def six_armed(encounter):
    assert encounter['alive'] == 6 and encounter['armed'] == 6
    actors = encounter['actors']
    assert len(actors) == 6
    assert all(a['hp'] > 0 and a['weapon'] and a['weapon']['hp'] > 0 for a in actors)


def summarize(result, name, build):
    route = result['combatRoute']
    assert route['path'] == route['evidence']['playerPath'] == 200
    assert route['evidence']['version'] == 'existing-flat-combat-route-1' and route['evidence']['selected']
    assert route['checkedNativeSightLines'] == 30 and len(route['enemies']) == 6
    warmup = result['playerFireWarmup']
    assert warmup['shotFrames'] > 0 and warmup['encounter']['actualShotFrames'] > 0
    six_armed(warmup['encounter'])
    assert len(result['samples']) == 4
    summary = dict(name=name, diagnosticOnly=True, performanceEligible=False, deployed=False,
        checks=len(result['assertions']), combatRoute=route, playerFireWarmup=warmup,
        hostSHA256=HOST, limitations=build['limitations'], samples=[])
    for row_index, row in enumerate(result['samples']):
        assert len(row['frames']) == 300 and row['empty'] == 0 and row['misses'] == 0
        assert len(row['nativeBand']) == len(row['warm']) == 300
        # The first script interval starts before its recorder is attached.
        # Existing route evidence has 299 there; native/profile counts stay 300.
        assert len(row['totalScript']) in ((299, 300) if row_index == 0 else (300,))
        stats = row['locationProfile']; check_stats(stats)
        assert row['enemyShotFrames'] > 0 and row['playerShotFrames'] > 0
        six_armed(row['encounter'])
        assert len(row['combatWindows']) == 20
        windows = []
        for wi in range(10):
            pair = sorted((x for x in row['combatWindows'] if x['frame']//30 == wi), key=lambda x:x['frame'])
            assert len(pair) == 2 and [x['frame'] for x in pair] == [wi*30, wi*30+29]
            for sample in pair:six_armed(sample['encounter'])
            player = pair[1]['playerShots'] - pair[0]['playerShots']
            enemy = pair[1]['encounter']['actualShotFrames'] - pair[0]['encounter']['actualShotFrames']
            assert player > 0 and enemy >= 0
            windows.append(dict(window=wi, playerShots=player, enemyShots=enemy, population=pair))
        summary['samples'].append(dict(name=row['name'], frames=300, profile=stats,
            perFrame={key:stats[key+'Ms']/300 for key in GROUPS}, totalMsPerFrame=stats['totalMs']/300,
            nativeBand=statistics.mean(row['nativeBand']), script=statistics.mean(row['totalScript']),
            scriptSamples=len(row['totalScript']),
            playerShots=row['playerShotFrames'], enemyShots=row['enemyShotFrames'],
            warmed=sum(row['warm']), quietEnemyWindows=sum(w['enemyShots'] == 0 for w in windows), combatWindows=windows))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--compile-probe', action='store_true')
    parser.add_argument('--registry-wait', type=int, default=600)
    args = parser.parse_args()
    assert args.name and all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.name), 'Evidence name'
    assert not (r.E/args.name).exists(), 'Use a fresh evidence name'
    with m.Registration(owner='ContinuousScene / Location step diagnosis / 01a13816', purpose=args.name,
            run_dir=m.RUNTIME, evidence=r.E/args.name, wait=args.registry_wait) as lease:
        assert not m.air_pids(), 'Other AIR present; untouched'
        baseline = r.baseline()
        assert baseline['pfe.swf'] == FORMAL_HOST and baseline[CS_PATH] == FORMAL_CS
        build = audited_host()
        sources, scripts = source_hashes(), runner_inputs()
        if args.compile_probe:
            compile_probe(lease)
            assert sources == source_hashes() and scripts == runner_inputs(), 'Probe inputs changed during compile'
            r.save(OUT/'probe-build.json', dict(sourceSHA256=sources, runnerInputs=scripts,
                probeSHA256=r.sha(OUT/'ContinuousSceneProbe.swf'), hostSHA256=HOST,
                diagnosticOnly=True, performanceEligible=False))
        probe = r.read(OUT/'probe-build.json')
        assert probe['sourceSHA256'] == sources and probe['runnerInputs'] == scripts
        assert probe['probeSHA256'] == r.sha(OUT/'ContinuousSceneProbe.swf') and probe['hostSHA256'] == HOST
        assert probe['diagnosticOnly'] and not probe['performanceEligible']
        assert r.baseline() == baseline, 'Production drift before preparation'
        m.prepare()
        shutil.copy2(OUT/'pfe.swf', m.RUNTIME/'pfe.swf')
        shutil.copy2(OUT/'ContinuousSceneProbe.swf', m.RUNTIME/PROBE_PATH)
        assert r.sha(m.RUNTIME/CS_PATH) == FORMAL_CS, 'An activity/other CS candidate must not be used'
        assert sources == source_hashes() and scripts == runner_inputs(), 'Probe inputs changed before launch'
        options = ['--name', args.name, '--high-qos', '--encounter', '--fixed-enemies', '--benchmark', 'scene',
            '--speed', '4', '--short', '--location-profile', '--window-width', '2048', '--window-height', '1123',
            '--no-lighting', '--no-wall', '--expect-no-signs', '--stable-motion', '--player-fire',
            '--combat-route', '--combat-route-length', '200']
        m.run_owned(m.parse_args(options), lease)
        result, inputs = r.result(args.name)
        assert r.baseline() == baseline, 'Production drift'
        for path, digest in baseline.items():
            if path not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[path] == (HOST if path == 'pfe.swf' else digest), path
        assert inputs[PROBE_PATH] == probe['probeSHA256'] and inputs[CS_PATH] == FORMAL_CS
        policy = r.read(r.E/args.name/'process-policy.json')
        assert policy['performanceEligible'] is False and 'Location.step' in policy['diagnosticOnly']
        r.save(r.E/args.name/'probe-build.json', probe)
        summary = summarize(result, args.name, build)
        r.save(OUT/(args.name+'-summary.json'), summary)
        r.save(r.E/args.name/'location-profile-summary.json', summary)
        print(json.dumps(dict(name=args.name, diagnosticOnly=True, performanceEligible=False,
            samples=[{k:v for k,v in row.items() if k not in ('combatWindows', 'profile')}
                     for row in summary['samples']])), flush=True)
        lease.outcome = 'passed'
        lease.note = 'Location.step inclusive diagnostic counters; no frame-performance acceptance or deployment'


if __name__ == '__main__':
    main()
