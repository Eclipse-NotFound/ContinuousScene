"""Interpret only complete owned thread-counter intervals inside clock bounds."""
def summarize(policy, alignment, bounds):
    samples=[s['threadSample'] for s in policy['ownedProcessCpuSamples'] if s['threadSample'] is not None]
    expected_pid=policy['pid']
    start,end=alignment['conservativeStartEpochMs'],alignment['conservativeEndEpochMs']
    def phase(begin,finish):
        used=[]; totals={}; errors=[]; membership=[]; window_sets=[]
        for i,(a,b) in enumerate(zip(samples,samples[1:])):
            if a['epochBeforeMs']<begin or b['epochAfterMs']>finish:continue
            if not a['complete'] or not b['complete'] or not a['valid'] or not b['valid']:
                errors.append(dict(interval=i,firstErrors=a['errors'],lastErrors=b['errors']));continue
            assert a['pid']==b['pid']==expected_pid
            assert a['process']['identity']==b['process']['identity']
            assert a['cleanup']['handlesOpened']==a['cleanup']['handlesClosed'] and not a['cleanup']['closeErrors']
            assert b['cleanup']['handlesOpened']==b['cleanup']['handlesClosed'] and not b['cleanup']['closeErrors']
            elapsed=(b['monotonicBefore']-a['monotonicBefore'])*1000
            assert elapsed>0 and abs(b['epochBeforeMs']-a['epochBeforeMs']-elapsed)<=20
            left={x['identity']:x for x in a['threads']};right={x['identity']:x for x in b['threads']}
            assert len(left)==len(a['threads']) and len(right)==len(b['threads'])
            missing=sorted(set(left)^set(right))
            if missing:membership.append(dict(interval=i,unpairedIdentities=missing))
            interval_cpu=0
            for key in sorted(set(left)&set(right)):
                x,y=left[key],right[key]
                assert not x['errors'] and not y['errors']
                cpu=(int(y['kernel100ns'])+int(y['user100ns'])-int(x['kernel100ns'])-int(x['user100ns']))/10000
                cycles=int(y['cycles'])-int(x['cycles'])
                span=(y['monotonicBefore']-x['monotonicBefore'])*1000
                assert cpu>=0 and cycles>=0 and span>0
                entry=totals.setdefault(key,dict(identity=key,tid=x['tid'],creationTime100ns=x['creationTime100ns'],
                    cpuMs=0,cycles=0,coveredElapsedMs=0,intervals=0,windowHandles=[]))
                entry['cpuMs']+=cpu;entry['cycles']+=cycles;entry['coveredElapsedMs']+=span;entry['intervals']+=1
                entry['windowHandles']=sorted(set(entry['windowHandles'])|set(x['windowHandles'])|set(y['windowHandles']))
                interval_cpu+=cpu
            used.append(dict(index=i,elapsedMs=elapsed,matchedThreadCpuMs=interval_cpu))
            window_sets.append(dict(index=i,first=a['windows'],last=b['windows']))
        elapsed=sum(x['elapsedMs'] for x in used);cpu=sum(x['matchedThreadCpuMs'] for x in used)
        ordered=sorted(totals.values(),key=lambda x:x['cpuMs'],reverse=True)
        for row in ordered:
            row['meanCoreEquivalent']=row['cpuMs']/row['coveredElapsedMs']
            row['ownsObservedWindow']=bool(row['windowHandles']);row['cycles']=str(row['cycles'])
        return dict(passed=bool(used) and not errors,startEpochMs=begin,endEpochMs=finish,
            intervalCount=len(used),coveredElapsedMs=elapsed,matchedThreadCpuMs=cpu,
            summedCoreEquivalent=cpu/elapsed if elapsed else None,threads=ordered,
            incompleteIntervals=errors,membershipChanges=membership,windowMappings=window_sets,
            unmatchedThreadsAreNotZero=True,intervals=used)
    whole=phase(start,end)
    cases=[];marks=alignment['caseAnchors']
    for i,mark in enumerate(marks):
        finish=bounds(marks[i+1])[0] if i+1<len(marks) else end
        cases.append(dict(index=i,**phase(bounds(mark)[1],finish)))
    in_window=[s for s in samples if s['epochBeforeMs']>=start and s['epochAfterMs']<=end]
    return dict(version='owned-thread-counter-review-1',passed=whole['passed'] and all(x['passed'] for x in cases),
        whole=whole,cases=cases,sampleCount=len(samples),timedSampleCount=len(in_window),
        observerElapsedMs=[s['elapsedMs'] for s in in_window],
        limitations=['Matched thread deltas exclude newly created or exited identities and are not exact total process CPU.',
            'Thread reads are sequential, not an atomic snapshot; each retains its own clock interval.',
            'Window ownership is not proof of AS3/rendering role. CPU residual is not GPU or a wait category.'])
