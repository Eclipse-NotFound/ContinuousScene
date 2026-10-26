"""Independent interval/count, unchanged-input, and region-content audit."""
from pathlib import Path
import importlib.util
import json
from PIL import Image

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('region_identity_audit', HERE.parent/'camera-stage3d-wholeworld-settle-20261027/verify_runs.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
NAME = 'camera-stage3d-region-refresh-20261027-r1'


def main():
    result = base.review(NAME)
    folder = base.E/NAME
    raw = base.read(folder/'storage/result.json')
    trial = raw['cameraRaster']
    end = trial['cleanup']['presentation']
    assert trial['complete'] and len(trial['framesMs']) == 960 and trial['passed']
    assert end['regionRasterCalls'] == 493
    assert end['copies'] == end['allocated']-1+493
    assert end['uploads'] == end['texturesCreated']+493
    assert end['texturesCreated'] == end['texturesDisposed']
    assert end['allocated'] == end['disposed'] == end['texturesCreated']+1
    area = end['initial']['refreshArea']
    intersection = end['initial']['refreshIntersection']
    assert area['width'] == area['height'] == 512
    for origin, extent in (('x', 'width'), ('y', 'height')):
        assert intersection[origin] <= area[origin]
        assert area[origin]+area[extent] <= intersection[origin]+intersection[extent]
    first = trial['windows'][0]['presentation'][0]
    previous = first['regionRasterCalls']
    assert previous == 13
    for row in trial['windows']:
        cached = row['condition'] >= 2
        assert row['copiesEnd']-row['copiesStart'] == (120 if cached else 0)
        for presentation in row['presentation']:
            assert presentation['regionRasterCalls'] == previous+(1 if cached else 0)
            assert presentation['uploads'] == presentation['regionRasterCalls']+end['texturesCreated']
            assert presentation['copies'] == presentation['regionRasterCalls']+end['allocated']-1
            previous = presentation['regionRasterCalls']
    assert previous == 493
    last = trial['windows'][-1]['presentation'][-1]
    result['timedRefresh'] = dict(calls=480, rasterMs=last['regionRasterMs']-first['regionRasterMs'],
        uploadMs=last['regionUploadMs']-first['regionUploadMs'])
    result['timedRefresh']['meanRasterMs'] = result['timedRefresh']['rasterMs']/480
    result['timedRefresh']['meanUploadMs'] = result['timedRefresh']['uploadMs']/480
    picture = folder/'storage/stage3d-pixels/refresh-region-1.png'
    with Image.open(picture) as image:
        assert image.size == (512, 512)
        alpha = image.convert('RGBA').getchannel('A')
        histogram = alpha.histogram()
        result['regionContent'] = dict(path=str(picture), sha256=base.sha(picture),
            bounds=alpha.getbbox(), transparent=histogram[0], opaque=histogram[255],
            nonTransparent=512*512-histogram[0])
        assert result['regionContent']['nonTransparent'] > 0
    result['regionArea'] = area
    result['visualMaxRGB'] = [p['candidate']['maxRGB'] for p in trial['pixels']]
    result['visualMaxAlpha'] = [p['candidate']['maxAlpha'] for p in trial['pixels']]
    dest = HERE/'run-review.json'
    assert not dest.exists()
    dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
    print(json.dumps({key: result[key] for key in ('arms', 'pairs', 'timedRefresh', 'visualAccepted', 'regionContent')}))


if __name__ == '__main__':
    main()
