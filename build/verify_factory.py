"""Audit imported native content and the captured chunk/native renderer comparison.

This reads evidence; it does not change scenes or image pixels.
"""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parents[1]
evidence = MOD / 'knowledge/experiments/evidence' / sys.argv[1]
pool = ET.parse(evidence / 'scene.xml').getroot()
room = pool.find('room')
originals = list(ET.parse(ROOT / 'Rooms/rooms_plant.xml').getroot())
checks = []

def check(name, passed, detail=None):
    checks.append(dict(name=name, passed=bool(passed), detail=detail))

check('factory-source-selected', pool.get('sceneKind') == 'factory')
check('factory-12-native-rooms', len(room.find('sceneRegions')) == 12)
source_objects, source_art = [], []
for region in room.find('sceneRegions'):
    ox, oy, index = (int(region.get(k)) for k in ('x', 'y', 'index'))
    original = originals[index]
    for tag, output in [('obj', source_objects), ('back', source_art)]:
        for node in original.findall(tag):
            if tag == 'obj' and node.get('id') == 'player' and (ox, oy) != (0, 0):
                continue
            data = dict(node.attrib)
            data['x'], data['y'] = str(int(data['x'])+ox), str(int(data['y'])+oy)
            if data.get('code'):
                data['code'] = f'factory-{ox//48}-{oy//25}-' + data['code']
            output.append(data)
    # Native interiors are preserved; only the outer two cells can be carved for connections.
    for y in range(2, 23):
        imported = room.findall('a')[oy+y].text.split('.')[ox+2:ox+46]
        native = original.findall('a')[y].text.split('.')[2:46]
        if imported != native:
            raise AssertionError(f'Native interior changed: room {index}, row {y}')
check('factory-native-interiors-preserved', True)
check('factory-444-native-objects-preserved', source_objects == [n.attrib for n in room.findall('obj')] and len(source_objects) == 444)
check('factory-603-native-decorations-preserved', source_art == [n.attrib for n in room.findall('back')] and len(source_art) == 603)
codes = [n.get('code') for n in room.findall('obj')]
check('factory-object-identifiers-unique', len(codes) == len(set(codes)))

comparisons = []
for layer in range(4):
    a = np.asarray(Image.open(evidence/f'raster-cached-{layer}.png').convert('RGBA')).astype(np.int16)
    b = np.asarray(Image.open(evidence/f'raster-native-{layer}.png').convert('RGBA')).astype(np.int16)
    # The oracle is deliberately a single 48x25 room: its exterior has no neighbours.
    # Exclude that artificial 20px rim, but include every internal 320px chunk seam.
    diff = np.abs(a[20:-20, 20:-20] - b[20:-20, 20:-20])
    significant = np.any(diff > 8, axis=2)
    alpha = diff[:, :, 3] > 8
    row = dict(layer=layer, pixels=int(significant.size), changedPixels=int(np.any(diff != 0, axis=2).sum()),
               significantPixels=int(significant.sum()), alphaPixels=int(alpha.sum()))
    # Permit isolated AIR antialiasing differences, never a missing block or repeated art.
    check(f'native-raster-layer-{layer}', significant.sum() <= 64 and alpha.sum() <= 32, row)
    comparisons.append(row)

result = dict(passed=all(c['passed'] for c in checks), checks=checks, comparison=comparisons,
              sourceSHA256=hashlib.sha256((ROOT/'Rooms/rooms_plant.xml').read_bytes()).hexdigest(),
              sceneSHA256=hashlib.sha256((evidence/'scene.xml').read_bytes()).hexdigest())
(evidence/'factory-audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
assert result['passed'], 'Factory audit failed'
