"""Independently review bounded pruning, restoration, interval counts and pixels."""
from pathlib import Path
import importlib.util
import json
from PIL import Image
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('region_prune_identity',HERE.parent/'camera-stage3d-wholeworld-settle-20261027/verify_runs.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
NAME='camera-stage3d-region-prune-20261027-r1'


def main():
    result=base.review(NAME)
    folder=base.E/NAME;raw=base.read(folder/'storage/result.json');t=raw['cameraRaster'];p=t['cleanup']['presentation']
    assert p['boundsImagesAllocated']==p['boundsImagesDisposed']
    assert p['cullWrites']==p['cullRestores'] and p['cullRestored'] and p['cullPending']==0
    if p['worldPrepared'] and 'cullInventory' in t:
        area=p['initial']['refreshArea'];items=t['cullInventory']
        assert len(items)==p['initial']['cullCount']>0
        for item in items:
            extent=item['extent']
            assert extent['x']+extent['width']<=area['x'] or area['x']+512<=extent['x'] or extent['y']+extent['height']<=area['y'] or area['y']+512<=extent['y']
        result['selectedRoots']=len(items)
    result['cullChecks']=p['cullChecks']
    if t['complete']:
        assert p['regionRasterCalls']==p['cullCalls']==493 and p['cullVerifyDraws']==13
        assert p['copies']==p['allocated']-p['boundsImagesAllocated']-2+493+13
        assert p['uploads']==p['texturesCreated']+493 and p['allocated']==p['texturesCreated']+2+p['boundsImagesAllocated']
        assert [c['call'] for c in p['cullChecks']]==list(range(1,14))
        assert all(c['equal'] and c['restored'] for c in p['cullChecks'])
        first=t['windows'][0]['presentation'][0];last=t['windows'][-1]['presentation'][-1]
        previous=13
        for row in t['windows']:
            gpu=row['condition']>=2
            assert row['copiesEnd']-row['copiesStart']==(120 if gpu else 0)
            for item in row['presentation']:
                assert item['regionRasterCalls']==previous+(1 if gpu else 0)
                assert item['cullCalls']==item['regionRasterCalls'] and item['cullVerifyDraws']==13
                assert item['cullWrites']==item['cullRestores'] and item['cullRestored'] and item['cullPending']==0
                assert item['boundsImagesAllocated']==item['boundsImagesDisposed']==p['boundsImagesAllocated']
                previous=item['regionRasterCalls']
        assert previous==493
        result['timedRefresh']=dict(calls=480,rasterMs=last['regionRasterMs']-first['regionRasterMs'],
            uploadMs=last['regionUploadMs']-first['regionUploadMs'],writes=last['cullWrites']-first['cullWrites'])
        for field in ('rasterMs','uploadMs','writes'):
            result['timedRefresh'][field+'PerCall']=result['timedRefresh'][field]/480
        paths=[folder/'storage/stage3d-pixels'/name for name in ('cull-native-1.png','cull-pruned-1.png')]
        pixels=[]
        for path in paths:
            with Image.open(path) as image:
                assert image.size==(512,512);pixels.append(image.convert('RGBA').tobytes())
        assert pixels[0]==pixels[1]
        result['firstRegionPixels']=dict(equalRGBA=True,inputs={str(path):base.sha(path) for path in paths})
    dest=HERE/'run-review.json';assert not dest.exists()
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({key:result.get(key) for key in ('complete','frames','trialErrors','selectedRoots','arms','pairs','timedRefresh','visualAccepted')}))


if __name__=='__main__':main()
