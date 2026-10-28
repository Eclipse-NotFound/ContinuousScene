from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'unit-run-regression-20261028'
origin={}
for name in ('ContinuousSceneMotionMod.as','ProbeDoc.as','build_probe.py','run_functional.py'):
    data=(OLD/name).read_bytes();origin[str(OLD/name)]=hashlib.sha256(data).hexdigest().upper()
    text=data.decode('utf-8-sig')
    if name=='ContinuousSceneMotionMod.as':
        old=',shX1:u.shX1,shX2:u.shX2'
        assert text.count(old)==1
        text=text.replace(old,'')
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
with (HERE/'origin.json').open('x',encoding='utf-8') as stream:json.dump(origin,stream,indent=2)
print('Removed protected probe fields; failed v1 evidence preserved')
