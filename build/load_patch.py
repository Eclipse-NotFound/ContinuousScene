"""Batch initial raster work without increasing per-impact damage surfaces."""
from pathlib import Path
from render_camera_patch import _replace


def apply_grafon(source):
    source = _replace(source, '   import flash.display.Sprite;', '   import flash.display.Sprite;\n   import flash.events.Event;\n   import flash.events.DataEvent;')
    source = _replace(source, '         this.loc = value; value.grafon = this; this.sceneLarge = true;',
                      '         this.loc = value; value.grafon = this; this.sceneLarge = true;\n'
                      '         World.w.main.dispatchEvent(new Event("continuousSceneBeforeRaster"));')
    source = _replace(source, '      private function sceneClear() : void\n      {',
                      '      private function sceneClear() : void\n      {\n'
                      '         World.w.main.dispatchEvent(new Event("continuousSceneBeforeRasterClear"));')
    source = _replace(source, '      private function sceneSats() : void\n      {', '''      private function sceneSats() : void
      {
         var sceneHidden:Array = [];
         for each(var surface:Object in this.sceneChunks) for each(var raster:Bitmap in surface.bitmaps)
            if(!raster.visible) { sceneHidden.push(raster); raster.visible = true; }
         for each(var parent:Sprite in [this.visFront,this.visBack]) for(var i:int = 0; i < parent.numChildren; ++i)
         {
            raster = parent.getChildAt(i) as Bitmap;
            if(raster != null && !raster.visible && (raster.name == "WallBlendSceneFront" || raster.name == "WallBlendSceneBack"))
            { sceneHidden.push(raster); raster.visible = true; }
         }
         try
         {''')
    source = _replace(source, '            this.visSats.addChild(bitmap); entry.sats = bitmap;\n         }\n      }',
                      '            this.visSats.addChild(bitmap); entry.sats = bitmap;\n         }\n'
                      '         } finally { for each(raster in sceneHidden) raster.visible = false; }\n      }')
    # Pooled masks must not retain their temporary parents. Otherwise each
    # unused mask keeps an entire cached material Sprite tree alive between
    # passes, including its native renderer allocations outside AS3 memory.
    source = _replace(source, '''            this.backBmp.draw(_loc6_,this.sceneMatrix(this.m),null,null,null,false);
         }
      }''', '''            this.backBmp.draw(_loc6_,this.sceneMatrix(this.m),null,null,null,false);
         }
         if(this.sceneLarge)
         {
            _loc7_.mask = null; _loc9_.mask = null; _loc11_.mask = null;
            _loc6_.filters = [];
            for each(var sceneLayer:Sprite in [_loc7_,_loc8_,_loc9_,_loc10_,_loc11_,_loc12_])
            {
               sceneLayer.cacheAsBitmap = false;
               sceneLayer.graphics.clear();
               while(sceneLayer.numChildren > 0) sceneLayer.removeChildAt(sceneLayer.numChildren - 1);
            }
            while(_loc6_.numChildren > 0) _loc6_.removeChildAt(_loc6_.numChildren - 1);
         }
      }''')
    source = _replace(source,
        'var width:int = this.sceneLarge ? this.sceneSide + this.sceneGutter * 2 : 1920;',
        'var width:int = this.scenePreloadWidth > 0 ? this.scenePreloadWidth : (this.sceneLarge ? this.sceneSide * (this.sceneBatch ? this.sceneBatchCells : 1) + this.sceneGutter * 2 : 1920);')
    source = _replace(source, 'var height:int = this.sceneLarge ? width : 1000;',
                      'var height:int = this.scenePreloadHeight > 0 ? this.scenePreloadHeight : (this.sceneLarge ? width : 1000);')
    source = _replace(source,
        '         if(this.scenePreload)\n         {\n            left = top = 0; width = this.loc.limX - 1; height = this.loc.limY - 1;\n         }',
        '         if(this.scenePreload)\n         {\n            this.scenePreloadAll(); return;\n         }')
    extension = (Path(__file__).resolve().parents[1] / 'src/patches/ScenePreload.as.inc').read_text(encoding='utf-8')
    return _replace(source, '      public function Grafon(param1:Sprite)', extension + '      public function Grafon(param1:Sprite)')
