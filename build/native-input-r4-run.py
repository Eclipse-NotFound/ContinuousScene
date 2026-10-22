"""R4 failure localization: reuse r3 isolated early-check harness, never timing."""
from pathlib import Path
import contextlib
import importlib.util
import io
import sys

sys.dont_write_bytecode=True
B=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


runner=load('native_input_r4_harness',B/'native-input-r3-run.py')
builder=load('native_input_r4_builder',B/'sleeping-root-r4-build.py')
r=runner.r
runner.builder=builder
runner.OUT=B/'generated/native-input-r4-20261023'
runner.HELPER_SOURCE=builder.OUT/'probe-helper/SceneSleepingRootPresentation.as'
runner.HELPER_SHA='B42684C51B1091DC7FFCFE016FAE71592D241A3BC09D751D685DD5CDC97A176C'
runner.PROOF_SHA='3021DDC672C8D4E36E901878F310739D8B0AF2AB6FA2D0F69B51636F829FFC88'
runner.BUILDER_SHA='09F5FCB9184CC24C948DB0D9B3FB0638057A07DE20A39A081DCD5CE61B25995A'


def runner_inputs():
    values=runner.base.runner_inputs()
    for path in (Path(__file__),B/'native-input-r3-run.py',B/'sleeping-root-r4-build.py',B/'sleeping-root-r3-build.py'):
        values[str(path)]=r.sha(path)
    return values


def candidate_inputs():
    assert r.sha(B/'sleeping-root-r4-build.py')==runner.BUILDER_SHA
    assert r.sha(builder.OUT/'source-provenance.json')==runner.PROOF_SHA
    assert r.sha(runner.HELPER_SOURCE)==runner.HELPER_SHA
    with contextlib.redirect_stdout(io.StringIO()):builder.check()
    values=runner.support.candidate_inputs()
    values.update(builder.inputs())
    values.update(r.read(builder.previous.OUT/'source-provenance.json')['sourceReferences']['inputs'])
    for path in (B/'sleeping-root-r4-build.py',builder.OUT/'source-provenance.json',runner.HELPER_SOURCE):
        values[str(path)]=r.sha(path)
    return values


old_stats=runner.check_stats
old_verification=runner.verification
old_summary=runner.summarize


def check_stats(stats):
    assert stats['version']=='sleeping-root-probe-4'
    # Schema unchanged; the shared r3 validator retains every safety check.
    old_stats(dict(stats,version='sleeping-root-probe-3'))


def verification(result):
    verify=result['sleepingRootVerification']
    assert verify['version']=='sleeping-root-pixels-4'
    old_verification(dict(result,sleepingRootVerification=dict(verify,version='sleeping-root-pixels-3')))
    return verify


def summarize(result,args):
    assert args.check and args.early_check and not args.short_interleave
    summary=old_summary(result,args)
    summary.update(version='native-input-r4-summary-1',diagnosticFailureOnly=True)
    return summary


runner.runner_inputs=runner_inputs
runner.candidate_inputs=candidate_inputs
runner.check_stats=check_stats
runner.base.check_sleeping_stats=check_stats
runner.verification=verification
runner.summarize=summarize
runner.__doc__=__doc__


if __name__=='__main__':
    if '--check' not in sys.argv or '--early-check' not in sys.argv or '--short-interleave' in sys.argv:
        raise RuntimeError('R4 only diagnoses failure; require --check --early-check, never timing')
    runner.main()
