"""Locate allocation churn without reading allocated objects or identities."""
from pathlib import Path
import ast,importlib.util
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'camera-visible-room-sampling-policy-20261027'
VERSION='camera-visible-allocation-stacks-1'
def load(name,p):
    sp=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
base=load('allocation_stack_base',BASE/'prepare.py');one=base.one
SAMPLER=base.SAMPLER
def helper_source():return base.helper_source().replace(base.VERSION,VERSION)
def runner_source():return base.runner_source().replace(base.VERSION,VERSION)
def sampler_source():
    s=base.sampler_source().replace('room-camera-sampler-1','room-camera-allocation-sampler-1')
    s=one(s,'            var top:Object={},stacks:Object={},inclusive:Object={};',
        '            var top:Object={},stacks:Object={},inclusive:Object={};\n            var newStacks:Object={},newTop:Object={},uniqueNewStacks:int=0;')
    s=one(s,'                // New/Delete references, IDs, types, and allocation stacks are not read.\n                if(sample is NewObjectSample){counts.newObject=Number(counts.newObject)+1;continue;}',
        '''                // Only copied stack names are retained; never read sample.object, id, type or size.
                if(sample is NewObjectSample) {
                    counts.newObject=Number(counts.newObject)+1;
                    var allocationNames:Array=[];
                    if(sample.stack!=null)for each(var allocationFrame:StackFrame in sample.stack)
                        allocationNames.push(allocationFrame.name==null?"":String(allocationFrame.name));
                    var allocationKey:String="$"+JSON.stringify(allocationNames);
                    if(!newStacks.hasOwnProperty(allocationKey)) {
                        if(++uniqueNewStacks>4096)throw new Error("Allocation stack cardinality exceeded 4096");
                        newStacks[allocationKey]={names:allocationNames,samples:0};
                    }
                    newStacks[allocationKey].samples=Number(newStacks[allocationKey].samples)+1;
                    var allocationTop:String=allocationNames.length==0?"<empty-stack>":allocationNames[0].length==0?"<anonymous>":allocationNames[0];
                    increment(newTop,"$"+allocationTop);
                    continue;
                }''')
    s=one(s,'            current.top=nameRows(top);current.inclusiveNames=nameRows(inclusive);',
        '''            current.newObjectTop=nameRows(newTop);current.newObjectStacks=[];
            for(var allocation:String in newStacks)current.newObjectStacks.push(newStacks[allocation]);
            current.newObjectStacks.sortOn("samples",Array.NUMERIC|Array.DESCENDING);
            current.top=nameRows(top);current.inclusiveNames=nameRows(inclusive);''')
    s=one(s,'"AS allocations remain sampled; new/delete are only counted and can add observer overhead"',
        '"AS allocations remain sampled; only copied new-object stack names are aggregated after pause; no live objects, IDs, types or sizes are read"')
    return s
if __name__=='__main__':
    (HERE/'tests').mkdir(exist_ok=True)
    for name,s in [('tests/SceneCameraRasterTrial.as',helper_source()),('tests/SceneCameraSampler.as',sampler_source()),('run.py',runner_source())]:
        p=HERE/name
        if p.suffix=='.py':ast.parse(s)
        if p.exists():assert p.read_text('utf-8-sig')==s
        else:p.write_text(s,'utf-8')
    print('Prepared bounded allocation-name stacks; no production edits')
