"""Seed native Snd settings for this recipe's fresh motion-test AIR application.

AMF3 values follow Adobe's January 2013 specification (sections 1.3, 3.6,
3.7, 3.8 and 3.11): https://veovera.org/docs/legacy/amf3-file-format-spec.pdf
The TCSO wrapper is checked against the existing 36-byte config.sol in
camera-native-once-20261028-base-r1/storage/#SharedObjects/pfe.swf:
SHA256 6E461452BA29CCEA7129DB355E682BB8917799CCA0C3696C9DBC4B1AAE5DF553.
This is a narrow settings codec, not a general AMF implementation. It covers
native Snd only; independent sounds played directly by mods are not guaranteed.
"""
from pathlib import Path
import hashlib
import math
import os
import re
import stat
import struct
import xml.etree.ElementTree as ET


RUNTIME = Path(__file__).resolve().parents[2] / 'runtime'
ID_PATTERN = re.compile(r'pfe-modsettings-continuous-motion-[0-9a-f]{32}\Z')
VOLUMES = ('globalVol', 'stepVol', 'musicVol')
TCSO = bytes.fromhex('5443534f0004000000000006636f6e66696700000003')
MAX_SIZE = 65536


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value):
    raw = value.encode('utf-8')
    require(len(raw) < 64, 'Only short literal settings keys are written')
    return bytes((len(raw) * 2 + 1,)) + raw


def seed_bytes():
    # Anonymous, dynamic, inline object: 0A marker, U29 traits 0B, empty name.
    snd = b'\x0a\x0b\x01' + b''.join(
        _text(key) + b'\x05' + struct.pack('>d', 0.0) for key in VOLUMES
    ) + b'\x01'
    body = _text('nadv') + b'\x04\x01\x00' + _text('snd') + snd + b'\x00'
    payload = TCSO + body
    return b'\x00\xbf' + struct.pack('>I', len(payload)) + payload


class _Reader:
    def __init__(self, raw):
        self.raw, self.at = raw, 0
        self.strings, self.objects, self.traits = [], [], []

    def take(self, count):
        require(count >= 0 and self.at + count <= len(self.raw), 'Truncated AMF3')
        value = self.raw[self.at:self.at + count]
        self.at += count
        return value

    def u29(self):
        value = 0
        for index in range(4):
            octet = self.take(1)[0]
            if index == 3:
                return (value << 8) | octet
            value = (value << 7) | (octet & 127)
            if not octet & 128:
                return value
        raise ValueError('Invalid U29')

    def string(self):
        header = self.u29()
        if not header & 1:
            index = header >> 1
            require(index < len(self.strings), 'Invalid AMF3 string reference')
            return self.strings[index]
        value = self.take(header >> 1).decode('utf-8', errors='strict')
        if value:
            self.strings.append(value)
        return value

    def value(self, depth=0):
        require(depth <= 4, 'Settings nesting exceeds this narrow reader')
        marker = self.take(1)[0]
        if marker == 4:
            value = self.u29()
            return value - (1 << 29) if value & (1 << 28) else value
        if marker == 5:
            return struct.unpack('>d', self.take(8))[0]
        require(marker == 10, 'Unsupported settings AMF3 marker: ' + str(marker))
        header = self.u29()
        if not header & 1:
            index = header >> 1
            require(index < len(self.objects), 'Invalid AMF3 object reference')
            return self.objects[index]
        if not header & 2:
            require((header >> 2) < len(self.traits), 'Invalid AMF3 trait reference')
        else:
            require(header == 11 and self.string() == '',
                    'Only anonymous dynamic settings objects are supported')
            self.traits.append(True)
        result = {}
        self.objects.append(result)
        while True:
            key = self.string()
            if not key:
                return result
            require(key not in result and len(result) < 32, 'Duplicate/excess settings keys')
            result[key] = self.value(depth + 1)


def decode_config(raw):
    """Read the observed config TCSO wrapper and its numeric/dynamic AMF3 values."""
    require(isinstance(raw, bytes) and 6 + len(TCSO) <= len(raw) <= MAX_SIZE,
            'Invalid config size/type')
    require(raw[:2] == b'\x00\xbf', 'Invalid SharedObject signature')
    require(struct.unpack('>I', raw[2:6])[0] == len(raw) - 6, 'TCSO length mismatch')
    require(raw[6:6 + len(TCSO)] == TCSO, 'Expected config TCSO with AMF3 encoding')
    reader = _Reader(raw[6 + len(TCSO):])
    result = {}
    while reader.at < len(reader.raw):
        key = reader.string()
        require(key and key not in result and len(result) < 32, 'Invalid top-level key')
        result[key] = reader.value()
        require(reader.take(1) == b'\x00', 'Missing TCSO value terminator')
    return result


def _silent(decoded):
    snd = decoded.get('snd')
    require(isinstance(snd, dict), 'Native Snd settings missing')
    for key in VOLUMES:
        value = snd.get(key)
        require(type(value) in (int, float) and math.isfinite(value) and value == 0,
                'Native Snd setting is not zero: ' + key)
    return {key: snd[key] for key in VOLUMES}


def verify_retained(path):
    """Independently decode a retained config (including one in an evidence folder)."""
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_SIZE + 1)
    return _silent(decode_config(raw))


def _descriptor_id(raw):
    require(len(raw) <= MAX_SIZE and b'<!' not in raw, 'Unsupported descriptor declarations')
    root = ET.fromstring(raw)
    match = re.fullmatch(r'\{(http://ns\.adobe\.com/air/application/[0-9.]+)\}application', root.tag)
    require(match is not None, 'Expected AIR application descriptor')
    namespace = '{' + match.group(1) + '}'
    ids = root.findall(namespace + 'id')
    require(len(ids) == 1, 'Descriptor must contain exactly one application ID')
    app_id = ids[0].text or ''
    require(ID_PATTERN.fullmatch(app_id) is not None, 'Not a fresh motion-test application ID')
    contents = root.findall(namespace + 'initialWindow/' + namespace + 'content')
    require(len(contents) == 1 and contents[0].text == 'pfe.swf', 'Expected local pfe.swf content')
    return app_id


def _not_link(path):
    info = path.lstat()
    require(not stat.S_ISLNK(info.st_mode) and not (
        getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
    ), 'Refuse symlink/reparse path: ' + str(path))


def seed(descriptor_path, expected_runtime_root):
    """Write once, only below APPDATA/<ID parsed from this runtime descriptor>."""
    runtime = Path(expected_runtime_root).resolve(strict=True)
    require(runtime == RUNTIME.resolve(strict=True), 'External runtime root refused')
    descriptor = Path(descriptor_path)
    require(descriptor.is_absolute(), 'Descriptor must be absolute')
    _not_link(descriptor)
    descriptor = descriptor.resolve(strict=True)
    require(descriptor.parent == runtime, 'Descriptor is outside the expected runtime root')
    raw = descriptor.read_bytes()
    app_id = _descriptor_id(raw)
    require(descriptor.name == app_id + '.xml', 'Descriptor filename and application ID differ')
    appdata_value = os.environ.get('APPDATA', '')
    require(appdata_value and Path(appdata_value).is_absolute(), 'APPDATA must be an absolute directory')
    appdata = Path(appdata_value).resolve(strict=True)
    require(appdata.is_dir(), 'APPDATA is not a directory')
    app_root = appdata / app_id
    target = app_root / 'Local Store' / '#SharedObjects' / 'pfe.swf' / 'config.sol'
    require(not os.path.lexists(app_root), 'Fresh application storage already exists')
    require(not os.path.lexists(target), 'Never replace an existing config.sol')
    require(descriptor.read_bytes() == raw, 'Descriptor changed during preflight')
    payload = seed_bytes()
    decoded = decode_config(payload)
    require(set(decoded) == {'nadv', 'snd'} and decoded['nadv'] == 1, 'Seed contents differ')
    _silent(decoded)
    # Exclusive creation: failure deliberately preserves any created evidence.
    app_root.mkdir(exist_ok=False)
    parent = app_root
    for part in ('Local Store', '#SharedObjects', 'pfe.swf'):
        _not_link(parent)
        require(parent.resolve(strict=True).is_relative_to(app_root), 'Storage path escaped application')
        parent = parent / part
        parent.mkdir(exist_ok=False)
    _not_link(parent)
    require(parent.resolve(strict=True) == target.parent, 'Storage path changed')
    with target.open('xb') as stream:
        stream.write(payload)
    retained = verify_retained(target)
    require(target.read_bytes() == payload, 'Seed bytes changed during write/readback')
    return dict(applicationID=app_id, descriptor=str(descriptor),
                descriptorSHA256=hashlib.sha256(raw).hexdigest().upper(), path=str(target),
                sha256=hashlib.sha256(payload).hexdigest().upper(), byteLength=len(payload),
                snd=retained, nadv=decoded['nadv'], writeOnce=True, decodedAfterWrite=True,
                nativeSndOnly=True, allAudioMuted=False, gameReadConfirmed=False)
