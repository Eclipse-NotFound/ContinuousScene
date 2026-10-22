"""Fail-closed, one-method BEFC Location.step diagnostic retention/audit.

The first import is inspection-only. Its actual activation/catch bytecode and
class layout must be reviewed before the explicit approval constants are set.
No JVM/AIR; never copies an imported class, constructor or unrelated method.
The shared Bullet/World audit files are not changed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B/'generated/location-step-profile-20261022'
CLASS = 'fe.loc.Location'
TARGET = CLASS + '::0:1:step'
BASE_XML_HASH = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
BASE_CODE_HASH = '775A6C5607A63E9FB3A10D2A84D13946EABA67D2C54CC878A36D6658141F2D9E'

# Reviewed from the actual compiled instruction stream, not source inference.
# The original import-review/provenance remain unchanged. Original locals move
# to slots 31/33/32 respectively; all accesses resolve by those same identities.
REVIEWED_IMPORT_XML_SHA = '93914AEFC040DFA79B4D67A2E107991093A529B7BEED2AE2ED126BE1B952C9D8'
REVIEWED_CODE_SHA = '854E3DEF1C6B4094B1BE455519AACD92DC6D8DC3EEF7A7EF8CC850944225E0B8'
REVIEWED_FRAME = dict(init_scope_depth='5', max_scope_depth='10', max_regs='4', max_stack='4')
REVIEWED_EXCEPTION = dict(type='ABCException', end='997', name_index='191', start='595', target='1001', type_index='0')
# One row per slot: explicitly reviewed setslot offsets, then getslot offsets.
_REVIEWED_SLOT_OFFSETS = [
    ('22', '1904'),
    ('29 219', '223 234'),
    ('36 244', '248 264 275'),
    ('43 288', '326 355 395 460 516 652 746 1016 1110 1201 1230 1423 1449 1503 1529 1569 1855 1914 1924 1934 1942 1950 1959 1968 1977 1986 1995 2004 2013 2022 2031 2040 2049 2058 2067 2076 2085 2094 2103 2112 2121 2130 2139 2148 2157 2166 2175 2184 2193 2202 2211 2220 2229 2238 2247 2256 2276 2280 2299 2310 2321 2325 2340 2344 2359 2363 2382 2393 2404 2408 2423 2427 2446 2457 2468 2472 2487 2491 2510 2521 2532 2536 2551 2555 2574 2585 2596 2600 2615 2619 2638 2649 2660 2664 2679 2683 2702 2713 2724 2728 2743 2747 2766 2777 2788 2792 2807 2811 2830 2841 2852 2856 2871 2875 2894 2905 2916 2920 2935 2939 2958 2969'),
    ('49 343 412 734 1218 1440 1520 1586', '377 482 764 1252 1471 1551 1877'),
    ('55 533', '1132'), ('61 768', '788 825 862 889'),
    ('67 663 680 701 722', '772 809 846'), ('73 1908', '2287 2295 2314'),
    ('79 1030', '1027 2332'), ('85 382', '366 2351 2378 2397'),
    ('91 391', '388 2370'), ('97 487', '471 2415 2442 2461'),
    ('103 496', '493 2434'), ('109 1137', '1121 2479 2506 2525'),
    ('115 1146', '1143 2498'), ('121 792', '784 2543 2570 2589'),
    ('127 801', '798 2562'), ('133 829', '821 2607 2634 2653'),
    ('139 838', '835 2626'), ('145 866', '858 2671 2698 2717'),
    ('151 875', '872 2690'), ('157 893', '885 2735 2762 2781'),
    ('163 902', '899 2754'), ('169 1257', '1241 2799 2826 2845'),
    ('175 1266', '1263 2818'), ('181 1476 1556', '1460 1540 2863 2890 2909'),
    ('187 1485 1565', '1482 1562 2882'), ('193 1882', '1866 2927 2954 2973'),
    ('199 1891', '1888 2946'), ('540 1073', '1070 1077'), ('456', '624 636'),
    ('295 550 1064', '587 606 613 640 667 688 709 738 906 919 938 966 989 1043 1102'),
]
REVIEWED_SLOT_RECEIVERS = {int(offset): (opcode, slot, 'activation')
    for slot, pair in enumerate(_REVIEWED_SLOT_OFFSETS, 1)
    for opcode, offsets in zip((0x6d, 0x6c), pair) for offset in offsets.split()}
REVIEWED_SLOT_RECEIVERS.update({1012: (0x6d, 1, 'catch'), 1039: (0x6c, 1, 'catch')})


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load('location_private_bullet_audit', B/'bullet-segments-audit.py')
recipe = load('location_profile_recipe', B/'location-step-profile.py')
engine.CLASS, engine.TARGET, engine.OUT = CLASS, TARGET, OUT
core, require = engine.core, engine.require
BASE_XML, BASE_SWF, BASE_HASH = engine.BASE_XML, engine.BASE_SWF, engine.BASE_HASH
_timer_binding = engine.timer_binding
NATIVE_LOCALS = [('numb', 0), ('obj', 27), ('sceneSleeping', 13)]
REVIEWED_ACTIVATION_ORDER = recipe.LOCAL_SCHEMA + [('numb', 0), ('sceneSleeping', 13), ('obj', 27)]


def slot_receiver_proof(abc, rows):
    """Prove receivers in this exact reviewed body; reject unknown effects.

    A branch-free reverse stack walk covers every slot except the one native
    sceneSleeping ternary. Its two paths are pinned below: both keep the same
    activation receiver underneath their one result. No permissive CFG merge.
    """
    executable = [r for r in rows if r[2] not in core.DEBUG]
    require([(r[2], r[3]) for r in executable[:6]] ==
            [(0xd0, []), (0x30, []), (0x57, []), (0x2a, []), (0xd5, []), (0x30, [])],
            'Activation is not the reviewed local1/scope1 object')
    require([(r[0], r[2], r[3]) for r in rows if 1001 <= r[0] <= 1012] == [
        (1001, 0xd0, []), (1002, 0x30, []), (1003, 0xd1, []), (1004, 0x30, []),
        (1005, 0x5a, [('u', 0)]), (1007, 0x2a, []), (1008, 0xd6, []),
        (1009, 0x2a, []), (1010, 0x30, []), (1011, 0x2b, []), (1012, 0x6d, [('u', 1)])],
        'Native catch scope reconstruction or err store changed')
    ternary = [
        (414, 0x65, [('b', 1)]), (416, 0x60, [('n', 48)]), (418, 0x66, [('n', 1316)]),
        (421, 0x66, [('n', 279)]), (424, 0x66, [('n', 8844)]), (427, 0x12, [('target', 453)]),
        (431, 0x60, [('n', 48)]), (433, 0x66, [('n', 1316)]), (436, 0x66, [('n', 279)]),
        (439, 0x2c, [('s', 7896)]), (442, 0xd0, []), (443, 0x56, [('u', 1)]),
        (445, 0x46, [('n', 9048), ('u', 2)]), (449, 0x10, [('target', 454)]),
        (453, 0x20, []), (454, 0x80, [('n', 13)]), (456, 0x6d, [('u', 32)])]
    require([(r[0], r[2], r[3]) for r in rows if 414 <= r[0] <= 456] == ternary,
            'Native sceneSleeping branch/receiver changed')
    require({r[0] for r in rows if r[2] == 0xd1} == {1003}, 'Activation local1 escapes catch restoration')
    require({r[0] for r in rows if r[2] == 0xd5} == {10}, 'Activation local1 is overwritten')
    consumed, proven = set(), {}

    def receiver(position, depth):
        for j in range(position - 1, -1, -1):
            row = rows[j]; op, args = row[2], row[3]
            if op in core.DEBUG:continue
            if op == 0x2a:
                depth = 1 if depth <= 2 else depth - 1
                continue
            if op == 0x2b:
                if depth <= 2:depth = 3 - depth
                continue
            if op in (0x65, 0x5a, 0x20, 0x24, 0x25, 0x26, 0x27, 0x2c, 0x5d, 0x60, 0xd0, 0xd1, 0xd2, 0xd3):
                pops, pushes = 0, 1
            elif op in (0x73, 0x76, 0x80, 0x82, 0x86, 0x91, 0xc0, 0xc1):pops, pushes = 1, 1
            elif op in (0xa0, 0xa1, 0x87):pops, pushes = 2, 1
            elif op in (0x66, 0x6c):pops, pushes = 1, 1
            elif op == 0x46:pops, pushes = int(args[1][1]) + 1, 1
            elif op in (0xd5, 0xd6, 0xd7, 0x30, 0x29):pops, pushes = 1, 0
            else:raise AssertionError('Unreviewed receiver expression at ' + str(row[0]) + ': ' + hex(op))
            if op in (0x5d, 0x60, 0x66, 0x46):
                kind = abc.cp['constant_multiname'][args[0][1]].get('kind')
                require(kind in ('7', '9', '13', '14') or op == 0x66 and kind == '27',
                        'Unreviewed late-name expression stack effect')
                if kind == '27':pops += 1
            if depth <= pushes:return row
            depth = depth - pushes + pops
        raise AssertionError('Slot receiver escaped reviewed expression')

    for i, row in enumerate(rows):
        if row[2] not in (0x6c, 0x6d):continue
        producer = next(r for r in rows if r[0] == 414) if row[0] == 456 else receiver(i, 1 if row[2] == 0x6c else 2)
        slot = row[3][0][1]
        if producer[2:] == (0x65, [('b', 1)]):
            consumed.add(producer[0]); owner = 'activation'
        elif row[0] == 1012 and producer[2:] == (0x5a, [('u', 0)]):owner = 'catch'
        elif row[0] == 1039 and producer[2:] == (0x65, [('b', 2)]):owner = 'catch'
        else:raise AssertionError('Slot receiver is neither reviewed activation nor native catch: ' + str(row[0]))
        proven[row[0]] = (row[2], slot, owner)
    require(proven == REVIEWED_SLOT_RECEIVERS, 'Slot receiver/identity differs from explicit reviewed offsets')
    require({r[0] for r in rows if r[2:] == (0x65, [('b', 1)])} == consumed,
            'Activation scope1 object escapes reviewed slot operations')
    return dict(numericSlotOperations=len(proven), activationObjectEscapes=False,
                activationScopeIndex=1, catchScopeIndex=2, nativeCatchReadOffset=1039,
                nativeCatchWriteOffset=1012, sceneSleepingTernaryReceiverOffset=414)


def code_sha(body):
    return hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()


def activation_proof(abc, index):
    body = abc.bodies[index]
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, abc, addresses)
    require(abc.names_by_method.get(index) == TARGET, 'Approval is only for Location.step')
    require(abc.methods[index].get('flags') == '2', 'Location.step activation flag changed')
    frame = {k: body.get(k) for k in ('init_scope_depth', 'max_scope_depth', 'max_regs', 'max_stack')}
    exceptions = list(body.find('exceptions'))
    require(len(exceptions) == 1 and exceptions[0].get('name_index') == '191'
            and exceptions[0].get('type_index') == '0' and abc.simple(191) == 'err',
            'Native catch name/type/count changed')
    traits = list(body.find('traits/traits'))
    actual = [(abc.simple(int(t.get('name_index'))), int(t.get('type_index'))) for t in traits]
    baseline = code_sha(body) == BASE_CODE_HASH
    receiver_evidence = None
    if baseline:
        require(index == 258 and len(bytes.fromhex(body.get('codeBytes'))) == 925, 'Wrong baseline target')
        require(frame == dict(init_scope_depth='5', max_scope_depth='10', max_regs='4', max_stack='4'),
                'Native Location.step invocation frame changed')
        require(actual == NATIVE_LOCALS, 'Native activation identities changed')
        require(exceptions[0].attrib == dict(type='ABCException', end='330', name_index='191',
                                           start='174', target='334', type_index='0'), 'Native catch range changed')
    else:
        require(REVIEWED_CODE_SHA is not None and REVIEWED_FRAME is not None
                and REVIEWED_ACTIVATION_ORDER is not None and REVIEWED_SLOT_RECEIVERS is not None,
                'Location imported activation/catch requires explicit post-compile review; use --inspect-import')
        require(code_sha(body) == REVIEWED_CODE_SHA, 'Target body differs from the reviewed import')
        require(frame == REVIEWED_FRAME, 'Reviewed invocation frame changed')
        require(exceptions[0].attrib == REVIEWED_EXCEPTION, 'Reviewed native catch range changed')
        require(actual == REVIEWED_ACTIVATION_ORDER, 'Reviewed activation ordering changed')
        require(len(actual) == 33 and len(set(name for name, _ in actual)) == 33
                and set(actual) == set(NATIVE_LOCALS + recipe.LOCAL_SCHEMA),
                'Original locals or the 30 diagnostic-only local identities changed')
        slot_ops = {r[0]: (r[2], int(r[3][0][1])) for r in rows if r[2] in (0x6c, 0x6d)}
        require(set(slot_ops) == set(REVIEWED_SLOT_RECEIVERS), 'Unreviewed numeric slot operation')
        catch_reads = catch_writes = 0
        for offset, (opcode, slot, owner) in REVIEWED_SLOT_RECEIVERS.items():
            require(slot_ops[offset] == (opcode, slot), 'Reviewed slot instruction changed')
            if owner == 'activation':require(1 <= slot <= 33, 'Invalid activation slot')
            elif owner == 'catch':
                require(slot == 1, 'Native catch slot changed')
                if opcode == 0x6c:catch_reads += 1
                else:catch_writes += 1
            else:raise AssertionError('Slot receiver has not been explicitly identified')
        require(catch_reads == catch_writes == 1, 'Native catch must have one err store and one err read')
        receiver_evidence = slot_receiver_proof(abc, rows)
    for slot, (trait, (name, type_index)) in enumerate(zip(traits, actual), 1):
        qname = int(trait.get('name_index'))
        require({k: v for k, v in trait.attrib.items() if k not in ('bytes', 'fileOffset')} ==
                dict(type='TraitSlotConst', deleted='false', kindFlags='0', kindType='0', name_index=str(qname),
                     slot_id=str(slot), type_index=str(type_index), value_index='0', value_kind='0'),
                'Activation slot flags/defaults changed: ' + name)
        require(abc.cp['constant_multiname'][qname].get('kind') == '7'
                and abc.cp['constant_multiname'][qname].get('namespace_index') == '43'
                and abc.cp['constant_namespace'][43].get('kind') == '23'
                and engine.namespace_name(abc, 43) == 'fe.loc', 'Activation local namespace changed')
        require(len(trait) == 1 and trait[0].tag == 'metadata' and not list(trait[0]), 'Unexpected local metadata')
    require(sum(r[2] == 0x57 for r in rows) == sum(r[2] == 0x5a for r in rows) == 1,
            'Unexpected activation or catch object count')
    require(not any(r[2] in (0x43, 0x6e, 0x6f) for r in rows), 'Unreviewed direct method/global slot access')
    return dict(originalLocals=NATIVE_LOCALS, diagnosticLocals=0 if baseline else 30,
                nativeCatch='one separate err:* catch object', codeSHA256=code_sha(body),
                slotReceivers='baseline exact bytes' if baseline else 'explicit per-offset review and reverse-stack proof',
                receiverEvidence=receiver_evidence)


def body_operands(abc, index):
    activation_proof(abc, index)
    rows, _ = core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    require(not any(kind in ('m', 'c') for row in rows for kind, _ in row[3]), 'New method/class-index operand')
    return {value for row in rows for kind, value in row[3] if kind == 'n'}


def timer_binding(abc, index):
    result = _timer_binding(abc, index)
    require(result['callCount'] == recipe.TIMER_CALLS, 'Unexpected Location timer call count')
    return result


def lexical_map(a, b, old_names, new_names):
    """Anchor blank private URIs by original private callable identities."""
    require(a.named[TARGET] == 258, 'Unexpected baseline method identity')
    old_sets, old_direct = engine.namespace_uses(a, old_names)
    require(old_sets == {163}, 'Original Location.step lexical set changed')
    original = engine.set_members(a, 163)
    require({n for n in original if engine.private(a, n)} == {44, 442}, 'Native private identities changed')
    require({n for n in old_direct if engine.private(a, n)} == {44}, 'Native direct private binding changed')
    anchors = {a.simple(n) for n in old_names if a.cp['constant_multiname'][n].get('namespace_index') == '44'}
    require(anchors and len(anchors) >= 3, 'Private callable anchors are missing')
    candidate_direct = {int(b.cp['constant_multiname'][n].get('namespace_index', '0'))
                        for n in new_names if b.simple(n) in anchors
                        and engine.private(b, int(b.cp['constant_multiname'][n].get('namespace_index', '0')))}
    require(len(candidate_direct) == 1, 'Imported class-private identity is ambiguous')
    class_private = next(iter(candidate_direct))
    for abc, ns in ((a, 44), (b, class_private)):
        traits = abc.instances[abc.class_by_name[CLASS]].find('instance_traits/traits')
        declared = {abc.simple(int(t.get('name_index'))) for t in traits
                    if t.get('type') == 'TraitMethodGetterSetter'
                    and abc.cp['constant_multiname'][int(t.get('name_index'))].get('namespace_index') == str(ns)}
        require(anchors <= declared, 'Private call is not bound to its original Location method')
    stable = {n for n in original if not engine.private(a, n)}
    new_sets, direct = engine.namespace_uses(b, new_names)
    mapping, evidence = {}, []
    for new_set in sorted(new_sets):
        members = engine.set_members(b, new_set)
        private_members = {n for n in members if engine.private(b, n)}
        if not private_members:continue
        require(len(members) == len(set(members)) and {n for n in members if not engine.private(b, n)} == stable,
                'Imported lexical non-private scope changed')
        require(class_private in private_members and len(private_members) == 2, 'Private file scope is ambiguous')
        pairs = ((class_private, 44), (next(iter(private_members - {class_private})), 442))
        for new, old in pairs:
            if new < len(a.cp['constant_namespace']):require(new == old, 'Cannot rebind existing private namespace')
            else:
                require(mapping.get(new, old) == old, 'Conflicting private mapping')
                mapping[new] = old
        require({mapping.get(n, n) for n in members} == set(original), 'Mapped lexical scope differs from original')
        evidence.append(dict(candidateSet=new_set, originalSet=163, anchors=sorted(anchors),
                             originalClassPrivate=44, originalFilePrivate=442))
    for ns in direct:
        if engine.private(b, ns):
            require(mapping.get(ns, ns) in (44, 442), 'Unbound direct private reference')
    return mapping, evidence


engine.body_operands = body_operands
engine.timer_binding = timer_binding
engine.lexical_map = lexical_map


def strict_audit(base_xml, candidate_xml, base_swf=BASE_SWF, candidate_swf=OUT/'pfe.swf'):
    paths = list(map(Path, (base_xml, candidate_xml, base_swf, candidate_swf)))
    require(engine.sha(paths[0]) == BASE_XML_HASH and engine.sha(paths[2]) == BASE_HASH, 'Not exact BEFC')
    require(engine.support.swf_envelope(paths[2]) == engine.support.swf_envelope(paths[3]), 'Non-ABC asset changed')
    old_nodes, new_nodes = ET.parse(paths[0]).findall('.//abc'), ET.parse(paths[1]).findall('.//abc')
    require(len(old_nodes) == len(new_nodes) and old_nodes, 'ABC count changed')
    ignored = {'bytes', 'fileOffset'}
    changed, hashes, pools, found, activation, timer = [], {}, [], 0, None, None
    counts = dict(unchangedMethodBodies=0, unchangedNamedMethods=0, unchangedClassLayouts=0,
                  unchangedScriptInitializers=0, unchangedUnnamedBodies=0, totalMethods=0)
    for number, (old, new) in enumerate(zip(old_nodes, new_nodes)):
        a, b = core.ABC(old), core.ABC(new)
        require(old.attrib == new.attrib and a.named == b.named and a.class_by_name == b.class_by_name,
                'ABC or named/class identity/index changed')
        require(len(a.methods) == len(b.methods) and set(a.cp) == set(b.cp), 'Method/pool table changed')
        for pool, entries in a.cp.items():
            require(len(b.cp[pool]) >= len(entries)
                    and all(core.xml_value(n) == core.xml_value(b.cp[pool][i]) for i, n in enumerate(entries)),
                    'Original constant prefix changed: ' + pool)
        pools.append({key: len(b.cp[key]) - len(value) for key, value in a.cp.items()})
        for index, (x, y) in enumerate(zip(a.methods, b.methods)):
            require(core.xml_value(x, ignored) == core.xml_value(y, ignored), 'Method metadata changed: ' + str(index))
        require(set(a.bodies) == set(b.bodies), 'Method body set changed')
        script_ids = {int(n.get('init_index')) for n in old.find('script_info')}
        for index, body in a.bodies.items():
            candidate = b.bodies[index]
            name = a.names_by_method.get(index)
            if name == TARGET:
                found += 1
                old_names, new_names = body_operands(a, index), body_operands(b, index)
                activation = activation_proof(b, index)
                require(activation['diagnosticLocals'] == 30, 'Missing reviewed diagnostic locals')
                timer = timer_binding(b, index)
                mapping, _ = lexical_map(a, b, old_names, new_names)
                require(not mapping, 'Final body retains a new private binding')
                if core.xml_value(body, ignored) != core.xml_value(candidate, ignored):changed.append(TARGET)
            else:
                require(core.xml_value(body, ignored) == core.xml_value(candidate, ignored),
                        (name or 'method-' + str(index)) + ': non-target body changed')
                hashes['abc-' + str(number) + '/method-' + str(index)] = code_sha(body)
                counts['unchangedMethodBodies'] += 1
                if index not in a.names_by_method and index not in script_ids:counts['unchangedUnnamedBodies'] += 1
        for table in ('instance_info', 'class_info', 'script_info'):
            require(core.xml_value(old.find(table), ignored) == core.xml_value(new.find(table), ignored),
                    table + ': original layout/binding changed')
        covered = {'constants', 'method_info', 'bodies', 'instance_info', 'class_info', 'script_info'}
        require([core.xml_value(n, ignored) for n in old if n.tag not in covered] ==
                [core.xml_value(n, ignored) for n in new if n.tag not in covered], 'Other ABC metadata changed')
        counts['unchangedNamedMethods'] += len(a.named) - int(TARGET in a.named)
        counts['unchangedClassLayouts'] += len(a.class_by_name)
        counts['unchangedScriptInitializers'] += len(list(old.find('script_info')))
        counts['totalMethods'] += len(a.methods)
    require(found == 1 and changed == [TARGET], 'Exactly Location.step must change')
    return dict(passed=True, auditTarget=TARGET, **counts, actualChangedBodies=changed,
                originalConstantPoolPreserved=True, appendedConstants=pools, nonABCSWFEnvelopePreserved=True,
                preservedOriginalLayout=True, constructorsPreserved=True, addedFields=[], addedMethods=[],
                timerBinding=timer, activationProof=activation, unchangedMethodBodySHA256=hashes,
                baseSHA256=engine.sha(paths[2]), candidateSHA256=engine.sha(paths[3]),
                baseXMLSHA256=engine.sha(paths[0]), candidateXMLSHA256=engine.sha(paths[1]))


engine.audit = strict_audit


def safe_output(path, suffix):
    path = Path(path)
    require(path.suffix == suffix and path.resolve().is_relative_to(OUT.resolve()), 'Output must stay in isolated generated directory')
    return path


def inspect_import(base_xml, candidate_xml):
    """Evidence only. A successful inspection never authorizes retention."""
    a = core.ABC(ET.parse(base_xml).findall('.//abc')[0])
    b = core.ABC(ET.parse(candidate_xml).findall('.//abc')[0])
    oi, ni = a.named[TARGET], b.named[TARGET]
    baseline = activation_proof(a, oi)
    body = b.bodies[ni]
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, b, addresses)
    slots = [dict(offset=r[0], opcode=r[2], slot=r[3][0][1]) for r in rows if r[2] in (0x6c, 0x6d)]
    compare = core.Compare(a, b)
    differences = []
    for part, x, y, child in [('instance', a.instances[a.class_by_name[CLASS]], b.instances[b.class_by_name[CLASS]], 'instance_traits/traits'),
                              ('static', a.statics[a.class_by_name[CLASS]], b.statics[b.class_by_name[CLASS]], 'static_traits/traits')]:
        old, new = list(x.find(child)), list(y.find(child))
        for i in range(max(len(old), len(new))):
            left, right = old[i] if i < len(old) else None, new[i] if i < len(new) else None
            if left is None or right is None or compare.trait(left, a) != compare.trait(right, b):
                differences.append(dict(part=part, row=i, original=None if left is None else left.attrib,
                                        imported=None if right is None else right.attrib,
                                        originalName=None if left is None else a.simple(int(left.get('name_index'))),
                                        importedName=None if right is None else b.simple(int(right.get('name_index')))))
    return dict(inspected=True, passed=False, runtimeReady=False, reviewRequired=True, target=TARGET,
                originalMethod=oi, importedMethod=ni, originalActivation=baseline,
                importedXMLSHA256=engine.sha(candidate_xml), importedCodeSHA256=code_sha(body),
                frame={k: v for k, v in body.attrib.items() if k != 'codeBytes'},
                activation=[dict(name=b.simple(int(t.get('name_index'))), **t.attrib) for t in body.find('traits/traits')],
                exceptions=[n.attrib for n in body.find('exceptions')], numericSlotOperations=slots,
                importedLayoutDifferences=differences,
                requiredReview=['original numb/obj/sceneSleeping slot identity and receiver preservation',
                    '30 new locals never escape; err catch remains a distinct object',
                    'qualified timer binding, lexical private callable identity, no new closures',
                    'imported class/constructor discarded; any layout drift must receive separate exact review'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base', type=Path, default=BASE_XML)
    p.add_argument('--candidate', type=Path, default=OUT/'compiled.xml')
    p.add_argument('--base-swf', type=Path, default=BASE_SWF)
    p.add_argument('--candidate-swf', type=Path, default=OUT/'pfe.swf')
    p.add_argument('--out', type=Path)
    actions = p.add_mutually_exclusive_group()
    actions.add_argument('--inspect-import', action='store_true')
    actions.add_argument('--retain', action='store_true')
    actions.add_argument('--splice-abc', action='store_true')
    args = p.parse_args()
    require(engine.sha(args.base) == BASE_XML_HASH, 'Requires exact BEFC XML')
    if args.inspect_import:
        result = inspect_import(args.base, args.candidate)
    elif args.retain:
        require(REVIEWED_IMPORT_XML_SHA is not None and engine.sha(args.candidate) == REVIEWED_IMPORT_XML_SHA,
                'Compiled import is not yet explicitly reviewed')
        require(args.out is not None, 'Retain requires output')
        result = engine.retain(args.base, args.candidate, safe_output(args.out, '.xml'))
        result.update(preservedOriginalLayout=True, importedClassCopied=False, importedConstructorsCopied=False,
            importedLayoutReview=dict(originalClassIndex=14, originalInstanceTraits=193, originalStaticTraits=0,
                privateNamespaceRelocations={'865':44, '864':442},
                strictLayoutCheckUnmodified=True, importedLayoutDriftException=False))
    elif args.splice_abc:
        require(args.out is not None, 'Splice requires output')
        result = engine.splice_abc(args.base, args.candidate, args.base_swf, args.candidate_swf, safe_output(args.out, '.swf'))
    else:
        result = strict_audit(args.base, args.candidate, args.base_swf, args.candidate_swf)
    result.update(diagnosticOnly=True, performanceEligible=False, wrapperSHA256=engine.sha(Path(__file__)))
    if args.out and not (args.retain or args.splice_abc):
        safe_output(args.out, '.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('unchangedMethodBodySHA256', 'numericSlotOperations', 'activation', 'importedLayoutDifferences')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
