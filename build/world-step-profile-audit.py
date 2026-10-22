"""Strict, isolated BEFC World.step retention/audit. Never starts JVM or AIR.

Uses a private instance of the existing Bullet audit. No shared audit file is
modified. Only the original World.step lexical scope may anchor fresh private
namespaces; class layouts and every other method body remain exact.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B / 'generated/world-step-profile-20261022'
CLASS = 'fe.World'
TARGET = CLASS + '::0:1:step'
EXPECTED_TIMER_CALLS = 22
spec = importlib.util.spec_from_file_location('world_step_private_audit', B/'bullet-segments-audit.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
engine.CLASS, engine.TARGET, engine.OUT = CLASS, TARGET, OUT
require = engine.require
BASE_XML, BASE_SWF, BASE_HASH = engine.BASE_XML, engine.BASE_SWF, engine.BASE_HASH
BASE_XML_HASH = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
IMPORTED_XML_HASH = 'BC64179FF4C570CD12F03498E7EFEED6FE3CE6632EF9EE5EA8B05C6C092E45D9'
_timer_binding = engine.timer_binding
_core = engine.core
_APPROVED_CODE = '2666D1E3B7623C998390D116116F6817D2FF7A349C86D3AEA0E08FC47D8FA8A9'
_LOCAL_SCHEMA = [('csWSWholeStart', 3), ('csWSCarrier', 13), ('csWSApi', 13),
                 ('csWSStats', 13), ('csWSPartStart', 3), ('csWSTotal', 3),
                 ('csWSFailed', 1), ('csWSEarly', 1)] + [
    ('csWS' + key + suffix, 3)
    for key in ('ctr', 'snd', 'land', 'satsStep2', 'inventory', 'cam', 'gui', 'pip', 'sats')
    for suffix in ('Ms', 'Calls')]


def activation_proof(abc, index):
    """Exact reviewed build: 26 new locals, separate unchanged catch object.

    This is deliberately not a general permission for activation traits. The
    body bytes, slot schema, scope producers and native catch binding are all
    checked. Original World.step has no activation fields to reorder.
    """
    require(abc.names_by_method.get(index) == TARGET, 'Activation approval is only for World.step')
    body = abc.bodies[index]
    rows, addresses = _core.decode(bytes.fromhex(body.get('codeBytes')))
    _core.Compare.exceptions(body, abc, addresses)
    traits = list(body.find('traits/traits'))
    require(abc.methods[index].get('flags') == '2', 'World.step activation flag changed')
    require({k: body.get(k) for k in ('init_scope_depth', 'max_scope_depth', 'max_regs', 'max_stack')}
            == dict(init_scope_depth='5', max_scope_depth='10', max_regs='4', max_stack='5'),
            'World.step invocation frame changed')
    exceptions = list(body.find('exceptions'))
    require(len(exceptions) == 1 and exceptions[0].get('name_index') == '191'
            and exceptions[0].get('type_index') == '0' and abc.simple(191) == 'err',
            'Original native catch identity/type changed')
    if not traits:
        require(index == 167 and len(bytes.fromhex(body.get('codeBytes'))) == 1075,
                'Only the exact baseline may have an empty activation')
        return dict(addedActivationLocals=0, nativeCatchSlot=1)
    require(hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper() == _APPROVED_CODE,
            'World.step bytes differ from the reviewed activation build')
    require(len(traits) == len(_LOCAL_SCHEMA), 'Unexpected activation trait count')
    for slot, (trait, (name, type_index)) in enumerate(zip(traits, _LOCAL_SCHEMA), 1):
        attrs = {k: v for k, v in trait.attrib.items() if k not in ('bytes', 'fileOffset')}
        qname = int(trait.get('name_index'))
        require(attrs == dict(type='TraitSlotConst', deleted='false', kindFlags='0', kindType='0',
                    name_index=str(qname), slot_id=str(slot), type_index=str(type_index), value_index='0', value_kind='0'),
                'Unexpected activation field flags/type/default/slot: ' + name)
        require(abc.simple(qname) == name and abc.cp['constant_multiname'][qname].get('kind') == '7'
                and abc.cp['constant_multiname'][qname].get('namespace_index') == '23'
                and abc.cp['constant_namespace'][23].get('kind') == '23'
                and engine.namespace_name(abc, 23) == 'fe', 'Activation local identity changed: ' + name)
        require(len(trait) == 1 and trait[0].tag == 'metadata' and not list(trait[0]),
                'Activation local has unexpected metadata')
    code = [row for row in rows if row[2] not in _core.DEBUG]
    prefix = [(r[2], r[3]) for r in code[:6]]
    require(prefix == [(0xd0, []), (0x30, []), (0x57, []), (0x2a, []), (0xd5, []), (0x30, [])],
            'Activation is not the original local1/local-scope1 object')
    require(sum(r[2] == 0x57 for r in rows) == 1 and sum(r[2] == 0x5a for r in rows) == 1,
            'Unexpected extra activation or catch object')
    require(not any(r[2] in (0x43, 0x6e, 0x6f) for r in rows), 'Unreviewed dispatch/global slot access')
    consumed = set()
    catch_reads = catch_writes = 0

    def receiver(position, depth):
        # Walk one expression backwards. Unknown effects or control flow are
        # rejected; only fixed-name operations emitted in this pinned build
        # are supported. This proves setslot's receiver, not merely its index.
        for j in range(position - 1, -1, -1):
            r = rows[j]; op, args = r[2], r[3]
            if op in _core.DEBUG:
                continue
            if op == 0x2a:
                depth = 1 if depth <= 2 else depth - 1
                continue
            if op == 0x2b:
                if depth <= 2: depth = 3 - depth
                continue
            if op in (0x65, 0x5a, 0x20, 0x24, 0x25, 0x26, 0x27, 0x2c, 0x5d, 0x60, 0xd0, 0xd1, 0xd2, 0xd3):
                pops, pushes = 0, 1
            elif op in (0x73, 0x76, 0x80, 0x86, 0xc0, 0xc1):
                pops, pushes = 1, 1
            elif op in (0xa0, 0xa1, 0x87):
                pops, pushes = 2, 1
            elif op in (0x66, 0x6c):
                pops, pushes = 1, 1
            elif op == 0x46:
                pops, pushes = int(args[1][1]) + 1, 1
            elif op in (0xd5, 0xd6, 0xd7, 0x30, 0x29):
                pops, pushes = 1, 0
            else:
                raise AssertionError('Unreviewed slot receiver expression opcode ' + hex(op) + ' at ' + str(r[0]))
            if op in (0x5d, 0x60, 0x66, 0x46):
                kind = abc.cp['constant_multiname'][args[0][1]].get('kind')
                require(kind in ('7', '9', '13', '14') or op == 0x66 and kind == '27',
                        'Unreviewed late-name stack effects')
                if kind == '27':pops += 1  # MultinameL consumes the literal bracket key.
            if depth <= pushes:
                return r
            depth = depth - pushes + pops
        raise AssertionError('Slot receiver escaped the reviewed expression')

    for i, row in enumerate(rows):
        if row[2] not in (0x6c, 0x6d):
            continue
        producer = receiver(i, 1 if row[2] == 0x6c else 2)
        slot = row[3][0][1]
        if producer[2] == 0x65 and producer[3] == [('b', 1)]:
            require(1 <= slot <= 26, 'Activation slot outside explicit csWS schema')
            consumed.add(producer[0])
        elif row[2] == 0x6c and producer[2] == 0x65 and producer[3] == [('b', 2)] and slot == 1:
            catch_reads += 1
        elif row[2] == 0x6d and producer[2] == 0x5a and producer[3] == [('u', 0)] and slot == 1:
            catch_writes += 1
        else:
            raise AssertionError('Slot receiver is neither the reviewed activation nor native catch object')
    require(catch_reads == catch_writes == 1, 'Native err slot binding changed')
    require({r[0] for r in rows if r[2] == 0x65 and r[3] == [('b', 1)]} == consumed,
            'Activation object escapes the reviewed slot operations')
    return dict(addedActivationLocals=26, nativeCatchSlot=1, nativeCatchReadCount=catch_reads,
                nativeCatchWriteCount=catch_writes, activationScopeIndex=1, catchScopeIndex=2,
                activationObjectEscapes=False, approvedBodySHA256=_APPROVED_CODE,
                localSchema=[dict(slot=i, name=n, typeIndex=t) for i, (n, t) in enumerate(_LOCAL_SCHEMA, 1)])


def world_body_operands(abc, index):
    activation_proof(abc, index)
    rows, _ = _core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    require(not any(k in ('m', 'c') for row in rows for k, value in row[3]),
            'Target method/class-index operand needs separate relocation review')
    return {value for row in rows for kind, value in row[3] if kind == 'n'}


engine.body_operands = world_body_operands


def world_timer_binding(abc, index):
    result = _timer_binding(abc, index)
    require(result['callCount'] == EXPECTED_TIMER_CALLS,
            'World.step must contain exactly the reviewed 22 qualified timer calls')
    return result


def world_lexical_map(a, b, old_names, new_names):
    """Match only the exact BEFC step scope, never another World method."""
    require(a.named[TARGET] == 167, 'Unexpected baseline World.step method index')
    old_sets, _ = engine.namespace_uses(a, old_names)
    require(old_sets == {175}, 'Baseline World.step lexical scope changed')
    original = engine.set_members(a, 175)
    require({i for i in original if engine.private(a, i)} == {856, 857},
            'Baseline World.step private identities changed')
    require(engine.namespace_name(a, 856) == 'fe:World'
            and engine.namespace_name(a, 857) == 'World.as$12',
            'World class/file private namespace anchors changed')
    stable = {i for i in original if not engine.private(a, i)}
    new_sets, direct = engine.namespace_uses(b, new_names)
    old_count = len(a.cp['constant_namespace'])
    mapping, evidence = {}, []
    for new_index in sorted(new_sets):
        members = engine.set_members(b, new_index)
        require(len(members) == len(set(members)), 'Duplicate namespace in imported World scope')
        fresh = {i for i in members if i >= old_count}
        if not fresh:
            if any(engine.private(b, i) for i in members):
                require(set(members) == set(original), 'Existing private scope is not the original World.step scope')
            continue
        require(all(engine.private(b, i) for i in fresh), 'New non-private World scope is unsupported')
        require({i for i in members if not engine.private(b, i)} == stable,
                'Imported World scope does not match the original step scope')
        private_members = {i for i in members if engine.private(b, i)}
        class_private = {i for i in private_members if engine.namespace_name(b, i) == 'fe:World'}
        require(len(class_private) == 1 and len(private_members - class_private) == 1,
                'Imported World private scope is ambiguous')
        pairs = [(next(iter(class_private)), 856), (next(iter(private_members - class_private)), 857)]
        for ni, oi in pairs:
            if ni < old_count:
                require(ni == oi, 'Cannot rebind an existing World namespace index')
            else:
                require(mapping.get(ni, oi) == oi, 'Conflicting World private mapping')
                mapping[ni] = oi
        require({mapping.get(i, i) for i in members} == set(original),
                'Mapped World lexical scope differs from original step')
        evidence.append(dict(candidateSet=new_index, originalStepSet=175,
                             candidateMembers=members, originalMembers=original))
    for index in direct:
        if index >= old_count and engine.private(b, index):
            require(index in mapping, 'Fresh direct World private reference lacks exact step-scope proof')
        elif engine.private(b, index):
            require(index in (856, 857), 'Direct private reference belongs to a different World scope')
    return mapping, evidence


engine.lexical_map = world_lexical_map
engine.timer_binding = world_timer_binding


def rejected_imported_layout(a, b):
    """Review this fixed import's drift, never declare its layouts equivalent.

    FFDec moved four existing fields across ten methods and changed the
    wildcard actionDist default from a double to an int. Neither imported
    class nor its constructors are eligible for retention. The target body
    uses named class properties; every numeric slot receiver is separately
    proved to be its activation or original catch object.
    """
    ai, bi = a.class_by_name[CLASS], b.class_by_name[CLASS]
    require(ai == bi == 12, 'World class identity/index drift')
    ignored = {'iinit_index', 'cinit_index', 'bytes', 'fileOffset'}
    compare = _core.Compare(a, b)
    instance_a, instance_b = a.instances[ai], b.instances[bi]
    static_a, static_b = a.statics[ai], b.statics[bi]
    for part, old, new in [('instance', instance_a, instance_b), ('static', static_a, static_b)]:
        require(engine.support.header(old, ignored) == engine.support.header(new, ignored),
                'World class header changed: ' + part)
        omitted = 'instance_traits' if part == 'instance' else 'static_traits'
        require([_core.xml_value(n, ignored) for n in old if n.tag != omitted] ==
                [_core.xml_value(n, ignored) for n in new if n.tag != omitted],
                'World interfaces/metadata changed: ' + part)
    x = list(instance_a.find('instance_traits/traits'))
    y = list(instance_b.find('instance_traits/traits'))
    require(len(x) == len(y) == 190, 'Reviewed World instance trait count changed')
    identity = lambda t: (t.get('type'), t.get('kindType'), t.get('name_index'))
    keys_x, keys_y = [identity(t) for t in x], [identity(t) for t in y]
    require(len(set(keys_x)) == len(set(keys_y)) == 190 and set(keys_x) == set(keys_y),
            'Reviewed World trait identities changed')
    for kind, count in [('TraitSlotConst', 151), ('TraitMethodGetterSetter', 39)]:
        old_order = [identity(t) for t in x if t.get('type') == kind]
        new_order = [identity(t) for t in y if t.get('type') == kind]
        require(len(old_order) == len(new_order) == count and old_order == new_order,
                'World field/method relative order changed: ' + kind)
    moved_fields = ['ng', 'data', 'opt', 'newName']
    crossed_methods = ['onCompleteLoadLang', 'onErrorLoadLang', 'initLangs', 'textsLoadOk',
                       'defuxLang', 'init2', 'roomsLoadOk', 'onDeactivate', 'resizeScreen', 'consolOnOff']
    require([a.simple(int(t.get('name_index'))) for t in x[147:157]] == crossed_methods
            and [a.simple(int(t.get('name_index'))) for t in x[157:161]] == moved_fields,
            'Original World mixed trait sequence differs from the reviewed baseline')
    require(keys_y == keys_x[:147] + keys_x[157:161] + keys_x[147:157] + keys_x[161:],
            'Imported World trait permutation differs from the reviewed drift')
    by_key = {identity(t): t for t in y}
    for row, old in enumerate(x):
        new = by_key[identity(old)]
        if row != 99:
            require(compare.trait(old, a) == compare.trait(new, b),
                    'Unreviewed imported World trait change: ' + a.simple(int(old.get('name_index'))))
            continue
        attrs = dict(type='TraitSlotConst', deleted='false', kindFlags='0', kindType='0',
                     name_index='357', slot_id='0', type_index='0')
        require(a.simple(357) == b.simple(357) == 'actionDist', 'Reviewed default owner changed')
        require({k: v for k, v in old.attrib.items() if k not in ('bytes', 'fileOffset')} ==
                dict(attrs, value_index='5', value_kind='6'), 'Original actionDist default changed')
        require({k: v for k, v in new.attrib.items() if k not in ('bytes', 'fileOffset')} ==
                dict(attrs, value_index='126', value_kind='3'), 'Imported actionDist default drift changed')
        require((a.cp['constant_double'][5].text or '').strip() == '40000.0'
                and (b.cp['constant_int'][126].text or '').strip() == '40000',
                'Reviewed actionDist constants changed')
        require([_core.xml_value(n) for n in old] == [_core.xml_value(n) for n in new],
                'actionDist metadata changed')
    sx, sy = list(static_a.find('static_traits/traits')), list(static_b.find('static_traits/traits'))
    require(len(sx) == len(sy) == 16 and all(compare.trait(t, a) == compare.trait(u, b) for t, u in zip(sx, sy)),
            'World static trait layout changed')
    target_names = world_body_operands(b, b.named[TARGET])
    require(not {'actionDist', *moved_fields}.intersection(b.simple(n) for n in target_names),
            'Target body refers to reviewed discarded drift')
    return dict(rejected=True, importedClassCopied=False, importedConstructorsCopied=False,
                instanceTraits=190, fields=151, methods=39, staticTraits=16,
                traitIdentitiesPreserved=True, fieldRelativeOrderPreserved=True, methodRelativeOrderPreserved=True,
                defaultDrift=dict(name='actionDist', type='*', originalKind='double', originalValue='40000.0',
                                  importedKind='int', importedValue='40000', consideredEquivalent=False),
                exactPermutation=dict(fields=moved_fields, originalRows=[157, 158, 159, 160],
                                      importedRows=[147, 148, 149, 150], crossedMethods=crossed_methods),
                targetUsesDiscardedDrift=False, targetNumericSlots='activation and original catch only')


def retained_original_layout(a):
    index = a.class_by_name[CLASS]
    return dict(preserved=True, className=CLASS, classIndex=index,
                originalInstanceInitializer=int(a.instances[index].get('iinit_index')),
                originalStaticInitializer=int(a.statics[index].get('cinit_index')),
                allInstanceClassAndScriptTables='exact original BEFC', constructors='exact original BEFC',
                onlyCopiedBody=TARGET)


def retain_world(base_xml, candidate_xml, output_xml):
    """Copy one reviewed body into BEFC; discard the entire imported layout."""
    base_xml, candidate_xml, output_xml = map(Path, (base_xml, candidate_xml, output_xml))
    require(engine.sha(candidate_xml) == IMPORTED_XML_HASH, 'Only the reviewed compiled World XML is accepted')
    require(output_xml.resolve() not in (base_xml.resolve(), candidate_xml.resolve()), 'Use a separate retained XML')
    before, imported = ET.parse(base_xml), ET.parse(candidate_xml)
    old_nodes, new_nodes = before.findall('.//abc'), imported.findall('.//abc')
    require(len(old_nodes) == len(new_nodes) and old_nodes, 'ABC count changed or missing')
    copied, scopes, timer, rejected, preserved = [], [], None, None, None
    ignored = {'bytes', 'fileOffset'}
    for number, (old_node, new_node) in enumerate(zip(old_nodes, new_nodes)):
        a, b = _core.ABC(old_node), _core.ABC(new_node)
        if TARGET not in a.named:
            require(_core.xml_value(old_node, ignored) == _core.xml_value(new_node, ignored), 'Unrelated ABC changed')
            continue
        require(old_node.attrib == new_node.attrib, 'ABC header changed')
        require(set(a.named) == set(b.named), 'Named method set changed')
        require(set(a.class_by_name) == set(b.class_by_name), 'Class set changed')
        require(len(a.methods) == len(b.methods), 'Method table count changed')
        require(set(a.cp) == set(b.cp), 'Constant pool kind changed')
        for pool, entries in a.cp.items():
            require(len(b.cp[pool]) >= len(entries), 'Constant pool shortened: ' + pool)
            require(all(_core.xml_value(v) == _core.xml_value(b.cp[pool][i]) for i, v in enumerate(entries)),
                    'Constant prefix changed: ' + pool)
        oi, ni = a.named[TARGET], b.named[TARGET]
        require(a.signature(oi) == b.signature(ni), 'World.step signature changed')
        require(a.bodies[oi].get('init_scope_depth') == b.bodies[ni].get('init_scope_depth'), 'Captured scope depth changed')
        old_names, new_names = world_body_operands(a, oi), world_body_operands(b, ni)
        timer = world_timer_binding(b, ni)
        ns_map, evidence = world_lexical_map(a, b, old_names, new_names)
        require(ns_map == {}, 'This reviewed import must reuse the original World private identities')
        rejected = rejected_imported_layout(a, b)
        preserved = retained_original_layout(a)
        original_tables = {key: _core.xml_value(old_node.find(key), ignored)
                           for key in ('instance_info', 'class_info', 'script_info', 'method_info')}
        replacement = copy.deepcopy(b.bodies[ni]); replacement.set('method_info', str(oi))
        bodies = old_node.find('bodies'); index = list(bodies).index(a.bodies[oi])
        bodies.remove(a.bodies[oi]); bodies.insert(index, replacement)
        original_constants = old_node.find('constants'); index = list(old_node).index(original_constants)
        old_node.remove(original_constants); old_node.insert(index, copy.deepcopy(new_node.find('constants')))
        require(all(_core.xml_value(old_node.find(key), ignored) == value for key, value in original_tables.items()),
                'Retain changed an original class/script/method table')
        require(all(_core.xml_value(body, ignored) == _core.xml_value(a.bodies[int(body.get('method_info'))], ignored)
                    for body in bodies if int(body.get('method_info')) != oi), 'Retain changed a non-target body')
        copied.append(dict(abc=number, method=TARGET, importedIndex=ni, originalIndex=oi))
        scopes.append(dict(abc=number, privateNamespaces=ns_map, originalStepScopeEvidence=evidence))
    require(len(copied) == 1 and rejected and preserved, 'Expected exactly one World.step body')
    before.write(output_xml, encoding='utf-8', xml_declaration=True)
    return dict(stagedXML=True, outputXML=str(output_xml), outputXMLSHA256=engine.sha(output_xml),
                baseXMLSHA256=engine.sha(base_xml), importedXMLSHA256=engine.sha(candidate_xml),
                copiedBodies=copied, namespaceMappings=scopes, timerBinding=timer,
                rejectedImportedLayout=rejected, preservedOriginalLayout=preserved,
                nextStep='Serialize and splice only the retained ABC, then audit every original class and constructor strictly.')


def strict_world_audit(base_xml, candidate_xml, base_swf=BASE_SWF, candidate_swf=OUT/'pfe.swf'):
    """Same retention gates as Bullet; only target activation delta is explicit.

    No XML comparator is weakened or monkey-patched. The target-local schema
    replaces only Bullet's empty-traits equality check; all other gates remain.
    """
    paths = list(map(Path, (base_xml, candidate_xml, base_swf, candidate_swf)))
    require(engine.sha(paths[0]) == BASE_XML_HASH and engine.sha(paths[2]) == BASE_HASH, 'Baseline is not exact BEFC')
    require(engine.support.swf_envelope(paths[2]) == engine.support.swf_envelope(paths[3]), 'Non-ABC SWF asset changed')
    old_nodes, new_nodes = ET.parse(paths[0]).findall('.//abc'), ET.parse(paths[1]).findall('.//abc')
    require(len(old_nodes) == len(new_nodes) and old_nodes, 'ABC count changed')
    counts = dict(unchangedNamedMethods=0, unchangedClassLayouts=0, unchangedScriptInitializers=0,
                  unchangedUnnamedBodies=0, unchangedMethodBodies=0, totalMethods=0)
    changed, hashes, pools, found, timer, activation, preserved = [], {}, [], 0, None, None, None
    ignored = {'bytes', 'fileOffset'}
    for number, (old, new) in enumerate(zip(old_nodes, new_nodes)):
        a, b = _core.ABC(old), _core.ABC(new)
        require(old.attrib == new.attrib, 'ABC header changed')
        require(a.named == b.named, 'Named method identity/index changed')
        require(a.class_by_name == b.class_by_name, 'Class identity/index changed')
        require(len(a.methods) == len(b.methods), 'Method table size changed')
        require(set(a.cp) == set(b.cp), 'Constant pool kind changed')
        for pool, entries in a.cp.items():
            require(len(b.cp[pool]) >= len(entries), 'Constant pool shortened: ' + pool)
            require(all(_core.xml_value(v) == _core.xml_value(b.cp[pool][i]) for i, v in enumerate(entries)),
                    'Constant prefix changed: ' + pool)
        pools.append({pool: len(b.cp[pool]) - len(a.cp[pool]) for pool in a.cp})
        for index, (x, y) in enumerate(zip(a.methods, b.methods)):
            require(_core.xml_value(x, ignored) == _core.xml_value(y, ignored), 'Method metadata/signature changed: ' + str(index))
        require(set(a.bodies) == set(b.bodies), 'Method body set changed')
        script_ids = {int(n.get('init_index')) for n in old.find('script_info')}
        for index, body in a.bodies.items():
            candidate = b.bodies[index]
            name = a.names_by_method.get(index)
            if name == TARGET:
                found += 1
                preserved = retained_original_layout(a)
                require(body.get('init_scope_depth') == candidate.get('init_scope_depth'), 'Captured scope depth changed')
                world_body_operands(a, index)
                new_names = world_body_operands(b, index)
                timer = world_timer_binding(b, index)
                used_sets, direct = engine.namespace_uses(b, new_names)
                used = direct | {v for nsset in used_sets for v in engine.set_members(b, nsset)}
                require(not any(ns >= len(a.cp['constant_namespace']) and engine.private(b, ns) for ns in used),
                        'New World private namespace was not rebound')
                world_lexical_map(a, b, world_body_operands(a, index), new_names)
                require(not list(body.find('traits/traits')), 'Baseline activation must have no fields')
                activation = activation_proof(b, index)
                require(activation['addedActivationLocals'] == 26, 'Missing explicit diagnostic local schema')
                if _core.xml_value(body, ignored) != _core.xml_value(candidate, ignored):changed.append(TARGET)
            else:
                require(_core.xml_value(body, ignored) == _core.xml_value(candidate, ignored),
                        (name or 'method-' + str(index)) + ': non-target body/metadata changed')
                hashes['abc-' + str(number) + '/method-' + str(index)] = hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()
                counts['unchangedMethodBodies'] += 1
                if index not in a.names_by_method and index not in script_ids:counts['unchangedUnnamedBodies'] += 1
        for container in ('instance_info', 'class_info', 'script_info'):
            require(_core.xml_value(old.find(container), ignored) == _core.xml_value(new.find(container), ignored),
                    container + ': layout/binding changed')
        covered = {'constants', 'method_info', 'bodies', 'instance_info', 'class_info', 'script_info'}
        require([_core.xml_value(n, ignored) for n in old if n.tag not in covered] ==
                [_core.xml_value(n, ignored) for n in new if n.tag not in covered], 'Other ABC metadata changed')
        counts['unchangedNamedMethods'] += len(a.named) - int(TARGET in a.named)
        counts['unchangedClassLayouts'] += len(a.class_by_name)
        counts['unchangedScriptInitializers'] += len(list(old.find('script_info')))
        counts['totalMethods'] += len(a.methods)
    require(found == 1 and changed == [TARGET], 'Exactly one World.step body must change')
    return dict(passed=True, auditTarget=TARGET, **counts, allowedChangedMethods=[TARGET], actualChangedBodies=changed,
                timerBinding=timer, activationProof=activation, methodAndClassIndicesPreserved=True,
                preservedOriginalLayout=preserved,
                addedFields=[], addedMethods=[], originalConstantPoolPreserved=True, appendedConstants=pools,
                nonABCSWFEnvelopePreserved=True, unchangedMethodBodySHA256=hashes,
                baseXML=str(paths[0]), candidateXML=str(paths[1]), baseSWF=str(paths[2]), candidateSWF=str(paths[3]),
                baseXMLSHA256=engine.sha(paths[0]), candidateXMLSHA256=engine.sha(paths[1]),
                baseSHA256=engine.sha(paths[2]), candidateSHA256=engine.sha(paths[3]),
                auditImplementationSHA256=engine.sha(Path(__file__)),
                auditSupportSHA256=engine.sha(B/'stationary-threat-audit.py'),
                semanticComparatorSHA256=engine.sha(B/'native-crop-audit.py'),
                xmlProvenance='Existing exports; build receipt binds exact XML and SWF files')


# splice_abc calls this private module's audit for donor preflight. The shared
# audit file and all its other module instances remain unchanged.
engine.audit = strict_world_audit


def output_path(path, suffix):
    path = Path(path)
    require(path.suffix.lower() == suffix and path.resolve().is_relative_to(OUT.resolve()),
            'Output must remain in generated/world-step-profile-20261022 with suffix ' + suffix)
    return path


def baseline_xml(path):
    path = Path(path)
    require(engine.sha(path) == BASE_XML_HASH, 'World audit requires the exact BEFC XML')
    return path


def label(result):
    result.update(auditTarget=TARGET, diagnosticOnly=True, performanceEligible=False,
                  wrapperSHA256=engine.sha(Path(__file__)),
                  sharedAuditSHA256=engine.sha(B/'bullet-segments-audit.py'),
                  privateMappingPolicy='Only original World.step scope 175, class 856 and file 857',
                  importedClassLayoutNormalization=False)
    return result


def retain(base_xml, candidate_xml, output_xml):
    result = label(retain_world(baseline_xml(base_xml), Path(candidate_xml), output_path(output_xml, '.xml')))
    receipt = output_path(Path(output_xml).with_suffix('.audit.json'), '.json')
    result['retentionAuditPath'] = str(receipt)
    receipt.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    return result


def splice_abc(base_xml, candidate_xml, base_swf, candidate_swf, output_swf):
    return label(engine.splice_abc(baseline_xml(base_xml), Path(candidate_xml), Path(base_swf),
                                  Path(candidate_swf), output_path(output_swf, '.swf')))


def audit(base_xml, candidate_xml, base_swf=BASE_SWF, candidate_swf=OUT/'pfe.swf'):
    result = engine.audit(baseline_xml(base_xml), Path(candidate_xml), Path(base_swf), Path(candidate_swf))
    require(result['actualChangedBodies'] == [TARGET], 'Exactly World.step must change')
    return label(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=BASE_XML)
    parser.add_argument('--candidate', type=Path, default=OUT/'compiled.xml')
    parser.add_argument('--base-swf', type=Path, default=BASE_SWF)
    parser.add_argument('--candidate-swf', type=Path, default=OUT/'pfe.swf')
    parser.add_argument('--out', type=Path)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--retain', '--retain-unchanged-bodies', dest='retain', action='store_true')
    actions.add_argument('--splice-abc', dest='splice', action='store_true')
    args = parser.parse_args()
    report = None
    try:
        if args.retain:
            require(args.out is not None, 'Retain requires --out XML')
            result = retain(args.base, args.candidate, args.out)
        elif args.splice:
            require(args.out is not None, 'Splice requires --out SWF')
            result = splice_abc(args.base, args.candidate, args.base_swf, args.candidate_swf, args.out)
        else:
            if args.out:
                report = output_path(args.out, '.json')
                require(report.resolve() not in {p.resolve() for p in (args.base, args.candidate, args.base_swf, args.candidate_swf)},
                        'Audit report must not overwrite an input')
            result = audit(args.base, args.candidate, args.base_swf, args.candidate_swf)
    except Exception as error:
        result = dict(passed=False, auditTarget=TARGET, error=type(error).__name__ + ': ' + str(error))
        if report:
            report.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(1)
    if report:
        report.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'unchangedMethodBodySHA256'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
