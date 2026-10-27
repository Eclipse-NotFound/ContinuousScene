"""Exact reviewed tooling transitions; historical receipts remain immutable."""
from pathlib import Path
import hashlib
OLD_REGISTRY='8B35A6D6CA1DD94CFD5CBA9A42979EBD14D9AE65497688FA859D084425922049'
PREVIOUS_REGISTRY='E9F51CB75420C507F6DB1D96BE6B1430374B0B7A797607FF4438A695A717809E'
NEW_REGISTRY='E3E43581D677D26C83B7E887C64669634CCC8D901AEFA5A826E1CFED8A5F0CF0'
OLD_LAUNCHER='628FFED886DB293ABE0177FD42C61AC09482E04AEE6AAE358CF2E3D6DEB0D1F9'
NEW_LAUNCHER='ECE3ED087D9E31AC4EC91FA1E7B7F82985A149D503C55E682C1C2241027CC3B0'
RESOURCES='86D5F280320DE95DC7DFEDA27020DBCCF432668BB7D2D0DB8C9F3D93FF55CFCB'
def tool_paths(ref):
    tools=ref.r.ROOT/'mods/ModLoader/tools'
    paths=[tools/'air_test_process.py',tools/'test_resources.py']
    for p,d in zip(paths,[NEW_LAUNCHER,RESOURCES]):assert ref.r.sha(p)==d,str(p)
    return paths
def read_seed(ref):
    r=ref.r;tool_paths(ref)
    registryBytes=(r.ROOT/'mods/ModLoader/tools/test_registry.py').read_bytes()
    changed=b'text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=15, check=True,'
    original=b'text=True, capture_output=True, timeout=15, check=True,'
    assert registryBytes.count(changed)==1
    assert hashlib.sha256(registryBytes.replace(changed,original)).hexdigest().upper()==PREVIOUS_REGISTRY
    assert r.sha(ref.SEED)==ref.SEED_SHA
    value=r.read(ref.SEED);original=Path(value['probePath']).parent/'probe-build.json'
    assert r.sha(original)==ref.SEED_SHA and r.read(original)==value
    tools=r.ROOT/'mods/ModLoader/tools'
    transitions={(tools/'test_registry.py').resolve():(OLD_REGISTRY,NEW_REGISTRY),
        (tools/'air_test_process.py').resolve():(OLD_LAUNCHER,NEW_LAUNCHER)}
    seen=set()
    for field in ('runnerInputs','compilerInputs','candidateInputs'):
        for path,digest in value[field].items():
            p=Path(path);actual=r.sha(p)
            if p.resolve() in transitions:
                assert field=='runnerInputs' and (digest,actual)==transitions[p.resolve()]
                assert p.resolve() not in seen;seen.add(p.resolve())
            else:assert actual==digest,(field,path)
    assert seen==set(transitions)
    checked=ref.base.verify_probe(original,value['productionSHA256'],value['runnerInputs'],value['compilerInputs'],value['candidateInputs'])
    assert checked==value and value['probeSHA256']==ref.PROBE_SHA==ref.patch.SOURCE_PROBE
    assert len(value['frozenSourceSHA256'])==85 and value['denseFixture']==ref.FIXTURE
    assert r.sha(Path(value['sourceOrigin']))==value['sourceOriginSHA256']
    assert r.read(Path(value['sourceOrigin']))['stagedSHA256']==value['frozenSourceSHA256']
    return value
def fixture_inputs(ref):
    value=read_seed(ref)
    return {str(p):ref.r.sha(p) for p in [ref.SEED,Path(value['probePath']),Path(value['configPath']),
        Path(value['sourceOrigin']),Path(value['probePath']).parent/'probe-build.json',
        ref.HERE/'probe_patch.py',ref.HELPER,ref.support.OUT/'source-provenance.json',*tool_paths(ref)]}
