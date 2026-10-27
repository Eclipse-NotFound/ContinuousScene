        private function poseKey(state:Object,rect:Rectangle,frames:String):String {
            var m:Matrix=state.matrix,c:ColorTransform=state.color;
            // Integer root translation is excluded, but fractional raster phase and
            // cached coverage relative to that translation remain part of the key.
            var ix:Number=Math.floor(m.tx),iy:Number=Math.floor(m.ty);
            return [m.a,m.b,m.c,m.d,m.tx-ix,m.ty-iy,
                c.redMultiplier,c.greenMultiplier,c.blueMultiplier,c.alphaMultiplier,
                c.redOffset,c.greenOffset,c.blueOffset,c.alphaOffset,state.alpha,state.blend,
                rect.x-ix,rect.y-iy,rect.width,rect.height,frames].join("|");
        }
        private function findPose(owner:DisplayObject,key:String):Object {
            for each(var pose:Object in posePool)if(pose.owner===owner && pose.key===key){pose.age=++poseClock;return pose;}
            return null;
        }
        private function savePose(owner:DisplayObject,key:String,pixels:BitmapData):void {
            var bytes:Number=Number(pixels.width)*pixels.height*4;
            if(bytes>2*1024*1024){++poseSkipped;return;}
            while(posePool.length && (poseBytes+bytes>24*1024*1024 || liveCPUBytes+bytes>128*1024*1024 || posePool.length>=512)) {
                var oldest:int=0;
                for(var i:int=1;i<posePool.length;++i)if(posePool[i].age<posePool[oldest].age)oldest=i;
                var evicted:Object=posePool.splice(oldest,1)[0];
                poseBytes-=Number(evicted.pixels.width)*evicted.pixels.height*4;disposePixels(evicted.pixels);++poseEvictions;
            }
            if(liveCPUBytes+bytes>128*1024*1024){++poseSkipped;return;}
            var data:BitmapData=newPixels(pixels.width,pixels.height);
            data.copyPixels(pixels,pixels.rect,new Point());++copies;
            posePool.push({owner:owner,key:key,pixels:data,age:++poseClock});
            poseBytes+=bytes;posePeak=Math.max(posePeak,poseBytes);
        }
