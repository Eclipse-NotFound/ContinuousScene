package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.DisplayObjectContainer;
    import flash.display.Stage;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;
    import flash.utils.getQualifiedClassName;
    import flash.utils.getTimer;

    // Read-only bounds census. No draw, property setters, Tile guesses or animation calls.
    public final class SceneOcclusionCensus {
        private static function box(r:Rectangle):Object {
            return {x:r.x,y:r.y,width:r.width,height:r.height};
        }
        private static function finiteRect(r:Rectangle):Boolean {
            return r && isFinite(r.x) && isFinite(r.y) && isFinite(r.width) && isFinite(r.height);
        }
        private static function finiteMatrix(m:Matrix):Boolean {
            return m && isFinite(m.a) && isFinite(m.b) && isFinite(m.c) && isFinite(m.d) &&
                isFinite(m.tx) && isFinite(m.ty) && m.a*m.d-m.b*m.c!=0;
        }
        private static function colorOK(c:ColorTransform,identity:Boolean):Boolean {
            if(!isFinite(c.redMultiplier)||!isFinite(c.greenMultiplier)||!isFinite(c.blueMultiplier)||
                !isFinite(c.alphaMultiplier)||!isFinite(c.redOffset)||!isFinite(c.greenOffset)||
                !isFinite(c.blueOffset)||!isFinite(c.alphaOffset))return false;
            return !identity || (c.redMultiplier==1 && c.greenMultiplier==1 && c.blueMultiplier==1 &&
                c.alphaMultiplier==1 && c.redOffset==0 && c.greenOffset==0 && c.blueOffset==0 && c.alphaOffset==0);
        }
        private static function geometry(d:DisplayObject):String {
            if(d.filters.length)return "filters";
            if(d.mask || d.scrollRect)return "mask-or-scrollRect";
            if(d.blendMode!="normal")return "blend";
            if(d.transform.matrix3D || !finiteMatrix(d.transform.matrix))return "nonfinite-or-3d-transform";
            if(!colorOK(d.transform.colorTransform,false))return "nonfinite-color";
            return null;
        }
        private static function chain(d:DisplayObject,end:DisplayObject,fog:Boolean):String {
            while(d && d!==end) {
                if(!d.visible)return "already-hidden";
                var c:ColorTransform=d.transform.colorTransform;
                if(c.alphaMultiplier==0 && c.alphaOffset<=0)return "already-hidden";
                var reason:String=geometry(d);if(reason)return reason;
                if(fog && (d.alpha!=1 || !colorOK(c,true)))return "fog-alpha-or-color";
                d=d.parent;
            }
            return d===end?null:"detached-parent-chain";
        }
        private static function subtree(d:DisplayObject,r:Object):String {
            ++r.nodesChecked;var reason:String=geometry(d);if(reason)return reason;
            var c:DisplayObjectContainer=d as DisplayObjectContainer;
            if(c)for(var i:int=0;i<c.numChildren;++i) {
                reason=subtree(c.getChildAt(i),r);if(reason)return reason;
            }
            return null;
        }
        private static function skip(r:Object,reason:String):void {
            r.skipped[reason]=int(r.skipped[reason])+1;
        }
        public static function capture(w:*,segment:int,frame:int):Object {
            var started:int=getTimer();
            var r:Object={version:"occlusion-census-1",segment:segment,frame:frame,startedAtMs:started,
                diagnosticOnly:true,performanceEligible:false,valid:false,rootCountNotUnitCount:true,
                areaIsSummedBoundsNotUnion:true,roots:0,eligible:0,occluded:0,onScreenOccluded:0,
                occludedStageArea:0,onScreenOccludedArea:0,nodesChecked:0,pixelsRead:0,
                skipped:{},covered:[],errors:[],readOnly:true};
            try { inspect(w,r); }
            catch(e:Error){r.errors.push(String(e));r.valid=false;}
            r.elapsedMs=getTimer()-started;return r;
        }
        private static function inspect(w:*,r:Object):void {
            var g:* = w.grafon;var visual:DisplayObjectContainer=g.visual as DisplayObjectContainer;
            var layer:DisplayObjectContainer=g.visObjs[2] as DisplayObjectContainer;
            var light:DisplayObjectContainer=g.visLight as DisplayObjectContainer;
            var data:BitmapData=g.lightBmp as BitmapData;var stage:Stage=visual?visual.stage:null;
            if(!g.sceneLarge || !visual || !layer || !light || !data || !stage) {r.reason="missing-native-scene";return;}
            r.roots=layer.numChildren;
            if(layer.parent!==visual || light.parent!==visual || visual.getChildIndex(light)<=visual.getChildIndex(layer)) {
                r.reason="unexpected-layer-order";return;
            }
            if(light.numChildren!=1) {r.reason="non-unique-light-child";return;}
            var bitmap:Bitmap=light.getChildAt(0) as Bitmap;
            if(!bitmap || bitmap.bitmapData!==data) {r.reason="light-buffer-identity";return;}
            var reason:String=chain(bitmap,stage,true);
            if(reason){r.reason="light-"+reason;return;}
            reason=chain(layer,visual,false);if(reason){r.reason="unit-layer-"+reason;return;}
            var transform:Matrix=bitmap.transform.concatenatedMatrix;
            if(!finiteMatrix(transform) || transform.b!=0 || transform.c!=0 || Math.abs(transform.a)<2 || Math.abs(transform.d)<2) {
                r.reason="light-source-pixel-not-axis-aligned-at-least-two-stage-pixels";return;
            }
            r.light={width:data.width,height:data.height,smoothing:bitmap.smoothing,pixelSnapping:bitmap.pixelSnapping,
                matrix:{a:transform.a,b:transform.b,c:transform.c,d:transform.d,tx:transform.tx,ty:transform.ty},
                expandedSourcePixels:2,blend:light.blendMode};
            var screen:Rectangle=new Rectangle(0,0,stage.stageWidth,stage.stageHeight);
            for(var i:int=0;i<layer.numChildren;++i) {
                var root:DisplayObject=layer.getChildAt(i);
                reason=chain(root,layer,false);if(!reason)reason=subtree(root,r);
                if(reason){skip(r,reason);continue;}
                var bounds:Rectangle=root.getBounds(bitmap);var projected:Rectangle=root.getBounds(stage);
                if(!finiteRect(bounds)||!finiteRect(projected)||bounds.width<=0||bounds.height<=0||projected.width<=0||projected.height<=0) {
                    skip(r,"empty-or-nonfinite-bounds");continue;
                }
                // Two full source pixels cover filtering/snapping only under the >=2 scale gate above.
                var x0:int=int(Math.floor(bounds.left))-2;var y0:int=int(Math.floor(bounds.top))-2;
                var x1:int=int(Math.ceil(bounds.right))+2;var y1:int=int(Math.ceil(bounds.bottom))+2;
                if(bounds.left<2 || bounds.top<2 || bounds.right>data.width-2 || bounds.bottom>data.height-2 ||
                    x0<0 || y0<0 || x1>data.width || y1>data.height) {skip(r,"outside-light-buffer");continue;}
                ++r.eligible;var opaque:Boolean=true;
                for(var y:int=y0;y<y1 && opaque;++y)for(var x:int=x0;x<x1;++x) {
                    ++r.pixelsRead;if(data.getPixel32(x,y)!=uint(0xFF000000)){opaque=false;break;}
                }
                if(!opaque){skip(r,"not-fully-opaque-black");continue;}
                var overlap:Rectangle=projected.intersection(screen);
                ++r.occluded;r.occludedStageArea+=projected.width*projected.height;
                if(!overlap.isEmpty()){++r.onScreenOccluded;r.onScreenOccludedArea+=overlap.width*overlap.height;}
                r.covered.push({index:i,cls:getQualifiedClassName(root),sourceBounds:box(bounds),
                    sampledSourceRect:{x:x0,y:y0,width:x1-x0,height:y1-y0},stageBounds:box(projected),onScreen:box(overlap)});
            }
            r.valid=bitmap.bitmapData===data && light.parent===visual && layer.parent===visual && layer.numChildren==r.roots;
            if(!r.valid)r.reason="binding-or-child-count-changed-during-read";
        }
    }
}
