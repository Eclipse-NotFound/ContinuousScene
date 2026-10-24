"""Source-only, one-statement recipe. No compiler, host writes, or runtime code.

The historical Grafon source is a method donor, NOT a replacement for A796's
whole class. A future builder must retain only this method in exact A796.
"""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
GENERATED = HERE.parent
SOURCE = GENERATED / 'motion-direction-rays/source/fe/graph/Grafon.as'
TARGET = 'fe.graph.Grafon::0:1:scenePreloadRegions'
HOST_SHA256 = 'A796827173AF7D6FAB9885FB66ECC62182AB5335918A30C7CCE4C44914A238B7'
SOURCE_SHA256 = '75157C9397AAC37163AB5CE6A8A872D7451CB723B35E87C6BF48EFE3969D38EB'
METHOD_SHA256 = '62076B8C4CB76AF3EBCE8AB4994A86D8D91C277EC36DDFA3E627368A2C24F9F0'
CHANGED_METHOD_SHA256 = '48A7FE260D46E16C12706BE751EE799001C971CD0E9E5A3DE83F261E74649A2D'
START = b'      private function scenePreloadRegions() : Boolean\r\n'
END = b'      private var sceneNativeEnvironments:'
OLD = b'                  for(n = 0; n < 4; ++n) surface.nativeBuffers[n].copyPixels(buffers[n],source,point);\r\n'
NEW = b'                  ++surface.revision;\r\n' + OLD
AUDITS = {
    'fog-typed/strict-audit.json': '5EA30684ADA25B28EBD70E4C93C0D0365F385E134CF1F18C36B111DCAF003838',
    'fog-typed/provenance.json': 'A7568546F8919C937B603CA29ACEFFA9036EE5ED8D3C510C32077E215587200A',
    'combat-near-native-20261023/logic-profile-audit/fog-last-blocker-production-minimal/semantic-audit.json': 'D239A9D614C26F2704E6ED7E6F452ABF49D6D27E0A98CB58EE9BD933F0E19A66',
    'vertical-camera-band-20261023/semantic-audit.json': 'F8147E6F0E6939E65387F5A15FE9E80322EF925A306096F8816A490F401AE4B1',
    'scene-compat-20261024/tint/product/semantic-audit.json': '0A24C942735D105956DAC367B8097A34E1DA57F747403080493C917B61F5CF83',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def extract_target(source: bytes) -> bytes:
    require(sha(source) == SOURCE_SHA256, 'Frozen historical source mismatch')
    require(source.count(START) == 1 and source.count(END) == 1, 'Ambiguous method boundaries')
    start = source.index(START)
    end = source.index(END, start)
    method = source[start:end]
    require(sha(method) == METHOD_SHA256, 'Frozen target method mismatch')
    return method


def transform(method: bytes) -> bytes:
    require(sha(method) == METHOD_SHA256, 'Only the exact unmodified target is accepted')
    require(method.count(OLD) == 1 and NEW not in method, 'Target insertion is not unique')
    result = method.replace(OLD, NEW, 1)
    require(sha(result) == CHANGED_METHOD_SHA256, 'Unexpected transformed method')
    return result


def reverse(method: bytes) -> bytes:
    require(sha(method) == CHANGED_METHOD_SHA256, 'Only the exact changed target is accepted')
    require(method.count(NEW) == 1, 'Reverse insertion is not unique')
    result = method.replace(NEW, OLD, 1)
    require(sha(result) == METHOD_SHA256, 'Reverse did not restore the target')
    return result


def check() -> dict:
    """Read small provenance records and source; do not parse XML or write files."""
    records = {}
    for rel, expected in AUDITS.items():
        raw = (GENERATED / rel).read_bytes()
        require(sha(raw) == expected, 'Historical audit changed: ' + rel)
        records[rel] = json.loads(raw)
    first = records['fog-typed/strict-audit.json']
    origin = records['fog-typed/provenance.json']
    require(first['passed'] and first['changedMethods'] == ['fe.loc.Location::0:1:lighting'], '81C1 -> BEFC target preservation failed')
    require(origin['base'] == '81C1BFB552AA8EFBB20CCF15CB404AB5D879F58515B466FF788A079F5F0EC015', 'Unexpected source host')
    prior = origin['sha256']
    for rel in list(AUDITS)[2:]:
        audit = records[rel]
        require(audit['passed'] and audit['baseSHA256'] == prior, 'Broken host audit chain')
        require(audit['actualChangedBodies'] == audit['allowedChangedMethods'] and TARGET not in audit['actualChangedBodies'], 'Target changed in host chain')
        prior = audit['candidateSHA256']
    require(prior == HOST_SHA256, 'Audit chain does not end at A796')
    source = SOURCE.read_bytes()
    method = extract_target(source)
    changed = transform(method)
    require(reverse(changed) == method, 'Byte-exact reverse failed')
    require(source.count(method) == 1 and source.count(OLD) == 1, 'Whole-source insertion ambiguous')
    staged = source.replace(method, changed, 1)
    require(staged.replace(changed, reverse(changed), 1) == source, 'Non-target bytes changed')
    negatives = [(extract_target, source + b' '), (transform, method.replace(b'point);', b'point );', 1)),
                 (transform, method.replace(b'\r\n', b'\n')), (transform, changed),
                 (reverse, method), (reverse, changed.replace(b'++surface.revision;', b'--surface.revision;', 1))]
    for action, bad in negatives:
        try:
            action(bad)
        except ValueError:
            continue
        raise ValueError('Negative control was accepted')
    return dict(version='scene-raster-invalidation-source-1', target=TARGET,
                hostSHA256=HOST_SHA256, sourcePath=str(SOURCE), sourceSHA256=sha(source),
                methodSHA256=sha(method), changedMethodSHA256=sha(changed),
                insertedStatements=1, originalBytesPreserved=True, exactReverse=True,
                negativeControlsRejected=len(negatives), provenanceChain=AUDITS,
                compiled=False, runtimeTested=False, deployed=False,
                wholeHistoricalClassIsNotA796=True)


if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False, indent=2))
