package tests {
    import flash.display.Bitmap;
    import flash.display.BitmapData;
    import flash.display.DisplayObject;
    import flash.display.PNGEncoderOptions;
    import flash.display.Sprite;
    import flash.filesystem.File;
    import flash.filesystem.FileMode;
    import flash.filesystem.FileStream;
    import flash.geom.Matrix;
    import flash.geom.Rectangle;

    /** Pixel diagnosis only. Caller restores native alpha first. No scene/display/config writes. */
    public class SceneCellSamplingChecks {
        public static function run(main:*,w:*,check:Function):Object {
            var out:Object={version:"cell-sampling-1",diagnosticOnly:true,performanceEligible:false,
                cases:[],error:"",allocations:0,disposals:0,borrowedBufferDisposals:0,sceneWrites:0,
                scales:[1,43690/65536,0.5],offsets:[[0,0],[17,-11]],
                scope:"Detached one-buffer renders; no Stage presentation or performance claim. Fixed16 scale is the observed v3 two-thirds value, not a newly measured renderer matrix."};
            var selected:Object=null,originalPixels:Vector.<uint>=null,oldStamp:String="";
            var loc:*,g:*,cam:*,visual:*,worldMatrix:String="",revision:*,parent:*,depth:int=-1;
            try {
                must(w && w.loc && w.grafon && w.cam && w.visual,"World unavailable");
                loc=w.loc;g=w.grafon;cam=w.cam;visual=w.visual;worldMatrix=visual.transform.matrix.toString();
                out.stageQuality=main && main.stage?main.stage.quality:null;
                out.worldScale=Number(cam.scaleV);out.worldMatrix=worldMatrix;
                selected=choose(g.sceneSurfaces(),out);
                must(selected!=null,"No visible nonempty native cell with restored alpha and supported plain geometry");
                var b:Bitmap=selected.bitmap;var data:BitmapData=selected.data;
                oldStamp=stamp(b);parent=b.parent;depth=parent.getChildIndex(b);revision=selected.surface.revision;
                originalPixels=data.getVector(data.rect);
                out.source={cx:selected.surface.cx,cy:selected.surface.cy,layer:selected.layer,
                    side:selected.surface.side,gutter:selected.surface.gutter,width:data.width,height:data.height,
                    pixelSnapping:b.pixelSnapping,smoothing:b.smoothing,scrollRect:b.scrollRect.toString(),
                    matrix:b.transform.matrix.toString(),color:b.transform.colorTransform.toString(),
                    alpha:b.alpha,visible:b.visible,blendMode:b.blendMode,opaqueBackground:b.opaqueBackground,
                    cacheAsBitmap:b.cacheAsBitmap,filterCount:b.filters.length,pattern:selected.pattern};
                for each(var scale:Number in out.scales)for(var grid:int=0;grid<3;++grid)
                    for each(var offset:Array in out.offsets) {
                        var row:Object=one(b,int(selected.surface.side),int(selected.surface.gutter),
                            int(selected.surface.cx)+grid,int(selected.surface.cy)+grid,scale,offset,out);
                        out.cases.push(row);
                        check("cell-sampling-reference-"+(out.cases.length-1),
                            row.repeat.changed==0 && row.repeat.sourceColored>0,row);
                    }
            } catch(error:Error) {out.error=error.message;}
            finally {
                out.sourceUnchanged=false;
                if(selected && originalPixels) {
                    try {
                        b=selected.bitmap;data=selected.data;
                        var after:Vector.<uint>=data.getVector(data.rect),equal:Boolean=after.length==originalPixels.length;
                        for(var n:int=0;equal && n<after.length;++n)if(after[n]!==originalPixels[n])equal=false;
                        out.sourceUnchanged=equal && b.bitmapData===data && stamp(b)==oldStamp &&
                            b.parent===parent && parent.getChildIndex(b)==depth && selected.surface.revision===revision &&
                            selected.surface.bitmaps[selected.layer]===b && selected.surface.nativeBuffers[selected.layer]===data &&
                            w.loc===loc && w.grafon===g && w.cam===cam && w.visual===visual &&
                            visual.transform.matrix.toString()==worldMatrix && Number(cam.scaleV)===out.worldScale;
                        out.sourcePixelsChecked=after.length;
                    } catch(verifyError:Error) {out.error+=(out.error?"; ":"")+verifyError.message;}
                }
                originalPixels=null;after=null;
                out.resourcesBalanced=out.allocations==out.disposals;
            }
            out.ok=out.error=="" && out.sourceUnchanged && out.resourcesBalanced && out.cases.length==18;
            check("cell-sampling-read-only-and-cleanup",out.ok,{error:out.error,sourceUnchanged:out.sourceUnchanged,
                allocations:out.allocations,disposals:out.disposals,cases:out.cases.length});
            return out;
        }

        private static function choose(surfaces:Array,out:Object):Object {
            var ordered:Array=surfaces.concat();ordered.sort(function(a:Object,b:Object):Number{return a.cy==b.cy?a.cx-b.cx:a.cy-b.cy;});
            out.examined=0;out.alphaZero=0;
            for each(var surface:Object in ordered) {
                if(surface.side!=320 || !surface.bitmaps || !surface.nativeBuffers)continue;
                for(var i:int=0;i<4;++i) {
                    var b:Bitmap=surface.bitmaps[i] as Bitmap,data:BitmapData=surface.nativeBuffers[i] as BitmapData;
                    if(!b || !data || !b.visible || !b.parent || b.bitmapData!==data)continue;
                    if(b.alpha<=0){++out.alphaZero;continue;}
                    var m:Matrix=b.transform.matrix,r:Rectangle=b.scrollRect;
                    if(!r || r.x!=surface.gutter || r.y!=surface.gutter || r.width!=320 || r.height!=320 ||
                        b.x!=surface.cx*320 || b.y!=surface.cy*320 || m.a!=1 || m.b!=0 || m.c!=0 || m.d!=1 ||
                        b.transform.matrix3D!=null || b.mask!=null || b.filters.length || b.cacheAsBitmap || b.blendMode!="normal")continue;
                    if(++out.examined>128)return null;
                    var seen:Object={},unique:int=0,colored:int=0;
                    for(var y:int=int(r.y)+10;y<r.bottom;y+=40)for(var x:int=int(r.x)+10;x<r.right;x+=40) {
                        var value:uint=data.getPixel32(x,y),key:String=value.toString(16);
                        if(!seen[key]){seen[key]=true;++unique;}
                        if((value>>>24)>0 && ((value&255)>16 || ((value>>>8)&255)>16 || ((value>>>16)&255)>16))++colored;
                    }
                    if(unique>=4 && colored>=4)return {surface:surface,bitmap:b,data:data,layer:i,pattern:{unique:unique,colored:colored}};
                }
            }
            return null;
        }

        private static function one(source:Bitmap,side:int,gutter:int,cx:int,cy:int,s:Number,offset:Array,out:Object):Object {
            var referenceRoot:Sprite=new Sprite(),worldRoot:Sprite=new Sprite(),localRoot:Sprite=new Sprite();
            var reference:Bitmap=new Bitmap(source.bitmapData,source.pixelSnapping,source.smoothing);
            var world:Sprite=new Sprite(),local:Sprite=new Sprite(),images:Array=[];
            var x:Number=cx*side,y:Number=cy*side,size:int=Math.ceil(side*s)+64;
            var result:Object;
            var matrix:Matrix=new Matrix(s,0,0,s,16-Math.floor(x*s)+offset[0],16-Math.floor(y*s)+offset[1]);
            try {
                copyStyle(source,reference);reference.scrollRect=source.scrollRect.clone();
                var nativeMatrix:Matrix=source.transform.matrix.clone();nativeMatrix.tx=x;nativeMatrix.ty=y;
                reference.transform.matrix=nativeMatrix;referenceRoot.addChild(reference);
                copyStyle(source,world);worldRoot.addChild(world);
                world.graphics.beginBitmapFill(source.bitmapData,new Matrix(1,0,0,1,x-gutter,y-gutter),false,source.smoothing);
                world.graphics.drawRect(x,y,side,side);world.graphics.endFill();
                copyStyle(source,local);local.x=x;local.y=y;localRoot.addChild(local);
                local.graphics.beginBitmapFill(source.bitmapData,new Matrix(1,0,0,1,-gutter,-gutter),false,source.smoothing);
                local.graphics.drawRect(0,0,side,side);local.graphics.endFill();
                var a:BitmapData=draw(referenceRoot,matrix,size,images,out),repeat:BitmapData=draw(referenceRoot,matrix,size,images,out);
                var b:BitmapData=draw(worldRoot,matrix,size,images,out),c:BitmapData=draw(localRoot,matrix,size,images,out);
                var worldDiff:Object=diff(a,b),localDiff:Object=diff(a,c);
                worldDiff.withinProductPixelLimit=worldDiff.maxRGB<=2 && worldDiff.maxAlpha==0;
                localDiff.withinProductPixelLimit=localDiff.maxRGB<=2 && localDiff.maxAlpha==0;
                if(s==43690/65536 && out.cases.length==6) {
                    save(a,"cell-reference.png");save(b,"cell-world-fill.png");save(c,"cell-local-fill.png");
                }
                result={cx:cx,cy:cy,offset:offset.concat(),scale:s,width:size,height:size,
                    drawMatrix:{a:matrix.a,b:matrix.b,c:matrix.c,d:matrix.d,tx:matrix.tx,ty:matrix.ty},
                    bitmapMatrix:reference.transform.matrix.toString(),localMatrix:local.transform.matrix.toString(),
                    phaseX:x*s-Math.floor(x*s),phaseY:y*s-Math.floor(y*s),
                    repeat:diff(a,repeat),worldFill:worldDiff,localFill:localDiff};
            } finally {
                world.graphics.clear();local.graphics.clear();
                if(reference.parent)reference.parent.removeChild(reference);reference.bitmapData=null;
                if(world.parent)world.parent.removeChild(world);if(local.parent)local.parent.removeChild(local);
                for each(var image:BitmapData in images){image.dispose();++out.disposals;}
            }
            return result;
        }
        private static function save(image:BitmapData,name:String):void {
            var stream:FileStream=new FileStream();
            stream.open(File.applicationStorageDirectory.resolvePath(name),FileMode.WRITE);
            try {stream.writeBytes(image.encode(image.rect,new PNGEncoderOptions()));}
            finally {stream.close();}
        }

        private static function copyStyle(source:Bitmap,target:DisplayObject):void {
            target.visible=source.visible;target.blendMode=source.blendMode;target.opaqueBackground=source.opaqueBackground;
            target.cacheAsBitmap=source.cacheAsBitmap;target.filters=source.filters;
            target.transform.colorTransform=source.transform.colorTransform;
        }
        private static function draw(root:Sprite,m:Matrix,size:int,images:Array,out:Object):BitmapData {
            var image:BitmapData=new BitmapData(size,size,true,0);images.push(image);++out.allocations;
            image.draw(root,m,null,null,null,true);return image;
        }
        private static function diff(a:BitmapData,b:BitmapData):Object {
            var av:Vector.<uint>=a.getVector(a.rect),bv:Vector.<uint>=b.getVector(b.rect);
            var out:Object={changed:0,maxRGB:0,maxAlpha:0,sourceColored:0};
            for(var i:int=0;i<av.length;++i) {
                var x:uint=av[i],y:uint=bv[i];
                if((x>>>24)>0 && ((x&255)>16 || ((x>>>8)&255)>16 || ((x>>>16)&255)>16))++out.sourceColored;
                if(x==y)continue;++out.changed;
                out.maxAlpha=Math.max(out.maxAlpha,Math.abs(int(x>>>24)-int(y>>>24)));
                out.maxRGB=Math.max(out.maxRGB,Math.abs(int(x&255)-int(y&255)),
                    Math.abs(int((x>>>8)&255)-int((y>>>8)&255)),Math.abs(int((x>>>16)&255)-int((y>>>16)&255)));
            }
            return out;
        }
        private static function stamp(b:Bitmap):String {
            return [b.transform.matrix.toString(),b.transform.colorTransform.toString(),b.scrollRect?b.scrollRect.toString():null,
                b.alpha,b.visible,b.pixelSnapping,b.smoothing,b.blendMode,b.opaqueBackground,b.cacheAsBitmap,
                b.filters.length,b.mask,b.transform.matrix3D,b.bitmapData.width,b.bitmapData.height].join("|");
        }
        private static function must(value:Boolean,message:String):void {if(!value)throw new Error(message);}
    }
}
