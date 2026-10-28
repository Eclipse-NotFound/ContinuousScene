"""Guard four native vertical collision column reads; preserve every other method.

The normal path adds only dup/iftrue after the existing column lookup.
A missing column produces null, already handled by Unit.collisionTile.
No source class recompilation, new constants, or change to collision arithmetic.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SUPPORT = HERE.parent / 'camera-environment-paired-binary-20261028'
sys.path.insert(0, str(SUPPORT))
from raw_abc import RawABC, require, u30
from resources import ResourceGuard


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b = load('unit_boundary_swf_support', SUPPORT / 'build.py')
core = load('unit_boundary_instruction_decoder', HERE.parents[1] / 'native-crop-audit.py')
BASE = '4E5FAB45D6F5A2634C83BE5E7EAF387443F9FB4E56B945CD2BF54880F1F73C75'
OLD_CODE = 'D08BF3C434778103A0B790E617B2AA484D35B741B009D1D476A877055AD9A0D8'
TARGET = 'fe.unit.Unit::0:1:run'
METHOD = 1159
# Immediately after column retrieval, then immediately before Tile coercion.
SITES = ((2443, 2462), (2608, 2633), (3063, 3085), (3658, 3677))


def source_inputs():
    paths = [Path(__file__), SUPPORT/'build.py', SUPPORT/'raw_abc.py', SUPPORT/'resources.py',
             HERE.parents[1]/'native-crop-audit.py']
    return {str(p): b.sha(p) for p in paths}


def guarded_code(abc):
    require(abc.named.get(TARGET) == METHOD, 'Unexpected native Unit.run identity')
    code = abc.code(METHOD)
    require(b.digest(code) == OLD_CODE and len(code) == 3864, 'Native Unit.run changed')
    rows, _ = core.decode(code)
    by_start = {r[0]: r for r in rows}
    by_end = {r[1]: r for r in rows}
    insertions = {start: end for start, end in SITES}
    for start, end in SITES:
        require(by_end[start][2:] == (0x66, [('n', 7326)]), 'Expected dynamic column lookup')
        require(by_start[end][2:] == (0x80, [('n', 28)]), 'Expected native Tile coercion')
        require(by_end[end][2:] == (0x66, [('n', 7326)]), 'Expected dynamic row lookup')
        require(abc.qualified(28) == 'fe.loc.Tile', 'Tile binding changed')
        require(abc.multinames[7326][0] in (27, 28), 'Column operand is not MultinameL')
        require(not any(k == 'target' for a, z, op, args in rows if start <= a < end for k, v in args),
                'Row expression unexpectedly contains branching')
    require(not any(op == 0x1b for _, _, op, _ in rows), 'Unreviewed switch relocation')
    # Map original instruction boundaries to their new guard/operation boundary.
    mapping = {a: a + 11*sum(s < a for s in insertions) for a, _, _, _ in rows}
    mapping[len(code)] = len(code) + 11*len(SITES)
    out = bytearray()
    guard_ranges = []
    for start, end, op, args in rows:
        require(len(out) == mapping[start], 'Relocation accounting drift')
        if start in insertions:
            at = len(out)
            # [column] -> [column,column] -> branch -> [column]
            # Missing path: pop column; push null; skip only the row expression.
            out += b'\x2a\x11' + (6).to_bytes(3, 'little', signed=True) + b'\x29\x20\x10'
            destination = mapping[insertions[start]]
            out += (destination-(at+11)).to_bytes(3, 'little', signed=True)
            guard_ranges.append((at, at+11, destination))
        targets = [v for k, v in args if k == 'target']
        if targets:
            require(len(targets) == 1 and end-start == 4 and 0x0c <= op <= 0x1a,
                    'Unexpected branch encoding')
            out.append(op)
            out += (mapping[targets[0]]-(len(out)+3)).to_bytes(3, 'little', signed=True)
        else:
            out += code[start:end]
    after_rows, _ = core.decode(bytes(out))
    kept = [r for r in after_rows if not any(a <= r[0] < z for a, z, _ in guard_ranges)]
    require(len(kept) == len(rows), 'Original instructions lost or added')
    for old, new in zip(rows, kept):
        a, z, op, args = old
        expected_args = [(kind, mapping[value] if kind == 'target' else value) for kind, value in args]
        require(new == (mapping[a]+(11 if a in insertions else 0),
                        mapping[a]+(11 if a in insertions else 0)+(z-a), op, expected_args),
                'Original instruction changed beyond branch relocation')
    for at, end, destination in guard_ranges:
        actual = [(op, args) for a, z, op, args in after_rows if at <= a < end]
        require(actual == [(0x2a, []), (0x11, [('target', at+11)]), (0x29, []),
                           (0x20, []), (0x10, [('target', destination)])], 'Guard differs')
        # Both paths start with one column and end with one Tile/null. Existing
        # row evaluation already peaks above two operands, so max_stack 5 holds.
    return bytes(out), dict(guards=[dict(start=a,end=z,nullTarget=d) for a,z,d in guard_ranges],
        originalInstructionsPreserved=len(rows), existingBranchesRelocated=True,
        addedInstructions=20, inBoundsExtraInstructionsPerLookup=2,
        localStackProof='Both paths preserve one operand; dup peaks at two <= existing max_stack 5')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    outputs = [HERE/n for n in ('pfe-unit-boundary.swf','host-audit.json')]
    if args.build:
        require(not any(p.exists() for p in outputs), 'Preserve prior outputs')
    guard = ResourceGuard()
    try:
        inputs = source_inputs()
        swf = b.RawSWF(ROOT/'pfe.swf')
        require(swf.sha256 == BASE, 'Formal host changed; rebase before patching')
        indices = [i for i,t in enumerate(swf.tags) if t[0] in (72,82)]
        require(len(indices) == 2, 'Unexpected ABC inventory')
        abc = RawABC(swf.abc(indices[0])[1])
        old = abc.bodies[METHOD]
        require((old.stack,old.registers,old.scope,old.max_scope,old.exceptions,old.traits) == (5,8,6,7,0,0),
                'Unexpected native run frame')
        code, proof = guarded_code(abc)
        body = b''.join(u30(v) for v in (METHOD,old.stack,old.registers,old.scope,old.max_scope,len(code)))
        body += code + bytes(abc.data[old.tail_start:old.end])
        changed, inverse = b.edit_bytes(abc.data, [(old.start,old.end,body,'native-unit-run-column-guards')])
        restored, _ = b.edit_bytes(changed,inverse)
        require(restored == abc.data, 'Exact full ABC restoration failed')
        after = RawABC(changed)
        require(abc.data[:old.start] == after.data[:after.bodies[METHOD].start] and
                abc.data[old.end:] == after.data[after.bodies[METHOD].end:], 'Other ABC data changed')
        require(abc.named == after.named and abc.class_by_name == after.class_by_name and
                set(abc.bodies) == set(after.bodies), 'Class/method identity changed')
        preserved = 0
        for method, before_body in abc.bodies.items():
            if method == METHOD:
                continue
            other = after.bodies[method]
            require(abc.data[before_body.start:before_body.end] == after.data[other.start:other.end],
                    'Unrelated method changed')
            preserved += 1
        proof.update(baseSHA256=BASE,method=TARGET,methodIndex=METHOD,onlyMethodChanged=True,
            unchangedBodiesInMainABC=preserved,unchangedClassesInMainABC=abc.class_count,
            unchangedConstantsAndSignatures=True,exactInverseRestoresABC=True,
            oldCodeSHA256=OLD_CODE,newCodeSHA256=b.digest(code),oldCodeBytes=3864,newCodeBytes=len(code),
            sourceInputs=inputs,passed=True,runtimeVerified=False,performanceClaim=False,
            implementation='python-direct-abc; no class recompile',maxStackUnchanged=5)
        guard.sample('audit-complete')
        require(inputs == source_inputs() and b.sha(ROOT/'pfe.swf') == BASE, 'Inputs changed during audit')
        if args.build:
            b.write_candidate(outputs[0],swf,indices[0],changed)
            actual = b.RawSWF(outputs[0])
            require(actual.signature == swf.signature and actual.body[:actual.frame_end] == swf.body[:swf.frame_end],
                    'Movie header changed')
            require(len(actual.tags) == len(swf.tags), 'Tag inventory changed')
            for i, (a,c) in enumerate(zip(swf.tags,actual.tags)):
                require(a[0] == c[0], 'Tag order/type changed')
                if i == indices[0]:
                    require(actual.abc(i)[0] == swf.abc(i)[0] and actual.abc(i)[1] == changed, 'ABC readback differs')
                else:
                    require(actual.raw_tag(i) == swf.raw_tag(i), 'Other tag/loader/assets changed')
            proof.update(candidateSHA256=actual.sha256,preservedRawTags=len(swf.tags)-1,candidateReadbackExact=True)
            proof['resources'] = guard.receipt()
            require(inputs == source_inputs() and b.sha(ROOT/'pfe.swf') == BASE, 'Inputs changed during build')
            b.json_write(outputs[1],proof)
        print(json.dumps({k:v for k,v in proof.items() if k not in ('resources','sourceInputs')},ensure_ascii=False))
    finally:
        guard.close()


if __name__ == '__main__':
    main()
