"""Read-only proof for the two pinned RV SWFs: only ProductInfo build date differs.

No code/resource normalization, no binary writes, no acceptance of arbitrary builds.
"""
from pathlib import Path
import hashlib
import json
import struct
import zlib

ROOT = Path(__file__).resolve().parents[3]
PUBLISHED = 'B7695DF82AA45FDB783C4EB88AFFCB0C34A7674E3A052D2FD128867172A83A49'
REBUILT = 'A3E2F4634F62CD1C2E10C4733E1CE9EEB3BF85F11FE2B385DBC47AFA8C1F336E'


def inspect(path, expected):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    assert digest == expected, 'RV bytes differ from reviewed build'
    assert raw[:3] in (b'CWS', b'FWS')
    data = bytearray(raw[8:] if raw[:3] == b'FWS' else zlib.decompress(raw[8:]))
    assert struct.unpack_from('<I', raw, 4)[0] == len(data) + 8
    offset = (5 + 4 * (data[0] >> 3) + 7) // 8 + 4
    dates, tags = [], 0
    while offset < len(data):
        header = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        tag, length = header >> 6, header & 63
        if length == 63:
            length = struct.unpack_from('<I', data, offset)[0]
            offset += 4
        assert offset + length <= len(data)
        if tag == 41:
            assert length == 26
            dates.append({'offset': offset + 18, 'milliseconds': struct.unpack_from('<Q', data, offset + 18)[0]})
            data[offset + 18:offset + 26] = bytes(8)
        tags += 1
        offset += length
    assert offset == len(data) and len(dates) == 1
    # Version, declared length, RECT, frame rate/count, tag headers and every
    # remaining payload byte must all be equal, including all DoABC contents.
    normalized = raw[3:8] + data
    return normalized, {'sha256': digest, 'tags': tags, 'buildDate': dates[0],
                        'normalizedSHA256': hashlib.sha256(normalized).hexdigest().upper()}


production, p = inspect(ROOT / 'mods/RealisticVision/release/RealisticVisionMod.swf', PUBLISHED)
runtime, r = inspect(ROOT / 'mods/ContinuousScene/build/runtime/mods/RealisticVision/release/RealisticVisionMod.swf', REBUILT)
assert production == runtime, 'Difference outside ProductInfo timestamp'
print(json.dumps({'passed': True, 'scope': 'Only 8-byte ProductInfo build date ignored; every other uncompressed byte equal',
                  'production': p, 'runtime': r}))
