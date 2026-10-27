from pathlib import Path
HERE=Path(__file__).resolve().parent
def one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def source():
    s=(HERE.parent/'camera-live-parking-window-20261027/review_batch.py').read_text('utf-8-sig')
    s=one(s,"assert not policy.get('otherAirProcessIds') and not policy.get('memoryAbort')", "assert not policy.get('otherAirProcessIds')")
    s=one(s,"failure=read(folder/'runner-failure.json');assert 'TimeoutError' in failure['error'] and policy['runFailure']\n        out.update(outcome='timed-out-no-result',error=failure['error'],heartbeat=read(folder/'storage/heartbeat.json'),cleanupVerified=False)",
        "failure=read(folder/'runner-failure.json');assert policy['runFailure']\n        if policy.get('memoryAbort'):\n            assert 'Memory pressure' in failure['error'] and policy['memoryAbort']['availableCommit']<512*1024**2\n            kind='memory-abort-no-result'\n        else:\n            assert 'TimeoutError' in failure['error'];kind='timed-out-no-result'\n        out.update(outcome=kind,error=failure['error'],heartbeat=read(folder/'storage/heartbeat.json'),cleanupVerified=False,memoryBefore=policy['memoryBefore'],memoryAbort=policy.get('memoryAbort'))")
    s=one(s,"if raw['ok']:\n        spec=", "if raw['ok']:\n        if 'math-' in t['version']:\n            assert all(t[k]['passed'] and t[k]['checks']>0 and t[k]['maxError']<0.00001 for k in ['boundsAuditParked','boundsAuditNative'])\n        spec=")
    return s
if __name__=='__main__':
    p=HERE/'review_batch.py';s=source()
    if p.exists():assert p.read_text('utf-8-sig')==s
    else:p.write_text(s,'utf-8')
    print('Prepared independent memory-abort and transform audit review')
