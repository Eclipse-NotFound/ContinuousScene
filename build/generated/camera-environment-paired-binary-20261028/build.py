"""Build one diagnostic A/B host by exact byte edits; no XML, Java or AIR.

Only --build writes artifacts, exclusively in this script's directory.
--check-only performs the same in-memory transform/audit without writing files.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse
import ast
import hashlib
import json
import sys
import zlib

sys.dont_write_bytecode = True
from raw_abc import RawABC, require, u30
from resources import ResourceGuard

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SOURCE = ROOT / 'pfe.swf'
PAIRED = HERE.parent / 'camera-environment-paired-20261028'
CORE = HERE.parents[1] / 'native-crop-audit.py'
F15_PROOF = HERE.parent / 'camera-environment-keycache-20261027/stage-proof.json'
ORIGIN_SHA = 'A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
BASE_SHA = '4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75'
ORIGIN = HERE.parents[1] / 'backups/alicorn-20261028-121734-7ee3b24f/pfe.swf'
DEPLOYMENT = HERE.parents[2] / 'state/alicorn-alert-deployment-20261028.json'
DEPLOYMENT_AUDIT = HERE.parent / 'alicorn-alerts-20261028/audit.json'
BASE_POOLS = dict(int=126,uint=0,double=102,string=8173,namespace=868,nsset=185,multiname=9717)
ALICORN_METHODS = {1940: 'budilo',1941: 'telepat',1943: 'alarma',1945: 'setNull',1947: 'control'}
ALICORN_METHOD_INFOS = {
    1940: ('01000f0008011703','01000fe13f08011703'),
    1941: ('00000000','0000e73f00'),
    1943: ('02000f0f00080202030203','02000f0fe93f080202030203'),
    1945: ('0100010008010a0a','010001ec3f08010a0a'),
    1947: ('00000000','0000ea3f02'),
}
ALICORN_SUFFIXES = {
    'string': (8161,8173,'8E947C96323E759F97006E5BB26B77A51244E1793EAB19A1F06B056C9C32268C'),
    'nsset': (183,185,'4B1A9EF062F90B4AAE884875C75FAE614CEF10B4AF0DD154056D6B227073920F'),
    'multiname': (9705,9717,'D9E62650A82F9FB6B9A6F8C6196D9EF4E2C8ADF117849E92284735E47EFA2F86'),
}
ALICORN_STRINGS = ['fe.unit:UnitAlicorn/budilo','sceneGraph','sceneBounded','sceneHalfWidth',
    'sceneHalfHeight','alicornAllow','fe.unit:UnitAlicorn/telepat','alicornReceive',
    'fe.unit:UnitAlicorn/alarma','fe.unit:UnitAlicorn/control','alicornClear','fe.unit:UnitAlicorn/setNull']
OLD_CODE_SHA = 'BF4AF7FF4B66C3C999EF16A7293A090CB12A6B66C4B7F680620E5F4F241DC934'
TARGET = 'fe.graph.Grafon::0:1:sceneNativeEnvironment'
METHOD = 3253
NAMES = ('_csEnvironmentCellKeysV1', '_csUseEnvironmentKeyCacheV1')
PINS = {
    PAIRED / 'audit.py': '96F1C76BC74F708778A34FD61F9EFCAC5CF41492CDB9F5397FFBDBD8F2CCB7FF',
    CORE: 'AC4383A6FA899EE62CAA54282AE6F31E5DDB83CEBABFC65A920EA5954F0F46DE',
    F15_PROOF: 'E10FE316EFE4BD41B0F50693B4A625626D4008754AB940614E2E916ECFDEF88C',
    ORIGIN: ORIGIN_SHA,
    DEPLOYMENT: '2B2CBB6A7D79DC8CBB8FF52FD94CA3B9B7E5445B7BEFF251703B1056B5AB6BB3',
    DEPLOYMENT_AUDIT: '73AB8EDA0701CBF492C249F86C76F700765A5CF7110F4F78662F5265322C49EB',
}


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest().upper()


def source_inputs():
    for path, expected in PINS.items():
        require(sha(path) == expected, 'Reviewed input changed: ' + str(path))
    paths = [HERE / p for p in ('build.py', 'raw_abc.py', 'resources.py', 'README.md')]
    return {str(p): sha(p) for p in [*paths, *PINS]}


class RawSWF:
    """Span-based equivalent of bullet-segments-audit.raw_swf; no tag copies."""
    def __init__(self, path):
        require(Path(path).stat().st_size <= 32 * 1024**2, 'Unexpected SWF file size')
        raw = Path(path).read_bytes()
        require(len(raw) >= 12 and raw[:3] in (b'FWS', b'CWS'), 'Unsupported SWF signature')
        self.sha256 = digest(raw)
        self.signature = raw[:4]
        size = int.from_bytes(raw[4:8], 'little')
        require(12 <= size <= 128 * 1024**2, 'Unexpected expanded SWF size')
        if raw[:3] == b'CWS':
            decoder = zlib.decompressobj()
            body = decoder.decompress(memoryview(raw)[8:], size - 8 + 1)
            require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
                    'Invalid compressed SWF envelope')
        else:
            body = raw[8:]
        require(len(body) + 8 == size, 'Invalid expanded SWF length')
        self.body = memoryview(body)
        pos = (5 + 4 * (body[0] >> 3) + 7) // 8 + 4
        require(pos <= len(body), 'Truncated SWF frame header')
        self.frame_end = pos
        self.tags = []
        ended = False
        while pos < len(body):
            start = pos
            require(pos + 2 <= len(body), 'Truncated SWF tag header')
            record = int.from_bytes(body[pos:pos+2], 'little')
            pos += 2
            kind, size = record >> 6, record & 63
            if size == 63:
                require(pos + 4 <= len(body), 'Truncated SWF long header')
                size = int.from_bytes(body[pos:pos+4], 'little')
                pos += 4
            payload_start = pos
            pos += size
            require(pos <= len(body), 'Truncated SWF tag payload')
            self.tags.append((kind, start, payload_start, pos))
            if kind == 0:
                require(size == 0 and pos == len(body), 'Invalid SWF End tag')
                ended = True
                break
        require(ended, 'Missing SWF End tag')

    def raw_tag(self, index):
        _, start, _, end = self.tags[index]
        return self.body[start:end]

    def abc(self, index):
        kind, _, start, end = self.tags[index]
        require(kind in (72, 82), 'Expected ABC tag')
        at = start
        if kind == 82:
            require(start + 5 <= end, 'Truncated DoABC prefix')
            at += 4
            while at < end and self.body[at]:
                at += 1
            require(at < end, 'Unterminated DoABC name')
            at += 1
        return self.body[start:at], self.body[at:end]


def reviewed_algorithm(abc):
    """Execute only exact reviewed decoder/patch function ASTs, not module imports.

    In particular, prior.original is replaced before any algorithm runs. Neither
    original audit module nor its XML parser/import chain is executed.
    """
    source = CORE.read_text('utf-8-sig')
    tree = ast.parse(source, str(CORE))
    start = next(n.lineno for n in tree.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'OPS' for t in n.targets))
    decoder = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'decode')
    nodes = [n for n in tree.body if start <= n.lineno <= decoder.lineno]
    scope = {'require': require}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(CORE), 'exec'), scope)
    core = SimpleNamespace(decode=scope['decode'])
    data = abc.code(METHOD)
    rows, _ = core.decode(data)
    require(len(data) == 205 and digest(data) == OLD_CODE_SHA, 'Original method bytes differ')
    require(abc.qualified(4720) == 'Math' and abc.simple(5071) == 'max' and abc.string(5107) == ':',
            'Original Math/max/separator bindings differ')
    require(abc.qualified(26) == 'Array' and abc.qualified(10) == 'String', 'Array/String binding differs')
    require(abc.namespaces[1][0] == 22 and abc.string(abc.namespaces[1][1]) == '', 'Public namespace differs')
    dynamic = abc.binding(8883)
    require(dynamic['kind'] == 27 and any(n.get('kind') == 22 and n.get('name') == ''
            for n in dynamic['namespaces']), 'Array dynamic lookup is not public MultinameL')
    for lo, hi, local in ((73, 83, 0xd2), (100, 110, 0xd3)):
        picked = [(op, args) for a, b, op, args in rows if lo <= a < hi]
        require(picked == [(0x60, [('n', 4720)]), (0x24, [('b', 0)]), (local, []),
                           (0x46, [('n', 5071), ('u', 2)])], 'Original clamp instructions differ')
    original = lambda: (None, abc, None, data, rows)
    path = PAIRED / 'audit.py'
    tree = ast.parse(path.read_text('utf-8-sig'), str(path))
    wanted = {'check_stack', 'cached_key_code', 'key_code', 'patched'}
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    require({n.name for n in functions} == wanted and len(functions) == 4, 'Patch functions changed')
    qname = abc.pools['multiname'].count
    scope = dict(prior=SimpleNamespace(original=original), core=core, QNAME=qname, SWITCH_QNAME=qname+1)
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), scope)
    cached, key, patched = scope['cached_key_code'](), scope['key_code'](), scope['patched']()
    require((len(cached), len(key), len(patched)) == (274, 339, 493), 'Unexpected patch lengths')
    require(key[10:10+274] == cached and key[-51:] == data[66:117], 'A/B blocks not retained')
    f15 = json.loads(F15_PROOF.read_text('utf-8-sig'))
    require(f15['base'] == ORIGIN_SHA and f15['oldCodeSHA256'] == digest(data), 'F15 origin receipt differs')
    # Reconstruct the historical F15 method against the unchanged 205-byte body.
    # Only its cache QName must relocate for the current append-only constant pool.
    legacy = dict(prior=SimpleNamespace(original=original),core=core,QNAME=9705,SWITCH_QNAME=9706)
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(path),'exec'),legacy)
    old_cached = legacy['cached_key_code']()
    legacy['key_code'] = legacy['cached_key_code']
    require(digest(legacy['patched']()) == f15['newCodeSHA256'], 'Historical F15 code receipt differs')
    old_rows, _ = core.decode(old_cached)
    new_rows, _ = core.decode(cached)
    require(new_rows == [(lo,hi,op,[(kind,qname if kind=='n' and value==9705 else value)
            for kind,value in args]) for lo,hi,op,args in old_rows], 'Cached algorithm changed beyond QName relocation')
    origin = dict(baseSHA256=ORIGIN_SHA,stageProofSHA256=sha(F15_PROOF),
                  historicalMethodSHA256=f15['newCodeSHA256'],oldQName=9705,currentQName=qname,
                  onlyCacheQNameRelocated=True,historicalCachedKeySHA256=digest(old_cached),
                  currentCachedKeySHA256=digest(cached))
    return patched, core, scope['check_stack'](key), rows, origin


def edit_bytes(original, edits):
    """Return edited bytes and an exact inverse edit list, without full-tree serialization."""
    view = memoryview(original)
    chunks, inverse, cursor, delta = [], [], 0, 0
    for start, end, replacement, label in sorted(edits):
        require(cursor <= start <= end <= len(view), 'Overlapping/out-of-range edit')
        chunks.extend((view[cursor:start], replacement))
        inverse.append((start+delta, start+delta+len(replacement), bytes(view[start:end]), label))
        delta += len(replacement) - (end-start)
        cursor = end
    chunks.append(view[cursor:])
    return b''.join(chunks), inverse


def verify_baseline_evolution(current_swf, current, abc_indices):
    """Independently reverse the five-method A796 -> 4E5F deployment in memory."""
    deployment = json.loads(DEPLOYMENT.read_text('utf-8-sig'))
    published = json.loads(DEPLOYMENT_AUDIT.read_text('utf-8-sig'))
    require(deployment['host'] == BASE_SHA and deployment['priorHost'] == ORIGIN_SHA and
            deployment['version'] == '0.9.1' and deployment['installedReadbackPassed'], 'Deployment lineage differs')
    require(Path(deployment['backup']).resolve() == ORIGIN.parent.resolve(), 'Deployment backup differs')
    require(deployment['auditSHA256'] == sha(DEPLOYMENT_AUDIT) and published['ok'] and
            published['base'] == ORIGIN_SHA and published['host'] == BASE_SHA, 'Published host audit differs')
    old_swf = RawSWF(ORIGIN)
    require(old_swf.sha256 == ORIGIN_SHA and current_swf.sha256 == BASE_SHA, 'Pinned evolution host differs')
    require(old_swf.signature == current_swf.signature and
            old_swf.body[:old_swf.frame_end] == current_swf.body[:current_swf.frame_end], 'Evolution changed frame header')
    require(len(old_swf.tags) == len(current_swf.tags), 'Evolution changed tag count')
    for i,(old_tag,new_tag) in enumerate(zip(old_swf.tags,current_swf.tags)):
        require(old_tag[0] == new_tag[0], 'Evolution changed tag order/type')
        if i != abc_indices[0]:
            require(old_swf.raw_tag(i) == current_swf.raw_tag(i), 'Evolution changed another raw tag')
        else:
            require(old_swf.abc(i)[0] == current_swf.abc(i)[0], 'Evolution changed DoABC prefix')
    origins = [RawABC(old_swf.abc(i)[1]) for i in abc_indices]
    records = []
    unchanged = classes = 0
    inverse = []
    pool_changes = []
    method_info_changes = []
    for number,(old,new) in enumerate(zip(origins,current)):
        require(old.named == new.named and old.class_by_name == new.class_by_name and
                set(old.bodies) == set(new.bodies), 'Evolution changed ABC identities')
        require(len(old.methods) == len(new.methods), 'Evolution changed method-info count')
        for method,(a,b) in enumerate(zip(old.methods,new.methods)):
            old_info,new_info = old.raw(a),new.raw(b)
            if old_info == new_info:
                continue
            require(number == 0 and method in ALICORN_METHOD_INFOS and
                    (bytes(old_info).hex(),bytes(new_info).hex()) == ALICORN_METHOD_INFOS[method],
                    'Evolution changed an unapproved method-info byte')
            inverse.append((b[0],b[1],bytes(old_info),'restore-method-info-'+str(method)))
            method_info_changes.append(dict(method=method,oldHex=bytes(old_info).hex(),
                currentHex=bytes(new_info).hex(),parameterReturnAndDefaultsPreserved=True,
                debugNameAdded=True,needActivationAdded=(method==1947)))
        require(old.class_count == new.class_count, 'Evolution changed class count')
        for a,b in zip(old.instances,new.instances):
            require(old.raw(a) == new.raw(b), 'Evolution changed instance layout')
        for a,b in zip(old.classes,new.classes):
            require(old.raw(a) == new.raw(b), 'Evolution changed static layout')
        classes += old.class_count
        if number == 0:
            require({name:p.count for name,p in new.pools.items()} == BASE_POOLS, 'Evolution current pool counts differ')
            for name,a in old.pools.items():
                b = new.pools[name]
                prefix_end = b.entries_start+a.end-a.entries_start
                require(old.data[a.entries_start:a.end] == new.data[b.entries_start:prefix_end],
                        'Evolution changed old constant bytes')
                if name in ALICORN_SUFFIXES:
                    expected_old,expected_new,suffix_sha = ALICORN_SUFFIXES[name]
                    suffix = new.data[prefix_end:b.end]
                    require((a.count,b.count) == (expected_old,expected_new) and digest(suffix) == suffix_sha,
                            'Evolution appended constants differ')
                    inverse.extend(((b.count_start,b.entries_start,u30(a.count),name+'-old-count'),
                                    (prefix_end,b.end,b'',name+'-remove-suffix')))
                    pool_changes.append(dict(pool=name,oldCount=a.count,newCount=b.count,
                                             appendedBytes=len(suffix),appendedSHA256=suffix_sha))
                else:
                    require(a.count == b.count and prefix_end == b.end, 'Unapproved evolution pool addition')
            require([new.string(i) for i in range(8161,8173)] == ALICORN_STRINGS, 'Alicorn added strings differ')
        else:
            require(old.data == new.data, 'Evolution changed secondary ABC')
        for method,a in old.bodies.items():
            b = new.bodies[method]
            old_raw,new_raw = old.data[a.start:a.end],new.data[b.start:b.end]
            if old_raw == new_raw:
                unchanged += 1
                continue
            require(number == 0 and method in ALICORN_METHODS, 'Evolution changed an unapproved method')
            label = 'fe.unit.UnitAlicorn::0:1:' + ALICORN_METHODS[method]
            require(old.named.get(label) == new.named.get(label) == method, 'Alicorn method binding differs')
            inverse.append((b.start,b.end,bytes(old_raw),'restore-'+label))
            records.append(dict(method=method,name=label,oldCodeSHA256=digest(old.code(method)),
                currentCodeSHA256=digest(new.code(method)),currentBodySHA256=digest(new_raw),
                oldCodeBytes=a.code_end-a.code_start,currentCodeBytes=b.code_end-b.code_start))
    require({r['method'] for r in records} == set(ALICORN_METHODS) and unchanged == 5766 and classes == 1016,
            'Evolution five-method inventory differs')
    require({r['method'] for r in method_info_changes} == set(ALICORN_METHOD_INFOS),
            'Evolution method-info inventory differs')
    require(sorted(r['name'] for r in records) == published['methods'], 'Published changed-method list differs')
    recovered,_ = edit_bytes(current[0].data,inverse)
    require(recovered == origins[0].data, 'Evolution reverse edits did not restore entire A796 ABC')
    require(current[0].code(METHOD) == origins[0].code(METHOD) and
            digest(current[0].code(METHOD)) == OLD_CODE_SHA, 'Grafon changed across baseline evolution')
    return dict(priorHostSHA256=ORIGIN_SHA,currentHostSHA256=BASE_SHA,deploymentReceiptSHA256=sha(DEPLOYMENT),
        publishedAuditSHA256=sha(DEPLOYMENT_AUDIT),independentRawABCAudit=True,
        changedMethods=records,changedMethodInfo=method_info_changes,
        unchangedBodies=unchanged,unchangedClasses=classes,
        originalConstantPoolPrefix=True,appendedPools=pool_changes,appendedStrings=ALICORN_STRINGS,
        inverseRestoredEntirePriorABC=True,priorABCSHA256=digest(origins[0].data),
        recoveredPriorABCSHA256=digest(recovered),secondaryABCExact=True,otherRawTagsExact=True,
        grafonCodeBytes=205,grafonCodeSHA256=OLD_CODE_SHA,
        currentAlicornMethodsMustRemainByteExact=True)


def transform(abc):
    require({key:value.count for key,value in abc.pools.items()} == BASE_POOLS, 'Current 4E5F pool anchors differ')
    string_index,qname = abc.pools['string'].count,abc.pools['multiname'].count
    require(all(name.encode('utf-8') not in abc.strings for name in NAMES), 'Diagnostic names already present')
    require(abc.named.get(TARGET) == METHOD, 'Target is not the expected Grafon instance method')
    old = abc.bodies[METHOD]
    require((old.stack, old.registers, old.exceptions, old.traits) == (6, 9, 0, 0), 'Target frame/tail differs')
    patched, core, stack, rows, cache_origin = reviewed_algorithm(abc)
    strings = b''.join(u30(len(n.encode('utf-8'))) + n.encode('utf-8') for n in NAMES)
    names = b''.join(bytes([7]) + u30(1) + u30(index) for index in (string_index,string_index+1))
    body = b''.join(u30(n) for n in (METHOD, 8, 17, old.scope, old.max_scope, len(patched)))
    body += patched + bytes(abc.data[old.tail_start:old.end])
    edits = []
    for pool, addition in (('string', strings), ('multiname', names)):
        p = abc.pools[pool]
        edits.extend(((p.count_start, p.entries_start, u30(p.count+2), pool+'-count'),
                      (p.end, p.end, addition, pool+'-append')))
    edits.append((old.start, old.end, body, 'method-3253'))
    result, inverse = edit_bytes(abc.data, edits)
    reversed_abc, _ = edit_bytes(result, inverse)
    require(reversed_abc == abc.data, 'Inverse edit did not restore the complete original ABC')
    after = RawABC(result)
    for pool in abc.pools:
        a, b = abc.pools[pool], after.pools[pool]
        require(b.count == a.count + (2 if pool in ('string', 'multiname') else 0), 'Unexpected pool count change')
        size = a.end-a.entries_start
        require(abc.data[a.entries_start:a.end] == after.data[b.entries_start:b.entries_start+size], 'Original pool bytes changed')
    require(after.strings[string_index:] == [n.encode('utf-8') for n in NAMES], 'Wrong appended strings')
    require(after.multinames[qname:] == [(7,1,string_index),(7,1,string_index+1)], 'Wrong appended QNames')
    new_rows, _ = core.decode(patched)
    indices = sorted({value for _, _, _, args in rows+new_rows for kind, value in args if kind == 'n'})
    bindings = []
    for index in indices:
        current = after.binding(index)
        if index < qname:
            require(current == abc.binding(index), 'Existing operand binding changed')
        bindings.append(current)
    strings_used = sorted({value for _, _, _, args in rows+new_rows for kind, value in args if kind == 's'})
    for index in strings_used:
        require(abc.strings[index] == after.strings[index], 'Existing string operand changed')
    proof = dict(originalABCSHA256=digest(abc.data), candidateABCSHA256=digest(result),
        reverseRestoredABCSHA256=digest(reversed_abc), inverseRestoredEntireABC=True,
        oldCodeSHA256=OLD_CODE_SHA, newCodeSHA256=digest(patched), oldCodeBytes=205, newCodeBytes=493,
        originalKeyBytes=51, cachedKeyBytes=274, selectorKeyBytes=339, stackProof=stack,
        originalConstantPoolPrefix=True, appendedStringIndices=[string_index,string_index+1],
        appendedQNameIndices=[qname,qname+1],cacheAlgorithmOrigin=cache_origin,
        appendedNames=list(NAMES), bindings=bindings, stringOperandIndices=strings_used,
        edits=[dict(label=label, originalStart=a, originalEnd=b, newBytes=len(v),
                    oldSHA256=digest(abc.data[a:b]), newSHA256=digest(v)) for a,b,v,label in sorted(edits)])
    return result, after, proof


def audit_structures(before, after):
    preserved = classes = 0
    changed = []
    for number, (a, b) in enumerate(zip(before, after)):
        require(a.version == b.version and a.named == b.named and a.class_by_name == b.class_by_name,
                'ABC identities changed')
        require(a.data[a.method_start:a.method_end] == b.data[b.method_start:b.method_end], 'Method signatures changed')
        require(set(a.bodies) == set(b.bodies), 'Method body set changed')
        require(a.class_count == b.class_count, 'Class count changed')
        for x, y in zip(a.instances, b.instances):
            require(a.raw(x) == b.raw(y), 'Instance layout bytes changed')
        for x, y in zip(a.classes, b.classes):
            require(a.raw(x) == b.raw(y), 'Static layout bytes changed')
        classes += a.class_count
        for method, old in a.bodies.items():
            new = b.bodies[method]
            if number == 0 and method == METHOD:
                require((new.stack,new.registers,new.scope,new.max_scope,new.exceptions,new.traits) ==
                        (8,17,old.scope,old.max_scope,0,0), 'Unexpected target frame change')
                require(a.data[old.tail_start:old.end] == b.data[new.tail_start:new.end], 'Target tail changed')
                changed.append(TARGET)
            else:
                require(a.data[old.start:old.end] == b.data[new.start:new.end], 'Unrelated body changed')
                preserved += 1
    require(changed == [TARGET] and preserved == 5770 and classes == 1016, 'Whole-host inventory differs')
    return dict(changed=changed, unchangedBodies=preserved, unchangedClasses=classes,
                originalPrivateIdentities=True, unchangedMethodSignatures=True, unchangedClassBytes=True)


def candidate_chunks(swf, tag_index, new_abc):
    yield swf.body[:swf.frame_end]
    prefix, _ = swf.abc(tag_index)
    payload_length = len(prefix)+len(new_abc)
    kind, start, payload, end = swf.tags[tag_index]
    # A main ABC always uses the original long-header representation.
    require(payload-start == 6, 'Unexpected main ABC tag header representation')
    for i in range(len(swf.tags)):
        if i != tag_index:
            yield swf.raw_tag(i)
        else:
            yield ((kind << 6) | 63).to_bytes(2, 'little') + payload_length.to_bytes(4, 'little')
            yield prefix
            yield new_abc


def write_candidate(path, swf, tag_index, new_abc):
    _, old_abc = swf.abc(tag_index)
    length = len(swf.body)+8+len(new_abc)-len(old_abc)
    with path.open('xb') as stream:
        stream.write(swf.signature + length.to_bytes(4, 'little'))
        compressor = zlib.compressobj(9) if swf.signature[:3] == b'CWS' else None
        for item in candidate_chunks(swf, tag_index, new_abc):
            for at in range(0, len(item), 1024*1024):
                chunk = item[at:at+1024*1024]
                stream.write(compressor.compress(chunk) if compressor else chunk)
        if compressor:
            stream.write(compressor.flush())


def json_write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--build', action='store_true')
    args = parser.parse_args()
    require(__debug__, 'Python -O is unsupported: reviewed algorithm uses assertions')
    require(HERE.name == 'camera-environment-paired-binary-20261028', 'Unexpected output directory')
    outputs = [HERE / name for name in ('pfe.swf','audit-proof.json','build.json')]
    if args.build:
        require(not any(p.exists() for p in outputs), 'Preserve existing output/partial evidence')
    guard = ResourceGuard()
    try:
        inputs = source_inputs()
        require(sha(SOURCE) == BASE_SHA, 'Installed 4E5F host changed')
        swf = RawSWF(SOURCE)
        require(swf.sha256 == BASE_SHA, 'Host changed while being read')
        abc_indices = [i for i,t in enumerate(swf.tags) if t[0] in (72,82)]
        require(len(abc_indices) == 2, 'Expected two ABC tags')
        before = [RawABC(swf.abc(i)[1]) for i in abc_indices]
        require(before[0].named.get(TARGET) == METHOD and TARGET not in before[1].named,
                'Unexpected target ABC/method identity')
        guard.sample('original-parsed')
        evolution = verify_baseline_evolution(swf,before,abc_indices)
        guard.sample('baseline-evolution-audited')
        candidate_abc, after, proof = transform(before[0])
        proof.update(audit_structures(before, [after,before[1]]))
        for record in evolution['changedMethods']:
            body = after.bodies[record['method']]
            require(digest(after.data[body.start:body.end]) == record['currentBodySHA256'],
                    'Diagnostic candidate lost a current Alicorn method')
        proof.update(version='scene-environment-paired-python-direct-abc-2', method='python-direct-abc',
                     passed=True, diagnosticOnly=True, deployed=False, runtimeVerified=False,
                     performanceEligible=False, xmlAudit=False, ffdecUsed=False, baseSHA256=BASE_SHA,
                     sourceInputs=inputs, onlyABCTagChanged=abc_indices[0], abcTagCount=2,
                     baselineEvolution=evolution,currentAlicornMethodsPreserved=5,
                     limitation='Byte-preservation and bounded local stack audit only; AVM2 load/behavior/performance remain unverified.')
        guard.sample('candidate-audited-in-memory')
        require(inputs == source_inputs() and sha(SOURCE) == BASE_SHA, 'Input changed during audit')
        if args.check_only:
            print(json.dumps(dict(checkOnly=True,wroteArtifacts=False,method=proof['method'],
                unchangedBodies=proof['unchangedBodies'],unchangedClasses=proof['unchangedClasses'],
                baseSHA256=BASE_SHA,candidateABCSHA256=proof['candidateABCSHA256'],
                appendedStringIndices=proof['appendedStringIndices'],appendedQNameIndices=proof['appendedQNameIndices'],
                baselineEvolution=evolution,cacheAlgorithmOrigin=proof['cacheAlgorithmOrigin'],
                resources=guard.receipt())), flush=True)
            return
        write_candidate(outputs[0],swf,abc_indices[0],candidate_abc)
        actual = RawSWF(outputs[0])
        require(actual.signature == swf.signature and actual.body[:actual.frame_end] == swf.body[:swf.frame_end],
                'SWF signature/frame header changed')
        require(len(actual.tags) == len(swf.tags), 'SWF tag count changed')
        for i,(left,right) in enumerate(zip(swf.tags,actual.tags)):
            require(left[0] == right[0], 'Tag kind/order changed')
            if i != abc_indices[0]:
                require(swf.raw_tag(i) == actual.raw_tag(i), 'Unrelated raw tag changed')
            else:
                prefix, content = actual.abc(i)
                require(prefix == swf.abc(i)[0] and content == candidate_abc, 'ABC readback differs')
        proof.update(candidateSHA256=actual.sha256, originalRawAssets=True,
                     preservedRawTags=len(swf.tags)-1, candidateReadbackExact=True)
        guard.sample('candidate-readback')
        proof['resources'] = guard.receipt()
        require(inputs == source_inputs() and sha(SOURCE) == BASE_SHA, 'Input changed during build')
        json_write(outputs[1],proof)
        result = dict(version=proof['version'],method=proof['method'],base=BASE_SHA,candidate=actual.sha256,
                      audit=sha(outputs[1]),sourceInputs=inputs,diagnosticOnly=True,deployed=False,
                      runtimeVerified=False,performanceEligible=False,xmlAudit=False,ffdecUsed=False,
                      baselineEvolution=evolution,currentAlicornMethodsPreserved=5,
                      cacheAlgorithmOrigin=proof['cacheAlgorithmOrigin'],resources=guard.receipt())
        require(sha(outputs[0]) == actual.sha256 and sha(SOURCE) == BASE_SHA, 'Final fingerprint changed')
        require(inputs == source_inputs(), 'Final source fingerprint changed')
        json_write(outputs[2],result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('sourceInputs','resources','baselineEvolution')}),flush=True)
    finally:
        guard.close()


if __name__ == '__main__':
    main()
