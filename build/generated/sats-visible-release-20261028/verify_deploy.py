"""Verify the actual V3 production pair; --deploy is the only installation path.

Prepared source only. This module never starts games, compilers, or another tool.
Verification consumes completed frozen evidence and creates verification.json
exclusively. Deployment rechecks it, preserves configuration, and rolls back only
this invocation's targets whose current fingerprints still match its new bytes.
"""
from __future__ import annotations
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import argparse
from collections import Counter
import hashlib
import json
import os
import re
import shutil
import statistics
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]
ROOT = HERE.parents[4]
EVIDENCE_ROOT = MOD / 'knowledge/experiments/evidence'
FUNCTIONAL = EVIDENCE_ROOT / 'sats-visible-product-checks-v3-20261028-r1'
TRIAL = EVIDENCE_ROOT / 'camera-sats-visible-trial-v2-20261028-r1'
TRIAL_SOURCE = HERE.parent / 'camera-sats-visible-trial-v2-20261028'
PROBE_SOURCE = HERE.parent / 'sats-visible-product-checks-v3-20261028'
BASE = 'B84F24280B3C676F4068E1CDC5A6EBEE89988F62BCF7A44D4DD71A4771360184'
MOD_BASE = '9A5E24E13AF2E2E211FAEAC038697D2CA2641CD6482766048BC3B9B4A506AA31'
HOST = 'A80ED32BEE50C612CB46EA1E581C8CA9C81072E0B9E6EE1A51E5BACEFBDCBA19'
TRIAL_HOST = 'C3B45958ABB3611077ACC1AC3EEF015A14DB7235BB5782CB4876BFE929B4075A'
TRIAL_PROBE = '054767DFA12DD7C66AA8F52F5BAFC600267609A6F2C9CE85737D596E69E5CDAE'
RECEIPT = MOD / 'state/sats-visible-deployment-20261028.json'
VERIFICATION = HERE / 'verification.json'
PROBE_REL = 'mods/ContinuousSceneMotion/release/ContinuousSceneMotionMod.swf'
PRODUCT_REL = 'mods/ContinuousScene/release/ContinuousSceneMod.swf'
TARGET_METHODS = {
    'sceneSats': (3231, '69BF23AA7AC530656672D08F1E561D944E1366845A980A07A6119E8DA671BBF9',
                  '92F31C034C49FBD41CDEA26CD89A75C2D7DC5069714797FC26F6402F2667384D'),
    'sceneTick': (3219, 'DEFB11339BB22D7D55790C3E822B8451355EFA6101F6B0C17166711D3D69BF76',
                  'EC49069DEB696D09394C860D21AA95A52DD9A4CD879414C1A722459E81B0AFCF'),
    'onSats': (3282, '50C3A93BEACD1ED41B19F27122408535897F0DE595D8F3C635220BF7226CD092',
               'BF7ABB713DAF0453CE311405338EFEEC73D8CBDE8730AE545FE18EDD35C27E9B'),
    'sceneClear': (3209, '448E962DFEC38BE8AFC9011CDDEECE8DCC4A8E990683CDD4112A1B7BC699ECB2',
                   'C403F4D642806BC55644E5525E085047D118C9122E4604F4135659850E4CA480'),
}
V_CASES = [
    ('initial-base-native-rejection', False, False),
    ('large-effects-off', True, True),
    ('large-rv-light-wall-on', True, True),
    ('large-active-rebuild', True, True),
    ('base-after-large-native-rejection', False, False),
    ('ordinary-room-native-fallback', False, True),
    ('base-mode-reenabled-native-rejection', False, False),
]


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text('utf-8-sig'))


def canonical(path):
    return os.path.normcase(os.path.abspath(str(path)))


def relative_inputs(path):
    result = {}
    for name, value in read(path).items():
        item = PurePosixPath(name.replace('\\', '/'))
        need(not item.is_absolute() and '..' not in item.parts and ':' not in name,
             'Evidence input is not a relative local path: ' + name)
        key = item.as_posix()
        need(key not in result and re.fullmatch('[A-F0-9]{64}', value), 'Invalid input fingerprint')
        result[key] = value
    return result


def source_hash(inputs, path):
    matches = [value for name, value in inputs.items() if canonical(name) == canonical(path)]
    need(len(matches) == 1, 'Missing/ambiguous frozen source fingerprint: ' + str(path))
    return matches[0]


def check_file(path, expected):
    need(sha(path) == expected, 'Fingerprint changed: ' + str(path))


def check_inputs(inputs):
    for path, expected in inputs.items():
        check_file(path, expected)


def passed_checks(result):
    need(result.get('ok') is True and result.get('error') is None, 'Functional result failed or incomplete')
    rows = result.get('assertions', [])
    need(rows and all(row.get('ok') is True for row in rows), 'An assertion failed or evidence is absent')
    return Counter(row['name'] for row in rows)


def have(checks, name, count=1):
    need(checks[name] >= count, 'Missing successful assertion: ' + name)


def environment(directory, performance=False):
    policy = read(directory / 'process-policy.json')
    need(policy.get('desktopPolicy') == 'private' and policy.get('pid', 0) > 0,
         'Missing private owned AIR receipt')
    need(not policy.get('runFailure') and not policy.get('memoryAbort'), 'Run failed or memory-aborted')
    if performance:
        need(policy.get('otherAirProcessIds') == [], 'Other AIR invalidates the performance comparison')
        power = policy.get('powerPolicy', {}).get('applied', [])
        need(len(power) == 2 and power[0] & 1 and not power[1] & 1, 'Owned HighQoS was not confirmed')
        need(policy.get('minimumAvailableCommit', 0) >= 512 * 1024**2, 'Memory pressure invalidates timing')
    loader = read(directory / 'loader-check.json')
    need(len(loader.get('sessions', [])) == 1 and loader.get('loaded') and
         all(value is True for value in loader['loaded'].values()), 'Single-session loader verification failed')
    need(loader['loaded'].get('ContinuousSceneMod') and loader['loaded'].get('ContinuousSceneMotionMod'),
         'Product or diagnostic probe was not loaded')
    return policy, loader


def pixels(group, checks, repeats=1):
    cases = group.get('cases', [])
    need(len(cases) == 7 and [r['index'] for r in cases] == list(range(7)), 'Seven pixel cases required')
    for case in cases:
        need(case.get('compared', 0) > 0 and case.get('changed') == 0 and case.get('newChanged') == 0,
             'SATS pixel/fresh-exposure mismatch')
        need(case.get('attached', 0) > 0 and case.get('copies', 0) >= case['attached'], 'No copied image observed')
        for prefix in ('sats-pixels-', 'sats-frozen-reuse-', 'sats-actors-restored-'):
            have(checks, prefix + str(case['index']), repeats)
    for name in ('sats-close-releases-all-copies', 'sats-reopen-has-image', 'sats-test-explored-beyond-one-view'):
        have(checks, name, repeats)
    need(group.get('maxResident', 0) > group.get('maxAttached', 0) > 0, 'No beyond-one-view coverage')
    return len(cases)


def compact_as(source):
    """Remove comments/outer whitespace, preserving quoted literal contents."""
    pattern = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/|\s+|.', re.S)
    return ''.join(token for token in pattern.findall(source)
                   if not token.isspace() and not token.startswith('//') and not token.startswith('/*'))


def performance_bridge():
    old = compact_as((TRIAL_SOURCE / 'SatsVisibleGuard.as').read_text('utf-8-sig'))
    new = compact_as((HERE / 'SatsVisibleGuard.as').read_text('utf-8-sig'))
    replacements = [
        ('stats:Object={opens:0,closes:0,refreshes:', 'stats:Object={opens:0,closes:0,clears:0,refreshes:'),
        ('["satsVisibleV2"]=handle;', '["satsVisibleV3"]=handle;carrier["nativeAPI"]["satsVisibleStatsV3"]=stats;'),
        ('functionhandle(g:*,mode:int):Boolean{',
         'functionhandle(g:*,mode:int):Boolean{if(mode==3){clear(g);stats.clears++;returntrue;}'),
    ]
    expected = old
    for prior, replacement in replacements:
        need(expected.count(prior) == 1, 'Trial-to-product bridge anchor changed')
        expected = expected.replace(prior, replacement, 1)
    need(new == expected, 'Product screenshot algorithm differs beyond reviewed V3 lifecycle/stats changes')
    return dict(trialGuard=sha(TRIAL_SOURCE / 'SatsVisibleGuard.as'), productGuard=sha(HERE / 'SatsVisibleGuard.as'),
                unchangedCaptureAndViewAlgorithm=True, addedLifecycleClear=True, addedStatsObservation=True)


def verify_trial():
    result = read(TRIAL / 'storage/result.json')
    checks = passed_checks(result)
    need(result.get('version') == 'camera-sats-visible-trial-1', 'Wrong historical trial')
    policy, _ = environment(TRIAL, performance=True)
    receipt = read(TRIAL / 'camera-sats-inputs.json')
    actual = relative_inputs(TRIAL / 'inputs.json')
    need(receipt['base'] == BASE and receipt['host'] == actual['pfe.swf'] == TRIAL_HOST, 'Trial host mismatch')
    need(receipt['probe'] == actual[PROBE_REL] == TRIAL_PROBE, 'Trial probe mismatch')
    need(actual[PRODUCT_REL] == MOD_BASE, 'Trial must use original carrier')
    check_inputs(receipt['sourceInputs'])
    build = read(TRIAL_SOURCE / 'probe-build.json')
    need(build['compiled'] and build['outputSHA256'] == TRIAL_PROBE, 'Trial build receipt mismatch')
    check_inputs(build['inputs'])
    check_file(TRIAL_SOURCE / 'ContinuousSceneMotionMod.swf', TRIAL_PROBE)
    need(result.get('satsOrder') == [False, True, True, False, False, True], 'Native V restore sequence changed')
    rounds = result.get('sats', [])
    need(len(rounds) == 6, 'Six native V rounds required')
    have(checks, 'six-native-v-trials')
    target_counts, cameras, native_off, native_on = [], [], [], []
    for i, row in enumerate(rounds):
        enabled = result['satsOrder'][i]
        need(row['round'] == i and row['enabled'] is enabled and row['keyAccepted'], 'V round not executed as planned')
        for prefix in ('native-v-opens-', 'sats-no-ap-charge-', 'guard-open-dispatch-', 'sats-next-frame-visible-', 'native-v-closes-'):
            have(checks, prefix + str(i))
        need(row['helperOpened']['opens'] - row['helperBefore']['opens'] == int(enabled), 'No real on/off dispatch contrast')
        need(row['helperAfterClose']['closes'] > row['helperBefore']['closes'], 'No native close restoration')
        if enabled:
            need(row['helperOpened']['captures'] > row['helperBefore']['captures'], 'No candidate capture')
        target_counts.append(row['nativeTargetCount']); cameras.append(row['camera'])
        (native_on if enabled else native_off).append(row['openObserverMs'])
    need(min(target_counts) > 0 and len(set(target_counts)) == 1 and all(c == cameras[0] for c in cameras),
         'Native V comparison changed camera/target count')
    need(max(native_on) < min(native_off), 'Native V observations do not consistently improve')
    pixels(result['pixels'], checks)
    timing = result['pixels'].get('openingTiming', [])
    need([r['approach'] for r in timing] == ['legacy', 'candidate', 'candidate', 'legacy'], 'Missing ABBA component comparison')
    need(len({r['resident'] for r in timing}) == 1 and timing[0]['resident'] > 1, 'ABBA residency changed')
    old = [r['ms'] for r in timing if r['approach'] == 'legacy']
    new = [r['ms'] for r in timing if r['approach'] == 'candidate']
    need(min(new) > 0 and max(new) < min(old), 'ABBA does not show a consistent improvement')
    return dict(kind='Historical V2 same-world component ABBA and six native V openings; not frame-rate acceptance',
                host=TRIAL_HOST, probe=TRIAL_PROBE, pid=policy['pid'], nativeOffMs=native_off, nativeOnMs=native_on,
                abba=timing, componentMeanReduction=1-statistics.mean(new)/statistics.mean(old),
                algorithmBridge=performance_bridge(), cameraStutterResolved=False)


def verify_product(pair, product):
    receipt = read(FUNCTIONAL / 'sats-product-inputs.json')
    result = read(FUNCTIONAL / 'storage/result.json')
    checks = passed_checks(result)
    need(receipt.get('passed') is True and receipt.get('pair') == pair, 'Actual product pair did not complete its test')
    need(receipt.get('resultSHA256') == sha(FUNCTIONAL / 'storage/result.json') and
         receipt.get('assertions') == len(result['assertions']), 'Functional result changed after producer validation')
    need(result.get('version') == 'sats-visible-product-checks-3', 'Only V3 export-based product evidence is accepted')
    need(result.get('guardInstalledByProbe') is False and result.get('linkedGuardImplementation') is False,
         'Probe installed/linked its own handler instead of testing the product')
    check_inputs(receipt['sourceInputs'])
    probe = read(PROBE_SOURCE / 'probe-build.json')
    need(probe['compiled'] and probe['outputSHA256'] == receipt['probe'], 'Product test probe build mismatch')
    check_inputs(probe['inputs'])
    check_file(PROBE_SOURCE / 'ContinuousSceneMotionMod.swf', receipt['probe'])
    actual = relative_inputs(FUNCTIONAL / 'inputs.json')
    need(actual['pfe.swf'] == pair['host'] and actual[PRODUCT_REL] == pair['product'] and
         actual[PROBE_REL] == receipt['probe'], 'Runtime did not use the verified host/product/probe trio')
    policy, loader = environment(FUNCTIONAL)
    need(receipt['productionBaseline'] == {str(ROOT/'pfe.swf'):BASE, str(MOD/'release/ContinuousSceneMod.swf'):MOD_BASE},
         'Functional test production baseline differs')
    for name in ('startup-product-carrier', 'startup-product-handler-export', 'startup-product-stats-export',
                 'functional-chain-complete', 'initial-base-native', 'natural-base-after-large',
                 'ordinary-room-size', 'base-stays-native-after-mode-toggle'):
        have(checks, name)
    rounds = result.get('sats', [])
    need(len(rounds) == len(V_CASES), 'Seven native V scenarios were not completed')
    for row, (label, large, opens) in zip(rounds, V_CASES):
        need(row['label'] == label and row['large'] is large and row['expectOpen'] is opens and row['keyAccepted'],
             'Wrong or missing native V scenario: ' + label)
        for suffix in ('product-carrier','product-handler-export','product-stats-export','product-handler-identity',
                       'scene-mode','native-key-accepted','open-state','open-no-ap-charge','handler-open-count'):
            have(checks, label + '-' + suffix)
        need(row['statsOpened']['opens'] - row['statsBefore']['opens'] == int(large and opens), 'Wrong large/native fallback dispatch')
        if large and opens:
            have(checks, label + '-product-captured-on-native-v')
            need(row['statsOpened']['captures'] > row['statsBefore']['captures'] and row['copiesOpened'] > 0,
                 'No real product capture on native V')
        if opens:
            for suffix in ('actor-layer-hidden','snapshot-route','native-close','native-targets-cleared','owned-copies-released'):
                have(checks, label + '-' + suffix)
            need(row['statsClosed']['closes'] > row['statsBefore']['closes'], 'Close hook not observed')
            if not large:
                need(row['copiesOpened'] == 0, 'Ordinary room did not retain native screenshot path')
        else:
            have(checks, label + '-base-still-running')
    need(set(result.get('pixels', {})) == {'effectsOff', 'effectsOn'}, 'Both effects configurations required')
    pixel_count = sum(pixels(result['pixels'][mode], checks, 2) for mode in ('effectsOff', 'effectsOn'))
    for name in ('off-pixels-returned-closed', 'on-pixels-returned-closed'):
        have(checks, name)
    settings = result['settings']
    for mod, key in [('wallblend','enabled'),('realisticvision','enabled'),('realisticvision','wallbright'),('light-and-darkness','enabled')]:
        need({r['actual'] for r in settings if r['mod'] == mod and r['key'] == key} == {False, True},
             'Effects on/off settings were not confirmed: '+mod+'.'+key)
    life = result.get('lifecycle') or {}
    need(life.get('oldCopies', 0) > 0 and life.get('sameGrafon') and life.get('sameLocation') and
         life.get('clearedAllOldEntries') and life.get('disposedAllOldPixels'), 'No positive same-Grafon clear/disposal evidence')
    need(life['statsAfterClear']['clears'] > life['statsBefore']['clears'] and
         life['statsAfterExposure']['opens'] > life['statsAfterClear']['opens'] and
         life['statsAfterClose']['closes'] > life['statsAfterExposure']['closes'], 'Clear/recapture/close lifecycle counters not positive')
    for i in range(life['oldCopies']):
        for prefix in ('rebuild-old-entry-null-','rebuild-old-bitmap-detached-','rebuild-old-data-disposed-'):
            have(checks, prefix + str(i))
    for name in ('rebuild-mode3-dispatched','rebuild-next-frame-recaptured','rebuild-next-frame-fresh-open',
                 'rebuild-close-cleared-current-copies'):
        have(checks, name)
    return actual, loader, dict(pid=policy['pid'], pair=pair, nativeVScenarios=len(rounds),
                               pixelCases=pixel_count, lifecycle=life, assertions=len(result['assertions']),
                               performanceClaim='Functional product verification only')


def dependencies(actual, loader):
    selected, excluded = {}, {}
    transient = {'sessions','drafts','logs','events','commands','responses','backups'}
    for name, value in actual.items():
        parts = PurePosixPath(name).parts
        lower = [part.lower() for part in parts]
        if len(parts) < 4 or lower[0] != 'mods':
            continue
        if lower[1] in {'continuousscenemotion','continuoussceneprobe'}:
            excluded[name] = 'Isolated diagnostic probe, never deployed'
            continue
        if name.lower() == 'mods/modloader/release/telemetry.json':
            excluded[name] = 'Isolated loader telemetry controls, not production configuration'
            continue
        suffix = PurePosixPath(name).suffix.lower()
        is_swf = lower[2] == 'release' and suffix == '.swf'
        is_release_config = lower[2] == 'release' and (
            lower[-1] in {'config.txt','config.json','config.xml','config.ini','config.cfg','scene.xml'})
        is_config = lower[2] == 'config' and suffix in {'.json','.txt','.xml','.ini','.cfg'} and not transient.intersection(lower[3:])
        if (is_swf or is_release_config or is_config) and name != PRODUCT_REL:
            selected[name] = value
    atmosphere = 'mods/LightAndDarkness/atmosphere.json'
    need(atmosphere in actual, 'Missing tested lighting configuration')
    selected[atmosphere] = actual[atmosphere]
    need(selected and any(name.endswith('ModLoaderMod.swf') for name in selected), 'Actual loader runtime must remain pinned')
    # Test manifests include the diagnostic probe. Compare the active production
    # entry set semantically; retain the untouched production file's own hash.
    manifest = ROOT / 'mods/loader-manifest.txt'
    active = {}
    for line in manifest.read_text('utf-8-sig').splitlines():
        if line.strip().startswith('#'):
            continue
        fields = line.split('|')
        if len(fields) == 5 and fields[2] == '1':
            directory, entry = fields[:2]
            need(directory not in ('', '.', '..') and '/' not in directory and '\\' not in directory,
                 'Invalid active loader directory')
            need(re.fullmatch('[A-Za-z0-9_]+', entry), 'Invalid active loader class')
            need(entry not in active, 'Duplicate active loader entry')
            active[entry] = 'mods/' + directory + '/release/' + entry + '.swf'
    need(set(active) == set(loader['loaded']) - {'ContinuousSceneMotionMod'},
         'Production selected modules differ from tested modules')
    lookup = {name.lower(): value for name, value in actual.items()}
    for entry, name in active.items():
        need(name.lower() in lookup, 'Selected production module missing from test inputs: ' + entry)
        if entry != 'ContinuousSceneMod':
            selected[name] = lookup[name.lower()]
    check_inputs({str(ROOT/name): value for name, value in selected.items()})
    # Pin installation-chain/configuration preservation without treating the
    # test's unique application ID and test-control manifest as production files.
    descriptor = ROOT / 'application.xml'
    doc = ET.fromstring(descriptor.read_text('utf-8-sig'))
    contents = [e.text for e in doc.iter() if e.tag.rsplit('}', 1)[-1] == 'content']
    need(contents == ['pfe.swf'], 'Active application is not the root host')
    unchanged = dict(selected)
    for name in ('application.xml','mods/loader-manifest.txt','mods/ModLoader/supported-mods.txt',
                 'DLC/pfe.swf','DLC/pfeUI.swf'):
        unchanged[name] = sha(ROOT/name)
    return dict(sorted(unchanged.items())), dict(sorted(excluded.items()))


def source_and_host():
    need(HERE.name == 'sats-visible-release-20261028', 'Wrong release directory')
    host = read(HERE/'host-audit.json')
    product = read(HERE/'product-build.json')
    need(host.get('passed') is True and host.get('base') == BASE and
         host.get('candidate') == host.get('identicalFrozenHost') == HOST, 'Unverified or different host patch')
    need(host.get('handlerAction') == 'satsVisibleV3' and host.get('sceneClearHookBeforeNativeDrop') is True,
         'Missing V3 lifecycle hook')
    for key in ('exactInverseRestoresABC','unitBoundaryFixPreserved','loaderPreserved','requiresExplicitHandlerInstall'):
        need(host.get(key) is True, 'Host preservation proof absent: '+key)
    need(host.get('unchangedOtherMainBodies') == 3281 and host.get('unchangedClasses') == 350 and
         host.get('preservedRawTags') == 5038 and host.get('closeMode') == 2 and host.get('sceneClearMode') == 3,
         'Host preservation counts or lifecycle modes changed')
    methods = host.get('methods', [])
    need(len(methods) == 4 and {r['name'] for r in methods} == set(TARGET_METHODS), 'Host changes are not the four reviewed methods')
    for row in methods:
        index, old, new = TARGET_METHODS[row['name']]
        need((row['method'],row['oldCodeSHA256'],row['newCodeSHA256']) == (index,old,new) and
             row.get('unchangedOriginalInstructions') is True and row.get('unchangedTraits') is True,
             'Host method audit mismatch: '+row['name'])
    check_inputs(host['sourceInputs'])
    check_file(HERE/'pfe.swf', HOST)
    need(product.get('compiled') is True and product.get('productOnly') is True and
         product.get('version') == '0.9.2' and product.get('hostBaseline') == BASE and
         product.get('modBaseline') == MOD_BASE and product.get('handlerAction') == 'satsVisibleV3' and
         product.get('statsExport') == 'satsVisibleStatsV3', 'Not the completed V3 product build')
    product_sha = product.get('outputSHA256', '')
    need(re.fullmatch('[A-F0-9]{64}', product_sha) and product_sha != MOD_BASE, 'Missing actual compiled product fingerprint')
    check_file(HERE/'ContinuousSceneMod.swf', product_sha)
    need(set(product['sourceFilesChanged']) == {'ContinuousSceneMod.as','SatsVisibleGuard.as'}, 'Unexpected product source scope')
    # Only the affected official source is locked to its build-time fingerprint;
    # unrelated WIP sources/tests are neither read nor required to be clean.
    entry_old = source_hash(product['inputs'], MOD/'src/ContinuousSceneMod.as')
    check_file(MOD/'src/ContinuousSceneMod.as', entry_old)
    need(not os.path.lexists(MOD/'src/SatsVisibleGuard.as'), 'Guard source already exists; do not overwrite a concurrent integration')
    entry_new = product['frozenSource']['ContinuousSceneMod.as']
    guard_new = product['frozenSource']['SatsVisibleGuard.as']
    check_file(HERE/'product-src/ContinuousSceneMod.as', source_hash(product['inputs'], HERE/'product-src/ContinuousSceneMod.as'))
    check_file(HERE/'SatsVisibleGuard.as', source_hash(product['inputs'], HERE/'SatsVisibleGuard.as'))
    for name, expected in [('ContinuousSceneMod.as',entry_new),('SatsVisibleGuard.as',guard_new)]:
        check_file(HERE/'frozen-product-src'/name, expected)
    check_file(HERE/'product-src/ContinuousSceneMod.as', entry_new)
    check_file(HERE/'SatsVisibleGuard.as', guard_new)
    check_file(HERE/'compile_product.py', source_hash(product['inputs'], HERE/'compile_product.py'))
    check_file(HERE/'product-compiler.xml', product['configSHA256'])
    original = (MOD/'src/ContinuousSceneMod.as').read_text('utf-8-sig')
    changes = [('public static const VERSION:String="0.9.1";', 'public static const VERSION:String="0.9.2";'),
               ('            main.addChild(carrier); log("v"+VERSION+" loaded");',
                '            main.addChild(carrier); log("v"+VERSION+" loaded");\n            SatsVisibleGuard.install(main);')]
    for prior, replacement in changes:
        need(original.count(prior) == 1, 'Changed source integration anchor')
        original = original.replace(prior, replacement, 1)
    need(original == (HERE/'product-src/ContinuousSceneMod.as').read_text('utf-8-sig'), 'Entry modifies more than version and install')
    return host, product, dict(host=HOST, product=product_sha,
                              hostAudit=sha(HERE/'host-audit.json'), productBuild=sha(HERE/'product-build.json')), \
           dict(entryOld=entry_old, entryNew=entry_new, guardNew=guard_new)


def verify():
    check_file(ROOT/'pfe.swf', BASE)
    check_file(MOD/'release/ContinuousSceneMod.swf', MOD_BASE)
    host, product, pair, sources = source_and_host()
    actual, loader, behavior = verify_product(pair, product)
    trial = verify_trial()
    unchanged, excluded = dependencies(actual, loader)
    evidence_files = [HERE/'host-audit.json',HERE/'product-build.json',Path(__file__),
                      FUNCTIONAL/'sats-product-inputs.json',FUNCTIONAL/'storage/result.json',FUNCTIONAL/'inputs.json',
                      FUNCTIONAL/'loader-check.json',FUNCTIONAL/'process-policy.json',
                      PROBE_SOURCE/'probe-build.json',TRIAL/'camera-sats-inputs.json',TRIAL/'storage/result.json',
                      TRIAL/'inputs.json',TRIAL/'loader-check.json',TRIAL/'process-policy.json',TRIAL_SOURCE/'probe-build.json']
    return dict(verified=True, version='0.9.2', productPair=pair, sourceFingerprints=sources,
                originalHost=BASE, originalMod=MOD_BASE, functional=behavior, satsOpeningEvidence=trial,
                preservedHost=dict(otherMainBodies=3281,classesInChangedABC=350,rawTags=5038,
                                   boundaryFix=True,loader=True,originalInstructions=True),
                unchangedRuntimeInputs=unchanged, excludedTestInputs=excluded,
                evidence={str(p):sha(p) for p in evidence_files},
                scope='SATS snapshot opening and lifecycle only; overall camera/performance goal remains incomplete',
                playerStorageTouched=False, configurationsToWrite=[], filesToChange=[
                    str(ROOT/'pfe.swf'),str(MOD/'release/ContinuousSceneMod.swf'),
                    str(MOD/'src/ContinuousSceneMod.as'),str(MOD/'src/SatsVisibleGuard.as')])


def checked_path(path, may_be_missing=False):
    path = Path(path).absolute()
    need(canonical(path).startswith(canonical(ROOT)+os.sep), 'Write path escapes workspace')
    relative = path.relative_to(ROOT)
    current = ROOT
    for part in relative.parts:
        current = current/part
        if not os.path.lexists(current):
            need(may_be_missing, 'Write parent or target is missing: '+str(current))
            continue
        info = current.lstat()
        need(not current.is_symlink() and not (getattr(info,'st_file_attributes',0) & 0x400),
             'Refuse reparse/symlink write path: '+str(current))
    return path


def write_bytes_exclusive(path, data):
    checked_path(path, may_be_missing=True)
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    check_file(path, digest(data))


def write_json_exclusive(path, value):
    """Windows rename cannot replace an existing receipt; preserve prior evidence."""
    need(os.name == 'nt', 'This exact deployment recipe is Windows-only')
    path = checked_path(path, may_be_missing=True)
    data = (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    temp = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    expected = digest(data)
    try:
        write_bytes_exclusive(temp,data)
        need(not os.path.lexists(path), 'Preserve existing evidence: '+str(path))
        os.rename(temp,path)  # Windows: fails if destination exists, no replacement.
        check_file(path,expected)
    finally:
        if temp.exists() and sha(temp)==expected:
            temp.unlink()


def recheck_unchanged(proof):
    check_inputs({str(ROOT/name):value for name,value in proof['unchangedRuntimeInputs'].items()})
    check_inputs(proof['evidence'])


def install_target(row, token):
    target = checked_path(row['target'],may_be_missing=row['old'] is None)
    source = Path(row['source'])
    data = source.read_bytes()
    need(digest(data)==row['new'], 'Candidate changed while staging: '+str(source))
    if row['old'] is None:
        # On Windows rename fails if a destination appeared. Stage complete
        # bytes first, so even an interrupted write leaves no partial src guard.
        temp=target.with_name(target.name+'.sats-visible-'+token+'.tmp')
        row['staged']=str(temp)
        write_bytes_exclusive(temp,data)
        need(not os.path.lexists(target),'Guard source appeared while staging')
        os.rename(temp,target)
        row['createdByThisRun']=True
        row['installed']=True
        check_file(target,row['new'])
        return
    temp = target.with_name(target.name+'.sats-visible-'+token+'.tmp')
    row['staged']=str(temp)
    write_bytes_exclusive(temp,data)
    check_file(target,row['old'])
    # Fingerprint is checked immediately before atomic replacement. The separate
    # deployment lock serializes this recipe; other tasks must still be detected
    # by fingerprints, and never overwritten during rollback if they diverged.
    os.replace(temp,target)
    row['installed']=True
    check_file(target,row['new'])


def rollback(rows, token):
    results=[]
    for row in reversed(rows):
        if not row.get('installed') and not row.get('createdByThisRun'):
            continue
        target=Path(row['target'])
        item=dict(target=str(target),restored=False)
        try:
            checked_path(target)
            current=sha(target)
            if current!=row['new']:
                item.update(skipped=True,reason='Current fingerprint differs; preserve concurrent/partial content',current=current)
            elif row['old'] is None:
                need(row.get('createdByThisRun') is True,'New guard was not created by this invocation')
                check_file(target,row['new'])
                target.unlink()
                item.update(restored=True,action='Removed only this invocation\'s exact new guard')
            else:
                saved=Path(row['backup']);check_file(saved,row['old'])
                temporary=target.with_name(target.name+'.sats-visible-rollback-'+token+'.tmp')
                row['rollbackStaged']=str(temporary)
                write_bytes_exclusive(temporary,saved.read_bytes())
                check_file(target,row['new'])
                os.replace(temporary,target);check_file(target,row['old'])
                item.update(restored=True,action='Restored verified prior bytes')
        except BaseException as error:
            item.update(error=type(error).__name__+': '+str(error))
        results.append(item)
    return results


def deploy(proof):
    need(os.name=='nt','This exact deployment recipe is Windows-only')
    need(not os.path.lexists(RECEIPT),'Preserve prior deployment receipt')
    token=datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:12]
    backup=checked_path(MOD/'build/backups'/('sats-visible-'+token),may_be_missing=True)
    lock=checked_path(MOD/'state/sats-visible-deploy.lock',may_be_missing=True)
    lock_data=(token+'\n').encode('ascii')
    lock_digest=digest(lock_data)
    write_bytes_exclusive(lock,lock_data)
    rows=[]; failure=None; success=None
    try:
        # Recompute after acquiring our lock. This also checks the old entry hash
        # obtained from product-build inputs, not a guessed current fingerprint.
        need(verify()==proof,'Verification changed before deployment')
        need(read(VERIFICATION)==proof,'Saved verification differs')
        recheck_unchanged(proof)
        need(not os.path.lexists(RECEIPT),'Deployment receipt appeared concurrently')
        backup.mkdir(parents=True,exist_ok=False)
        source=proof['sourceFingerprints'];pair=proof['productPair']
        rows=[
            dict(target=str(MOD/'src/SatsVisibleGuard.as'),source=str(HERE/'frozen-product-src/SatsVisibleGuard.as'),old=None,new=source['guardNew']),
            dict(target=str(MOD/'src/ContinuousSceneMod.as'),source=str(HERE/'frozen-product-src/ContinuousSceneMod.as'),old=source['entryOld'],new=source['entryNew'],backup=str(backup/'ContinuousSceneMod.as')),
            dict(target=str(MOD/'release/ContinuousSceneMod.swf'),source=str(HERE/'ContinuousSceneMod.swf'),old=MOD_BASE,new=pair['product'],backup=str(backup/'ContinuousSceneMod.swf')),
            dict(target=str(ROOT/'pfe.swf'),source=str(HERE/'pfe.swf'),old=BASE,new=HOST,backup=str(backup/'pfe.swf')),
        ]
        for row in rows:
            checked_path(row['target'],may_be_missing=row['old'] is None)
            check_file(row['source'],row['new'])
            if row['old'] is None:
                need(not os.path.lexists(row['target']),'Guard source appeared concurrently')
            else:
                check_file(row['target'],row['old'])
                data=Path(row['target']).read_bytes()
                need(digest(data)==row['old'],'Concurrent change while reading backup')
                write_bytes_exclusive(Path(row['backup']),data)
        write_json_exclusive(backup/'before.json',dict(token=token,targets=rows,verification=proof))
        for row in rows:
            recheck_unchanged(proof)
            # Never overwrite a known concurrent change in an uninstalled target.
            for pending in rows:
                if pending.get('installed'):
                    check_file(pending['target'],pending['new'])
                elif pending['old'] is None:
                    need(not os.path.lexists(pending['target']),'Concurrent new source integration')
                else:
                    check_file(pending['target'],pending['old'])
            install_target(row,token)
        for row in rows:
            check_file(row['target'],row['new'])
        recheck_unchanged(proof)
        success=dict(installed=True,installedAt=datetime.now(timezone.utc).isoformat(),token=token,
                     version='0.9.2',host=HOST,mod=pair['product'],priorHost=BASE,priorMod=MOD_BASE,
                     backup=str(backup),targets=rows,verification=proof,verificationSHA256=sha(VERIFICATION),
                     installedReadbackPassed=True,playerStorageTouched=False,playerProcessesTouched=False,
                     configurationsChanged=False,otherModsChanged=False,
                     validationReuse='Same functionally tested V3 host/product pair and pinned runtime dependencies; no loading-chain/configuration changes.',
                     limitation='SATS opening/lifecycle fix only; camera motion performance goal remains incomplete.')
        write_json_exclusive(RECEIPT,success)
        return success
    except BaseException as error:
        failure=dict(installed=False,failedAt=datetime.now(timezone.utc).isoformat(),token=token,
                     error=type(error).__name__+': '+str(error),backup=str(backup),targets=rows,
                     rollback=rollback(rows,token),playerStorageTouched=False,configurationsChanged=False)
        # Never overwrite another invocation's receipt. Keep failure evidence in
        # our unique backup even when the public receipt was created concurrently.
        if backup.exists():
            write_json_exclusive(backup/'failure.json',failure)
        if not os.path.lexists(RECEIPT):
            write_json_exclusive(RECEIPT,failure)
        raise
    finally:
        for row in rows:
            for field,expected in [('staged',row['new']),('rollbackStaged',row['old'])]:
                path=Path(row[field]) if row.get(field) else None
                if path and path.exists() and expected and sha(path)==expected:
                    checked_path(path);path.unlink()
        if lock.exists() and sha(lock)==lock_digest:
            lock.unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--verify',action='store_true',help='Verify only (default); exclusive verification.json output')
    mode.add_argument('--deploy',action='store_true',help='Explicitly install this exact verified pair and source')
    args=parser.parse_args()
    proof=verify()
    if args.deploy and VERIFICATION.exists():
        need(read(VERIFICATION)==proof,'Existing verification does not match current evidence/inputs')
    else:
        write_json_exclusive(VERIFICATION,proof)
    if args.deploy:
        result=deploy(proof)
        print(json.dumps(dict(installed=True,host=result['host'],mod=result['mod'],backup=result['backup'],receipt=str(RECEIPT))))
    else:
        print(json.dumps(dict(verified=True,deployed=False,host=proof['productPair']['host'],
                              mod=proof['productPair']['product'],verification=str(VERIFICATION))))


if __name__=='__main__':
    main()
