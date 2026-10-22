"""Isolated RC 574D offline presentation sampling experiment; never deploys."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
BUILD = Path(__file__).resolve().parent
GAME = BUILD.parents[2]
BASE = GAME / 'mods/RConnect/build/m52/coop-bundle-04'
OUT = BUILD / 'generated/rc-offline-probe-20261023-r1'
PREPARED_SHA = '4D0743B2FDD61586B22193C431E5D5FBA534D77CA33E0BC5483B2F286AE112B1'
FORMAL_RC = '574D2B51490AE8B25A1396555600F56A301F8A20AE50104C0E35CF2796441AFE'
CHANGED = {'src/RConnectMod.as', 'src/rconnect/core/Session.as', 'src/rconnect/game/GameBridge.as'}
JAVA = Path('D:/Program Files/Adobe Animate 2024/jre/bin/java.exe')
SDK = GAME / 'mods/Sandevistan/build/tools/flexsdk'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


SESSION_API = '''      // Isolated probe: one network attempt permanently revokes eligibility.
      public var offlineProbeEnabled:Boolean=false;
      private var _networkAttempted:Boolean=false;
      public function get networkAttempted():Boolean {return _networkAttempted;}
      public function offlineProbeEligible():Boolean {
         return offlineProbeEnabled && !_networkAttempted && mode===OFFLINE;
      }

'''

CARRIER = '''
      private function installOfflineProbeCarrier():void
      {
         // No control surface in a normal installation. The switch stays false.
         try
         {
            var appID:String=NativeApplication.nativeApplication.applicationID;
            if(appID.indexOf("pfe-modsettings-continuous-motion-")!=0)return;
            if(main["getChildByName"]("RConnectOfflineProbeCarrier")!=null)
               throw new Error("Duplicate offline probe carrier");
            var probeSession:Session=session;
            var probeGame:GameBridge=game;
            var carrier:MovieClip=new MovieClip();
            carrier.name="RConnectOfflineProbeCarrier";
            carrier["rcOfflineProbeAPI"]={version:"rc-offline-probe-1",
               setEnabled:function(value:Boolean):void {probeSession.offlineProbeEnabled=value;},
               snapshot:function():Object {
                  var result:Object=probeGame.offlineProbeSnapshot();
                  result.enabled=probeSession.offlineProbeEnabled;
                  result.eligible=probeSession.offlineProbeEligible();
                  result.mode=probeSession.mode;
                  result.networkAttempted=probeSession.networkAttempted;
                  return result;
               }};
            main["addChild"](carrier);
         }
         catch(error:*) {Log.d("RConnect offline probe unavailable: "+error);}
      }
'''

BRIDGE_API = '''      // Null/unknown/throwing eligibility preserves every original sample.
      public var offlineProbeEligibility:Function=null;
      private var _offlineProbeChecks:uint=0;
      private var _offlineProbeErrors:uint=0;
      private var _offlineProbeMirrorSkipped:uint=0;
      private var _offlineProbeFinalSkipped:uint=0;
      private function skipOfflineCollection(finalPass:Boolean):Boolean {
         var skip:Boolean=false;
         ++_offlineProbeChecks;
         try {
            if(offlineProbeEligibility!=null)skip=offlineProbeEligibility()===true;
         }
         catch(error:*) {++_offlineProbeErrors;}
         if(skip) {
            if(finalPass)++_offlineProbeFinalSkipped;
            else ++_offlineProbeMirrorSkipped;
         }
         return skip;
      }
      public function offlineProbeSnapshot():Object {
         return {version:"rc-offline-probe-1",diagnosticOnly:true,performanceAcceptance:false,
            mirrorSkipped:_offlineProbeMirrorSkipped,finalSkipped:_offlineProbeFinalSkipped,
            perceptionSkipped:0,perceptionGated:false,
            eligibilityChecks:_offlineProbeChecks,eligibilityErrors:_offlineProbeErrors};
      }

'''


def modify(name, original):
    """Small exact replacements, with reverse reconstruction of every byte."""
    if name not in CHANGED:
        return original
    source = original.decode('utf-8')
    assert '\r' not in source, 'Unexpected source line endings'
    edits = []

    def edit(before, after):
        nonlocal source
        assert source.count(before) == 1, (name, before[:100], source.count(before))
        source = source.replace(before, after, 1)
        edits.append((before, after))

    if name == 'src/rconnect/core/Session.as':
        edit('      public var mod:RConnectMod;', SESSION_API + '      public var mod:RConnectMod;')
        for method in ('startHost', 'startJoin'):
            before = '      public function ' + method + '():void\n      {\n         stop();'
            edit(before, before.replace('         stop();', '         _networkAttempted=true;\n         stop();'))
        assert source.count('_networkAttempted=true;') == 2
        assert source.count('_networkAttempted:Boolean=false;') == 1
    elif name == 'src/RConnectMod.as':
        edit('   import flash.display.Stage;', '   import flash.desktop.NativeApplication;\n   import flash.display.MovieClip;\n   import flash.display.Stage;')
        edit('         this.session = new Session(this);', '''         this.session = new Session(this);
         var probeSession:Session=this.session;
         game.offlineProbeEligibility=function():Boolean {return probeSession.offlineProbeEligible();};
         installOfflineProbeCarrier();''')
        edit('      }\n   }\n}', '      }\n' + CARRIER + '   }\n}')
        assert source.index('this.game = new GameBridge(main);') < source.index('this.session = new Session(this);')
        assert source.index('game.offlineProbeEligibility=') < source.index('session.autoStart();')
    elif name == 'src/rconnect/game/GameBridge.as':
        edit('      public var main:Object;', BRIDGE_API + '      public var main:Object;')
        final = '''            if(gg!=null)_presentation.observePlayer(gg,_sampleAt);
            if(gg!=null)_bodyEffects.observe(gg,_sampleAt);
            if(!_mirroring)_presentation.observeFinal(loc,_sampleAt);'''
        mirror = '''         if(!_mirroring) _presentation.observe(loc,_sampleAt);
         if(gg!=null)_presentation.observePlayer(gg,_sampleAt);
         if(gg!=null)_bodyEffects.observe(gg,_sampleAt);'''
        for block, indent, final_pass in ((final, '            ', 'true'), (mirror, '         ', 'false')):
            edit(block, indent + 'if(!skipOfflineCollection(' + final_pass + ')) {\n' +
                 '\n'.join('   ' + line for line in block.splitlines()) + '\n' + indent + '}')
        # Early observation, wall replay, native timestamp and AI remain byte-identical.
        start = '      private function onPerceptionFrame(e:Event):void'
        end = '      private function presentationTime()'
        assert source.split(start)[1].split(end)[0] == original.decode('utf-8').split(start)[1].split(end)[0]
        for line in ('_wall.observe(loc);', 'if(gg!=null)_ports.observe(gg,_sampleAt,roomKey(),roomEpoch);',
                     'try {main.stage.invalidate();} catch(stageError:*) {}'):
            assert source.count(line) == original.decode('utf-8').count(line)
    else:
        return original
    reversed_source = source
    for before, after in reversed(edits):
        assert reversed_source.count(after) == 1, (name, 'Ambiguous reverse edit')
        reversed_source = reversed_source.replace(after, before, 1)
    assert reversed_source.encode('utf-8') == original, name
    return source.encode('utf-8')


def verify_files(root, manifest):
    for name, expected in manifest.items():
        assert sha(root / name) == expected.upper(), str(root / name)


def tool_inputs():
    paths = [JAVA, SDK / 'bin/amxmlc.bat', SDK / 'lib/mxmlc.jar', SDK / 'lib/compc.jar',
             SDK / 'frameworks/air-config.xml', SDK / 'frameworks/libs/air/airglobal.swc']
    return {str(path): sha(path) for path in paths}


def compile_command():
    return [sys.executable, '-B', str(OUT / 'candidate/tools/build_mod.py'),
            '--amxmlc', str(SDK / 'bin/amxmlc.bat'), '--java', str(JAVA),
            '--output', str(OUT / 'RConnectMod.swf')]


def prepare():
    assert not OUT.exists(), 'Refusing to overwrite frozen experiment'
    assert sha(BASE / 'prepared.json') == PREPARED_SHA
    manifest = read(BASE / 'prepared.json')
    receipt = read(BASE / 'deployment.json')
    assert receipt['proof']['prepared_sha256'].upper() == PREPARED_SHA
    assert receipt['proof']['candidate_sha256'].upper() == FORMAL_RC
    assert manifest['candidate_sha256'].upper() == FORMAL_RC
    assert sha(BASE / 'RConnectMod.swf') == FORMAL_RC
    assert sha(GAME / 'mods/RConnect/release/RConnectMod.swf') == FORMAL_RC
    sources, inputs = manifest['source'], manifest['inputs']
    actual = {p.relative_to(BASE).as_posix() for p in (BASE / 'src').rglob('*.as')}
    assert len(sources) == 78 and set(sources) == actual
    assert len(inputs) == 71 and set(sources).isdisjoint(inputs)
    verify_files(BASE, {**sources, **inputs})
    tools = tool_inputs()  # Reads files only; no JVM or compiler starts here.
    prepared_edits = {name: modify(name, (BASE / name).read_bytes()) for name in CHANGED}
    OUT.mkdir(parents=True)
    for name in ('prepared.json', 'deployment.json'):
        shutil.copy2(BASE / name, OUT / name)
    before, after, diffs = {}, {}, []
    for name in sorted({**sources, **inputs}):
        original = (BASE / name).read_bytes()
        result = prepared_edits.get(name, original)
        for directory, data in (('baseline', original), ('candidate', result)):
            target = OUT / directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        before[name] = hashlib.sha256(original).hexdigest().upper()
        after[name] = hashlib.sha256(result).hexdigest().upper()
        if original != result:
            diffs.extend(difflib.unified_diff(original.decode('utf-8').splitlines(True),
                result.decode('utf-8').splitlines(True), fromfile='baseline/' + name, tofile='candidate/' + name))
    changed = {name for name in sources if before[name] != after[name]}
    assert changed == CHANGED
    (OUT / 'source.diff').write_text(''.join(diffs), encoding='utf-8')
    proof = dict(version='rc-offline-probe-1', diagnosticOnly=True, performanceAcceptance=False,
        productionSource=str(BASE), formalRC=FORMAL_RC, preparedSHA=PREPARED_SHA,
        receiptSHA=sha(OUT / 'deployment.json'), builderSHA=sha(__file__),
        before=before, after=after, sourceCount=78, changed=sorted(changed), unchangedSourceCount=75,
        buildInputCount=len(inputs), reverseByteReconstruction=True, tools=tools,
        gated=['mirror presentation/bodyEffects observations', 'final presentation/bodyEffects observations'],
        preserved=['wall', 'ports', 'invalidate', 'onPerceptionFrame', 'actual presentation', 'AI', 'local telekinesis'],
        carrier='RConnectOfflineProbeCarrier', api='rcOfflineProbeAPI',
        isolatedAppIDPrefix='pfe-modsettings-continuous-motion-', defaultEnabled=False,
        eligibility='enabled && !networkAttempted && mode === OFFLINE', networkAttemptReset=False,
        diffSHA=sha(OUT / 'source.diff'), compileCommand=compile_command(), compiled=False)
    save(OUT / 'source-provenance.json', proof)
    return check()


def check():
    proof = read(OUT / 'source-provenance.json')
    assert proof['builderSHA'] == sha(__file__)
    assert sha(OUT / 'prepared.json') == PREPARED_SHA
    assert proof['receiptSHA'] == sha(OUT / 'deployment.json')
    manifest = read(OUT / 'prepared.json')
    assert len(manifest['source']) == 78
    for directory, values in (('baseline', proof['before']), ('candidate', proof['after'])):
        verify_files(OUT / directory, values)
        actual = {p.relative_to(OUT / directory).as_posix() for p in (OUT / directory / 'src').rglob('*.as')}
        assert actual == set(manifest['source']), directory
        stubs = {p.relative_to(OUT / directory).as_posix() for p in (OUT / directory / 'tools/stubs').rglob('*.as')}
        assert stubs == set(manifest['inputs']) - {'tools/build_mod.py'}, directory
    verify_files(OUT / 'baseline', {**manifest['source'], **manifest['inputs']})
    changed = set()
    for name in manifest['source']:
        original = (OUT / 'baseline' / name).read_bytes()
        actual = (OUT / 'candidate' / name).read_bytes()
        assert modify(name, original) == actual, name
        if original != actual:
            changed.add(name)
    assert changed == CHANGED
    for name in manifest['inputs']:
        assert proof['before'][name] == proof['after'][name]
    assert sha(OUT / 'source.diff') == proof['diffSHA']
    for path, expected in proof['tools'].items():
        assert sha(path) == expected, path
    return dict(valid=True, changed=sorted(changed), unchanged=75, compiled=False,
                proofSHA=sha(OUT / 'source-provenance.json'), output=str(OUT))


def compile_candidate():
    check()
    target = OUT / 'RConnectMod.swf'
    assert not target.exists() and not (OUT / 'compile.json').exists(), 'Refusing to overwrite compiled evidence'
    sys.path.insert(0, str(GAME / 'mods/ModLoader/tools'))
    from test_registry import Registration
    with Registration(owner='ContinuousScene / RC offline presentation probe', resource='offline',
                      purpose='Compile frozen 574D-derived diagnostic only; no AIR or deployment',
                      run_dir=OUT, evidence=OUT / 'compile.json', wait=300) as record:
        with (OUT / 'compile.log').open('w', encoding='utf-8') as log:
            result = subprocess.run(compile_command(), cwd=OUT / 'candidate', stdout=log, stderr=subprocess.STDOUT)
        assert result.returncode == 0, 'RC probe compilation failed; see compile.log'
        check()
        save(OUT / 'compile.json', dict(candidateSHA=sha(target), bytes=target.stat().st_size,
             sourceProofSHA=sha(OUT / 'source-provenance.json'), builderSHA=sha(__file__),
             logSHA=sha(OUT / 'compile.log'), command=compile_command(),
             diagnosticOnly=True, performanceAcceptance=False, AIRLaunched=False, deployed=False))
        record.outcome = 'passed'
        record.note = 'Compilation and frozen-source checks only; no runtime/performance qualification'
    return read(OUT / 'compile.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', action='store_true')
    group.add_argument('--check', action='store_true')
    group.add_argument('--compile', action='store_true')
    args = parser.parse_args()
    print(json.dumps(prepare() if args.prepare else compile_candidate() if args.compile else check(),
                     ensure_ascii=False, indent=2))
