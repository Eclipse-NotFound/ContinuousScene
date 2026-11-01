from pathlib import Path
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'camera-scaled-fill-v9-20261101'
source=(OLD/'ContinuousSceneMotionMod.as').read_text('utf-8')
source=source.replace('LocalPhaseMaskedBitmapFill','ScreenTerrainCache').replace('camera-scaled-fill-9','camera-screen-cache-12')
source=source.replace('["static","x","y","y","x","static"]','["x","y","y","x"]').replace('frames:180','frames:270')
(HERE/'ContinuousSceneMotionMod.as').write_text(source,'utf-8')
(HERE/'work.py').write_text((OLD/'work.py').read_text('utf-8'),'utf-8')
print('Prepared device-resolution incremental terrain cache experiment.')
