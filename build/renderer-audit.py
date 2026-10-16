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
    old_xml = ROOT / 'cache/v07-baseline/host.xml'
    new_xml = candidate.with_suffix('.xml')
    before, after = abc_methods(old_xml), abc_methods(new_xml)
    preserved = 0
    for key, value in before.items():
        if key.startswith('fe.graph.Grafon::'):
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
              'sourceHostSHA256': hashlib.sha256((ROOT/'cache/v07-baseline/pfe.swf').read_bytes()).hexdigest().upper(),
              'finalHostSHA256': hashlib.sha256(candidate.read_bytes()).hexdigest().upper()}
    candidate.with_suffix('.audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
