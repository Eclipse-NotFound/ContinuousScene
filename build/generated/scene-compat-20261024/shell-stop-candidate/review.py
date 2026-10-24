"""Read retained runs; record the normal-mode wrapper error without rewriting it."""
from pathlib import Path
import importlib.util
import json
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('shell_combat_review', HERE/'combat_run.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
r = c.r


def main():
    destination = HERE/'combat-review.json'
    assert not destination.exists(), 'Keep previous review evidence'
    entries = []
    baselines = []
    accepted = []
    for name, mode, complete in (
        ('shell-stop-20261024-baseline-r1', 'scene', True),
        ('shell-stop-20261024-candidate-r1', 'scene', False),
        ('shell-stop-20261024-candidate-r2', 'scene', False),
        ('shell-stop-20261024-normal-baseline-r1', 'normal', True)):
        folder = r.E/name
        raw = r.read(folder/'storage/result.json')
        original = r.read(folder/'summary.json')
        record = r.read(folder/'runner-inputs.json')
        inputs = {k.replace('\\','/'):v for k,v in r.read(folder/'inputs.json').items()}
        policy = r.read(folder/'process-policy.json')
        baselines.append(record['baseline'])
        assert record['seedReceiptSHA256'] == c.SEED_SHA
        assert record['probeSHA256'] == c.PROBE == inputs[c.base.PROBE_PATH]
        assert inputs['pfe.swf'] == record['hostSHA256']
        assert not policy.get('runFailure') and not policy.get('memoryAbort') and not policy.get('otherAirProcessIds')
        for key, digest in record['baseline'].items():
            if key not in ('application.xml', 'mods/loader-manifest.txt'):
                assert inputs[key] == (record['hostSHA256'] if key == 'pfe.swf' else digest)
        evidence = {str(p.relative_to(folder)):r.sha(p) for p in
            (folder/'storage/result.json', folder/'summary.json', folder/'runner-inputs.json',
             folder/'inputs.json', folder/'process-policy.json', folder/'probe-build.json')}
        row = dict(name=name, mode=mode, completeNativeWorkload=complete,
            originalRunnerGatePassed=complete and mode=='scene', hostSHA256=inputs['pfe.swf'],
            completeSegments=len(raw['samples']), error=raw.get('error'), evidence=evidence)
        if complete:
            r.result(name)
            assert raw['ok'] and raw.get('error') is None
            assert len(raw['assertions']) == (21 if mode=='normal' else 26)
            summary = c.dense.summarize(raw, SimpleNamespace(mode=mode, name=name))
            assert summary['qualification']['passed'] and summary['continuous']['count'] == 1200
            if mode == 'normal':
                assert original['incomplete'] and original['error'] == 'AssertionError()'
                row['wrapperCorrection'] = 'Normal mode omits four scene exit/arrow checks and one scene chunk-size check; 21 is the expected count. Original failed receipt stays unchanged.'
            else:
                assert original['continuous'] == summary['continuous']
            row.update(acceptedDataBoundary='Full native workload and continuous frame data only; no candidate benefit acceptance',
                checks=len(raw['assertions']), continuous=summary['continuous'], qualification=summary['qualification'])
            accepted.append(summary)
        else:
            assert not raw['ok'] and 'Native input left the verified full platform' in raw['error']
            assert original['incomplete'] and not original['qualification']['passed']
            row.update(acceptedDataBoundary='Failure and partial observations only; excluded from complete performance comparison',
                partialFrames=sum(len(s['continuousFramesMs']) for s in raw['samples']))
        entries.append(row)
    assert all(x == baselines[0] for x in baselines)
    first, second = accepted
    for key in ('normalizedRoute','nativeRouteHash','selectedCombatCorridorTiles','viewport'):
        assert first[key] == second[key], key
    c.seed()
    result = dict(version='shell-stop-combat-review-1', originalNormalRunnerGatePassed=False,
        sourceSHA256=r.sha(Path(__file__)), installedInputsStillMatch=r.baseline()==baselines[0],
        sameFormalInputs=True, sameFrozenProbe=True, sameNormalizedTerrainAndViewport=True,
        runs=entries, candidatePerformanceAccepted=False, deployed=False,
        disposition='Stop shell candidate: no complete valid candidate comparison; two native route failures retained, cause not established.',
        limitations=['Scene and normal modes differ in population and active enemies; their gap is not a single-function causal cost.',
            'The original failed normal runner is not relabeled; only its independently checked raw workload is accepted here.',
            'No partial candidate windows are used to claim a speedup or deterministic regression.'])
    r.save(destination, result)
    print(json.dumps(dict(review=str(destination), sameInputs=True,
        scene=first['continuous']['metrics'], normal=second['continuous']['metrics'],
        candidatePerformanceAccepted=False, installedInputsStillMatch=result['installedInputsStillMatch'])))


if __name__ == '__main__': main()
