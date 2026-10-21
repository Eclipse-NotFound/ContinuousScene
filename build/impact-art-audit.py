"""Fail-closed, offline audit of native decal classes eligible for per-call reuse.

Reads FFDec XML only. Does not start FFDec/AIR, import a game class, or edit any
game file. Prints JSON; --out optionally saves the same report to a new file.
This proves a narrow native-art whitelist, not arbitrary MovieClip safety or
pixel equivalence of a renderer change. A pixel/runtime test is still required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ART = (
    'bullet_dyr', 'bullet_tre', 'bullet_metal', 'bullet_wood', 'expl_tre',
    'metal_tre', 'punch_tre', 'fire_soft', 'laser_tre', 'plasma_dyr',
    'plasma_tre', 'bluplasma_tre', 'pinkplasma_tre', 'cryo_soft',
    'plaexpl_tre', 'block_plav', 'block_pla', 'block_bur',
)
SHAPES = {'DefineShapeTag', 'DefineShape2Tag', 'DefineShape3Tag', 'DefineShape4Tag'}
TIMELINE = {'PlaceObjectTag', 'PlaceObject2Tag', 'PlaceObject3Tag',
            'RemoveObjectTag', 'RemoveObject2Tag', 'ShowFrameTag', 'EndTag'}
EMPTY_INIT = 'd030d0490047'  # getlocal0; pushscope; getlocal0; constructsuper 0; returnvoid
EMPTY_STATIC = 'd03047'     # getlocal0; pushscope; returnvoid


def require(ok, message):
    if not ok:
        raise ValueError(message)


def semantic(node):
    # Only serializer transport metadata is irrelevant to sprite/shape content.
    ignored = {'forceWriteAsLong', 'fileOffset'}
    return (node.tag, tuple(sorted((k, v) for k, v in node.attrib.items() if k not in ignored)),
            (node.text or '').strip(), tuple(semantic(c) for c in node))


def classes(tree):
    result = {}
    for abc in tree.findall('.//abc'):
        cp = abc.find('constants')
        strings = [n.text or '' for n in cp.find('constant_string')]
        namespaces, multinames = list(cp.find('constant_namespace')), list(cp.find('constant_multiname'))

        def qualified(index):
            entry = multinames[int(index)]
            require(entry.get('namespace_index') is not None, 'Non-QName class/super identity')
            namespace = namespaces[int(entry.get('namespace_index'))]
            prefix, name = strings[int(namespace.get('name_index', 0))], strings[int(entry.get('name_index', 0))]
            return prefix + '.' + name if prefix else name

        bodies = {int(n.get('method_info')): n for n in abc.find('bodies')}
        instances, statics = list(abc.find('instance_info')), list(abc.find('class_info'))
        require(len(instances) == len(statics), 'Instance/static table length mismatch')
        for instance, static in zip(instances, statics):
            name = qualified(instance.get('name_index'))
            if name not in ART:
                continue
            require(name not in result, 'Duplicate class definition: ' + name)
            require(qualified(instance.get('super_index')) == 'flash.display.MovieClip', name + ': non-native base class')
            require(len(instance.find('interfaces')) == 0, name + ': unexpected interfaces')
            require(len(instance.find('instance_traits/traits')) == 0, name + ': instance slots/methods/frame scripts')
            require(len(static.find('static_traits/traits')) == 0, name + ': static slots/methods')
            row = {'super': 'flash.display.MovieClip', 'instanceTraits': 0, 'staticTraits': 0}
            for label, index, expected in (
                ('constructor', int(instance.get('iinit_index')), EMPTY_INIT),
                ('staticInitializer', int(static.get('cinit_index')), EMPTY_STATIC),
            ):
                body = bodies.get(index)
                require(body is not None, name + ': missing ' + label)
                require(body.get('codeBytes', '').lower() == expected, name + ': nontrivial ' + label)
                require(len(body.find('exceptions')) == 0, name + ': initializer exception handlers')
                traits = body.find('traits')
                require(traits is not None and traits.find('traits') is not None and
                        len(traits.find('traits')) == 0, name + ': initializer traits')
                row[label] = expected
            result[name] = row
    require(set(result) == set(ART), 'Missing whitelist classes: ' + ', '.join(sorted(set(ART) - set(result))))
    return result


def assets(tree):
    definitions, symbol_names, linked = {}, {}, {}
    for node in tree.iter():
        kind = node.get('type', '')
        if kind == 'DefineSpriteTag' or kind in SHAPES:
            identity = int(node.get('spriteId') if kind == 'DefineSpriteTag' else node.get('shapeId'))
            require(identity not in definitions, 'Duplicate character definition: ' + str(identity))
            definitions[identity] = node
        if kind not in {'SymbolClassTag', 'ExportAssetsTag'}:
            continue
        tags, names = node.find('tags'), node.find('names')
        require(tags is not None and names is not None and len(tags) == len(names), 'Malformed linkage table')
        for tag, name in zip(tags, names):
            identity, label = int(tag.text), name.text or ''
            linked.setdefault(identity, []).append({'kind': kind, 'name': label})
            if kind == 'SymbolClassTag':
                require(label not in symbol_names or symbol_names[label] == identity, 'Duplicate symbol class: ' + label)
                symbol_names[label] = identity
    return definitions, symbol_names, linked


def audit_asset(name, definitions, symbol_names, linked):
    require(name in symbol_names, name + ': no native symbol linkage')
    identity = symbol_names[name]
    sprite = definitions.get(identity)
    require(sprite is not None and sprite.get('type') == 'DefineSpriteTag', name + ': no native sprite')
    frame_count = int(sprite.get('frameCount', 0))
    require(frame_count > 0, name + ': no frames')
    sub = sprite.find('subTags')
    require(sub is not None, name + ': no timeline')
    children, seen_frames = set(), 0
    for item in sub:
        kind = item.get('type', '')
        require(kind in TIMELINE, name + ': unsupported timeline tag ' + kind)
        if kind == 'ShowFrameTag':
            seen_frames += 1
        for field in ('placeFlagHasClipActions', 'placeFlagHasClassName', 'placeFlagHasImage'):
            require(item.get(field, 'false').lower() == 'false', name + ': scripted/injected placement ' + field)
        require(not item.get('className'), name + ': placement className')
        require(not any('Action' in n.get('type', '') or n.tag.lower() == 'clipactions' for n in item.iter()),
                name + ': embedded action metadata')
        if kind.startswith('PlaceObject') and item.get('characterId'):
            child_id = int(item.get('characterId'))
            child = definitions.get(child_id)
            require(child is not None and child.get('type') in SHAPES,
                    name + ': child is not a static shape: ' + str(child_id))
            require(child_id not in linked, name + ': child has symbol/export linkage: ' + str(child_id))
            children.add(child_id)
        elif kind.startswith('PlaceObject'):
            require(item.get('placeFlagHasCharacter', 'false').lower() == 'false', name + ': missing placed character ID')
    require(seen_frames == frame_count, name + ': incomplete timeline frames')
    require(children, name + ': no proven static artwork')
    return {'name': name, 'symbolId': identity, 'frames': frame_count,
            'children': [{'id': i, 'type': definitions[i].get('type'), 'linked': False} for i in sorted(children)],
            'scriptedChildren': 0}, [sprite] + [definitions[i] for i in sorted(children)]


def audit(host: Path, reference: Path):
    host_bytes, reference_bytes = host.read_bytes(), reference.read_bytes()
    current, prior = ET.ElementTree(ET.fromstring(host_bytes)), ET.ElementTree(ET.fromstring(reference_bytes))
    current_classes, reference_classes = classes(current), classes(prior)
    current_assets, reference_assets = assets(current), assets(prior)
    rows = []
    for name in ART:
        row, definitions = audit_asset(name, *current_assets)
        reference_row, prior_definitions = audit_asset(name, *reference_assets)
        require(row == reference_row, name + ': symbol/timeline/child structure changed')
        require(current_classes[name] == reference_classes[name], name + ': constructors changed')
        require([semantic(n) for n in definitions] == [semantic(n) for n in prior_definitions],
                name + ': timeline/static geometry changed')
        row.update(current_classes[name])
        row['referenceAssetDefinitionsEqual'] = True
        rows.append(row)
    return {'passed': True, 'hostXML': str(host.resolve()), 'referenceXML': str(reference.resolve()),
            'hostXMLSHA256': hashlib.sha256(host_bytes).hexdigest().upper(),
            'referenceXMLSHA256': hashlib.sha256(reference_bytes).hexdigest().upper(),
            'classCount': len(rows), 'classes': rows,
            'scope': 'Native Class identity whitelist only; reuse within one synchronous sceneApply only.',
            'limitations': ['Does not prove renderer pixels, native lazy-raster cost, or runtime speed.',
                           'Unknown classes, injected subclasses and test wrappers require fallback.',
                           'No cross-frame or replay pooling; preserve frame choice and per-draw transform.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', type=Path, required=True, help='FFDec XML for the exact candidate host')
    parser.add_argument('--reference', type=Path, required=True, help='Known reference FFDec XML')
    parser.add_argument('--out', type=Path, help='Optional NEW JSON report; existing files are never overwritten')
    args = parser.parse_args()
    try:
        report = audit(args.host, args.reference)
    except Exception as error:
        report = {'passed': False, 'error': type(error).__name__ + ': ' + str(error),
                  'hostXML': str(args.host), 'referenceXML': str(args.reference)}
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.out:
        with args.out.open('x', encoding='utf-8') as stream:
            stream.write(output + '\n')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
