"""Build isolated CS/TDFC activity candidates. Never launches AIR or deploys."""
from pathlib import Path
from xml.sax.saxutils import escape
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import traceback
import uuid
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


support = load('activity_candidate_support', HERE.parent/'stage-quality-native-20261025/run.py')
cs = load('activity_candidate_cs', HERE/'cs/prepare_cs_v3.py')
tdfc = load('activity_candidate_tdfc', HERE/'tdfc_transform_v2.py')
r, m, base = support.r, support.m, support.base
core = load('activity_candidate_abc', HERE.parents[1]/'native-crop-audit.py')
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()
tree = lambda path: {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
NATIVE = ('fe.Pt', 'fe.Obj', 'fe.unit.Unit', 'fe.unit.UnitRaider', 'fe.unit.UnitMerc',
          'fe.unit.UnitSlaver', 'fe.weapon.Weapon', 'fe.weapon.WThrow')
ACCESS = ('fe.unit.NativeSceneIdleAccess', 'fe.weapon.NativeSceneWeaponIdleAccess')
INTERNAL = {'fe.unit': {'aiState', 'aiSpok', 'aiAttack', 't_chCel'},
            'fe.weapon': {'is_attack', 'is_pattack', 't_ret', 'rotUp'}}

READ_RECORD = '''        public static function activityProbe(u:*):Object {
            if(!u)return null;
            var s:Object=rooms[u.loc];if(!s)return null;
            var r:Object=s.records[u];if(!r)return null;
            return {tick:s.tick,hp:r.hp,engaged:r.engaged,released:r.released,
                externalWake:r.externalWake,until:r.until,leaseUntil:r.leaseUntil,
                sleeping:Boolean(s.sleeping[u])};
        }
'''


def add_observer(folder):
    """Test artifact only; exposes immutable records across sibling mod domains."""
    edits = {
        'ContinuousSceneMod.as': [
            ('    import flash.utils.getTimer;\n',
             '    import flash.utils.getTimer;\n    import fe.unit.NativeSceneIdleAccess;\n    import fe.weapon.NativeSceneWeaponIdleAccess;\n'),
            ('activityLeaseVersion:NativeSceneActivity.activityLeaseVersion};',
             'activityLeaseVersion:NativeSceneActivity.activityLeaseVersion,\n                activityProbe:NativeSceneActivity.activityProbe,idleAccess:NativeSceneIdleAccess,weaponIdleAccess:NativeSceneWeaponIdleAccess};')],
        'NativeSceneActivity.as': [
            ('        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {',
             READ_RECORD+'        private static function freeze(parent:DisplayObjectContainer,clips:Array):void {')]
    }
    evidence = {}
    for name, pairs in edits.items():
        path=folder/name;before=path.read_text('utf-8');after=before
        for old,new in pairs:
            assert after.count(old)==1 and new not in after
            after=after.replace(old,new,1)
        reverse=after
        for old,new in reversed(pairs):reverse=reverse.replace(new,old,1)
        assert reverse==before
        evidence[name]=dict(beforeSHA256=sha(path),reverseExact=True,edits=pairs)
        path.write_text(after,'utf-8');evidence[name]['afterSHA256']=sha(path)
    return evidence


def inputs():
    outputs, proof = cs.artifacts()
    for path, data in outputs.items():
        assert path.read_bytes() == data, path
    pins, original = tdfc.inputs()
    tproof = r.read(HERE/'tdfc-source-proof-v2.json')
    assert tproof['baseSHA256'] == tdfc.BASE_SHA
    assert tproof['candidate'] == tree(HERE/'tdfc-candidate-v2') and len(tproof['candidate']) == 22
    for name, data in original.items():
        value = (HERE/'tdfc-candidate-v2'/name).read_bytes()
        if name in tdfc.CHANGED:
            assert tdfc.transform(name, tdfc.normalized(value), True) == tdfc.normalized(data)
        else:
            assert value == data
    assert len(tree(HERE/'access-v2')) == 2 and len(tree(HERE/'extern-v2')) == 8
    files = [Path(__file__), HERE/'tdfc_transform_v2.py', HERE/'tdfc-source-proof-v2.json',
             HERE/'cs/prepare_cs_v3.py', HERE/'cs/source-proof-v3.json', HERE.parents[1]/'native-crop-audit.py']
    files += [p for folder in ('cs/source-v3', 'access-v2', 'extern-v2', 'tdfc-candidate-v2')
              for p in (HERE/folder).rglob('*') if p.is_file()]
    return dict(support.runner_inputs(), **{str(p): sha(p) for p in files})


def audit(xml):
    classes, helpers, activations, internal_reads = set(), {}, {}, {name: set() for name in INTERNAL}
    for node in ET.parse(xml).findall('.//abc'):
        abc = core.ABC(node); classes.update(abc.class_by_name)
        for name, index in abc.named.items():
            owner = name.split('::')[0]
            if owner not in ACCESS or index not in abc.bodies: continue
            body = abc.bodies[index]
            rows, _ = core.decode(bytes.fromhex(body.get('codeBytes')))
            if name.endswith(':mayRest'):
                # ASC puts the wrapper's parameters/result in its NEWACTIVATION
                # and the caught value in NEWCATCH. These are not native slots.
                # Demand the complete known wrapper shape; inspect() below may
                # still use only QName field access on native objects.
                expected = (
                    'd0 30 57 2a d6 30 65 d1 6d 65 27 6d 65 5d 65 6c 46 76 6d 10 '
                    'd0 30 d2 30 5a 2a d7 2a 30 2b 6d 65 27 6d 1d 08 65 6c 48'
                    if owner == ACCESS[0] else
                    'd0 30 57 2a d7 30 65 d1 6d 65 d2 6d 65 27 6d 65 5d 65 6c 65 6c 46 76 6d 10 '
                    'd0 30 d3 30 5a 2a 63 2a 30 2b 6d 65 27 6d 1d 08 65 6c 48')
                assert [row[2] for row in rows] == [int(op, 16) for op in expected.split()], name
                for j, row in enumerate(rows):
                    if row[2] == 0x65: assert row[3] == [('b', 1)]
                    if row[2] == 0x6c: assert rows[j-1][2:] == (0x65, [('b', 1)])
                    if row[2] in (0x5d, 0x46): assert abc.simple(row[3][0][1]) == 'inspect'
                assert len(list(body.find('exceptions'))) == 1
                activations[name] = {'shapeVerified': True, 'nativeReadsAbsent': True,
                    'localSlotOperations': sum(row[2] in (0x6c, 0x6d) for row in rows)}
            else:
                assert not any(row[2] in (0x6c, 0x6d, 0x6e, 0x6f) for row in rows), name
            if name.endswith(':inspect') or name.endswith(':mayRest'):
                assert not any(row[2] in (0x61, 0x68, 0x05, 0x04) for row in rows), name
            for _, _, op, operands in rows:
                if op != 0x66: continue
                entry = abc.cp['constant_multiname'][operands[0][1]]
                if entry.get('kind') != '7': continue
                ns = abc.cp['constant_namespace'][int(entry.get('namespace_index'))]
                if int(ns.get('kind')) != 0x17: continue
                namespace = abc.string(int(ns.get('name_index')))
                field = abc.simple(operands[0][1])
                assert namespace in INTERNAL and field in INTERNAL[namespace], (name, namespace, field)
                internal_reads[namespace].add(field)
            helpers[name] = hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()
    assert not set(NATIVE) & classes, 'Native extern definitions leaked into candidate'
    assert {name for name in classes if name.startswith('fe.')} == set(ACCESS)
    assert internal_reads == INTERNAL, internal_reads
    assert len(activations) == 2
    return dict(passed=True, nativeDefinitionsAbsent=True, nativeFieldNumericSlotsAbsent=True,
                wrapperActivationSlots=activations,
                internalReads={k: sorted(v) for k, v in internal_reads.items()}, helperBodies=helpers,
                nativeRuntimeIdentityVerified=False, gameplayVerified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry-wait', type=int, default=600)
    parser.add_argument('--with-observer', action='store_true')
    args = parser.parse_args()
    folder = HERE/'candidate-builds'/uuid.uuid4().hex
    with m.Registration(owner='ContinuousScene / activity release build / 01a13816',
            purpose='Compile exact-source CS and TDFC candidates; no game',
            run_dir=folder, evidence=folder, resource='game', wait=args.registry_wait) as lease:
        record = dict(version='activity-release-build-1', gameStarted=False, deployed=False,observerOnly=args.with_observer,
                      performanceEligible=False)
        try:
            assert not m.air_pids(), 'Existing AIR remains untouched'
            support.control.memory_gate()
            baseline, source_inputs = r.baseline(), inputs()
            for key, value in support.old.PINS.items(): assert baseline[key] == value, key
            compiler = support.support.compiler_inputs()
            tools, java = r.enemy.TOOLS, r.enemy.JAVA
            for tool in (tools/'flexsdk/lib/compc.jar', tools/'ffdec/ffdec-cli.jar'):
                compiler[str(tool)] = sha(tool)
            folder.mkdir(parents=True, exist_ok=False)
            for original, destination in (('cs/source-v3', 'cs'), ('access-v2', 'cs'),
                                           ('extern-v2', 'extern'), ('tdfc-candidate-v2', 'tdfc')):
                shutil.copytree(HERE/original, folder/destination, dirs_exist_ok=True)
            if args.with_observer:record['observerTransforms']=add_observer(folder/'cs')
            frozen = {name: tree(folder/name) for name in ('cs', 'extern', 'tdfc')}
            assert len(frozen['cs']) == 8 and len(frozen['extern']) == 8 and len(frozen['tdfc']) == 22
            air, swc = tools/'airsdk/frameworks/libs/air/airglobal.swc', folder/'NativeActivityExtern.swc'
            commands = []
            for kind, externs in (('extern', [air]), ('cs', [air, swc]), ('tdfc', [air])):
                config = folder/(kind+'-config.xml')
                config.write_text('<flex-config><target-player>32.0</target-player><compiler>'
                    '<external-library-path>'+''.join('<path-element>'+escape(str(p))+'</path-element>' for p in externs)+
                    '</external-library-path><source-path><path-element>'+escape(str(folder/kind))+
                    '</path-element></source-path><debug>false</debug><optimize>true</optimize><theme/>'
                    '</compiler></flex-config>', 'utf-8')
                command = [str(java), '-Xmx512m', '-Dfile.encoding=UTF-8', '-jar',
                           str(tools/'flexsdk/lib'/('compc.jar' if kind == 'extern' else 'mxmlc.jar')),
                           '+flexlib='+str(tools/'flexsdk/frameworks'), '-load-config='+str(config), '-swf-version=32']
                if kind == 'extern': command += ['-include-classes='+','.join(NATIVE), '-output='+str(swc)]
                else:
                    name = 'ContinuousSceneMod' if kind == 'cs' else 'TDFCMod'
                    entry = 'ContinuousSceneDoc.as' if kind == 'cs' else 'TDFCMod.as'
                    command += ['-static-link-runtime-shared-libraries=true', '-output='+str(folder/(name+'.swf')),
                                str(folder/kind/entry)]
                commands.append(command)
            commands.append([str(java), '-Xmx512m', '-jar', str(tools/'ffdec/ffdec-cli.jar'),
                '-swf2xml', str(folder/'ContinuousSceneMod.swf'), str(folder/'candidate.xml')])
            record.update(productionSHA256=baseline, sourceInputs=source_inputs, compilerInputs=compiler,
                          frozenSourceSHA256=frozen, commands=commands)
            r.save(folder/'prepared.json', record)
            for index, command in enumerate(commands):
                assert not m.air_pids(), 'Other AIR appeared; untouched'
                process = None
                lease.before_launch('Activity candidate build '+str(index))
                try:
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    lease.child(process.pid)
                    log, _ = process.communicate(); (folder/('compile-'+str(index)+'.log')).write_bytes(log)
                    assert process.returncode == 0, 'Build failed; log retained in '+str(folder)
                finally:
                    if process is not None:
                        if process.poll() is None: process.kill(); process.wait(timeout=15)
                        lease.child_stopped()
            proof = audit(folder/'candidate.xml')
            assert inputs() == source_inputs and r.baseline() == baseline
            for path, digest in compiler.items(): assert sha(path) == digest
            assert {name: tree(folder/name) for name in frozen} == frozen
            record.update(compiled=True, bytecodeAudit=proof,
                artifacts={p.name: sha(p) for p in folder.iterdir() if p.is_file() and p.name != 'build.json'})
            r.save(folder/'build.json', record)
            lease.outcome='passed'; lease.note='Two isolated candidates compile; native access QName audit only; no game/deployment'
            print(json.dumps(dict(build=str(folder/'build.json'), compiled=True, audit=proof)), flush=True)
        except BaseException as error:
            folder.mkdir(parents=True, exist_ok=True)
            r.save(folder/'failure.json', dict(record, error=repr(error), traceback=traceback.format_exc()))
            lease.outcome='failed'; lease.note=repr(error); raise


if __name__ == '__main__': main()
