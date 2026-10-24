"""Review CPU occurrences separately; never rewrite the failed mixed-order gate."""
from pathlib import Path
import collections
import hashlib
import json
import math

HERE=Path(__file__).resolve().parent
E=HERE.parents[3]/'knowledge/experiments/evidence/combat-sampler-v3-20261024-scene-r1'


def read(path): return json.loads(path.read_text('utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    raw,summary=read(E/'storage/result.json'),read(E/'summary.json')
    profile=raw['combatSampler']
    assert profile==summary['callStackProfile'] and raw['ok'] and summary['qualification']['passed']
    assert profile['valid'] is False and summary['samplerVerification']['passed'] is False
    assert profile['cleanup']==dict(stopped=True,callbackCleared=True,active=False)
    assert len(profile['windows'])==len(raw['samples'])==4 and not profile['errors']
    top=collections.Counter();inclusive=collections.Counter();windows=[]
    for i,w in enumerate(profile['windows']):
        assert w==raw['samples'][i]['combatSampler'] and w['segment']==i
        assert w['headFrames']==5 and w['firstAge']==295 and w['lastObservedHeadAge']==w['pausedAge']==299
        assert w['paused'] and w['stopped'] and w['callbackCleared'] and not w['errors']
        assert not w['overflow'] and not w['overLimit'] and w['initialSampleCount']==0
        c=w['counts'];d=w['timeDiagnostics'];ts=d['cpuTimes'];indices=d['cpuGlobalIndices']
        assert c['total']==w['reportedSampleCount']==sum(c[k] for k in ('cpu','newObject','deleteObject','unknown'))<100000
        assert c['unknown']==0 and w['enumerationMatchesCount'] and w['categories']['game']>0
        assert c['cpu']==len(ts)==len(indices)==sum(x['samples'] for x in w['top'])==sum(x['samples'] for x in w['stacks'])
        assert all(isinstance(t,(int,float)) and math.isfinite(t) and t>0 for t in ts)
        assert all(a<b for a,b in zip(ts,ts[1:])) and all(a<b for a,b in zip(indices,indices[1:]))
        assert all(isinstance(x,int) and 0<=x<c['total'] for x in indices)
        assert ts[0]==w['firstCPUSampleTime'] and ts[-1]==w['lastCPUSampleTime']
        assert ts[-1]-ts[0]==w['rawCPUSampleSpanUs']
        for key in ('cpu','newObject','deleteObject'):
            t=d['byType'][key]
            assert t['count']==t['finite']==t['positive']==c[key]
            assert t['bad']==t['nonFinite']==t['nonPositive']==t['nonMonotonic']==0
        g=d['global']
        assert g['count']==g['finite']==g['positive']==c['total'] and g['nonFinite']==g['nonPositive']==0
        assert g['bad']==g['nonMonotonic']==d['globalBadByCurrentType']['cpu']>0
        assert all(d['globalBadByCurrentType'][k]==0 for k in ('newObject','deleteObject','unknown'))
        assert w['sampleTimesValid'] is False
        for x in w['top']:top[x['name']]+=x['samples']
        for x in w['inclusiveNames']:inclusive[x['name']]+=x['samples']
        windows.append(dict(segment=i,cpuSamples=c['cpu'],cpuSpanUs=ts[-1]-ts[0],windowWallMs=w['windowWallMs'],
            mixedBackwardCount=g['nonMonotonic'],mixedMaxBackwardUs=g['maxBackward'],
            counts=c,workload=summary['sampledWorkload'][i]))
    result=dict(version='cpu-occurrence-review-1',originalSamplerGatePassed=False,
        cpuOccurrenceCountsUsable=True,diagnosticOnly=True,performanceAcceptance=False,deployed=False,
        evidenceSHA256={name:sha(E/name) for name in ('storage/result.json','summary.json','probe-build.json','runner-inputs.json','process-policy.json')},
        reviewerSHA256=sha(Path(__file__)),cpuSamples=sum(w['cpuSamples'] for w in windows),windows=windows,
        top=[dict(name=k,samples=v) for k,v in top.most_common()],
        inclusive=[dict(name=k,samples=v) for k,v in inclusive.most_common()],
        limitations=['Only twenty main updates sampled; no whole-run timing share or FPS acceptance.',
            'Mixed CPU/allocation iterator is not time sorted. Each observed type subsequence is positive, finite and ordered.',
            'CPU occurrence counts do not depend on ordering between different sample types; original mixed-order failure remains unchanged.',
            'Native runtime labels such as [render] are kept verbatim, not interpreted as GPU or exact render milliseconds.',
            'Inclusive stacks may identify a flush point for globally queued animation, not the object that created all pending work.',
            'Counts are sample occurrences, not invocation counts or milliseconds; overlapping inclusive counts must not be added.'])
    out=E/'cpu-occurrence-review.json';assert not out.exists()
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(cpuSamples=result['cpuSamples'],cpuOccurrenceCountsUsable=True,originalSamplerGatePassed=False,out=str(out))))


if __name__=='__main__':main()
