from pathlib import Path
import ast,importlib.util,inspect,types
HERE=Path(__file__).resolve().parent;VERSION='camera-persistent-repeated-1'
sp=importlib.util.spec_from_file_location('repeated_combat_summary_base',HERE.parent/'camera-persistent-combat-imports-20261027/summary.py')
prior=importlib.util.module_from_spec(sp);sp.loader.exec_module(prior);base=prior.base
base.VERSION=VERSION;base.scope['VERSION']=VERSION

def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
class Counts(ast.NodeTransformer):
    def __init__(self,mapping):self.mapping=mapping;self.counts={n:0 for n in mapping}
    def visit_Constant(self,node):
        if type(node.value) is int and node.value in self.mapping:
            self.counts[node.value]+=1
            return ast.copy_location(ast.Constant(self.mapping[node.value]),node)
        return node
def compiled(source,scope,mapping,expected):
    tree=ast.parse(source);c=Counts(mapping);tree=c.visit(tree);ast.fix_missing_locations(tree)
    assert c.counts==expected,c.counts
    local=dict(scope);exec(compile(tree,'<repeated-combat-length-verifier>','exec'),local)
    return local[tree.body[0].name]

continuous=compiled(inspect.getsource(base.dense.continuous),base.dense.__dict__,{300:60},{300:1})
workload=compiled(inspect.getsource(base.dense.workload),base.dense.__dict__,{300:60},{300:3})
s=base.summary_source
for a,b in [
    ("len(result['samples']) == 4","len(result['samples']) == 20"),
    ("atlas_report['order'] == [False, True, True, False]","atlas_report['order'] == [False, True, True, False] * 5"),
    ("['draw-baseline-a', 'draw-control-b', 'draw-control-b-repeat', 'draw-baseline-a-repeat'][index]","['draw-baseline-a', 'draw-control-b', 'draw-control-b-repeat', 'draw-baseline-a-repeat'][index % 4]"),
    ("atlas = row['atlasMotion']; enabled = index in (1, 2)","atlas = row['atlasMotion']; enabled = index % 4 in (1, 2)"),
    ("mode='atlas' if index in (1, 2) else 'native'","mode='atlas' if index % 4 in (1, 2) else 'native'"),
    ("if (i in (1, 2)) == (mode == 'atlas')","if (i % 4 in (1, 2)) == (mode == 'atlas')")]:s=one(s,a,b)
scope=dict(base.scope);scope.update(VERSION=VERSION,page_state=prior.page_state,
    dense=types.SimpleNamespace(VERSION=base.dense.VERSION,continuous=continuous,workload=workload))
core=compiled(s,scope,{300:60},{300:6})
wrapper_scope=dict(base.__dict__);wrapper_scope.update(VERSION=VERSION,pool_summary=core,page_state=prior.page_state)
base.pool_verified_summary=compiled(inspect.getsource(base.pool_verified_summary),wrapper_scope,
    {480:1200,120:60,4:20},{480:1,120:2,4:2})

def summarize(raw):
    result=base.summarize(raw)
    assert raw['nativeWindowRestored'] and not [e for e in raw['nativeWindowEvents'] if e['phase']>=2]
    v=raw['nativeCombatView'];assert v['visible'] and v['worldVisible'] and not v['menuActive'] and v['frameRate']==30
    assert v['width']>=1900 and v['height']>=1000
    assert result['continuous']['count']==1200 and len(result['rows'])==20
    result['nativeCombatView']=v
    result['pairs']=[dict(nativeIndex=i+a,candidateIndex=i+b,
        nativeMean=result['rows'][i+a]['continuous']['mean'],candidateMean=result['rows'][i+b]['continuous']['mean'])
        for i in range(0,20,4) for a,b in [(0,1),(3,2)]]
    return result
