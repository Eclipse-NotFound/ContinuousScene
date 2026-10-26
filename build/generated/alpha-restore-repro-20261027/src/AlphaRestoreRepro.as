package {
    import flash.desktop.NativeApplication;
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.PNGEncoderOptions;
    import flash.display.Shape;
    import flash.display.Sprite;
    import flash.display.StageAlign;
    import flash.display.StageScaleMode;
    import flash.events.Event;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.filters.BlurFilter;
    import flash.filters.GlowFilter;
    import flash.geom.ColorTransform;
    import flash.geom.Matrix;
    import flash.text.TextField;
    import flash.text.TextFormat;
    import flash.system.Capabilities;
    import flash.utils.getTimer;

    [SWF(width="512",height="512",frameRate="60",backgroundColor="#26343E")]
    public final class AlphaRestoreRepro extends Sprite {
        private var result:Object={version:"alpha-restore-repro-1",completed:false,passed:false,
            diagnosticOnly:true,deployed:false,errors:[],cases:[],allocations:0,disposals:0};
        private var names:Array=["vector","cached-vector","blurred-vector","glowing-vector",
            "bitmap-auto","bitmap-always","bitmap-never","bitmap-smooth",
            "text","cached-text","nested-cached","rotated-cached",
            "filtered-parent","color-parent","mixed-particles","cached-group"];
        private var group:Sprite;
        private var allocations:Array=[];
        private var index:int=0;
        private var age:int=0;
        private var began:int;
        private var done:Boolean=false;
        public function AlphaRestoreRepro() {
            if(stage)start();else addEventListener(Event.ADDED_TO_STAGE,added);
        }
        private function added(e:Event):void {removeEventListener(Event.ADDED_TO_STAGE,added);start();}
        private function start():void {
            began=getTimer();
            try {
                var s:FileStream=new FileStream();s.open(File.applicationDirectory.resolvePath("fixture.json"),FileMode.READ);
                var fixture:Object=JSON.parse(s.readUTFBytes(s.bytesAvailable));s.close();
                result.appId=fixture.appId;result.nonce=fixture.nonce;
                var descriptor:XML=NativeApplication.nativeApplication.applicationDescriptor,ns:Namespace=descriptor.namespace();
                result.actualAppId=String(descriptor.ns::id);
                require(result.appId==result.actualAppId,"Identity mismatch");
                stage.align=StageAlign.TOP_LEFT;stage.scaleMode=StageScaleMode.NO_SCALE;
                stage.quality="high";result.runtime=Capabilities.version;
                require(stage.stageWidth==512 && stage.stageHeight==512,"Viewport mismatch");
                graphics.beginFill(0x26343E);graphics.drawRect(0,0,512,512);graphics.endFill();
                makeCase();addEventListener(Event.ENTER_FRAME,tick);
            }catch(error:Error){result.errors.push(error.toString());finish();}
        }
        private function own(w:int,h:int,transparent:Boolean=true,color:uint=0):BitmapData {
            var b:BitmapData=new BitmapData(w,h,transparent,color);allocations.push(b);++result.allocations;return b;
        }
        private function disposeAll():void {while(allocations.length){BitmapData(allocations.pop()).dispose();++result.disposals;}}
        private function star():Shape {
            var s:Shape=new Shape();s.graphics.lineStyle(1.3,0x19E644,.7);
            s.graphics.beginFill(0xBA9326,.8);s.graphics.moveTo(0,-33.1);
            for(var i:int=1;i<15;++i){var a:Number=i*Math.PI/7-Math.PI/2,r:Number=i%2?13.4:33.1;s.graphics.lineTo(Math.cos(a)*r,Math.sin(a)*r);}
            s.graphics.endFill();return s;
        }
        private function makeCase():void {
            group=new Sprite();group.x=-4700;group.y=-3900;addChild(group);
            var content:Sprite=new Sprite();content.x=4956.45;content.y=4156.1;group.addChild(content);
            var n:String=names[index],child:DisplayObject;
            if(n.indexOf("bitmap")==0 || n=="mixed-particles") {
                var data:BitmapData=own(5,5,true,0);
                for(var y:int=0;y<5;++y)for(var x:int=0;x<5;++x)data.setPixel32(x,y,uint(((x+y+1)*25)<<24)|0xE23941);
                var count:int=n=="mixed-particles"?120:1;
                for(var k:int=0;k<count;++k){
                    var bitmap:Bitmap=new Bitmap(data,n=="bitmap-always"?"always":n=="bitmap-never"?"never":"auto",n=="bitmap-smooth");
                    bitmap.x=k%12*7.35;bitmap.y=int(k/12)*7.85;
                    if(count==1){bitmap.scaleX=9.37;bitmap.scaleY=8.23;bitmap.rotation=13.2;}
                    content.addChild(bitmap);
                }
            }else if(n.indexOf("text")>=0){
                var tf:TextField=new TextField();tf.defaultTextFormat=new TextFormat("Arial",23,0xEDC530,true);
                tf.text="327\nMoving camera";tf.width=210;tf.height=90;tf.x=-100.2;tf.y=-30.15;content.addChild(tf);
                if(n=="cached-text")content.cacheAsBitmap=true;
            }else{
                child=star();content.addChild(child);
                if(n=="cached-vector")child.cacheAsBitmap=true;
                if(n=="blurred-vector")child.filters=[new BlurFilter(0,6,1)];
                if(n=="glowing-vector")child.filters=[new GlowFilter(0x22FF44,1,6,6,1,3)];
                if(n=="nested-cached" || n=="rotated-cached"){
                    content.scaleX=.675;content.scaleY=.837;child.x=11.5;child.y=-14.05;child.scaleY=.43023681640625;
                    child.cacheAsBitmap=true;if(n=="rotated-cached")content.rotation=35.2;
                }
                if(n=="filtered-parent")group.filters=[new GlowFilter(0x22FF44,1,6,6,1,3)];
                if(n=="color-parent")group.transform.colorTransform=new ColorTransform(.83,.65,.92,1,10,20,5,0);
                if(n=="cached-group")group.cacheAsBitmap=true;
            }
            age=0;
        }
        private function capture():BitmapData {var b:BitmapData=own(512,512);b.draw(stage);return b;}
        private function compare(a:BitmapData,b:BitmapData):Object {
            var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect),changed:int=0,rgb:int=0,alpha:int=0;
            for(var i:int=0;i<av.length;++i)if(av[i]!=bv[i]){
                ++changed;var x:uint=av[i],y:uint=bv[i];alpha=Math.max(alpha,Math.abs(int(x>>>24)-int(y>>>24)));
                rgb=Math.max(rgb,Math.abs(int(x>>>16&255)-int(y>>>16&255)),Math.abs(int(x>>>8&255)-int(y>>>8&255)),Math.abs(int(x&255)-int(y&255)));
            }
            return {equal:changed==0,differentPixels:changed,maxRGB:rgb,maxAlpha:alpha};
        }
        private function savePixel(name:String,b:BitmapData):void {
            var f:File=File.applicationStorageDirectory.resolvePath("pixels");f.createDirectory();
            var s:FileStream=new FileStream();try{s.open(f.resolvePath(name+".png"),FileMode.WRITE);s.writeBytes(b.encode(b.rect,new PNGEncoderOptions()));}finally{s.close();}
        }
        private function matrix(d:DisplayObject):Object {var m:Matrix=d.transform.concatenatedMatrix;return {a:m.a,b:m.b,c:m.c,d:m.d,tx:m.tx,ty:m.ty};}
        private function tick(e:Event):void {
            if(done)return;
            try{
                require(getTimer()-began<20000,"Fixture timeout");
                if(++age<4)return;
                var row:Object={name:names[index],initialAlpha:group.alpha,matrixBefore:matrix(group)};
                var original:BitmapData=capture(),repeat:BitmapData=capture();row.nativeRepeat=compare(original,repeat);
                require(row.nativeRepeat.equal,"Unchanged native captures differ");
                group.alpha=0;var hidden:BitmapData=capture();group.alpha=row.initialAlpha;
                var restored:BitmapData=capture(),restored2:BitmapData=capture();
                row.hidden=compare(original,hidden);row.restored=compare(original,restored);row.restoredRepeat=compare(restored,restored2);
                row.originalVsSecondRestore=compare(original,restored2);row.finalAlpha=group.alpha;row.matrixAfter=matrix(group);
                if(!row.restored.equal){savePixel(row.name+"-original",original);savePixel(row.name+"-restored",restored);}
                result.cases.push(row);require(row.hidden.differentPixels>0,"Case did not suppress visible content");
                removeChild(group);group=null;disposeAll();
                if(++index==names.length){result.completed=true;finish();}else makeCase();
            }catch(error:Error){result.errors.push(error.toString());finish();}
        }
        private function require(condition:Boolean,message:String):void {if(!condition)throw new Error(message);}
        private function finish():void {
            if(done)return;done=true;removeEventListener(Event.ENTER_FRAME,tick);
            if(group){removeChild(group);group=null;}disposeAll();
            result.elapsedMs=getTimer()-began;
            result.passed=result.completed && result.errors.length==0 && result.allocations==result.disposals;
            result.limits=["Synthetic renderer diagnosis only; not game pixels, game performance or a candidate acceptance.",
                "A completed diagnostic may reproduce unequal restored pixels; this does not approve that change for gameplay."];
            var s:FileStream=new FileStream();s.open(File.applicationStorageDirectory.resolvePath("result.json"),FileMode.WRITE);
            s.writeUTFBytes(JSON.stringify(result));s.close();NativeApplication.nativeApplication.exit(result.passed?0:1);
        }
    }
}
