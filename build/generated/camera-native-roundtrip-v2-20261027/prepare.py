from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('roundtrip_patch_v2',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-native-roundtrip-20261027/run.py').read_text('utf-8-sig')
write(HERE/'run.py',s.replace('camera-native-roundtrip-1','camera-native-roundtrip-2'))
print('Prepared 3D-aware native camera round-trip metadata')
