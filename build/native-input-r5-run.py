"""R5 null-node rejection diagnostic: early pixels, then the same frozen probe's short ABBA.

Reuses the r3 harness/receipt schema and unchanged r2 CS binary. Only the frozen
helper override is r5; a historical r2/r3/r4 pixel check cannot qualify timing.
"""
from pathlib import Path
import contextlib
import importlib.util
import io
import json
import sys

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load('native_input_r5_harness', B / 'native-input-r3-run.py')
builder = load('native_input_r5_builder', B / 'sleeping-root-r5-build.py')
r = runner.r
runner.builder = builder
runner.OUT = B / 'generated/native-input-r5-20261023'
runner.HELPER_SOURCE = builder.OUT / 'probe-helper/SceneSleepingRootPresentation.as'
runner.HELPER_SHA = 'B9700C1B866423B7BF3E51926214B0788402691A826C9743FD9ABEB335FA9081'
runner.PROOF_SHA = 'F171B93F16EF9A277E7F7FB1DAEAFDE0173E0818C33B993151AAFB5B2736C1ED'
runner.BUILDER_SHA = '9166EED000CA5082076196EE71E443B0A29847B262BAE554F815ACA39D6483A4'


def runner_inputs():
    values = runner.base.runner_inputs()
    for path in (Path(__file__), B / 'native-input-r3-run.py', B / 'sleeping-root-r5-build.py',
                 B / 'sleeping-root-r4-build.py', B / 'sleeping-root-r3-build.py'):
        values[str(path)] = r.sha(path)
    return values


def candidate_inputs():
    assert r.sha(B / 'sleeping-root-r5-build.py') == runner.BUILDER_SHA
    assert r.sha(builder.OUT / 'source-provenance.json') == runner.PROOF_SHA
    assert r.sha(runner.HELPER_SOURCE) == runner.HELPER_SHA
    with contextlib.redirect_stdout(io.StringIO()):
        builder.check()
    values = runner.support.candidate_inputs()
    values.update(builder.inputs())
    values.update(r.read(builder.OUT / 'source-provenance.json')['sourceReferences']['inputs'])
    for path in (B / 'sleeping-root-r5-build.py', builder.OUT / 'source-provenance.json', runner.HELPER_SOURCE):
        values[str(path)] = r.sha(path)
    return values


old_stats = runner.check_stats
old_verification = runner.verification
old_summary = runner.summarize


def check_stats(stats):
    assert stats['version'] == 'sleeping-root-probe-5'
    old_stats(dict(stats, version='sleeping-root-probe-3'))


def verification(result):
    verify = result['sleepingRootVerification']
    assert verify['version'] == 'sleeping-root-pixels-5'
    old_verification(dict(result, sleepingRootVerification=dict(verify, version='sleeping-root-pixels-3')))
    return verify


def summarize(result, args):
    summary = old_summary(result, args)
    summary.update(version='native-input-r5-summary-1', candidateVariant='sleepingroots-r5',
                   behaviorFix='reject-null-safe-tree')
    return summary


def prior_check(name, probe, baseline, candidate):
    result, inputs = r.result(name)
    folder = r.E / name
    summary, record = r.read(folder / 'summary.json'), r.read(folder / 'runner-inputs.json')
    assert summary['version'] == 'native-input-r5-summary-1' and summary['runKind'] == 'check'
    assert summary['helperSHA256'] == runner.HELPER_SHA and summary['verification']['complete']
    assert summary['helperSourceProvenanceSHA256'] == runner.PROOF_SHA
    assert result['config']['nativeInputMotion'] and result['config']['sleepingRootCheck']
    assert not result['config']['sleepingRootShort']
    verification(result)
    if result['config'].get('sleepingRootEarlyCheck'):
        assert summary['earlyCheck'] is True
        runner.summarize_early(result, name)
    assert inputs[runner.base.CS_PATH] == runner.base.CANDIDATE_SHA
    assert inputs[runner.base.PROBE_PATH] == probe['probeSHA256']
    assert r.read(folder / 'probe-build.json') == probe
    assert record['baseline'] == baseline and record['candidateInputs'] == candidate
    assert record['runnerInputs'] == runner_inputs()
    return {str(folder / path): r.sha(folder / path) for path in
        ('storage/result.json', 'inputs.json', 'summary.json', 'runner-inputs.json', 'probe-build.json', 'process-policy.json')}


runner.runner_inputs = runner_inputs
runner.candidate_inputs = candidate_inputs
runner.check_stats = check_stats
runner.base.check_sleeping_stats = check_stats
runner.verification = verification
runner.summarize = summarize
runner.prior_check = prior_check
runner.__doc__ = __doc__


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('Assertions required')
    if sys.argv[1:] == ['--static-check']:
        values = candidate_inputs()
        print(json.dumps(dict(valid=True, staticOnly=True, candidateInputs=len(values),
            helperSHA256=runner.HELPER_SHA, proofSHA256=runner.PROOF_SHA, runnerSHA256=r.sha(Path(__file__)))))
    else:
        runner.main()
