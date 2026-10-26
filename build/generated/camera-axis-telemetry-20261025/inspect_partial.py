"""Read-only partial-stream inventory; never qualify a failed/truncated run."""
from pathlib import Path
import hashlib
import importlib.util
import json
import collections
import time

HERE=Path(__file__).resolve().parent
VENDOR=HERE.parent/'camera-telemetry-v2-20261025/vendor/amf3reader.py'
assert hashlib.sha256(VENDOR.read_bytes()).hexdigest().upper()=='5069D8CE17858E2625D3C309EDC17099A6DA6C147AC7612BD9D7DB021E2F20F3'
spec=importlib.util.spec_from_file_location('adobe_partial_reader',VENDOR)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def inspect(folder):
    path=folder/'native.flm';data=path.read_bytes();assert len(data)<=128*1024**2
    reader=module.amf3reader(data);assert reader.getFormat()=='amfstream'
    count=0;names=collections.Counter();unions=collections.defaultdict(list);events=collections.Counter()
    custom=[];meta=[];examples=[];stamp=0;begin=time.monotonic();truncated=None;out_of_order=[]
    while reader.pos<len(data):
        before=reader.pos;item=reader.readMetric()
        if item is None or reader.pos<=before:
            truncated=dict(offset=before,remaining=len(data)-before);break
        count+=1;assert count<=8000000 and time.monotonic()-begin<120
        name=item['name'];names[name]+=1
        if 'delta' in item:stamp+=item['delta']
        elif 'time' in item:stamp=item['time']
        if name.startswith(('remains.','.tlm.custom','.trace')):custom.append(dict(item,atUs=stamp))
        if name.startswith(('.starttimer','.swf.start','.tlm.date','.tlm.detailed')):meta.append(dict(item,atUs=stamp))
        if name=='.as.event':
            label=json.dumps(item.get('value'),sort_keys=True,ensure_ascii=False)
            if label in events or len(events)<2000:events[label]+=1
            if len(examples)<8:examples.append(dict(item,atUs=stamp))
        span=item.get('span',0)
        if span<=0 or not name.startswith(('.rend.','.as.','.gc.','.player.','.tlm.txtime')):continue
        left,right=stamp-span,stamp;stack=unions[name]
        if stack and right<stack[-1][1]:out_of_order.append(dict(name=name,atUs=stamp));continue
        while stack and stack[-1][1]>=left:left=min(left,stack.pop()[0])
        stack.append((left,right))
    result=dict(validFullRun=False,rawSHA256=hashlib.sha256(data).hexdigest().upper(),records=count,truncated=truncated,
        metricCounts=dict(names),nativeUnions=dict(unions),custom=custom,metadata=meta,eventExamples=examples,
        eventValues=events.most_common(20),outOfOrder=out_of_order,
        limitation='Failed run; truncated stream and no application end marker. No final performance acceptance.')
    destination=folder/'partial-spans.json';assert not destination.exists()
    destination.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(records=count,truncated=truncated,customCount=len(custom),customFirst=custom[:3],customLast=custom[-3:],
        metadata=meta,eventValues=events.most_common(6),eventExamples=examples[:2],outOfOrder=len(out_of_order)),ensure_ascii=False))

if __name__=='__main__':
    inspect(HERE.parents[2]/'knowledge/experiments/evidence/camera-axis-telemetry-20261025-r2')
