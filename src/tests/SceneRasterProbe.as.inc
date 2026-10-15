      public function sceneProfilePixels() : Object
      {
         var result:Object = {surfaces:0,layers:0,differentLayers:0,differentCorePixels:0,examples:[]};
         var core:Rectangle = new Rectangle(this.sceneGutter,this.sceneGutter,this.sceneSide,this.sceneSide);
         this.sceneRasterizing = true;
         this.sceneRepaint = true;
         try
         {
            for each(var surface:Object in this.sceneChunks)
            {
               // Cover outer edges, both region seams, and interior material.
               // This diagnostic stays below one frame's renderer cache budget.
               if(["0:0","1:2","5:2","5:3","6:3","7:6","11:6","12:6","17:3","18:6","22:8","23:9"].indexOf(surface.cx+":"+surface.cy)<0) continue;
               ++result.surfaces;
               this.sceneX = surface.x; this.sceneY = surface.y;
               this.sceneDrawRegionChunk();
               var buffers:Array = [this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
               for(var n:int = 0; n < 4; ++n)
               {
                  ++result.layers;
                  var difference:* = buffers[n].compare(surface.nativeBuffers[n]);
                  if(!(difference is BitmapData)) continue;
                  var pixels:Vector.<uint> = difference.getVector(core);
                  var count:int = 0;
                  for each(var pixel:uint in pixels) if(pixel != 0) ++count;
                  if(count > 0)
                  {
                     ++result.differentLayers;
                     result.differentCorePixels += count;
                     if(result.examples.length < 8) result.examples.push({cx:surface.cx,cy:surface.cy,layer:n,pixels:count});
                  }
                  difference.dispose();
               }
            }
         }
         catch(error:*)
         {
            this.sceneX = this.sceneY = 0;
            this.sceneRasterizing = this.sceneRepaint = false;
            throw error;
         }
         this.sceneX = this.sceneY = 0;
         this.sceneRasterizing = this.sceneRepaint = false;
         return result;
      }
