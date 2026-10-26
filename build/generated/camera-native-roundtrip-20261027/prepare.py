from pathlib import Path
import importlib.util
import ast
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_roundtrip_patch',HERE/'probe_patch.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
def write(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_text('utf-8-sig')==s,p
    else:p.write_text(s,'utf-8')
write(patch.HELPER,patch.helper_source())
s=(HERE.parent/'camera-display-state-20261027/run.py').read_text('utf-8-sig')
s=s.replace('camera-display-state-1','camera-native-roundtrip-1')
start=s.index('def summarize(raw):')
end=s.index('\n\ndef main():',start)
s=s[:start]+'''def summarize(raw):
    trial=raw['cameraRaster']
    assert trial['version']==VERSION and trial['nativeRoundtripOnly']
    assert raw['ok'] and trial['complete'] and trial['passed'] and not trial['errors']
    assert not trial['framesMs'] and trial['nativeRepeat']['equal']
    assert len(trial['pixels'])==1 and trial['pixels'][0]['passed']
    assert len(trial['pixels'][0]['conditions'])==3
    assert all(row['restored']['equal'] and row['repeat']['equal'] for row in trial['pixels'][0]['conditions'])
    assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==11
    assert trial['cleanup']['restored'] and not trial['cleanup']['errors']
    return dict(version=VERSION,complete=True,diagnosticOnly=True,performanceEligible=False,deployed=False,
        arms={},pairs=[],pixels=trial['pixels'],cleanup=trial['cleanup'],measurementFrames=0,
        limits=['Natural camera round-trip pixel invariance only; no display layer changes and no performance claim.'])
'''+s[end:]
s=s.replace('camera display contribution / 01a13816','native camera roundtrip / 01a13816')
ast.parse(s);write(HERE/'run.py',s)
print('Prepared native camera-only round trips; no alpha suppression')
