"""Review ordered-root interval costs and compare its first region to native draw."""
from pathlib import Path
import importlib.util
import json
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('items_identity_audit', HERE.parent/'camera-stage3d-wholeworld-settle-20261027/verify_runs.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
NAME = 'camera-stage3d-region-items-20261027-r1'


def main():
    result = base.review(NAME)
    folder = base.E/NAME
    raw = base.read(folder/'storage/result.json')
    trial = raw['cameraRaster']
    end = trial['cleanup']['presentation']
    # Retain the original timeout. Do not turn an incomplete run into a passed
    # moving-camera comparison or extend the deadline to rescue the recipe.
    assert not trial['complete'] and not trial['passed'] and not raw['ok']
    assert trial['errors'] == ['Camera raster timeout']
    assert len(trial['framesMs']) == 351
    assert end['regionRasterCalls'] == 125
    assert end['copies'] == end['allocated']-1+125
    assert end['uploads'] == end['texturesCreated']+125
    assert end['texturesCreated'] == end['texturesDisposed']
    assert end['allocated'] == end['disposed'] == end['texturesCreated']+2
    area = end['initial']['refreshArea']
    intersection = end['initial']['refreshIntersection']
    assert area['width'] == area['height'] == 512
    for origin, extent in (('x', 'width'), ('y', 'height')):
        assert intersection[origin] <= area[origin]
        assert area[origin]+area[extent] <= intersection[origin]+intersection[extent]
    first = trial['windows'][0]['presentation'][0]
    previous = first['regionRasterCalls']
    assert previous == 13
    clock = trial['timingStartAtMs']
    stamps, intervals = [], []
    assert [row['condition'] for row in trial['windows']] == [0,1,2]
    assert [len(row['framesMs']) for row in trial['windows']] == [120,120,111]
    for row in trial['windows']:
        cached = row['condition'] >= 2
        assert row['startAtMs'] == clock
        if 'copiesEnd' in row:
            assert row['copiesEnd']-row['copiesStart'] == (120 if cached else 0)
        for stamp, interval in zip(row['sampleAtMs'],row['framesMs']):
            assert stamp-clock == interval and interval >= 0
            clock = stamp
            stamps.append(stamp)
            intervals.append(interval)
        for presentation in row['presentation']:
            assert presentation['regionRasterCalls'] == previous+(1 if cached else 0)
            assert presentation['uploads'] == presentation['regionRasterCalls']+end['texturesCreated']
            assert presentation['copies'] == presentation['regionRasterCalls']+end['allocated']-1
            assert presentation['regionRootQueries'] == presentation['regionItemsDrawn']+presentation['regionItemsSkipped']
            assert presentation['regionCullClassifications'] == first['regionCullClassifications']
            previous = presentation['regionRasterCalls']
    assert intervals == trial['framesMs'] and stamps == trial['sampleAtMs']
    assert previous == 124
    # One more update was executed, but its following interval hit the timeout
    # before it could be sampled; preserve the distinction in the report.
    assert end['regionRasterCalls'] == previous+1
    last = trial['windows'][-1]['presentation'][-1]
    fields = ('regionRasterMs','regionUploadMs','regionSelectionMs','regionItemDrawMs',
        'regionRootQueries','regionItemsDrawn','regionItemsSkipped')
    result['timedRefresh'] = {'calls':111,'incompleteGpuStaticWindow':True,'unsampledLastUpdate':True}
    for field in fields:
        result['timedRefresh'][field] = last[field]-first[field]
        result['timedRefresh'][field+'PerCall'] = (last[field]-first[field])/111
    pictures = [folder/'storage/stage3d-pixels'/name for name in ('refresh-native-1.png','refresh-region-1.png')]
    arrays = []
    for picture in pictures:
        with Image.open(picture) as image:
            assert image.size == (512,512)
            arrays.append(np.array(image.convert('RGBA'),dtype=np.int16))
    delta = np.abs(arrays[0]-arrays[1])
    rgb = delta[:,:,:3].max(axis=2)
    ys,xs = np.where(np.any(delta>0,axis=2))
    result['regionPixels'] = dict(inputs={str(p):base.sha(p) for p in pictures},
        maxRGB=int(rgb.max()),maxAlpha=int(delta[:,:,3].max()),differentPixels=len(xs),
        rgbOver2=int((rgb>2).sum()),alphaDifferences=int((delta[:,:,3]>0).sum()),
        bounds=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None)
    result['regionPixels']['accepted'] = result['regionPixels']['maxRGB']<=2 and result['regionPixels']['maxAlpha']==0
    result['visualMaxRGB'] = [p['candidate']['maxRGB'] for p in trial['pixels']]
    result['visualMaxAlpha'] = [p['candidate']['maxAlpha'] for p in trial['pixels']]
    dest = HERE/'run-review.json'
    assert not dest.exists()
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({key:result[key] for key in ('complete','frames','arms','timedRefresh','regionPixels','visualAccepted')}))


if __name__ == '__main__':
    main()
