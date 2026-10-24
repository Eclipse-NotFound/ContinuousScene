"""Prepare six source-method replacements only; never import, launch, or deploy.

The historical Grafon source is deliberately NOT emitted as a complete class:
it predates the installed tint repair. Each selected method must still match
the installed A796 method semantically before it may be used as a patch seed.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys
import uuid
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
B = HERE.parents[1]
ROOT = B.parents[2]
SOURCE = B / 'generated/motion-direction-rays/source/fe/graph/Grafon.as'
BASE_XML = B / 'generated/fog-typed/pfe.xml'
HOST_XML = B / 'generated/scene-compat-20261024/tint/product/pfe.xml'
FRAGMENT = HERE / 'candidate/scene-crop-presentation.as.inc'
HOST = 'A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
PINS = {
    SOURCE: '75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB',
    BASE_XML: 'E5DBF6959F268078B99F0111EB9720F49C2759C1837C82486D9638A17AB92A66',
    HOST_XML: '1D2642C7D55D1F97121738E6AE84996A140EBFEFF686E6706C88CEF82A7338DA',
    ROOT / 'pfe.swf': HOST,
}
TARGETS = ['sceneClear', 'sceneDrop', 'sceneCullSurfaces', 'sceneApply',
           'sceneFinishBatch', 'sceneSats']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def once(text, before, after):
    assert text.count(before) == 1, (before, text.count(before))
    return text.replace(before, after)


def replacements(original):
    changed = dict(original)
    changed['sceneClear'] = once(changed['sceneClear'],
        '         this.sceneChunks = {}; this.sceneResident = 0;',
        '         this.sceneCropClear();\n         this.sceneChunks = {}; this.sceneResident = 0;')
    changed['sceneDrop'] = once(changed['sceneDrop'],
        '         for each(var nativeBuffer:BitmapData in entry.nativeBuffers) nativeBuffer.dispose();',
        '         this.sceneCropRelease(entry);\n         for each(var nativeBuffer:BitmapData in entry.nativeBuffers) nativeBuffer.dispose();')
    changed['sceneCullSurfaces'] = once(changed['sceneCullSurfaces'],
        '         var view:Rectangle = this.sceneViewport();',
        '         var cropAllowed:Boolean = this.sceneCropAllowed();\n         var view:Rectangle = this.sceneViewport();')
    changed['sceneCullSurfaces'] = once(changed['sceneCullSurfaces'],
        '         key += ":" + this.sceneResident;',
        '         key += ":" + this.sceneResident + ":" + cropAllowed;')
    changed['sceneCullSurfaces'] = once(changed['sceneCullSurfaces'],
        '         this.sceneCullKey = key;',
        '''         this.sceneCullKey = key;
         // Reclaim leaving tiles first, before allocating entering tiles.
         for each(var leaving:Object in this.sceneChunks)
            if(view != null && !view.intersects(new Rectangle(leaving.cx * this.sceneSide,leaving.cy * this.sceneSide,this.sceneSide,this.sceneSide)))
               this.sceneCropSetVisible(leaving,false,cropAllowed);''')
    changed['sceneCullSurfaces'] = once(changed['sceneCullSurfaces'],
        '            for each(var bitmap:Bitmap in surface.bitmaps)',
        '            this.sceneCropSetVisible(surface,visible,cropAllowed);\n            for each(var bitmap:Bitmap in surface.bitmaps)')
    changed['sceneApply'] = once(changed['sceneApply'],
        '         this.sceneLastDirtyCount = 0;',
        '         var cropWriteComplete:Boolean = false;\n         this.sceneLastDirtyCount = 0;')
    changed['sceneApply'] = once(changed['sceneApply'],
        '               ++entry.revision; ++this.sceneLastDirtyCount;',
        '               ++entry.revision; ++this.sceneLastDirtyCount;\n               this.sceneCropSync(entry,kind);')
    changed['sceneApply'] = once(changed['sceneApply'],
        '            }\n         }\n         finally',
        '            }\n            cropWriteComplete = true;\n         }\n         finally')
    changed['sceneApply'] = once(changed['sceneApply'],
        '            this.sceneX = ox; this.sceneY = oy; this.sceneRasterizing = false; this.sceneStamp = null;',
        '            this.sceneX = ox; this.sceneY = oy; this.sceneRasterizing = false; this.sceneStamp = null;\n            if(!cropWriteComplete) this.sceneCropAbort();')
    # Preserve the original exception restoration exactly; only display-copy
    # errors are handled inside the new helper, never native drawing errors.
    changed['sceneFinishBatch'] = once(changed['sceneFinishBatch'],
        '         this.sceneRasterizing = false;',
        '         this.sceneRasterizing = false;\n         for each(var surface:Object in this.sceneChunks) this.sceneCropSync(surface,"batch");')
    body = changed['sceneSats']
    opening, closing = body.index('{'), body.rfind('}')
    changed['sceneSats'] = (body[:opening + 1] +
        '\n         this.sceneCropSuspend();\n         try\n         {\n' + body[opening + 1:closing] +
        '\n         }\n         finally { this.sceneCropResume(); }\n      ' + body[closing:])
    assert all(changed[name] != original[name] for name in TARGETS)
    return changed


def prepare():
    for path, expected in PINS.items():
        assert sha(path) == expected, 'Pinned input changed: ' + str(path)
    inputs = {str(p): sha(p) for p in [Path(__file__), SOURCE, BASE_XML, HOST_XML,
              ROOT / 'pfe.swf', FRAGMENT, B / 'profile-vision.py', B / 'native-crop-audit.py']}
    core = load('camera_crop_compare', B / 'native-crop-audit.py')
    parser = load('camera_crop_source_parser', B / 'profile-vision.py')
    def read_abc(path):
        return next(a for node in ET.parse(path).findall('.//abc')
                    for a in [core.ABC(node)] if 'fe.graph.Grafon' in a.class_by_name)
    before, installed = read_abc(BASE_XML), read_abc(HOST_XML)
    comparator = core.Compare(before, installed)
    selected = {}
    for name in TARGETS:
        label = 'fe.graph.Grafon::0:1:' + name
        comparator.body(before.named[label], installed.named[label], label)
        selected[name] = dict(baseIndex=before.named[label], installedIndex=installed.named[label],
            installedCodeSHA256=hashlib.sha256(bytes.fromhex(installed.bodies[installed.named[label]].get('codeBytes'))).hexdigest().upper())
    source = SOURCE.read_text('utf-8-sig')
    original = {}
    for name in TARGETS:
        a, z = parser._body(source, name)
        head = re.search(r'^      (?:private|public) function ' + name + r'\s*\(', source, re.M)
        assert head and head.start() < a
        original[name] = source[head.start():z + 1]
    candidate = replacements(original)
    folder = HERE / 'prepared' / uuid.uuid4().hex
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'original-methods.as.inc').write_text('\n\n'.join(original.values()) + '\n', 'utf-8')
    (folder / 'candidate-methods.as.inc').write_text('\n\n'.join(candidate.values()) + '\n', 'utf-8')
    (folder / 'scene-crop-presentation.as.inc').write_bytes(FRAGMENT.read_bytes())
    assert inputs == {p: sha(Path(p)) for p in inputs}, 'Inputs changed during preparation'
    report = dict(version='camera-crop-guarded-1', host=HOST, prepared=True,
        compiledHost=False, launchedAir=False, deployed=False, performanceEligible=False,
        selectedMethods=selected, inputs=inputs,
        outputs={p.name: sha(p) for p in folder.iterdir()},
        sourceScope='Only these six method replacements plus helper; do not rebuild the historical complete Grafon class.',
        pending=['exact host assembly and full untouched-method/layout audit', 'integer pixels and actual benefit',
                 'fractional/zoom/shake native fallback', 'SATS and live combat edits', 'RV/WB/LAD compatibility'])
    (folder / 'preparation.json').write_text(json.dumps(report, indent=2), 'utf-8')
    return folder, report


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'mods/ModLoader/tools'))
    from test_registry import Registration
    with Registration(owner='ContinuousScene / guarded crop preparation / 01a13816',
                      purpose='Offline six-method provenance and source preparation; no AIR',
                      resource='offline', run_dir=HERE, evidence=HERE / 'prepared', wait=0) as lease:
        folder, report = prepare()
        lease.outcome = 'passed'
        lease.note = 'Six original methods match installed A796; source candidate prepared only'
        print(json.dumps(dict(prepared=str(folder), methodCount=len(report['selectedMethods']),
                              compiledHost=False, launchedAir=False, deployed=False)))
