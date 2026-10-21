"""Pinned BEFC Unit.blit retain/splice/audit wrapper; no JVM/AIR.

Shares Bullet's strict body/layout and original-asset checks through a private
module instance. Bullet's default timer gate and source are left untouched.
Only this candidate's generated directory may receive outputs.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B / 'generated/unit-blit-20261022'
CLASS = 'fe.unit.Unit'
TARGET = CLASS + '::0:1:blit'
spec = importlib.util.spec_from_file_location('unit_blit_private_audit', B/'bullet-segments-audit.py')
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
engine.CLASS, engine.TARGET, engine.OUT = CLASS, TARGET, OUT
require = engine.require
BASE_XML, BASE_SWF, BASE_HASH = engine.BASE_XML, engine.BASE_SWF, engine.BASE_HASH
_layout_proof = None


def unit_body_check(abc, index):
    rows, _ = engine.core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    require(not any(r[2] in (0x43, 0x6c, 0x6d, 0x6e, 0x6f) for r in rows),
            'Unit.blit uses slot/dispatch indices; imported layout cannot be discarded safely')
    require(not any((kind == 'n' and abc.simple(value) == 'namok_t') or
                    (kind == 's' and abc.string(value) == 'namok_t')
                    for row in rows for kind, value in row[3]),
            'Unit.blit references namok_t instead of only its approved blit/callback properties')
    return None


def normalize_discarded_unit_layout(a, b, new_names):
    """Validate import-only layout drift; output still uses baseline nodes.

    This changes only the in-memory imported XML used by retain's layout
    check. No original constant-pool slot, body or final class node is edited.
    Unit.blit must access fields by name, not by the reordered slot/dispatch
    indices. Every imported field definition must match its original one.
    """
    global _layout_proof
    unit_body_check(b, b.named[TARGET])
    rows, _ = engine.core.decode(bytes.fromhex(b.bodies[b.named[TARGET]].get('codeBytes')))
    require(not any(r[2] in (0x43, 0x6c, 0x6d, 0x6e, 0x6f) for r in rows),
            'Unit.blit uses slot/dispatch indices; imported layout cannot be discarded safely')
    ai, bi = a.class_by_name[CLASS], b.class_by_name[CLASS]
    old_instance = a.instances[ai].find('instance_traits/traits')
    new_instance = b.instances[bi].find('instance_traits/traits')
    require(len(old_instance) == len(new_instance), 'Unit instance trait count changed')
    compare = engine.core.Compare(a, b)
    private_changes = []
    for old, new in zip(old_instance, new_instance):
        if compare.trait(old, a) == compare.trait(new, b):continue
        oi, ni = int(old.get('name_index')), int(new.get('name_index'))
        require(old.get('type') == new.get('type') == 'TraitSlotConst' and
                a.simple(oi) == b.simple(ni) == 'namok_t', 'Unexpected Unit instance layout drift')
        om, nm = a.cp['constant_multiname'][oi], b.cp['constant_multiname'][ni]
        ons, nns = int(om.get('namespace_index')), int(nm.get('namespace_index'))
        require(ons == 140 and nns == 840 and oi == 2550 and ni >= len(a.cp['constant_multiname']),
                'namok_t differs from the pinned BEFC/import identity pair')
        require(engine.private(a, ons) and engine.private(b, nns) and engine.namespace_name(b, nns) == 'fe.unit:Unit',
                'namok_t is not the uniquely identified Unit private field')
        normalized_name = copy.deepcopy(nm);normalized_name.set('namespace_index', str(ons))
        require(engine.core.xml_value(om) == engine.core.xml_value(normalized_name), 'namok_t QName changed beyond its private identity')
        require(not any(b.simple(n) == 'namok_t' for n in new_names) and
                not any(k == 's' and b.string(v) == 'namok_t' for row in rows for k, v in row[3]),
                'New blit references imported namok_t; cannot discard its private binding')
        normalized_trait = copy.deepcopy(new);normalized_trait.set('name_index', str(oi))
        require(compare.trait(old, a) == compare.trait(normalized_trait, b), 'namok_t field type/default/layout changed')
        new.set('name_index', str(oi))
        private_changes.append(dict(field='namok_t', importedQName=ni, retainedQName=oi,
                                    importedPrivateNamespace=nns, retainedPrivateNamespace=ons))
    require(len(private_changes) <= 1, 'Ambiguous namok_t field definition')
    old_static = a.statics[ai].find('static_traits/traits')
    new_static = b.statics[bi].find('static_traits/traits')
    require(len(old_static) == len(new_static), 'Unit static field count changed')
    def key(trait, abc):
        require(trait.get('type') in ('TraitSlotConst', 'TraitMethodGetterSetter'), 'Unexpected Unit static trait')
        clone = copy.deepcopy(trait);clone.attrib.pop('slot_id', None)
        return compare.trait(clone, abc)
    imported = {}
    for trait in new_static:
        token = key(trait, b)
        require(token not in imported, 'Duplicate imported Unit static definition')
        imported[token] = trait
    restored, slot_changes = [], []
    for old in old_static:
        token = key(old, a)
        require(token in imported, 'Unit static field name/type/default/metadata changed')
        new = copy.deepcopy(imported.pop(token))
        if old.get('type') == 'TraitSlotConst':
            if new.get('slot_id') != old.get('slot_id'):
                slot_changes.append(dict(field=a.simple(int(old.get('name_index'))),
                                         importedSlot=new.get('slot_id'), retainedSlot=old.get('slot_id')))
            new.set('slot_id', old.get('slot_id'))
        else:
            require(a.names_by_method[int(old.get('method_info'))] == b.names_by_method[int(new.get('method_info'))],
                    'Imported Unit static method identity changed')
        restored.append(new)
    require(not imported, 'Unexpected added Unit static definition')
    new_static[:] = restored
    _layout_proof = dict(importedPrivateFieldViewNormalized=private_changes,
                        importedStaticSlotOrderDiscarded=slot_changes,
                        targetHasNoSlotOrDispatchIndexOperands=True,
                        finalClassLayoutSource='Original BEFC XML; no imported layout is copied')


def existing_private_identities(a, b, old_names, new_names):
    # Original blit has no lexical namespace-set. Unit's other historical
    # bodies contain several distinct private scopes; do not guess among them.
    sets, direct = engine.namespace_uses(b, new_names)
    used = direct | {n for nsset in sets for n in engine.set_members(b, nsset)}
    require(not any(n >= len(a.cp['constant_namespace']) and engine.private(b, n) for n in used),
            'Unit.blit introduces a new private scope without an original-blit mapping proof')
    normalize_discarded_unit_layout(a, b, new_names)
    return {}, []


engine.lexical_map = existing_private_identities
engine.timer_binding = unit_body_check


def output_path(path, suffix):
    path = Path(path)
    require(path.suffix.lower() == suffix and path.resolve().is_relative_to(OUT.resolve()),
            'Output must remain inside generated/unit-blit-20261022 with suffix ' + suffix)
    return path


def label(result):
    result.pop('timerBinding', None)
    result['auditTarget'] = TARGET
    result['wrapperSHA256'] = engine.sha(Path(__file__))
    result['sharedAuditSHA256'] = engine.sha(B/'bullet-segments-audit.py')
    return result


def retain(base_xml, candidate_xml, output_xml):
    global _layout_proof
    _layout_proof = None
    result = label(engine.retain(Path(base_xml), Path(candidate_xml), output_path(output_xml, '.xml')))
    result['discardedImportedLayoutProof'] = _layout_proof
    return result


def splice_abc(base_xml, candidate_xml, base_swf, candidate_swf, output_swf):
    return label(engine.splice_abc(Path(base_xml), Path(candidate_xml), Path(base_swf), Path(candidate_swf),
                                   output_path(output_swf, '.swf')))


def audit(base_xml, candidate_xml, base_swf=BASE_SWF, candidate_swf=OUT/'pfe.swf'):
    return label(engine.audit(Path(base_xml), Path(candidate_xml), Path(base_swf), Path(candidate_swf)))


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
                out = output_path(args.out, '.json')
                require(out.resolve() not in {p.resolve() for p in (args.base, args.candidate, args.base_swf, args.candidate_swf)},
                        'Audit report must not overwrite an input')
                report = out
            result = audit(args.base, args.candidate, args.base_swf, args.candidate_swf)
    except Exception as error:
        result = dict(passed=False, auditTarget=TARGET, error=type(error).__name__ + ': ' + str(error))
        if report:report.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
        print(json.dumps(result, ensure_ascii=False));raise SystemExit(1)
    if report:report.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'unchangedMethodBodySHA256'}, ensure_ascii=False))


if __name__ == '__main__':main()
