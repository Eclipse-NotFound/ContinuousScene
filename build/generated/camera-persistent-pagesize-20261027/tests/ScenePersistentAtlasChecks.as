package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObjectContainer;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.display.Stage;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.getTimer;
    import ScenePersistentAtlas;

    /** Real Flash display/events/pixels, synthetic terrain; no game world writes. */
    public final class ScenePersistentAtlasChecks {
        public static function run(stage:Stage):Object {
            var start:int=getTimer(),out:Object={complete:false,passed:false,errors:[],cases:[],pixelCreated:0,pixelDisposed:0,sourceCreated:0,sourceDisposed:0,surfaceReads:0};
            var renderer:ScenePersistentAtlas=new ScenePersistentAtlas();
            var holder:Sprite=new Sprite(),visual:Sprite=new Sprite(),reference:Sprite=new Sprite();
            holder.name="ContinuousSceneOwnedAtlasContractFixture";holder.visible=false;holder.addChild(visual);
            var ctx:Object={out:out,renderer:renderer,holder:holder,visual:visual,reference:reference,
                parents:[],refs:[],surfaces:[],data:[],bitmaps:[],view:new Rectangle(20,20,960,640),cullKey:"",pictures:[]};
            try {
                stage.addChild(holder);
                var g:Object={sceneLarge:true,sceneChunkSide:320,sceneResident:0,sceneRedraws:0,sceneEvictions:0,visSats:new Sprite()};
                g.visSats.visible=false;
                for(var layer:int=0;layer<4;++layer){ctx.parents.push(new Sprite());ctx.refs.push(new Sprite());}
                // Actual original order: background1, background2, foreground, water.
                for each(layer in [1,2,0,3]){visual.addChild(ctx.parents[layer]);reference.addChild(ctx.refs[layer]);}
                ctx.parents[3].alpha=ctx.refs[3].alpha=.6;
                g.visFront=ctx.parents[0];g.visBack=ctx.parents[1];g.visBack2=ctx.parents[2];g.visVoda=ctx.parents[3];
                g.sceneSurfaces=function():Array {++out.surfaceReads;return ctx.surfaces.concat();};
                g.sceneViewport=function():Rectangle {return ctx.view.clone();};
                ctx.g=g;ctx.w={loc:{id:"owned-atlas-fixture"},grafon:g,visual:visual,sats:{active:false},cam:{vx:-20,vy:-20,scaleV:1,quakeX:0,quakeY:0}};
                for(var cy:int=0;cy<4;++cy)for(var cx:int=0;cx<12;++cx)ctx.surfaces.push(makeSurface(ctx,cx,cy,0));
                g.sceneResident=ctx.surfaces.length;g.sceneRedraws=ctx.surfaces.length;
                setView(ctx,20,20);renderer.preallocate(ctx.w);
                checkpoint(ctx,"first");
                var steady:Object=renderer.snapshot(),reads:int=out.surfaceReads;
                checkpoint(ctx,"steady-repeat");
                var next:Object=renderer.snapshot();
                require(next.bindingRefreshes==steady.bindingRefreshes && out.surfaceReads==reads,"Steady scene rebuilt membership");
                require(next.visibilityWrites==steady.visibilityWrites && next.restoreWrites==steady.restoreWrites && next.copies==steady.copies,"Steady presentation toggled/copied native content");
                setView(ctx,21,21);checkpoint(ctx,"within-cell-camera");
                next=renderer.snapshot();require(next.visibilityRefreshes==steady.visibilityRefreshes,"Subcell movement rebuilt culling");
                setView(ctx,350,50);checkpoint(ctx,"cross-cell-camera");
                require(renderer.snapshot().visibilityRefreshes>next.visibilityRefreshes,"Cell boundary did not refresh culling");
                setView(ctx,2570,50);checkpoint(ctx,"cross-page-camera");
                setView(ctx,20,20);checkpoint(ctx,"return-to-first");

                var changed:Object=ctx.surfaces[1];
                var before:BitmapData=capture(ctx,reference),refreshBefore:int=renderer.snapshot().bindingRefreshes;
                changed.nativeBuffers[1].fillRect(new Rectangle(80,80,40,40),0xFFFF0011);++changed.revision;
                var after:BitmapData=capture(ctx,reference),different:Object=compare(before,after);
                require(different.differentPixels>0,"Revision fixture changed no reference pixels");disposePictures(ctx);
                checkpoint(ctx,"native-pixel-revision");
                require(renderer.snapshot().bindingRefreshes==refreshBefore,"Pixel revision rebuilt membership unnecessarily");

                // Replace one cell without changing counts or redraw counters.
                // Only actual Flash ADDED/REMOVED events invalidate membership.
                var index:int=2,old:Object=ctx.surfaces[index];refreshBefore=renderer.snapshot().bindingRefreshes;
                for(layer=0;layer<4;++layer){ctx.parents[layer].removeChild(old.bitmaps[layer]);ctx.refs[layer].removeChild(old.refs[layer]);}
                ctx.surfaces[index]=makeSurface(ctx,old.cx,old.cy,1);ctx.cullKey="";setView(ctx,20,20);
                checkpoint(ctx,"same-count-native-replacement");
                require(renderer.snapshot().bindingRefreshes>refreshBefore,"Same-count replacement missed display events");

                var extra:Shape=new Shape(),extraRef:Shape=new Shape();
                for each(var shape:Shape in [extra,extraRef]){shape.graphics.beginFill(0x00FF99);shape.graphics.drawRect(350,100,60,60);shape.graphics.endFill();shape.visible=false;}
                ctx.parents[2].addChild(extra);ctx.refs[2].addChild(extraRef);
                checkpoint(ctx,"invisible-foreign-child");
                extra.visible=extraRef.visible=true;
                renderer.update(ctx.w,true,true);
                require(!renderer.snapshot().presented && renderer.snapshot().fallbackReason=="background-order-or-effects","Foreign child activation did not restore native presentation");
                compareCurrent(ctx,"foreign-visibility-fallback",false);
                ctx.parents[2].removeChild(extra);ctx.refs[2].removeChild(extraRef);
                checkpoint(ctx,"foreign-child-removed");

                ctx.w.sats.active=true;renderer.update(ctx.w,true,true);
                require(!renderer.snapshot().presented && renderer.snapshot().fallbackReason=="sats","SATS did not fall back");
                compareCurrent(ctx,"sats-fallback",false);ctx.w.sats.active=false;
                checkpoint(ctx,"sats-return");

                renderer.useNativeForTest();compareCurrent(ctx,"explicit-native-restore",false);
                checkpoint(ctx,"native-to-atlas-return");
                renderer.clear();out.afterClear=renderer.snapshot();
                require(out.afterClear.ownedBitmaps==0 && out.afterClear.pendingHidden==0 && out.afterClear.attached==0,"Fixture atlas did not release");
                compareCurrent(ctx,"final-native-restore",false);
                var epoch:int=renderer.snapshot().treeEpoch,probe:Shape=new Shape();
                ctx.parents[1].addChild(probe);ctx.parents[1].removeChild(probe);
                require(renderer.snapshot().treeEpoch==epoch,"Display listeners remain after clear");
                out.complete=true;out.passed=true;
            } catch(error:Error){out.errors.push(error.message);}
            finally {
                try {renderer.clear();out.cleanup=renderer.snapshot();}catch(e:Error){out.errors.push("atlas cleanup: "+e.message);}
                disposePictures(ctx);
                if(holder.parent)holder.parent.removeChild(holder);
                for each(var bitmap:Bitmap in ctx.bitmaps)bitmap.bitmapData=null;
                for each(var data:BitmapData in ctx.data)try {data.dispose();++out.sourceDisposed;}catch(disposeError:Error){out.errors.push(disposeError.message);}
                out.holderDetached=holder.parent==null;out.elapsedMs=getTimer()-start;
                if(out.errors.length || out.pixelCreated!=out.pixelDisposed || out.sourceCreated!=out.sourceDisposed || !out.holderDetached){out.passed=false;out.complete=false;}
            }
            return out;
        }
        private static function makeSurface(ctx:Object,cx:int,cy:int,variant:int):Object {
            var s:Object={cx:cx,cy:cy,x:cx*320-40,y:cy*320-40,side:320,gutter:40,revision:0,bitmaps:[],nativeBuffers:[],refs:[]};
            for(var layer:int=0;layer<4;++layer) {
                var color:uint=layer==1?(variant?0xFF775522:0xFF335577):layer==2?0x40AA8866:0;
                var data:BitmapData=new BitmapData(400,400,true,color);ctx.data.push(data);++ctx.out.sourceCreated;
                if(layer==2)data.fillRect(new Rectangle(90,90,70,50),0x90337722);
                if(layer==0)data.fillRect(new Rectangle(180,180,30,40),0xBBAA0033);
                if(layer==3)data.fillRect(new Rectangle(220,220,50,25),0x803399EE);
                var b:Bitmap=new Bitmap(data),r:Bitmap=new Bitmap(data);
                for each(var bitmap:Bitmap in [b,r]){bitmap.x=cx*320;bitmap.y=cy*320;bitmap.scrollRect=new Rectangle(40,40,320,320);ctx.bitmaps.push(bitmap);}
                ctx.parents[layer].addChild(b);ctx.refs[layer].addChild(r);
                s.bitmaps.push(b);s.refs.push(r);s.nativeBuffers.push(data);
            }
            return s;
        }
        private static function setView(ctx:Object,x:int,y:int):void {
            ctx.view=new Rectangle(x,y,960,640);ctx.w.cam.vx=-x;ctx.w.cam.vy=-y;ctx.visual.x=-x;ctx.visual.y=-y;
            var v:Rectangle=ctx.view,key:String=Math.floor(v.left/320)+":"+Math.floor(v.top/320)+":"+Math.ceil(v.right/320)+":"+Math.ceil(v.bottom/320)+":"+ctx.g.sceneResident;
            if(key==ctx.cullKey)return;ctx.cullKey=key;
            for each(var s:Object in ctx.surfaces)for each(var b:Bitmap in s.bitmaps)b.visible=v.intersects(new Rectangle(s.cx*320,s.cy*320,320,320));
        }
        private static function checkpoint(ctx:Object,name:String):void {
            ctx.renderer.update(ctx.w,true,true);require(ctx.renderer.snapshot().presented,"Fixture unexpectedly fell back: "+name);
            compareCurrent(ctx,name,true);
        }
        private static function compareCurrent(ctx:Object,name:String,presented:Boolean):void {
            try {
                var expected:BitmapData=capture(ctx,ctx.reference),actual:BitmapData=capture(ctx,ctx.visual);
                var comparison:Object=compare(expected,actual);
                ctx.out.cases.push({name:name,presented:presented,pixels:comparison,state:ctx.renderer.snapshot()});
                require(comparison.maxRGB<=2 && comparison.maxAlpha==0,"Fixture pixels differ: "+name);
                if(!presented)require(comparison.differentPixels==0,"Native restoration is not exact: "+name);
            } finally {disposePictures(ctx);}
        }
        private static function capture(ctx:Object,display:DisplayObjectContainer):BitmapData {
            var data:BitmapData=new BitmapData(960,640,true,0);ctx.pictures.push(data);++ctx.out.pixelCreated;
            data.draw(display,new Matrix(1,0,0,1,-ctx.view.x,-ctx.view.y));return data;
        }
        private static function compare(a:BitmapData,b:BitmapData):Object {
            var x:Vector.<uint>=a.getVector(a.rect),y:Vector.<uint>=b.getVector(b.rect),n:int=0,alpha:int=0,rgb:int=0;
            for(var i:int=0;i<x.length;++i)if(x[i]!=y[i]){++n;alpha=Math.max(alpha,Math.abs(int(x[i]>>>24)-int(y[i]>>>24)));rgb=Math.max(rgb,Math.abs(int(x[i]>>>16&255)-int(y[i]>>>16&255)),Math.abs(int(x[i]>>>8&255)-int(y[i]>>>8&255)),Math.abs(int(x[i]&255)-int(y[i]&255)));}
            return {differentPixels:n,maxAlpha:alpha,maxRGB:rgb,pixels:x.length};
        }
        private static function disposePictures(ctx:Object):void {
            while(ctx.pictures.length){var data:BitmapData=ctx.pictures.pop();data.dispose();++ctx.out.pixelDisposed;}
        }
        private static function require(ok:Boolean,message:String):void {if(!ok)throw new Error(message);}
    }
}
