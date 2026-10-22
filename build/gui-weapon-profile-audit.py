"""Fail-closed, one-method BEFC GUI.setWeapon diagnostic retention/audit.

The first import is evidence only. Approve its exact instruction body, invocation
frame and lexical namespace identities after inspection, before retention.
The shared audit remains unchanged; no imported class or constructor is copied.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
OUT = B/'generated/gui-weapon-profile-20261022'
CLASS = 'fe.inter.GUI'
TARGET = CLASS + '::0:1:setWeapon'
BASE_XML_HASH = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
BASE_CODE_HASH = '04A6125014B7C64CC0142262817D4CEBD9E24E0E2F8138DB13B442F4F66AC158'
BASE_FRAME = dict(init_scope_depth='4', max_scope_depth='5', max_regs='5', max_stack='3')

# Reviewed from compiled.xml; original import-review/provenance remain intact.
REVIEWED_IMPORT_XML_SHA = 'B84CD2BC0E82B24564DCD7CEEEEF9C6265DCA2A62EC9F4449B5045088E88C2EF'
REVIEWED_CODE_SHA = '7FEA681E40CE43AFC7208D894D83655F2247853B37E790E5F71F4E14EE4ADA30'
REVIEWED_FRAME = dict(init_scope_depth='4', max_scope_depth='5', max_regs='21', max_stack='3')
REVIEWED_IMPORT_NAMESPACE_MAP = {865: 487, 864: 488}
REVIEWED_OPERAND_BINDINGS_SHA = 'A57EA9975B3722667098E046A3008B930D20834F1FFE5B842878312A00837184'
REVIEWED_NATIVE_PROJECTION_SHA = 'AFCA9B3351F271BE384898575AACD22A8DDD6DA90F5F34C7712CEC6A49FBEB61'
NATIVE_RANGES = [(0, 2), (276, 463), (480, 488), (530, 550), (575, 601), (618, 646),
                 (671, 686), (703, 718), (743, 747), (764, 773), (798, 802), (819, 828),
                 (870, 879), (921, 926), (1335, 1336)]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load('gui_weapon_private_bullet_audit', B/'bullet-segments-audit.py')
recipe = load('gui_weapon_profile_recipe', B/'gui-weapon-profile.py')
engine.CLASS, engine.TARGET, engine.OUT = CLASS, TARGET, OUT
core, require = engine.core, engine.require
BASE_XML, BASE_SWF, BASE_HASH = engine.BASE_XML, engine.BASE_SWF, engine.BASE_HASH
_timer_binding, _strict_audit = engine.timer_binding, engine.audit


def code_sha(body):
    return hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()


def value_sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest().upper()


def resolved_name(abc, index):
    """Resolve every used name/string/scope, including appended pool entries."""
    node = abc.cp['constant_multiname'][index]
    kind = node.get('kind')
    require(kind in ('7', '9', '27'), 'Unreviewed target multiname kind')
    ns, nsset = int(node.get('namespace_index', '0')), int(node.get('namespace_set_index', '0'))

    def namespace(number):
        item = abc.cp['constant_namespace'][number]
        if number in REVIEWED_IMPORT_NAMESPACE_MAP:
            require(item.get('kind') == '5' and engine.namespace_name(abc, number) ==
                    {865: 'fe.inter:GUI', 864: 'GUI.as$33'}[number], 'Reviewed imported private identity changed')
            return REVIEWED_IMPORT_NAMESPACE_MAP[number], '5', ''
        return number, item.get('kind'), engine.namespace_name(abc, number)

    return (kind, abc.simple(index), namespace(ns) if ns else None,
            sorted(namespace(number) for number in engine.set_members(abc, nsset)) if nsset else None)


def operand_bindings_sha(abc, rows):
    bindings = {}
    for row in rows:
        for kind, value in row[3]:
            if kind == 'n':bindings['n:' + str(value)] = resolved_name(abc, value)
            elif kind == 's':bindings['s:' + str(value)] = abc.string(value)
            else:require(kind not in ('i', 'q', 'd', 'p', 'm', 'c'), 'Unreviewed constant/index operand')
    return value_sha(bindings)


def native_projection_proof(a, b):
    """Project exactly the reviewed native spans, preserving branch destinations."""
    old, _ = core.decode(bytes.fromhex(a.bodies[a.named[TARGET]].get('codeBytes')))
    imported, _ = core.decode(bytes.fromhex(b.bodies[b.named[TARGET]].get('codeBytes')))
    # FFDec adds coerce_s to an already-String result. This is the sole excluded
    # native-span instruction: getlocal1 + literal '</span>' + add + coerce_s.
    extra = [row for row in imported if 456 <= row[0] <= 462]
    require([(row[0], row[2], row[3]) for row in extra] == [
        (456, 0xd1, []), (457, 0x2c, [('s', 4698)]), (460, 0xa0, []),
        (461, 0x85, []), (462, 0xd5, [])] and b.string(4698) == '</span>',
        'Reviewed redundant String coercion context changed')
    native = [row for row in imported if row[0] != 461 and
              any(start <= row[0] < end for start, end in NATIVE_RANGES)]

    def canonical(abc, rows):
        positions = [row[0] for row in rows]
        result = []
        for _, _, opcode, args in rows:
            operands = []
            for kind, value in args:
                if kind == 'n':value = resolved_name(abc, value)
                elif kind == 's':value = abc.string(value)
                elif kind == 'target':value = bisect.bisect_left(positions, value)
                operands.append((kind, value))
            result.append((opcode, operands))
        return result

    before, after = canonical(a, old), canonical(b, native)
    require(len(before) == 170 and before == after and value_sha(before) == REVIEWED_NATIVE_PROJECTION_SHA,
            'Original GUI instructions, register identities, operands or branch destinations changed')
    return dict(nativeInstructions=170, nativeProjectionSHA256=REVIEWED_NATIVE_PROJECTION_SHA,
                nativeRegisters=[1, 2, 3, 4], diagnosticRegisters=list(range(5, 19)),
                statsIncrementTemporaryRegisters=[19, 20], redundantStringCoercionOffset=461,
                originalCallAndBranchOrderPreserved=True)


def body_proof(abc, index):
    require(abc.names_by_method.get(index) == TARGET, 'Approval applies only to GUI.setWeapon')
    body = abc.bodies[index]
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, abc, addresses)
    require(abc.methods[index].get('flags') == '0', 'Native method flags changed; no activation is permitted')
    require(not list(body.find('traits/traits')) and not list(body.find('exceptions')),
            'GUI.setWeapon must have no activation traits or catch objects')
    require(not any(row[2] in (0x40, 0x43, 0x57, 0x5a, 0x6c, 0x6d, 0x6e, 0x6f) for row in rows),
            'Unexpected closure/activation/catch/direct-method/numeric-slot instruction')
    require(not any(kind in ('m', 'c') for row in rows for kind, _ in row[3]),
            'Target method/class-index operand requires explicit relocation')
    frame = {key: body.get(key) for key in BASE_FRAME}
    baseline = code_sha(body) == BASE_CODE_HASH
    if baseline:
        require(index == 599 and frame == BASE_FRAME, 'Native GUI.setWeapon identity/frame changed')
    else:
        require(REVIEWED_CODE_SHA is not None and REVIEWED_FRAME is not None,
                'GUI imported body/frame requires explicit post-compile review; use --inspect-import')
        require(code_sha(body) == REVIEWED_CODE_SHA and frame == REVIEWED_FRAME,
                'Target body/frame differs from the reviewed import')
        require(frame['init_scope_depth'] == BASE_FRAME['init_scope_depth']
                and frame['max_scope_depth'] == BASE_FRAME['max_scope_depth'], 'Captured scope changed')
        require(operand_bindings_sha(abc, rows) == REVIEWED_OPERAND_BINDINGS_SHA,
                'Reviewed name/string/namespace operand binding changed')
        debug_locals = [(abc.string(row[3][1][1]), row[3][2][1]) for row in rows if row[2] == 0xef]
        require(debug_locals == list(zip(['_loc1_', '_loc2_', '_loc3_', '_loc4_'] +
                    [name for name, _ in recipe.LOCAL_SCHEMA], range(18))), 'Reviewed local register layout changed')
    return dict(codeSHA256=code_sha(body), baseline=baseline, frame=frame,
                newActivation=False, newClosures=False, newCatch=False, numericSlotAccess=False)


def body_operands(abc, index):
    body_proof(abc, index)
    rows, _ = core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    return {value for row in rows for kind, value in row[3] if kind == 'n'}


def timer_binding(abc, index):
    result = _timer_binding(abc, index)
    require(result['callCount'] == recipe.TIMER_CALLS, 'Unexpected GUI timer call count')
    return result


def lexical_map(a, b, old_names, new_names):
    """Use only an explicitly reviewed import-to-original private identity map."""
    require(a.named[TARGET] == 599, 'Unexpected original method identity')
    old_sets, old_direct = engine.namespace_uses(a, old_names)
    require(old_sets == {35} and old_direct == {1, 9, 10, 36}, 'Original lexical bindings changed')
    original = engine.set_members(a, 35)
    require(original == [487, 1, 36, 488, 14, 421, 9, 70, 489], 'Original GUI lexical scope changed')
    original_private = {487, 488}
    require({n for n in original if engine.private(a, n)} == original_private, 'Original private identity changed')
    require(not any(int(n.get('namespace_index', '0')) in original_private for n in a.cp['constant_multiname']),
            'Original private namespaces unexpectedly declare or directly refer to a QName')
    sets, direct = engine.namespace_uses(b, new_names)
    used_private = {n for n in direct if engine.private(b, n)} | {
        n for nsset in sets for n in engine.set_members(b, nsset) if engine.private(b, n)}
    new_private = used_private - original_private
    mapping = {}
    if new_private:
        require(REVIEWED_IMPORT_NAMESPACE_MAP is not None, 'GUI private namespace identities await explicit review')
        require(set(REVIEWED_IMPORT_NAMESPACE_MAP) == new_private
                and set(REVIEWED_IMPORT_NAMESPACE_MAP.values()) == original_private,
                'Imported private scope does not match the reviewed identities')
        mapping = dict(REVIEWED_IMPORT_NAMESPACE_MAP)
        require(all(new >= len(a.cp['constant_namespace']) and engine.private(b, new) for new in mapping),
                'Cannot rebind existing or non-private namespace')
        require(not any(int(n.get('namespace_index', '0')) in new_private for n in b.cp['constant_multiname']),
                'Imported private namespaces unexpectedly declare or directly refer to a QName')
        native_projection_proof(a, b)
    evidence = []
    for nsset in sorted(sets):
        members = engine.set_members(b, nsset)
        if not any(engine.private(b, n) for n in members):continue
        require(len(members) == len(set(members)) and
                {mapping.get(n, n) for n in members} == set(original), 'Mapped GUI lexical scope changed')
        evidence.append(dict(candidateSet=nsset, originalSet=35, exactReviewedPrivateMap=mapping))
    require(all(mapping.get(n, n) in original_private for n in used_private), 'Unbound private reference')
    return mapping, evidence


engine.body_operands = body_operands
engine.timer_binding = timer_binding
engine.lexical_map = lexical_map


def strict_audit(base_xml, candidate_xml, base_swf=BASE_SWF, candidate_swf=OUT/'pfe.swf'):
    require(engine.sha(base_xml) == BASE_XML_HASH, 'Requires exact BEFC XML')
    result = _strict_audit(base_xml, candidate_xml, base_swf, candidate_swf)
    require(result['actualChangedBodies'] == [TARGET], 'Exactly GUI.setWeapon must change')
    result.update(preservedOriginalLayout=True, constructorsPreserved=True, importedClassCopied=False,
                  importedConstructorsCopied=False, noActivationOrCatch=True, reviewedBodySHA256=REVIEWED_CODE_SHA,
                  operandBindingsSHA256=REVIEWED_OPERAND_BINDINGS_SHA,
                  nativeProjectionSHA256=REVIEWED_NATIVE_PROJECTION_SHA)
    return result


engine.audit = strict_audit


def safe_output(path, suffix):
    path = Path(path)
    require(path.suffix == suffix and path.resolve().is_relative_to(OUT.resolve()),
            'Output must stay in this isolated generated directory')
    return path


def inspect_import(base_xml, candidate_xml):
    """Successful evidence extraction does not authorize retention or execution."""
    a = core.ABC(ET.parse(base_xml).findall('.//abc')[0])
    b = core.ABC(ET.parse(candidate_xml).findall('.//abc')[0])
    oi, ni = a.named[TARGET], b.named[TARGET]
    baseline = body_proof(a, oi)
    body = b.bodies[ni]
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, b, addresses)
    names = {value for row in rows for kind, value in row[3] if kind == 'n'}
    sets, direct = engine.namespace_uses(b, names)
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
    namespace_ids = direct | {n for nsset in sets for n in engine.set_members(b, nsset)}
    return dict(inspected=True, passed=False, runtimeReady=False, reviewRequired=True, target=TARGET,
        originalMethod=oi, importedMethod=ni, originalBody=baseline,
        importedXMLSHA256=engine.sha(candidate_xml), importedCodeSHA256=code_sha(body),
        frame={key: value for key, value in body.attrib.items() if key != 'codeBytes'},
        methodMetadata=b.methods[ni].attrib, signature=b.signature(ni),
        activation=[t.attrib for t in body.find('traits/traits')], exceptions=[n.attrib for n in body.find('exceptions')],
        numericSlotOperations=[dict(offset=r[0], opcode=r[2], slot=r[3][0][1]) for r in rows if r[2] in (0x6c, 0x6d)],
        namespaceSets={str(n): engine.set_members(b, n) for n in sets}, directNamespaces=sorted(direct),
        namespaces={str(n): dict(name=engine.namespace_name(b, n), **b.cp['constant_namespace'][n].attrib) for n in namespace_ids},
        timerBinding=timer_binding(b, ni), importedLayoutDifferences=differences,
        requiredReview=['exact instruction stream/frame and original native statements remain in order',
            '14 new locals stay registers, no activation/catch/closure/class members',
            'qualified timers and explicit private namespace identities',
            'strict imported layout comparison; original classes/constructors remain output'])


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
                'Compiled GUI import is not yet explicitly reviewed')
        require(args.out is not None, 'Retain requires output')
        result = engine.retain(args.base, args.candidate, safe_output(args.out, '.xml'))
        result.update(preservedOriginalLayout=True, importedClassCopied=False, importedConstructorsCopied=False,
                      strictLayoutCheckUnmodified=True, importedLayoutDriftException=False)
    elif args.splice_abc:
        require(args.out is not None, 'Splice requires output')
        result = engine.splice_abc(args.base, args.candidate, args.base_swf, args.candidate_swf, safe_output(args.out, '.swf'))
    else:
        result = strict_audit(args.base, args.candidate, args.base_swf, args.candidate_swf)
    result.update(diagnosticOnly=True, performanceEligible=False, wrapperSHA256=engine.sha(Path(__file__)))
    if args.out and not (args.retain or args.splice_abc):
        safe_output(args.out, '.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    print(json.dumps({key: value for key, value in result.items()
        if key not in ('unchangedMethodBodySHA256', 'numericSlotOperations', 'activation', 'importedLayoutDifferences')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
