"""Generate narrowly anchored AS3 patches from the verified, current SWF export.

Only writes build/generated and build/runtime inside this project.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import render_camera_patch
import decal_patch
import map_patch
import backdrop_patch
import region_patch
import entity_color_patch
import interaction_patch
import load_patch
import native_map_patch
import material_bounds_patch
import progressive_patch

MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parents[1]
SOURCE = MOD / 'build/cache/current-swf/scripts'
OUT = MOD / 'build/generated/scripts'
RUNTIME = MOD / 'build/runtime'
BASELINE = 'c631cbf3511b6ee303f533d08d51511fe0eb702f43e5db17f5241d8576c64867'
MERGE_SOURCE = ROOT / 'mods/RConnect/build/m52/a22-map-only-03/native'
MERGE_BASELINE = 'bebeea8b3f40a7db3e7b1be6f3530d5af9ea7a3299decb164bf0dae107d4011f'
LAND_BASELINE = 'b1727e83fbec9863a267b07b5428853cb734c442572d747d592922e8b1ebc060'

def replace(text, old, new, count=1):
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f'Anchor mismatch: expected {count}, got {actual}: {old[:100]}')
    return text.replace(old, new)

def method(text, name, change):
    start = re.search(r'\bfunction ' + re.escape(name) + r'\(', text).start()
    next_method = re.search(r'\n      (?:public|private|internal|protected) function ', text[start+1:])
    end = start + 1 + next_method.start() if next_method else text.rfind('   }')
    return text[:start] + change(text[start:end]) + text[end:]

def write_class(name, text):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

def patches():
    baseline = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'pfe.swf'
    actual = hashlib.sha256(baseline.read_bytes()).hexdigest()
    if actual != BASELINE:
        raise RuntimeError('Current game SWF changed; export/review it before building.')
    if hashlib.sha256((MERGE_SOURCE/'pfe.swf').read_bytes()).hexdigest() != MERGE_BASELINE:
        raise RuntimeError('Published RConnect Map1 merge host changed; review it before building.')
    land_path = MERGE_SOURCE/'after/scripts/fe/loc/Land.as'
    if hashlib.sha256(land_path.read_bytes()).hexdigest() != LAND_BASELINE:
        raise RuntimeError('Published RConnect Map1 Land source changed; review it before building.')
    location = (SOURCE/'fe/loc/Location.as').read_text(encoding='utf-8-sig')
    location = replace(location, 'this.spaceY = World.cellsY;', '''this.spaceY = World.cellsY;
         if(param2.@sceneWidth.length() || param2.@sceneHeight.length())
         {
            this.spaceX = int(param2.@sceneWidth);
            this.spaceY = int(param2.@sceneHeight);
            if(this.spaceX < 48 || this.spaceY < 25 || this.spaceX > 512 || this.spaceY > 256)
               throw new Error("ContinuousScene dimensions out of bounds (48..512 by 25..256)");
         }''')
    location = replace(location, 'this.buildLoc(param2);', 'this.buildLoc(param2);\n         World.w.grafon.sceneTrack(this,String(param2.@sceneRevision));')
    write_class('fe/loc/Location.as', native_map_patch.location(region_patch.apply_location(location), method))

    game = (SOURCE/'fe/loc/Game.as').read_text(encoding='utf-8-sig')
    game = method(game, 'save', lambda s: replace(s, 'var _loc1_:Object = new Object();', 'World.w.grafon.sceneSave(this);\n         var _loc1_:Object = new Object();'))
    write_class('fe/loc/Game.as', native_map_patch.game(game))

    # Preserve the deployed seed callback, seed field, and constructor; only
    # our createMap body is selected for the final method-level replacement.
    land = land_path.read_text(encoding='utf-8-sig')
    write_class('fe/loc/Land.as', native_map_patch.land(map_patch.apply_land(land)))
    area = (SOURCE/'fe/loc/Area.as').read_text(encoding='utf-8-sig')
    write_class('fe/loc/Area.as', native_map_patch.area(area))
    unit = (SOURCE/'fe/unit/Unit.as').read_text(encoding='utf-8-sig')
    write_class('fe/unit/Unit.as', entity_color_patch.apply_unit(unit))
    box = (SOURCE/'fe/loc/Box.as').read_text(encoding='utf-8-sig')
    write_class('fe/loc/Box.as', entity_color_patch.apply_box(box))
    player = (SOURCE/'fe/unit/UnitPlayer.as').read_text(encoding='utf-8-sig')
    write_class('fe/unit/UnitPlayer.as', interaction_patch.apply_unit_player(player))

    grafon = (SOURCE/'fe/graph/Grafon.as').read_text(encoding='utf-8-sig')
    extension = (MOD/'src/patches/GrafonChunks.as.inc').read_text(encoding='utf-8')
    extension += (MOD/'src/patches/ScenePersistence.as.inc').read_text(encoding='utf-8')
    grafon = replace(grafon, '      public function Grafon(param1:Sprite)', extension + '      public function Grafon(param1:Sprite)')
    def drawloc(s):
        s = replace(s, 'var transpFon:Boolean = false;', '''if(!this.sceneRasterizing && (param1.spaceX > World.cellsX || param1.spaceY > World.cellsY))
         {
            this.sceneOpen(param1); return;
         }
         var sceneStarted:int = getTimer();
         this.scenePrepare(param1);
         var transpFon:Boolean = false;''')
        s = replace(s, 'i = 0;', 'i = Math.max(0,this.sceneX / Tile.tileX - 2);')
        s = replace(s, 'i < this.loc.spaceX', 'i < Math.min(this.loc.spaceX,(this.sceneX + this.rectX) / Tile.tileX + 2)')
        s = replace(s, 'j = 0;', 'j = Math.max(0,this.sceneY / Tile.tileY - 2);')
        s = replace(s, 'j < this.loc.spaceY', 'j < Math.min(this.loc.spaceY,(this.sceneY + this.rectY) / Tile.tileY + 2)')
        s = replace(s, 'this.lightBmp.fillRect(this.lightRect,4278190080);\n            this.setLight();', '''if(!this.sceneRepaint)
            {
               this.lightBmp.fillRect(this.lightRect,4278190080);
               this.setLight();
            }''')
        # DisplayObject sources use world coordinates; scratch BitmapData composites stay local.
        # backBmp2 ends with a digit. The old *Bmp regex silently missed that
        # layer, stamping its pipes/fences at the same local position in every chunk.
        s, count = re.subn(r'(this\.(?:vodaBmp|frontBmp|backBmp2)\.draw\((?:voda|front|back|back2),)new Matrix\(\)', r'\1this.sceneMatrix()', s)
        if count != 4: raise RuntimeError('Expected four world-space tile draws')
        s, count = re.subn(r'(this\.(?:backBmp|backBmp2|satsBmp|colorBmp)\.draw\(bo\.(?:vis|erase|light),)this\.m', r'\1this.sceneMatrix(this.m)', s)
        if count != 4: raise RuntimeError('Expected four world-space decoration draws')
        s = replace(s, 'this.backBmp2.draw(this.getObj("back_pink_t",numbBack),this.m,', 'this.backBmp2.draw(this.getObj("back_pink_t",numbBack),this.sceneMatrix(this.m),')
        s = replace(s, 'this.drawAllObjs();', '''this.sceneRestoreMarks();
         if(!this.sceneRepaint) this.drawAllObjs();
         this.sceneDrawMs = getTimer() - sceneStarted;
         if(this.sceneLarge) this.sceneMaxDrawMs = Math.max(this.sceneMaxDrawMs,this.sceneDrawMs);
         ++this.sceneRedraws;''')
        return s
    grafon = method(grafon, 'drawLoc', drawloc)
    def worlddraw(s):
        return s.replace('this.m,null,null,null,false);', 'this.sceneMatrix(this.m),null,null,null,false);').replace('this.m,this.loc.cTransform,null,null,false);', 'this.sceneMatrix(this.m),this.loc.cTransform,null,null,false);')
    grafon = method(grafon, 'drawBackWall', worlddraw)
    def kusok(s):
        s = worlddraw(s)
        for factory in ['textureMask','borderMask','floorMask']:
            s = replace(s, 'new param1.'+factory+'()', 'this.sceneMask(param1.'+factory+')')
        s = replace(s, 'var _loc14_:* = 0;', 'var _loc14_:* = Math.max(0,this.sceneX / Tile.tileX - 2);')
        s = replace(s, '_loc14_ < this.loc.spaceX', '_loc14_ < Math.min(this.loc.spaceX,(this.sceneX + this.rectX) / Tile.tileX + 2)')
        s = replace(s, '_loc15_ = 0;', '_loc15_ = Math.max(0,this.sceneY / Tile.tileY - 2);')
        s = replace(s, '_loc15_ < this.loc.spaceY', '_loc15_ < Math.min(this.loc.spaceY,(this.sceneY + this.rectY) / Tile.tileY + 2)')
        # Avoid allocating scene-sized mask caches; bitmap fill remains globally aligned.
        s = replace(s, 'drawRect(0,0,this.kusokX * Tile.tileX,this.kusokY * Tile.tileY)', 'drawRect(Math.max(0,this.sceneX - 80),Math.max(0,this.sceneY - 80),this.rectX + 160,this.rectY + 160)', 3)
        return s
    grafon = method(grafon, 'drawKusok', kusok)
    def dispatch(s, kind, args):
        pos = s.index('{') + 1
        return s[:pos] + '\n         if(this.sceneLarge && !this.sceneRasterizing) { this.sceneApply("'+kind+'",['+args+']); return; }\n' + s[pos:]
    grafon = method(grafon, 'drawWater', lambda s: dispatch(replace(s, 'this.m,this.loc.cTransform', 'this.sceneMatrix(this.m),this.loc.cTransform'),'drawWater','param1,param2'))
    grafon = method(grafon, 'drawSats', lambda s: replace(s, 'this.satsBmp.fillRect', 'if(this.sceneLarge) { this.sceneSats(); return; }\n         this.satsBmp.fillRect'))
    grafon = method(grafon, 'gwall', lambda s: dispatch(replace(s, 'this.frontBmp.draw(_loc4_,_loc3_)', 'this.frontBmp.draw(_loc4_,this.sceneMatrix(_loc3_))'),'gwall','param1,param2'))
    def decal(s):
        s = dispatch(s,'decal','param1,param2,param3,param4,param5,param6,param7')
        # A single native mark must keep the same frame across chunks and reloads.
        s = replace(s, 'Math.random() * _loc8_.totalFrames', '(this.sceneStamp != null ? Number(this.sceneStamp[0]) : Math.random()) * _loc8_.totalFrames')
        s = replace(s, 'Math.random() * _loc9_.totalFrames', '(this.sceneStamp != null ? Number(this.sceneStamp[1]) : Math.random()) * _loc9_.totalFrames')
        return replace(s, 'var _loc8_:MovieClip = null;', '''param3 -= this.sceneX;
         param4 -= this.sceneY;
         if(this.sceneLarge && (param3 < -512 || param4 < -512 || param3 > this.rectX + 512 || param4 > this.rectY + 512)) return;
         var _loc8_:MovieClip = null;''')
    grafon = method(grafon, 'decal', decal)
    def paint(s):
        s = dispatch(s,'paint','param1,param2,param3,param4,param5')
        return replace(s, 'var _loc6_:MovieClip = null;', '''param1 -= this.sceneX; param3 -= this.sceneX;
         param2 -= this.sceneY; param4 -= this.sceneY;
         if(this.sceneLarge && (Math.max(param1,param3) < -50 || Math.max(param2,param4) < -50 || Math.min(param1,param3) > this.rectX + 50 || Math.min(param2,param4) > this.rectY + 50)) return;
         var _loc6_:MovieClip = null;''')
    grafon = method(grafon, 'paint', paint)
    grafon = decal_patch.apply_grafon(grafon)
    grafon = render_camera_patch.apply_grafon(grafon)
    grafon = backdrop_patch.apply_grafon(grafon)
    grafon = region_patch.apply_grafon(grafon)
    grafon = entity_color_patch.apply_grafon(grafon)
    grafon = load_patch.apply_grafon(grafon)
    grafon = native_map_patch.grafon(grafon)
    grafon = material_bounds_patch.apply_grafon(grafon)
    grafon = progressive_patch.apply_grafon(grafon)
    write_class('fe/graph/Grafon.as', grafon)

    camera = (SOURCE/'fe/inter/Camera.as').read_text(encoding='utf-8-sig')
    camera = replace(camera, 'if(this.isZoom == 1)', 'if(World.w.loc && (World.w.loc.spaceX > World.cellsX || World.w.loc.spaceY > World.cellsY)) this.isZoom = 0;\n         if(this.isZoom == 1)')
    camera = replace(camera, 'Snd.centrX = this.X;', 'this.w.grafon.sceneTick();\n         Snd.centrX = this.X;')
    write_class('fe/inter/Camera.as', render_camera_patch.apply_camera(camera))

    # Keep production MainFE and its native manifest loader byte-identical.
    old_main=OUT/'MainFE.as'
    if old_main.exists(): old_main.unlink()
    (MOD/'build/generated/baseline.json').write_text(json.dumps({'source_sha256':actual,'merge_source_sha256':MERGE_BASELINE,'merge_source':str(MERGE_SOURCE/'pfe.swf'),'land_source_sha256':LAND_BASELINE,'patched_classes':['fe.loc.Game','fe.loc.Land','fe.loc.Location','fe.graph.Grafon','fe.inter.Camera','fe.unit.Unit','fe.loc.Box','fe.unit.UnitPlayer']},indent=2),encoding='utf-8')

def scene():
    width,height = 192,60
    room = ET.Element('room',name='continuous-lab',sceneWidth=str(width),sceneHeight=str(height),sceneRevision='lab-2')
    ET.SubElement(room,'options',black='0',color='yellow',darkness='-120')
    for y in range(height):
        cells=[]
        for x in range(width):
            cell = '_R' if 80 <= x <= 88 else '_Q'
            if x in (0,width-1) or y in (0,height-1) or y >= 54: cell='A'
            if y >= 54 and 80 <= x <= 88: cell='C'
            if y >= 54 and 128 <= x <= 131: cell='I'
            if y >= 54 and 132 <= x <= 135: cell='C'
            if y >= 54 and 152 <= x <= 155: cell='G'
            if y >= 54 and 156 <= x <= 159: cell='H'
            # Three suspended decks leave large traversable shafts and a continuous floor.
            if y in (18,36) and x % 48 < 30 and x > 4: cell='J'
            if y == 48 and 76 <= x <= 88: cell='C'
            cells.append(cell)
        ET.SubElement(room,'a').text='.'.join(cells)
    ET.SubElement(room,'obj',id='player',x='7',y='53',code='cs-spawn')
    root=ET.Element('all'); root.append(room)
    # Keep the old sparse corridor solely as an isolated combat regression fixture.
    (RUNTIME/'scene-lab.xml').write_bytes(ET.tostring(root,encoding='utf-8',xml_declaration=True))

def resources():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for pattern in ['texture*.swf','sprite*.swf','sound*.swf','text_*.xml','lang.xml']:
        for src in ROOT.glob(pattern):
            dest=RUNTIME/src.name
            if not dest.exists() or dest.stat().st_size != src.stat().st_size: shutil.copy2(src,dest)
    for folder in ['Rooms','Music','Texture']:
        if (ROOT/folder).exists(): shutil.copytree(ROOT/folder,RUNTIME/folder,dirs_exist_ok=True)
    (RUNTIME/'mods').mkdir(exist_ok=True)
    (RUNTIME/'drivers').mkdir(exist_ok=True)
    (RUNTIME/'mods/loader-manifest.txt').write_text('ContinuousScene|ContinuousSceneMod|1|0|0\nContinuousSceneProbe|ContinuousSceneProbe|1|0|0\n',encoding='utf-8')
    descriptor='''<?xml version="1.0" encoding="utf-8"?>
<application xmlns="http://ns.adobe.com/air/application/30.0">
  <id>pfe-modsettings-continuous-scene</id><versionNumber>0.1.0</versionNumber>
  <filename>ContinuousSceneLab</filename><name>Remains Continuous Scene Lab</name>
  <initialWindow><content>pfe.swf</content><visible>false</visible><width>1280</width><height>800</height><renderMode>direct</renderMode><resizable>true</resizable></initialWindow>
  <supportedProfiles>extendedDesktop</supportedProfiles>
</application>'''
    (RUNTIME/'application.xml').write_text(descriptor,encoding='utf-8')

if __name__ == '__main__':
    patches()
    if '--sources-only' not in sys.argv:
        resources(); scene()
        from factory_scene import build as factory
        factory()
    print(json.dumps({'generated':str(OUT),'runtime':str(RUNTIME)},ensure_ascii=False))
