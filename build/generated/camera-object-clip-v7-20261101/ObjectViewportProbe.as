package {
    import flash.display.DisplayObjectContainer;
    import flash.display.Shape;
    import flash.geom.Rectangle;

    /** Diagnostic only: preserve native children, visibility, order and game logic. */
    public class ObjectViewportProbe {
        private var owner:*, entries:Array=[], active:String="full", key:String="";
        public function ObjectViewportProbe(g:*):void {
            owner=g;
            for each(var layer:* in g.visObjs) {
                if(layer.x!=0 || layer.y!=0 || layer.scrollRect!=null || layer.mask!=null)
                    throw new Error("Unexpected object-layer transform or clipping");
                var shape:Shape=new Shape();
                entries.push({layer:layer,mask:shape});
            }
        }
        public function apply(mode:String,camera:*):void {
            if(mode!=active){restore();active=mode;}
            if(mode=="full")return;
            var scale:Number=camera.scaleV;
            var left:Number=Math.floor((-camera.vx-camera.quakeX)/scale/128)*128-256;
            var top:Number=Math.floor((-camera.vy-camera.quakeY)/scale/128)*128-256;
            var width:Number=Math.ceil(camera.screenX/scale/128)*128+640;
            var height:Number=Math.ceil(camera.screenY/scale/128)*128+640;
            var next:String=left+":"+top+":"+width+":"+height;
            if(next==key)return;
            key=next;
            for each(var item:Object in entries) {
                var layer:*=item.layer;
                if(mode=="objectClip") {
                    layer.scrollRect=new Rectangle(left,top,width,height);
                    layer.x=left;layer.y=top;
                }else if(mode=="objectMask") {
                    var mask:Shape=item.mask;
                    if(mask.parent==null)owner.visual.addChild(mask);
                    mask.graphics.clear();mask.graphics.beginFill(0xffffff);
                    mask.graphics.drawRect(left,top,width,height);mask.graphics.endFill();
                    layer.mask=mask;
                }else throw new Error("Unknown viewport mode "+mode);
            }
        }
        public function restore():void {
            for each(var item:Object in entries) {
                item.layer.scrollRect=null;item.layer.x=0;item.layer.y=0;item.layer.mask=null;
                if(item.mask.parent)item.mask.parent.removeChild(item.mask);
            }
            active="full";key="";
        }
    }
}
