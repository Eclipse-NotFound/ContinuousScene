"""Keep native vector masks/filters; exclude transparent space from filter bounds."""
from render_camera_patch import _replace


def apply_grafon(source):
    source = _replace(source,
        '         _loc7_.cacheAsBitmap = _loc8_.cacheAsBitmap = _loc9_.cacheAsBitmap = _loc10_.cacheAsBitmap = _loc11_.cacheAsBitmap = _loc12_.cacheAsBitmap = true;',
        '''         if(this.sceneLarge)
         {
            var scenePaintRect:Rectangle = new Rectangle(Math.max(0,this.sceneX-80),Math.max(0,this.sceneY-80),this.rectX+160,this.rectY+160);
            this.sceneMaterialFill(_loc7_,_loc8_,this.loc.homeStable && param1.alttexture != null ? param1.alttexture : param1.texture,scenePaintRect);
            if(param1.border) this.sceneMaterialFill(_loc9_,_loc10_,param1.border,scenePaintRect);
            if(param1.floor) this.sceneMaterialFill(_loc11_,_loc12_,param1.floor,scenePaintRect);
         }
         _loc7_.cacheAsBitmap = _loc8_.cacheAsBitmap = _loc9_.cacheAsBitmap = _loc10_.cacheAsBitmap = _loc11_.cacheAsBitmap = _loc12_.cacheAsBitmap = true;''')
    helper = '''      private function sceneMaterialFill(fill:Sprite,mask:Sprite,texture:BitmapData,clip:Rectangle) : void
      {
         var bounds:Rectangle = mask.getBounds(mask);
         fill.graphics.clear();
         if(bounds.isEmpty()) return;
         bounds = new Rectangle(Math.floor(bounds.left)-1,Math.floor(bounds.top)-1,
            Math.ceil(bounds.right)-Math.floor(bounds.left)+2,Math.ceil(bounds.bottom)-Math.floor(bounds.top)+2).intersection(clip);
         if(bounds.isEmpty()) return;
         if(texture == null) fill.graphics.beginFill(6710886);
         else fill.graphics.beginBitmapFill(texture);
         fill.graphics.drawRect(bounds.x,bounds.y,bounds.width,bounds.height);
      }

'''
    return _replace(source, '      public function Grafon(param1:Sprite)', helper + '      public function Grafon(param1:Sprite)')
