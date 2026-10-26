"""Recheck completed data without rewriting its failed runner or hardcoded telemetry.

The original reducer expects four parents, but snapshot() still emitted the
legacy literal 3. This read-only review verifies that reporting defect and checks
the remaining invariants. It does not claim an actually observed parent count.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
HERE=Path(__file__).resolve().parent
E=HERE.parents[2]/'knowledge/experiments/evidence/camera-stage3d-static-terrain-20261027-r1'
def read(p):return json.loads(p.read_text('utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
receipt=read(E/'runner-inputs.json');probe=read(E/'probe-build.json')
assert sha(HERE/'run.py')==receipt['runnerInputs'][str(HERE/'run.py')]
renderer=Path(probe['frozenSourcePath'])/'SceneTilePresentation.as'
assert sha(renderer)==probe['frozenSourceSHA256']['SceneTilePresentation.as']
rs=renderer.read_text('utf-8-sig')
assert rs.count('parents:active?3:0')==1
assert rs.count('parents=[backdrop,g.visBack,g.visBack2,g.visFront];')==1
assert 'for(layer=0;layer<parents.length;++layer)parents[layer].visible=false;' in rs
source=(HERE/'run.py').read_text('utf-8-sig');tree=ast.parse(source)
function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='summarize')
review_source=ast.get_source_segment(source,function)
assert review_source.count("row['presentation']['parents']==4")==1
assert review_source.count('(4 if condition>=2 else 0)')==2
review_source=review_source.replace("row['presentation']['parents']==4","row['presentation']['parents']==3")
review_source=review_source.replace('(4 if condition>=2 else 0)','(3 if condition>=2 else 0)')
spec=importlib.util.spec_from_file_location('readonly_terrain_metrics',HERE/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
namespace={'VERSION':runner.VERSION,'metric':runner.metric}
exec(compile(review_source,str(HERE/'review.py')+':readonly-invariants','exec'),namespace)
raw=read(E/'storage/result.json');review=namespace['summarize'](raw)
review.update(originalRunnerPassed=False,originalFailure='Stale literal parents=3 versus reducer expected=4',
    otherDataAssertionsPassed=True,actualParentCountObserved=False,
    parentCountEvidence='Frozen renderer configures four parents, but recorded count was hardcoded; no runtime count claim.',
    resultSHA256=sha(E/'storage/result.json'),probeSHA256=probe['probeSHA256'],
    acceptance=False,performanceAcceptance=False,deployed=False)
path=E/'read-only-review.json';assert not path.exists()
path.write_text(json.dumps(review,ensure_ascii=False,indent=2),'utf-8')
print(json.dumps({k:review[k] for k in ('originalRunnerPassed','otherDataAssertionsPassed','actualParentCountObserved','arms','pairs')},ensure_ascii=False))
