"""Independently validate per-interval CPU redraw/upload counts and continuous clocks."""
from pathlib import Path
import importlib.util
import json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('viewport_refresh_identity_audit',HERE.parent/'camera-stage3d-wholeworld-settle-20261027/verify_runs.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
NAME='camera-stage3d-viewport-refresh-20261027-r1'
def main():
    result=base.review(NAME)
    raw=base.read(base.E/NAME/'storage/result.json');t=raw['cameraRaster'];end=t['cleanup']['presentation']
    assert t['complete'] and len(t['framesMs'])==960 and t['passed']
    assert end['fullRasterCalls']==493 and end['uploads']==495 and end['copies']==494
    assert end['texturesCreated']==end['texturesDisposed']==end['allocated']==end['disposed']==2
    first=t['windows'][0]['presentation'][0];previous=first['fullRasterCalls']
    assert previous==13
    for row in t['windows']:
        cached=row['condition']>=2
        assert row['copiesEnd']-row['copiesStart']==(120 if cached else 0)
        for p in row['presentation']:
            assert p['fullRasterCalls']==previous+(1 if cached else 0)
            assert p['uploads']==p['fullRasterCalls']+2 and p['copies']==p['fullRasterCalls']+1
            previous=p['fullRasterCalls']
    assert previous==493
    last=t['windows'][-1]['presentation'][-1]
    result['timedRefresh']=dict(calls=480,rasterMs=last['fullRasterMs']-first['fullRasterMs'],uploadMs=last['fullUploadMs']-first['fullUploadMs'])
    result['timedRefresh']['meanRasterMs']=result['timedRefresh']['rasterMs']/480
    result['timedRefresh']['meanUploadMs']=result['timedRefresh']['uploadMs']/480
    dest=HERE/'run-review.json';assert not dest.exists()
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(dict(arms=result['arms'],pairs=result['pairs'],timedRefresh=result['timedRefresh'],visualAccepted=result['visualAccepted'])))
if __name__=='__main__':main()
