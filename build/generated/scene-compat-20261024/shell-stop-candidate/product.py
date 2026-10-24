"""Exact A796 candidate staging/splicing/audit. Never installs or launches AIR."""
from pathlib import Path
from itertools import zip_longest
import copy
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
B = HERE.parents[2]


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


plan = load('shell_stop_frozen_plan', HERE / 'audit.py')
engine = load('shell_stop_binary_support', B / 'bullet-segments-audit.py')
core, sha = plan.core, plan.sha
BASE, HOST, XML, TARGET = plan.BASE, plan.HOST, plan.XML, plan.TARGET
PLAN_SHA = '79D533FC73169200E0BD5495CC681724CD1C35B40CE946B4F538F807160101A2'
PROOF_SHA = '571147F4D6AB8560E70981F46A423ACF7195253D9940B5C7CE030CA191F9969D'
VERSION = 'shell-stop-candidate-1'


def frozen():
    assert sha(HERE / 'audit.py') == PLAN_SHA
    assert sha(HERE / 'static-proof.json') == PROOF_SHA
    assert sha(BASE / 'pfe.swf') == HOST and sha(BASE / 'pfe.xml') == XML
    proof = json.loads((HERE / 'static-proof.json').read_text(encoding='utf-8'))
    code, _ = plan.candidate_code()
    assert proof['candidateCodeBytes'] == code.hex() and proof['hostSHA256'] == HOST
    assert proof['target'] == TARGET and plan.stack_proof()['changedFrameAttributes'] == []
    return code


def appended_nodes(abc):
    string = copy.deepcopy(abc.cp['constant_string'][1]); string.text = 'visualGilza'
    name = copy.deepcopy(abc.cp['constant_multiname'][plan.Q['vis']])
    name.set('name_index', str(plan.CP_STRING))
    assert name.get('kind') == '7' and name.get('namespace_index') == '1'
    return string, name


def compare_abc(old, new, index):
    """Remove only the reviewed additions, then require exact complete ABC XML."""
    a, b = core.ABC(old), core.ABC(new)
    assert a.named == b.named and a.class_by_name == b.class_by_name
    assert set(a.bodies) == set(b.bodies)
    changed = 0
    if index == 0:
        assert a.named[TARGET] == b.named[TARGET] == plan.METHOD
        before, after = a.bodies[plan.METHOD], b.bodies[plan.METHOD]
        assert bytes.fromhex(before.get('codeBytes')) == plan.OLD
        assert bytes.fromhex(after.get('codeBytes')) == plan.candidate_code()[0]
        assert {k:v for k,v in after.attrib.items() if k != 'codeBytes'} == plan.FRAME
        assert not list(after.find('exceptions')) and not list(after.find('traits/traits'))
        after.set('codeBytes', before.get('codeBytes'))
        expected = appended_nodes(a)
        for pool, index_expected, added in zip(('constant_string', 'constant_multiname'),
                                              (plan.CP_STRING, plan.CP_QNAME), expected):
            original_pool, new_pool = old.find('constants/' + pool), new.find('constants/' + pool)
            assert len(original_pool) == index_expected and len(new_pool) == index_expected + 1
            assert core.xml_value(new_pool[-1], {'bytes', 'fileOffset'}) == core.xml_value(added, {'bytes', 'fileOffset'})
            new_pool.remove(new_pool[-1])
        changed = 1
    else:
        assert index == 1 and TARGET not in a.named
    # Includes all method signatures/bodies, fields, classes, script initializers,
    # namespace identities and untouched pool entries; not just named methods.
    assert core.xml_value(old, {'bytes', 'fileOffset'}) == core.xml_value(new, {'bytes', 'fileOffset'})
    return len(a.bodies) - changed, len(a.class_by_name), changed


def audit_xml(candidate):
    counts = [0, 0, 0]; blocks = 0
    for index, pair in enumerate(zip_longest(plan.abcs(BASE / 'pfe.xml'), plan.abcs(candidate))):
        old, new = pair; assert old is not None and new is not None
        values = compare_abc(old, new, index)
        counts = [a + b for a, b in zip(counts, values)]; blocks += 1
    assert blocks == 2 and counts == [5770, 1016, 1], (blocks, counts)
    return dict(unchangedMethodBodies=counts[0], unchangedClassLayouts=counts[1],
                actualChangedBodies=[TARGET], otherABCXMLPreserved=True)


def raw_pools(tag):
    """Read raw AVM2 pool entry encodings; no normalization/rebinding."""
    data = tag[1][len(engine.abc_prefix(tag)):]; pos = 4
    assert len(data) >= 4

    def number():
        nonlocal pos
        value = 0
        for shift in range(0, 35, 7):
            assert pos < len(data); byte = data[pos]; pos += 1
            value |= (byte & 127) << shift
            if byte < 128: return value
        raise AssertionError('Overlong ABC integer')

    pools = {}
    for pool in ('int', 'uint', 'double', 'string', 'namespace', 'namespace_set', 'multiname'):
        start = pos; count = number(); count_bytes = data[start:pos]; entries = []
        for unused in range(1, count):
            start = pos
            if pool in ('int', 'uint'): number()
            elif pool == 'double': pos += 8
            elif pool == 'string':
                size = number(); pos += size
            elif pool == 'namespace':
                pos += 1; number()
            elif pool == 'namespace_set':
                for unused2 in range(number()): number()
            else:
                assert pos < len(data); kind = data[pos]; pos += 1
                if kind in (7, 13, 9, 14): number(); number()
                elif kind in (15, 16, 27, 28): number()
                elif kind in (17, 18): pass
                elif kind == 29:
                    number()
                    for unused2 in range(number()): number()
                else: raise AssertionError(('Unsupported multiname kind', kind))
            assert pos <= len(data); entries.append(data[start:pos])
        pools[pool] = dict(count=count, countBytes=count_bytes, entries=entries)
    return data[:4], pools


def binary_pool_audit(base_tag, candidate_tag):
    av, a = raw_pools(base_tag); bv, b = raw_pools(candidate_tag)
    assert av == bv
    expected = {'string': bytes(plan.u30(11)) + b'visualGilza',
                'multiname': bytes([7, 1]) + bytes(plan.u30(plan.CP_STRING))}
    assert a['string']['count'] == plan.CP_STRING and a['multiname']['count'] == plan.CP_QNAME
    for pool, original in a.items():
        other = b[pool]
        if pool in expected:
            assert other['count'] == original['count'] + 1
            assert other['countBytes'] == bytes(plan.u30(other['count']))
            assert other['entries'][:-1] == original['entries'] and other['entries'][-1] == expected[pool]
        else:
            assert original == other, ('Untouched raw constant pool changed', pool)
    return dict(originalConstantPoolPrefixBytesPreserved=True, addedStringIndex=plan.CP_STRING,
                addedPublicQNameIndex=plan.CP_QNAME, newConstants=2, newNamespaces=0)


def stage():
    code = frozen(); output = HERE / 'retained.xml'
    assert not output.exists(), 'Keep previous stage evidence'
    tree = ET.parse(BASE / 'pfe.xml'); nodes = tree.findall('.//abc')
    assert len(nodes) == 2; a = core.ABC(nodes[0])
    assert a.named[TARGET] == plan.METHOD and bytes.fromhex(a.bodies[plan.METHOD].get('codeBytes')) == plan.OLD
    assert len(a.cp['constant_string']) == plan.CP_STRING and len(a.cp['constant_multiname']) == plan.CP_QNAME
    for pool, value in zip(('constant_string', 'constant_multiname'), appended_nodes(a)):
        nodes[0].find('constants/' + pool).append(value)
    a.bodies[plan.METHOD].set('codeBytes', code.hex())
    tree.write(output, encoding='utf-8', xml_declaration=True)
    del tree, nodes, a
    return dict(version=VERSION, base=HOST, baseXML=XML, target=TARGET,
                retainedXML=sha(output), staticProofSHA256=PROOF_SHA, **audit_xml(output))


def splice():
    frozen(); xml_check = audit_xml(HERE / 'serialized.xml')
    sig, header, old = engine.raw_swf(BASE / 'pfe.swf')
    dsig, dheader, donor = engine.raw_swf(HERE / 'serialized.swf')
    assert sig[3:] == dsig[3:] and header == dheader
    assert len(old) == len(donor) and [t[0] for t in old] == [t[0] for t in donor]
    ids = [i for i,t in enumerate(old) if t[0] in (72, 82)]; assert len(ids) == 2
    for i in ids: assert engine.abc_prefix(old[i]) == engine.abc_prefix(donor[i])
    target = ids[0]; pools = binary_pool_audit(old[target], donor[target])
    assert old[target][1] != donor[target][1]
    tags = [donor[i][2] if i == target else old[i][2] for i in range(len(old))]
    body = header + b''.join(tags); output = HERE / 'pfe.swf'
    assert not output.exists() and output.resolve().parent == HERE.resolve()
    output.write_bytes(sig + (len(body) + 8).to_bytes(4, 'little') +
                       (zlib.compress(body, 9) if sig[:3] == b'CWS' else body))
    fs, fh, final = engine.raw_swf(output)
    assert fs == sig and fh == header and [t[2] for t in final] == tags
    return dict(passed=True, base=HOST, candidate=sha(output), donor=sha(HERE / 'serialized.swf'),
                donorXML=sha(HERE / 'serialized.xml'), targetABCIndex=0, targetTagIndex=target,
                preservedRawTags=len(old)-1, finalExportAndAuditRequired=True, **xml_check, **pools)


def audit():
    frozen(); result = audit_xml(HERE / 'pfe.xml')
    sig, header, old = engine.raw_swf(BASE / 'pfe.swf')
    nsig, nheader, new = engine.raw_swf(HERE / 'pfe.swf')
    ids = [i for i,t in enumerate(old) if t[0] in (72, 82)]
    assert len(ids) == 2 and sig == nsig and header == nheader and len(old) == len(new)
    target = ids[0]
    assert engine.abc_prefix(old[target]) == engine.abc_prefix(new[target])
    assert old[target][0] == new[target][0] and old[target][1] != new[target][1]
    assert all(a[2] == b[2] for i,(a,b) in enumerate(zip(old,new)) if i != target)
    assert engine.support.swf_envelope(BASE / 'pfe.swf') == engine.support.swf_envelope(HERE / 'pfe.swf')
    pools = binary_pool_audit(old[target], new[target])
    return dict(version=VERSION, passed=True, auditTarget=TARGET, baseSHA256=HOST, baseXMLSHA256=XML,
                candidateSHA256=sha(HERE / 'pfe.swf'), candidateXMLSHA256=sha(HERE / 'pfe.xml'),
                wrapperSHA256=sha(Path(__file__)), frozenPlanSHA256=PLAN_SHA, staticProofSHA256=PROOF_SHA,
                addedFields=[], addedMethods=[], constructorsPreserved=True, preservedOriginalLayout=True,
                methodAndClassIndicesPreserved=True, originalPrivateIdentitiesPreserved=True,
                originalBranchesPreserved=True, originalRandomCallsPreserved=True,
                untouchedRawTagsPreserved=True, otherABCRawTagPreserved=True, nonABCSWFEnvelopePreserved=True,
                runtimeVerified=False, performanceEligible=False, deployed=False, **result, **pools)


if __name__ == '__main__':
    actions = {'stage': (stage, 'stage.json'), 'splice': (splice, 'splice.json'), 'audit': (audit, 'semantic-audit.json')}
    action = sys.argv[1]; function, filename = actions[action]
    output = HERE / filename; assert not output.exists(), 'Preserve earlier evidence'
    result = function(); output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(step=action, passed=True, receipt=str(output), sha256=sha(output))), flush=True)
