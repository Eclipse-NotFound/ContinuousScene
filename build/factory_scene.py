"""Bake original factory room fixtures into one continuous Location.

Reads native data only. No original campaign files are changed. Room seams are
opened only at mutually compatible native door slots, as Land.setDoor does.
"""
from pathlib import Path
import collections
import copy
import hashlib
import json
import xml.etree.ElementTree as ET

MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parents[1]
RUNTIME = MOD / 'build/runtime'
# Entrance rooms plus level-zero factory fixtures; no rear-room portals.
LAYOUT = [[12, 33, 13, 41], [24, 32, 49, 18], [7, 37, 52, 48]]


def build():
    source = ROOT / 'Rooms/rooms_plant.xml'
    rooms = list(ET.parse(source).getroot())
    width, height = len(LAYOUT[0]) * 48, len(LAYOUT) * 25
    out = ET.Element('all', sceneKind='factory', source='Rooms/rooms_plant.xml')
    room = ET.SubElement(out, 'room', name='continuous-factory', sceneWidth=str(width),
                         sceneHeight=str(height), sceneRevision='factory-1')
    ET.SubElement(room, 'options', backwall='tBackWall', music='music_plant_2')
    regions = ET.SubElement(room, 'sceneRegions')
    cells = [['A'] * width for _ in range(height)]
    objects, backdrops, links, provenance = [], [], [], []
    door_slots = {}
    for ry, row in enumerate(LAYOUT):
        for rx, index in enumerate(row):
            original = rooms[index]
            options = original.find('options').attrib
            if options.get('back') or options.get('tip') == 'back':
                raise ValueError('Rear rooms need explicit continuous placement')
            door_slots[rx, ry] = list(map(int, original.findtext('doors').split('.')))
            ox, oy = rx * 48, ry * 25
            data = [a.text.split('.') for a in original.findall('a')]
            assert len(data) == 25 and all(len(a) == 48 for a in data)
            for y, row_cells in enumerate(data):
                cells[oy+y][ox:ox+48] = row_cells
            ET.SubElement(regions, 'region', x=str(ox), y=str(oy), width='48', height='25',
                          backwall=options.get('backwall') or 'tBackWall',
                          color=options.get('color') or '', dark=options.get('dark') or '0',
                          source=original.get('name'), index=str(index))
            for tag, dest in [('obj', objects), ('back', backdrops)]:
                for item in original.findall(tag):
                    # A single entrance, rather than every template's spawn marker.
                    if tag == 'obj' and item.get('id') == 'player' and (rx, ry) != (0, 0):
                        continue
                    item = copy.deepcopy(item)
                    item.set('x', str(int(item.get('x')) + ox))
                    item.set('y', str(int(item.get('y')) + oy))
                    if item.get('code'):
                        item.set('code', 'factory-%d-%d-%s' % (rx, ry, item.get('code')))
                    dest.append(item)
            provenance.append({'rx': rx, 'ry': ry, 'index': index, 'name': original.get('name'),
                               'objects': len(original.findall('obj')), 'backdrops': len(original.findall('back'))})

    def clear(x, y):
        # Keep backdrop encodings after the underscore, remove solid foreground.
        old = cells[y][x]
        cells[y][x] = old[old.index('_'):] if '_' in old else '_'

    for (rx, ry), doors in door_slots.items():
        for dx, dy, offset, indices in [(1, 0, 11, range(6)), (0, 1, 11, range(6, 11))]:
            neighbor = door_slots.get((rx+dx, ry+dy))
            if neighbor is None:
                continue
            choices = [(slot, min(doors[slot], neighbor[slot+offset])) for slot in indices
                       if min(doors[slot], neighbor[slot+offset]) >= 2]
            if not choices:
                continue
            # Open every compatible native passage, without adding room transitions.
            for slot, size in choices:
                if dx:
                    y = ry*25 + slot*4+3
                    for xx in range((rx+1)*48-2, (rx+1)*48+2):
                        for yy in range(y-(2 if size > 2 else 1), y+1):
                            clear(xx, yy)
                    links.append({'axis': 'x', 'x': (rx+1)*48, 'y': y, 'size': size,
                                  'from': [rx, ry], 'to': [rx+1, ry]})
                else:
                    x = rx*48 + (slot-6)*9+4
                    for yy in range((ry+1)*25-2, (ry+1)*25+2):
                        for xx in range(x+(0 if size > 2 else 1), x+(4 if size > 2 else 3)):
                            clear(xx, yy)
                    links.append({'axis': 'y', 'x': x, 'y': (ry+1)*25, 'size': size,
                                  'from': [rx, ry], 'to': [rx, ry+1]})
    reached = {(0, 0)}
    while True:
        before = len(reached)
        for link in links:
            a, b = tuple(link['from']), tuple(link['to'])
            if a in reached or b in reached:
                reached.update([a, b])
        if len(reached) == before:
            break
    assert len(reached) == 12, 'Factory room graph must be fully connected'
    for x in range(width):
        cells[0][x] = cells[-1][x] = 'A'
    for y in range(height):
        cells[y][0] = cells[y][-1] = 'A'
        ET.SubElement(room, 'a').text = '.'.join(cells[y])
    for item in objects + backdrops:
        room.append(item)
    ET.SubElement(room, 'sceneLinks').text = json.dumps(links, separators=(',', ':'))
    output = RUNTIME/'mods/ContinuousScene/release/scene.xml'
    output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(out, space='  ')
    output.write_bytes(ET.tostring(out, encoding='utf-8', xml_declaration=True))
    (RUNTIME/'scene.xml').write_bytes(output.read_bytes())
    (RUNTIME/'scene-factory.xml').write_bytes(output.read_bytes())
    report = {'source': str(source), 'sourceSHA256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'outputSHA256': hashlib.sha256(output.read_bytes()).hexdigest(), 'width': width, 'height': height,
              'rooms': provenance, 'objects': len(objects), 'backdrops': len(backdrops),
              'objectTypes': dict(collections.Counter(n.get('id') for n in objects)), 'links': links,
              'allRoomsConnected': True}
    (MOD/'build/generated/factory-provenance.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['width', 'height', 'objects', 'backdrops', 'allRoomsConnected']}))


if __name__ == '__main__':
    build()
