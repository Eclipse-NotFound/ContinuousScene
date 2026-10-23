"""Pure BEFC production candidate; only per-call opaque-blocker reuse.

No telemetry, API switch, timers, imports, persistent cache, or extra members.
The produced source still requires emitted-body review and exact-host tests.
"""
import hashlib

VERSION = 'fog-last-blocker-production-minimal-1'
TARGET = 'fe.loc.Location::0:1:lighting'
HOST_SHA = 'BEFCF0509E11FAC9FEF7AFB834708B8B93752A14AE3D5CD72B42AA6D42F9B82A'
SOURCE_SHA = '4D8B971D16A6D4CE8E8E8F691D9E8006969DD8779DB5B0D08DD1D4D8FA7D6320'
TIMER_CALLS = 0


def once(source, before, after):
    assert source.count(before) == 1, ('Ambiguous source anchor', before)
    return source.replace(before, after)


DECLARATIONS = '''
         // Only the current large-scene renderer opts into blocker reuse.
         var csLBEligible:Boolean = bounded && interiorRay && this.grafon.sceneLarge;
         var csLBStep:int = 0;
         var csLBX:int = 0;
         var csLBY:int = 0;
'''

PREFIX = '''                        if(csLBEligible && csLBStep > 0 && csLBStep <= _loc15_
                           && int(int(param1 + csLBStep * _loc13_) / Tile.tileX) == csLBX
                           && int(int(param2 + csLBStep * _loc14_) / Tile.tileY) == csLBY)
                        {
                           _loc6_ = 0;
                        }
                        else
                        {
'''

UPDATE = '''                                 if(csLBEligible && _loc18_ >= 1)
                                 {
                                    csLBStep = _loc16_;
                                    csLBX = int(int(param1 + _loc16_ * _loc13_) / Tile.tileX);
                                    csLBY = int(int(param2 + _loc16_ * _loc14_) / Tile.tileY);
                                 }
'''

SUFFIX = '''                        }
'''


def _brace_end(text, opening):
    depth = 0
    for pos in range(opening, len(text)):
        if text[pos] == '{':
            depth += 1
        elif text[pos] == '}':
            depth -= 1
            if depth == 0:
                return pos + 1
    raise AssertionError('Unclosed native loop')


def transform(source, parser):
    """Inverse proves all original statements remain in their original order."""
    assert 'csLB' not in source, 'Local name collision'
    start, end = parser._body(source, 'lighting')
    original = source[start + 1:end]
    ray_start = original.index('                        _loc16_ = 1;')
    while_start = original.index('                        while(_loc16_ <= _loc15_)', ray_start)
    loop_end = _brace_end(original, original.index('{', while_start))
    assert original[loop_end:loop_end + 1] == '\n'
    loop_end += 1
    loop = original[ray_start:loop_end]
    assert 'old_loc' not in loop
    assert loop.count('this.getAbsTile(') == loop.count('_loc16_++') == 1
    assert loop.count('_loc6_ -= _loc18_;') == 1
    assert 'currentTile.' not in loop and 'setPixel' not in loop and 'getTimer' not in loop
    extinction = '                                 _loc6_ = 0;\n'
    augmented_loop = once(loop, extinction, UPDATE + extinction)
    wrapped = PREFIX + augmented_loop + SUFFIX
    body = once(original, loop, wrapped)
    declaration = '         var currentTile:Tile;\n'
    body = once(body, declaration, declaration + DECLARATIONS)
    restored = once(body, wrapped, loop)
    restored = once(restored, declaration + DECLARATIONS, declaration)
    assert restored == original, 'Native statements changed'
    assert once(augmented_loop, UPDATE + extinction, extinction) == loop
    result = source[:start + 1] + body + source[end:]
    a, z = parser._body(result, 'lighting')
    assert result[:a + 1] == source[:start + 1] and result[z:] == source[end:]
    assert result.count('getTimer') == source.count('getTimer')
    assert result.count('nativeAPI') == source.count('nativeAPI')
    assert result.count('setPixel32(') == source.count('setPixel32(')
    assert not any(x in result for x in ('fogLastBlockerEnabled', 'fogLastBlockerProfile', 'csFB'))
    return result


def read_pinned_source(path):
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest().upper() == SOURCE_SHA, 'Wrong BEFC source'
    return data.decode('utf-8-sig').replace('\r\n', '\n')
