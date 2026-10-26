from pathlib import Path
import importlib.util
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('alpha_trim_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
content=patch.helper_source();patch.HELPER.parent.mkdir(parents=True,exist_ok=True)
if patch.HELPER.exists():assert patch.HELPER.read_text('utf-8-sig')==content
else:patch.HELPER.write_text(content,'utf-8')
source=(HERE.parent/'camera-native-light-crop-v2-20261027/run.py').read_text('utf-8-sig')
source=source.replace('camera-native-light-crop-2','camera-alpha-trim-1').replace('lightcrop-','alphatrim-')
source=source.replace("row['presentation']['parents']==1","row['presentation']['parents']==4")
source=source.replace("(1 if condition>=2 else 0)","(4 if condition>=2 else 0)")
source=source.replace('Only the native darkness bitmap display extent is cropped; light data and layers remain unchanged; real combat unproven.',
    'Only transparent native terrain margins are cropped; all source pixels unchanged; real combat unproven.')
source=source.replace('camera native light crop / 01a13816','camera transparent margins / 01a13816')
needle="    assert trial['version'] == VERSION and trial['complete'] and trial['passed'] and not trial['errors']"
assert source.count(needle)==1;source=source.replace(needle,needle+"\n    assert trial['nativeMenuChildren'] and 'visMainMenu' not in trial['nativeMenuChildren']")
needle="        assert row['cached'] is (condition>=2) and row['moving'] is (condition%2==1) and row['startAtMs'] == previous"
assert source.count(needle)==1;source=source.replace(needle,needle+"\n        if condition>=2:\n            assert all(p['visibleBitmaps']>0 and p['trimmedBitmaps']>0 and p['visibleCroppedPixels']<p['visibleNativePixels'] for p in row['presentation'])")
target=HERE/'run.py'
if target.exists():assert target.read_text('utf-8-sig')==source
else:target.write_text(source,'utf-8')
print('Prepared alpha-bound native crop and unchanged 13-view / 960-frame gates')
