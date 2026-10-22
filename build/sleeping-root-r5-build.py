"""Prepare r5: reject a null safeTree node; retain r4 diagnostics and ownership rules."""
from pathlib import Path
import argparse
import ast
import contextlib
import difflib
import importlib.util
import io
import json
import sys

sys.dont_write_bytecode = True
B = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('sleeping_root_r5_previous', B / 'sleeping-root-r4-build.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
OUT = B / 'generated/sleeping-root-20261023-r5'
R2_HELPER, CLASSES, HELPER = previous.R2_HELPER, previous.CLASSES, previous.HELPER
sha, read, digest = previous.sha, previous.read, previous.digest
PREVIOUS_HELPER = 'B42684C51B1091DC7FFCFE016FAE71592D241A3BC09D751D685DD5CDC97A176C'
PREVIOUS_PROOF = '3021DDC672C8D4E36E901878F310739D8B0AF2AB6FA2D0F69B51636F829FFC88'
PREVIOUS_BUILDER = '09F5FCB9184CC24C948DB0D9B3FB0638057A07DE20A39A081DCD5CE61B25995A'


def inputs():
    paths = {B / 'sleeping-root-r4-build.py': PREVIOUS_BUILDER,
             previous.OUT / 'source-provenance.json': PREVIOUS_PROOF,
             previous.OUT / 'probe-helper' / HELPER: PREVIOUS_HELPER}
    for path, expected in paths.items():
        assert sha(path) == expected, str(path)
    with contextlib.redirect_stdout(io.StringIO()):
        previous.check()
    return dict(previous.inputs(), **{str(path): value for path, value in paths.items()})


def modify(original):
    source, edits = original.decode('utf-8'), []
    replacements = (
        ('            diagnosticStage="safe-tree";diagnosticNode=node;\n'
         '            if(node.mask || node.filters.length || node.scrollRect)return false;',
         '            diagnosticStage="safe-tree";diagnosticNode=node;\n'
         '            if(node==null)return false;\n'
         '            if(node.mask || node.filters.length || node.scrollRect)return false;'),
        ('version:"sleeping-root-probe-4"', 'version:"sleeping-root-probe-5"'),
        ('version:"sleeping-root-pixels-4"', 'version:"sleeping-root-pixels-5"'))
    for before, after in replacements:
        assert source.count(before) == 1, before
        source = source.replace(before, after, 1)
        edits.append(dict(before=before, after=after))
    reverse = source
    for edit in reversed(edits):
        assert reverse.count(edit['after']) == 1
        reverse = reverse.replace(edit['after'], edit['before'], 1)
    assert reverse.encode('utf-8') == original
    return source.encode('utf-8'), edits


def prepare():
    ast.parse(Path(__file__).read_text('utf-8'))
    assert not OUT.exists(), 'Preserve existing r5 evidence; use --check'
    before = inputs()
    original = (previous.OUT / 'probe-helper' / HELPER).read_bytes()
    modified, edits = modify(original)
    OUT.mkdir(); (OUT / 'probe-helper').mkdir()
    (OUT / 'probe-helper' / HELPER).write_bytes(modified)
    (OUT / 'helper.patch').write_text(''.join(difflib.unified_diff(original.decode('utf-8').splitlines(True),
        modified.decode('utf-8').splitlines(True), fromfile='r4-returnfix/' + HELPER, tofile='r5/' + HELPER)), 'utf-8')
    prior = read(previous.OUT / 'source-provenance.json')
    proof = dict(version='sleeping-root-helper-source-5', diagnosticOnly=True, behaviorFix='reject-null-safe-tree',
        performanceAcceptance=False, helperCompiled=False, airRun=False, deployed=False,
        builderSHA256=sha(__file__), baseline=prior['baseline'], host=prior['host'],
        previousInputs=before, previousHelperSHA256=PREVIOUS_HELPER, probeHelperSHA256=digest(modified),
        nativeCandidatePath=prior['nativeCandidatePath'], nativeCandidateSHA256=prior['nativeCandidateSHA256'],
        reusesR2NativeBinary=True, edits=edits, reverseInsertionCheck=True,
        sourceReferences=read(previous.previous.OUT / 'source-provenance.json')['sourceReferences'],
        note='Only null safeTree nodes reject the complete unit before detachment; no catch broadening, ownership or whitelist changes.')
    (OUT / 'source-provenance.json').write_text(json.dumps(proof, indent=2), 'utf-8')
    assert before == inputs()
    return check()


def check():
    proof = read(OUT / 'source-provenance.json')
    assert proof['version'] == 'sleeping-root-helper-source-5' and proof['builderSHA256'] == sha(__file__)
    assert proof['previousInputs'] == inputs() and proof['behaviorFix'] == 'reject-null-safe-tree'
    modified, edits = modify((previous.OUT / 'probe-helper' / HELPER).read_bytes())
    assert edits == proof['edits'] and digest(modified) == proof['probeHelperSHA256'] == sha(OUT / 'probe-helper' / HELPER)
    prior = read(previous.OUT / 'source-provenance.json')
    assert proof['nativeCandidateSHA256'] == prior['nativeCandidateSHA256']
    assert sha(proof['nativeCandidatePath']) == proof['nativeCandidateSHA256']
    assert proof['sourceReferences'] == read(previous.previous.OUT / 'source-provenance.json')['sourceReferences']
    return dict(passed=True, staticOnly=True, helperSHA256=proof['probeHelperSHA256'],
                provenanceSHA256=sha(OUT / 'source-provenance.json'), builderSHA256=sha(__file__))


if __name__ == '__main__':
    if not __debug__:
        raise RuntimeError('Assertions required')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    print(json.dumps(check() if args.check else prepare()))
