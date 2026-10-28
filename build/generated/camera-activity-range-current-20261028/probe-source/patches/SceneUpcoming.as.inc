      private var sceneUpcomingReady:Boolean = false;
      private var sceneNextWarm:int = 0;
      public var sceneWarmMaxMs:int = 0;
      public var sceneWarmCount:int = 0;

      public function sceneViewReady() : Boolean
      {
         if(!this.sceneLarge) return true;
         var view:Rectangle = this.sceneViewport();
         if(view == null) view = new Rectangle(0,0,this.loc.limX,this.loc.limY);
         var minX:int = Math.max(0,Math.floor(view.left / this.sceneSide));
         var minY:int = Math.max(0,Math.floor(view.top / this.sceneSide));
         var maxX:int = Math.min(Math.ceil(this.loc.limX / this.sceneSide)-1,Math.floor((view.right-1) / this.sceneSide));
         var maxY:int = Math.min(Math.ceil(this.loc.limY / this.sceneSide)-1,Math.floor((view.bottom-1) / this.sceneSide));
         for(var x:int = minX; x <= maxX; ++x) for(var y:int = minY; y <= maxY; ++y)
            if(!this.sceneChunks[x+":"+y]) return false;
         return true;
      }

      private function sceneEnsureUpcoming(left:Number,top:Number,width:Number,height:Number) : void
      {
         // Cover the actual camera including its current shake. The two-cell
         // upcoming ring is prepared separately; a hidden 80px margin otherwise
         // draws a whole extra native room at an exactly aligned room edge.
         var minX:int = Math.max(0,Math.floor(left/this.sceneSide));
         var minY:int = Math.max(0,Math.floor(top/this.sceneSide));
         var maxX:int = Math.min(Math.ceil(this.loc.limX/this.sceneSide)-1,Math.ceil((left+width)/this.sceneSide)-1);
         var maxY:int = Math.min(Math.ceil(this.loc.limY/this.sceneSide)-1,Math.ceil((top+height)/this.sceneSide)-1);
         if(!this.sceneUpcomingReady)
         {
            // Camera.setLoc and the native spawn have both completed by now.
            // Batch the first viewport, rather than preparing the old room's
            // position in sceneOpen and doing it a second time after spawn.
            this.sceneUpcomingReady = true;
            if(this.sceneRegionData[this.loc] != null) this.sceneFirstWindow(minX,minY,maxX,maxY);
         }
         for(var x:int = minX; x <= maxX; ++x) for(var y:int = minY; y <= maxY; ++y)
            if(!this.sceneChunks[x+":"+y]) {++this.sceneMisses;this.sceneRender(x,y);}
         // No preparation is hidden outside the measured entry. After control
         // returns, prepare one nearest upcoming tile, favouring travel direction.
         if(World.w.t_exit != 0) {this.sceneNextWarm=getTimer()+250;return;}
         if(getTimer() < this.sceneNextWarm) return;
         var centerX:Number = left+width/2;
         var centerY:Number = top+height/2;
         var dx:Number = this.loc.gg.dx;
         var dy:Number = this.loc.gg.dy;
         centerX += Math.max(-640,Math.min(640,dx*60));
         centerY += Math.max(-640,Math.min(640,dy*60));
         var bestX:int = -1;
         var bestY:int = -1;
         var best:Number = Number.MAX_VALUE;
         for(x = Math.max(0,minX-2); x <= Math.min(Math.ceil(this.loc.limX/this.sceneSide)-1,maxX+2); ++x)
            for(y = Math.max(0,minY-2); y <= Math.min(Math.ceil(this.loc.limY/this.sceneSide)-1,maxY+2); ++y)
            {
               if(this.sceneChunks[x+":"+y]) continue;
               var score:Number = Math.abs((x+0.5)*this.sceneSide-centerX)+Math.abs((y+0.5)*this.sceneSide-centerY);
               if(score < best) {best=score;bestX=x;bestY=y;}
            }
         if(bestX >= 0)
         {
            var started:int = getTimer();
            this.sceneRender(bestX,bestY);
            var elapsed:int = getTimer()-started;
            this.sceneWarmMaxMs = Math.max(this.sceneWarmMaxMs,elapsed);++this.sceneWarmCount;
            this.sceneNextWarm = getTimer()+100;
         }
      }

      private function sceneFirstWindow(minX:int,minY:int,maxX:int,maxY:int) : void
      {
         var regions:Array = this.sceneRegionData[this.loc];
         var area:Number = 0;
         for each(var region:Object in regions) area+=region.bounds.width*region.bounds.height;
         if(area != this.loc.limX*this.loc.limY) return;
         var original:Object = {backwall:this.loc.backwall,color:this.loc.color,cTransform:this.loc.cTransform,
            darkness:this.loc.darkness,backform:this.loc.backform,transpFon:this.loc.transpFon,
            tipWater:this.loc.tipWater,gas:this.loc.gas,homeStable:this.loc.homeStable};
         var size:int = this.sceneSide+2*this.sceneGutter;
         var parents:Array = [this.visFront,this.visBack,this.visBack2,this.visVoda];
         var requested:Rectangle = new Rectangle(minX*this.sceneSide-this.sceneGutter,minY*this.sceneSide-this.sceneGutter,
            (maxX-minX+1)*this.sceneSide+2*this.sceneGutter,(maxY-minY+1)*this.sceneSide+2*this.sceneGutter);
         var made:Array = [];
         this.sceneRasterizing = true;this.sceneRepaint = true;
         try
         {
            for(var cx:int = minX; cx <= maxX; ++cx) for(var cy:int = minY; cy <= maxY; ++cy)
            {
               var key:String = cx+":"+cy;
               if(this.sceneChunks[key]) continue;
               var buffers:Array = [];
               var bitmaps:Array = [];
               for(var n:int = 0; n < 4; ++n)
               {
                  var data:BitmapData = new BitmapData(size,size,true,0);
                  var bitmap:Bitmap = new Bitmap(data);
                  bitmap.scrollRect = new Rectangle(this.sceneGutter,this.sceneGutter,this.sceneSide,this.sceneSide);
                  bitmap.x=cx*this.sceneSide;bitmap.y=cy*this.sceneSide;
                  parents[n].addChild(bitmap);bitmaps.push(bitmap);buffers.push(data);
               }
               var x:int = cx*this.sceneSide-this.sceneGutter;
               var y:int = cy*this.sceneSide-this.sceneGutter;
               var surface:Object = {cx:cx,cy:cy,bitmaps:bitmaps,sats:null,nativeBuffers:buffers,revision:0,
                  backobjs:this.sceneBackdropObjects(x,y,size,size),x:x,y:y,side:this.sceneSide,gutter:this.sceneGutter};
               this.sceneChunks[key]=surface;made.push(surface);++this.sceneResident;
            }
            for each(var style:Object in regions)
            {
               var clip:Rectangle = style.bounds.clone();
               if(clip.left == 0) clip.left=-this.sceneGutter;
               if(clip.top == 0) clip.top=-this.sceneGutter;
               if(clip.right == this.loc.limX) clip.right=Math.ceil(this.loc.limX/this.sceneSide)*this.sceneSide+this.sceneGutter;
               if(clip.bottom == this.loc.limY) clip.bottom=Math.ceil(this.loc.limY/this.sceneSide)*this.sceneSide+this.sceneGutter;
               clip=clip.intersection(requested);
               if(clip.isEmpty()) continue;
               var draw:Rectangle = clip.clone();draw.inflate(this.sceneGutter,this.sceneGutter);
               this.sceneX=draw.x;this.sceneY=draw.y;
               this.scenePreloadWidth=draw.width;this.scenePreloadHeight=draw.height;
               this.scenePrepare(this.loc);this.sceneRegionDrawPass(style);
               buffers=[this.frontBmp,this.backBmp,this.backBmp2,this.vodaBmp];
               for each(surface in made)
               {
                  var worldClip:Rectangle = clip.intersection(new Rectangle(surface.x,surface.y,size,size));
                  if(worldClip.isEmpty()) continue;
                  var source:Rectangle = worldClip.clone();source.offset(-this.sceneX,-this.sceneY);
                  var point:Point = new Point(worldClip.x-surface.x,worldClip.y-surface.y);
                  for(n=0;n<4;++n) surface.nativeBuffers[n].copyPixels(buffers[n],source,point);
               }
            }
         }
         finally
         {
            for(var field:String in original) this.loc[field]=original[field];
            this.sceneFinishBatch();
         }
      }
