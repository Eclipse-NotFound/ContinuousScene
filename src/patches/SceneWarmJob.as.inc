      // One unpublished chunk may span frames. Live terrain always keeps its
      // own buffers; only complete output enters the display list and WallBlend.
      public var sceneAsyncWarm:Boolean = true;
      public var sceneWarmSlices:int = 0;
      public var sceneWarmForced:int = 0;
      public var sceneWarmVerify:Boolean = false;
      public var sceneWarmComparisons:Array = [];
      public var sceneWarmBudget:int = 8;
      private var sceneWarmMean:Number = 48;
      private var sceneWarmViewX:Number = NaN;
      private var sceneWarmViewY:Number = NaN;
      private var sceneWarmJob:Object;
      private var sceneWarmBuffers:Array;
      private const sceneWarmFields:Array = ["frontBmp","backBmp","backBmp2","vodaBmp","satsBmp","colorBmp","shadBmp",
         "rectX","rectY","allRect","sceneX","sceneY","sceneScratch","sceneRasterizing","sceneRepaint",
         "sceneRegionPassActive","sceneRasterRegion","sceneMaskCursor","m"];
      private const sceneWarmStyleFields:Array = ["backwall","color","cTransform","darkness","backform","transpFon","tipWater","gas","homeStable"];

      private function sceneCancelWarm(affected:Rectangle = null):void
      {
         var job:Object = this.sceneWarmJob;
         if(job == null) return;
         var support:Rectangle=job.bounds.clone();support.inflate(80,80);
         if(affected != null && !affected.intersects(support))return;
         this.sceneWarmJob = null;
         for each(var data:BitmapData in job.buffers) data.unlock();
         for each(data in job.output) data.dispose();
         job.steps = null;
      }

      private function sceneClearWarm():void
      {
         this.sceneCancelWarm();
         if(this.sceneWarmBuffers)for each(var data:BitmapData in this.sceneWarmBuffers)data.dispose();
         this.sceneWarmBuffers=null;
      }

      private function sceneBeginWarm(cx:int,cy:int):void
      {
         var size:int = this.sceneSide + 2*this.sceneGutter;
         var bounds:Rectangle = new Rectangle(cx*this.sceneSide-this.sceneGutter,cy*this.sceneSide-this.sceneGutter,size,size);
         var original:Object = {};
         for each(var field:String in this.sceneWarmStyleFields) original[field] = this.loc[field];
         var originalKey:String = this.sceneRegionStyleKey(original);
         var groups:Array = [];
         var byKey:Object = {};
         var area:Number = 0;
         var inWorld:Rectangle = bounds.intersection(new Rectangle(0,0,this.loc.limX,this.loc.limY));
         for each(var slice:Object in this.sceneRegionSlices(this.loc,bounds))
         {
            if(slice.style.key == originalKey) continue;
            var group:Object = byKey[slice.style.key];
            if(group == null) {group={style:slice.style,clips:[],area:0};byKey[slice.style.key]=group;groups.push(group);}
            group.clips.push(slice.bounds);group.area+=slice.bounds.width*slice.bounds.height;
            area+=slice.bounds.width*slice.bounds.height;
         }
         if(groups.length == 0) groups.push({style:original,clips:[bounds]});
         else if(groups.length == 1 && area == inWorld.width*inWorld.height) groups[0].clips=[bounds];
         else if(area == inWorld.width*inWorld.height) groups[0].clips=[bounds];
         else groups.unshift({style:original,clips:[bounds]});
         var job:Object = {cx:cx,cy:cy,bounds:bounds,buffers:[],output:[],groups:groups,group:0,steps:null,at:0,work:0,
            cursor:new Dictionary(),matrix:new Matrix(),usedFront:[],usedBack:[]};
         if(this.sceneWarmBuffers==null) {
            this.sceneWarmBuffers=[];
            for(var n:int=0;n<7;++n)this.sceneWarmBuffers.push(new BitmapData(size,size,true,0));
         }
         job.buffers=this.sceneWarmBuffers;
         for(n=0;n<4;++n)job.output.push(new BitmapData(size,size,true,0));
         this.sceneWarmJob=job;
      }

      private function sceneAdvanceWarm(force:Boolean=false):void
      {
         var job:Object=this.sceneWarmJob;
         if(job==null)return;
         var prior:Object={};
         var style:Object={};
         var usedFront:Array=[];
         var usedBack:Array=[];
         var field:String;
         var mat:Material;
         var n:int;
         for each(field in this.sceneWarmFields)prior[field]=this[field];
         for each(field in this.sceneWarmStyleFields)style[field]=this.loc[field];
         for each(mat in this.arrFront){if(mat.used)usedFront.push(mat);mat.used=false;}
         for each(mat in this.arrBack){if(mat.used)usedBack.push(mat);mat.used=false;}
         for each(mat in job.usedFront)mat.used=true;
         for each(mat in job.usedBack)mat.used=true;
         var start:int=getTimer();
         var complete:Boolean=false;
         if(force)++this.sceneWarmForced;
         try
         {
            this.frontBmp=job.buffers[0];this.backBmp=job.buffers[1];this.backBmp2=job.buffers[2];this.vodaBmp=job.buffers[3];
            this.satsBmp=job.buffers[4];this.colorBmp=job.buffers[5];this.shadBmp=job.buffers[6];
            this.rectX=this.rectY=job.bounds.width;this.allRect=new Rectangle(0,0,this.rectX,this.rectY);
            this.sceneScratch=job.buffers;this.sceneX=job.bounds.x;this.sceneY=job.bounds.y;
            this.sceneRasterizing=this.sceneRepaint=this.sceneRegionPassActive=true;
            this.sceneMaskCursor=job.cursor;this.m=job.matrix;
            while(force || getTimer()-start<this.sceneWarmBudget)
            {
               var group:Object=job.groups[job.group];
               for each(field in this.sceneWarmStyleFields)this.loc[field]=group.style[field];
               this.sceneRasterRegion=group.style.nativeRegion?group.style:null;
               if(job.steps==null) {this.sceneMaskCursor=new Dictionary();job.steps=this.sceneDrawSteps(this.loc);job.at=0;++this.sceneRegionPasses;}
               if(job.at<job.steps.length) {if(job.steps[job.at].call(null)!==false)++job.at;}
               else
               {
                  for each(var clip:Rectangle in group.clips)
                  {
                     var local:Rectangle=clip.clone();local.offset(-this.sceneX,-this.sceneY);
                     for(n=0;n<4;++n)job.output[n].copyPixels(job.buffers[n],local,local.topLeft);
                  }
                  job.steps=null;
                  if(++job.group==job.groups.length){complete=true;break;}
               }
            }
            job.cursor=this.sceneMaskCursor;job.matrix=this.m;
            job.usedFront=[];job.usedBack=[];
            for each(mat in this.arrFront)if(mat.used)job.usedFront.push(mat);
            for each(mat in this.arrBack)if(mat.used)job.usedBack.push(mat);
         }
         catch(error:*) {this.sceneCancelWarm();throw error;}
         finally
         {
            for each(field in this.sceneWarmFields)this[field]=prior[field];
            for each(field in this.sceneWarmStyleFields)this.loc[field]=style[field];
            for each(mat in this.arrFront)mat.used=false;
            for each(mat in this.arrBack)mat.used=false;
            for each(mat in usedFront)mat.used=true;
            for each(mat in usedBack)mat.used=true;
            World.w.gr_stage=0;
         }
         var elapsed:int=getTimer()-start;job.work+=elapsed;++this.sceneWarmSlices;
         this.sceneWarmMaxMs=Math.max(this.sceneWarmMaxMs,elapsed);
         if(!complete)return;
         if(this.sceneWarmVerify)
         {
            this.sceneRender(job.cx,job.cy);
            var reference:Object=this.sceneChunks[job.cx+":"+job.cy];
            var comparison:Object={cx:job.cx,cy:job.cy,equal:true,changed:0,max:0,layers:[],groups:[]};
            for each(var debugGroup:Object in job.groups)comparison.groups.push({key:this.sceneRegionStyleKey(debugGroup.style),clips:String(debugGroup.clips)});
            for(n=0;n<4;++n)
            {
               var layerStats:Object={layer:n,changed:0,max:0,examples:[]};
               var actual:Vector.<uint> = job.output[n].getVector(job.output[n].rect);
               var expected:Vector.<uint> = reference.nativeBuffers[n].getVector(reference.nativeBuffers[n].rect);
               for(var p:int=0;p<actual.length;++p)if(actual[p]!=expected[p])
               {
                  comparison.equal=false;++comparison.changed;
                  ++layerStats.changed;
                  if(layerStats.examples.length<3)layerStats.examples.push({x:p%job.bounds.width,y:int(p/job.bounds.width),actual:actual[p].toString(16),expected:expected[p].toString(16)});
                  for(var shift:int=0;shift<=24;shift+=8)layerStats.max=Math.max(layerStats.max,Math.abs(int((actual[p]>>>shift)&255)-int((expected[p]>>>shift)&255)));
               }
               comparison.max=Math.max(comparison.max,layerStats.max);comparison.layers.push(layerStats);
            }
            this.sceneWarmComparisons.push(comparison);
            this.sceneDrop(reference);delete this.sceneChunks[job.cx+":"+job.cy];
         }
         var parents:Array=[this.visFront,this.visBack,this.visBack2,this.visVoda];
         var bitmaps:Array=[];
         for(n=0;n<4;++n)
         {
            var bitmap:Bitmap=new Bitmap(job.output[n]);
            bitmap.scrollRect=new Rectangle(this.sceneGutter,this.sceneGutter,this.sceneSide,this.sceneSide);
            bitmap.x=job.cx*this.sceneSide;bitmap.y=job.cy*this.sceneSide;
            parents[n].addChild(bitmap);bitmaps.push(bitmap);
         }
         this.sceneChunks[job.cx+":"+job.cy]={cx:job.cx,cy:job.cy,bitmaps:bitmaps,sats:null,nativeBuffers:job.output,revision:0,
            backobjs:this.sceneBackdropObjects(job.bounds.x,job.bounds.y,job.bounds.width,job.bounds.height),
            x:job.bounds.x,y:job.bounds.y,side:this.sceneSide,gutter:this.sceneGutter};
         ++this.sceneResident;++this.sceneWarmCount;
         this.sceneDrawMs=job.work;this.sceneMaxDrawMs=Math.max(this.sceneMaxDrawMs,job.work);
         this.sceneWarmMean=this.sceneWarmMean*0.8+Math.min(200,job.work)*0.2;
         this.sceneWarmJob=null;this.sceneNextWarm=getTimer();
      }
