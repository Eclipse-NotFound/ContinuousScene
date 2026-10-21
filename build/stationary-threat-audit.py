"""Offline fail-closed audit: only NativeSceneActivity.update/stats may change.

Consumes existing FFDec XML; never starts a compiler/JVM/AIR or writes a SWF.
Reuses native-crop-audit's ABC instruction/signature/exception/trait comparator.
All class layouts, named methods, script initializers and anonymous bodies must
remain equivalent except the two explicitly permitted executable bodies.
The build that exports XML must retain its SWF/XML provenance; this tool records
both hashes but deliberately does not claim to regenerate XML from binary.
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
import zlib

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B / 'generated/stationary-threat-20261021'
BASE_SWF = B / 'large-map/ContinuousSceneMod.swf'
CANDIDATE_SWF = OUT / 'ContinuousSceneMod.swf'
BASE_HASH = '7F1F2961C6E299D949423591F3C65C610C2EAEFA7FC72E8A583A402770D6B51F'
ALLOWED = {'NativeSceneActivity::1:1:update', 'NativeSceneActivity::1:1:stats'}
spec = importlib.util.spec_from_file_location('stationary_threat_abc', B / 'native-crop-audit.py')
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)
require = core.require


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def swf_envelope(path):
    """Compare actual non-ABC SWF payloads, independent of compression/tag form."""
    raw = path.read_bytes()
    require(len(raw) >= 12 and raw[:3] in (b'FWS', b'CWS'), 'Unsupported SWF signature: ' + str(path))
    body = zlib.decompress(raw[8:]) if raw[:3] == b'CWS' else raw[8:]
    require(len(body) + 8 == int.from_bytes(raw[4:8], 'little'), 'Invalid SWF expanded length')
    rect_bytes = (5 + (body[0] >> 3) * 4 + 7) // 8
    cursor = rect_bytes + 4
    require(cursor <= len(body), 'Truncated SWF frame header')
    header = (raw[3], body[:cursor])
    tags = []
    while cursor < len(body):
        require(cursor + 2 <= len(body), 'Truncated tag header')
        tag = int.from_bytes(body[cursor:cursor + 2], 'little'); cursor += 2
        kind, length = tag >> 6, tag & 63
        if length == 63:
            require(cursor + 4 <= len(body), 'Truncated long tag header')
            length = int.from_bytes(body[cursor:cursor + 4], 'little'); cursor += 4
        require(cursor + length <= len(body), 'Truncated tag payload')
        payload = body[cursor:cursor + length]; cursor += length
        if kind == 82:
            require(len(payload) >= 5 and b'\0' in payload[4:], 'Invalid DoABC header')
            end = payload.index(b'\0', 4) + 1
            tags.append((kind, payload[:end]))
        elif kind == 72:
            tags.append((kind, b''))
        else:
            tags.append((kind, payload))
        if kind == 0:
            require(cursor == len(body), 'Trailing SWF bytes after End tag')
            break
    return header, tags


def method_refs(abc, index, anonymous_only=False):
    body = abc.bodies.get(index)
    if body is None:
        return []
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    # Validate exception targets even in an explicitly changed method.
    core.Compare.exceptions(body, abc, addresses)
    return [value for _, _, opcode, operands in rows if opcode not in core.DEBUG
            for kind, value in operands if kind == 'm'
            and (not anonymous_only or value not in abc.names_by_method)]


def header(node, ignored):
    return {k: v for k, v in node.attrib.items() if k not in ignored}


def traits(compare, a, b, label):
    require(a is not None and b is not None and len(a) == len(b), label + ': trait count changed')
    for number, (old, new) in enumerate(zip(a, b)):
        require(compare.trait(old, compare.a) == compare.trait(new, compare.b), label + ': trait layout changed')
        for attr in ('method_info', 'function', 'function_index'):
            if attr in old.attrib or attr in new.attrib:
                require(attr in old.attrib and attr in new.attrib, label + ': trait binding removed')
                oi, ni = int(old.get(attr)), int(new.get(attr))
                on, nn = compare.a.names_by_method.get(oi), compare.b.names_by_method.get(ni)
                require(on == nn, label + ': trait method identity changed')
                if on not in ALLOWED:
                    compare.body(oi, ni, label + '/trait-' + str(number))


def retain_unchanged_bodies(base_xml, candidate_xml, output_xml):
    """Stage two imported bodies onto the original XML skeleton.

    FFDec importScript reorders the method table and recreates private
    namespaces, so merely restoring old bodies in the imported class is unsafe.
    Keep the complete original skeleton instead. New bodies contain no method
    or class-index operands and no activation traits; new constant pool slots
    are appended without touching the old prefix. Rebind recreated class and
    lexical private namespaces through appended pool entries, never bytecode.
    """
    require(output_xml.suffix.lower() == '.xml', 'Retained-body output must be XML')
    require(output_xml.resolve() not in (base_xml.resolve(), candidate_xml.resolve()), 'Use a separate retained-body output')
    old_tree, new_tree = ET.parse(base_xml), ET.parse(candidate_xml)
    old_nodes, new_nodes = old_tree.findall('.//abc'), new_tree.findall('.//abc')
    require(len(old_nodes) == len(new_nodes) and old_nodes, 'ABC count changed or missing')
    copied, mappings = [], []
    for number, (old_node, new_node) in enumerate(zip(old_nodes, new_nodes)):
        a, b = core.ABC(old_node), core.ABC(new_node)
        require(old_node.attrib == new_node.attrib, 'ABC header changed')
        require(set(a.named) == set(b.named) and set(a.class_by_name) == set(b.class_by_name), 'Method/class set changed')
        require(len(a.methods) == len(b.methods), 'Method table size changed')
        require(set(a.cp) == set(b.cp), 'Constant pool kind changed')
        for pool, entries in a.cp.items():
            require(len(b.cp[pool]) >= len(entries), 'Constant pool shortened: ' + pool)
            require(all(core.xml_value(v) == core.xml_value(b.cp[pool][i]) for i, v in enumerate(entries)), 'Constant pool prefix changed: ' + pool)
        local_allowed = ALLOWED & set(a.named)
        if not local_allowed:
            require(core.xml_value(old_node) == core.xml_value(new_node), 'Unrelated ABC changed')
            continue
        require(local_allowed == ALLOWED, 'Expected both target bodies in the same ABC')
        ai, bi = a.class_by_name['NativeSceneActivity'], b.class_by_name['NativeSceneActivity']
        old_traits = a.statics[ai].find('static_traits/traits')
        new_traits = b.statics[bi].find('static_traits/traits')
        require(len(old_traits) == len(new_traits), 'Activity trait count changed')
        ns_map = {}
        class_old, class_new = set(), set()
        for old, new in zip(old_traits, new_traits):
            on, nn = int(old.get('name_index')), int(new.get('name_index'))
            require(a.simple(on) == b.simple(nn), 'Activity member order/name changed')
            om, nm = a.cp['constant_multiname'][on], b.cp['constant_multiname'][nn]
            oi, ni = int(om.get('namespace_index', '0')), int(nm.get('namespace_index', '0'))
            if oi != ni:
                require(ni >= len(a.cp['constant_namespace']), 'Existing namespace binding changed')
                require(a.cp['constant_namespace'][oi].get('kind') == b.cp['constant_namespace'][ni].get('kind') == '5', 'Only recreated private namespaces may be rebound')
                require(ns_map.get(ni, oi) == oi, 'Ambiguous private namespace map')
                ns_map[ni] = oi;class_old.add(oi);class_new.add(ni)
        require(len(class_old) == len(class_new) == 1, 'Expected one recreated Activity private namespace')
        # Its lexical namespace set also has one file-private namespace. Match
        # all public/protected identities first; the remaining private pair is
        # uniquely determined, with no name-based guessing among empty URIs.
        old_class, new_class = next(iter(class_old)), next(iter(class_new))
        for new_set in b.cp['constant_namespace_set'][len(a.cp['constant_namespace_set']):]:
            members = [int(n.text) for n in new_set.findall('namespaces/item')]
            if new_class not in members:
                continue
            stable = {i for i in members if b.cp['constant_namespace'][i].get('kind') != '5'}
            matches = []
            for old_set in a.cp['constant_namespace_set']:
                old_members = [int(n.text) for n in old_set.findall('namespaces/item')]
                if old_class in old_members and {i for i in old_members if a.cp['constant_namespace'][i].get('kind') != '5'} == stable:
                    matches.append(old_members)
            require(len(matches) == 1, 'Ambiguous original Activity lexical namespace set')
            old_private = set(matches[0]) - stable - {old_class}
            new_private = set(members) - stable - {new_class}
            require(len(old_private) == len(new_private) == 1, 'Unexpected Activity lexical namespace structure')
            oi, ni = next(iter(old_private)), next(iter(new_private))
            require(ni >= len(a.cp['constant_namespace']) and b.cp['constant_namespace'][ni].get('kind') == '5', 'Unexpected lexical namespace remapping')
            require(ns_map.get(ni, oi) == oi, 'Conflicting lexical namespace mapping')
            ns_map[ni] = oi
        constants = copy.deepcopy(new_node.find('constants'))
        for entry in list(constants.find('constant_multiname'))[len(a.cp['constant_multiname']):]:
            value = int(entry.get('namespace_index', '0'))
            if value in ns_map:entry.set('namespace_index', str(ns_map[value]))
        for entry in list(constants.find('constant_namespace_set'))[len(a.cp['constant_namespace_set']):]:
            for item in entry.findall('namespaces/item'):
                value = int(item.text)
                if value in ns_map:item.text = str(ns_map[value])
        # Prove the imported class really has the original layout after the
        # private identities are restored, before discarding the imported one.
        normalized_node = copy.deepcopy(new_node)
        normalized_node.remove(normalized_node.find('constants'));normalized_node.insert(0, copy.deepcopy(constants))
        normalized = core.ABC(normalized_node);compare = core.Compare(a, normalized)
        for old, new in zip(old_traits, normalized.statics[bi].find('static_traits/traits')):
            require(compare.trait(old, a) == compare.trait(new, normalized), 'Activity layout changed beyond private namespace recreation')
        for name in local_allowed:
            oi, ni = a.named[name], b.named[name]
            require(a.signature(oi) == b.signature(ni), name + ': method signature changed')
            body = b.bodies.get(ni)
            require(body is not None and not list(body.find('traits/traits')), name + ': missing body or activation traits')
            rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
            core.Compare.exceptions(body, b, addresses)
            require(not any(kind in ('m', 'c') for row in rows for kind, value in row[3]), name + ': method/class-index operands require explicit relocation')
            replacement = copy.deepcopy(body);replacement.set('method_info', str(oi))
            old_body = a.bodies[oi];container = old_node.find('bodies')
            index = list(container).index(old_body);container.remove(old_body);container.insert(index, replacement)
            copied.append(dict(method=name, importedIndex=ni, originalIndex=oi, codeSHA256=hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()))
        old_constants = old_node.find('constants');index = list(old_node).index(old_constants)
        old_node.remove(old_constants);old_node.insert(index, constants)
        mappings.append(dict(abc=number, privateNamespaces=ns_map))
    require({c['method'] for c in copied} == ALLOWED, 'Did not copy exactly the two target bodies')
    old_tree.write(output_xml, encoding='utf-8', xml_declaration=True)
    return dict(stagedXML=True, outputXML=str(output_xml), outputXMLSHA256=sha(output_xml), copiedBodies=copied,
                namespaceMappings=mappings, bytecodeOperandsUnchanged=True,
                nextStep='Convert this XML to SWF, export it again, then run the unmodified strict audit.')


def audit(base_xml, candidate_xml, base_swf, candidate_swf):
    require(sha(base_swf) == BASE_HASH, 'Baseline is not installed CS 0.9.0 / 7F1F')
    require(swf_envelope(base_swf) == swf_envelope(candidate_swf), 'Non-ABC SWF header/tag/asset changed')
    old_tree, new_tree = ET.parse(base_xml), ET.parse(candidate_xml)
    old_nodes, new_nodes = old_tree.findall('.//abc'), new_tree.findall('.//abc')
    require(len(old_nodes) == len(new_nodes) and old_nodes, 'ABC count changed or missing')
    counts = dict(unchangedNamedMethods=0, unchangedClassLayouts=0, unchangedScriptInitializers=0,
                  equivalentAnonymousMethods=0, unchangedUnreferencedMethods=0,
                  totalBaseMethods=0, totalCandidateMethods=0)
    seen_allowed, actual_changed, hashes, pools = set(), [], {}, []
    for number, (old_node, new_node) in enumerate(zip(old_nodes, new_nodes)):
        a, b = core.ABC(old_node), core.ABC(new_node)
        require(old_node.attrib == new_node.attrib, 'ABC header changed')
        for pool, entries in a.cp.items():
            require(pool in b.cp and len(b.cp[pool]) >= len(entries), 'Constant pool shortened: ' + pool)
            for i, value in enumerate(entries):
                require(core.xml_value(value) == core.xml_value(b.cp[pool][i]), 'Existing constant changed: ' + pool + ':' + str(i))
        require(set(a.cp) == set(b.cp), 'Constant pool kind changed')
        pools.append({name: len(b.cp[name]) - len(a.cp[name]) for name in a.cp})
        require(set(a.named) == set(b.named), 'Named method set changed')
        require(set(a.class_by_name) == set(b.class_by_name), 'Class set changed')
        require(len(a.methods) == len(b.methods), 'Method table size changed; added anonymous/orphan body is not permitted')
        compare = core.Compare(a, b)
        allowed_pairs = set()
        for name, oi in a.named.items():
            ni = b.named[name]
            if name in ALLOWED:
                seen_allowed.add(name); allowed_pairs.add((oi, ni))
                require(a.signature(oi) == b.signature(ni), name + ': signature changed')
                require((oi in a.bodies) == (ni in b.bodies), name + ': body availability changed')
                old_refs = method_refs(a, oi, True); new_refs = method_refs(b, ni, True)
                require(len(old_refs) == len(new_refs), name + ': anonymous references added/removed')
                for index, (oref, nref) in enumerate(zip(old_refs, new_refs)):
                    compare.anonymous.add((oref, nref));compare.body(oref, nref, name + '/anonymous-' + str(index))
                obody, nbody = a.bodies.get(oi), b.bodies.get(ni)
                if obody is not None:
                    traits(compare, obody.find('traits/traits'), nbody.find('traits/traits'), name + '/activation')
                    if obody.get('codeBytes') != nbody.get('codeBytes'):
                        actual_changed.append(name)
            else:
                compare.body(oi, ni, name);counts['unchangedNamedMethods'] += 1
        for name, ai in a.class_by_name.items():
            bi = b.class_by_name[name]
            for part, x, y in [('instance', a.instances[ai], b.instances[bi]), ('static', a.statics[ai], b.statics[bi])]:
                require(header(x, {'iinit_index', 'cinit_index', 'bytes', 'fileOffset'}) == header(y, {'iinit_index', 'cinit_index', 'bytes', 'fileOffset'}), name + ': class header changed')
                container = 'instance_traits/traits' if part == 'instance' else 'static_traits/traits'
                traits(compare, x.find(container), y.find(container), name + '/' + part)
                ignored_container = 'instance_traits' if part == 'instance' else 'static_traits'
                require([core.xml_value(n, {'bytes', 'fileOffset'}) for n in x if n.tag != ignored_container] ==
                        [core.xml_value(n, {'bytes', 'fileOffset'}) for n in y if n.tag != ignored_container], name + ': class metadata/interfaces changed')
            counts['unchangedClassLayouts'] += 1
        old_scripts, new_scripts = list(old_node.find('script_info')), list(new_node.find('script_info'))
        require(len(old_scripts) == len(new_scripts), 'Script count changed')
        for index, (x, y) in enumerate(zip(old_scripts, new_scripts)):
            require(header(x, {'init_index'}) == header(y, {'init_index'}), 'Script header changed')
            compare.body(int(x.get('init_index')), int(y.get('init_index')), 'abc-' + str(number) + '/script-' + str(index))
            traits(compare, x.find('traits/traits'), y.find('traits/traits'), 'script-' + str(index))
            counts['unchangedScriptInitializers'] += 1
        # Do not silently ignore old orphan/anonymous bodies just because no
        # named method happens to reach them after this particular import.
        covered_old = {p[0] for p in compare.visited | allowed_pairs}
        covered_new = {p[1] for p in compare.visited | allowed_pairs}
        old_left = set(range(len(a.methods))) - covered_old
        new_left = set(range(len(b.methods))) - covered_new
        require(old_left == new_left, 'Unmapped method relocation; require explicit review rather than guessing')
        for index in sorted(old_left):
            compare.body(index, index, 'abc-' + str(number) + '/unreferenced-' + str(index))
            counts['unchangedUnreferencedMethods'] += 1
        counts['equivalentAnonymousMethods'] += len(compare.anonymous)
        counts['totalBaseMethods'] += len(a.methods);counts['totalCandidateMethods'] += len(b.methods)
        covered = {'constants', 'method_info', 'bodies', 'instance_info', 'class_info', 'script_info'}
        require([core.xml_value(n, {'bytes', 'fileOffset'}) for n in old_node if n.tag not in covered] ==
                [core.xml_value(n, {'bytes', 'fileOffset'}) for n in new_node if n.tag not in covered], 'Other ABC metadata changed')
        hashes.update({'abc-' + str(number) + '/' + label: digest for label, digest in compare.hashes.items()})
    require(seen_allowed == ALLOWED, 'Expected NativeSceneActivity.update/stats methods not found')
    return dict(passed=True, **counts, allowedChangedMethods=sorted(ALLOWED), actualChangedBodies=sorted(actual_changed),
                addedFields=[], addedMethods=[], originalConstantPoolPreserved=True, appendedConstants=pools,
                nonABCSWFEnvelopePreserved=True, baseXML=str(base_xml), candidateXML=str(candidate_xml),
                baseSWF=str(base_swf), candidateSWF=str(candidate_swf), baseXMLSHA256=sha(base_xml),
                candidateXMLSHA256=sha(candidate_xml), baseSHA256=sha(base_swf), candidateSHA256=sha(candidate_swf),
                semanticComparatorSHA256=sha(B/'native-crop-audit.py'), normalizedExecutableHashes=hashes,
                xmlProvenance='Existing FFDec exports; build must bind these XML hashes to the recorded SWF inputs.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=OUT/'baseline.xml')
    parser.add_argument('--candidate', type=Path, default=OUT/'candidate.xml')
    parser.add_argument('--base-swf', type=Path, default=BASE_SWF)
    parser.add_argument('--candidate-swf', type=Path, default=CANDIDATE_SWF)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--retain-unchanged-bodies', action='store_true', help='Write a separate XML preserving the original skeleton and importing only update/stats; --out must be .xml')
    args = parser.parse_args()
    if args.retain_unchanged_bodies:
        require(args.out is not None, '--retain-unchanged-bodies requires a separate --out XML')
        result = retain_unchanged_bodies(args.base.resolve(), args.candidate.resolve(), args.out.resolve())
        print(json.dumps(result, ensure_ascii=False));return
    paths = [p.resolve() for p in (args.base, args.candidate, args.base_swf, args.candidate_swf)]
    if args.out:
        require(args.out.suffix.lower() == '.json' and args.out.resolve() not in paths, 'Output must be a separate JSON report')
    try:
        result = audit(*paths)
    except Exception as error:
        result = dict(passed=False, error=type(error).__name__ + ': ' + str(error), baseXML=str(paths[0]), candidateXML=str(paths[1]))
        if args.out:args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
        print(json.dumps(result, ensure_ascii=False));raise SystemExit(1)
    if args.out:args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'normalizedExecutableHashes'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
