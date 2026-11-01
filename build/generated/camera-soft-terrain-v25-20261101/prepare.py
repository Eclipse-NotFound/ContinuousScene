from pathlib import Path
import shutil
here=Path(__file__).resolve().parent
old=here.parent/'camera-soft-present-v22-20261101'
shutil.copy2(old/'work.py',here/'work.py')
shutil.copytree(old/'tests',here/'tests',dirs_exist_ok=True)
terrain=(here.parent/'camera-screen-cache-v13-20261101/ScreenTerrainCache.as').read_text('utf-8')
terrain=terrain.replace('private var mask:int;', 'private var mask:int;private var resolution:Number;')
terrain=terrain.replace('public function ScreenTerrainCache(mask:int=7){this.mask=mask;}', 'public function ScreenTerrainCache(mask:int=7,resolution:Number=.5){this.mask=mask;this.resolution=resolution;}')
terrain=terrain.replace('var matrix:Matrix=w.visual.transform.concatenatedMatrix;', 'var matrix:Matrix=w.visual.transform.concatenatedMatrix;matrix.scale(resolution,resolution);')
terrain=terrain.replace('matrix.a<0.5 || matrix.a>1 || matrix.tx!=Math.floor(matrix.tx) || matrix.ty!=Math.floor(matrix.ty)', 'matrix.a<0.2 || matrix.a>1')
terrain=terrain.replace('w.cam.screenX','(w.cam.screenX*resolution)').replace('w.cam.screenY','(w.cam.screenY*resolution)')
terrain=terrain.replace('new Bitmap(data,"always",false)', 'new Bitmap(data,"never",true)')
(here/'ScreenTerrainCache.as').write_text(terrain,'utf-8')
src=(old/'ContinuousSceneMotionMod.as').read_text('utf-8').replace('camera-soft-present-22','camera-soft-terrain-25')
src=src.replace('preAt=getTimer();\n            fill.restore();','preAt=getTimer();')
src=src.replace('w.gg.invulner=true;', 'w.gg.invulner=!options.dense;')
src=src.replace('["full","half","edge","edge","half","full"]','["full","half","soft","soft","half","full"]')
src=src.replace('if(options.nativePresentation)main.getChildByName', 'main.getChildByName')
src=src.replace('mark.fill.hidden && mark.fill.overlayVisible','mark.fill.active && mark.fill.errors==0')
src=src.replace('["half","edge","soft","half-low"]','["half","soft"]')
(here/'ContinuousSceneMotionMod.as').write_text(src,'utf-8')
print('Prepared v25: lower-resolution terrain only, actors/HUD and simulation stay native')
