"""Offline, fail-closed semantic audit for the BEFC display-crop candidate.

No compiler, game process, or SWF writes. Existing constant-pool entries must
remain byte-meaning equivalent. All non-Grafon named bodies/layouts stay exact;
unmodified Grafon methods and recursively referenced anonymous functions must
retain executable instructions, branch targets, signatures, activation traits,
exception tables and frame sizes. Only debug instructions and equivalent pool /
anonymous-method relocations are normalized. Unknown opcodes are rejected.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

B = Path(__file__).resolve().parent
BASE = B / 'generated/fog-typed/pfe.xml'
CANDIDATE = B / 'generated/native-crop-20261021/pfe.xml'
CLASS = 'fe.graph.Grafon'
CHANGED = {'<init>', 'sceneClear', 'sceneDrop', 'sceneCullSurfaces',
           'sceneApply', 'sceneFinishBatch'}
ADDED = {'sceneCropBind', 'sceneCropSync', 'sceneCropRelease'}
FIELDS = {'sceneCropVersion', 'sceneCropPresentation', 'sceneCropCopies', 'sceneCropAllocations', 'sceneCropPool'}


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def xml_value(node, ignored=frozenset()):
    return (node.tag, tuple(sorted((k, v) for k, v in node.attrib.items() if k not in ignored)),
            (node.text or '').strip(), tuple(xml_value(n, ignored) for n in node))


class ABC:
    def __init__(self, node):
        self.node = node
        self.cp = {p.tag: list(p) for p in node.find('constants')}
        self.methods = list(node.find('method_info'))
        self.bodies = {int(n.get('method_info')): n for n in node.find('bodies')}
        self.instances = list(node.find('instance_info'))
        self.statics = list(node.find('class_info'))
        self.named = {}
        self.names_by_method = {}
        self.class_by_name = {}
        for index, (instance, static) in enumerate(zip(self.instances, self.statics)):
            name = self.qualified(int(instance.get('name_index')))
            self.class_by_name[name] = index
            for label, method in [('<init>', instance.get('iinit_index')),
                                  ('<static>', static.get('cinit_index'))]:
                self.add_named(name + '::' + label, int(method))
            for scope, traits in [('0', instance.find('instance_traits/traits')),
                                  ('1', static.find('static_traits/traits'))]:
                for trait in traits:
                    if trait.get('type') == 'TraitMethodGetterSetter':
                        key = name + '::' + scope + ':' + trait.get('kindType') + ':' + self.simple(int(trait.get('name_index')))
                        self.add_named(key, int(trait.get('method_info')))

    def add_named(self, name, index):
        require(name not in self.named, 'Duplicate named method: ' + name)
        self.named[name] = index
        self.names_by_method[index] = name

    def value(self, pool, index):
        require(pool in self.cp and 0 <= index < len(self.cp[pool]), 'Invalid pool index')
        return xml_value(self.cp[pool][index])

    def string(self, index):
        return self.cp['constant_string'][index].text or ''

    def simple(self, index):
        return self.string(int(self.cp['constant_multiname'][index].get('name_index', '0')))

    def qualified(self, index):
        n = self.cp['constant_multiname'][index]
        ns = self.cp['constant_namespace'][int(n.get('namespace_index', '0'))]
        prefix = self.string(int(ns.get('name_index', '0')))
        return (prefix + '.' if prefix else '') + self.simple(index)

    def multiname(self, index):
        n = self.cp['constant_multiname'][index]
        # Index zero is the wildcard. QName/ns-set records retain namespace
        # index identity (especially private namespaces); TypeName duplicates
        # created by FFDec may use new pool slots with identical parameters.
        if n.get('kind') == '29':
            return ('TypeName', self.multiname(int(n.get('qname_index'))),
                    tuple(self.multiname(int(c.text)) for c in n.find('params')))
        return xml_value(n)

    def constant(self, kind, index):
        pools = {1: 'constant_string', 3: 'constant_int', 4: 'constant_uint',
                 6: 'constant_double', 8: 'constant_namespace', 22: 'constant_namespace',
                 23: 'constant_namespace', 24: 'constant_namespace', 25: 'constant_namespace',
                 26: 'constant_namespace', 5: 'constant_namespace'}
        if kind in (0, 10, 11, 12):
            return ('literal', kind, index)
        require(kind in pools, 'Unknown constant kind ' + str(kind))
        return (kind, self.value(pools[kind], index))

    def signature(self, index):
        m = self.methods[index]
        # Method debug names do not affect invocation; parameter names are
        # retained because they are part of reflective method metadata.
        attrs = tuple(sorted((k, v) for k, v in m.attrib.items() if k not in ('name_index', 'ret_type')))
        optional = tuple((n.get('type'), self.constant(int(n.get('value_kind', n.get('kind', '0'))),
                                                     int(n.get('val', n.get('value_index', '0')))))
                         for n in m.find('optional'))
        return (attrs, self.multiname(int(m.get('ret_type'))),
                tuple(self.multiname(int(n.text)) for n in m.find('param_types')),
                optional, tuple(self.string(int(n.text)) for n in m.find('paramNames')))


# Operand schemas. u = unsigned integer, b = byte, j = signed branch offset,
# n = multiname, m = method, c = class, and s/i/q/d/p = typed constant pool.
OPS = {}
for op in [0x01, 0x02, 0x03, 0x07, 0x09, 0x1c, 0x1d, 0x1e, 0x1f,
           0x20, 0x21, 0x23, 0x26, 0x27, 0x28, 0x29, 0x2a, 0x2b, 0x30,
           *range(0x35, 0x3f), 0x47, 0x48, 0x50, 0x51, 0x52, 0x57, 0x64,
           0x69, 0x6b, *range(0x70, 0x79), 0x81, 0x82, 0x83, 0x84, 0x85,
           0x87, 0x88, 0x89, 0x90, 0x91, 0x93, 0x95, 0x96, 0x97,
           *range(0xa0, 0xb2), 0xb3, 0xb4, 0xc0, 0xc1, *range(0xc4, 0xc8),
           *range(0xd0, 0xd8)]:
    OPS[op] = ''
for op in [0x04, 0x05, 0x59, 0x5d, 0x5e, 0x5f, 0x60, 0x61, 0x66, 0x68, 0x6a, 0x80, 0x86, 0xb2]:
    OPS[op] = 'n'
for op in [0x08, 0x25, 0x41, 0x42, 0x49, 0x53, 0x55, 0x56, 0x5a,
           0x62, 0x63, 0x67, 0x6c, 0x6d, 0x6e, 0x6f, 0x92, 0x94, 0xc2, 0xc3, 0xf0, 0xf2]:
    OPS[op] = 'u'
for op in range(0x0c, 0x1b):
    OPS[op] = 'j'
for op in [0x45, 0x46, 0x4a, 0x4c, 0x4e, 0x4f]:
    OPS[op] = 'nu'
OPS.update({0x06: 's', 0x24: 'b', 0x25: 'h', 0x2c: 's', 0x2d: 'i', 0x2e: 'q', 0x2f: 'd',
            0x31: 'p', 0x32: 'uu', 0x40: 'm', 0x43: 'uu', 0x44: 'mu',
            0x58: 'c', 0x65: 'b', 0xef: 'bsbu', 0xf1: 's'})
DEBUG = {0xef, 0xf0, 0xf1, 0xf2}
POOLS = {'s': 'constant_string', 'i': 'constant_int', 'q': 'constant_uint',
         'd': 'constant_double', 'p': 'constant_namespace'}


def decode(data):
    rows = []
    cursor = 0

    def u30(limit=30):
        nonlocal cursor
        value = 0
        for shift in range(0, 35, 7):
            require(cursor < len(data), 'Truncated u30')
            byte = data[cursor]; cursor += 1
            value |= (byte & 127) << shift
            if byte < 128:
                require(value < 1 << limit, 'Invalid encoded integer')
                return value
        raise AssertionError('Overlong u30')

    def s24():
        nonlocal cursor
        require(cursor + 3 <= len(data), 'Truncated s24')
        value = int.from_bytes(data[cursor:cursor + 3], 'little', signed=True)
        cursor += 3
        return value

    while cursor < len(data):
        start = cursor; op = data[cursor]; cursor += 1
        if op == 0x1b:
            default = s24(); count = u30()
            require(count <= len(data), 'Invalid switch count')
            operands = [('target', start + default)]
            operands.extend(('target', start + s24()) for _ in range(count + 1))
        else:
            require(op in OPS, 'Unknown opcode 0x%02x at %d' % (op, start))
            operands = []
            for kind in OPS[op]:
                if kind == 'b':
                    require(cursor < len(data), 'Truncated byte')
                    value = data[cursor]; cursor += 1
                elif kind == 'j':
                    value = s24(); value += cursor; kind = 'target'
                else:
                    # pushshort accepts the sign-extended 32-bit encoding used
                    # by this FFDec export for negative immediate values.
                    value = u30(32 if kind == 'h' else 30)
                operands.append((kind, value))
        rows.append((start, cursor, op, operands))
    # Debug instructions vanish; branches to a debug record resolve to the
    # following executable instruction, not its changing source-byte offset.
    addresses = {len(data): sum(r[2] not in DEBUG for r in rows)}
    index = 0
    for start, end, op, operands in rows:
        addresses[start] = index
        if op not in DEBUG:
            index += 1
    for _, _, _, operands in rows:
        for kind, value in operands:
            if kind == 'target':
                require(value in addresses, 'Branch into instruction operand')
    return rows, addresses


class Compare:
    def __init__(self, before, after):
        self.a, self.b = before, after
        self.visited = set()
        self.anonymous = set()
        self.hashes = {}

    def body(self, old, new, label):
        pair = old, new
        if pair in self.visited:
            return
        self.visited.add(pair)
        a, b = self.a.bodies.get(old), self.b.bodies.get(new)
        require((a is None) == (b is None), label + ': body availability changed')
        require(self.a.signature(old) == self.b.signature(new), label + ': signature changed')
        if a is None:
            return
        for attr in ('max_stack', 'max_regs', 'init_scope_depth', 'max_scope_depth'):
            require(a.get(attr) == b.get(attr), label + ': ' + attr + ' changed')
        rows_a, addr_a = decode(bytes.fromhex(a.get('codeBytes')))
        rows_b, addr_b = decode(bytes.fromhex(b.get('codeBytes')))
        code_a = [r for r in rows_a if r[2] not in DEBUG]
        code_b = [r for r in rows_b if r[2] not in DEBUG]
        require(len(code_a) == len(code_b), label + ': executable instruction count changed')
        canonical = []
        for ordinal, (ra, rb) in enumerate(zip(code_a, code_b)):
            require(ra[2] == rb[2], label + ': opcode changed at ' + str(ordinal))
            require(len(ra[3]) == len(rb[3]), label + ': operand count changed')
            normalized = []
            for (ka, va), (kb, vb) in zip(ra[3], rb[3]):
                require(ka == kb, label + ': operand type changed')
                if ka == 'm':
                    named_a = self.a.names_by_method.get(va)
                    named_b = self.b.names_by_method.get(vb)
                    require(named_a == named_b, label + ': method reference changed')
                    if named_a is None:
                        self.anonymous.add((va, vb))
                        self.body(va, vb, label + '/anonymous@' + str(ordinal))
                        value_a = value_b = ('anonymous', ordinal)
                    else:
                        value_a = value_b = ('method', named_a)
                elif ka == 'n':
                    value_a, value_b = self.a.multiname(va), self.b.multiname(vb)
                elif ka in POOLS:
                    value_a, value_b = self.a.value(POOLS[ka], va), self.b.value(POOLS[ka], vb)
                elif ka == 'target':
                    value_a, value_b = addr_a[va], addr_b[vb]
                elif ka == 'c':
                    value_a = self.a.qualified(int(self.a.instances[va].get('name_index')))
                    value_b = self.b.qualified(int(self.b.instances[vb].get('name_index')))
                else:
                    value_a, value_b = va, vb
                require(value_a == value_b, label + ': operand changed at ' + str(ordinal))
                normalized.append((ka, value_a))
            canonical.append((ra[2], normalized))
        require(self.exceptions(a, self.a, addr_a) == self.exceptions(b, self.b, addr_b), label + ': exceptions changed')
        self.traits(a.find('traits/traits'), b.find('traits/traits'), label + '/activation')
        self.hashes[label] = hashlib.sha256(json.dumps(canonical, ensure_ascii=False).encode()).hexdigest().upper()

    @staticmethod
    def exceptions(body, abc, addresses):
        result = []
        for item in body.find('exceptions'):
            entry = []
            for k, v in sorted(item.attrib.items()):
                if k in ('from', 'to', 'target'):
                    require(int(v) in addresses, 'Exception target is not an instruction boundary')
                    entry.append((k, addresses[int(v)]))
                elif k in ('type_index', 'name_index'):
                    entry.append((k, abc.multiname(int(v))))
                else:
                    entry.append((k, v))
            result.append(entry)
        return result

    def trait(self, node, abc):
        ignored = {'bytes', 'fileOffset', 'method_info', 'function', 'function_index'}
        result = []
        for k, v in sorted(node.attrib.items()):
            if k in ignored:
                continue
            if k in ('name_index', 'type_index'):
                result.append((k, abc.multiname(int(v))))
            else:
                result.append((k, v))
        return (tuple(result), tuple(xml_value(n) for n in node))

    def traits(self, a, b, label):
        require(len(a) == len(b), label + ': trait count changed')
        for i, (x, y) in enumerate(zip(a, b)):
            require(self.trait(x, self.a) == self.trait(y, self.b), label + ': trait layout changed')
            for attr in ('method_info', 'function', 'function_index'):
                if attr in x.attrib or attr in y.attrib:
                    require(attr in x.attrib and attr in y.attrib, label + ': method trait removed')
                    self.body(int(x.get(attr)), int(y.get(attr)), label + '/trait-' + str(i))


def audit(base, candidate):
    old = ET.parse(base).findall('.//abc')
    new = ET.parse(candidate).findall('.//abc')
    require(len(old) == len(new), 'ABC count changed')
    named_count = layouts = methods = anonymous = 0
    hashes = {}
    for abc_number, (oa, ob) in enumerate(zip(old, new)):
        a, b = ABC(oa), ABC(ob)
        for pool, entries in a.cp.items():
            require(pool in b.cp and len(b.cp[pool]) >= len(entries), 'Constant pool shortened')
            for index, item in enumerate(entries):
                require(xml_value(item) == xml_value(b.cp[pool][index]), 'Existing constant changed: ' + pool + ':' + str(index))
        require(set(a.class_by_name) == set(b.class_by_name), 'Class set changed')
        c = Compare(a, b)
        additions = set(b.named) - set(a.named)
        expected_additions = {CLASS + '::0:1:' + name for name in ADDED} if CLASS in a.class_by_name else set()
        require(additions == expected_additions, 'Unexpected added named methods: ' + str(additions))
        require(set(a.named) <= set(b.named), 'Named methods removed')
        for name, old_index in a.named.items():
            new_index = b.named[name]
            short = name.split(':')[-1]
            if name.startswith(CLASS + '::'):
                require(a.signature(old_index) == b.signature(new_index), name + ': Grafon signature changed')
                if short not in CHANGED:
                    c.body(old_index, new_index, name)
                    methods += 1
            else:
                ba, bb = a.bodies.get(old_index), b.bodies.get(new_index)
                require((ba is None) == (bb is None), name + ': body availability changed')
                if ba is not None:
                    require(ba.get('codeBytes') == bb.get('codeBytes'), name + ': non-renderer code changed')
                    require(xml_value(ba, {'method_info', 'fileOffset'}) == xml_value(bb, {'method_info', 'fileOffset'}),
                            name + ': non-renderer body metadata changed')
                require(a.signature(old_index) == b.signature(new_index), name + ': non-renderer signature changed')
                named_count += 1
        for name, ai in a.class_by_name.items():
            bi = b.class_by_name[name]
            for part, x, y in [('instance', a.instances[ai], b.instances[bi]), ('static', a.statics[ai], b.statics[bi])]:
                container = 'instance_traits/traits' if part == 'instance' else 'static_traits/traits'
                if name != CLASS:
                    ignored = {'bytes', 'fileOffset', 'iinit_index', 'cinit_index', 'method_info'}
                    require(xml_value(x, ignored) == xml_value(y, ignored), name + ': class layout changed')
                else:
                    attrs = lambda node: {k: v for k, v in node.attrib.items() if k not in ('iinit_index', 'cinit_index')}
                    require(attrs(x) == attrs(y), 'Grafon class header changed')
                    xa, ya = list(x.find(container)), list(y.find(container))
                    names_a = {a.simple(int(n.get('name_index'))) for n in xa}
                    extra = [n for n in ya if b.simple(int(n.get('name_index'))) not in names_a]
                    expect = FIELDS | ADDED if part == 'instance' else set()
                    require({b.simple(int(n.get('name_index'))) for n in extra} == expect, 'Unexpected Grafon traits')
                    # Preserve existing slot/dispatch order; only explicit new
                    # instance fields and helpers may appear between them.
                    retained = [n for n in ya if b.simple(int(n.get('name_index'))) in names_a]
                    require(len(xa) == len(retained), 'Grafon existing trait count changed')
                    for tx, ty in zip(xa, retained):
                        require(c.trait(tx, a) == c.trait(ty, b), 'Grafon existing trait metadata changed')
            if name != CLASS:
                layouts += 1
        anonymous += len(c.anonymous)
        hashes.update(c.hashes)
    return dict(passed=True, baseXML=str(base), candidateXML=str(candidate),
                baseXMLSHA256=hashlib.sha256(base.read_bytes()).hexdigest().upper(),
                candidateXMLSHA256=hashlib.sha256(candidate.read_bytes()).hexdigest().upper(),
                unchangedNonRendererNamedMethods=named_count, unchangedNonRendererClassLayouts=layouts,
                equivalentGrafonNamedMethods=methods, equivalentAnonymousMethods=anonymous,
                allowedChangedGrafonMethods=sorted(CHANGED), addedGrafonMethods=sorted(ADDED),
                addedGrafonFields=sorted(FIELDS), originalConstantPoolPreserved=True,
                normalizedExecutableHashes=hashes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=BASE)
    parser.add_argument('--candidate', type=Path, default=CANDIDATE)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--self-test', action='store_true', help='Exercise rejection and debug-normalization cases in memory only')
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(args.base.resolve())))
        return
    result = audit(args.base.resolve(), args.candidate.resolve())
    if args.out:
        args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    summary = {k: v for k, v in result.items() if k != 'normalizedExecutableHashes'}
    print(json.dumps(summary, ensure_ascii=False))


def self_test(path):
    a = next(abc for node in ET.parse(path).findall('.//abc')
             for abc in [ABC(node)] if CLASS in abc.class_by_name)
    index = a.named[CLASS + '::0:1:decal']
    base_code = bytes.fromhex(a.bodies[index].get('codeBytes'))
    rows, addresses = decode(base_code)
    checked = []

    def attempt(label, changed_index, edit, expected):
        b = copy.copy(a)
        b.bodies = dict(a.bodies)
        b.bodies[changed_index] = copy.deepcopy(a.bodies[changed_index])
        edit(b.bodies[changed_index])
        try:
            c = Compare(a, b)
            target = a.named[CLASS + '::0:1:sceneDrawSteps'] if changed_index != index else index
            c.body(target, target, label)
            passed = True
        except AssertionError:
            passed = False
        require(passed == expected, 'Audit self-test failed: ' + label)
        checked.append(label)

    def patched(offset, value):
        def mutate(body):
            data = bytearray.fromhex(body.get('codeBytes'))
            data[offset] = value
            body.set('codeBytes', data.hex())
        return mutate

    debug = next(row for row in rows if row[2] == 0xef)
    # Last operand is a small source-line number for a parameter (zero here).
    attempt('debug-line-only-accepted', index, patched(debug[1] - 1, 1), True)
    simple = next(row for row in rows if row[2] == 0xa1)
    attempt('subtraction-to-addition-rejected', index, patched(simple[0], 0xa0), False)
    branch = next(row for row in rows if row[2] == 0x12)
    attempt('inverted-branch-rejected', index, patched(branch[0], 0x11), False)
    attempt('unknown-opcode-rejected', index, patched(simple[0], 0xff), False)
    attempt('frame-size-change-rejected', index,
            lambda body: body.set('max_stack', str(int(body.get('max_stack')) + 1)), False)
    draw = a.bodies[a.named[CLASS + '::0:1:sceneDrawSteps']]
    calls, _ = decode(bytes.fromhex(draw.get('codeBytes')))
    anonymous = next(value for _, _, opcode, operands in calls if opcode == 0x40
                     for kind, value in operands if kind == 'm')
    attempt('reachable-anonymous-change-rejected', anonymous, patched(0, 0xff), False)
    return {'passed': True, 'inMemoryOnly': True, 'cases': checked}


if __name__ == '__main__':
    main()
