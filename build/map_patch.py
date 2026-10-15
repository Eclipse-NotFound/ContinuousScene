"""Expand the native local-map canvas to include actual Location dimensions.

The native grid origin and one-pixel-per-tile coordinates remain unchanged.
This is source preparation only; the caller owns bytecode export and audit.
"""

_ORIGINAL = """      public function createMap() : *
      {
         this.map = new BitmapData(World.cellsX * (this.maxLocX - this.minLocX),World.cellsY * (this.maxLocY - this.minLocY),true,0);
      }"""

_REPLACEMENT = """      public function createMap() : *
      {
         var mapWidth:int = World.cellsX * (this.maxLocX - this.minLocX);
         var mapHeight:int = World.cellsY * (this.maxLocY - this.minLocY);
         var mapLoc:Location;
         for(var mapX:int = this.minLocX; mapX < this.maxLocX; ++mapX)
         {
            for(var mapY:int = this.minLocY; mapY < this.maxLocY; ++mapY)
            {
               mapLoc = this.locs[mapX][mapY][0];
               if(mapLoc != null)
               {
                  mapWidth = Math.max(mapWidth,(mapLoc.landX - this.minLocX) * World.cellsX + mapLoc.spaceX);
                  mapHeight = Math.max(mapHeight,(mapLoc.landY - this.minLocY) * World.cellsY + mapLoc.spaceY);
               }
            }
         }
         this.map = new BitmapData(mapWidth,mapHeight,true,0);
      }"""


def apply_land(source: str) -> str:
    """Replace exactly the verified 1.02 allocator; reject drift or reapplication."""
    if source.count("function createMap(") != 1:
        raise RuntimeError("Expected exactly one Land.createMap method")
    count = source.count(_ORIGINAL)
    if count != 1:
        raise RuntimeError(f"Land.createMap anchor mismatch: expected 1, got {count}")
    return source.replace(_ORIGINAL, _REPLACEMENT, 1)
