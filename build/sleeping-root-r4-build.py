"""Prepare r4 failure diagnostics only; no behavior fix, compile, AIR or deploy."""
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
spec = importlib.util.spec_from_file_location('sleeping_root_r3_source', B / 'sleeping-root-r3-build.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
OUT = B / 'generated/sleeping-root-20261022-r4-returnfix'
R2_HELPER, CLASSES = previous.R2_HELPER, previous.CLASSES
HELPER = previous.HELPER
sha, read, digest = previous.sha, previous.read, previous.digest
PREVIOUS_HELPER = '210DD1BF60EBAA0D2AED2E1F8513D50F3FE9243AF3398353B7D31B096409B8A5'
PREVIOUS_PROOF = '7EFEFC2130F56B37095F2084419017AE6EEEEA12B19C4E8E84D7302C1B0FDF26'
PREVIOUS_BUILDER = 'A924F632662F2412D358FA6CAFE33708348046A5021130EACA1F7DA6DB82CB5D'


def inputs():
    paths = {B / 'sleeping-root-r3-build.py': PREVIOUS_BUILDER,
        previous.OUT / 'source-provenance.json': PREVIOUS_PROOF,
        previous.OUT / 'probe-helper' / HELPER: PREVIOUS_HELPER}
    for path, expected in paths.items():
        assert sha(path) == expected, str(path)
    with contextlib.redirect_stdout(io.StringIO()):
        previous.check()
    return {str(path): value for path, value in paths.items()}


DIAGNOSTICS = '''        private function failureDetail(u:*,error:*):String {
            var detail:Object={stage:diagnosticStage};
            try {detail.error=String(error);}catch(e:*) {detail.error="unreadable error";}
            try {detail.stack=error is Error?Error(error).getStackTrace():null;}catch(e1:*) {detail.stack="unavailable";}
            try {detail.unitClass=getQualifiedClassName(u);detail.unitNull=u==null;}catch(e2:*) {detail.unitClass="unavailable";}
            try {detail.childObjsNull=u.childObjs===null;detail.childObjsArray=u.childObjs is Array;
                if(u.childObjs is Array)detail.childCount=u.childObjs.length;}catch(e3:*) {detail.childrenReadFailed=true;}
            try {detail.weaponNull=u.currentWeapon===null;}catch(e4:*) {detail.weaponReadFailed=true;}
            try {detail.visNull=u.vis===null;detail.hpbarNull=u.hpbar===null;detail.locNull=u.loc===null;}catch(e5:*) {detail.rootsReadFailed=true;}
            try {detail.nodeNull=diagnosticNode==null;detail.nodeClass=getQualifiedClassName(diagnosticNode);
                if(diagnosticNode)detail.nodeFiltersNull=diagnosticNode.filters===null;}catch(e6:*) {detail.nodeReadFailed=true;}
            var serialized:String;
            try {serialized=JSON.stringify(detail);}catch(e7:*) {serialized="Failure diagnostic serialization unavailable";}
            return serialized;
        }

'''


def modify(original):
    source = original.decode('utf-8')
    edits = []
    def edit(before, after):
        nonlocal source
        assert source.count(before) == 1, (before[:90], source.count(before))
        source = source.replace(before, after, 1)
        edits.append(dict(before=before, after=after))
    edit('        private var lastWake:Object;', '        private var lastWake:Object;\n        private var diagnosticStage:String="idle",diagnosticNode:DisplayObject;')
    edit('            var begin:int=getTimer();++callbacks;', '            var begin:int=getTimer();++callbacks;diagnosticStage="callback-entry";diagnosticNode=null;')
    for before, label in (
        ('                if(!sameContext(world))', 'context'),
        ('                var record:Object=held[u];', 'held-record'),
        ('                if(!sleeping) {', 'wake'),
        ('                ++sleepCalls;', 'sleep'),
        ('                var unitClass:String=getQualifiedClassName(u);', 'class'),
        ('                if(u.loc!==location', 'unit-state'),
        ('                if(!(u.childObjs is Array)', 'child-policy'),
        ('                record=collect(u);', 'collect'),
        ('                held[u]=record;', 'claim'),
        ('                    parking.addChild(item.root);', 'detach'),
        ('            var root:DisplayObject=owner[field] as DisplayObject;', 'root-field'),
        ('            var parent:DisplayObjectContainer=root.parent;', 'root-parent'),
        ('            var bounds:Rectangle=root.getBounds(visual);', 'root-bounds'),
        ('            var u:*=record.unit;', 'validate'),
        ('            if(strict)validateOwnership(record);', 'restore')):
        indent = before[:len(before)-len(before.lstrip())]
        edit(before, indent+'diagnosticStage="'+label+'";\n'+before)
    edit('            if(node.mask || node.filters.length || node.scrollRect)return false;',
         '            diagnosticStage="safe-tree";diagnosticNode=node;\n            if(node.mask || node.filters.length || node.scrollRect)return false;')
    edit('            }catch(error:*){fail("callback",error);}',
         '            }catch(error:*){\n                var detail:String=null;\n                try {detail=failureDetail(u,error);}catch(diagnosticError:*) {}\n                fail("callback",detail?detail:error);\n            }')
    edit('        private function fail(where:String,error:*):void {', DIAGNOSTICS+'        private function fail(where:String,error:*):void {')
    edit('version:"sleeping-root-probe-3"', 'version:"sleeping-root-probe-4"')
    edit('version:"sleeping-root-pixels-3"', 'version:"sleeping-root-pixels-4"')
    reverse = source
    for item in reversed(edits):
        assert reverse.count(item['after']) == 1
        reverse = reverse.replace(item['after'], item['before'], 1)
    assert reverse.encode('utf-8') == original
    return source.encode('utf-8'), edits


def prepare():
    ast.parse(Path(__file__).read_text('utf-8'))
    assert not OUT.exists(), 'Preserve existing r4 evidence; use --check'
    before = inputs()
    original = (previous.OUT / 'probe-helper' / HELPER).read_bytes()
    modified, edits = modify(original)
    OUT.mkdir(); (OUT / 'probe-helper').mkdir()
    (OUT / 'probe-helper' / HELPER).write_bytes(modified)
    (OUT / 'helper.patch').write_text(''.join(difflib.unified_diff(original.decode('utf-8').splitlines(True),
        modified.decode('utf-8').splitlines(True), fromfile='r3/'+HELPER, tofile='r4/'+HELPER)), 'utf-8')
    proof = dict(version='sleeping-root-helper-source-4', diagnosticOnly=True, diagnosticFailureOnly=True,
        behaviorFix=False, performanceAcceptance=False, helperCompiled=False, airRun=False, deployed=False,
        builderSHA256=sha(Path(__file__)), baseline=previous.BASE_SHA, host=previous.HOST_SHA,
        previousInputs=before, previousHelperSHA256=PREVIOUS_HELPER, probeHelperSHA256=digest(modified),
        nativeCandidatePath=str(previous.R2/'ContinuousSceneMod.swf'), nativeCandidateSHA256=previous.R2_NATIVE,
        reusesR2NativeBinary=True, edits=edits, reverseInsertionCheck=True,
        note='Failure stage/class/null structure and optional stack only; no speculative null-child behavior fix.')
    (OUT / 'source-provenance.json').write_text(json.dumps(proof, indent=2), 'utf-8')
    assert before == inputs()
    print(json.dumps(dict(prepared=True, helperSHA256=digest(modified), provenanceSHA256=sha(OUT/'source-provenance.json'), builderSHA256=sha(Path(__file__)))))


def check():
    proof = read(OUT/'source-provenance.json')
    assert proof['version']=='sleeping-root-helper-source-4' and proof['builderSHA256']==sha(Path(__file__))
    assert proof['previousInputs']==inputs() and proof['diagnosticFailureOnly'] and not proof['behaviorFix']
    modified, edits=modify((previous.OUT/'probe-helper'/HELPER).read_bytes())
    assert edits==proof['edits'] and digest(modified)==proof['probeHelperSHA256']==sha(OUT/'probe-helper'/HELPER)
    assert proof['nativeCandidateSHA256']==previous.R2_NATIVE
    print(json.dumps(dict(passed=True, staticOnly=True, diagnosticFailureOnly=True, helperSHA256=proof['probeHelperSHA256'])))


if __name__=='__main__':
    if not __debug__:raise RuntimeError('Assertions required')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();(check if args.check else prepare)()
