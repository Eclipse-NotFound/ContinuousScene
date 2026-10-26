"""Generate an explicit runner from the unchanged native-axis guard set."""
from pathlib import Path
import hashlib

HERE=Path(__file__).resolve().parent
source=(HERE.parent/'camera-axis-motion-20261025/run.py').read_text('utf-8-sig')
edits=[
 ('VERSION = \'camera-axis-motion-1\'',"VERSION = 'camera-terrain-layers-1'"),
 ('PINS = dict(reference.PINS)', '''PINS = dict(reference.PINS)
RC_RECEIPT=HERE.parents[4]/'mods/RConnect/build/m52/a-live-animation-deploy-01/verified.json'
RC_CURRENT='2C49DFD05D524085EA43FB8FFA537D1A9359FEBD52FB13D6A19FAAE6E2563621'
PINS['mods/Rconnect/release/RConnectMod.swf']=RC_CURRENT'''),
 ('def runner_inputs():', '''def runner_inputs():
    assert r.sha(RC_RECEIPT)=='5446D95AAA1552622CF1E691BBDE5C962875897014CF5C06A452A95037ACBC3B'
    rc=r.read(RC_RECEIPT)
    assert rc['status']=='verified' and rc['version']=='0.2.24-animfix1' and rc['release_sha256'].upper()==RC_CURRENT'''),
 ("Path(reference.__file__), HERE/'run.py', HERE/'README.md', HERE/'probe_patch.py',", "Path(reference.__file__), HERE/'run.py', HERE/'README.md', HERE/'probe_patch.py', HERE/'prepare_runner.py', RC_RECEIPT,"),
 ("assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==10", "assert trial['pixelBitmapsCreated']==trial['pixelBitmapsDisposed']==35\n    assert cleanup['terrainRestored']"),
 ("    for row in trial['pixels']:\n        c=row['nativeRepeat'];assert row['passed'] and c['equal'] and c['differentPixels']==c['maxRGB']==c['maxAlpha']==0", '''    for row in trial['pixels']:
        assert row['passed'] and len(row['conditions'])==3
        for mode,item in enumerate(row['conditions'],1):
            assert item['condition']==mode
            c=item['restored'];assert c['equal'] and c['differentPixels']==c['maxRGB']==c['maxAlpha']==0
    for i in range(3):assert any(row['conditions'][i]['changed']['differentPixels']>0 for row in trial['pixels'])'''),
 ("('native-static','native-horizontal','native-vertical','native-combined')", "('native-moving','back-hidden-moving','front-hidden-moving','terrain-hidden-moving')"),
 ("row['moving'] is (condition!=0)","row['moving'] is True"),
 ("'workMs','worldVisible','windowVisible'):","'workMs','worldVisible','windowVisible','terrain'):"),
 ("        assert (len(xs)>1)==(condition in (1,3)) and (len(ys)>1)==(condition in (2,3))", '''        assert len(xs)>1 and len(ys)>1
        expected=[bool(initial_visible and not (condition & (1 if j<2 else 2))) for j,initial_visible in enumerate(trial['terrainInitial'])]
        assert all(value==expected for value in row['terrain'])
        if i:assert row['vx']==trial['windows'][0]['vx'] and row['vy']==trial['windows'][0]['vy']'''),
 ("movementMinusStaticMs=", "suppressedMinusNativeMs="),
 ("'Native world stays visible in every interval; static versus axis movement, no rendering optimization.'", "'All windows move the camera identically; terrain suppression is diagnostic, not a gameplay proposal.'"),
 ('camera axis motion / 01a13816','camera terrain layers / 01a13816'),
 ('960 native paused camera axis frames; diagnostic only, no deployment','960 moving camera terrain-layer controls; diagnostic only, no deployment')
]
out=source
for old,new in edits:
    assert out.count(old)==1,(old,out.count(old))
    out=out.replace(old,new,1)
target=HERE/'run.py'
if target.exists():assert target.read_text('utf-8-sig')==out
else:target.write_text(out,'utf-8')
print({'runner':hashlib.sha256(target.read_bytes()).hexdigest().upper()})
