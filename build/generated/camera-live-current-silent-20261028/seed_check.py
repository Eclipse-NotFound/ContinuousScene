"""Create one private silent settings seed and verify it without starting AIR."""
from pathlib import Path
import hashlib
import importlib.util
import json
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('native_silence_seed_check', HERE / 'silence.py')
silence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(silence)
root = HERE.parents[4]
app_id = 'pfe-modsettings-continuous-motion-' + uuid.uuid4().hex
doc = ET.fromstring((root / 'application.xml').read_bytes())
namespace = doc.tag.split('}')[0] + '}'
doc.find(namespace + 'id').text = app_id
descriptor = silence.RUNTIME.resolve(strict=True) / (app_id + '.xml')
with descriptor.open('xb') as stream:
    stream.write(ET.tostring(doc, encoding='utf-8', xml_declaration=True))
receipt = silence.seed(descriptor, silence.RUNTIME)
assert receipt['snd'] == dict(globalVol=0, stepVol=0, musicVol=0)
assert receipt['sha256'] == '12CC4E62A459EAFDA8463F800F8E1E8388CC392AC6A5BDD882D14C572435B257'
try:
    silence.seed(descriptor, silence.RUNTIME)
except ValueError as error:
    assert str(error) == 'Fresh application storage already exists', str(error)
else:
    raise AssertionError('Existing seed was not rejected')
assert silence.verify_retained(receipt['path']) == receipt['snd']
receipt.update(airStarted=False, duplicateRefused=True,
               helperSHA256=hashlib.sha256((HERE / 'silence.py').read_bytes()).hexdigest().upper())
target = HERE / 'seed-checks'
target.mkdir(exist_ok=True)
with (target / (app_id + '.json')).open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, ensure_ascii=False, indent=2)
print(json.dumps(receipt, ensure_ascii=False))
