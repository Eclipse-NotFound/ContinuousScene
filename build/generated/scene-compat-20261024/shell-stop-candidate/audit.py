"""STATIC DRAFT: exact A796 Part.initVis plan; never writes XML or SWF.

Only --proof writes this directory's static-proof.json. No compiler, runtime,
class importer, constant rebinder, production installation, or timing claim.
The future serializer/envelope audit remains a separate reviewed step.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
B = HERE.parents[2]
BASE = HERE.parent / 'tint/product'
HOST = 'A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
XML = '1D2642C7D55D1F97121738E6AE84996A140EBFEFF686E6706C88CEF82A7338DA'
TARGET = 'fe.graph.Part::0:1:initVis'
METHOD = 963
OLD = bytes.fromhex(
    'd030d066c011120f00005ebb01d04ac0110068bb011001000047d1240014230000'
    '60bb0160f02460f02446cd250060bb0166c030a22401a046db0d014fac250110080000'
    '60bb01d14fac2501d066c1112400140b000060bb012661d22510380000d066c1112402'
    '1423000060bb0160f02460f02446cd250060bb0166c030a246db0d012401a04ffb3401'
    '100b000060bb01d12401a04ffb340160bb0160b60161cb1c60bb0160b70161cc1c'
    '60bb01d066c51161b12747')
FRAME = dict(type='MethodBody', init_scope_depth='5', max_regs='2',
             max_scope_depth='6', max_stack='4', method_info='963')
CP_STRING = 8161
CP_QNAME = 9705
POINTS = (60, 72)
Q = dict(World=48, w=1316, grafon=279, sceneLarge=8844, vClass=2240,
         isAnim=2241, vis=187, stop=4819, totalFrames=6208,
         currentFrame=7257, gotoAndStop=4780)

spec = importlib.util.spec_from_file_location('shell_stop_static_core', B / 'native-crop-audit.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def abcs(path):
    """Retain one ABC at a time, discard unrelated sprite/bitmap XML."""
    inside = False
    for event, node in ET.iterparse(path, events=('start', 'end')):
        if event == 'start' and node.tag == 'abc':
            inside = True
        elif event == 'end' and node.tag == 'abc':
            yield node
            inside = False
            node.clear()
        elif event == 'end' and not inside and node.tag == 'item':
            node.clear()


def u30(value):
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return out


def guard():
    """Entry [original receiver, original selected frame], exit same or []."""
    out = bytearray()
    branches = []
    labels = {}

    def emit(op, *args):
        out.append(op)
        for arg in args:
            out.extend(u30(arg))

    def branch(op, label):
        branches.append((len(out), label))
        out.extend(bytes([op, 0, 0, 0]))

    # Crucially this executes AFTER the original Math.random/floor expression.
    emit(0x2a); emit(0x24, 1); branch(0x1a, 'fallback')
    emit(0xd0); emit(0x66, Q['isAnim']); emit(0x24, 0); branch(0x1a, 'fallback')
    emit(0xd0); emit(0x66, Q['vClass']); emit(0x60, CP_QNAME); branch(0x1a, 'fallback')
    emit(0x60, Q['World']); emit(0x66, Q['w']); emit(0x2a); branch(0x12, 'drop')
    emit(0x66, Q['grafon']); emit(0x2a); branch(0x12, 'drop')
    emit(0x66, Q['sceneLarge']); emit(0x26); branch(0x1a, 'fallback')
    emit(0x60, Q['vis']); emit(0x66, Q['totalFrames']); emit(0x24, 1); branch(0x1a, 'fallback')
    emit(0x60, Q['vis']); emit(0x66, Q['currentFrame']); emit(0x24, 1); branch(0x1a, 'fallback')
    emit(0x29)  # Discard only the already evaluated original argument.
    emit(0x4f, Q['stop'], 0)  # Use the original receiver still on the stack.
    branch(0x10, 'continue')
    labels['drop'] = len(out)
    emit(0x29)  # Null World.w/grafon remains above the original two operands.
    branch(0x10, 'fallback')
    labels['fallback'] = len(out)  # Exact original gotoAndStop instruction.
    labels['continue'] = len(out) + 4  # Following original instruction.
    for start, label in branches:
        out[start + 1:start + 4] = (labels[label] - start - 4).to_bytes(3, 'little', signed=True)
    return bytes(out), labels


def candidate_code():
    prefix, labels = guard()
    rows, _ = core.decode(OLD)
    assert len(OLD) == 182
    assert all(OLD[p:p + 4] == bytes.fromhex('4fac2501') for p in POINTS)
    assert not any(v in POINTS for r in rows for k, v in r[3] if k == 'target')

    def old_address(offset):
        return offset + sum(len(prefix) for p in POINTS if p <= offset)

    result = bytearray()
    inserted = []
    for start, end, op, args in rows:
        if start in POINTS:
            inserted.append((len(result), len(result) + len(prefix)))
            result.extend(prefix)
        part = bytearray(OLD[start:end])
        destinations = [v for k, v in args if k == 'target']
        assert op != 0x1b
        if destinations:
            assert len(destinations) == 1 and end - start == 4
            part[1:4] = (old_address(destinations[0]) - old_address(start) - 4).to_bytes(3, 'little', signed=True)
        result.extend(part)
    actual, addresses = core.decode(bytes(result))
    survivors = [r for r in actual if not any(lo <= r[0] < hi for lo, hi in inserted)]
    assert len(survivors) == len(rows)
    for old, new in zip(rows, survivors):
        assert new[0] == old_address(old[0]) and new[2] == old[2]
        assert new[3] == [(k, old_address(v) if k == 'target' else v) for k, v in old[3]]
    assert all(v in addresses for r in actual for k, v in r[3] if k == 'target')
    return bytes(result), inserted


def stack_proof():
    """Exact guard CFG verifies stack4 suffices and both exits balance."""
    prefix, labels = guard()
    # Append native fallback call, allowing both terminal paths to be verified.
    rows, _ = core.decode(prefix + OLD[60:64])
    by = {r[0]: r for r in rows}
    queue = [(0, 2)]
    seen = {}
    peak = 2
    exits = []
    while queue:
        pc, depth = queue.pop()
        if pc == labels['continue']:
            exits.append(depth)
            assert depth == 0
            continue
        if pc in seen:
            assert seen[pc] == depth
            continue
        seen[pc] = depth
        start, end, op, args = by[pc]
        if op in (0x24, 0x26, 0x60, 0xd0): delta = 1
        elif op == 0x2a: delta = 1
        elif op in (0x29, 0x12): delta = -1
        elif op == 0x1a: delta = -2
        elif op in (0x66, 0x10): delta = 0
        elif op == 0x4f: delta = -1 - args[1][1]
        else: raise AssertionError(('Unreviewed guard opcode', op))
        depth += delta
        assert depth >= 0
        peak = max(peak, depth)
        target = [v for k, v in args if k == 'target']
        if target: queue.append((target[0], depth))
        if op != 0x10: queue.append((end, depth))
    assert peak == 4 and exits and seen[labels['fallback']] == 2
    return dict(peak=peak, fallbackStack=2, continuationStack=0,
                changedFrameAttributes=[], localsAdded=0, closuresAdded=0)


def facts():
    assert sha(BASE / 'pfe.xml') == XML
    receipt = json.loads((BASE / 'build.json').read_text(encoding='utf-8'))
    assert receipt['candidate'] == HOST and receipt['candidateXML'] == XML
    result = dict(version='shell-stop-static-1', target=TARGET, hostSHA256=HOST,
                  xmlSHA256=XML, hostHashSource='tint/product/build.json; XML rehashed here',
                  binaryReadByThisDraft=False, compiled=False, runtimeTested=False,
                  performanceEligible=False, deploymentEligible=False)
    definitions = []
    count = 0
    for index, node in enumerate(abcs(BASE / 'pfe.xml')):
        count += 1
        a = core.ABC(node)
        if index == 0:
            assert len(a.cp['constant_string']) == CP_STRING
            assert len(a.cp['constant_multiname']) == CP_QNAME
            assert not any((s.text or '') == 'visualGilza' for s in a.cp['constant_string'])
            assert not any(a.simple(i) == 'visualGilza' for i in range(CP_QNAME))
            ns = a.cp['constant_namespace'][1]
            assert ns.get('kind') == '22' and a.string(int(ns.get('name_index'))) == ''
            for name, idx in Q.items():
                mn = a.cp['constant_multiname'][idx]
                expected_ns = 'fe' if name == 'World' else ''
                n = a.cp['constant_namespace'][int(mn.get('namespace_index'))]
                assert mn.get('kind') == '7' and a.simple(idx) == name
                assert n.get('kind') == '22' and a.string(int(n.get('name_index'))) == expected_ns
            assert a.named[TARGET] == METHOD
            body = a.bodies[METHOD]
            assert bytes.fromhex(body.get('codeBytes')) == OLD
            assert {k: v for k, v in body.attrib.items() if k != 'codeBytes'} == FRAME
            assert not list(body.find('exceptions')) and not list(body.find('traits/traits'))
            result['originalBodySHA256'] = hashlib.sha256(OLD).hexdigest().upper()
            result['originalFrame'] = FRAME
            result['existingQNames'] = Q
        if 'visualGilza' in a.class_by_name:
            ci = a.class_by_name['visualGilza']
            inst, static = a.instances[ci], a.statics[ci]
            mi = int(inst.get('name_index'))
            mn = a.cp['constant_multiname'][mi]
            ns = a.cp['constant_namespace'][int(mn.get('namespace_index'))]
            assert index == 1 and mi == 731 and mn.get('kind') == '7'
            assert ns.get('kind') == '22' and a.string(int(ns.get('name_index'))) == ''
            bindings = []
            for si, script in enumerate(node.find('script_info')):
                for trait in script.find('traits/traits'):
                    if a.simple(int(trait.get('name_index'))) == 'visualGilza':
                        assert int(trait.get('name_index')) == mi and trait.get('type') == 'TraitClass'
                        assert int(trait.get('class_info')) == ci
                        bindings.append(dict(script=si, trait=dict(trait.attrib)))
            assert len(bindings) == 1
            definitions.append(dict(abc=index, classIndex=ci, instance=dict(inst.attrib),
                                    static=dict(static.attrib), binding=bindings[0],
                                    constructor=dict(a.bodies[int(inst.get('iinit_index'))].attrib),
                                    classInitializer=dict(a.bodies[int(static.get('cinit_index'))].attrib)))
    assert count == 2 and len(definitions) == 1
    code, ranges = candidate_code()
    result.update(classDefinition=definitions[0], appendOnlyPoolEntries=[
        dict(pool='constant_string', index=CP_STRING, value='visualGilza'),
        dict(pool='constant_multiname', index=CP_QNAME, kind=7,
             name_index=CP_STRING, namespace_index=1)],
        originalIndicesUnchanged=True, originalPoolEntriesUnchanged=True,
        candidateCodeBytes=code.hex(), candidateBodySHA256=hashlib.sha256(code).hexdigest().upper(),
        insertionRanges=ranges, originalInstructionsProjectedExactly=True,
        originalRandomExpressionsAndCallsPreserved=True, stack=stack_proof(),
        artifactBoundary='Static bytes in JSON only; no candidate XML or binary exists from this script',
        stillRequired=['actual runtime class-domain binding and component checks',
                       'global animation queue/event timing equivalence',
                       'strict all-other-ABC/body/class/initializer/non-ABC-envelope audit after serialization',
                       'real combat benefit without visual or gameplay regression'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--proof', action='store_true')
    args = parser.parse_args()
    proof = facts()
    if args.proof:
        proof['draftSHA256'] = sha(Path(__file__))
        (HERE / 'static-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: proof[k] for k in ('version', 'target', 'compiled', 'runtimeTested',
                                           'candidateBodySHA256', 'stack')}, ensure_ascii=False))
