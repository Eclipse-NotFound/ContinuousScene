"""Review all finished intervals, even when a terminal correctness audit fails."""
from pathlib import Path
import importlib.util,json,statistics,sys
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('parking_review_base',HERE.parent/'camera-live-parking-math-20261027/review_batch.py')
clock=load('parking_clock_review',HERE.parent/'camera-live-parking-return-20261027/verify_run.py')
def review(name):
    out=base.review(name)
    if out.get('samples')==20:
        independent=clock.review(name)
        for k in ['frames','elapsedMs','arms','pairs','rows','verification']:out[k]=independent[k]
        raw=base.read(base.E/name/'storage/result.json')
        out['managementMs']={str(on):statistics.mean(x['workMs'] for i,s in enumerate(raw['samples']) if (i%4 in (1,2)) is on for x in s['farParking']) for on in [False,True]}
        if out['rawOK'] and 'groups-' in raw['farParking']['version']:
            t=raw['farParking'];assert t['groups']>0 and t['groupBoundsQueries']>0 and t['groupPreparations']>0
            assert not [a for a in raw['assertions'] if not a['ok']]
            for i,s in enumerate(raw['samples']):
                if i%4 in (1,2):assert min(x['heldGroups'] for x in s['farParking'])>0
            out['selectedGroups']=t['groups']
    out['reviewSourceSHA256']=base.sha(Path(__file__))
    return out
if __name__=='__main__':
    for name in sys.argv[1:]:
        r=review(name);out=HERE/(name+'-review.json');assert not out.exists()
        out.write_text(json.dumps(r,ensure_ascii=False,indent=2),'utf-8')
        print(json.dumps({k:v for k,v in r.items() if k not in ['rows','parking','verification']},ensure_ascii=False))
