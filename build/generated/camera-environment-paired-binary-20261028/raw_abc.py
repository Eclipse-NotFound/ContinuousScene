"""Small offset-preserving reader for ABC 46.16; not an AVM2 verifier.

Sources: Adobe avmplus doc/abcFormat-46-16.txt and core/AbcParser.cpp.
TypeName and MultinameLA follow the parser, including forward TypeName refs.
Every unedited structure stays as a raw span; no XML is loaded or emitted.
"""
from dataclasses import dataclass


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def u30(value):
    require(0 <= value < 1 << 30, 'Value is not U30')
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


class Reader:
    def __init__(self, data):
        self.data = memoryview(data)
        self.pos = 0

    def take(self, size):
        require(0 <= size <= len(self.data) - self.pos, 'Truncated ABC')
        start = self.pos
        self.pos += size
        return self.data[start:self.pos]

    def byte(self):
        return self.take(1)[0]

    def integer(self, bits=30):
        result = 0
        for shift in range(0, 35, 7):
            b = self.byte()
            result |= (b & 127) << shift
            if b < 128:
                require(result < 1 << bits, 'Encoded integer overflow')
                return result
        raise AssertionError('Overlong encoded integer')

    def count(self):
        n = self.integer()
        require(n <= len(self.data) - self.pos + 1, 'Implausible ABC count')
        return n


@dataclass(frozen=True)
class Pool:
    count: int
    count_start: int
    entries_start: int
    end: int


@dataclass(frozen=True)
class Body:
    method: int
    start: int
    end: int
    stack: int
    registers: int
    scope: int
    max_scope: int
    code_start: int
    code_end: int
    tail_start: int
    exceptions: int
    traits: int


class RawABC:
    def __init__(self, data):
        self.data = memoryview(data)
        r = self.r = Reader(data)
        self.version = (int.from_bytes(r.take(2), 'little'), int.from_bytes(r.take(2), 'little'))
        require(self.version == (16, 46), 'Only ABC 46.16 is supported')
        self.pools = {}
        self.ints = self.pool('int', lambda: r.integer(32))
        self.uints = self.pool('uint', lambda: r.integer(32))
        self.doubles = self.pool('double', lambda: bytes(r.take(8)))
        self.strings = self.pool('string', lambda: bytes(r.take(r.integer())))
        self.namespaces = self.pool('namespace', self.read_namespace)
        self.nssets = self.pool('nsset', lambda: tuple(self.ref('namespace', zero=False) for _ in range(r.count())))
        self.multinames = self.pool('multiname', self.read_multiname)
        self.validate_multinames()
        self.method_start = r.pos
        self.methods = [self.read_method() for _ in range(r.count())]
        self.method_end = r.pos
        self.metadata_count = r.count()
        for _ in range(self.metadata_count):
            self.ref('string')
            n = r.count()
            for _ in range(2 * n):
                self.ref('string')
        self.class_count = r.count()
        self.instances = []
        self.classes = []
        self.named = {}
        self.class_by_name = {}
        for i in range(self.class_count):
            start = r.pos
            name = self.qualified(self.ref('multiname', zero=False))
            require(name not in self.class_by_name, 'Duplicate class name')
            self.class_by_name[name] = i
            self.ref('multiname')
            flags = r.byte()
            require(not flags & ~15, 'Unknown instance flag')
            if flags & 8:
                self.ref('namespace', zero=False)
            for _ in range(r.count()):
                self.ref('multiname', zero=False)
            init = self.method_ref()
            traits = self.read_traits(name + '::0')
            self.instances.append((start, r.pos, name, init, traits))
        for i in range(self.class_count):
            start = r.pos
            init = self.method_ref()
            traits = self.read_traits(self.instances[i][2] + '::1')
            self.classes.append((start, r.pos, init, traits))
        self.script_count = r.count()
        for _ in range(self.script_count):
            self.method_ref()
            self.read_traits()
        self.bodies = {}
        for _ in range(r.count()):
            start = r.pos
            method = self.method_ref()
            require(method not in self.bodies, 'Duplicate method body')
            stack, regs, scope, max_scope = (r.integer() for _ in range(4))
            require(scope <= max_scope, 'Invalid scope depth')
            size = r.integer()
            require(size > 0, 'Empty method body')
            code_start = r.pos
            r.take(size)
            code_end = tail_start = r.pos
            exceptions = r.count()
            for _ in range(exceptions):
                lo, hi, target = (r.integer() for _ in range(3))
                require(lo <= hi <= size and target < size, 'Invalid exception offset')
                self.ref('multiname')
                self.ref('multiname')
            traits = self.read_traits()
            self.bodies[method] = Body(method, start, r.pos, stack, regs, scope, max_scope,
                                       code_start, code_end, tail_start, exceptions, traits)
        require(r.pos == len(self.data), 'Unparsed ABC bytes')

    def pool(self, name, entry):
        r = self.r
        start = r.pos
        count = r.count()
        entries = r.pos
        values = [None]
        # Forward references in a multiname must use the declared total count.
        self.pools[name] = Pool(count, start, entries, -1)
        for _ in range(1, count):
            values.append(entry())
        self.pools[name] = Pool(count, start, entries, r.pos)
        return values

    def ref(self, name, zero=True):
        value = self.r.integer()
        require((zero or value != 0) and value < max(1, self.pools[name].count), 'Invalid ' + name + ' reference')
        return value

    def read_namespace(self):
        kind = self.r.byte()
        require(kind in (5, 8, 22, 23, 24, 25, 26), 'Unknown namespace kind')
        return kind, self.ref('string')

    def read_multiname(self):
        r = self.r
        kind = r.byte()
        if kind in (7, 13):
            return kind, self.ref('namespace'), self.ref('string')
        if kind in (9, 14):
            return kind, self.ref('string'), self.ref('nsset', zero=False)
        if kind in (15, 16):
            return kind, self.ref('string')
        if kind in (17, 18):
            return (kind,)
        if kind in (27, 28):
            return kind, self.ref('nsset', zero=False)
        if kind == 29:
            base = self.ref('multiname', zero=False)
            require(r.integer() == 1, 'TypeName must have one parameter')
            return kind, base, self.ref('multiname')
        raise AssertionError('Unknown multiname kind: ' + str(kind))

    def validate_multinames(self):
        for index, name in enumerate(self.multinames[1:], 1):
            if name[0] != 29:
                continue
            require(self.multinames[name[1]][0] != 29, 'Parameterized TypeName base')
            seen = {index}
            at = name[2]
            while at and self.multinames[at][0] == 29:
                require(at not in seen, 'Cyclic TypeName')
                seen.add(at)
                at = self.multinames[at][2]

    def read_method(self):
        r = self.r
        start = r.pos
        count = r.count()
        self.ref('multiname')
        for _ in range(count):
            self.ref('multiname')
        self.ref('string')
        flags = r.byte()
        if flags & 8:
            optional = r.count()
            require(0 < optional <= count, 'Invalid optional parameter count')
            for _ in range(optional):
                self.constant(r.integer(), r.byte())
        if flags & 128:
            for _ in range(count):
                self.ref('string')
        return start, r.pos

    def constant(self, index, kind):
        pool = {1: 'string', 3: 'int', 4: 'uint', 6: 'double',
                5: 'namespace', 8: 'namespace', 22: 'namespace', 23: 'namespace',
                24: 'namespace', 25: 'namespace', 26: 'namespace'}.get(kind)
        if pool:
            require(index < max(1, self.pools[pool].count), 'Invalid default value')
        else:
            require(kind in (0, 10, 11, 12), 'Unknown default-value kind')

    def method_ref(self):
        index = self.r.integer()
        require(index < len(self.methods), 'Invalid method reference')
        return index

    def read_traits(self, owner=None):
        r = self.r
        count = r.count()
        for _ in range(count):
            name = self.ref('multiname', zero=False)
            tag = r.byte()
            kind = tag & 15
            require(not tag & 128, 'Unknown trait flag')
            if kind in (0, 6):
                r.integer()
                self.ref('multiname')
                value = r.integer()
                if value:
                    self.constant(value, r.byte())
            elif kind in (1, 2, 3):
                r.integer()
                method = self.method_ref()
                if owner:
                    label = owner + ':' + str(kind) + ':' + self.simple(name)
                    require(label not in self.named, 'Duplicate named method')
                    self.named[label] = method
            elif kind == 4:
                r.integer()
                require(r.integer() < self.class_count, 'Invalid class reference')
            elif kind == 5:
                r.integer()
                self.method_ref()
            else:
                raise AssertionError('Unknown trait kind: ' + str(kind))
            if tag & 64:
                for _ in range(r.count()):
                    require(r.integer() < self.metadata_count, 'Invalid metadata reference')
        return count

    def string(self, index):
        require(0 <= index < len(self.strings), 'Invalid string index')
        return '' if index == 0 else self.strings[index].decode('utf-8')

    def simple(self, index):
        name = self.multinames[index]
        require(name[0] in (7, 13, 9, 14, 15, 16), 'Name is not statically named')
        return self.string(name[2] if name[0] in (7, 13) else name[1])

    def qualified(self, index):
        name = self.multinames[index]
        require(name[0] in (7, 13), 'Qualified name is not a QName')
        prefix = self.string(self.namespaces[name[1]][1]) if name[1] else ''
        return (prefix + '.' if prefix else '') + self.simple(index)

    def binding(self, index):
        require(0 < index < len(self.multinames), 'Invalid binding index')
        value = self.multinames[index]
        kind = value[0]
        result = {'index': index, 'kind': kind, 'rawValues': list(value[1:])}
        def ns(n):
            return {'index': n, 'kind': self.namespaces[n][0], 'name': self.string(self.namespaces[n][1])} if n else {'index': 0}
        if kind in (7, 13):
            result.update(name=self.simple(index), namespace=ns(value[1]))
        elif kind in (9, 14, 27, 28):
            set_index = value[2] if kind in (9, 14) else value[1]
            result['namespaces'] = [ns(n) for n in self.nssets[set_index]]
            if kind in (9, 14):
                result['name'] = self.simple(index)
        elif kind in (15, 16):
            result['name'] = self.simple(index)
        elif kind == 29:
            result.update(base=self.binding(value[1]), parameter=self.binding(value[2]) if value[2] else '*')
        return result

    def code(self, method):
        body = self.bodies[method]
        return bytes(self.data[body.code_start:body.code_end])

    def raw(self, span):
        return self.data[span[0]:span[1]]
