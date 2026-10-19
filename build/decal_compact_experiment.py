"""Rejected performance experiment; never applied by the production build."""
from pathlib import Path
import sys
from decal_patch import _once

HELPER = r"""      public var sceneCompactImpacts:Boolean = true;

      // Keep the native surface origin while shortening its temporary canvas.
      // Moving the raster origin can change rotated vector antialiasing even
      // by an integer offset, so only crop the far right/bottom empty area.
      // The unchanged world mark is still replayed when another chunk appears.
      private function sceneApplyCompactDecal(args:Array, affected:Rectangle) : void
      {
         var area:Rectangle = affected.intersection(new Rectangle(this.sceneX,this.sceneY,this.frontBmp.width,this.frontBmp.height));
         if(area.isEmpty()) return;
         area = new Rectangle(Math.floor(area.x),Math.floor(area.y),Math.ceil(area.right)-Math.floor(area.x),Math.ceil(area.bottom)-Math.floor(area.y));
         if(!this.sceneCompactImpacts || area.width > this.sceneSide || area.height > this.sceneSide)
         {
            this.sceneApplyRegionAction("decal",args,affected); return;
         }
         var previous:BitmapData = this.frontBmp;
         var ox:int = this.sceneX;
         var oy:int = this.sceneY;
         var width:int = this.rectX;
         var height:int = this.rectY;
         var local:Rectangle = area.clone(); local.offset(-ox,-oy);
         var temporary:BitmapData = new BitmapData(int(local.right),int(local.bottom),true,0);
         temporary.copyPixels(previous,local,local.topLeft);
         try
         {
            this.frontBmp = temporary;
            this.rectX = temporary.width; this.rectY = temporary.height;
            this.sceneApplyRegionAction("decal",args,affected);
            previous.copyPixels(temporary,local,local.topLeft);
         }
         finally
         {
            this.frontBmp = previous; this.sceneX = ox; this.sceneY = oy;
            this.rectX = width; this.rectY = height; temporary.dispose();
         }
      }

"""


def apply_compact(source: str) -> str:
    # Regional dispatch is added after the native decal helper patch.
    return _once(source, '               this.sceneApplyRegionAction(kind,args,affected);',
                 '               if(kind == "decal") this.sceneApplyCompactDecal(args,affected);\n'
                 '               else this.sceneApplyRegionAction(kind,args,affected);')

if __name__ == "__main__":
    path=Path(sys.argv[1])
    s=path.read_text(encoding="utf-8-sig")
    s=_once(s,"      // Match the two native decal frame choices",HELPER+"      // Match the two native decal frame choices")
    path.write_text(apply_compact(s),encoding="utf-8")
