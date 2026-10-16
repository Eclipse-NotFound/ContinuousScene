      private function sceneProfileComparePass(style:Object) : void
      {
         if(!this.sceneProfileWantOracle) return;
         if(this.sceneProfileRasterResult == null)
            this.sceneProfileRasterResult = {passes:0,layers:0,differentLayers:0,differentCorePixels:0,coreAbove8:0,maxChannelError:0,examples:[]};
         var result:Object = this.sceneProfileRasterResult;
         var buffers:Array = [this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
         var copies:Array = [];
         var previousLegacy:Boolean = this.sceneProfileLegacyMaterials;
         try
         {
            for each(var data:BitmapData in buffers) copies.push(data.clone());
            this.sceneProfileLegacyMaterials = true;
            this.sceneRegionDrawPass(style);
            --this.sceneRegionPasses;
            ++result.passes;
            for(var n:int = 0; n < 4; ++n)
            {
                  ++result.layers;
                  var difference:* = buffers[n].compare(copies[n]);
                  if(!(difference is BitmapData)) continue;
                  var pixels:Vector.<uint> = difference.getVector(difference.rect);
                  var count:int = 0;
                  for each(var pixel:uint in pixels) if(pixel != 0) ++count;
                  if(count > 0)
                  {
                     var legacy:Vector.<uint> = buffers[n].getVector(buffers[n].rect);
                     var fast:Vector.<uint> = copies[n].getVector(copies[n].rect);
                     for(var pi:int = 0; pi < legacy.length; ++pi)
                     {
                        var errorMax:int = 0;
                        for(var shift:int = 0; shift <= 24; shift += 8)
                           errorMax = Math.max(errorMax,Math.abs(int((legacy[pi] >>> shift) & 255)-int((fast[pi] >>> shift) & 255)));
                        result.maxChannelError = Math.max(result.maxChannelError,errorMax);
                        if(errorMax > 8) ++result.coreAbove8;
                     }
                     ++result.differentLayers;
                     result.differentCorePixels += count;
                     if(result.examples.length < 12) result.examples.push({x:this.sceneX,y:this.sceneY,layer:n,pixels:count});
                  }
                  difference.dispose();
            }
         }
         finally
         {
            this.sceneProfileLegacyMaterials = previousLegacy;
            for(var i:int = 0; i < copies.length; ++i)
            {
               buffers[i].copyPixels(copies[i],copies[i].rect,new Point());
               copies[i].dispose();
            }
         }
      }
