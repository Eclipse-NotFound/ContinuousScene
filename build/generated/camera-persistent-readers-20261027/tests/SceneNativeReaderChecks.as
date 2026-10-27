package tests {
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.geom.Matrix;
    import flash.geom.Point;
    import flash.geom.Rectangle;
    import SceneLegacyRVWallSurface;
    import SceneNativeRVWallSurface;
    public final class SceneNativeReaderChecks {
        public static function run(ctx:Object):Object {
            var out:Object={passed:false,errors:[],created:0,disposed:0,steps:[]},images:Array=[];
            var old:SceneLegacyRVWallSurface=new SceneLegacyRVWallSurface();
            var next:SceneNativeRVWallSurface=new SceneNativeRVWallSurface();
            next.nativeTerrainSources=ctx.renderer.nativeTerrainSources;
            try {
                var front:DisplayObjectContainer=ctx.parents[0],ref:DisplayObjectContainer=ctx.refs[0];
                check(out,images,ctx,ref,front,old,next,"before-change",false);
                var changed:Object=ctx.surfaces[1];
                changed.nativeBuffers[0].fillRect(new Rectangle(100,100,40,40),0xFF55CC22);++changed.revision;
                // Deliberately read before the presenter observes the native revision.
                // RV runs before the CS presentation callback in the proposed integration.
                var before:Object=ctx.renderer.snapshot();
                check(out,images,ctx,ref,front,old,next,"native-revision-before-presentation",true);
                var after:Object=ctx.renderer.snapshot();
                require(before.copies==after.copies && before.visibilityWrites==after.visibilityWrites && before.restoreWrites==after.restoreWrites,"Reader mutated rendering state");
                ctx.renderer.update(ctx.w,true,true);
                check(out,images,ctx,ref,front,old,next,"after-presentation-refresh",false);
                ctx.renderer.useNativeForTest();
                require(ctx.renderer.nativeTerrainSources(front)==null,"Native display did not use original reader fallback");
                check(out,images,ctx,ref,front,old,next,"native-fallback",false);
                ctx.renderer.update(ctx.w,true,true);
                out.passed=true;
            } catch(error:Error){out.errors.push(error.message);}
            finally {
                next.nativeTerrainSources=null;old.reset();next.reset();
                for each(var data:BitmapData in images){data.dispose();++out.disposed;}
                if(out.created!=out.disposed || out.errors.length)out.passed=false;
            }
            return out;
        }
        private static function check(out:Object,images:Array,ctx:Object,ref:DisplayObjectContainer,front:DisplayObjectContainer,old:SceneLegacyRVWallSurface,next:SceneNativeRVWallSurface,name:String,expectStale:Boolean):void {
            var expected:BitmapData=make(out,images,ctx.view);expected.draw(ref,new Matrix(1,0,0,1,-ctx.view.x,-ctx.view.y));
            var legacy:BitmapData=readSources(old.diagnosticSources(front),ctx.view,out,images);
            var candidate:BitmapData=readSources(next.diagnosticSources(front),ctx.view,out,images);
            var a:Object=compare(expected,legacy),b:Object=compare(expected,candidate);
            out.steps.push({name:name,legacy:a,candidate:b,expectedStale:expectStale});
            require(b.differentPixels==0,"Native reader pixels mismatch: "+name);
            require(expectStale?a.differentPixels>0:a.differentPixels==0,"Legacy positive/negative control mismatch: "+name);
        }
        private static function make(out:Object,images:Array,view:Rectangle):BitmapData {
            var d:BitmapData=new BitmapData(view.width,view.height,true,0);images.push(d);++out.created;return d;
        }
        private static function readSources(sources:Array,view:Rectangle,out:Object,images:Array):BitmapData {
            require(sources!=null,"Unexpected source fallback");var d:BitmapData=make(out,images,view);
            for each(var s:Object in sources){
                var r:Rectangle=view.intersection(s.rect);if(r.isEmpty())continue;
                var p:Point=new Point(r.x-view.x,r.y-view.y);r.offset(-s.x,-s.y);d.copyPixels(s.data,r,p,null,null,true);
            }return d;
        }
        private static function compare(a:BitmapData,b:BitmapData):Object {
            var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect),n:int=0;
            for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i])++n;
            return {differentPixels:n,pixels:av.length};
        }
        private static function require(ok:Boolean,msg:String):void {if(!ok)throw new Error(msg);}
    }
}
