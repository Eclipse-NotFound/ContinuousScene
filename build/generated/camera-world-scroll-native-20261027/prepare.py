"""Prepare a new immutable recipe; do not alter the earlier failed runs."""
from pathlib import Path
import ast
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_scroll_probe_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():assert path.read_text('utf-8-sig')==text,path
    else:path.write_text(text,'utf-8')

write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-world-scroll-phases-20261027/run.py').read_text('utf-8-sig')
for before,after in [
    ('camera-world-scroll-phases-1','camera-world-scroll-native-1'),
    ("phase['snapshots']==480","phase['snapshots']>=480"),
    ("assert entry==expected or entry==native_entry","assert entry==expected"),
    ("assert reposition_count==phase['nativeEntryRepositions']", "assert reposition_count==phase['nativeEntryRepositions']==0\n    assert trial['nativePositionChecks']==240"),
    ("'Original camera transform writes retained before scroll setup; not a host camera rewrite.',", "'Only two world x/y setters are skipped under scrollRect in an exact isolated host; SATS and all other native calculations retained.',\n                'Latest EXIT_FRAME states retained; callback count is not a count of physical presentations.',"),
    ("record=dict(version=VERSION,options=options(args.name),diagnosticOnly=True,deployed=False)",
     "host=json.loads((HERE/'host-build.json').read_text('utf-8-sig'))\n    assert host['base']==PINS['pfe.swf'] and host['diagnosticOnly'] and not host['deployed']\n    assert r.sha(HERE/'pfe.swf')==host['candidate'] and r.sha(HERE/'audit-proof.json')==host['audit']\n    record=dict(version=VERSION,options=options(args.name),diagnosticOnly=True,deployed=False,hostReceipt=host)"),
    ("m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)",
     "m.prepare();shutil.copy2(probe['probePath'],m.RUNTIME/base.PROBE_PATH)\n            shutil.copy2(HERE/'pfe.swf',m.RUNTIME/'pfe.swf')\n            assert r.sha(m.RUNTIME/'pfe.swf')==host['candidate']"),
    ("if key not in ('application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key",
     "if key not in ('pfe.swf','application.xml','mods/loader-manifest.txt'):assert r.sha(m.RUNTIME/key)==digest,key"),
    ("if key not in ('application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key",
     "if key not in ('pfe.swf','application.xml','mods/loader-manifest.txt'):assert actual[key]==digest,key\n            assert actual['pfe.swf']==host['candidate']"),
    ("lease.note='480 attribution-only uncached scroll frames; visual rejection retained; diagnostic only, no deployment'",
     "lease.note='480 isolated-host scroll intervals; exact world positions at next entry; visual rejection retained; no deployment'"),
]:
    assert before in s,before;s=s.replace(before,after)
ast.parse(s);write(HERE/'run.py',s)
print('Prepared exact native setter-suppression diagnostic; unchanged RGB2 acceptance')
