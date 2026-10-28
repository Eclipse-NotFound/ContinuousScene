from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'unit-prestep-boundary-20261028'
names=('ProbeDoc.as','build_probe.py','run_functional.py')
origin={}
for name in names:
    data=(OLD/name).read_bytes();origin[str(OLD/name)]=hashlib.sha256(data).hexdigest().upper()
    text=data.decode('utf-8-sig')
    if name=='run_functional.py':
        before="HERE/'functional_runner.py'"
        assert text.count(before)==1
        text=text.replace(before,"HERE.parent/'unit-prestep-boundary-20261028/functional_runner.py'")
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)
with (HERE/'origin.json').open('x',encoding='utf-8') as stream:json.dump(origin,stream,indent=2)
print('Prepared trajectory-only successor; preserved original boundary probe and evidence')
