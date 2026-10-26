"""Reuse immutable game source after the separately authorized registry repair.

Historical results and receipts are never rewritten. Exactly one tooling input
may differ, at the two pinned hashes below; all other inputs remain checked.
"""
from pathlib import Path

OLD_REGISTRY='8B35A6D6CA1DD94CFD5CBA9A42979EBD14D9AE65497688FA859D084425922049'
NEW_REGISTRY='E9F51CB75420C507F6DB1D96BE6B1430374B0B7A797607FF4438A695A717809E'

def read_seed(ref):
    r=ref.r
    assert r.sha(ref.SEED)==ref.SEED_SHA
    value=r.read(ref.SEED)
    original=Path(value['probePath']).parent/'probe-build.json'
    assert r.sha(original)==ref.SEED_SHA and r.read(original)==value
    registry=(r.ROOT/'mods/ModLoader/tools/test_registry.py').resolve()
    allowed=0
    for field in ('runnerInputs','compilerInputs','candidateInputs'):
        for path,digest in value[field].items():
            actual=r.sha(Path(path))
            if Path(path).resolve()==registry:
                assert field=='runnerInputs' and digest==OLD_REGISTRY and actual==NEW_REGISTRY
                allowed+=1
            else:assert actual==digest,(field,path)
    assert allowed==1
    # Verify source, compiled probe, compiler config/log, source provenance and
    # original receipt against its historical inputs, not a relabelled receipt.
    checked=ref.base.verify_probe(original,value['productionSHA256'],value['runnerInputs'],
        value['compilerInputs'],value['candidateInputs'])
    assert checked==value and value['probeSHA256']==ref.PROBE_SHA==ref.patch.SOURCE_PROBE
    assert len(value['frozenSourceSHA256'])==85 and value['denseFixture']==ref.FIXTURE
    assert r.sha(Path(value['sourceOrigin']))==value['sourceOriginSHA256']
    origin=r.read(Path(value['sourceOrigin']))
    assert origin['stagedSHA256']==value['frozenSourceSHA256']
    return value

def fixture_inputs(ref):
    value=read_seed(ref)
    return {str(p):ref.r.sha(p) for p in [ref.SEED,Path(value['probePath']),Path(value['configPath']),
        Path(value['sourceOrigin']),Path(value['probePath']).parent/'probe-build.json',
        ref.HERE/'probe_patch.py',ref.HELPER,ref.support.OUT/'source-provenance.json']}
