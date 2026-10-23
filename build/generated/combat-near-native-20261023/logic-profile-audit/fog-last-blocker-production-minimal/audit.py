"""Fail-closed adapter: retain only reviewed lighting; all other BEFC bytes stay.

The first import can only be inspected. Approval constants remain None until
the actual emitted branches, locals and namespace identities are reviewed.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
OUT = Path(__file__).resolve().parent
B = OUT.parents[3]
CLASS = 'fe.loc.Location'
TARGET = CLASS + '::0:1:lighting'
BASE_XML_SHA = 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66'
BASE_CODE_SHA = '6D1753E4B00B49C53053134248C2DCC9AA09AC2F35480A2C37FD9FDC54B26BC8'
BASE_FRAME = dict(init_scope_depth='4', max_scope_depth='5', max_regs='52', max_stack='7')
BASE_SIGNATURE_SHA = '257BE9B13FA9D53F9A4CA173414F624D5EA32A803B9FA729C145EB4A26E7DBF3'
REVIEWED_IMPORT_XML_SHA = '53E42F57E0FD19AFA215AC9C30D947CAE4EDCFD239819C28F58773F3770F7114'
REVIEWED_CODE_SHA = 'C1162A32C0A4B16F3A5820DC01E3669D4F1B1FA918A98685F1E20977BA13C52C'
REVIEWED_FRAME = dict(init_scope_depth='4', max_scope_depth='5', max_regs='56', max_stack='7')
# Imported private namespace identities must be reviewed from this actual import;
# never inherit another candidate's private map or approvals.
REVIEWED_PRIVATE_MAP = {864: 442, 865: 44}
REVIEWED_BINDINGS_SHA = 'B526D3EEE7D33C4616060EA1BC37B6E5E9936AED47BE796456125C6C0F0DDEFA'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load('fog_last_blocker_minimal_private_audit_engine', B/'bullet-segments-audit.py')
recipe = load('fog_last_blocker_minimal_audit_recipe', OUT/'recipe.py')
engine.CLASS, engine.TARGET, engine.OUT = CLASS, TARGET, OUT
core, require, sha = engine.core, engine.require, engine.sha
BASE_XML, BASE_SWF = engine.BASE_XML, engine.BASE_SWF
original_timer_binding, original_audit = engine.timer_binding, engine.audit


def code_sha(body):
    return hashlib.sha256(bytes.fromhex(body.get('codeBytes'))).hexdigest().upper()


def normalized_namespace(abc, index):
    mapping = REVIEWED_PRIVATE_MAP or {}
    if index in mapping:
        require(engine.private(abc, index) and mapping[index] in (44, 442), 'Invalid reviewed private map')
        return mapping[index], '5', ''
    return index, abc.cp['constant_namespace'][index].get('kind'), engine.namespace_name(abc, index)


def bindings(abc, rows):
    result = {}
    for row in rows:
        for kind, value in row[3]:
            if kind == 'n':
                node = abc.cp['constant_multiname'][value]
                require(node.get('kind') in ('7', '9', '27'), 'Review other multiname kinds explicitly')
                ns, nsset = int(node.get('namespace_index', '0')), int(node.get('namespace_set_index', '0'))
                result['n:'+str(value)] = (node.get('kind'), abc.simple(value),
                    normalized_namespace(abc, ns) if ns else None,
                    sorted(normalized_namespace(abc, n) for n in engine.set_members(abc, nsset)) if nsset else None)
            elif kind == 's':result['s:'+str(value)] = abc.string(value)
            elif kind in ('i', 'q', 'd'):
                result[kind+':'+str(value)] = core.xml_value(abc.cp[core.POOLS[kind]][value])
            elif kind == 'p':result['p:'+str(value)] = normalized_namespace(abc, value)
            elif kind in ('m', 'c'):
                raise AssertionError('Explicit review required for method/class operand '+kind)
    return result


def bindings_sha(abc, rows):
    return hashlib.sha256(json.dumps(bindings(abc, rows), sort_keys=True).encode()).hexdigest().upper()


def body_proof(abc, index):
    require(abc.names_by_method.get(index) == TARGET, 'Wrong approval target')
    body = abc.bodies[index]
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, abc, addresses)
    require(abc.methods[index].get('flags') == '8', 'Exact native HAS_OPTIONAL-only flags required')
    signature = hashlib.sha256(json.dumps(abc.signature(index), sort_keys=True,
        separators=(',', ':')).encode()).hexdigest().upper()
    require(signature == BASE_SIGNATURE_SHA, 'Native return/parameter/optional signature changed')
    require(not list(body.find('traits/traits')) and not list(body.find('exceptions')), 'No catch/activation allowed')
    require(not any(r[2] in (0x40, 0x43, 0x57, 0x5a, 0x6c, 0x6d, 0x6e, 0x6f) for r in rows),
            'Closure/direct-method/activation/catch/numeric-slot instruction needs separate review')
    frame = {k: body.get(k) for k in BASE_FRAME}
    baseline = code_sha(body) == BASE_CODE_SHA
    if baseline:
        require(index == 254 and frame == BASE_FRAME, 'Original lighting identity changed')
    else:
        require(all(x is not None for x in (REVIEWED_CODE_SHA, REVIEWED_FRAME, REVIEWED_PRIVATE_MAP, REVIEWED_BINDINGS_SHA)),
                'Actual import has not been explicitly reviewed')
        require(code_sha(body) == REVIEWED_CODE_SHA and frame == REVIEWED_FRAME, 'Reviewed code/frame drift')
        require(frame['init_scope_depth'] == '4' and frame['max_scope_depth'] == '5', 'Captured scope changed')
        require(bindings_sha(abc, rows) == REVIEWED_BINDINGS_SHA, 'Reviewed operand binding drift')
    return dict(baseline=baseline, codeSHA256=code_sha(body), frame=frame)


def body_operands(abc, index):
    body_proof(abc, index)
    rows, _ = core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    return {v for r in rows for k, v in r[3] if k == 'n'}


def timer_binding(abc, index):
    # Production target must have no diagnostic timer/class-check references.
    rows, _ = core.decode(bytes.fromhex(abc.bodies[index].get('codeBytes')))
    forbidden = {'getTimer', 'getQualifiedClassName'}
    require(not any(abc.simple(value) in forbidden for row in rows for kind, value in row[3] if kind == 'n'),
            'Diagnostic function reference leaked into production target')
    require(not any(abc.string(value) in ('fogLastBlockerEnabled', 'fogLastBlockerProfile', 'fog-last-blocker-1')
                    for row in rows for kind, value in row[3] if kind == 's'),
            'Diagnostic API reference leaked into production target')
    return dict(callCount=0, diagnosticCalls=False, callOffsets=[])


def lexical_map(a, b, old_names, new_names):
    old_sets, old_direct = engine.namespace_uses(a, old_names)
    require(old_sets == {163} and old_direct == {1, 6, 9}, 'Original lighting lexical scope changed')
    original = engine.set_members(a, 163)
    require(original == [1, 421, 6, 43, 9, 16, 44, 42, 443, 442], 'Original namespace identities changed')
    sets, direct = engine.namespace_uses(b, new_names)
    private_used = {n for n in direct if engine.private(b, n)} | {
        n for s in sets for n in engine.set_members(b, s) if engine.private(b, n)}
    new_private = private_used - {44, 442}
    mapping = {}
    if new_private:
        require(REVIEWED_PRIVATE_MAP is not None and set(REVIEWED_PRIVATE_MAP) == new_private,
                'Explicit imported private identity map is missing')
        require(set(REVIEWED_PRIVATE_MAP.values()) == {44, 442}, 'Ambiguous original private identity')
        mapping = dict(REVIEWED_PRIVATE_MAP)
        require(all(k >= len(a.cp['constant_namespace']) and engine.private(b, k) for k in mapping),
                'Cannot rebind existing/non-private namespace')
    evidence = []
    for s in sets:
        members = engine.set_members(b, s)
        if not any(engine.private(b, n) for n in members):continue
        require(len(members) == len(set(members)) and {mapping.get(n, n) for n in members} == set(original),
                'Mapped lexical scope differs')
        evidence.append(dict(candidateSet=s, originalSet=163, exactPrivateMap=mapping))
    require(all(mapping.get(n, n) in {44, 442} for n in private_used), 'Private operand not rebound')
    return mapping, evidence


def strict_audit(base_xml, candidate_xml, base_swf=BASE_SWF, candidate_swf=OUT/'pfe.swf'):
    require(sha(base_xml) == BASE_XML_SHA, 'Exact BEFC XML required')
    result = original_audit(base_xml, candidate_xml, base_swf, candidate_swf)
    require(result['actualChangedBodies'] == [TARGET], 'Exactly lighting must change')
    result.update(preservedOriginalLayout=True, constructorsPreserved=True, importedClassCopied=False,
        reviewedBodySHA256=REVIEWED_CODE_SHA, operandBindingsSHA256=REVIEWED_BINDINGS_SHA)
    return result


engine.body_operands, engine.timer_binding = body_operands, timer_binding
engine.lexical_map, engine.audit = lexical_map, strict_audit


def inspect(path):
    a = core.ABC(ET.parse(BASE_XML).findall('.//abc')[0])
    b = core.ABC(ET.parse(path).findall('.//abc')[0])
    body = b.bodies[b.named[TARGET]]
    rows, addresses = core.decode(bytes.fromhex(body.get('codeBytes')))
    core.Compare.exceptions(body, b, addresses)
    names = {v for r in rows for k, v in r[3] if k == 'n'}
    sets, direct = engine.namespace_uses(b, names)
    ns = direct | {n for s in sets for n in engine.set_members(b, s)}
    return dict(inspected=True, passed=False, runtimeReady=False, reviewRequired=True, target=TARGET,
        baseline=body_proof(a, a.named[TARGET]), importedXMLSHA256=sha(path), importedCodeSHA256=code_sha(body),
        frame={k:v for k,v in body.attrib.items() if k != 'codeBytes'}, methodMetadata=b.methods[b.named[TARGET]].attrib,
        activation=[x.attrib for x in body.find('traits/traits')], exceptions=[x.attrib for x in body.find('exceptions')],
        namespaceSets={str(s):engine.set_members(b, s) for s in sets},
        namespaces={str(n):dict(name=engine.namespace_name(b, n), **b.cp['constant_namespace'][n].attrib) for n in ns},
        timerBinding=timer_binding(b, b.named[TARGET]), instructions=rows,
        operandBindings=bindings(b, rows), operandBindingsSHA256=bindings_sha(b, rows),
        requiredReview=['Non-scene or ineligible rays preserve the complete BEFC typed loop and writes; legacy branch unchanged',
            'Cached step is an actual fully opaque native sample; predictions preserve N, diagonal perturbation and both int conversions',
            'Only this.grafon.sceneLarge and original bounded/interior rays use cache; effective native water opacity, not water presence, seeds it',
            'Hit sets only local brightness zero; all original tile/pixel writes remain, including equivalent zero writes for negative visi',
            'relight_t assignment, active return, all state/pixel writes and native arithmetic unchanged',
            'No new API, timer, counters, imports, persistent cache or class members; only four local values',
            'Explicit private namespace identities, registers and no catch/activation/closures',
            'Retain must reject any imported class layout drift; never copy imported constructors'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate', type=Path, default=OUT/'compiled.xml')
    p.add_argument('--candidate-swf', type=Path, default=OUT/'pfe.swf')
    p.add_argument('--out', type=Path, required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument('--inspect-import', action='store_true')
    g.add_argument('--retain', action='store_true')
    g.add_argument('--splice-abc', action='store_true')
    x = p.parse_args()
    require(x.out.resolve().is_relative_to(OUT.resolve()), 'Isolated output only')
    require(sha(BASE_XML) == BASE_XML_SHA, 'Exact BEFC XML required')
    if x.inspect_import:result = inspect(x.candidate)
    elif x.retain:
        require(REVIEWED_IMPORT_XML_SHA is not None and sha(x.candidate) == REVIEWED_IMPORT_XML_SHA,
                'Actual import is unreviewed')
        result = engine.retain(BASE_XML, x.candidate, x.out)
    elif x.splice_abc:result = engine.splice_abc(BASE_XML, x.candidate, BASE_SWF, x.candidate_swf, x.out)
    else:result = strict_audit(BASE_XML, x.candidate, BASE_SWF, x.candidate_swf)
    result.update(diagnosticOnly=False, productionCandidate=True, performanceEligible=False, wrapperSHA256=sha(Path(__file__)))
    if not (x.retain or x.splice_abc):
        require(x.out.suffix == '.json', 'Report must be JSON')
        x.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('instructions','operandBindings','unchangedMethodBodySHA256')}, ensure_ascii=False))


if __name__ == '__main__':main()
