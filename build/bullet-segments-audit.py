"""Offline retain/audit for a BEFC Bullet.run timing-only candidate.

Never starts JVM/AIR. Retain copies one body onto the baseline XML skeleton.
Splice writes only an isolated diagnostic SWF, preserving original raw assets.
Audit checks frozen method/class identities and the actual non-ABC envelope.
Existing pool slots stay unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zlib

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B / 'generated/bullet-segments-20261021'
BASE_XML = B / 'generated/fog-typed/pfe.xml'
BASE_SWF = B / 'generated/fog-typed/pfe.swf'
BASE_HASH = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
CLASS = 'fe.weapon.Bullet'
TARGET = CLASS + '::0:1:run'

spec = importlib.util.spec_from_file_location('bullet_segments_audit_support', B / 'stationary-threat-audit.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)
core, require, sha = support.core, support.require, support.sha


def body_operands(abc, index):
    body = abc.bodies.get(index)
    require(body is not None, 'Missing target body')
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, abc, addresses)
    require(not list(body.find('traits/traits')), 'Target activation traits require explicit review')
    require(not any(k in ('m', 'c') for row in rows for k, value in row[3]),
            'Target method/class-index operand requires explicit relocation')
    return {value for row in rows for kind, value in row[3] if kind == 'n'}


def timer_binding(abc, index):
    """Require real package-function calls, not FFDec's flash.utils chain."""
    rows, _ = core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    rows = [row for row in rows if row[2] not in core.DEBUG]
    calls = []
    for i, row in enumerate(rows):
        names = [value for kind, value in row[3] if kind == 'n']
        for value in names:
            name = abc.simple(value)
            if name == 'flash' and row[2] in (0x5d, 0x5e, 0x60):
                raise AssertionError('Bullet.run timer binding uses a global flash property chain')
            if name != 'getTimer':continue
            mn = abc.cp['constant_multiname'][value]
            ns = int(mn.get('namespace_index', '0'))
            require(mn.get('kind') == '7' and abc.cp['constant_namespace'][ns].get('kind') == '22'
                    and namespace_name(abc, ns) == 'flash.utils',
                    'Bullet.run getTimer is not QName flash.utils::getTimer')
            if row[2] == 0x5d:
                require(i + 1 < len(rows), 'Unpaired getTimer function lookup')
                following = rows[i + 1]
                require(following[2] == 0x46 and len(following[3]) == 2 and following[3][1] == ('u', 0)
                        and following[3][0][0] == 'n' and abc.multiname(following[3][0][1]) == abc.multiname(value),
                        'getTimer lookup is not followed by its direct zero-argument call')
            elif row[2] == 0x46:
                require(i > 0 and row[3] == [('n', value), ('u', 0)], 'Unexpected getTimer call arguments')
                previous = rows[i - 1]
                require(previous[2] == 0x5d and len(previous[3]) == 1 and previous[3][0][0] == 'n'
                        and abc.multiname(previous[3][0][1]) == abc.multiname(value),
                        'getTimer receiver is not the directly resolved package function')
                calls.append(row[0])
            else:
                raise AssertionError('Unexpected getTimer reference opcode: ' + hex(row[2]))
    require(calls, 'No qualified getTimer timing calls found in diagnostic Bullet.run')
    return dict(qualifiedName='flash.utils::getTimer', callCount=len(calls), callOffsets=calls,
                allCallsDirectQualified=True, globalFlashPropertyChain=False)


def namespace_uses(abc, multinames):
    sets, direct, visited = set(), set(), set()
    def visit(index):
        if index in visited:return
        visited.add(index)
        node = abc.cp['constant_multiname'][index]
        ns, nsset = int(node.get('namespace_index', '0')), int(node.get('namespace_set_index', '0'))
        if ns:direct.add(ns)
        if nsset:sets.add(nsset)
        if node.get('kind') == '29':
            visit(int(node.get('qname_index')))
            for child in node.find('params'):visit(int(child.text))
    for index in multinames:visit(index)
    return sets, direct


def set_members(abc, index):
    return [int(n.text) for n in abc.cp['constant_namespace_set'][index].findall('namespaces/item')]


def private(abc, index):
    return abc.cp['constant_namespace'][index].get('kind') == '5'


def namespace_name(abc, index):
    return abc.string(int(abc.cp['constant_namespace'][index].get('name_index', '0')))


def lexical_map(a, b, old_names, new_names):
    """Infer only from exact original run scopes, never all-pool name guesses."""
    old_sets, _ = namespace_uses(a, old_names)
    new_sets, direct = namespace_uses(b, new_names)
    mapping, evidence = {}, []
    old_count = len(a.cp['constant_namespace'])
    for new_index in sorted(new_sets):
        members = set_members(b, new_index)
        require(len(members) == len(set(members)), 'Duplicate namespace in candidate scope')
        fresh = {i for i in members if i >= old_count}
        if not fresh:continue
        require(all(private(b, i) for i in fresh), 'New non-private namespace changes original run scope')
        stable = {i for i in members if not private(b, i)}
        matches = []
        for old_index in old_sets:
            old = set_members(a, old_index)
            if {i for i in old if not private(a, i)} == stable:
                matches.append((old_index, old))
        require(len(matches) == 1, 'Candidate scope does not uniquely match an original Bullet.run namespace set')
        old_index, old_members = matches[0]
        old_private = {i for i in old_members if private(a, i)}
        new_private = {i for i in members if private(b, i)}
        old_class = {i for i in old_private if namespace_name(a, i) == 'fe.weapon:Bullet'}
        new_class = {i for i in new_private if namespace_name(b, i) == 'fe.weapon:Bullet'}
        require(len(old_class) == len(new_class) == 1, 'Class-private identity is not uniquely anchored by its exact URI')
        pairs = [(next(iter(new_class)), next(iter(old_class)))]
        old_file, new_file = old_private - old_class, new_private - new_class
        require(len(old_file) == len(new_file) == 1, 'Lexical private namespace has multiple possible mappings')
        pairs.append((next(iter(new_file)), next(iter(old_file))))
        for ni, oi in pairs:
            if ni < old_count:
                require(ni == oi, 'Cannot rebind an existing namespace index')
            else:
                require(mapping.get(ni, oi) == oi, 'Conflicting scope-derived private namespace mapping')
                mapping[ni] = oi
        require({mapping.get(i, i) for i in members} == set(old_members), 'Mapped lexical scope differs from original')
        evidence.append(dict(candidateSet=new_index, originalRunSet=old_index,
                             candidateMembers=members, originalMembers=old_members,
                             matchedNonPrivateNamespaces=sorted(stable)))
    for index in direct:
        if index >= old_count and private(b, index):
            require(index in mapping, 'Direct new private reference has no unique original-run scope mapping')
    return mapping, evidence


def retain(base_xml, candidate_xml, output_xml):
    base_xml, candidate_xml, output_xml = map(Path, (base_xml, candidate_xml, output_xml))
    require(output_xml.suffix.lower() == '.xml', 'Retain output must be XML')
    require(output_xml.resolve() not in (base_xml.resolve(), candidate_xml.resolve()), 'Use a separate retained XML output')
    before, imported = ET.parse(base_xml), ET.parse(candidate_xml)
    old_nodes, new_nodes = before.findall('.//abc'), imported.findall('.//abc')
    require(len(old_nodes) == len(new_nodes) and old_nodes, 'ABC count changed or missing')
    copied, scopes, timer = [], [], None
    for number, (old_node, new_node) in enumerate(zip(old_nodes, new_nodes)):
        a, b = core.ABC(old_node), core.ABC(new_node)
        if TARGET not in a.named:
            # FFDec's absolute fileOffset annotations move when the preceding
            # ABC grows; bytes annotations duplicate decoded trait fields.
            # Neither annotation is executable content. The output keeps this
            # entire original ABC node, not the imported copy.
            require(core.xml_value(old_node, {'bytes', 'fileOffset'}) ==
                    core.xml_value(new_node, {'bytes', 'fileOffset'}), 'Unrelated ABC changed')
            continue
        require(old_node.attrib == new_node.attrib, 'ABC header changed')
        require(set(a.named) == set(b.named), 'Named method set changed')
        require(set(a.class_by_name) == set(b.class_by_name), 'Class set changed')
        require(len(a.methods) == len(b.methods), 'Method table count changed')
        require(set(a.cp) == set(b.cp), 'Constant pool kind changed')
        for pool, entries in a.cp.items():
            require(len(b.cp[pool]) >= len(entries), 'Constant pool shortened: ' + pool)
            require(all(core.xml_value(v) == core.xml_value(b.cp[pool][i]) for i, v in enumerate(entries)), 'Constant prefix changed: ' + pool)
        oi, ni = a.named[TARGET], b.named[TARGET]
        require(a.signature(oi) == b.signature(ni), 'Bullet.run signature changed')
        require(a.bodies[oi].get('init_scope_depth') == b.bodies[ni].get('init_scope_depth'), 'Bullet.run captured scope depth changed')
        old_names, new_names = body_operands(a, oi), body_operands(b, ni)
        timer = timer_binding(b, ni)
        ns_map, evidence = lexical_map(a, b, old_names, new_names)
        constants = copy.deepcopy(new_node.find('constants'))
        for entry in list(constants.find('constant_multiname'))[len(a.cp['constant_multiname']):]:
            value = int(entry.get('namespace_index', '0'))
            if value in ns_map:entry.set('namespace_index', str(ns_map[value]))
        for entry in list(constants.find('constant_namespace_set'))[len(a.cp['constant_namespace_set']):]:
            for item in entry.findall('namespaces/item'):
                value = int(item.text)
                if value in ns_map:item.text = str(ns_map[value])
        # Verify all target class field and method layouts before discarding
        # the imported class. Original baseline headers/traits remain output.
        normalized_node = copy.deepcopy(new_node)
        normalized_node.remove(normalized_node.find('constants'));normalized_node.insert(0, copy.deepcopy(constants))
        normalized = core.ABC(normalized_node);compare = core.Compare(a, normalized)
        ai, bi = a.class_by_name[CLASS], normalized.class_by_name[CLASS]
        for part, old, new in [('instance', a.instances[ai], normalized.instances[bi]), ('static', a.statics[ai], normalized.statics[bi])]:
            ignored = {'iinit_index', 'cinit_index', 'bytes', 'fileOffset'}
            require(support.header(old, ignored) == support.header(new, ignored), 'Bullet class header changed')
            container = 'instance_traits/traits' if part == 'instance' else 'static_traits/traits'
            x, y = old.find(container), new.find(container)
            require(len(x) == len(y), 'Bullet trait count changed')
            require(all(compare.trait(t, a) == compare.trait(u, normalized) for t, u in zip(x, y)), 'Bullet layout changed')
            omitted = 'instance_traits' if part == 'instance' else 'static_traits'
            require([core.xml_value(n, ignored) for n in old if n.tag != omitted] ==
                    [core.xml_value(n, ignored) for n in new if n.tag != omitted], 'Bullet interfaces/metadata changed')
        replacement = copy.deepcopy(b.bodies[ni]);replacement.set('method_info', str(oi))
        bodies = old_node.find('bodies');index = list(bodies).index(a.bodies[oi])
        bodies.remove(a.bodies[oi]);bodies.insert(index, replacement)
        original_constants = old_node.find('constants');index = list(old_node).index(original_constants)
        old_node.remove(original_constants);old_node.insert(index, constants)
        copied.append(dict(abc=number, method=TARGET, importedIndex=ni, originalIndex=oi))
        scopes.append(dict(abc=number, privateNamespaces=ns_map, originalRunScopeEvidence=evidence))
    require(len(copied) == 1, 'Expected exactly one Bullet.run body')
    before.write(output_xml, encoding='utf-8', xml_declaration=True)
    return dict(stagedXML=True, outputXML=str(output_xml), outputXMLSHA256=sha(output_xml),
                baseXMLSHA256=sha(base_xml), importedXMLSHA256=sha(candidate_xml), copiedBodies=copied,
                namespaceMappings=scopes, timerBinding=timer, bytecodeOperandsUnchanged=True,
                nextStep='Generate SWF, export it again, then run strict audit against the original BEFC XML/SWF.')


def audit(base_xml, candidate_xml, base_swf=BASE_SWF, candidate_swf=OUT/'pfe.swf'):
    paths = list(map(Path, (base_xml, candidate_xml, base_swf, candidate_swf)))
    require(sha(paths[2]) == BASE_HASH, 'Baseline host SWF is not BEFC')
    require(support.swf_envelope(paths[2]) == support.swf_envelope(paths[3]), 'Non-ABC SWF header/tag/asset changed')
    old_nodes = ET.parse(paths[0]).findall('.//abc')
    new_nodes = ET.parse(paths[1]).findall('.//abc')
    require(len(old_nodes) == len(new_nodes) and old_nodes, 'ABC count changed or missing')
    counts = dict(unchangedNamedMethods=0, unchangedClassLayouts=0, unchangedScriptInitializers=0,
                  unchangedUnnamedBodies=0, unchangedMethodBodies=0, totalMethods=0)
    changed, hashes, pools, found, timer = [], {}, [], 0, None
    ignored = {'bytes', 'fileOffset'}
    for number, (old, new) in enumerate(zip(old_nodes, new_nodes)):
        a, b = core.ABC(old), core.ABC(new)
        require(old.attrib == new.attrib, 'ABC header changed')
        require(a.named == b.named, 'Named method identity/index changed')
        require(a.class_by_name == b.class_by_name, 'Class identity/index changed')
        require(len(a.methods) == len(b.methods), 'Method table size changed')
        require(set(a.cp) == set(b.cp), 'Constant pool kind changed')
        for pool, entries in a.cp.items():
            require(len(b.cp[pool]) >= len(entries), 'Constant pool shortened: ' + pool)
            require(all(core.xml_value(v) == core.xml_value(b.cp[pool][i]) for i, v in enumerate(entries)), 'Constant prefix changed: ' + pool)
        pools.append({pool: len(b.cp[pool]) - len(a.cp[pool]) for pool in a.cp})
        for index, (x, y) in enumerate(zip(a.methods, b.methods)):
            require(core.xml_value(x, ignored) == core.xml_value(y, ignored), 'Method metadata/signature changed at ' + str(index))
        # All indices and the old constant-pool prefix are frozen. Identical
        # bytes therefore retain identical targets, including every anonymous
        # and orphan body. Do not decode untouched legacy code: BEFC already
        # contains unreachable out-of-range branches (Location.insKontur).
        require(set(a.bodies) == set(b.bodies), 'Method body set changed')
        script_ids = {int(n.get('init_index')) for n in old.find('script_info')}
        for index, body in a.bodies.items():
            candidate = b.bodies[index]
            name = a.names_by_method.get(index)
            if name == TARGET:
                found += 1
                require(body.get('init_scope_depth') == candidate.get('init_scope_depth'), 'Bullet.run captured scope depth changed')
                body_operands(a, index);new_names = body_operands(b, index)
                timer = timer_binding(b, index)
                used_sets, direct = namespace_uses(b, new_names)
                used_namespaces = direct | {v for nsset in used_sets for v in set_members(b, nsset)}
                require(not any(ns >= len(a.cp['constant_namespace']) and private(b, ns) for ns in used_namespaces),
                        'New Bullet.run private namespace was not rebound to an original identity')
                require(core.xml_value(body.find('traits'), ignored) == core.xml_value(candidate.find('traits'), ignored), 'Target activation traits changed')
                if core.xml_value(body, ignored) != core.xml_value(candidate, ignored):changed.append(TARGET)
            else:
                require(core.xml_value(body, ignored) == core.xml_value(candidate, ignored),
                        (name or 'method-' + str(index)) + ': unchanged body/metadata differs')
                hashes['abc-' + str(number) + '/method-' + str(index)] = hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()
                counts['unchangedMethodBodies'] += 1
                if index not in a.names_by_method and index not in script_ids:counts['unchangedUnnamedBodies'] += 1
        for container in ('instance_info', 'class_info', 'script_info'):
            require(core.xml_value(old.find(container), ignored) == core.xml_value(new.find(container), ignored), container + ': layout/binding changed')
        covered = {'constants', 'method_info', 'bodies', 'instance_info', 'class_info', 'script_info'}
        require([core.xml_value(n, ignored) for n in old if n.tag not in covered] ==
                [core.xml_value(n, ignored) for n in new if n.tag not in covered], 'Other ABC metadata changed')
        counts['unchangedNamedMethods'] += len(a.named) - int(TARGET in a.named)
        counts['unchangedClassLayouts'] += len(a.class_by_name)
        counts['unchangedScriptInitializers'] += len(list(old.find('script_info')))
        counts['totalMethods'] += len(a.methods)
    require(found == 1, 'Expected exactly one Bullet.run body')
    return dict(passed=True, auditTarget=TARGET, **counts, allowedChangedMethods=[TARGET], actualChangedBodies=changed, timerBinding=timer,
                methodAndClassIndicesPreserved=True, addedFields=[], addedMethods=[], originalConstantPoolPreserved=True,
                appendedConstants=pools, nonABCSWFEnvelopePreserved=True, unchangedMethodBodySHA256=hashes,
                baseXML=str(paths[0]), candidateXML=str(paths[1]), baseSWF=str(paths[2]), candidateSWF=str(paths[3]),
                baseXMLSHA256=sha(paths[0]), candidateXMLSHA256=sha(paths[1]), baseSHA256=sha(paths[2]), candidateSHA256=sha(paths[3]),
                auditImplementationSHA256=sha(Path(__file__)), auditSupportSHA256=sha(B/'stationary-threat-audit.py'),
                semanticComparatorSHA256=sha(B/'native-crop-audit.py'),
                xmlProvenance='Existing FFDec exports; build must bind these XML hashes to the recorded SWF inputs.')


def raw_swf(path):
    """Keep every original tag header and payload, not decoded/re-encoded art."""
    raw = Path(path).read_bytes()
    require(len(raw) >= 12 and raw[:3] in (b'FWS', b'CWS'), 'Unsupported SWF signature')
    body = zlib.decompress(raw[8:]) if raw[:3] == b'CWS' else raw[8:]
    require(len(body) + 8 == int.from_bytes(raw[4:8], 'little'), 'Invalid expanded SWF length')
    cursor = (5 + 4 * (body[0] >> 3) + 7) // 8 + 4
    require(cursor <= len(body), 'Truncated frame header')
    frame_header, tags, ended = body[:cursor], [], False
    while cursor < len(body):
        start = cursor
        require(cursor + 2 <= len(body), 'Truncated tag header')
        record = int.from_bytes(body[cursor:cursor + 2], 'little');cursor += 2
        kind, length = record >> 6, record & 63
        if length == 63:
            require(cursor + 4 <= len(body), 'Truncated long tag header')
            length = int.from_bytes(body[cursor:cursor + 4], 'little');cursor += 4
        require(cursor + length <= len(body), 'Truncated tag payload')
        payload = body[cursor:cursor + length];cursor += length
        tags.append((kind, payload, body[start:cursor]))
        if kind == 0:
            require(cursor == len(body), 'Unexpected bytes after SWF End tag')
            ended = True;break
    require(ended, 'Missing SWF End tag')
    return raw[:4], frame_header, tags


def abc_prefix(tag):
    kind, payload, _ = tag
    require(kind in (72, 82), 'Expected an ABC tag')
    if kind == 72:return b''
    require(len(payload) >= 5 and b'\0' in payload[4:], 'Invalid DoABC flags/name')
    return payload[:payload.index(b'\0', 4) + 1]


def splice_abc(base_xml, candidate_xml, base_swf, candidate_swf, output_swf):
    """Use one audited donor ABC; preserve every other baseline raw tag."""
    base_xml, candidate_xml, base_swf, candidate_swf, output_swf = map(Path,
        (base_xml, candidate_xml, base_swf, candidate_swf, output_swf))
    require(output_swf.suffix.lower() == '.swf' and output_swf.resolve().is_relative_to(OUT.resolve()),
            'Splice output must be a diagnostic SWF inside this candidate directory')
    require(output_swf.resolve() not in {base_swf.resolve(), candidate_swf.resolve()}, 'Splice must not overwrite either input SWF')
    require(sha(base_swf) == BASE_HASH, 'Splice baseline host is not BEFC')
    # This is deliberately an XML-only preflight. Using the baseline twice
    # checks its own envelope; it does not approve the donor's rewritten art.
    # The final generated SWF must subsequently be exported and audited.
    preflight = audit(base_xml, candidate_xml, base_swf, base_swf)
    require(preflight['actualChangedBodies'] == [TARGET], 'Donor XML must change exactly Bullet.run')
    old_nodes, donor_nodes = ET.parse(base_xml).findall('.//abc'), ET.parse(candidate_xml).findall('.//abc')
    target_indices = [i for i, node in enumerate(old_nodes) if TARGET in core.ABC(node).named]
    require(len(target_indices) == 1, 'Ambiguous target ABC')
    target_abc = target_indices[0]
    require(target_abc == 0 and len(old_nodes) == 2, 'This diagnostic supports only the pinned BEFC target ABC 0 of 2')
    require(TARGET in core.ABC(donor_nodes[target_abc]).named, 'Donor target ABC order changed')
    signature, header, old = raw_swf(base_swf)
    donor_signature, donor_header, donor = raw_swf(candidate_swf)
    require(signature[3:] == donor_signature[3:] and header == donor_header, 'Donor SWF version/frame header changed')
    require(len(old) == len(donor) and all(a[0] == b[0] for a, b in zip(old, donor)), 'Donor tag count/order changed')
    old_abc = [i for i, tag in enumerate(old) if tag[0] in (72, 82)]
    require(len(old_abc) == len(old_nodes) == len(donor_nodes), 'XML/top-level binary ABC counts disagree')
    for index in old_abc:
        require(abc_prefix(old[index]) == abc_prefix(donor[index]), 'DoABC flags/name changed')
    target_tag = old_abc[target_abc]
    require(old[target_tag][1] != donor[target_tag][1], 'Donor ABC has no byte changes')
    raw_tags = [new[2] if index == target_tag else original[2]
                for index, (original, new) in enumerate(zip(old, donor))]
    body = header + b''.join(raw_tags)
    output_swf.write_bytes(signature + (len(body) + 8).to_bytes(4, 'little') +
                           (zlib.compress(body, 9) if signature[:3] == b'CWS' else body))
    final_signature, final_header, final = raw_swf(output_swf)
    require(final_signature == signature and final_header == header and len(final) == len(old), 'Spliced header/tag count mismatch')
    require(all(final[i][2] == (donor[i][2] if i == target_tag else old[i][2]) for i in range(len(old))),
            'Spliced raw tag differs from its designated source')
    require(support.swf_envelope(base_swf) == support.swf_envelope(output_swf), 'Spliced non-ABC envelope failed strict comparison')
    changed_art = Counter(a[0] for a, b in zip(old, donor) if a[0] not in (72, 82) and a[1] != b[1])
    return dict(spliced=True, outputSWF=str(output_swf), outputSHA256=sha(output_swf),
                baseSHA256=sha(base_swf), donorSHA256=sha(candidate_swf), donorXMLSHA256=sha(candidate_xml),
                targetABCIndex=target_abc, targetTagIndex=target_tag,
                preservedRawTags=len(old)-1, preservedNonABCTags=len(old)-len(old_abc), preservedOtherABCTags=len(old_abc)-1,
                discardedDonorAssetChangeCount=sum(changed_art.values()), discardedDonorAssetChangesByTag=dict(changed_art),
                nonABCSWFEnvelopePreserved=True, xmlPreflightOnly=True,
                nextStep='Export this spliced SWF to a fresh XML and run the unchanged final audit.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=BASE_XML)
    parser.add_argument('--candidate', type=Path, default=OUT/'compiled.xml')
    parser.add_argument('--base-swf', type=Path, default=BASE_SWF)
    parser.add_argument('--candidate-swf', type=Path, default=OUT/'pfe.swf')
    parser.add_argument('--out', type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--retain-unchanged-bodies', '--retain', dest='retain', action='store_true')
    action.add_argument('--splice-abc', dest='splice', action='store_true')
    args = parser.parse_args()
    report_path_valid = False
    try:
        if args.retain:
            require(args.out is not None, 'Retain requires a separate --out XML')
            result = retain(args.base, args.candidate, args.out)
        elif args.splice:
            require(args.out is not None, 'Splice requires a separate --out SWF')
            result = splice_abc(args.base, args.candidate, args.base_swf, args.candidate_swf, args.out)
        else:
            if args.out:
                inputs = [p.resolve() for p in (args.base, args.candidate, args.base_swf, args.candidate_swf)]
                require(args.out.suffix.lower() == '.json' and args.out.resolve() not in inputs, 'Audit output must be a separate JSON')
                report_path_valid = True
            result = audit(args.base, args.candidate, args.base_swf, args.candidate_swf)
            if args.out:args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    except Exception as error:
        result = dict(passed=False, error=type(error).__name__ + ': ' + str(error))
        if report_path_valid:
            args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
        print(json.dumps(result, ensure_ascii=False));raise SystemExit(1)
    print(json.dumps({k: v for k, v in result.items() if k != 'unchangedMethodBodySHA256'}, ensure_ascii=False))


if __name__ == '__main__':main()
