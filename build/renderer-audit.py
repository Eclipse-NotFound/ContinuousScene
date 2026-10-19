"""Reject any non-renderer method/layout/constant change in the installed merge."""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pcode_plan import abc_methods

ROOT = Path(__file__).resolve().parent


def layout(node):
    relocated = {'bytes', 'fileOffset', 'iinit_index', 'cinit_index', 'method_info'}
    return (node.tag, tuple(sorted((k, v) for k, v in node.attrib.items() if k not in relocated)),
            tuple(layout(c) for c in node))


def classes(path):
    result = {}
    for abc in ET.parse(path).findall('.//abc'):
        cp = abc.find('constants')
        strings = [e.text or '' for e in cp.find('constant_string')]
        spaces = list(cp.find('constant_namespace'))
        names = list(cp.find('constant_multiname'))
        for instance, static in zip(abc.find('instance_info'), abc.find('class_info')):
            name = names[int(instance.attrib['name_index'])]
            space = spaces[int(name.attrib.get('namespace_index', 0))]
            label = strings[int(space.attrib.get('name_index', 0))] + '.' + strings[int(name.attrib['name_index'])]
            result[label] = (layout(instance), layout(static))
    return result


def main():
    candidate = Path(sys.argv[1]).resolve()
    baseline = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / 'cache/v07-baseline'
    old_xml = baseline / 'host.xml'
    patched = set(json.loads(Path(sys.argv[3]).read_text(encoding='utf-8'))) if len(sys.argv) > 3 else set()
    assert patched <= {'fe.serv.Interact::0:1:move','fe.loc.Bonus::0:1:take',
                       'fe.unit.Unit::0:1:die','fe.unit.Unit::0:1:setCel','fe.unit.UnitPlayer::0:1:animate','fe.loc.Location::0:1:step'}, patched
    new_xml = candidate.with_suffix('.xml')
    before, after = abc_methods(old_xml), abc_methods(new_xml)
    preserved = 0
    for key, value in before.items():
        if key.startswith('fe.graph.Grafon::') or key in patched:
            continue
        other = after.get(key)
        if value is None:
            assert other is None, key
        else:
            assert other is not None and value[1].attrib['codeBytes'] == other[1].attrib['codeBytes'], key
        preserved += 1
    old_classes, new_classes = classes(old_xml), classes(new_xml)
    for name, value in old_classes.items():
        if name == 'fe.graph.Grafon':
            continue
        assert new_classes.get(name) == value, 'Class layout changed: ' + name
    # Existing pool indices must retain their meaning; appended renderer symbols
    # are fine. Raw unchanged bodies alone would not prove this requirement.
    a = ET.parse(old_xml).findall('.//abc/constants')
    b = ET.parse(new_xml).findall('.//abc/constants')
    assert len(a) == len(b)
    for ca, cb in zip(a, b):
        for pa in ca:
            pb = cb.find(pa.tag)
            assert pb is not None and len(pb) >= len(pa), pa.tag
            for index, old in enumerate(pa):
                assert layout(old) == layout(pb[index]) and old.text == pb[index].text, (pa.tag, index)
    result = {'passed': True, 'unchangedNamedMethodsAndInitializers': preserved,
              'unchangedClassLayouts': len(old_classes)-1, 'originalConstantPoolPreserved': True,
              'onlyRecompiledClass': 'fe.graph.Grafon',
              'patchedNativeMethods': sorted(patched),
              'sourceHostSHA256': hashlib.sha256((baseline/'pfe.swf').read_bytes()).hexdigest().upper(),
              'finalHostSHA256': hashlib.sha256(candidate.read_bytes()).hexdigest().upper()}
    output = Path(sys.argv[4]) if len(sys.argv) > 4 else candidate.with_suffix('.audit.json')
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
