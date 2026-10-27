"""Verify the frozen run and independently rebuild CPU stack occurrence counts."""
from pathlib import Path
import argparse,collections,importlib.util,json
HERE=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('room_sampler_verify_base',HERE.parent/'camera-visible-room-scout-20261027/verify_batch.py')
base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)

def main():
    p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    assert not args.out.exists()
    record,raw=base.verify(args.name,HERE,source_count=87)
    original=base.read(base.E/args.name/'runner-inputs.json')
    policies=original['startupResourcePolicies'];assert len(policies)==1
    applied=policies[0]['policy'];assert policies[0]['pid']==record['pid']
    assert applied['requested']=='test' and not applied['errors'] and not applied['after']['errors']
    assert applied['after']['cpuPriorityClass']==32 and applied['after']['memoryPriority']==5
    assert applied['after']['powerThrottling']['highQoS']
    record['startupResourcePolicies']=policies
    sample=raw['cameraRaster']['cpuSampling'];grouped={};windows=[]
    for w in sample['windows']:
        top=collections.Counter();inclusive=collections.Counter()
        for row in w['stacks']:
            names=row['names'];n=row['samples'];assert isinstance(n,int) and n>0
            top[names[0] or '<anonymous>' if names else '<empty-stack>']+=n
            inclusive.update({name:n for name in set(names) if name})
        assert dict(top)=={v['name']:v['samples'] for v in w['top']}
        assert dict(inclusive)=={v['name']:v['samples'] for v in w['inclusiveNames']}
        group=grouped.setdefault(w['name'],dict(cpuSamples=0,windows=0,top=collections.Counter(),inclusive=collections.Counter()))
        group['cpuSamples']+=w['counts']['cpu'];group['windows']+=1;group['top'].update(top);group['inclusive'].update(inclusive)
        allocations=collections.Counter();allocation_inclusive=collections.Counter()
        for row in w['newObjectStacks']:
            names=row['names'];n=row['samples'];assert isinstance(n,int) and n>0
            allocations[names[0] or '<anonymous>' if names else '<empty-stack>']+=n
            allocation_inclusive.update({name:n for name in set(names) if name})
        assert dict(allocations)=={v['name']:v['samples'] for v in w['newObjectTop']}
        assert sum(allocations.values())==w['counts']['newObject']
        group.setdefault('allocations',collections.Counter()).update(allocations)
        group.setdefault('allocationInclusive',collections.Counter()).update(allocation_inclusive)
        windows.append(dict(segment=w['segment'],name=w['name'],counts=w['counts'],
            cpuFirst=w['firstCPUSampleTime'],cpuLast=w['lastCPUSampleTime'],
            cpuSpanUs=w['rawCPUSampleSpanUs'],wallMs=w['windowWallMs'],aggregationMs=w['aggregationMs'],
            cpuMonotonic=w['timeDiagnostics']['byType']['cpu']['nonMonotonic']==0,
            mixedStreamBackwardCount=w['timeDiagnostics']['global']['nonMonotonic'],top=top.most_common(12)))
    groups={k:dict(cpuSamples=v['cpuSamples'],windows=v['windows'],top=v['top'].most_common(),inclusive=v['inclusive'].most_common(),allocations=v['allocations'].most_common(),allocationInclusive=v['allocationInclusive'].most_common()) for k,v in grouped.items()}
    record.pop('summary')
    result=dict(run=record,windows=windows,groups=groups,deployed=False,performanceAcceptance=False,
        limitation='Five sampled outgoing intervals per window, allocation overhead retained. Occurrence counts are not durations, invocation counts, or complete renderer/GPU coverage. Mixed iterator order is not used as a clock.')
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(verified=True,sha256=base.sha(args.out),groups={k:dict(cpuSamples=v['cpuSamples'],top=v['top'][:8],allocations=v['allocations'][:12]) for k,v in groups.items()}),ensure_ascii=False))
if __name__=='__main__':main()
